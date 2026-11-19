"""S2 (Sarvar) — controlled fusion ablation on ground-truth scenes (professor's guide §5).

Four methods on exactly the same frames and S3 masks:

    M1 depth_only     raw sensor depth, no cleaning filters, no reliability check, no fallback
    M2 mask_plane     every object placed from its mask + the desk plane (RGB prior, no depth geometry)
    M3 fixed_rgbd     standard cleaning (flying-pixel filter, desk RANSAC, outliers) with ONE fixed rule for
                      all objects: no per-object reliability routing, no spike filter, fixed fusion weights
    M4 adaptive_rgbd  the frozen configuration: reliability check per object (valid depth, see-through,
                      noise) decides depth vs mask+plane, spike filter, adaptive weights

    python -m src.evaluation.s2_fusion_eval --frames /data/frames --gt eval/ground_truth/ground_truth_positions.csv \\
        --tf configs/sensors/measured_tf.yaml
    python -m src.evaluation.s2_fusion_eval --synthetic       # self-check on generated frames with exact GT

``--frames`` holds ``<bag_id>/<frame_id>/`` folders (rgb.png, depth, camera_intrinsics.yaml, observation.json
from the frozen S3 run). Every GT row (bag_id, frame_id, class, x/y/z in the table frame) is one object
instance. Predictions are matched to GT objects of the same class with the Hungarian algorithm.
A missing prediction or an error above FAIL_CM counts as a failure.

Outputs (eval/results/s2/): s2_object_level_results.csv, fusion_ablation_table.csv (+ by condition),
error_by_object_type.png, failures/ (3 worst cases, image + JSON), frozen_fusion_config.yaml.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np
import yaml

from .common import COLUMNS, GT, as_float, load_tf, read_csv, results_dir, write_csv, write_json
from .stats import centroid_error, describe, rate

METHODS = ["M1_depth_only", "M2_mask_plane", "M3_fixed_rgbd", "M4_adaptive_rgbd"]
FAIL_CM = 5.0
CONDITIONS = ["normal", "shiny", "transparent", "small", "occluded"]
MIN_INSTANCES = {"normal": 50, "shiny": 30, "transparent": 30, "small": 30, "occluded": 30}   # guide §5.5


def method_configs(base: dict) -> dict:
    m1 = copy.deepcopy(base)
    m1["depth"]["flying_pixel_filter"]["enabled"] = False
    m1["depth_reliability"]["enabled"] = False
    m1["fusion"]["mode"] = "fixed"
    m3 = copy.deepcopy(base)
    m3["depth_reliability"]["enabled"] = False
    m3["fusion"]["mode"] = "fixed"
    m4 = copy.deepcopy(base)
    m4["fusion"]["mode"] = "adaptive"
    return {"M1_depth_only": m1, "M3_fixed_rgbd": m3, "M4_adaptive_rgbd": m4}


def desk_plane_from_tf(T):
    """The desk is z = 0 in the map frame → plane (n, d) in the camera frame."""
    return np.r_[T[2, :3], T[2, 3]]


def _predict(frame, obs, cfgs, T):
    """{method: [(label, center_map, object or None)]} for one frame."""
    from ..fusion_3d.mask_plane import estimate_from_mask
    from ..fusion_3d.pipeline import _resolve_tf, process_frame

    T = T if T is not None else _resolve_tf(frame, cfgs["M4_adaptive_rgbd"])
    if T is not None:
        frame.T_map_camera = T
    out = {}
    for m, c in cfgs.items():
        res = process_frame(frame, obs, c)
        out[m] = [(o.semantic_label, o.box_map["center"] if o.box_map else o.centroid_map, o) for o in res.objects
                  if (o.box_map or o.centroid_map)]
    plane = desk_plane_from_tf(T) if T is not None else None
    out["M2_mask_plane"] = []
    for o in obs:
        est = estimate_from_mask(o.mask, frame.intrinsics, plane, T) if plane is not None else None
        if est is not None:
            out["M2_mask_plane"].append((o.label, est["box_map"]["center"], None))
    return out


def _match(gt_rows, preds):
    """Hungarian matching per class on 3D distance. Returns [(gt_row, pred or None)]."""
    from ..tracking.assignment import linear_sum_assignment

    pairs = []
    for cls in sorted({g["class"] for g in gt_rows}):
        G = [g for g in gt_rows if g["class"] == cls]
        P = [p for p in preds if p[0].replace(" ", "_") == cls.replace(" ", "_")]
        if not P:
            pairs += [(g, None) for g in G]
            continue
        C = np.array([[centroid_error(p[1], [as_float(g["x_gt"]), as_float(g["y_gt"]), as_float(g["z_gt"])]) for p in P] for g in G])
        r, c = linear_sum_assignment(C)
        got = dict(zip(r.tolist(), c.tolist()))
        pairs += [(g, P[got[i]] if i in got else None) for i, g in enumerate(G)]
    return pairs


def evaluate(frames_root, gt_rows, tf_path=None, cfg_path=None) -> list[dict]:
    from ..fusion_3d.pipeline import load_config
    from ..preprocessing.frame_loader import load_frame, load_semantic_observations

    base = load_config(cfg_path)
    cfgs = method_configs(base)
    T = load_tf(tf_path)
    rows = []
    by_frame = {}
    for g in gt_rows:
        by_frame.setdefault((g["bag_id"], g["frame_id"]), []).append(g)
    for (bag, fid), G in sorted(by_frame.items()):
        d = Path(frames_root) / bag / fid
        if not d.exists():
            d = Path(frames_root) / fid
        if not (d / "observation.json").exists():
            print(f"skip {bag}/{fid}: no frame folder with observation.json")
            continue
        frame = load_frame(d)
        obs = load_semantic_observations(d / "observation.json")
        preds = _predict(frame, obs, cfgs, T)
        for m in METHODS:
            for g, p in _match(G, preds[m]):
                gt = [as_float(g["x_gt"]), as_float(g["y_gt"]), as_float(g["z_gt"])]
                o = p[2] if p else None
                terms = getattr(o, "confidence_terms", None) or {}
                err = None if p is None else 100 * centroid_error(p[1], gt)
                rows.append({"bag_id": bag, "frame_id": fid, "object_id": g["object_id"], "class": g["class"],
                             "condition": g.get("condition") or "normal", "method": m,
                             "x_pred": p[1][0] if p else None, "y_pred": p[1][1] if p else None, "z_pred": p[1][2] if p else None,
                             "x_gt": gt[0], "y_gt": gt[1], "z_gt": gt[2], "error_cm": err,
                             "valid_depth_ratio": terms.get("r_valid"), "depth_std_cm": (terms.get("sigma_z_m") or 0) * 100 if terms else None,
                             "confidence": getattr(o, "fused_confidence", None),
                             "status": "missed" if p is None else ("fail" if err > FAIL_CM else "ok")})
    return rows


def summarise(rows) -> tuple[list, list]:
    table, by_cond = [], []
    for m in METHODS:
        sub = [r for r in rows if r["method"] == m]
        errs = [r["error_cm"] for r in sub if r["error_cm"] is not None]
        d = describe(errs)
        fails = sum(r["status"] != "ok" for r in sub)
        table.append({"method": m, "n_instances": len(sub), "median_error_cm": d["median"], "mean_error_cm": d["mean"],
                      "p95_error_cm": d["p95"], "rmse_cm": round(float(np.sqrt(np.mean(np.square(errs)))), 3) if errs else None,
                      "ci95_mean_cm": d["ci95"], "failure_rate": rate(fails, len(sub))["text"],
                      "missed": sum(r["status"] == "missed" for r in sub)})
        for c in sorted({r["condition"] for r in sub}):
            cs = [r for r in sub if r["condition"] == c]
            dc = describe([r["error_cm"] for r in cs if r["error_cm"] is not None])
            by_cond.append({"method": m, "condition": c, "n": len(cs), "min_required": MIN_INSTANCES.get(c, ""),
                            "median_error_cm": dc["median"], "mean_error_cm": dc["mean"], "p95_error_cm": dc["p95"],
                            "failure_rate": rate(sum(r["status"] != "ok" for r in cs), len(cs))["text"]})
    return table, by_cond


def plot(rows, out: Path) -> Path | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    conds = [c for c in CONDITIONS if any(r["condition"] == c for r in rows)] or sorted({r["condition"] for r in rows})
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    w = 0.8 / len(METHODS)
    colors = ["#8a8a8a", "#d18b0f", "#3b82f6", "#14a085"]
    for i, m in enumerate(METHODS):
        med = []
        for c in conds:
            e = [r["error_cm"] for r in rows if r["method"] == m and r["condition"] == c and r["error_cm"] is not None]
            med.append(np.median(e) if e else np.nan)
        ax.bar(np.arange(len(conds)) + (i - 1.5) * w, med, w, label=m.replace("_", " "), color=colors[i])
    ax.set_xticks(range(len(conds)), [f"{c}\n(n={sum(1 for r in rows if r['method'] == METHODS[0] and r['condition'] == c)})" for c in conds])
    ax.set_ylabel("median centroid error (cm)")
    ax.set_title("S2 fusion ablation: error by object condition")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = out / "error_by_object_type.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def failures(rows, frames_root, out: Path, k: int = 3) -> list:
    """The k worst M4 instances: JSON with all four methods + the RGB frame with the GT point marked."""
    d = out / "failures"
    d.mkdir(parents=True, exist_ok=True)
    m4 = sorted([r for r in rows if r["method"] == "M4_adaptive_rgbd"],
                key=lambda r: -(r["error_cm"] if r["error_cm"] is not None else 1e9))[:k]
    saved = []
    for i, r in enumerate(m4, 1):
        same = [x for x in rows if (x["bag_id"], x["frame_id"], x["object_id"]) == (r["bag_id"], r["frame_id"], r["object_id"])]
        info = {"rank": i, "bag_id": r["bag_id"], "frame_id": r["frame_id"], "object_id": r["object_id"], "class": r["class"],
                "condition": r["condition"], "errors_cm": {x["method"]: x["error_cm"] for x in same},
                "explanation": "fill in: why did this fail (depth holes? mask bleed? see-through?)"}
        write_json(d / f"failure_{i}.json", info)
        src = Path(frames_root) / r["bag_id"] / r["frame_id"] / "rgb.png"
        if src.exists():
            (d / f"failure_{i}_rgb.png").write_bytes(src.read_bytes())
        saved.append(info)
    return saved


def write_all(rows, frames_root, cfg_path=None, out: Path | None = None) -> dict:
    out = out or results_dir("s2")
    write_csv(out / "s2_object_level_results.csv", rows, COLUMNS["s2_object_results"])
    table, by_cond = summarise(rows)
    write_csv(out / "fusion_ablation_table.csv", table)
    write_csv(out / "fusion_ablation_by_condition.csv", by_cond)
    plot(rows, out)
    failures(rows, frames_root, out)
    from ..fusion_3d.pipeline import load_config
    (out / "frozen_fusion_config.yaml").write_text("# frozen S2 configuration used for every method (M4 = as is)\n"
                                                   + yaml.safe_dump(load_config(cfg_path), sort_keys=False))
    return {"table": table, "by_condition": by_cond}


# ---------------------------------------------------------------- synthetic self-check
def synthetic(out_root: Path, seeds=(0, 1, 2)) -> tuple[Path, list]:
    """Generated frames with exact GT (mock_data) laid out like real bags, so the whole tool can be tested."""
    from ..fusion_3d.pipeline import _resolve_tf, load_config
    from ..preprocessing.frame_loader import load_frame
    from ..preprocessing.mock_data import generate

    cond = {"glass": "transparent", "multimeter": "small"}
    gt = []
    for s in seeds:
        for prof, mode, fail in (("zed_mini", "see_through", None), ("realsense", "holes", None), ("zed_mini", "see_through", 1.0)):
            bag = f"SYN_{prof}_{mode}" + ("_full" if fail else "")
            d = generate(out_root / bag / f"frame_{s:04d}", seed=s, profile=prof, glass_mode=mode, glass_failure=fail)
            T = _resolve_tf(load_frame(d), load_config())
            for g in json.loads((d / "ground_truth.json").read_text())["objects"]:
                c = g["center"]
                if T is not None and g.get("frame", "map") != "map":
                    c = (T @ np.r_[c, 1.0])[:3].tolist()
                gt.append({"bag_id": bag, "frame_id": d.name, "object_id": f"{g['name']}_01", "class": g["name"],
                           "x_gt": c[0], "y_gt": c[1], "z_gt": c[2], "condition": cond.get(g["name"], "normal"),
                           "measured_by": "generator"})
    return out_root, gt


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", help="root with <bag_id>/<frame_id>/ folders")
    ap.add_argument("--gt", default=str(GT / "ground_truth_positions.csv"))
    ap.add_argument("--tf", help="measured_tf.yaml (table frame); default: TF in each frame / fusion config")
    ap.add_argument("--config", help="fusion config (default configs/fusion_3d.yaml)")
    ap.add_argument("--synthetic", action="store_true", help="self-check on generated frames (not a result)")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.synthetic:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="s2_syn_"))
        frames, gt = synthetic(tmp)
        out = Path(a.out) if a.out else results_dir("s2") / "synthetic_selfcheck"
    else:
        frames, gt = a.frames, read_csv(a.gt)
        out = Path(a.out) if a.out else results_dir("s2")
        if not frames or not gt:
            ap.error("--frames and a filled --gt file are needed (or use --synthetic)")
    out.mkdir(parents=True, exist_ok=True)
    rows = evaluate(frames, gt, a.tf, a.config)
    res = write_all(rows, frames, a.config, out)
    for r in res["table"]:
        print(r)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

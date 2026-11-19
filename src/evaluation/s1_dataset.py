"""S1 (Muzaffar) — shared evaluation dataset: plan, per-bag metadata, manifest, splits, measured TF.

Professor's W12–W16 guide §2–§4. One controlled dataset for all seven modules.

    # 1. the recording plan: 45 bags in 8 families, difficulty, repetitions, dev/test split (frozen)
    python -m src.evaluation.s1_dataset plan
    # 2. one metadata YAML per planned bag (fill in on the recording day; §2.4)
    python -m src.evaluation.s1_dataset metadata
    # 3. measured camera pose in the table frame (tape measure + inclinometer) -> measured_tf.yaml
    python -m src.evaluation.s1_dataset tf --height 1.284 --pitch-deg 46.2 --x -0.20 --y 0.40 --yaw-deg 0
    # 4. manifest of what was actually recorded (+ measured FPS / gaps / sync from each bag)
    python -m src.evaluation.s1_dataset manifest --bags /path/to/bags
    # 5. RGB/depth alignment check: edge overlay of 10 frames with strong object boundaries
    python -m src.evaluation.s1_dataset align --bag /path/to/bags/B01_static_easy_rep1

Outputs go to eval/dataset/ (plan, manifest, metadata/, splits.json) and eval/results/s1/.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import yaml

from .common import COLUMNS, DATASET, GT, read_csv, results_dir, write_csv, write_json

# family -> (name, number of bags, typical duration, purpose, used by, difficulty cycle, scenario hints)
FAMILIES = {
    "A": ("calibration_reference", 3, "30-60 s", "camera calibration, alignment, static geometry", "S1, S2",
          ["easy"], ["checkerboard: centre, corners, near/far, tilts (>= 20 poses)", "tape-marked table frame, empty desk",
                     "static reference objects at measured positions"]),
    "B": ("static_known", 6, "30-45 s", "baseline localization and graph relations", "S2, S4",
          ["easy", "medium", "hard"], ["laptop, mug, book, bottle separated", "mug ON book, bottle near laptop",
                                       "cluttered: 6 objects, partial overlap"]),
    "C": ("difficult_depth", 6, "30-45 s", "glass, shiny, dark, small, partial depth", "S2",
          ["medium", "hard"], ["shiny mug + dark phone", "transparent glass beside laptop", "small objects (USB stick, eraser)"]),
    "D": ("unseen_objects", 6, "30-60 s", "5 held-out classes, prompt robustness", "S3",
          ["medium", "hard"], ["one held-out object among known ones", "held-out object + distractors (multimeter, calculator, power bank)"]),
    "E": ("motion_relocation", 6, "45-60 s", "tracking, temporal graph, relation changes", "S4, S6",
          ["easy", "medium", "hard"], ["mug moved desk -> book", "two objects swapped", "pick up, hold, place elsewhere"]),
    "F": ("occlusion_reentry", 6, "45-60 s", "object permanence and re-ID", "S6",
          ["medium", "hard"], ["hand covers mug 5-10 frames", "box hides object 11-20 frames", "object leaves view and re-enters (21-40 frames)"]),
    "G": ("similar_crossing", 4, "45-60 s", "ID-switch stress test", "S6",
          ["hard"], ["two identical mugs cross paths", "two similar bottles swap places"]),
    "H": ("language_action", 8, "45-90 s", "reasoning, verification, safe action", "S5, S7",
          ["easy", "medium", "hard"], ["known objects, simple queries", "negative / multi-hop queries", "blocked path + unseen target"]),
}
REPS = {"A": 1, "D": 2, "F": 2}          # §2.2: >= 3 repetitions overall; variable tests aim for more
DEV_SHARE = 1 / 3                         # §2.2: tune only on dev, report on test


def recording_plan() -> list[dict]:
    rows = []
    for fam, (name, n, dur, purpose, users, diffs, hints) in FAMILIES.items():
        for k in range(n):
            diff = diffs[k % len(diffs)]
            hint = hints[k % len(hints)]
            rep = k // len(hints) + 1
            bag_id = f"{fam}{k + 1:02d}_{name.split('_')[0]}_{diff}_rep{rep}"
            # dev split: the first repetition of every hint in the bigger families (frozen by construction)
            split = "dev" if (n >= 6 and k < max(1, math.floor(n * DEV_SHARE))) else "test"
            rows.append({"bag_id": bag_id, "family": f"{fam} {name}", "difficulty": diff, "scenario": hint,
                         "typical_duration": dur, "purpose": purpose, "used_by": users, "repetition": rep, "split": split})
    return rows


def metadata_template(row: dict) -> dict:
    """§2.4 metadata fields; values in <> are filled in on the recording day."""
    return {"bag_id": row["bag_id"], "date": "2026-11-XX", "duration_s": None, "camera": "ZED_Mini",
            "camera_height_m": None, "camera_pitch_deg": None, "lighting": "indoor_normal", "difficulty": row["difficulty"],
            "family": row["family"], "scenario": row["scenario"], "split": row["split"],
            "objects": [], "unseen_objects": [], "motion_events": [], "occlusion_fraction": 0.0,
            "ground_truth_available": False, "notes": ""}


def write_plan(out: Path = DATASET) -> list[dict]:
    rows = recording_plan()
    write_csv(out / "recording_plan.csv", rows)
    write_json(out / "splits.json", {"rule": "tune thresholds/prompts only on 'dev'; final numbers only on 'test'",
                                     "dev": [r["bag_id"] for r in rows if r["split"] == "dev"],
                                     "test": [r["bag_id"] for r in rows if r["split"] == "test"]})
    return rows


def write_metadata(out: Path = DATASET) -> int:
    plan = read_csv(out / "recording_plan.csv") or write_plan(out)
    d = out / "metadata"
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in plan:
        p = d / f"{r['bag_id']}.yaml"
        if not p.exists():                     # never overwrite what the team filled in
            p.write_text(yaml.safe_dump(metadata_template(r), sort_keys=False, allow_unicode=True))
            n += 1
    return n


# ---------------------------------------------------------------- measured TF (§3.1 + §4.1 step 3)
def measured_tf(height_m: float, pitch_deg: float, x_m: float = 0.0, y_m: float = 0.0, yaw_deg: float = 0.0,
                roll_deg: float = 0.0) -> dict:
    """Camera pose in the tape-marked table frame (origin at a table corner, +X long edge, +Y short edge, +Z up).

    pitch = downward tilt of the optical axis below the horizontal (what an inclinometer app shows);
    yaw = direction of the optical axis in the table plane, measured from +X towards +Y.
    Returns T_map_camera_link (ROS camera_link: x forward, y left, z up) as xyz + rpy and a 4x4 matrix.
    """
    r, p, yw = (math.radians(v) for v in (roll_deg, pitch_deg, yaw_deg))
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(yw), math.sin(yw)
    # ZYX (yaw, pitch, roll); positive pitch about +y tilts camera_link's x axis downwards
    R = np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                  [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                  [-sp, cp * sr, cp * cr]])
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, [x_m, y_m, height_m]
    return {"frame": "map (tape-marked table frame)", "child_frame": "camera_link",
            "xyz": [round(x_m, 4), round(y_m, 4), round(height_m, 4)], "rpy": [round(r, 5), round(p, 5), round(yw, 5)],
            "rpy_deg": [roll_deg, pitch_deg, yaw_deg], "T_map_camera_link": np.round(T, 6).tolist(),
            "source": "measured with tape measure + inclinometer (replaces the 0.80 m placeholder)"}


def write_tf(tf: dict, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# S1 measured camera pose (python -m src.evaluation.s1_dataset tf)\n" + yaml.safe_dump(tf, sort_keys=False))
    return out


# ---------------------------------------------------------------- manifest (§4.1 step 5, Appendix A.1)
def build_manifest(bag_dirs, out: Path = DATASET) -> list[dict]:
    from ..sensors.dataset_readme import describe, find_bags

    plan = {r["bag_id"]: r for r in read_csv(out / "recording_plan.csv") or recording_plan()}
    gt_bags = {r["bag_id"] for r in read_csv(GT / "ground_truth_positions.csv")}
    rows, measured = [], []
    for bag in find_bags(bag_dirs):
        name = bag.stem if bag.is_file() else bag.name
        meta_p = out / "metadata" / f"{name}.yaml"
        meta = yaml.safe_load(meta_p.read_text()) if meta_p.exists() else {}
        try:
            m = describe(bag)
        except Exception as e:  # unreadable bag: still listed, with the reason
            m = {"duration_s": None, "fps": None, "gaps": None, "sync_p95_ms": None, "error": str(e)}
        measured.append({"bag_id": name, **m})
        pl = plan.get(name, {})
        rows.append({"bag_id": name, "family": pl.get("family", meta.get("family", "unplanned")), "date": meta.get("date"),
                     "duration_s": m.get("duration_s"), "fps": m.get("fps"), "difficulty": meta.get("difficulty", pl.get("difficulty")),
                     "lighting": meta.get("lighting"), "objects": ";".join(meta.get("objects") or []),
                     "unseen_objects": ";".join(meta.get("unseen_objects") or []),
                     "motion": ";".join(map(str, meta.get("motion_events") or [])), "occlusion": meta.get("occlusion_fraction"),
                     "gt_available": name in gt_bags or bool(meta.get("ground_truth_available")),
                     "split": pl.get("split", "unplanned"), "path": str(bag), "notes": meta.get("notes", "")})
    write_csv(out / "dataset_manifest.csv", rows, COLUMNS["dataset_manifest"])
    write_json(out / "dataset_manifest.json", rows)
    write_csv(results_dir("s1") / "bag_timing.csv", measured)
    return rows


def completeness(out: Path = DATASET) -> dict:
    """What is still missing against the plan and §4.4 minimums."""
    plan = read_csv(out / "recording_plan.csv") or recording_plan()
    man = {r["bag_id"]: r for r in read_csv(out / "dataset_manifest.csv")}
    meta_dir = out / "metadata"
    gt_rows = read_csv(GT / "ground_truth_positions.csv")
    gt_scenes = {(r["bag_id"], r["frame_id"]) for r in gt_rows}
    fam = {}
    for r in plan:
        f = fam.setdefault(r["family"], {"planned": 0, "recorded": 0})
        f["planned"] += 1
        f["recorded"] += r["bag_id"] in man
    filled = sum(1 for r in plan if (meta_dir / f"{r['bag_id']}.yaml").exists()
                 and (yaml.safe_load((meta_dir / f"{r['bag_id']}.yaml").read_text()) or {}).get("duration_s"))
    calib = Path("configs/sensors/calibration_report.json")
    rep = {"planned_bags": len(plan), "recorded_bags": sum(r["bag_id"] in man for r in plan),
           "unplanned_bags": sorted(set(man) - {r["bag_id"] for r in plan}), "metadata_filled": filled,
           "ground_truth_scenes": len(gt_scenes), "ground_truth_objects": len(gt_rows), "by_family": fam,
           "calibration_report": calib.exists(), "measured_tf": Path("configs/sensors/measured_tf.yaml").exists(),
           "minimums": {"evaluation_bags": "~45", "ground_truth_scenes": ">= 15", "calibration": "mean/median/max + overlay"}}
    write_json(results_dir("s1") / "dataset_completeness.json", rep)
    return rep


# ---------------------------------------------------------------- RGB/depth alignment (§4.3)
def alignment_check(bag, n_frames: int = 10, every: int = 15, out: Path | None = None) -> list[dict]:
    """Overlay RGB edges (green) on depth edges (magenta) for frames with strong boundaries; report edge agreement."""
    import cv2

    from ..sensors.bag_replay import BagSource, detect_topics, iter_frames

    out = out or results_dir("s1") / "alignment" / Path(bag).name
    out.mkdir(parents=True, exist_ok=True)
    src = BagSource(Path(bag))
    cands = []
    for k, fr in enumerate(iter_frames(src, detect_topics(src.topics), every=every)):
        grey = cv2.cvtColor(fr.rgb, cv2.COLOR_RGB2GRAY)
        e_rgb = cv2.Canny(grey, 60, 160)
        d = fr.depth_raw.astype(np.float32)
        d = np.where(np.isfinite(d), d, 0)
        dn = cv2.normalize(d, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        e_d = cv2.Canny(dn, 30, 90)
        cands.append((int(e_rgb.sum() // 255), k, fr.rgb, e_rgb, e_d))
        if len(cands) >= 6 * n_frames:
            break
    rows = []
    for strength, k, rgb, e_rgb, e_d in sorted(cands, key=lambda c: -c[0])[:n_frames]:
        near = cv2.dilate(e_d, np.ones((5, 5), np.uint8)) > 0     # RGB edge within 2 px of a depth edge
        agree = float((near & (e_rgb > 0)).sum() / max(1, (e_rgb > 0).sum()))
        vis = rgb.copy()
        vis[e_rgb > 0] = (0, 255, 0)
        vis[e_d > 0] = (255, 0, 255)
        cv2.imwrite(str(out / f"frame_{k:04d}_edges.png"), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
        rows.append({"frame": k, "rgb_edge_px": strength, "rgb_edges_near_depth_edge": round(agree, 3)})
    write_csv(out / "alignment.csv", rows)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("metadata")
    t = sub.add_parser("tf")
    t.add_argument("--height", type=float, required=True, help="camera_link height above the table top (m)")
    t.add_argument("--pitch-deg", type=float, required=True, help="downward tilt of the optical axis (deg)")
    t.add_argument("--x", type=float, default=0.0)
    t.add_argument("--y", type=float, default=0.0)
    t.add_argument("--yaw-deg", type=float, default=0.0)
    t.add_argument("--roll-deg", type=float, default=0.0)
    t.add_argument("--out", default="configs/sensors/measured_tf.yaml")
    m = sub.add_parser("manifest")
    m.add_argument("--bags", nargs="+", required=True)
    sub.add_parser("status")
    al = sub.add_parser("align")
    al.add_argument("--bag", required=True)
    al.add_argument("--frames", type=int, default=10)
    a = ap.parse_args()
    if a.cmd == "plan":
        rows = write_plan()
        print(f"{len(rows)} planned bags -> {DATASET / 'recording_plan.csv'} (+ splits.json)")
    elif a.cmd == "metadata":
        print(f"{write_metadata()} new metadata files in {DATASET / 'metadata'}")
    elif a.cmd == "tf":
        p = write_tf(measured_tf(a.height, a.pitch_deg, a.x, a.y, a.yaw_deg, a.roll_deg), Path(a.out))
        print(f"-> {p}")
    elif a.cmd == "manifest":
        rows = build_manifest(a.bags)
        print(f"{len(rows)} bags -> {DATASET / 'dataset_manifest.csv'}")
        print(completeness())
    elif a.cmd == "status":
        print(completeness())
    elif a.cmd == "align":
        for r in alignment_check(a.bag, a.frames):
            print(r)


if __name__ == "__main__":
    main()

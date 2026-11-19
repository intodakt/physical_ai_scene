"""S6 (Shakhzodjon) — real tracking sequences and the 60 action-safety trials (professor's guide §9).

Tracking ground truth is tied to the *detections*, not to one tracker's IDs, so every tracker can be scored on
the same file: one row per S2 detection (``detection_id`` = frame-local object id) with the person's
``gt_object_id``, plus one row per frame in which a GT object is hidden (``occluded=1``, no detection).

    # 0. the 30-sequence plan (6 scenarios x 5) mapped onto the recorded bags
    python -m src.evaluation.s6_tracking_eval plan
    # 1. annotation sheet for a pipeline run of one sequence (fill gt_object_id; add occluded rows)
    python -m src.evaluation.s6_tracking_eval sheet --run runs/F01 --scenario medium_occlusion
    # 2. metrics + baseline (15 cm gate) vs multi-cue (Hungarian: distance + label + size [+ appearance])
    python -m src.evaluation.s6_tracking_eval score --runs runs/F01 runs/F02 ... [--frames-root /data/frames]
    # 3. 60 action trials (30 safe, 30 unsafe) on a scene graph, labels from an independent geometric check
    python -m src.evaluation.s6_tracking_eval actions --graph outputs/scene_graph/frame_000_scene_graph.json

Tracking metrics: ID switches, track recall, occlusion recovery rate, re-ID accuracy (+ IDF1 when the
``motmetrics`` package is installed). Action metrics: unsafe rejection, safe acceptance, false rejection,
false acceptance.

Outputs (eval/results/s6/): tracking_sequences_manifest.csv, tracking_metrics.csv, occlusion_recovery_by_length.csv,
baseline_vs_multicue_tracking.csv, action_safety_60_trials.csv (+ summary), trajectories_<seq>.png.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from .common import COLUMNS, GT, as_bool, as_float, read_csv, results_dir, write_csv
from .stats import rate

SCENARIOS = [  # (name, number of sequences, notes, families that can hold it)
    ("single_object_movement", 5, "basic baseline", "E"),
    ("short_occlusion_5_10", 5, "object hidden briefly", "F"),
    ("medium_occlusion_11_20", 5, "matches the current memory target", "F"),
    ("long_occlusion_21_40", 5, "stress test", "F"),
    ("similar_objects_crossing", 5, "ID-switch stress test", "G"),
    ("disappear_reenter", 5, "re-identification", "E, F"),
]
SHEET_COLS = ["sequence_id", "scenario", "frame_id", "detection_id", "gt_object_id", "pred_track_id", "occluded", "reappeared",
              "x", "y", "label"]
LENGTH_BUCKETS = [(1, 4, "1-4"), (5, 10, "5-10"), (11, 20, "11-20"), (21, 40, "21-40"), (41, 10 ** 6, ">40")]


# ---------------------------------------------------------------- plan + sheet
def plan() -> list[dict]:
    rows, k = [], 0
    for name, n, note, fam in SCENARIOS:
        for i in range(1, n + 1):
            k += 1
            rows.append({"sequence_id": f"T{k:02d}_{name}_{i}", "scenario": name, "notes": note, "record_in_family": fam,
                         "bag_id": "", "start_s": "", "end_s": ""})
    return rows


def _frames(run):
    return [json.loads(p.read_text()) for p in sorted((Path(run) / "objects").glob("*_objects.json"))]


def sheet(run, scenario="") -> list[dict]:
    seq = Path(run).name
    rows = []
    for f in _frames(run):
        for o in f["objects"]:
            c = (o.get("box_map") or {}).get("center") or o.get("centroid_map") or o["centroid"]
            rows.append({"sequence_id": seq, "scenario": scenario, "frame_id": f["frame"], "detection_id": o["object_id"],
                         "gt_object_id": "", "pred_track_id": o.get("persistent_id", ""), "occluded": 0, "reappeared": "",
                         "x": round(c[0], 4), "y": round(c[1], 4), "label": o["semantic_label"]})
    return rows


# ---------------------------------------------------------------- re-tracking with each method
def track_ids(frames, method: str, appearance: dict | None = None) -> dict:
    """{(frame, detection_id): track id} for 'baseline' (Week-5 greedy 15 cm gate) or 'multicue'."""
    from ..integration.s6_placeholder import CentroidTracker
    from ..tracking import MultiTermTracker

    if method == "baseline":
        tr = CentroidTracker()
    else:
        tr = MultiTermTracker(w_app=0.5 if appearance else 0.0)
    out = {}
    for f in frames:
        objs = copy.deepcopy(f["objects"])
        for o in objs:
            o.pop("persistent_id", None)
            if appearance:
                o["appearance"] = appearance.get((f["frame"], o["object_id"]))
        if method == "baseline":
            tr.update(objs)
        else:
            tr.update(objs, f.get("timestamp"))
        for o in objs:
            out[(f["frame"], o["object_id"])] = o["persistent_id"]
    return out


def appearance_from_frames(frames, frames_root) -> dict:
    import cv2

    from ..open_vocab.embeddings import ColorHistEmbedder
    emb, out = ColorHistEmbedder(), {}
    for f in frames:
        p = Path(frames_root) / f["frame"] / "rgb.png"
        if not p.exists():
            continue
        rgb = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
        for o in f["objects"]:
            if o.get("bbox_2d"):
                x1, y1, x2, y2 = (int(round(v)) for v in o["bbox_2d"])
                m = np.zeros(rgb.shape[:2], bool)
                m[max(0, y1):y2, max(0, x1):x2] = True
                out[(f["frame"], o["object_id"])] = emb.embed(rgb, m).tolist()
    return out


# ---------------------------------------------------------------- metrics
def metrics(gt_rows, ids: dict) -> dict:
    """gt_rows of ONE sequence (detections + occluded rows); ids = {(frame, detection_id): pred id}."""
    by_obj = defaultdict(list)
    order = {f: k for k, f in enumerate(sorted({r["frame_id"] for r in gt_rows}))}
    for r in gt_rows:
        if r.get("gt_object_id"):
            by_obj[r["gt_object_id"]].append(r)
    switches = visible = tracked = 0
    occl_events = recovered = 0
    reentry = reid_ok = 0
    gaps = []
    for gid, rows in by_obj.items():
        rows.sort(key=lambda r: order[r["frame_id"]])
        last_id, hidden, hidden_len = None, False, 0
        for r in rows:
            if as_bool(r.get("occluded")):
                if last_id is not None:
                    hidden, hidden_len = True, hidden_len + 1
                continue
            visible += 1
            pid = ids.get((r["frame_id"], r["detection_id"])) if r.get("detection_id") else None
            if pid:
                tracked += 1
            if hidden:
                occl_events += 1
                ok = pid is not None and pid == last_id
                recovered += ok
                gaps.append((hidden_len, ok))
                if as_bool(r.get("reappeared")):
                    reentry += 1
                    reid_ok += ok
            elif pid and last_id and pid != last_id:
                switches += 1
            if pid:
                last_id = pid
            hidden, hidden_len = False, 0
    return {"gt_objects": len(by_obj), "id_switches": switches, "track_recall": rate(tracked, visible),
            "occlusion_recovery": rate(recovered, occl_events), "reid_accuracy": rate(reid_ok, reentry), "gaps": gaps}


def idf1(gt_rows, ids) -> float | None:
    try:
        import motmetrics as mm
    except ImportError:
        return None
    acc = mm.MOTAccumulator(auto_id=True)
    frames = sorted({r["frame_id"] for r in gt_rows})
    for f in frames:
        rows = [r for r in gt_rows if r["frame_id"] == f and r.get("gt_object_id") and not as_bool(r.get("occluded"))]
        g = [r["gt_object_id"] for r in rows]
        h = sorted({ids[(f, r["detection_id"])] for r in rows if (f, r["detection_id"]) in ids})
        D = [[0.0 if ids.get((f, r["detection_id"])) == hh else np.nan for hh in h] for r in rows]
        acc.update(g, h, D)
    s = mm.metrics.create().compute(acc, metrics=["idf1"], name="seq")
    return round(float(s["idf1"].iloc[0]), 4)


def score(gt_rows, runs, frames_root=None) -> dict:
    by_seq = defaultdict(list)
    for r in gt_rows:
        by_seq[r["sequence_id"]].append(r)
    per_seq, comparison, buckets = [], [], defaultdict(lambda: [0, 0])
    totals = defaultdict(lambda: defaultdict(int))
    for run in runs:
        seq = Path(run).name
        if seq not in by_seq:
            print(f"skip {seq}: no annotated rows")
            continue
        frames = _frames(run)
        app = appearance_from_frames(frames, frames_root) if frames_root else None
        methods = {"baseline_15cm_gate": track_ids(frames, "baseline"), "multicue_hungarian": track_ids(frames, "multicue")}
        if app:
            methods["multicue_hungarian+appearance"] = track_ids(frames, "multicue", app)
        scen = by_seq[seq][0].get("scenario", "")
        for name, ids in methods.items():
            m = metrics(by_seq[seq], ids)
            row = {"sequence_id": seq, "scenario": scen, "method": name, "gt_objects": m["gt_objects"], "id_switches": m["id_switches"],
                   "track_recall": m["track_recall"]["text"], "occlusion_recovery": m["occlusion_recovery"]["text"],
                   "reid_accuracy": m["reid_accuracy"]["text"], "idf1": idf1(by_seq[seq], ids)}
            per_seq.append(row)
            t = totals[name]
            t["seq"] += 1
            t["sw"] += m["id_switches"]
            for key in ("track_recall", "occlusion_recovery", "reid_accuracy"):
                t[key + "_n"] += m[key]["num"]
                t[key + "_d"] += m[key]["den"]
            if name == "multicue_hungarian":
                for L, ok in m["gaps"]:
                    lab = next(b[2] for b in LENGTH_BUCKETS if b[0] <= L <= b[1])
                    buckets[lab][0] += ok
                    buckets[lab][1] += 1
    for name, t in totals.items():
        comparison.append({"method": name, "sequences": t["seq"], "id_switches": t["sw"],
                           "track_recall": rate(t["track_recall_n"], t["track_recall_d"])["text"],
                           "occlusion_recovery": rate(t["occlusion_recovery_n"], t["occlusion_recovery_d"])["text"],
                           "reid_accuracy": rate(t["reid_accuracy_n"], t["reid_accuracy_d"])["text"]})
    by_len = [{"hidden_frames": b[2], "recovered": rate(*buckets[b[2]])["text"]} for b in LENGTH_BUCKETS if b[2] in buckets]
    return {"per_sequence": per_seq, "comparison": comparison, "by_length": by_len}


def plot_tracks(run, out: Path) -> Path | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    tr = defaultdict(list)
    for k, f in enumerate(_frames(run)):
        for o in f["objects"]:
            c = (o.get("box_map") or {}).get("center") or o.get("centroid_map")
            if c and o.get("persistent_id"):
                tr[o["persistent_id"]].append((k, c[0], c[1]))
    fig, ax = plt.subplots(figsize=(5.5, 4.5), dpi=150)
    for pid, pts in sorted(tr.items()):
        P = np.array(pts)
        ax.plot(P[:, 2], P[:, 1], "-o", ms=2.5, lw=1, label=pid)
    ax.invert_xaxis()
    ax.set_xlabel("y (m)")
    ax.set_ylabel("x (m)")
    ax.set_title(f"Trajectories — {Path(run).name}", fontsize=9)
    ax.legend(fontsize=6, frameon=False, ncol=2)
    fig.tight_layout()
    p = out / f"trajectories_{Path(run).name}.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- action safety (60 trials)
def _rect(node, margin):
    (x, y, _), (w, d, _) = node["pose_map"], node["size"]
    return x, y, node.get("yaw", 0.0), w / 2 + margin, d / 2 + margin


def _in_rect(p, r) -> bool:
    """Independent check (not the planner's polygon code): point inside a rotated, inflated rectangle."""
    x, y, yaw, hx, hy = r
    c, s = math.cos(yaw), math.sin(yaw)
    dx, dy = p[0] - x, p[1] - y
    return abs(c * dx + s * dy) <= hx and abs(-s * dx + c * dy) <= hy


def oracle_safe(graph, target_id, cfg) -> tuple[bool, str]:
    nodes = {n["id"]: n for n in graph["nodes"]}
    if target_id not in nodes:
        return False, "target not in graph"
    t = nodes[target_id]
    if t.get("state") == "occluded":
        return False, "target occluded"
    zones = [_rect(n, cfg["exclusion_margin_m"]) for n in graph["nodes"] if n["id"] != target_id and not n.get("virtual")
             and n.get("state") != "occluded" and any(w in n["names"][0]["text"].split() for w in cfg["exclusion_labels"])]
    goal = t["pose_map"][:2]
    if any(_in_rect(goal, z) for z in zones):
        return False, "target inside exclusion zone"
    a = cfg["agent_start"]
    L = math.dist(a, goal)
    for k in range(int(L / 0.002) + 1):
        f = k * 0.002 / L if L else 0
        if any(_in_rect((a[0] + f * (goal[0] - a[0]), a[1] + f * (goal[1] - a[1])), z) for z in zones):
            return False, "straight path crosses exclusion zone"
    return True, "clear"


def action_trials(graph, cfg, n_safe=30, n_unsafe=30, seed=0) -> list[dict]:
    from ..planning import build_action_goal

    rng = random.Random(seed)
    excl = [n for n in graph["nodes"] if any(w in n["names"][0]["text"].split() for w in cfg["exclusion_labels"])]
    movable = [n for n in graph["nodes"] if not n.get("virtual") and n not in excl]
    if not excl or not movable:
        raise ValueError("graph needs an exclusion object (e.g. laptop) and at least one other object")
    zone = excl[0]
    bx0, bx1, by0, by1 = cfg["workspace_bounds"]
    trials, safe, unsafe_geo = [], [], []
    tries = 0
    while (len(safe) < n_safe or len(unsafe_geo) < 18) and tries < 20000:
        tries += 1
        g = copy.deepcopy(graph)
        tgt = rng.choice([n for n in g["nodes"] if n["id"] in {m["id"] for m in movable}])
        if rng.random() < 0.5:     # near the zone: the interesting cases
            zx, zy = zone["pose_map"][:2]
            tgt["pose_map"][:2] = [zx + rng.uniform(-0.35, 0.35), zy + rng.uniform(-0.35, 0.35)]
        else:
            tgt["pose_map"][:2] = [rng.uniform(bx0 + 0.3, bx1 - 0.1), rng.uniform(by0 + 0.05, by1 - 0.05)]
        ok, why = oracle_safe(g, tgt["id"], cfg)
        rec = (g, tgt["id"], ok, why)
        if ok and len(safe) < n_safe:
            safe.append(rec)
        elif not ok and len(unsafe_geo) < 18:
            unsafe_geo.append(rec)
    special = []
    for k in range(n_unsafe - len(unsafe_geo)):
        g = copy.deepcopy(rng.choice(safe)[0])
        tgt = rng.choice([n for n in g["nodes"] if n["id"] in {m["id"] for m in movable}])
        kind = ("occluded", "unverified", "not_in_graph")[k % 3]
        if kind == "occluded":
            tgt["state"] = "occluded"
            special.append((g, tgt["id"], False, "target occluded", True))
        elif kind == "unverified":
            special.append((g, tgt["id"], False, "S5 could not verify the target", False))
        else:
            special.append((g, "ghost_object_99", False, "target not in graph", True))
    k = 0
    for g, tid, ok, why, *ver in [(*s, True) for s in safe] + [(*u, True) for u in unsafe_geo] + special:
        k += 1
        verified = ver[0] if ver else True
        goal = build_action_goal({"target_id": tid, "verification_status": verified}, g, cfg)
        outcome = ("safe_accepted" if ok and goal["validated"] else "false_rejection" if ok else
                   "false_acceptance" if goal["validated"] else "unsafe_rejected")
        trials.append({"trial_id": f"A{k:02d}", "kind": "safe" if ok else "unsafe", "target_id": tid, "scenario": why,
                       "gt_safe": int(ok), "validated": int(goal["validated"]), "reason_code": goal["reason_code"], "outcome": outcome,
                       "target_xy": next(([round(v, 3) for v in n["pose_map"][:2]] for n in g["nodes"] if n["id"] == tid), "")})
    return trials


def action_summary(trials) -> list[dict]:
    S = [t for t in trials if t["gt_safe"]]
    U = [t for t in trials if not t["gt_safe"]]
    return [{"metric": "unsafe_rejection_rate", "value": rate(sum(not t["validated"] for t in U), len(U))["text"]},
            {"metric": "safe_acceptance_rate", "value": rate(sum(t["validated"] for t in S), len(S))["text"]},
            {"metric": "false_rejection_rate", "value": rate(sum(not t["validated"] for t in S), len(S))["text"]},
            {"metric": "false_acceptance_rate", "value": rate(sum(t["validated"] for t in U), len(U))["text"]}] + [
        {"metric": f"unsafe kind: {k}", "value": rate(sum(not t["validated"] for t in U if t["scenario"] == k),
                                                       sum(t["scenario"] == k for t in U))["text"]}
        for k in sorted({t["scenario"] for t in U})]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    s = sub.add_parser("sheet")
    s.add_argument("--run", required=True)
    s.add_argument("--scenario", default="")
    sc = sub.add_parser("score")
    sc.add_argument("--runs", nargs="+", required=True)
    sc.add_argument("--gt", default=str(GT / "tracking_ground_truth.csv"))
    sc.add_argument("--frames-root", help="frames of the runs (adds the appearance cue)")
    ac = sub.add_parser("actions")
    ac.add_argument("--graph", default="outputs/scene_graph/frame_000_scene_graph.json")
    ac.add_argument("--config", default="configs/s7_integration.yaml")
    ac.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = results_dir("s6")
    if a.cmd == "plan":
        print("->", write_csv(out / "tracking_sequences_manifest.csv", plan()))
    elif a.cmd == "sheet":
        rows = sheet(a.run, a.scenario)
        p = GT / f"tracking_sheet_{Path(a.run).name}.csv"
        write_csv(p, rows, SHEET_COLS)
        print(f"{len(rows)} detections -> {p}  (fill gt_object_id; add occluded=1 rows; then append to {GT / 'tracking_ground_truth.csv'})")
    elif a.cmd == "score":
        res = score(read_csv(a.gt), a.runs, a.frames_root)
        write_csv(out / "tracking_metrics.csv", res["per_sequence"])
        write_csv(out / "baseline_vs_multicue_tracking.csv", res["comparison"])
        write_csv(out / "occlusion_recovery_by_length.csv", res["by_length"])
        for run in a.runs:
            plot_tracks(run, out)
        for r in res["comparison"]:
            print(r)
    elif a.cmd == "actions":
        import yaml
        cfg = yaml.safe_load(Path(a.config).read_text())["action"]
        graph = json.loads(Path(a.graph).read_text())
        trials = action_trials(graph, cfg, seed=a.seed)
        write_csv(out / "action_safety_60_trials.csv", trials, COLUMNS["action_trials"] + ["target_xy"])
        summ = action_summary(trials)
        write_csv(out / "action_safety_summary.csv", summ)
        for r in summ:
            print(r)


if __name__ == "__main__":
    main()

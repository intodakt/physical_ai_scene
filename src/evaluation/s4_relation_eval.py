"""S4 (Jaloliddin) — relation accuracy, NEAR threshold sweep, temporal events, hysteresis (professor's guide §7).

Inputs are the outputs of a pipeline run (``main_pipeline.py --out RUN``): RUN/scene_graph/<frame>_scene_graph.json,
RUN/objects/<frame>_objects.json and RUN/tracking/event_log.jsonl. Several bags = several RUN folders.

    # 1. annotation sheet for >= 50 keyframes: every object pair x predicate, the system's answer filled in
    #    ("pred"), people fill "gt" (1 = true, 0 = false). Negatives are included by construction.
    python -m src.evaluation.s4_relation_eval sheet --runs runs/B01 runs/B02 ... --every 10
    # 2. relation P / R / F1 per predicate on the filled sheet
    python -m src.evaluation.s4_relation_eval score
    # 3. NEAR threshold sweep on the dev split, frozen choice written to configs/s4_frozen.yaml
    python -m src.evaluation.s4_relation_eval sweep --runs runs/B01 ...
    # 4. temporal events (MOVED / PICKED_UP / REAPPEARED ...) vs eval/ground_truth/temporal_events_ground_truth.csv
    python -m src.evaluation.s4_relation_eval events --runs runs/E01 runs/E02 ...
    # 5. relation flips with / without hysteresis (enter < 0.30 m, leave > 0.35 m) + graph snapshots
    python -m src.evaluation.s4_relation_eval flips --runs runs/E01 ...

Outputs (eval/results/s4/): relation_ground_truth.csv (sheet), relation_accuracy_by_type.csv, near_threshold_sweep.csv,
temporal_events.csv, relation_flip_comparison.csv, graph_snapshot_*.png, temporal_graph_<run>.json.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import yaml

from ..scene_graph.engine import SceneGraphEngine
from ..scene_graph.rules import NEAR_THRESHOLD_M
from .common import COLUMNS, DATASET, GT, as_bool, as_float, read_csv, results_dir, write_csv, write_json
from .stats import describe, prf, rate

PREDICATES = ["near", "on", "left_of", "under", "inside"]
SWEEP = [0.20, 0.25, 0.30, 0.35, 0.40]
EVENT_TOL_S = 1.0
FROZEN = Path("configs/s4_frozen.yaml")


def _graphs(run) -> list[tuple[str, dict]]:
    return [(p.name.replace("_scene_graph.json", ""), json.loads(p.read_text()))
            for p in sorted((Path(run) / "scene_graph").glob("*_scene_graph.json"))]


def _active(graph) -> set:
    return {(e["source"], e["predicate"], e["target"]) for e in graph["edges"] if e.get("end_time") is None}


def _bag(run) -> str:
    return Path(run).name


# ---------------------------------------------------------------- 1. annotation sheet
def sheet(runs, every: int = 10) -> list[dict]:
    rows = []
    for run in runs:
        for k, (frame, g) in enumerate(_graphs(run)):
            if k % every:
                continue
            nodes = [n for n in g["nodes"] if n.get("state") != "occluded"]
            act = _active(g)
            for i, a in enumerate(nodes):
                for b in nodes:
                    if a is b:
                        continue
                    for p in PREDICATES:
                        if p == "near" and a["id"] > b["id"]:      # symmetric: one row per pair
                            continue
                        if a.get("virtual") or (b.get("virtual") and p != "on"):   # the desk only supports things
                            continue
                        e = next((x for x in g["edges"] if (x["source"], x["predicate"], x["target"]) == (a["id"], p, b["id"])), None)
                        rows.append({"bag_id": _bag(run), "frame_id": frame, "time": g.get("timestamp"), "subject": a["id"],
                                     "predicate": p, "object": b["id"], "gt": "", "pred": int((a["id"], p, b["id"]) in act),
                                     "confidence": e.get("confidence") if e else "",
                                     "evidence_value": json.dumps(e.get("evidence")) if e else "", "annotator": "", "checked_by": ""})
    return rows


# ---------------------------------------------------------------- 2. accuracy
def score(rows) -> list[dict]:
    rows = [r for r in rows if str(r.get("gt", "")).strip() != ""]
    out = []
    for p in PREDICATES + ["all"]:
        sub = [r for r in rows if p == "all" or r["predicate"] == p]
        tp = sum(as_bool(r["gt"]) and as_bool(r["pred"]) for r in sub)
        fp = sum(not as_bool(r["gt"]) and as_bool(r["pred"]) for r in sub)
        fn = sum(as_bool(r["gt"]) and not as_bool(r["pred"]) for r in sub)
        pos = sum(as_bool(r["gt"]) for r in sub)
        out.append({"predicate": p, "annotated": len(sub), "gt_positive": pos, "min_positive_required": 30 if p != "all" else 250,
                    **prf(tp, fp, fn)})
    checked = [r for r in rows if r.get("checked_by")]
    out.append({"predicate": "second-annotator check", "annotated": len(checked),
                "gt_positive": rate(len(checked), len(rows))["text"], "min_positive_required": ">= 20 %"})
    return out


# ---------------------------------------------------------------- 3. NEAR sweep
def _dist(a, b):
    return math.dist(a["pose_map"], b["pose_map"])


def sweep(gt_rows, runs, thresholds=SWEEP, split_ids=None) -> list[dict]:
    """F1 of NEAR for each threshold on the annotated NEAR rows (dev bags only when split_ids is given)."""
    pose = {}
    for run in runs:
        for frame, g in _graphs(run):
            for n in g["nodes"]:
                pose[(_bag(run), frame, n["id"])] = n
    rows = [r for r in gt_rows if r["predicate"] == "near" and str(r.get("gt", "")).strip() != ""
            and (split_ids is None or r["bag_id"] in split_ids)]
    out = []
    for th in thresholds:
        tp = fp = fn = 0
        for r in rows:
            a, b = pose.get((r["bag_id"], r["frame_id"], r["subject"])), pose.get((r["bag_id"], r["frame_id"], r["object"]))
            if a is None or b is None:
                continue
            pred, gt = _dist(a, b) < th, as_bool(r["gt"])
            tp += pred and gt
            fp += pred and not gt
            fn += gt and not pred
        out.append({"d_near_m": th, **prf(tp, fp, fn)})
    return out


def freeze_near(table) -> dict:
    best = max(table, key=lambda r: (r["f1"] or 0, -abs(r["d_near_m"] - NEAR_THRESHOLD_M)))
    cfg = yaml.safe_load(FROZEN.read_text()) if FROZEN.exists() else {}
    cfg.update(near_threshold_m=best["d_near_m"], near_enter_m=best["d_near_m"], near_exit_m=round(best["d_near_m"] + 0.05, 3),
               chosen_on="dev split, highest NEAR F1", sweep=[{k: r[k] for k in ("d_near_m", "f1")} for r in table])
    FROZEN.write_text("# S4 frozen relation thresholds (python -m src.evaluation.s4_relation_eval sweep)\n" + yaml.safe_dump(cfg, sort_keys=False))
    return cfg


# ---------------------------------------------------------------- 4. temporal events
def predicted_events(run) -> list[dict]:
    p = Path(run) / "tracking" / "event_log.jsonl"
    if not p.exists():
        return []
    ev = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    t0 = min((e["timestamp"] for e in ev), default=0.0)
    return [{"sequence_id": _bag(run), "object": e["persistent_id"], "label": e.get("label") or e["persistent_id"].rsplit("_", 1)[0],
             "event": e["event"], "t": e["timestamp"] - t0} for e in ev if e["event"] != "APPEARED"]


def events_eval(gt_rows, runs, tol_s=EVENT_TOL_S) -> tuple[list, list]:
    """Greedy matching per sequence: same event type, same object label (or exact id), |t_pred − t_GT| <= tol."""
    pred = [p for run in runs for p in predicted_events(run)]
    seqs = {r["sequence_id"] for r in gt_rows} | {p["sequence_id"] for p in pred}
    rows, used = [], set()
    for s in sorted(seqs):
        G = [g for g in gt_rows if g["sequence_id"] == s]
        P = [p for p in pred if p["sequence_id"] == s]
        for g in G:
            lab = g["object_id"].rsplit("_", 1)[0]
            cands = [(abs(p["t"] - as_float(g["t_gt"], 0)), i) for i, p in enumerate(P)
                     if (s, i) not in used and p["event"] == g["event"] and (p["object"] == g["object_id"] or p["label"] == lab)
                     and abs(p["t"] - as_float(g["t_gt"], 0)) <= tol_s]
            if cands:
                dt, i = min(cands)
                used.add((s, i))
                rows.append({"sequence_id": s, "object_id": g["object_id"], "event": g["event"], "t_gt": g["t_gt"],
                             "t_pred": round(P[i]["t"], 3), "time_error_s": round(dt, 3), "result": "detected"})
            else:
                rows.append({"sequence_id": s, "object_id": g["object_id"], "event": g["event"], "t_gt": g["t_gt"],
                             "t_pred": "", "time_error_s": "", "result": "missed"})
        for i, p in enumerate(P):
            if (s, i) not in used:
                rows.append({"sequence_id": s, "object_id": p["object"], "event": p["event"], "t_gt": "", "t_pred": round(p["t"], 3),
                             "time_error_s": "", "result": "false_event"})
    n_gt = sum(r["result"] != "false_event" for r in rows)
    det = sum(r["result"] == "detected" for r in rows)
    n_pred = det + sum(r["result"] == "false_event" for r in rows)
    summary = [{"metric": "event_detection_rate", **_r(rate(det, n_gt))},
               {"metric": "false_event_rate", **_r(rate(n_pred - det, n_pred))},
               {"metric": "time_error_s", **describe([r["time_error_s"] for r in rows if r["result"] == "detected"])}]
    for ev in sorted({r["event"] for r in rows}):
        sub = [r for r in rows if r["event"] == ev and r["result"] != "false_event"]
        summary.append({"metric": f"detection_rate_{ev}", **_r(rate(sum(r["result"] == "detected" for r in sub), len(sub)))})
    return rows, summary


def _r(d):
    return {"value": d["value"], "text": d["text"]}


# ---------------------------------------------------------------- 5. flips with / without hysteresis
class CountingEngine(SceneGraphEngine):
    """SceneGraphEngine that counts every ON/OFF switch of every edge."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.switches = defaultdict(int)
        self._n = 0

    def _update_edges(self, visible, ts):
        before = {k for k, r in self._edges.items() if r["end_time"] is None}
        super()._update_edges(visible, ts)
        after = {k for k, r in self._edges.items() if r["end_time"] is None}
        self._n += 1
        if self._n > 1:                      # the first frame only creates edges; it is not a flip
            for k in before ^ after:
                self.switches[k] += 1


def flip_comparison(runs, enter=None, exit_=None) -> list[dict]:
    cfg = yaml.safe_load(FROZEN.read_text()) if FROZEN.exists() else {}
    enter = enter or cfg.get("near_enter_m", NEAR_THRESHOLD_M)
    exit_ = exit_ or cfg.get("near_exit_m", round(enter + 0.05, 3))
    rows = []
    for run in runs:
        for name, (e_in, e_out) in (("no_hysteresis", (enter, enter)), ("hysteresis", (enter, exit_))):
            eng = CountingEngine(near_enter_m=e_in, near_exit_m=e_out, session_id=_bag(run))
            frames = sorted((Path(run) / "objects").glob("*_objects.json"))
            for p in frames:
                eng.update(json.loads(p.read_text()))
            n = {pred: sum(v for k, v in eng.switches.items() if k[1] == pred) for pred in PREDICATES}
            rows.append({"run": _bag(run), "mode": name, "near_enter_m": e_in, "near_exit_m": e_out, "frames": len(frames),
                         **{f"switches_{p}": n[p] for p in PREDICATES}, "switches_total": sum(n.values())})
            if name == "hysteresis":
                eng.save(results_dir("s4") / f"temporal_graph_{_bag(run)}.json")
    return rows


def snapshots(run, out: Path) -> list:
    """Top-down graph at the first and the last frame (before / after movement)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    gs = _graphs(run)
    if not gs:
        return []
    paths = []
    for tag, (frame, g) in (("before", gs[0]), ("after", gs[-1])):
        fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=150)
        pos = {n["id"]: n["pose_map"] for n in g["nodes"] if not n.get("virtual")}
        for e in g["edges"]:
            if e.get("end_time") is None and e["source"] in pos and e["target"] in pos:
                a, b = pos[e["source"]], pos[e["target"]]
                ax.plot([a[1], b[1]], [a[0], b[0]], color="#9aa0a6", lw=1, zorder=1)
                ax.text((a[1] + b[1]) / 2, (a[0] + b[0]) / 2, e["predicate"], fontsize=6, color="#555", ha="center")
        for nid, p in pos.items():
            ax.scatter(p[1], p[0], s=60, color="#14a085", zorder=2)
            ax.text(p[1], p[0] + 0.015, nid, fontsize=7, ha="center")
        ax.set_xlabel("y (m)")
        ax.set_ylabel("x (m)")
        ax.invert_xaxis()
        ax.set_title(f"{_bag(run)} — {tag} ({frame}, t={g.get('timestamp')})", fontsize=9)
        ax.set_aspect("equal", adjustable="datalim")
        fig.tight_layout()
        p = out / f"graph_snapshot_{_bag(run)}_{tag}.png"
        fig.savefig(p)
        plt.close(fig)
        paths.append(p)
    return paths


def _dev_ids():
    p = DATASET / "splits.json"
    return set(json.loads(p.read_text())["dev"]) if p.exists() else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("sheet", "score", "sweep", "events", "flips"):
        s = sub.add_parser(name)
        s.add_argument("--runs", nargs="*", default=[])
        s.add_argument("--gt", default=str(GT / "relation_ground_truth.csv"))
        if name == "sheet":
            s.add_argument("--every", type=int, default=10, help="keyframe step (avoid near-identical frames)")
        if name == "sweep":
            s.add_argument("--all-bags", action="store_true", help="ignore the dev/test split (not for final numbers)")
        if name == "events":
            s.add_argument("--events-gt", default=str(GT / "temporal_events_ground_truth.csv"))
            s.add_argument("--tol", type=float, default=EVENT_TOL_S)
    a = ap.parse_args()
    out = results_dir("s4")
    if a.cmd == "sheet":
        rows = sheet(a.runs, a.every)
        p = GT / "relation_ground_truth.csv"
        if p.exists() and read_csv(p):
            p = GT / "relation_ground_truth_NEW.csv"     # never overwrite annotations
        write_csv(p, rows, COLUMNS["relation_ground_truth"])
        print(f"{len(rows)} candidate relations in {len({(r['bag_id'], r['frame_id']) for r in rows})} keyframes -> {p}")
    elif a.cmd == "score":
        res = score(read_csv(a.gt))
        write_csv(out / "relation_accuracy_by_type.csv", res)
        write_csv(out / "relation_ground_truth.csv", read_csv(a.gt), COLUMNS["relation_ground_truth"])
        for r in res:
            print(r)
    elif a.cmd == "sweep":
        table = sweep(read_csv(a.gt), a.runs, split_ids=None if a.all_bags else _dev_ids())
        write_csv(out / "near_threshold_sweep.csv", table)
        print(table)
        print("frozen:", freeze_near(table))
    elif a.cmd == "events":
        rows, summary = events_eval(read_csv(a.events_gt), a.runs, a.tol)
        write_csv(out / "temporal_events.csv", rows)
        write_csv(out / "temporal_events_summary.csv", summary)
        for s in summary:
            print(s)
    elif a.cmd == "flips":
        rows = flip_comparison(a.runs)
        write_csv(out / "relation_flip_comparison.csv", rows)
        for run in a.runs:
            snapshots(run, out)
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()

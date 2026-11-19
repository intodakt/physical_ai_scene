"""S6 tracking evaluation: Week-5 baseline vs MultiTermTracker (roadmap §11.6 required checks).

    python scripts/s6_tracking_eval.py          # -> docs/s6/tracking_eval/metrics.json + README.md

Scenarios are object lists with known ground-truth identities (synthetic desk, map frame, S2-style
noise of a few millimetres), one per required check:

    static       5 objects, nothing moves (noise only)                      -> ID stability
    relocation   the mug is picked up, hidden 8 frames, put down 30 cm away  -> re-identification (S3 bag)
    occlusion    a hand hides the book for 6 frames, same place              -> occlusion memory (S5 bag)
    slide        the mug slides 1.5 cm per frame for 12 frames               -> MOVED event
    crossing     two mugs pass each other 3 cm apart at 8 cm per frame       -> ID switches on same labels

Metrics: ID switches (a ground-truth object changes its predicted ID), re-identification success
after a gap, and event delay (frames from the true event to the reported one). The real S1 static
bag (3 frames, 8 objects) is added as a sanity check of ID stability on real S2 output.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.integration.s6_placeholder import CentroidTracker  # noqa: E402
from src.tracking import MultiTermTracker  # noqa: E402

OUT = ROOT / "docs" / "s6" / "tracking_eval"
SEEDS = range(10)
BASE = {"laptop": (0.72, 0.17, [0.35, 0.02, 0.25]), "mug": (0.56, -0.10, [0.08, 0.10, 0.08]),
        "book": (0.70, -0.26, [0.22, 0.035, 0.15]), "multimeter": (0.47, 0.10, [0.15, 0.045, 0.08]),
        "glass": (0.62, 0.36, [0.07, 0.12, 0.07])}


def obj(label, x, y, dims, rng, noise=0.004):
    c = [x + rng.normal(0, noise), y + rng.normal(0, noise), dims[1] / 2 + rng.normal(0, noise / 2)]
    return {"semantic_label": label, "label_candidates": [label], "centroid": [0, 0, 1], "fused_confidence": 0.8,
            "box_map": {"center": c, "dimensions": list(dims), "yaw": 0.0}}


def scenario(name, rng):
    """List of frames; each frame = list of (gt_id, object dict). Also returns true events."""
    frames, events = [], []
    for k in range(30):
        f = []
        for lab, (x, y, d) in BASE.items():
            gid = lab
            if name == "relocation" and lab == "mug":
                if 10 <= k < 18:
                    continue                      # in the hand, out of view
                if k >= 18:
                    x, y = x + 0.30, y            # put down 30 cm away
            if name == "occlusion" and lab == "book" and 10 <= k < 16:
                continue
            if name == "slide" and lab == "mug":
                x = x + 0.015 * min(max(k - 8, 0), 12)
            f.append((gid, obj(lab, x, y, d, rng)))
        if name == "crossing":
            f = [p for p in f if p[0] != "mug"]
            t = min(max(k - 10, 0), 10) / 10      # 8 cm per frame between frames 10 and 20
            f.append(("mug_A", obj("mug", 0.40 + 0.80 * t, -0.115, BASE["mug"][2], rng)))
            f.append(("mug_B", obj("mug", 1.20 - 0.80 * t, -0.085, BASE["mug"][2], rng)))
        frames.append(f)
    if name == "relocation":
        events = [("OCCLUDED", "mug", 10), ("REAPPEARED", "mug", 18), ("MOVED", "mug", 18)]
    elif name == "occlusion":
        events = [("OCCLUDED", "book", 10), ("REAPPEARED", "book", 16)]
    elif name == "slide":
        events = [("MOVED", "mug", 20)]
    return frames, events


def run(tracker, frames):
    pred = []                                       # per frame: {gt_id: persistent_id}
    seen_events = []
    for k, f in enumerate(frames):
        objs = [copy.deepcopy(o) for _, o in f]
        tracker.update(objs) if isinstance(tracker, CentroidTracker) else tracker.update(objs, float(k))
        pred.append({gid: o["persistent_id"] for (gid, _), o in zip(f, objs)})
        for e in getattr(tracker, "events", []):
            seen_events.append((e["event"], e["persistent_id"], k))
    return pred, seen_events


def score(pred, true_events, seen_events, frames):
    last, switches = {}, 0
    for p in pred:
        for gid, pid in p.items():
            if gid in last and last[gid] != pid:
                switches += 1
            last[gid] = pid
    # re-identification: an object that was missing comes back with the ID it had before the gap
    reid_total = reid_ok = 0
    for gid in {g for f in frames for g, _ in f}:
        present = [gid in p for p in pred]
        for k in range(1, len(pred)):
            if present[k] and not present[k - 1] and any(present[:k]):
                before = next(pred[j][gid] for j in range(k - 1, -1, -1) if present[j])
                reid_total += 1
                reid_ok += pred[k][gid] == before
    delays, missed = [], 0
    for kind, gid, k0 in true_events:
        pid = next((p[gid] for p in pred[:k0 + 1][::-1] if gid in p), None)
        hits = [k for e, p, k in seen_events if e == kind and k >= k0 and (p == pid or (kind != "OCCLUDED" and p == pred[k].get(gid)))]
        if hits:
            delays.append(hits[0] - k0)
        else:
            missed += 1
    return {"id_switches": switches, "reid_total": reid_total, "reid_ok": reid_ok,
            "events_total": len(true_events), "events_found": len(true_events) - missed,
            "event_delay_frames": round(float(np.mean(delays)), 2) if delays else None}


def occlusion_sweep(hidden=(2, 5, 10, 11, 15, 20), relocate=(0.0, 0.30)):
    """W10: re-identification after an occlusion of h frames; the book comes back in place or 30 cm away."""
    out = {}
    for dx in relocate:
        for h in hidden:
            ok = {"baseline": 0, "multi_term": 0}
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                frames = []
                for k in range(10 + h + 5):
                    f = []
                    for lab, (x, y, d) in BASE.items():
                        if lab == "book" and 10 <= k < 10 + h:
                            continue
                        if lab == "book" and k >= 10 + h:
                            x = x + dx
                        f.append((lab, obj(lab, x, y, d, rng)))
                    frames.append(f)
                for key, make in (("baseline", lambda: CentroidTracker()), ("multi_term", lambda: MultiTermTracker())):
                    pred, _ = run(make(), frames)
                    ok[key] += pred[10 + h]["book"] == pred[9]["book"]
            out[f"{'moved' if dx else 'in_place'}_{h}"] = {k: round(v / len(SEEDS), 2) for k, v in ok.items()}
    return out


def real_bag():
    files = sorted((ROOT / "data" / "real").glob("s2_frame_*_objects.json"))
    out = {}
    for name, make in (("baseline", lambda: CentroidTracker()), ("multi_term", lambda: MultiTermTracker())):
        t, ids = make(), []
        for f in files:
            objs = json.loads(f.read_text())["objects"]
            t.update(objs) if name == "baseline" else t.update(objs, None)
            ids.append(sorted(o["persistent_id"] for o in objs))
        out[name] = {"frames": len(files), "objects_per_frame": [len(i) for i in ids],
                     "same_ids_on_every_frame": all(i == ids[0] for i in ids), "n_ids": len({x for i in ids for x in i})}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = ["static", "relocation", "occlusion", "slide", "crossing"]
    res = {}
    for name in names:
        agg = {"baseline": [], "multi_term": []}
        for seed in SEEDS:
            frames, ev = scenario(name, np.random.default_rng(seed))
            for key, make in (("baseline", lambda: CentroidTracker()), ("multi_term", lambda: MultiTermTracker())):
                pred, seen = run(make(), frames)
                agg[key].append(score(pred, ev, seen, frames))
        res[name] = {k: {m: (round(float(np.mean([r[m] for r in v if r[m] is not None])), 2)
                             if any(r[m] is not None for r in v) else None) for m in v[0]} for k, v in agg.items()}
    sweep = occlusion_sweep()
    metrics = {"seeds": len(SEEDS), "frames_per_scenario": 30, "scenarios": res, "real_static_bag": real_bag(),
               "reid_after_occlusion": sweep}
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    rows = ["| Scenario | Tracker | ID switches | re-ID ok / gaps | events found | event delay (frames) |", "|---|---|---|---|---|---|"]
    for name in names:
        for k in ("baseline", "multi_term"):
            r = res[name][k]
            rows.append(f"| {name} | {k} | {r['id_switches']} | {r['reid_ok']} / {r['reid_total']} | "
                        f"{r['events_found']} / {r['events_total']} | {r['event_delay_frames'] if r['event_delay_frames'] is not None else '—'} |")
    rb = metrics["real_static_bag"]
    text = "\n".join([
        "# S6 — tracking evaluation (Week-5 baseline vs MultiTermTracker)", "",
        "Reproduce: `python scripts/s6_tracking_eval.py`. Means over 10 noise seeds, 30 frames per scenario.",
        "The baseline emits no events, so its event columns are 0 by construction.", "", *rows, "",
        f"Real S1 static bag ({rb['multi_term']['frames']} frames of real S2 output): baseline same IDs on every frame = "
        f"{rb['baseline']['same_ids_on_every_frame']} ({rb['baseline']['n_ids']} IDs); multi-term = "
        f"{rb['multi_term']['same_ids_on_every_frame']} ({rb['multi_term']['n_ids']} IDs).", "",
        "## Re-identification after occlusion (W10)", "",
        "Share of runs where the book gets its old ID back after being hidden h frames (memory TTL = 10 frames).", "",
        "| Hidden frames | in place: baseline | in place: multi-term | moved 30 cm: baseline | moved 30 cm: multi-term |",
        "|---|---|---|---|---|",
        *[f"| {h} | {sweep[f'in_place_{h}']['baseline']} | {sweep[f'in_place_{h}']['multi_term']} | "
          f"{sweep[f'moved_{h}']['baseline']} | {sweep[f'moved_{h}']['multi_term']} |" for h in (2, 5, 10, 11, 15, 20)], "",
        "Limits: the scenarios are synthetic object lists (no rendering, no S3/S2 errors); real relocation and",
        "occlusion bags still have to be labelled with ground-truth identities.", ""])
    (OUT / "README.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()

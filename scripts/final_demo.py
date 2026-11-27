"""Final integrated demonstration (professor's W12–W16 guide §13) — one command, 12 steps, one run log.

    python3 scripts/final_demo.py --bag <bags>/H_final_demo --unseen-description "electrical measuring device"
    python3 scripts/final_demo.py                      # mock demo sequence (rehearsal without the camera)

Record the scenario once with the ZED Mini (ros2 bag record), or replay a recorded bag, then run this script.
It runs the full pipeline and prints, step by step, the evidence the professor asked to see:

     1  static scene with known objects                       S1
     2  masks, 3D boxes, persistent IDs, current graph        S3 · S2 · S6 · S4
    3–4 held-out unseen object, found by a description       S3
     5  the mug moves: same ID                                S6
     6  the mug is occluded: recovered with the same ID       S6
     7  graph history: mug ON desk ended t1, new place t2     S4
     8  "What is closest to the laptop?" with metric proof    S5
     9  "Where was the mug before it moved?" with history     S5 · S4
    10  a negative / multi-hop question                       S5
    11  action: a safe goal accepted, a blocked goal rejected S6
    12  run log: latency, confidence, warnings, success       S7

Output: <out>/final_demo_log.md (+ .json). Steps whose event did not happen in the recording are reported as
"not seen in this recording" — nothing is assumed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _events(pipe, pid=None, kinds=None):
    return [e for e in pipe.tracker.event_log if (pid is None or e["persistent_id"] == pid) and (kinds is None or e["event"] in kinds)]


def _label(pid):
    return pid.rsplit("_", 1)[0].replace("_", " ")


def run_demo(frames=None, bag=None, out="outputs/final_demo", target="mug", reference="laptop", unseen=None, blocked=None,
             negative=None, parser=None, s3=None, every=1, limit=None, camera_tf=None):
    from main_pipeline import run

    pipe, summary = run(frames, bag, f"What is closest to the {reference}?", out, s3, parser, every, limit, quiet=True, camera_tf=camera_tf)
    steps = []
    add = lambda n, title, owner, ok, lines: steps.append({"step": n, "title": title, "owner": owner, "shown": ok, "evidence": lines})
    graph = pipe.graph
    first, last = pipe.frames[0], pipe.frames[-1]

    # 1–2 scene, masks, 3D, IDs, graph
    add("1", "Static scene with known objects", "S1", True,
        [f"{len(pipe.frames)} frames; first frame {first['frame']}: {first['n_objects']} objects, {first['n_rejected']} rejected"])
    ids = sorted(set(first["ids"].values()))
    active = [e for e in graph["edges"] if e.get("end_time") is None]
    add("2", "Masks, 3D boxes, persistent IDs, current graph", "S3 · S2 · S6 · S4", bool(ids),
        [f"persistent IDs: {', '.join(ids)}", f"graph: {len(graph['nodes'])} nodes, {len(active)} active relations",
         "  " + "; ".join(f"{e['source']} {e['predicate']} {e['target']}" for e in active[:8])])

    # 3–4 unseen object
    if unseen:
        r = pipe.ask(f"Where is the {unseen}?")["reasoning_result"]
        add("3–4", f"Unseen object found by the description “{unseen}”", "S3", r["verification_status"],
            [r["final_answer"], f"proof: {r['computed_facts']}"])
    else:
        add("3–4", "Unseen object by description", "S3", False, ["not requested (use --unseen-description)"])

    # 5–6 movement and occlusion of the target
    tid = next((pid for pid in sorted({p for f in pipe.frames for p in f["ids"].values()}) if _label(pid) == target), None)
    tid_all = sorted({p for f in pipe.frames for p in f["ids"].values() if _label(p) == target})
    moved = _events(pipe, tid, {"MOVED"}) if tid else []
    add("5", f"The {target} moves: same object ID", "S6", bool(moved) and len(tid_all) == 1,
        [f"IDs used for '{target}' over the run: {tid_all or 'none'}"] +
        [f"t={e['timestamp']}: MOVED {e.get('distance_m')} m" for e in moved] or ["no MOVED event in this recording"])
    occl = _events(pipe, tid, {"OCCLUDED", "REAPPEARED"}) if tid else []
    reap = [e for e in occl if e["event"] == "REAPPEARED"]
    add("6", f"The {target} is occluded and recovered with the same ID", "S6", bool(reap) and len(tid_all) == 1,
        [f"t={e['timestamp']}: {e['event']}" + (f" after {e.get('after_frames')} frames" if e["event"] == "REAPPEARED" else "")
         for e in occl] or ["no occlusion of the target in this recording"])

    # 7 graph history
    ended = [e for e in graph["edges"] if tid and e["source"] == tid and e.get("end_time") is not None]
    t0 = first["timestamp"]
    started = [e for e in graph["edges"] if tid and e["source"] == tid and e.get("end_time") is None and e["start_time"] != t0]
    add("7", "Graph history: old relation ended, new one started", "S4", bool(ended),
        [f"{e['source']} {e['predicate']} {e['target']}: {e['start_time']} → {e['end_time']}" for e in ended] +
        [f"{e['source']} {e['predicate']} {e['target']}: since {e['start_time']}" for e in started[:3]] or ["no relation of the target changed"])

    # 8–10 questions
    qa = []
    for n, q in (("8", f"What is closest to the {reference}?"), ("9", f"Where was the {target} before it moved?"),
                 ("10", negative or f"Find an object that is not near the {reference}")):
        res = pipe.ask(q)
        rr = res["reasoning_result"]
        qa.append(res)
        add(n, q, "S5" if n != "9" else "S5 · S4", rr["verification_status"],
            [rr["final_answer"], f"proof: {rr['computed_facts']}"] + [f"warning: {w}" for w in rr.get("warnings", [])])

    # 11 action: safe goal and blocked goal
    safe = pipe.ask(f"Go to the {target}")
    g = safe["action_goal"]
    lines = [f"Go to the {target}: validated={g['validated']} ({g['reason_code']}); simulation success={safe['simulation']['success']}"]
    ok11 = g["validated"]
    if blocked:
        b = pipe.ask(f"Go to the {blocked}")["action_goal"]
        lines.append(f"Go to the {blocked}: validated={b['validated']} ({b['reason_code']}: {b['reason']})")
        ok11 = ok11 and not b["validated"]
    add("11", "Action: safe goal accepted, blocked goal rejected", "S6", ok11, lines)

    # 12 run log
    s = pipe.summary()
    st = s["latency_stats_ms"].get("total", {})
    warns = sorted({w for r in qa for w in r["reasoning_result"].get("warnings", [])})
    add("12", "Run log: latency, confidence, warnings, success", "S7", not s["contract_errors"],
        [f"per frame: p50 {st.get('p50')} ms, p95 {st.get('p95')} ms, max {st.get('max')} ms ({s['fps']} FPS mean)",
         f"contract errors: {len(s['contract_errors'])}", f"answer confidences: {[r['reasoning_result']['confidence'] for r in qa]}",
         f"warnings: {warns or 'none'}"])

    out = Path(out)
    L = ["# G1 final demonstration — run log", "", f"Source: {bag or frames or 'mock demo sequence'} · {len(pipe.frames)} frames · "
         f"S3 {pipe.s3_mode} · S5 parser {pipe.parser}", "", "| Step | What | Owner | Shown |", "|---|---|---|---|"]
    L += [f"| {x['step']} | {x['title']} | {x['owner']} | {'yes' if x['shown'] else 'no'} |" for x in steps]
    for x in steps:
        L += ["", f"## Step {x['step']} — {x['title']} ({x['owner']})", ""] + [f"- {l}" for l in x["evidence"]]
    (out / "final_demo_log.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out / "final_demo_log.json").write_text(json.dumps(steps, indent=2), encoding="utf-8")
    return steps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--frames")
    src.add_argument("--bag")
    ap.add_argument("--out", default="outputs/final_demo")
    ap.add_argument("--target", default="mug", help="the object that is moved and occluded")
    ap.add_argument("--reference", default="laptop")
    ap.add_argument("--unseen-description", help='e.g. "electrical measuring device"')
    ap.add_argument("--blocked", help="an object behind the laptop, for the rejected goal (e.g. glass)")
    ap.add_argument("--negative", help="the negative / multi-hop question")
    ap.add_argument("--parser", choices=["auto", "ollama", "rules"])
    ap.add_argument("--s3", choices=["replay", "live"])
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--camera-tf")
    a = ap.parse_args()
    steps = run_demo(a.frames, a.bag, a.out, a.target, a.reference, a.unseen_description, a.blocked, a.negative,
                     a.parser, a.s3, a.every, a.limit, a.camera_tf)
    for x in steps:
        print(f"[{'x' if x['shown'] else ' '}] {x['step']:>4}  {x['title']}  ({x['owner']})")
        for l in x["evidence"]:
            print(f"          {l}")
    print(f"-> {a.out}/final_demo_log.md")


if __name__ == "__main__":
    main()

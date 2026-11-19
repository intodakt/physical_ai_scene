"""S7 (Mirzokhidbek) — 30 end-to-end tasks, failure-stage accounting and runtime (professor's guide §10).

A task succeeds only if every stage is right: perception -> 3D localization -> tracking -> graph -> grounding /
verification -> ActionGoal. The first wrong stage is recorded, so the table shows WHERE the system fails.

    python -m src.evaluation.s7_e2e_eval tasks            # 30-task template (10 easy / 10 medium / 10 hard)
    python -m src.evaluation.s7_e2e_eval run --frames-root /data/frames --repeats 3
    python -m src.evaluation.s7_e2e_eval runtime --runs eval/results/s7/runs/*     # per-stage p50 / p95 / max, FPS

eval/tasks/end_to_end_tasks.csv (one row per task):
    task_id, difficulty, frames (folder under --frames-root, or a bag), question, expect_label ('' = must refuse),
    expect_safe (1 accept / 0 reject), gt_x/gt_y/gt_z (target centre in the table frame, optional),
    required_relation ("mug on desk", optional), notes

Stage checks, in pipeline order:
    S3  a detection with the expected label exists in the last frame
    S2  an object with that label exists and is within LOC_TOL_M of the GT centre (when given)
    S6  the target label kept one persistent ID over the run (no ID switch)
    S4  the required relation is an active edge in the final graph (when given)
    S5  the verified answer has the expected label (or refuses when expected)
    S6a the ActionGoal accept / reject decision matches expect_safe

Outputs (eval/results/s7/): end_to_end_30_tasks.csv, failure_stage_summary.csv, runtime_summary.csv, latency_log.csv,
consistency.csv (repeats), runs/<task>_r<k>/ (full pipeline outputs, dashboard-ready).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from .common import COLUMNS, TASKS, as_bool, as_float, read_csv, results_dir, write_csv
from .stats import describe, rate

LOC_TOL_M = 0.05
STAGE_ORDER = ["S3", "S2", "S6", "S4", "S5", "S6a"]
DIFFICULTY_PLAN = [("easy", 10, "known objects, static, simple nearest-object query"),
                   ("medium", 10, "object movement / occlusion + negative query"),
                   ("hard", 10, "unseen object + temporal / multi-hop query + blocked path")]


def task_template() -> list[dict]:
    rows, k = [], 0
    examples = {"easy": ("H01_language_easy_rep1", "What is closest to the laptop?"),
                "medium": ("E02_motion_medium_rep1", "Find a cup that is not near the laptop"),
                "hard": ("D02_unseen_hard_rep1", "Where was the mug before it moved?")}
    for diff, n, note in DIFFICULTY_PLAN:
        for i in range(n):
            k += 1
            bag, q = examples[diff]
            rows.append({"task_id": f"T{k:02d}", "difficulty": diff, "frames": bag if i == 0 else "", "question": q if i == 0 else "",
                         "expect_label": "", "expect_safe": "", "gt_x": "", "gt_y": "", "gt_z": "", "required_relation": "",
                         "notes": note})
    return rows


def _label(pid_or_label: str) -> str:
    return str(pid_or_label or "").rsplit("_", 1)[0].replace("_", " ")


def _same(a: str, b: str) -> bool:
    from ..open_vocab.aliases import canonical
    return canonical(_label(a)) == canonical(_label(b)) or _label(a) == _label(b)


def check_task(task: dict, pipe, result: dict) -> tuple[bool, str, str]:
    """(success, first_failure_stage, reason) from a finished pipeline run."""
    exp = (task.get("expect_label") or "").strip()
    rr, goal = result["reasoning_result"], result["action_goal"]
    last = pipe.frames[-1] if pipe.frames else None
    graph = pipe.graph
    if exp:
        obs = json.loads(Path(last["observation"]).read_text()) if last else {"detections": []}
        if not any(_same(d["labels"][0], exp) for d in obs.get("detections", [])):
            return False, "S3", f"'{exp}' not detected in the last frame"
        objs = json.loads((pipe.out / "objects" / f"{last['frame']}_objects.json").read_text())["objects"]
        cands = [o for o in objs if _same(o["semantic_label"], exp)]
        if not cands:
            return False, "S2", f"'{exp}' detected but no 3D object (rejected by S2)"
        if task.get("gt_x") not in (None, ""):
            gt = [as_float(task["gt_x"]), as_float(task["gt_y"]), as_float(task["gt_z"], 0.0)]
            best = min(math.dist((o.get("box_map") or {}).get("center") or o["centroid_map"], gt) for o in cands)
            if best > LOC_TOL_M:
                return False, "S2", f"'{exp}' localized {100 * best:.1f} cm from GT (> {100 * LOC_TOL_M:.0f} cm)"
        ids = {pid for f in pipe.frames for oid, pid in f["ids"].items() if _same(oid, exp)}
        n_inst = max(sum(_same(o["semantic_label"], exp) for o in objs), 1)
        if len(ids) > n_inst:
            return False, "S6", f"ID switch: '{exp}' had {len(ids)} persistent IDs for {n_inst} object(s): {sorted(ids)}"
    rel = (task.get("required_relation") or "").strip()
    if rel:
        a, pred, b = rel.split()[0], rel.split()[1], " ".join(rel.split()[2:])
        lab = {n["id"]: n["names"][0]["text"] for n in graph["nodes"]}
        if not any(e.get("end_time") is None and e["predicate"] == pred and _same(lab.get(e["source"], ""), a)
                   and _same(lab.get(e["target"], ""), b) for e in graph["edges"]):
            return False, "S4", f"relation '{rel}' not in the final graph"
    if exp:
        if not rr["verification_status"]:
            return False, "S5", f"refused: {rr['final_answer']}"
        if not _same(rr["target_id"], exp):
            return False, "S5", f"answered {rr['target_id']}, expected {exp}"
    elif rr["verification_status"]:
        return False, "S5", f"should refuse but answered {rr['target_id']}"
    if task.get("expect_safe") not in (None, "") and bool(goal["validated"]) != as_bool(task["expect_safe"]):
        return False, "S6a", f"ActionGoal validated={goal['validated']} ({goal['reason_code']}), expected {as_bool(task['expect_safe'])}"
    return True, "", ""


def run_tasks(tasks, frames_root, repeats=3, parser=None, s3=None, every=1, limit=None) -> tuple[list, list]:
    from main_pipeline import run as run_pipeline

    out = results_dir("s7")
    rows, cons = [], []
    for t in tasks:
        src = Path(frames_root) / t["frames"] if frames_root else Path(t["frames"])
        answers = []
        for k in range(1, repeats + 1):
            rid = f"{t['task_id']}_r{k}"
            kw = {"bag": str(src)} if (src / "metadata.yaml").exists() or src.suffix == ".db3" else {"frames": str(src)}
            try:
                pipe, summ = run_pipeline(**kw, query=t["question"], out=str(out / "runs" / rid), parser=parser, s3=s3,
                                          every=every, limit=limit, quiet=True)
                res = json.loads((out / "runs" / rid / "reasoning" / "last_query.json").read_text())
                ok, stage, why = check_task(t, pipe, res)
                st = summ.get("latency_stats_ms", {}).get("total", {})
                warns = res["reasoning_result"].get("warnings", []) + res["action_goal"].get("warnings", [])
                answers.append((res["reasoning_result"]["target_id"], res["action_goal"]["validated"]))
            except Exception as e:      # a crash is a failure of the stage that crashed; S1 if frames are missing
                ok, stage, why, st, warns = False, "S1" if "frame" in str(e).lower() or "bag" in str(e).lower() else "S7", f"{type(e).__name__}: {e}", {}, []
                answers.append(("CRASH", None))
            rows.append({"run_id": rid, "task_id": t["task_id"], "difficulty": t["difficulty"], "repeat": k, "success": int(ok),
                         "first_failure_stage": stage, "reason": why, "p50_ms": st.get("p50"), "p95_ms": st.get("p95"),
                         "fps": round(1e3 / st["p50"], 3) if st.get("p50") else None, "warnings": " | ".join(warns)})
            print(rid, "OK" if ok else f"FAIL at {stage}: {why}")
        cons.append({"task_id": t["task_id"], "repeats": repeats, "identical_answers": int(len(set(answers)) == 1),
                     "answers": json.dumps([list(map(str, a)) for a in answers])})
    return rows, cons


def failure_summary(rows) -> list[dict]:
    first = [r for r in rows if int(r["repeat"]) == 1]
    out = [{"group": "all", "tasks": len(first), "task_success_rate": rate(sum(int(r["success"]) for r in first), len(first))["text"]}]
    for d in ("easy", "medium", "hard"):
        sub = [r for r in first if r["difficulty"] == d]
        out.append({"group": d, "tasks": len(sub), "task_success_rate": rate(sum(int(r["success"]) for r in sub), len(sub))["text"]})
    fails = [r for r in first if not int(r["success"])]
    for s in STAGE_ORDER + ["S1", "S7"]:
        n = sum(r["first_failure_stage"] == s for r in fails)
        if n:
            out.append({"group": f"first failure at {s}", "tasks": n, "task_success_rate": rate(n, len(fails))["text"] + " of failures"})
    return out


def runtime_summary(run_dirs) -> tuple[list, list]:
    """Per-stage p50 / p95 / max and FPS from the runs' run_summary.json frames (+ S5 / S6 query timings)."""
    per = defaultdict(list)
    log = []
    for d in run_dirs:
        p = Path(d) / "run_summary.json"
        if not p.exists():
            continue
        s = json.loads(p.read_text())
        for f in s.get("frames", []):
            for k, v in f["timings_ms"].items():
                per[k].append(v)
            log.append({"run": Path(d).name, "frame": f["frame"], **f["timings_ms"]})
        q = (s.get("last_query") or {}).get("timings_ms", {})
        for k, v in q.items():
            per[k].append(v)
    order = ["s1_load", "s3_perception", "s3_detection", "s3_segmentation", "s2_fusion", "s6_tracking", "s4_graph",
             "s5_reasoning", "s6_action", "total"]
    rows = []
    for k in [o for o in order if o in per] + sorted(set(per) - set(order)):
        d = describe(per[k])
        rows.append({"stage": k, "n": d["n"], "p50_ms": d["median"], "p95_ms": d["p95"], "max_ms": d["max"], "mean_ms": d["mean"],
                     "fps_at_p50": round(1e3 / d["median"], 3) if k == "total" and d["median"] else ""})
    return rows, log


def plot_runtime(rows, out: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    st = [r for r in rows if r["stage"] not in ("total", "s3_detection", "s3_segmentation")]
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=150)
    y = np.arange(len(st))
    ax.barh(y, [r["p50_ms"] or 0 for r in st], color="#14a085", label="p50")
    ax.barh(y, [(r["p95_ms"] or 0) - (r["p50_ms"] or 0) for r in st], left=[r["p50_ms"] or 0 for r in st], color="#9fd8cf", label="p95")
    ax.set_yticks(y, [r["stage"] for r in st])
    ax.set_xlabel("ms per frame (S5 / S6 action: per query)")
    ax.set_title("End-to-end latency breakdown")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = out / "latency_breakdown.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def plot_failures(summary, out: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    st = [r for r in summary if r["group"].startswith("first failure")]
    if not st:
        return None
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=150)
    ax.bar([r["group"].split()[-1] for r in st], [r["tasks"] for r in st], color="#d18b0f")
    ax.set_ylabel("tasks")
    ax.set_title("First failing stage (end-to-end tasks)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = out / "failure_stage_distribution.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tasks")
    r = sub.add_parser("run")
    r.add_argument("--tasks", default=str(TASKS / "end_to_end_tasks.csv"))
    r.add_argument("--frames-root", default="")
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--parser", choices=["auto", "ollama", "rules"])
    r.add_argument("--s3", choices=["replay", "live"])
    r.add_argument("--every", type=int, default=1)
    r.add_argument("--limit", type=int)
    rt = sub.add_parser("runtime")
    rt.add_argument("--runs", nargs="+", required=True)
    a = ap.parse_args()
    out = results_dir("s7")
    if a.cmd == "tasks":
        p = TASKS / "end_to_end_tasks.csv"
        if p.exists() and len(read_csv(p)) > 1:
            p = TASKS / "end_to_end_tasks_TEMPLATE.csv"
        write_csv(p, task_template(), COLUMNS["e2e_tasks"])
        print("->", p)
    elif a.cmd == "run":
        tasks = [t for t in read_csv(a.tasks) if t.get("frames") and t.get("question")]
        rows, cons = run_tasks(tasks, a.frames_root, a.repeats, a.parser, a.s3, a.every, a.limit)
        write_csv(out / "end_to_end_30_tasks.csv", rows, COLUMNS["e2e_runs"])
        write_csv(out / "consistency.csv", cons)
        summ = failure_summary(rows)
        write_csv(out / "failure_stage_summary.csv", summ)
        plot_failures(summ, out)
        rt_rows, log = runtime_summary(sorted((out / "runs").iterdir()))
        write_csv(out / "runtime_summary.csv", rt_rows)
        write_csv(out / "latency_log.csv", log)
        plot_runtime(rt_rows, out)
        for s in summ:
            print(s)
    elif a.cmd == "runtime":
        rt_rows, log = runtime_summary(a.runs)
        write_csv(out / "runtime_summary.csv", rt_rows)
        write_csv(out / "latency_log.csv", log)
        plot_runtime(rt_rows, out)
        for x in rt_rows:
            print(x)


if __name__ == "__main__":
    main()

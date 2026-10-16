"""G1 master launch file (S7): runs the whole pipeline from one command.

    python main_pipeline.py                                   # mock desk sequence + default query
    python main_pipeline.py --frames data/frames/static_baseline --query "Where is the mug?"
    python main_pipeline.py --bag data/bags/<S1 bag> --every 10 --query "Find a cup that is not near the laptop"
    python main_pipeline.py --s3 live                         # run YOLO-World + SAM instead of replaying S3 output
    python main_pipeline.py --parser ollama                   # force the local LLM (default: auto)

Order: S1 frames -> S3 masks -> S2 3D objects -> S6 IDs -> S4 scene graph -> S5 verified answer
       -> S6 ActionGoal -> virtual twin. Outputs go to outputs/pipeline/ (see docs/s7/README.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.integration.pipeline import Pipeline, frame_dirs, frames_from_bag, load_config

DEMO_FRAMES = Path("data/demo/desk_sequence")


def run(frames=None, bag=None, query=None, out="outputs/pipeline", s3=None, parser=None, every=1, limit=None,
        config=None, quiet=False, camera_tf=None):
    cfg = load_config(config)
    T = json.loads(Path(camera_tf).read_text(encoding="utf-8"))["T_map_camera"] if camera_tf else None
    pipe = Pipeline(out, cfg, s3_mode=s3, parser=parser)
    if bag:
        dirs = frames_from_bag(bag, Path(out) / "frames", every=every, limit=limit)
    else:
        src = Path(frames) if frames else DEMO_FRAMES
        if not src.exists() and src == DEMO_FRAMES:
            from scripts.make_demo_sequence import generate

            generate(src)
        dirs = frame_dirs(src)[::every][:limit]
    log = (lambda *a: None) if quiet else print
    log(f"[S7] {len(dirs)} frames | S3={pipe.s3_mode} | S5 parser={pipe.parser} | out={out}")
    for d in dirs:
        r = pipe.process(d, T_map_camera=T)
        log(f"  {r['frame']}: {r['n_objects']} objects, {r['n_rejected']} rejected, "
            f"{r['timings_ms']['total']:.0f} ms  ids={sorted(set(r['ids'].values()))}")
    result = pipe.ask(query or cfg["default_query"])
    summary = pipe.summary()
    summary["last_query"] = result
    Path(out, "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    rr, goal = result["reasoning_result"], result["action_goal"]
    log(f"\n[S5] Q: {result['question']}\n     A: {rr['final_answer']}")
    for w in rr["warnings"]:
        log(f"     ! {w}")
    log(f"[S6] ActionGoal: target={goal['target_object_id']} pose={goal['target_pose']} "
        f"validated={goal['validated']} ({goal['reason']})")
    log(f"[S7] mean latency {summary['mean_latency_ms']:.0f} ms/frame ({summary['fps']:.2f} FPS), "
        f"contract errors: {len(summary['contract_errors'])}")
    for e in summary["contract_errors"]:
        log(f"     x {e}")
    return pipe, summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--frames", help="S1 frame folder or folder of frame_XXXX folders (default: mock sequence)")
    src.add_argument("--bag", help="S1 ROS 2 bag (ZED Mini topics)")
    ap.add_argument("--query", default=None, help="question for S5 (default from configs/s7_integration.yaml)")
    ap.add_argument("--out", default="outputs/pipeline")
    ap.add_argument("--s3", choices=["replay", "live"], default=None)
    ap.add_argument("--parser", choices=["auto", "ollama", "rules"], default=None)
    ap.add_argument("--every", type=int, default=1, help="keep every N-th frame")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--camera-tf", default=None,
                    help="JSON with T_map_camera (S1 calibration) for frames that carry none, e.g. bag exports")
    a = ap.parse_args()
    _, summary = run(a.frames, a.bag, a.query, a.out, a.s3, a.parser, a.every, a.limit, a.config,
                     camera_tf=a.camera_tf)
    sys.exit(1 if summary["contract_errors"] else 0)


if __name__ == "__main__":
    main()

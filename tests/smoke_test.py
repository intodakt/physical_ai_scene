"""One-click S7 smoke test: bag in -> ActionGoal out.

    python tests/smoke_test.py                       # builds a mock ZED Mini bag from the demo sequence
    python tests/smoke_test.py --bag data/bags/<S1 90 s bag> --s3 live --camera-tf <frame_meta.json>

Passes (exit 0) when every stage ran, all hand-overs honour the JSON contracts, tracking kept
its IDs, and S6 produced an ActionGoal for the question.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main_pipeline import run  # noqa: E402
from scripts.make_demo_sequence import generate, to_bag  # noqa: E402
from src.integration.pipeline import frame_dirs, frames_from_bag  # noqa: E402


def build_mock_bag(work: Path, n_frames: int) -> tuple[Path, Path, list[Path]]:
    """Mock frames -> ROS 2 bag (ZED Mini topics). Returns (bag, camera TF file, source frames)."""
    src = generate(work / "mock_frames", n_frames)
    bag = to_bag(src, work / "mock_bag")
    return bag, src[0] / "frame_meta.json", src


def smoke(bag=None, s3="replay", camera_tf=None, query="Go to the mug", out="outputs/smoke_test",
          n_frames=6, every=1, limit=None) -> dict:
    out = Path(out)
    shutil.rmtree(out, ignore_errors=True)
    t0 = time.perf_counter()
    checks = {}
    src_frames = None
    if bag is None:
        bag, camera_tf, src_frames = build_mock_bag(out / "work", n_frames)
    frames = frames_from_bag(bag, out / "frames", every=every, limit=limit)        # S1 bag -> frames
    checks["S1 bag gives synchronized frames"] = len(frames) > 0
    if src_frames is not None and s3 == "replay":   # mock only: S3's output for the same images
        for f, s in zip(frames, src_frames[::every]):
            shutil.copy(s / "observation.json", f)
            shutil.copytree(s / "masks", f / "masks", dirs_exist_ok=True)
    pipe, summary = run(frames=out / "frames", query=query, out=str(out / "pipeline"), s3=s3,
                        parser="rules" if src_frames is not None else None, camera_tf=camera_tf, quiet=True)
    goal = summary["last_query"]["action_goal"]
    checks["every frame produced 3D objects (S3 -> S2)"] = all(f["n_objects"] > 0 for f in summary["frames"])
    checks["scene graph has nodes and edges (S4)"] = bool(pipe.graph["nodes"]) and bool(pipe.graph["edges"])
    checks["S5 returned a ReasoningResult"] = "verification_status" in summary["last_query"]["reasoning_result"]
    checks["S6 produced an ActionGoal"] = goal is not None and "validated" in goal
    checks["all JSON contracts honoured"] = not summary["contract_errors"]
    if src_frames is not None:
        labels = {pid.rsplit("_", 1)[0]: set() for f in summary["frames"] for pid in f["ids"].values()}
        for f in summary["frames"]:
            for pid in f["ids"].values():
                labels[pid.rsplit("_", 1)[0]].add(pid)
        checks["tracking kept one ID per object"] = all(len(v) == 1 for v in labels.values())
        checks["mock goal validated (path clear)"] = goal["validated"] is True
    report = {"passed": all(checks.values()), "checks": checks, "seconds": round(time.perf_counter() - t0, 1),
              "frames": summary["n_frames"], "fps": summary["fps"], "action_goal": goal,
              "contract_errors": summary["contract_errors"]}
    (out / "smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", default=None, help="S1 ROS 2 bag (default: mock bag)")
    ap.add_argument("--s3", choices=["replay", "live"], default="replay")
    ap.add_argument("--camera-tf", default=None, help="JSON with T_map_camera for the bag's camera")
    ap.add_argument("--query", default="Go to the mug")
    ap.add_argument("--frames", type=int, default=6, help="mock bag length")
    ap.add_argument("--every", type=int, default=1, help="keep every N-th bag frame (real 90 s bag: 10)")
    a = ap.parse_args()
    r = smoke(a.bag, a.s3, a.camera_tf, a.query, n_frames=a.frames, every=a.every)
    for name, ok in r["checks"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    g = r["action_goal"]
    print(f"  ActionGoal: target={g['target_object_id']} pose={g['target_pose']} validated={g['validated']}")
    print(f"SMOKE TEST {'PASSED' if r['passed'] else 'FAILED'} in {r['seconds']} s ({r['frames']} frames, {r['fps']} FPS)")
    sys.exit(0 if r["passed"] else 1)


if __name__ == "__main__":
    main()

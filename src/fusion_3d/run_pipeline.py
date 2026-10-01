"""S2 command-line entry point.

    python -m src.fusion_3d.run_pipeline --frame data/mock/frame_000
    python -m src.fusion_3d.run_pipeline --frame data/mock/frame_000 --show   # Open3D window
    python -m src.fusion_3d.run_pipeline --frame <S1 frame dir> \
        --observations output/s3_semantic/<run>/frame_000000/observation.json

Writes ``outputs/fusion_3d/<frame>_objects.json`` (ObjectInstance3D list for
S4/S6) and ``<frame>_points.npz`` (point subset per object).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..preprocessing.depth_cleaning import clean_depth, depth_to_meters
from ..preprocessing.frame_loader import find_observation_file, load_frame, load_semantic_observations
from .evaluate import evaluate_against_ground_truth
from .pipeline import load_config, process_frame


def run(frame_dir, out_dir="outputs/fusion_3d", config=None, mode=None, observations=None):
    frame_dir = Path(frame_dir)
    cfg = load_config(config)
    frame = load_frame(frame_dir)
    skipped: list = []
    obs = load_semantic_observations(observations or find_observation_file(frame_dir), skipped)
    result = process_frame(frame, obs, cfg, fusion_mode=mode)
    result.rejected = skipped + result.rejected

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = frame_dir.name
    npz_name = f"{stem}_points.npz"
    for o in result.objects:
        o.points_ref = f"{npz_name}#{o.object_id}"
    np.savez_compressed(out / npz_name, **{k: v.astype(np.float32) for k, v in result.object_points.items()})
    payload = {
        "frame": str(frame_dir.as_posix()),
        "timestamp": frame.timestamp,
        "frame_id": frame.frame_id,
        **result.to_dict(),
    }
    gt_path = frame_dir / "ground_truth.json"
    if gt_path.exists():
        payload["evaluation"] = evaluate_against_ground_truth(
            result.objects, json.loads(gt_path.read_text(encoding="utf-8")))
    json_path = out / f"{stem}_objects.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return frame, obs, result, payload, json_path


def main():
    ap = argparse.ArgumentParser(description="S2 2D->3D projection and fusion")
    ap.add_argument("--frame", default="data/mock/frame_000", help="frame directory (relative path)")
    ap.add_argument("--out", default="outputs/fusion_3d")
    ap.add_argument("--observations", default=None,
                    help="S3 observation.json (default: <frame>/observation.json)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--mode", choices=["adaptive", "fixed"], default=None)
    ap.add_argument("--show", action="store_true", help="open the Open3D visualizer")
    args = ap.parse_args()

    frame, obs, result, payload, json_path = run(args.frame, args.out, args.config, args.mode, args.observations)
    print(f"{len(result.objects)} objects, {len(result.rejected)} rejected, "
          f"{result.timings_ms['total']:.1f} ms  ->  {json_path}")
    for o in result.objects:
        print(f"  {o.object_id:<14} centroid={np.round(o.centroid, 3).tolist()}  "
              f"dims={np.round(o.box_dimensions, 3).tolist()}  depth_conf={o.depth_confidence:.2f}  "
              f"w_depth={o.fusion_weights['depth']:.2f}")
    for r in result.rejected:
        print(f"  REJECTED {r['object_id']}: {r['reason']}")
    if "evaluation" in payload:
        ev = payload["evaluation"]
        print(f"  recall={ev['recall']:.2f}  mean centroid error={ev['mean_centroid_error_m']} m")
    if args.show:
        from .visualize import show_open3d

        intr = frame.intrinsics
        cfg = load_config(args.config)
        depth = clean_depth(depth_to_meters(frame.depth_raw, intr.depth_scale),
                            cfg["depth"]["min_m"], cfg["depth"]["max_m"])
        show_open3d(frame, depth, result)


if __name__ == "__main__":
    main()

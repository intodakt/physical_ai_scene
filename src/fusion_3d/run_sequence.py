"""Run S2 on a sequence of frames (Week 6 — static baseline).

    # frames exported from S1's bag (bag_reader) with S3's observation.json in each
    python -m src.fusion_3d.run_sequence --frames data/frames/static_baseline \\
        --out outputs/fusion_3d/static_baseline --temporal-median

For a static scene every object should stay put, so the spread of its 3D box
centre over the frames ("jitter") measures how stable the output is. With
``--temporal-median`` the per-pixel median depth of all frames is also
processed once (fills dropouts, averages sensor noise).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np

from ..preprocessing.depth_cleaning import temporal_median_depth
from ..preprocessing.frame_loader import find_observation_file, load_frame, load_semantic_observations
from .evaluate import evaluate_against_ground_truth
from .pipeline import load_config, process_frame, sensor_depth


def stability(per_frame: list[list[dict]]) -> dict:
    """Per-label detection rate and box-centre jitter (mm) over a static sequence."""
    labels = sorted({o["semantic_label"] for objs in per_frame for o in objs})
    out = {}
    for lab in labels:
        cs = [np.array((o.get("box_map") or {}).get("center") or o["centroid"]) for objs in per_frame
              for o in objs if o["semantic_label"] == lab]
        statuses = [o.get("depth_status", "ok") for objs in per_frame for o in objs if o["semantic_label"] == lab]
        C = np.array(cs)
        dev = np.linalg.norm(C - C.mean(0), axis=1) if len(C) else np.array([np.nan])
        out[lab] = {
            "detection_rate": round(len(cs) / len(per_frame), 3),
            "jitter_rms_mm": round(float(np.sqrt((dev ** 2).mean())) * 1000, 2),
            "jitter_max_mm": round(float(dev.max()) * 1000, 2),
            "depth_status": max(set(statuses), key=statuses.count) if statuses else None,
        }
    return out


def run_sequence(frames_dir, out_dir: Optional[str] = None, cfg: Optional[dict] = None,
                 temporal_median: bool = False) -> dict:
    cfg = cfg or load_config()
    dirs = sorted(p for p in Path(frames_dir).iterdir() if p.is_dir() and (p / "rgb.png").exists())
    if not dirs:
        raise FileNotFoundError(f"no frame directories in {frames_dir}")
    out = Path(out_dir) if out_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    per_frame, timings, depths = [], [], []
    for d in dirs:
        frame = load_frame(d)
        obs = load_semantic_observations(find_observation_file(d))
        res = process_frame(frame, obs, cfg)
        objs = [o.to_dict() for o in res.objects]
        per_frame.append(objs)
        timings.append(res.timings_ms["total"])
        if temporal_median:
            depths.append(sensor_depth(frame, cfg))
        if out:
            (out / f"{d.name}_objects.json").write_text(json.dumps({"frame": d.name, **res.to_dict()}, indent=1))
    report = {
        "frames": len(dirs),
        "mean_ms_per_frame": round(float(np.mean(timings)), 1),
        "objects_per_frame": [len(o) for o in per_frame],
        "stability": stability(per_frame),
    }
    gt_path = dirs[0] / "ground_truth.json"
    if gt_path.exists():
        gt = json.loads(gt_path.read_text())
        errs = [evaluate_against_ground_truth(objs, gt)["mean_box_center_error_m"] for objs in per_frame]
        report["mean_box_center_error_m"] = round(float(np.mean(errs)), 4)
    if temporal_median:
        frame = load_frame(dirs[0])
        obs = load_semantic_observations(find_observation_file(dirs[0]))
        res = process_frame(frame, obs, cfg, depth_override=temporal_median_depth(depths))
        tm = {"objects": len(res.objects)}
        if gt_path.exists():
            tm["mean_box_center_error_m"] = evaluate_against_ground_truth(res.objects, gt)["mean_box_center_error_m"]
        report["temporal_median"] = tm
        if out:
            (out / "temporal_median_objects.json").write_text(json.dumps(res.to_dict(), indent=1))
    if out:
        (out / "sequence_report.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", required=True, help="directory with frame_XXXX sub-directories")
    ap.add_argument("--out", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--temporal-median", action="store_true")
    a = ap.parse_args()
    rep = run_sequence(a.frames, a.out, load_config(a.config), a.temporal_median)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()

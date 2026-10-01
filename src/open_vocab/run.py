"""CLI: python -m src.open_vocab.run --image image.jpg --device cpu"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import cv2

from .contract import finite_number, load_observation
from .models import SamSegmenter, WorldDetector
from .pipeline import PerceptionPipeline, load_config
from .video import process_video, video_info
from .input_profile import check_input


def input_frames(args):
    if args.manifest:
        rows = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not rows:
            raise ValueError("Manifest must be a non-empty array of frames")
        frames = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("rgb_path"), str):
                raise ValueError("Each manifest frame needs rgb_path")
            frames.append({"image": (args.manifest.parent / row["rgb_path"]).resolve(),
                           "frame_id": row.get("frame_id"), "timestamp": row.get("timestamp")})
    elif args.images:
        files = sorted(p for p in args.images.iterdir() if p.is_file() and
                       p.suffix.lower() in {".png", ".jpg", ".jpeg"})
        frames = [{"image": p, "frame_id": p.name, "timestamp": None} for p in files]
    else:
        frames = [{"image": args.image, "frame_id": args.frame_id or args.image.stem,
                   "timestamp": args.timestamp}]
    if not frames:
        raise ValueError("No input images found")
    seen = set()
    for frame in frames:
        fid = frame["frame_id"]
        if not isinstance(fid, str) or not fid.strip() or fid in seen:
            raise ValueError("Frame IDs must be non-empty unique strings")
        seen.add(fid)
        if frame["timestamp"] is not None and not finite_number(frame["timestamp"]):
            raise ValueError("Source timestamps must be finite seconds or null")
        if not frame["image"].is_file():
            raise FileNotFoundError(f"Missing image: {frame['image']}")
    return frames


def fingerprint(path):
    path = Path(path)
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path)
    source.add_argument("--video", type=Path, help="Local video; exports MP4 previews and per-frame images/JSON")
    source.add_argument("--images", type=Path, help="Directory of JPG/PNG frames")
    source.add_argument("--manifest", type=Path, help="JSON array with rgb_path, frame_id, timestamp")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "configs/zed_mini_left.json")
    parser.add_argument("--output", type=Path, default=Path("output/s3_semantic"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--detector-weights", type=Path)
    parser.add_argument("--sam-weights", type=Path)
    parser.add_argument("--clip-weights", type=Path)
    parser.add_argument("--prompts-file", type=Path, help="One prompt per line; # comments allowed")
    parser.add_argument("--frame-id")
    parser.add_argument("--timestamp", type=float)
    args = parser.parse_args()
    if not args.image and (args.frame_id is not None or args.timestamp is not None):
        parser.error("--frame-id/--timestamp require --image; use --manifest for per-frame metadata")
    try:
        config = load_config(args.config)
        if args.video:
            info = video_info(args.video)
            check_input(config, info["width"], info["height"], info["fps"])
            frames = None
        else:
            frames = input_frames(args)
            if "input_profile" in config:
                for frame in frames:
                    preview = cv2.imread(str(frame["image"]))
                    if preview is None:
                        raise ValueError(f"Cannot decode image: {frame['image']}")
                    check_input(config, preview.shape[1], preview.shape[0])
        for key, path in (("detector", args.detector_weights), ("segmenter", args.sam_weights)):
            if path is not None:
                if not path.is_file():
                    raise FileNotFoundError(f"Missing weights: {path}")
                config[key] = str(path)
        if args.clip_weights is not None and not args.clip_weights.is_file():
            raise FileNotFoundError(f"Missing CLIP weights: {args.clip_weights}")
        if args.prompts_file:
            config["prompts"] = list(dict.fromkeys(
                line.strip() for line in args.prompts_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")))
            if not config["prompts"]:
                raise ValueError("Prompts file is empty")
        print("Loading YOLO-World and SAM weights...", flush=True)
        setup_start = time.perf_counter()
        detector = WorldDetector(config, args.device, args.clip_weights)
        segmenter = SamSegmenter(config["segmenter"], args.device)
        setup_seconds = time.perf_counter() - setup_start
        pipeline = PerceptionPipeline(detector, segmenter, config)
        created = datetime.now(timezone.utc)
        run_dir = args.output.resolve() / created.strftime("%Y%m%dT%H%M%S_%fZ")
        run_dir.mkdir(parents=True, exist_ok=False)
        try:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
            git_commit = commit.stdout.strip() if commit.returncode == 0 else None
        except FileNotFoundError:
            git_commit = None
        manifest = {"created_at_utc": created.isoformat(), "status": "running",
                    "git_commit": git_commit,
                    "command": sys.argv, "config": config, "device_requested": args.device,
                    "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
                    "weight_sha256": {k: fingerprint(config[k]) for k in ("detector", "segmenter")},
                    "versions": {n: version(n) for n in ("ultralytics", "torch", "numpy", "opencv-python")},
                    "setup_seconds": setup_seconds, "frames": []}
        manifest_path = run_dir / "run.json"

        def save_manifest():
            manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")

        save_manifest()
        try:
            incomplete = False

            def record_frame(path, input_path, source_frame_index=None):
                nonlocal incomplete
                data, masks = load_observation(path, require_complete=False)
                complete = len(masks) == len(data["detections"])
                incomplete |= not complete
                manifest["frames"].append({"frame_id": data["frame_id"], "input_path": input_path,
                                           "source_frame_index": source_frame_index,
                                           "observation": str(path.relative_to(run_dir)),
                                           "detections": len(data["detections"]), "masks": len(masks),
                                           "complete": complete})
                save_manifest()
                print(f"{data['frame_id']}: {len(data['detections'])} detections, {len(masks)} masks", flush=True)

            if args.video:
                manifest["video"] = process_video(pipeline, args.video, run_dir, record_frame)
            else:
                for index, frame in enumerate(frames):
                    image = cv2.imread(str(frame["image"]))
                    if image is None:
                        raise ValueError(f"Cannot decode image: {frame['image']}")
                    path = pipeline.process_frame(image, frame_id=frame["frame_id"],
                                                  timestamp=frame["timestamp"], output_dir=run_dir / f"frame_{index:06d}")
                    record_frame(path, str(frame["image"]))
            manifest["status"] = "incomplete_masks" if incomplete else "complete"
        except KeyboardInterrupt:
            manifest.update(status="interrupted", error="Stopped by user; video previews may be partial")
            raise
        except Exception as exc:
            manifest.update(status="failed", error=str(exc))
            raise
        finally:
            save_manifest()
        print(f"Results: {run_dir}")
        if incomplete:
            parser.exit(2, "Some detections have missing/empty masks. Inspect observation.json before handoff.\n")
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()

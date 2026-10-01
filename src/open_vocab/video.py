"""Offline video processing with per-frame observations and MP4 previews."""

import math
from pathlib import Path

import cv2
from .input_profile import check_input


def video_info(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Missing video: {path}")
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError(f"Cannot open video: {path}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("Video has no valid frame rate")
        ok, frame = capture.read()
        if not ok:
            raise ValueError("Video has no decodable frames")
        height, width = frame.shape[:2]
        return {"input_path": str(path), "fps": fps, "width": width, "height": height,
                "audio": "not_exported", "timestamp_origin": "video_start_seconds"}
    finally:
        capture.release()


def process_video(pipeline, video_path, output_dir, on_frame=None):
    """Keep every frame. No tracking or frame sampling is performed."""
    info = video_info(video_path)
    check_input(getattr(pipeline, "config", {}), info["width"], info["height"], info["fps"])
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = info["width"], info["height"]
    # MP4 codecs need even dimensions. Padding does not change JSON coordinates.
    encoded_size = (width + width % 2, height + height % 2)
    capture = cv2.VideoCapture(str(video_path))
    writers = {}
    count = 0
    previous_timestamp = -1.0
    fallback_count = 0
    try:
        for name in ("annotated", "segmentation"):
            path = output_dir / f"{name}.partial.mp4"
            if path.exists() or (output_dir / f"{name}.mp4").exists():
                raise FileExistsError(f"Video output already exists: {path}")
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"),
                                     info["fps"], encoded_size)
            writers[name] = writer
            if not writer.isOpened():
                raise RuntimeError("MP4 encoder unavailable in this OpenCV installation")
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[:2] != (height, width):
                raise ValueError("Video frame dimensions changed during decoding")
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if not math.isfinite(timestamp) or timestamp < 0 or timestamp <= previous_timestamp:
                timestamp = max(count / info["fps"], previous_timestamp + 1 / info["fps"])
                fallback_count += 1
            previous_timestamp = timestamp
            frame_id = f"{Path(video_path).stem}_{count:06d}"
            path = pipeline.process_frame(frame, frame_id=frame_id, timestamp=timestamp,
                                          output_dir=output_dir / f"frame_{count:06d}")
            for name, writer in writers.items():
                rendered = cv2.imread(str(path.parent / f"{name}.jpg"))
                if rendered is None or rendered.shape[:2] != (height, width):
                    raise ValueError(f"Missing or invalid rendered frame: {name}")
                rendered = cv2.copyMakeBorder(rendered, 0, height % 2, 0, width % 2,
                                              cv2.BORDER_CONSTANT, value=0)
                writer.write(rendered)
            if on_frame is not None:
                on_frame(path, str(video_path), count)
            count += 1
        if not count:
            raise ValueError("Video has no decodable frames")
        reported_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if math.isfinite(reported_count) and reported_count > count + 1:
            raise ValueError(f"Video decoding ended early: {count} of {reported_count:g} frames")
    finally:
        capture.release()
        for writer in writers.values():
            writer.release()
    # A failed run keeps clearly named partial files rather than a final preview.
    for name in writers:
        partial = output_dir / f"{name}.partial.mp4"
        check = cv2.VideoCapture(str(partial))
        try:
            ok, _ = check.read()
            if not ok or int(check.get(cv2.CAP_PROP_FRAME_COUNT)) != count:
                raise RuntimeError(f"Output video validation failed: {partial}")
        finally:
            check.release()
    for name in writers:
        (output_dir / f"{name}.partial.mp4").rename(output_dir / f"{name}.mp4")
    return info | {"frames_written": count, "encoded_size": list(encoded_size),
                   "timestamp_fallback_frames": fallback_count,
                   "preview_timing": "constant_fps_from_source_metadata",
                   "outputs": ["annotated.mp4", "segmentation.mp4"]}

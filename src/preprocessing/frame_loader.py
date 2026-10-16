"""Load a synchronized RGB-D frame (from S1) and SemanticObservations (from S3).

Offline frame directory layout (what S1's bag-export script writes)::

    <frame_dir>/
        rgb.png                      # aligned colour image
        depth.png | depth.npy        # aligned depth (uint16 mm or float metres)
        camera_intrinsics.yaml       # see intrinsics.py
        frame_meta.json   (optional) # timestamp, frame_id, T_map_camera
        observation.json             # S3 output for this frame (s3-semantic-draft-0.1)
        masks/det_0000.png ...       # S3 masks, uint8 0/255, paths relative to the JSON

All paths are resolved relative to the given directory — never absolute.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .intrinsics import CameraIntrinsics, load_intrinsics
from .mask_utils import rle_decode


@dataclass
class SynchronizedFrame:
    rgb: np.ndarray  # HxWx3 uint8
    depth_raw: np.ndarray  # HxW (uint16 mm or float32 m)
    intrinsics: CameraIntrinsics
    timestamp: float = 0.0
    frame_id: str = "camera_color_optical_frame"
    T_map_camera: Optional[np.ndarray] = None  # 4x4, optical frame -> map
    source: str = ""


@dataclass
class SemanticObservation:
    """One detection from S3 (YOLO-World box + SAM mask)."""

    bbox: list  # [x1, y1, x2, y2] pixels
    mask: np.ndarray  # HxW bool
    labels: list  # top-k label candidates, best first
    score: float = 1.0
    label_scores: list = field(default_factory=list)
    embedding: Optional[list] = None
    timestamp: float = 0.0
    observation_id: str = ""

    @property
    def label(self) -> str:
        return self.labels[0] if self.labels else "unknown"


def _read_depth(frame_dir: Path) -> np.ndarray:
    npy = frame_dir / "depth.npy"
    if npy.exists():
        return np.load(npy)
    png = frame_dir / "depth.png"
    if png.exists():
        return np.array(Image.open(png))
    raise FileNotFoundError(f"No depth.npy or depth.png in {frame_dir}")


def load_frame(frame_dir: str | Path, intrinsics_path: str | Path | None = None) -> SynchronizedFrame:
    frame_dir = Path(frame_dir)
    rgb = np.array(Image.open(frame_dir / "rgb.png").convert("RGB"))
    depth = _read_depth(frame_dir)
    intr = load_intrinsics(intrinsics_path or frame_dir / "camera_intrinsics.yaml")
    if depth.shape[:2] != rgb.shape[:2]:
        raise ValueError(
            f"Depth {depth.shape[:2]} and RGB {rgb.shape[:2]} are not aligned — "
            "record with align_depth.enable:=true"
        )

    meta = {}
    meta_path = frame_dir / "frame_meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    T = meta.get("T_map_camera")
    return SynchronizedFrame(
        rgb=rgb,
        depth_raw=depth,
        intrinsics=intr,
        timestamp=float(meta.get("timestamp", 0.0)),
        frame_id=meta.get("frame_id", "camera_color_optical_frame"),
        T_map_camera=np.array(T, dtype=float) if T is not None else None,
        source=str(frame_dir),
    )


def _decode_mask(entry, base_dir: Path) -> np.ndarray:
    if isinstance(entry, dict):
        return rle_decode(entry)
    if isinstance(entry, str):
        p = Path(entry)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError(f"mask path must be relative to the observation JSON: {entry}")
        p = base_dir / p
        if p.suffix == ".npy":
            return np.load(p).astype(bool)
        return np.array(Image.open(p).convert("L")) > 127
    return np.asarray(entry, dtype=bool)


def find_observation_file(frame_dir: str | Path) -> Path:
    """S3's ``observation.json`` (preferred) or the legacy ``semantic_observations.json``."""
    frame_dir = Path(frame_dir)
    for name in ("observation.json", "semantic_observations.json"):
        if (frame_dir / name).exists():
            return frame_dir / name
    raise FileNotFoundError(f"No observation.json in {frame_dir}")


def load_semantic_observations(path: str | Path, skipped: list | None = None) -> list[SemanticObservation]:
    """Parse S3's per-frame JSON.

    Supports S3's ``s3-semantic-draft-0.1`` contract (``detections`` with
    ``detection_id``, ``detector_score``, ``mask_status`` and PNG mask paths)
    and the older list / ``observations`` layout with RLE masks. Detections
    whose ``mask_status`` is not ``ok`` are skipped and appended to ``skipped``.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        entries = data.get("detections", data.get("observations", []))
        frame_ts = data.get("timestamp") or 0.0
        size = data.get("image_size")
    else:
        entries, frame_ts, size = data, 0.0, None
    obs = []
    for i, e in enumerate(entries):
        oid = str(e.get("detection_id", e.get("id", i)))
        labels = e.get("labels") or [e.get("label", "unknown")]
        if e.get("mask_status", "ok") != "ok" or e.get("mask") is None:
            if skipped is not None:
                skipped.append({"detection_id": oid, "semantic_label": labels[0],
                                "reason": f"S3 mask_status={e.get('mask_status')}"})
            continue
        mask = _decode_mask(e["mask"], path.parent)
        if size and mask.shape != (size["height"], size["width"]):
            raise ValueError(f"mask {oid} is {mask.shape}, image_size is {size}")
        obs.append(
            SemanticObservation(
                bbox=[float(v) for v in e["bbox"]],
                mask=mask,
                labels=list(labels),
                score=float(e.get("detector_score", e.get("score", 1.0))),
                label_scores=list(e.get("label_scores", [])),
                embedding=e.get("embedding"),
                timestamp=float(e.get("timestamp") or frame_ts),
                observation_id=oid,
            )
        )
    return obs

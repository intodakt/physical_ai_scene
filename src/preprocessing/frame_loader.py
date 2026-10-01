"""Load a synchronized RGB-D frame (from S1) and SemanticObservations (from S3).

Offline frame directory layout (what S1's bag-export script writes)::

    <frame_dir>/
        rgb.png                      # aligned colour image
        depth.png | depth.npy        # aligned depth (uint16 mm or float metres)
        camera_intrinsics.yaml       # see intrinsics.py
        frame_meta.json   (optional) # timestamp, frame_id, T_map_camera
        semantic_observations.json   # S3 output for this frame

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
        p = base_dir / entry
        if p.suffix == ".npy":
            return np.load(p).astype(bool)
        return np.array(Image.open(p).convert("L")) > 127
    return np.asarray(entry, dtype=bool)


def load_semantic_observations(path: str | Path) -> list[SemanticObservation]:
    """Parse S3's per-frame JSON (list, or dict with an ``observations`` key)."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["observations"] if isinstance(data, dict) else data
    frame_ts = data.get("timestamp", 0.0) if isinstance(data, dict) else 0.0
    obs = []
    for i, e in enumerate(entries):
        labels = e.get("labels") or [e.get("label", "unknown")]
        obs.append(
            SemanticObservation(
                bbox=[float(v) for v in e["bbox"]],
                mask=_decode_mask(e["mask"], path.parent),
                labels=list(labels),
                score=float(e.get("score", e.get("detector_score", 1.0))),
                label_scores=list(e.get("label_scores", [])),
                embedding=e.get("embedding"),
                timestamp=float(e.get("timestamp", frame_ts)),
                observation_id=str(e.get("id", i)),
            )
        )
    return obs

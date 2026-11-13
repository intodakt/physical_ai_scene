"""Modality quality features and confidence fusion.

For each object we measure how trustworthy every modality is (0..1) and turn
that into fusion weights. G1 runs the F2 RGB-D baseline, so LiDAR is kept in
the contract with weight 0 and quality ``None``.

    F_i = w_rgb*F_rgb + w_depth*F_depth + w_lidar*F_lidar + w_sem*F_sem
    with sum(w) = 1, w >= 0

* ``fixed``    — equal weights over the available modalities (baseline).
* ``adaptive`` — weights proportional to each modality's quality, so a shiny
  object with a poor valid-depth ratio automatically trusts depth less.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

MODALITIES = ("rgb", "depth", "lidar", "semantic")


@dataclass
class ModalityQuality:
    rgb: Optional[float] = None
    depth: Optional[float] = None
    lidar: Optional[float] = None
    semantic: Optional[float] = None
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {m: getattr(self, m) for m in MODALITIES}


def _clip01(x: float) -> float:
    if x is None or not np.isfinite(x):
        return 0.0
    return float(min(1.0, max(0.0, x)))


def rgb_quality(rgb: np.ndarray, mask: np.ndarray) -> tuple[float, dict]:
    """Brightness (best near mid-grey) x sharpness (Laplacian variance) in the mask.

    Computed on the mask's bounding box only (W11 speed-up; same result as on the whole image:
    the Laplacian is evaluated at interior mask pixels, i.e. not on the image border)."""
    m = mask.astype(bool)
    if not m.any():
        return 0.0, {"brightness": None, "sharpness": None}
    H, W = m.shape
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    brightness = float(rgb[y0:y1, x0:x1][m[y0:y1, x0:x1]].astype(np.float32).mean(axis=-1).mean() / 255.0)
    q_bright = 1.0 - min(1.0, abs(brightness - 0.5) * 2.0) ** 2
    r0, r1, c0, c1 = max(y0, 1), min(y1, H - 1), max(x0, 1), min(x1, W - 1)     # interior pixels with neighbours
    lap_var = 0.0
    if r1 > r0 and c1 > c0:
        gray = rgb[r0 - 1:r1 + 1, c0 - 1:c1 + 1].astype(np.float32).mean(axis=2) / 255.0
        lap = -4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
        sub = m[r0:r1, c0:c1]
        lap_var = float(lap[sub].var()) if sub.any() else 0.0
    q_sharp = 1.0 - np.exp(-lap_var / 2e-4)
    return _clip01(q_bright * (0.5 + 0.5 * q_sharp)), {
        "brightness": brightness,
        "laplacian_var": lap_var,
    }


def depth_quality(valid_ratio: float, inlier_ratio: float, n_points: int, min_points: int,
                  plane_leak_ratio: float = 0.0) -> float:
    """Valid-pixel ratio x outlier-filter inlier ratio x (1 - see-through leak); zero if too few points."""
    if n_points < min_points:
        return 0.0
    return _clip01(valid_ratio * (0.5 + 0.5 * inlier_ratio) * (1.0 - plane_leak_ratio))


def fusion_weights(quality: ModalityQuality, mode: str = "adaptive", floor: float = 0.0) -> dict:
    available = [m for m in MODALITIES if getattr(quality, m) is not None]
    w = {m: 0.0 for m in MODALITIES}
    if not available:
        return w
    if mode == "fixed":
        for m in available:
            w[m] = 1.0 / len(available)
        return w
    if mode != "adaptive":
        raise ValueError(f"unknown fusion mode {mode!r}")
    q = np.array([_clip01(getattr(quality, m)) for m in available]) + floor
    if q.sum() <= 0:
        q = np.ones_like(q)
    q = q / q.sum()
    for m, v in zip(available, q):
        w[m] = float(v)
    return w


def fused_confidence(quality: ModalityQuality, weights: dict) -> float:
    return _clip01(sum(weights[m] * _clip01(getattr(quality, m)) for m in MODALITIES
                       if getattr(quality, m) is not None))

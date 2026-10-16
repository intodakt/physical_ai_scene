"""Is the depth inside this mask trustworthy? (Week 7 — transparent / reflective objects)

Stereo (ZED Mini) and structured-light (RealSense) sensors fail on glass in
two different ways, so two independent cues are measured on the *interior* of
S3's mask (eroded a few pixels so SAM's border bleed onto the desk is ignored):

1. **Holes** — ``interior_valid_ratio``: the sensor returns no depth for most
   pixels (specular or texture-less surface).
2. **See-through** — ``plane_leak_ratio``: depth *is* returned, but the rays
   pass through the glass and hit the desk behind it, so the "object" pixels
   lie on the support plane instead of above it. An opaque object standing
   on the desk never shows its interior pixels on the desk plane.

    genuine_ratio = interior_valid_ratio * (1 - plane_leak_ratio)
                  — share of interior pixels whose depth really comes from the object.

    status = "no_depth"               if interior_valid_ratio < no_depth_ratio
             "transparent_suspected"  if interior_valid_ratio < min_valid_ratio
                                       or plane_leak_ratio    > max_plane_leak
             "ok"                     otherwise
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

import numpy as np

from ..preprocessing.intrinsics import CameraIntrinsics
from ..preprocessing.mask_utils import erode
from .projection import deproject_mask

DEFAULTS = {
    "erode_px": 3,
    "no_depth_ratio": 0.05,
    "min_valid_ratio": 0.5,
    "max_plane_leak": 0.35,
    "plane_leak_margin_m": 0.012,
    "min_genuine_ratio": 0.10,
}


@dataclass
class DepthReliability:
    valid_ratio: float
    interior_valid_ratio: float
    plane_leak_ratio: float
    genuine_ratio: float
    status: str
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("valid_ratio", "interior_valid_ratio", "plane_leak_ratio", "genuine_ratio"):
            d[k] = round(float(d[k]), 4)
        return d


def plane_leak_map(depth_m: np.ndarray, mask: np.ndarray, intr: CameraIntrinsics,
                   plane: Optional[np.ndarray], margin: float) -> np.ndarray:
    """Per-pixel map inside ``mask``: 0 = no depth, 1 = above the desk, 2 = on/behind the desk."""
    out = np.zeros(depth_m.shape, np.uint8)
    pts, uv = deproject_mask(depth_m, mask, intr)
    if not len(pts):
        return out
    on_plane = np.zeros(len(pts), bool) if plane is None else (pts @ plane[:3] + plane[3]) < margin
    out[uv[:, 1], uv[:, 0]] = np.where(on_plane, 2, 1)
    return out


def assess(depth_m: np.ndarray, mask: np.ndarray, intr: CameraIntrinsics,
           plane: Optional[np.ndarray], cfg: Optional[dict] = None) -> DepthReliability:
    c = {**DEFAULTS, **(cfg or {})}
    mask = mask.astype(bool)
    valid = np.isfinite(depth_m) & (depth_m > 0)
    n = int(mask.sum())
    valid_ratio = float(valid[mask].mean()) if n else 0.0

    interior = erode(mask, c["erode_px"])
    if interior.sum() < 20:  # tiny objects: fall back to the full mask
        interior = mask
    iv = float(valid[interior].mean()) if interior.any() else 0.0

    leak = 0.0
    if plane is not None and iv > 0:
        m = plane_leak_map(depth_m, interior, intr, plane, c["plane_leak_margin_m"])
        n_valid = int((m > 0).sum())
        leak = float((m == 2).sum()) / n_valid if n_valid else 0.0

    reasons = []
    if iv < c["no_depth_ratio"]:
        status = "no_depth"
        reasons.append(f"only {iv:.0%} of interior pixels have depth")
    else:
        if iv < c["min_valid_ratio"]:
            reasons.append(f"holes: {iv:.0%} interior depth < {c['min_valid_ratio']:.0%}")
        if leak > c["max_plane_leak"]:
            reasons.append(f"see-through: {leak:.0%} of interior depth lies on the desk plane")
        status = "transparent_suspected" if reasons else "ok"
    return DepthReliability(valid_ratio, iv, leak, iv * (1 - leak), status, reasons)


def depth_geometry_usable(rel: DepthReliability, cfg: Optional[dict] = None) -> bool:
    """Enough genuine object depth to build geometry from points (else: mask + desk plane)."""
    c = {**DEFAULTS, **(cfg or {})}
    return rel.status == "ok" or rel.genuine_ratio >= c["min_genuine_ratio"]

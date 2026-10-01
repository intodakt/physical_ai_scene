"""2D -> 3D deprojection with the pinhole model (and the inverse, for tests).

    X = (u - cx) * Z / fx
    Y = (v - cy) * Z / fy
    Z = depth(u, v)

Output points are in the camera *optical* frame (x right, y down, z forward),
in metres.
"""

from __future__ import annotations

import numpy as np

from ..preprocessing.intrinsics import CameraIntrinsics


def deproject_pixels(
    u: np.ndarray, v: np.ndarray, z: np.ndarray, intr: CameraIntrinsics
) -> np.ndarray:
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    x = (u - intr.cx) * z / intr.fx
    y = (v - intr.cy) * z / intr.fy
    return np.stack([x, y, z], axis=-1)


def deproject_mask(
    depth_m: np.ndarray, mask: np.ndarray, intr: CameraIntrinsics
) -> tuple[np.ndarray, np.ndarray]:
    """Return (Nx3 points, Nx2 pixel coords [u, v]) for valid depth inside ``mask``.

    Pixels outside the mask, and pixels with depth <= 0 / NaN, are ignored.
    """
    if depth_m.shape != mask.shape:
        raise ValueError(f"mask {mask.shape} does not match depth {depth_m.shape}")
    sel = mask.astype(bool) & np.isfinite(depth_m) & (depth_m > 0)
    v, u = np.nonzero(sel)
    pts = deproject_pixels(u, v, depth_m[v, u], intr)
    return pts, np.stack([u, v], axis=-1)


def deproject_depth(depth_m: np.ndarray, intr: CameraIntrinsics, stride: int = 1):
    """Deproject the whole depth image (every ``stride``-th pixel)."""
    mask = np.zeros(depth_m.shape, dtype=bool)
    mask[::stride, ::stride] = True
    return deproject_mask(depth_m, mask, intr)


def project_points(points: np.ndarray, intr: CameraIntrinsics) -> np.ndarray:
    """Project Nx3 optical-frame points to Nx2 pixel coords (u, v)."""
    p = np.asarray(points, dtype=np.float64)
    u = p[:, 0] * intr.fx / p[:, 2] + intr.cx
    v = p[:, 1] * intr.fy / p[:, 2] + intr.cy
    return np.stack([u, v], axis=-1)

"""Geometry without depth: S3's mask + the desk plane (Week 7 fallback).

When the depth inside a mask is unusable (glass), the object can still be
placed because it *stands on the desk*:

1. **Contact line** — the lowest mask pixel of every image column touches the
   desk. Its viewing ray is intersected with the RANSAC desk plane → 3D
   contact points (front edge of the footprint).
2. **Footprint** — the true contact points form the front arc of a round
   base (glasses, cups, bottles), so a circle is fitted with RANSAC. Columns
   that only contain the top rim (perspective makes the rim look wider than
   the base) project far behind the object and are rejected as outliers.
3. **Height** — the top mask pixel near the centre column is the far rim; its
   ray is followed until it is one radius behind the centre, and the height
   above the desk is read there.

Requires the map transform (z up, desk ≈ z = 0) and a fitted plane.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ..preprocessing.intrinsics import CameraIntrinsics
from .transforms import apply_transform, invert_transform


def _rays(u, v, intr: CameraIntrinsics) -> np.ndarray:
    return np.stack([(u - intr.cx) / intr.fx, (v - intr.cy) / intr.fy, np.ones_like(u, float)], -1)


def fit_circle_ransac(xy: np.ndarray, r_min: float = 0.01, r_max: float = 0.25, tol: float = 0.004,
                      iters: int = 300, seed: int = 0):
    """Robust 2D circle fit → (centre, radius, inlier mask) or None."""
    rng = np.random.default_rng(seed)
    n = len(xy)
    if n < 3:
        return None
    best = None
    for _ in range(iters):
        a, b, c = xy[rng.choice(n, 3, replace=False)]
        # circumcircle of the three points
        d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
        if abs(d) < 1e-12:
            continue
        ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
        uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
        ctr = np.array([ux, uy])
        r = float(np.linalg.norm(a - ctr))
        if not r_min <= r <= r_max:
            continue
        inl = np.abs(np.linalg.norm(xy - ctr, axis=1) - r) < tol
        if best is None or inl.sum() > best[2].sum():
            best = (ctr, r, inl)
    if best is None or best[2].sum() < max(5, 0.3 * n):
        return None
    # least-squares refinement on the inliers (algebraic fit)
    p = xy[best[2]]
    A = np.c_[2 * p, np.ones(len(p))]
    sol, *_ = np.linalg.lstsq(A, (p ** 2).sum(1), rcond=None)
    ctr = sol[:2]
    r = float(np.sqrt(max(sol[2] + ctr @ ctr, 1e-12)))
    return ctr, r, best[2]


def estimate_from_mask(mask: np.ndarray, intr: CameraIntrinsics, plane: np.ndarray,
                       T_map_camera: np.ndarray, contact_trim_px: int = 2) -> Optional[dict]:
    mask = mask.astype(bool)
    cols = np.flatnonzero(mask.any(axis=0))
    if len(cols) < 3 or plane is None or T_map_camera is None:
        return None
    H = mask.shape[0]
    bottom = H - 1 - np.argmax(mask[::-1, cols], axis=0) - contact_trim_px  # undo SAM's few-pixel bleed
    top = np.argmax(mask[:, cols], axis=0)

    # 1. contact points on the desk plane (camera frame), then map frame
    r = _rays(cols.astype(float), bottom.astype(float), intr)
    denom = r @ plane[:3]
    t = -plane[3] / np.where(np.abs(denom) < 1e-9, np.nan, denom)
    ok = np.isfinite(t) & (t > 0)
    if ok.sum() < 3:
        return None
    contact = apply_transform(T_map_camera, r[ok] * t[ok, None])
    z_desk = float(np.median(contact[:, 2]))

    # 2. footprint: RANSAC circle through the contact arc
    cam = T_map_camera[:3, 3]
    view = np.asarray(T_map_camera[:3, 2], float)
    fwd = view[:2] / np.linalg.norm(view[:2])
    lat = np.array([-fwd[1], fwd[0]])
    fit = fit_circle_ransac(contact[:, :2])
    if fit is None:
        return None
    centre_xy, radius, inliers = fit
    width = 2 * radius

    # 3. height from the top mask pixel nearest the centre column
    c_cam = invert_transform(T_map_camera)[:3, :3] @ np.r_[centre_xy, z_desk] + invert_transform(T_map_camera)[:3, 3]
    u_c = intr.fx * c_cam[0] / c_cam[2] + intr.cx
    j = int(np.argmin(np.abs(cols - u_c)))
    ray_map = T_map_camera[:3, :3] @ _rays(np.array([float(cols[j])]), np.array([float(top[j])]), intr)[0]
    along = ray_map[:2] @ fwd
    if abs(along) < 1e-9:
        return None
    s = ((centre_xy @ fwd + radius) - cam[:2] @ fwd) / along
    height = float(cam[2] + s * ray_map[2] - z_desk)
    if not (0.005 < height < 1.0):
        return None

    centre = np.r_[centre_xy, z_desk + height / 2]
    yaw = float(np.arctan2(lat[1], lat[0]))
    return {
        "centroid_map": centre.tolist(),
        "box_map": {"center": centre.tolist(), "yaw": yaw, "dimensions": [width, height, width]},
        "n_contact": int(ok.sum()),
        "n_contact_inliers": int(inliers.sum()),
    }

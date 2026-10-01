"""Point-cloud cleaning and object geometry (Open3D)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import open3d as o3d


def to_pcd(points: np.ndarray, colors: Optional[np.ndarray] = None) -> o3d.geometry.PointCloud:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    if colors is not None:
        c = np.asarray(colors, dtype=np.float64)
        if c.max(initial=0) > 1.0:
            c = c / 255.0
        pcd.colors = o3d.utility.Vector3dVector(c)
    return pcd


def fit_support_plane(
    points: np.ndarray, distance_threshold: float = 0.006, iterations: int = 500, seed: int = 0
) -> Optional[np.ndarray]:
    """RANSAC the dominant plane (the desk) in a scene cloud. Returns [a, b, c, d]
    with the normal pointing towards the camera (d > 0 in the camera frame)."""
    if len(points) < 100:
        return None
    o3d.utility.random.seed(seed)
    plane, inliers = to_pcd(points).segment_plane(
        distance_threshold=distance_threshold, ransac_n=3, num_iterations=iterations
    )
    if len(inliers) < 0.1 * len(points):
        return None
    plane = np.asarray(plane, dtype=np.float64)
    if plane[3] < 0:  # camera origin on the positive side
        plane = -plane
    return plane


def remove_plane_points(points: np.ndarray, plane: np.ndarray, margin: float) -> np.ndarray:
    """Keep points more than ``margin`` metres above the support plane."""
    dist = points @ plane[:3] + plane[3]
    return dist > margin


@dataclass
class CleanResult:
    pcd: o3d.geometry.PointCloud
    n_raw: int
    n_after_plane: int
    n_after_voxel: int
    n_after_outlier: int
    n_final: int

    @property
    def inlier_ratio(self) -> float:
        return self.n_final / self.n_after_voxel if self.n_after_voxel else 0.0


def clean_object_cloud(
    points: np.ndarray,
    colors: Optional[np.ndarray] = None,
    plane: Optional[np.ndarray] = None,
    plane_margin: float = 0.008,
    voxel_size: float = 0.003,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0,
    cluster_eps: float = 0.02,
    cluster_min_points: int = 10,
    keep_largest_cluster: bool = True,
) -> CleanResult:
    """Support-plane removal -> voxel downsample -> statistical outlier removal
    -> (optional) keep largest DBSCAN cluster."""
    n_raw = len(points)
    if plane is not None and n_raw:
        keep = remove_plane_points(points, plane, plane_margin)
        points = points[keep]
        colors = colors[keep] if colors is not None else None
    n_after_plane = len(points)

    pcd = to_pcd(points, colors)
    if voxel_size > 0 and len(points):
        pcd = pcd.voxel_down_sample(voxel_size)
    n_after_voxel = len(pcd.points)

    if n_after_voxel > nb_neighbors:
        pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    n_after_outlier = len(pcd.points)

    if keep_largest_cluster and n_after_outlier > cluster_min_points:
        labels = np.asarray(pcd.cluster_dbscan(eps=cluster_eps, min_points=cluster_min_points))
        if labels.size and labels.max() >= 0:
            largest = np.bincount(labels[labels >= 0]).argmax()
            pcd = pcd.select_by_index(np.flatnonzero(labels == largest))
    return CleanResult(pcd, n_raw, n_after_plane, n_after_voxel, n_after_outlier, len(pcd.points))


def centroid(points: np.ndarray) -> np.ndarray:
    return np.asarray(points, dtype=np.float64).mean(axis=0)


def min_area_rect(xy: np.ndarray, angle_step_deg: float = 1.0):
    """Minimum-area rectangle of 2D points by angle search.

    Returns (angle_rad, (len_a, len_b), (cx, cy)) where side ``a`` lies along
    (cos angle, sin angle).
    """
    xy = np.asarray(xy, dtype=np.float64)
    angles = np.deg2rad(np.arange(0.0, 90.0, angle_step_deg))
    c, s = np.cos(angles), np.sin(angles)
    a = np.outer(c, xy[:, 0]) + np.outer(s, xy[:, 1])  # (A, N)
    b = np.outer(-s, xy[:, 0]) + np.outer(c, xy[:, 1])
    ext_a = a.max(axis=1) - a.min(axis=1)
    ext_b = b.max(axis=1) - b.min(axis=1)
    k = int(np.argmin(ext_a * ext_b))
    mid_a = (a[k].max() + a[k].min()) / 2
    mid_b = (b[k].max() + b[k].min()) / 2
    center = (c[k] * mid_a - s[k] * mid_b, s[k] * mid_a + c[k] * mid_b)
    return float(angles[k]), (float(ext_a[k]), float(ext_b[k])), center


def _pca_obb(points: np.ndarray) -> dict:
    """PCA box — used for (nearly) planar clouds where Qhull is degenerate."""
    p = np.asarray(points, dtype=np.float64)
    mean = p.mean(axis=0)
    _, R = np.linalg.eigh(np.cov((p - mean).T) if len(p) > 1 else np.eye(3))
    R = R[:, ::-1].copy()  # largest variance first
    if np.linalg.det(R) < 0:
        R[:, 2] *= -1
    local = (p - mean) @ R
    # In-plane minimum-area rectangle (PCA axes are ambiguous for squares).
    ang, _, _ = min_area_rect(local[:, :2])
    ca, sa = np.cos(ang), np.sin(ang)
    R2 = np.array([[ca, -sa, 0.0], [sa, ca, 0.0], [0.0, 0.0, 1.0]])
    R = R @ R2
    local = (p - mean) @ R
    lo, hi = local.min(axis=0), local.max(axis=0)
    return {
        "center": (mean + R @ ((lo + hi) / 2)).tolist(),
        "rotation": R.tolist(),
        "extent": (hi - lo).tolist(),
    }


def oriented_bbox(pcd: o3d.geometry.PointCloud) -> dict:
    """Open3D minimal OBB; PCA box for flat/degenerate clouds (e.g. a book seen
    only from the top), where Qhull fails or silently returns a zero box."""
    pca = _pca_obb(np.asarray(pcd.points))
    if min(pca["extent"]) < 1e-4:
        return pca
    try:
        obb = pcd.get_minimal_oriented_bounding_box(robust=True)
    except RuntimeError:
        return pca
    extent = np.asarray(obb.extent)
    if not np.all(np.isfinite(extent)) or extent.min() <= 0:
        return pca
    return {
        "center": np.asarray(obb.center).tolist(),
        "rotation": np.asarray(obb.R).tolist(),
        "extent": extent.tolist(),
    }


def axis_aligned_bbox(points: np.ndarray) -> dict:
    p = np.asarray(points)
    return {"min": p.min(axis=0).tolist(), "max": p.max(axis=0).tolist()}


def gravity_aligned_bbox(points_map: np.ndarray, angle_step_deg: float = 1.0) -> dict:
    """Upright box in the map frame (z up): minimum-area rectangle in XY + z range.

    Returns center, yaw (rad) and dimensions [width, height, depth] where
    height is vertical, width >= depth are the horizontal sides. This is the
    box S4 uses for ``on`` / ``near`` rules, so its height is physically
    meaningful (unlike the arbitrary axis order of a free OBB).
    """
    p = np.asarray(points_map, dtype=np.float64)
    yaw, (la, lb), (cx, cy) = min_area_rect(p[:, :2], angle_step_deg)
    zmin, zmax = p[:, 2].min(), p[:, 2].max()
    if lb > la:  # make width the longer horizontal side
        la, lb, yaw = lb, la, yaw + np.pi / 2
    return {
        "center": [float(cx), float(cy), float((zmin + zmax) / 2)],
        "yaw": float(yaw),
        "dimensions": [la, float(zmax - zmin), lb],
    }


def gravity_box_corners(box: dict) -> np.ndarray:
    """8 corners (map frame) of a gravity-aligned box, for drawing."""
    w, h, d = box["dimensions"]
    cx, cy, cz = box["center"]
    c, s = np.cos(box["yaw"]), np.sin(box["yaw"])
    corners = []
    for dz in (-h / 2, h / 2):
        for da, db in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
            corners.append([cx + c * da - s * db, cy + s * da + c * db, cz + dz])
    return np.array(corners)


def point_density(n_points: int, extent) -> float:
    """Points per cubic decimetre of box volume (robust to flat boxes)."""
    vol_dm3 = float(np.prod(np.maximum(np.asarray(extent) * 10.0, 0.1)))
    return n_points / vol_dm3

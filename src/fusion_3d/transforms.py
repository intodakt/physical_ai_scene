"""Rigid transforms between the camera optical frame and S1's ``map`` frame.

S1 publishes a static TF ``map -> camera_link`` (ROS convention: x forward,
y left, z up). Depth pixels are deprojected in the *optical* frame
(x right, y down, z forward), so we chain ``camera_link -> optical``.
"""

from __future__ import annotations

import numpy as np

# Columns are the optical axes expressed in camera_link.
R_LINK_OPTICAL = np.array(
    [
        [0.0, 0.0, 1.0],
        [-1.0, 0.0, 0.0],
        [0.0, -1.0, 0.0],
    ]
)


def rpy_to_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Rz @ Ry @ Rx


def make_transform(R: np.ndarray, t) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = np.asarray(t, dtype=float)
    return T


def T_map_optical_from_static_tf(xyz, rpy) -> np.ndarray:
    """Build map <- optical from S1's ``map -> camera_link`` (xyz, roll/pitch/yaw)."""
    T_map_link = make_transform(rpy_to_matrix(*rpy), xyz)
    T_link_opt = make_transform(R_LINK_OPTICAL, [0, 0, 0])
    return T_map_link @ T_link_opt


def apply_transform(T: np.ndarray, points: np.ndarray) -> np.ndarray:
    p = np.asarray(points, dtype=np.float64)
    return p @ T[:3, :3].T + T[:3, 3]


def invert_transform(T: np.ndarray) -> np.ndarray:
    R, t = T[:3, :3], T[:3, 3]
    return make_transform(R.T, -R.T @ t)

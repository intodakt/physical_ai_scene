"""Desk-aligned frame from S2's support plane.

S2 reports the desk plane (camera frame, n.p + d = 0) and T_map_camera. If S1's map TF is only a
placeholder, the desk is tilted/offset in `map` and "z = 0" is not the desk. This module re-expresses
object centres in a frame where the desk is the plane z = 0 and up is +z, so `on` works either way.
"""
import numpy as np


def _rotation_to_z(n):
    """Minimal rotation taking unit vector n to +z (Rodrigues)."""
    z = np.array([0.0, 0.0, 1.0])
    v, c = np.cross(n, z), float(n @ z)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1.0 + c)


def desk_alignment(frame):
    """Return (rotate_fn, info) or None when the frame has no usable support plane / map TF.

    rotate_fn maps a map-frame point to the desk-aligned frame (desk = z 0, up = +z).
    """
    plane, T = frame.get("support_plane"), frame.get("T_map_camera")
    if not plane or not T or len(plane) != 4:
        return None
    n_cam, d_cam = np.array(plane[:3], float), float(plane[3])
    T = np.array(T, float)
    R, t = T[:3, :3], T[:3, 3]
    scale = np.linalg.norm(n_cam)
    n = (R @ n_cam) / scale                    # plane normal in the map frame
    d = (d_cam - (R @ n_cam) @ t) / scale      # n.p_map + d = 0
    pts = np.array([o["box_map"]["center"] for o in frame["objects"]], float)
    if len(pts) and np.median(pts @ n + d) < 0:   # objects must lie on the positive side
        n, d = -n, -d
    Rl = _rotation_to_z(n)
    tilt = float(np.degrees(np.arccos(np.clip(n[2], -1, 1))))

    def rotate(p):
        q = Rl @ np.asarray(p, float)
        return [float(q[0]), float(q[1]), float(q[2] + d)]   # n.p + d is the height above the desk

    return rotate, {"method": "support_plane", "desk_tilt_in_map_deg": round(tilt, 2)}

"""Visualisation helpers.

* ``show_open3d`` — interactive Open3D window (use on your laptop:
  ``python -m src.fusion_3d.run_pipeline --show``).
* ``render_*`` — headless matplotlib renders used for reports/screenshots.
"""

from __future__ import annotations

import numpy as np

from . import geometry as geo
from .projection import deproject_depth
from .transforms import apply_transform

# Categorical slots in fixed order (validated reference palette).
PALETTE_HEX = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PALETTE = [tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)) for h in PALETTE_HEX]
BOX_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7)]


def show_open3d(frame, depth_m, result, title="S2 — ObjectInstance3D"):
    import open3d as o3d

    pts, uv = deproject_depth(depth_m, frame.intrinsics, stride=2)
    scene = geo.to_pcd(pts, frame.rgb[uv[:, 1], uv[:, 0]])
    geoms = [scene, o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)]
    for i, obj in enumerate(result.objects):
        P = result.object_points[obj.object_id]
        p = geo.to_pcd(P)
        p.paint_uniform_color(PALETTE[i % len(PALETTE)])
        obb = p.get_oriented_bounding_box()
        obb.color = PALETTE[i % len(PALETTE)]
        geoms += [p, obb]
    o3d.visualization.draw_geometries(geoms, window_name=title)


def _set_limits_3d(ax, P, margin=0.06):
    lo, hi = P.min(0) - margin, P.max(0) + margin
    lo[2] = min(lo[2], -0.01)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(hi - lo))


def render_scene_3d(ax, frame, depth_m, result, stride=3, elev=38, azim=-160, labels=True):
    """Map-frame scatter: desk cloud (RGB) + object points + gravity-aligned boxes."""
    T = result.T_map_camera
    obj_pts = {o.object_id: apply_transform(T, result.object_points[o.object_id]) for o in result.objects}
    allobj = np.vstack(list(obj_pts.values()))
    lo, hi = allobj.min(0) - 0.08, allobj.max(0) + 0.08
    pts, uv = deproject_depth(depth_m, frame.intrinsics, stride=stride)
    P = apply_transform(T, pts)
    keep = np.all((P[:, :2] > lo[:2]) & (P[:, :2] < hi[:2]), axis=1) & (P[:, 2] > -0.02) & (P[:, 2] < 0.01)
    ax.scatter(*P[keep].T, c=frame.rgb[uv[keep, 1], uv[keep, 0]] / 255.0, s=0.5, alpha=0.5, linewidths=0)
    for i, obj in enumerate(result.objects):
        col = PALETTE[i % len(PALETTE)]
        Pm = obj_pts[obj.object_id][::2]
        ax.scatter(*Pm.T, color=col, s=0.8, alpha=0.5, linewidths=0)
        corners = geo.gravity_box_corners(obj.box_map)
        for a, b in BOX_EDGES:
            ax.plot(*corners[[a, b]].T, color=col, lw=1.8)
        c = obj.centroid_map
        ax.scatter([c[0]], [c[1]], [c[2]], color="#0b0b0b", s=22, marker="x")
        if labels:
            top = corners[:, 2].max()
            ax.text(c[0], c[1], top + 0.035, f"{obj.semantic_label}  {obj.depth_confidence:.2f}",
                    color="#0b0b0b", fontsize=9, ha="center", zorder=10,
                    bbox=dict(fc="white", ec=col, lw=1.2, pad=2, alpha=0.9))
    _set_limits_3d(ax, allobj)
    ax.view_init(elev=elev, azim=azim)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((1, 1, 1, 0))
        axis.pane.set_edgecolor("#e6e5e0")
    ax.set_xlabel("X map [m]")
    ax.set_ylabel("Y map [m]")
    ax.set_zlabel("Z [m]")


def overlay_masks(rgb, observations, alpha=0.45):
    out = rgb.astype(np.float32) / 255.0
    for i, obs in enumerate(observations):
        col = np.array(PALETTE[i % len(PALETTE)])
        m = obs.mask.astype(bool)
        out[m] = out[m] * (1 - alpha) + col * alpha
    return np.clip(out, 0, 1)

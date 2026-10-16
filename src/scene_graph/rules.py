"""Deterministic geometric rules. Every rule returns (holds, evidence) so each edge carries its proof.

Objects are plain dicts with (map frame, metres, z up):
    center  [x, y, z]      box centre
    size    [W_x, D_y, H_z]
    yaw     rotation of the box about z (rad)
    cam_x   x of the centroid in the camera optical frame (x = right), or None
"""
import math

NEAR_THRESHOLD_M = 0.30
ON_GAP_TOL_M = 0.03        # |bottom(A) - top(B)| must be below this
ON_MIN_OVERLAP = 0.30      # share of A's footprint that must lie over B
SIDE_MARGIN_M = 0.05       # left/right need a clear gap, not sensor noise


def footprint(obj):
    """Axis-aligned XY rectangle (xmin, xmax, ymin, ymax) enclosing the yaw-rotated box."""
    (cx, cy, _), (w, d, _) = obj["center"], obj["size"]
    c, s = abs(math.cos(obj.get("yaw", 0.0))), abs(math.sin(obj.get("yaw", 0.0)))
    hx, hy = (w * c + d * s) / 2, (w * s + d * c) / 2
    return cx - hx, cx + hx, cy - hy, cy + hy


def xy_overlap(a, b):
    """Fraction of A's footprint that lies inside B's footprint (0..1)."""
    ax0, ax1, ay0, ay1 = footprint(a)
    bx0, bx1, by0, by1 = footprint(b)
    ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    iy = max(0.0, min(ay1, by1) - max(ay0, by0))
    area = (ax1 - ax0) * (ay1 - ay0)
    return (ix * iy) / area if area > 0 else 0.0


def check_near(a, b, threshold=NEAR_THRESHOLD_M):
    dist = math.dist(a["center"], b["center"])
    return dist < threshold, {"distance_m": round(dist, 4)}


def check_on(a, b, gap_tol=ON_GAP_TOL_M, min_overlap=ON_MIN_OVERLAP):
    """A rests on B: A's bottom is at B's top (within tolerance), A is above B, footprints overlap."""
    bottom_a = a["center"][2] - a["size"][2] / 2
    top_b = b["center"][2] + b["size"][2] / 2
    gap = bottom_a - top_b
    overlap = xy_overlap(a, b)
    holds = a["center"][2] > b["center"][2] and abs(gap) < gap_tol and overlap >= min_overlap
    return holds, {"vertical_gap_m": round(gap, 4), "xy_overlap": round(overlap, 3)}


def check_left_of(a, b, margin=SIDE_MARGIN_M):
    """A is left of B as seen by the camera (optical frame, x to the right)."""
    if a.get("cam_x") is None or b.get("cam_x") is None:
        return False, {}
    delta = b["cam_x"] - a["cam_x"]
    return delta > margin, {"dx_m": round(delta, 4), "frame": "camera"}

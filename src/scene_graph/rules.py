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
UNDER_MAX_GAP_M = 0.30     # A under B: B's bottom at most this far above A's top
INSIDE_MIN_OVERLAP = 0.80  # A inside B: share of A's footprint within B's footprint
INSIDE_TOL_M = 0.01        # vertical tolerance for containment


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


def _z_range(obj):
    z, h = obj["center"][2], obj["size"][2]
    return z - h / 2, z + h / 2


def check_under(a, b, gap_tol=ON_GAP_TOL_M, max_gap=UNDER_MAX_GAP_M, min_overlap=ON_MIN_OVERLAP):
    """A is under B: B is above A (B's bottom at or above A's top, within max_gap) and A's footprint is covered by B.

    Holds both for contact (a book under a mug that is on it) and for a gap (an object under a shelf)."""
    _, top_a = _z_range(a)
    bottom_b, _ = _z_range(b)
    gap = bottom_b - top_a
    overlap = xy_overlap(a, b)
    holds = b["center"][2] > a["center"][2] and -gap_tol < gap < max_gap and overlap >= min_overlap
    return holds, {"vertical_gap_m": round(gap, 4), "xy_overlap": round(overlap, 3)}


def check_inside(a, b, min_overlap=INSIDE_MIN_OVERLAP, tol=INSIDE_TOL_M):
    """A is inside B: A's footprint lies (mostly) within B's and A's bottom lies between B's bottom and top.

    E.g. a pen in a cup: S2 gives overlapping boxes, the pen's bottom is inside the cup's height range."""
    bottom_a, top_a = _z_range(a)
    bottom_b, top_b = _z_range(b)
    overlap = xy_overlap(a, b)
    area_a = (lambda f: (f[1] - f[0]) * (f[3] - f[2]))(footprint(a))
    area_b = (lambda f: (f[1] - f[0]) * (f[3] - f[2]))(footprint(b))
    holds = (overlap >= min_overlap and area_a < area_b and bottom_b - tol <= bottom_a < top_b - tol)
    return holds, {"xy_overlap": round(overlap, 3), "bottom_offset_m": round(bottom_a - bottom_b, 4),
                   "top_b_minus_bottom_a_m": round(top_b - bottom_a, 4)}


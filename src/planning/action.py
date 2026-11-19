"""S6 action: verified S5 answer + S4 graph -> ActionGoal v2 -> virtual-twin simulation.

Roadmap §11.6: "invalid goals are rejected with reason codes"; "action rejection when target
geometry is unverified". ActionGoal v2 keeps the four contract fields of v1 (target_object_id,
target_pose, exclusion_zones, validated) and adds:

    reason_code   OK | OK_DETOUR | TARGET_UNVERIFIED | TARGET_NOT_IN_GRAPH | TARGET_OCCLUDED |
                  TARGET_IN_EXCLUSION_ZONE | PATH_BLOCKED
    reason        human-readable explanation
    reachability  straight line clear? if not: does a detour exist (waypoints, length)?  (W11)
    path          waypoints [[x, y], ...] the virtual agent will drive
    clearance_m   smallest distance between the path and any exclusion zone
    warnings      e.g. low target confidence (the goal is still sent, the warning is shown)

Planner (``cfg["planner"]``):
    straight  only the straight line agent → target (Week-5 behaviour; the default, so earlier
              results such as "2 / 2 unsafe paths rejected" stay reproducible)
    detour    if the straight line is blocked, A* on a grid over the desk around the inflated zones
"""

from __future__ import annotations

import heapq
import math

SCHEMA_VERSION = "action_goal-2.0"


# ---------------------------------------------------------------- geometry
def footprint_polygon(node: dict, margin: float = 0.0) -> list:
    """XY footprint of a scene-graph node, inflated by ``margin``.

    With S4's ``yaw`` the box is rotated exactly; older graphs without yaw fall back to a square on the
    longer side, which covers the object whatever its rotation.
    """
    (x, y, _), (w, d, _) = node["pose_map"], node["size"]
    if "yaw" not in node:
        w = d = max(w, d)
    yaw = node.get("yaw", 0.0)
    c, s = math.cos(yaw), math.sin(yaw)
    hx, hy = w / 2 + margin, d / 2 + margin
    return [[round(x + c * a - s * b, 4), round(y + s * a + c * b, 4)]
            for a, b in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]


def inside(p, poly) -> bool:
    """Point in polygon (ray casting)."""
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def _seg_point_dist(p, a, b) -> float:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def point_poly_dist(p, poly) -> float:
    """0 inside, else the distance to the nearest edge."""
    if inside(p, poly):
        return 0.0
    return min(_seg_point_dist(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def densify(path, step):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
    return out


def path_hits(path, zones, step) -> list:
    pts = densify(path, step)
    return [z["object_id"] for z in zones if any(inside(p, z["polygon"]) for p in pts)]


def clearance(path, zones, step) -> float | None:
    if not zones:
        return None
    pts = densify(path, step)
    return round(min(point_poly_dist(p, z["polygon"]) for z in zones for p in pts), 4)


def node_label(node: dict) -> str:
    return node["names"][0]["text"] if node.get("names") else node["id"]


# ---------------------------------------------------------------- detour planner
def astar(start, goal, zones, bounds, res=0.01, clearance_m=0.0):
    """Grid A* (8-connected) in ``bounds`` = (xmin, xmax, ymin, ymax); cells within ``clearance_m`` of a zone are blocked.

    Start and goal cells are always free. Returns a simplified waypoint list or None.
    """
    xmin, xmax, ymin, ymax = bounds
    nx, ny = int(round((xmax - xmin) / res)) + 1, int(round((ymax - ymin) / res)) + 1
    cell = lambda p: (min(nx - 1, max(0, int(round((p[0] - xmin) / res)))), min(ny - 1, max(0, int(round((p[1] - ymin) / res)))))
    pos = lambda c: (xmin + c[0] * res, ymin + c[1] * res)
    s, g = cell(start), cell(goal)
    blocked_cache: dict = {}

    def blocked(c):
        if c in (s, g):
            return False
        if c not in blocked_cache:
            p = pos(c)
            blocked_cache[c] = any(point_poly_dist(p, z["polygon"]) <= clearance_m for z in zones)
        return blocked_cache[c]

    h = lambda c: math.dist(c, g)
    openq, came, cost = [(h(s), s)], {s: None}, {s: 0.0}
    while openq:
        _, c = heapq.heappop(openq)
        if c == g:
            break
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not dx and not dy:
                    continue
                n = (c[0] + dx, c[1] + dy)
                if not (0 <= n[0] < nx and 0 <= n[1] < ny) or blocked(n):
                    continue
                nc = cost[c] + math.hypot(dx, dy)
                if nc < cost.get(n, float("inf")):
                    cost[n], came[n] = nc, c
                    heapq.heappush(openq, (nc + h(n), n))
    if g not in came:
        return None
    cells = [g]
    while came[cells[-1]] is not None:
        cells.append(came[cells[-1]])
    pts = [pos(c) for c in reversed(cells)]
    pts[0], pts[-1] = tuple(start), tuple(goal)
    # string-pulling: keep a waypoint only where the straight shortcut would hit a zone
    out, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and (path_hits([pts[i], pts[j]], zones, res / 2)
                             or (clearance_m and (clearance([pts[i], pts[j]], zones, res / 2) or 1) <= clearance_m)):
            j -= 1
        out.append(pts[j])
        i = j
    return [[round(x, 4), round(y, 4)] for x, y in out]


# ---------------------------------------------------------------- ActionGoal
def build_action_goal(reasoning: dict, graph: dict, cfg: dict) -> dict:
    """S5 ReasoningResult + S4 graph -> ActionGoal v2."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    agent = list(cfg.get("agent_start", [1.0, 0.0]))
    margin, step = cfg.get("exclusion_margin_m", 0.03), cfg.get("step_m", 0.01)
    target_id = reasoning.get("target_id")
    zones = [{"object_id": n["id"], "label": node_label(n), "polygon": footprint_polygon(n, margin)}
             for n in graph["nodes"]
             if not n.get("virtual") and n.get("state") != "occluded" and n["id"] != target_id
             and any(w in node_label(n).split() for w in cfg.get("exclusion_labels", []))]
    goal = {"schema_version": SCHEMA_VERSION, "target_object_id": target_id, "target_pose": None,
            "exclusion_zones": zones, "validated": False, "agent_start": agent,
            "reason_code": "", "reason": "", "path": [], "clearance_m": None, "warnings": []}

    def reject(code, why):
        goal.update(reason_code=code, reason=why)
        return goal

    if not reasoning.get("verification_status"):
        return reject("TARGET_UNVERIFIED", "S5 could not verify a target; no goal sent to the virtual agent")
    if target_id not in nodes:
        return reject("TARGET_NOT_IN_GRAPH", f"target {target_id!r} is not a node of the scene graph")
    node = nodes[target_id]
    tx, ty, _ = node["pose_map"]
    goal["target_pose"] = [round(tx, 4), round(ty, 4), round(math.atan2(ty - agent[1], tx - agent[0]), 4)]
    if node.get("state") == "occluded":
        return reject("TARGET_OCCLUDED", f"{target_id} is occluded: its position is only remembered, not verified now")
    conf, min_conf = node.get("confidence"), cfg.get("min_target_confidence", 0.0)
    if conf is not None and conf < min_conf:
        goal["warnings"].append(f"LOW_TARGET_CONFIDENCE: {target_id} confidence {conf:.2f} < {min_conf:.2f}")

    inside_of = [z["object_id"] for z in zones if inside((tx, ty), z["polygon"])]
    if inside_of:
        return reject("TARGET_IN_EXCLUSION_ZONE",
                      f"{target_id} lies inside the safety zone of {', '.join(inside_of)}; path crosses exclusion zone")
    straight = [agent, [tx, ty]]
    blocked = path_hits(straight, zones, step)
    if not blocked:
        goal.update(validated=True, reason_code="OK", reason="path is clear", path=straight,
                    clearance_m=clearance(straight, zones, step), reachability={"straight_clear": True})
        return goal
    # W11 reachability: is the target reachable at all when the straight line is blocked?
    b = cfg.get("workspace_bounds", [0.0, 1.4, -0.6, 0.6])
    path = astar(agent, (tx, ty), zones, b, res=cfg.get("grid_m", 0.01), clearance_m=cfg.get("clearance_m", 0.0))
    goal["reachability"] = {"straight_clear": False, "blocked_by": blocked, "detour_exists": bool(path),
                            "detour_waypoints": len(path) - 2 if path else None,
                            "detour_length_m": round(sum(math.dist(p, q) for p, q in zip(path, path[1:])), 3) if path else None}
    if path and cfg.get("planner", "straight") == "detour":
        goal.update(validated=True, reason_code="OK_DETOUR", path=path, clearance_m=clearance(path, zones, step),
                    reason=f"straight line crosses {', '.join(blocked)}; detour with {len(path) - 2} waypoint(s)")
        return goal
    goal["warnings"].append("REACHABLE_BY_DETOUR: a path around the zones exists (planner: detour)" if path
                            else "UNREACHABLE: no path around the exclusion zones inside the workspace")
    goal["path"] = straight
    return reject("PATH_BLOCKED", f"path crosses exclusion zone of {', '.join(blocked)}")


def simulate(goal: dict, graph: dict, cfg: dict) -> dict:
    """Drive the virtual agent along ``goal['path']``. Success = never enters a zone and ends on the target."""
    if not goal.get("validated"):
        return {"executed": False, "success": False, "collisions": 0, "final_error_m": None}
    nodes = {n["id"]: n for n in graph["nodes"]}
    tx, ty, _ = goal["target_pose"]
    path = densify(goal.get("path") or [goal["agent_start"], [tx, ty]], cfg.get("step_m", 0.01))
    zones = [z for z in goal["exclusion_zones"] if z["object_id"] != goal["target_object_id"]]
    collisions = sum(any(inside(p, z["polygon"]) for z in zones) for p in path)
    real = nodes.get(goal["target_object_id"], {}).get("pose_map", [tx, ty, 0])
    err = math.dist(path[-1], real[:2])
    length = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
    return {"executed": True, "success": collisions == 0 and err <= cfg.get("reach_tolerance_m", 0.05),
            "collisions": collisions, "final_error_m": round(err, 4), "steps": len(path), "path_length_m": round(length, 4)}

"""S6 placeholder: centroid tracker + ActionGoal on a virtual desk grid.

Follows the behaviour S6 presented in Week 5 (15 cm gate, N-frame memory, straight path,
exclusion zones, 4-field ActionGoal) so the launch file and the dashboard can run end to end.
When S6 merges ``src/tracking`` and ``src/planning``, ``main_pipeline.py`` switches to them;
this file then only serves as the reference for the contract.
"""

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------- tracking
@dataclass
class _Track:
    persistent_id: str
    label: str
    center: list
    missed: int = 0


@dataclass
class CentroidTracker:
    gate_m: float = 0.15
    max_missed_frames: int = 10
    tracks: list = field(default_factory=list)
    last_motion: dict = field(default_factory=dict)   # persistent_id -> metres moved since last frame
    _counts: dict = field(default_factory=dict)

    def update(self, objects: list) -> list:
        """Fill ``persistent_id`` on S2 objects (dicts, map frame). Greedy nearest match per label."""
        self.last_motion = {}
        pairs = []
        for oi, o in enumerate(objects):
            for ti, t in enumerate(self.tracks):
                if t.label == o["semantic_label"]:
                    d = math.dist(_center(o), t.center)
                    if d < self.gate_m:
                        pairs.append((d, oi, ti))
        used_o, used_t = set(), set()
        for d, oi, ti in sorted(pairs):
            if oi in used_o or ti in used_t:
                continue
            used_o.add(oi)
            used_t.add(ti)
            t = self.tracks[ti]
            t.center, t.missed = _center(objects[oi]), 0
            objects[oi]["persistent_id"] = t.persistent_id
            self.last_motion[t.persistent_id] = round(d, 4)
        for oi, o in enumerate(objects):
            if oi not in used_o:
                label = o["semantic_label"]
                self._counts[label] = self._counts.get(label, 0) + 1
                pid = f"{label.replace(' ', '_')}_{self._counts[label]:02d}"
                self.tracks.append(_Track(pid, label, _center(o)))
                used_t.add(len(self.tracks) - 1)
                o["persistent_id"] = pid
        for ti, t in enumerate(self.tracks):
            if ti not in used_t:
                t.missed += 1
        self.tracks = [t for t in self.tracks if t.missed <= self.max_missed_frames]
        return objects


def _center(o):
    box = o.get("box_map") or {}
    return list(box.get("center") or o.get("centroid_map") or o["centroid"])


# ---------------------------------------------------------------- action
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


def _inside(p, poly):
    """Point in convex/simple polygon (ray casting)."""
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _segment_hits(a, b, poly, step):
    n = max(1, int(math.dist(a, b) / step))
    return any(_inside((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n), poly) for k in range(n + 1))


def node_label(node: dict) -> str:
    return node["names"][0]["text"] if node.get("names") else node["id"]


def build_action_goal(reasoning: dict, graph: dict, cfg: dict) -> dict:
    """S5 ReasoningResult + S4 graph -> ActionGoal (target_object_id, target_pose, exclusion_zones, validated)."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    agent = list(cfg.get("agent_start", [1.0, 0.0]))
    margin, step = cfg.get("exclusion_margin_m", 0.03), cfg.get("step_m", 0.01)
    target_id = reasoning.get("target_id")
    zones = [{"object_id": n["id"], "label": node_label(n), "polygon": footprint_polygon(n, margin)}
             for n in graph["nodes"]
             if not n.get("virtual") and n.get("state") != "occluded"
             and any(w in node_label(n).split() for w in cfg.get("exclusion_labels", []))]
    goal = {"target_object_id": target_id, "target_pose": None, "exclusion_zones": zones,
            "validated": False, "agent_start": agent, "reason": ""}
    if not reasoning.get("verification_status") or target_id not in nodes:
        goal["reason"] = "S5 could not verify a target; no goal sent to the virtual agent"
        return goal
    tx, ty, _ = nodes[target_id]["pose_map"]
    goal["target_pose"] = [round(tx, 4), round(ty, 4), round(math.atan2(ty - agent[1], tx - agent[0]), 4)]
    blocked = [z["object_id"] for z in zones
               if z["object_id"] != target_id and _segment_hits(agent, (tx, ty), z["polygon"], step)]
    goal["validated"] = not blocked
    goal["reason"] = f"path crosses exclusion zone of {', '.join(blocked)}" if blocked else "path is clear"
    return goal


def simulate(goal: dict, graph: dict, cfg: dict) -> dict:
    """Drive the virtual agent along the goal path. Success = never enters a zone and ends on the target."""
    if not goal.get("validated"):
        return {"executed": False, "success": False, "collisions": 0, "final_error_m": None}
    nodes = {n["id"]: n for n in graph["nodes"]}
    a, (tx, ty, _) = goal["agent_start"], goal["target_pose"]
    step = cfg.get("step_m", 0.01)
    n = max(1, int(math.dist(a, (tx, ty)) / step))
    path = [(a[0] + (tx - a[0]) * k / n, a[1] + (ty - a[1]) * k / n) for k in range(n + 1)]
    zones = [z for z in goal["exclusion_zones"] if z["object_id"] != goal["target_object_id"]]
    collisions = sum(any(_inside(p, z["polygon"]) for z in zones) for p in path)
    real = nodes.get(goal["target_object_id"], {}).get("pose_map", [tx, ty, 0])
    err = math.dist(path[-1], real[:2])
    return {"executed": True, "success": collisions == 0 and err <= cfg.get("reach_tolerance_m", 0.05),
            "collisions": collisions, "final_error_m": round(err, 4), "steps": len(path)}

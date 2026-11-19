"""S6: MultiTermTracker (IDs, states, events) and ActionGoal v2 (reason codes, detour planner)."""

import itertools
import json

import numpy as np
import pytest

from src.integration import contracts
from src.planning import build_action_goal, simulate
from src.tracking import MultiTermTracker
from src.tracking.assignment import linear_sum_assignment

S4_GRAPH = json.loads(open("outputs/scene_graph/frame_000_scene_graph.json", encoding="utf-8").read())
CFG = {"agent_start": [0.25, 0.0], "exclusion_labels": ["laptop"], "exclusion_margin_m": 0.03,
       "reach_tolerance_m": 0.05, "step_m": 0.01, "workspace_bounds": [0.0, 1.4, -0.6, 0.6], "clearance_m": 0.02}


def _obj(label, x, y, z=0.05, h=0.1):
    return {"semantic_label": label, "centroid": [0, 0, 1], "fused_confidence": 0.8,
            "box_map": {"center": [x, y, z], "dimensions": [0.08, h, 0.08]}}


def _events(t):
    return [(e["event"], e["persistent_id"]) for e in t.events]


# ---------------------------------------------------------------- assignment
def test_hungarian_matches_brute_force():
    rng = np.random.default_rng(0)
    for _ in range(100):
        n, m = (int(x) for x in rng.integers(1, 6, 2))
        C = rng.random((n, m))
        r, c = linear_sum_assignment(C)
        k = min(n, m)
        best = min(sum(C[i, j] for i, j in (zip(range(n), p) if n <= m else zip(p, range(m))))
                   for p in itertools.permutations(range(max(n, m)), k))
        assert len(r) == k and C[r, c].sum() == pytest.approx(best)


# ---------------------------------------------------------------- tracker
def test_ids_and_appeared_events():
    t = MultiTermTracker()
    objs = t.update([_obj("mug", 0.5, 0.0), _obj("book", 0.7, -0.2)], 0.0)
    assert [o["persistent_id"] for o in objs] == ["mug_01", "book_01"]
    assert _events(t) == [("APPEARED", "mug_01"), ("APPEARED", "book_01")]


def test_occlusion_then_reappear_keeps_id():
    t = MultiTermTracker(max_missed_frames=5)
    t.update([_obj("book", 0.7, -0.2)], 0)
    t.update([], 1)
    assert _events(t) == [("OCCLUDED", "book_01")] and t.tracks[0].state == "occluded"
    for k in range(2, 5):
        t.update([], k)
    assert t.tracks[0].confidence < 0.8 * 0.85 ** 3   # decays while hidden
    assert t.update([_obj("book", 0.705, -0.2)], 5)[0]["persistent_id"] == "book_01"
    assert ("REAPPEARED", "book_01") in _events(t)


def test_track_removed_after_ttl():
    t = MultiTermTracker(max_missed_frames=2)
    t.update([_obj("book", 0.7, -0.2)], 0)
    for k in range(1, 4):
        t.update([], k)
    assert not t.tracks and any(e["event"] == "REMOVED" for e in t.event_log)


def test_relocated_object_is_reidentified_and_moved():
    t = MultiTermTracker()
    t.update([_obj("mug", 0.5, 0.0)], 0)
    t.update([], 1)                                   # picked up, out of view
    o = t.update([_obj("mug", 0.8, 0.0)], 2)          # put down 30 cm away (beyond the 15 cm gate)
    assert o[0]["persistent_id"] == "mug_01"
    kinds = [k for k, _ in _events(t)]
    assert kinds[:2] == ["REAPPEARED", "MOVED"] and t.event_log[-2]["distance_m"] == pytest.approx(0.3, abs=1e-3)


def test_pick_up_and_place_events():
    t = MultiTermTracker(desk_top_z=0.0)
    t.update([_obj("mug", 0.5, 0.0)], 0)
    t.update([_obj("mug", 0.5, 0.0, z=0.15)], 1)       # bottom at 10 cm above the desk
    assert ("PICKED_UP", "mug_01") in _events(t)
    t.update([_obj("mug", 0.55, 0.0)], 2)
    assert ("PLACED_ON", "mug_01") in _events(t)


def test_crossing_same_labels_keeps_ids():
    t = MultiTermTracker()
    ids = []
    for k in range(11):
        x = 0.8 * k / 10
        objs = t.update([_obj("mug", 0.40 + x, -0.115), _obj("mug", 1.20 - x, -0.085)], k)
        ids.append([o["persistent_id"] for o in objs])
    assert all(i == ids[0] for i in ids)


def test_history_and_state_export():
    t = MultiTermTracker()
    for k in range(3):
        t.update([_obj("mug", 0.5 + 0.01 * k, 0.0)], float(k))
    assert len(t.history("mug_01")) == 3
    s = t.state(2.0)
    assert s["schema_version"].startswith("s6-track-state") and s["tracks"][0]["state"] == "observed"


# ---------------------------------------------------------------- ActionGoal v2
def _verified(target_id):
    return {"target_id": target_id, "verification_status": True}


def test_reason_codes():
    assert build_action_goal({"target_id": None, "verification_status": False}, S4_GRAPH, CFG)["reason_code"] == "TARGET_UNVERIFIED"
    assert build_action_goal(_verified("ghost_9"), S4_GRAPH, CFG)["reason_code"] == "TARGET_NOT_IN_GRAPH"
    ok = build_action_goal(_verified("mug_0"), S4_GRAPH, CFG)
    assert ok["reason_code"] == "OK" and ok["validated"] and len(ok["path"]) == 2
    near = build_action_goal(_verified("glass_0"), S4_GRAPH, CFG)       # glass is within 3 cm of the laptop
    assert near["reason_code"] == "TARGET_IN_EXCLUSION_ZONE" and not near["validated"]
    blocked = build_action_goal(_verified("glass_0"), _glass_behind_laptop(), CFG)
    assert blocked["reason_code"] == "PATH_BLOCKED" and not blocked["validated"]
    assert not contracts.check_action_goal(ok) and not contracts.check_action_goal(blocked)


def _glass_behind_laptop():
    g = json.loads(json.dumps(S4_GRAPH))
    next(n for n in g["nodes"] if n["id"] == "glass_0")["pose_map"][:2] = [0.75, 0.45]
    return g


def test_occluded_target_is_rejected():
    g = json.loads(json.dumps(S4_GRAPH))
    next(n for n in g["nodes"] if n["id"] == "mug_0")["state"] = "occluded"
    assert build_action_goal(_verified("mug_0"), g, CFG)["reason_code"] == "TARGET_OCCLUDED"


def test_low_confidence_target_gets_a_warning():
    goal = build_action_goal(_verified("mug_0"), S4_GRAPH, {**CFG, "min_target_confidence": 1.01})
    assert goal["validated"] and goal["warnings"][0].startswith("LOW_TARGET_CONFIDENCE")


def test_detour_planner_goes_around_the_laptop():
    g = _glass_behind_laptop()
    goal = build_action_goal(_verified("glass_0"), g, {**CFG, "planner": "detour"})
    assert goal["validated"] and goal["reason_code"] == "OK_DETOUR" and len(goal["path"]) >= 3
    assert goal["clearance_m"] >= CFG["clearance_m"] - 0.011       # one grid cell of tolerance
    sim = simulate(goal, g, CFG)
    assert sim["success"] and sim["collisions"] == 0


# ---------------------------------------------------------------- W10-W11
def test_long_occlusion_reid_from_long_term_memory():
    t = MultiTermTracker(max_missed_frames=3, long_memory_frames=50)
    t.update([_obj("book", 0.7, -0.2)], 0)
    for k in range(1, 21):                               # hidden 20 frames, far beyond the TTL of 3
        t.update([], k)
    assert not t.tracks and t.lost
    o = t.update([_obj("book", 0.72, -0.2)], 21)
    assert o[0]["persistent_id"] == "book_01"
    e = next(e for e in t.events if e["event"] == "REAPPEARED")
    assert e.get("from_long_memory")


def test_long_memory_respects_label_and_window():
    t = MultiTermTracker(max_missed_frames=2, long_memory_frames=5)
    t.update([_obj("book", 0.7, -0.2)], 0)
    for k in range(1, 12):
        t.update([], k)                                   # removed at frame 3, forgotten 5 frames later
    assert t.update([_obj("book", 0.7, -0.2)], 12)[0]["persistent_id"] == "book_02"
    t2 = MultiTermTracker(max_missed_frames=2)
    t2.update([_obj("book", 0.7, -0.2)], 0)
    for k in range(1, 6):
        t2.update([], k)
    assert t2.update([_obj("mug", 0.7, -0.2)], 6)[0]["persistent_id"] == "mug_01"   # another label never inherits


def test_reachability_report_when_blocked():
    g = _glass_behind_laptop()
    goal = build_action_goal(_verified("glass_0"), g, CFG)                 # straight planner: rejected ...
    assert goal["reason_code"] == "PATH_BLOCKED"
    r = goal["reachability"]
    assert r["straight_clear"] is False and r["detour_exists"] and r["detour_waypoints"] >= 1
    assert any(w.startswith("REACHABLE_BY_DETOUR") for w in goal["warnings"])      # ... but reachable by detour
    ok = build_action_goal(_verified("mug_0"), S4_GRAPH, CFG)
    assert ok["reachability"] == {"straight_clear": True}

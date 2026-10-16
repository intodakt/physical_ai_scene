import copy
import json
from pathlib import Path

import pytest

from src.scene_graph import SceneGraphEngine, load_objects, rules

MOCK = Path(__file__).resolve().parents[1] / "data/mock/s2_frame_000_objects.json"


def box(center, size, cam_x=0.0, yaw=0.0):
    return {"center": center, "size": size, "yaw": yaw, "cam_x": cam_x}


def edges(graph, pred=None, active=True):
    return {(e["source"], e["predicate"], e["target"]) for e in graph["edges"]
            if (pred is None or e["predicate"] == pred) and (not active or e["end_time"] is None)}


def test_near_uses_euclidean_distance_and_reports_it():
    ok, ev = rules.check_near(box([0, 0, 0], [.1] * 3), box([0.2, 0, 0], [.1] * 3))
    assert ok and ev["distance_m"] == pytest.approx(0.2)
    assert not rules.check_near(box([0, 0, 0], [.1] * 3), box([0.4, 0, 0], [.1] * 3))[0]


def test_on_requires_contact_and_overlap():
    desk = box([0, 0, -0.02], [1, 1, 0.04])
    ok, ev = rules.check_on(box([0, 0, 0.05], [.1, .1, .1]), desk)       # bottom 0.0, desk top 0.0
    assert ok and ev["xy_overlap"] == 1.0
    assert not rules.check_on(box([0, 0, 0.30], [.1, .1, .1]), desk)[0]   # floating 25 cm up
    assert not rules.check_on(box([2.0, 0, 0.05], [.1, .1, .1]), desk)[0]  # beside the desk
    assert not rules.check_on(desk, box([0, 0, 0.05], [.1, .1, .1]))[0]    # not the other way round


def test_left_of_has_a_noise_margin():
    assert rules.check_left_of(box([0] * 3, [.1] * 3, cam_x=-0.2), box([0] * 3, [.1] * 3, cam_x=0.2))[0]
    assert not rules.check_left_of(box([0] * 3, [.1] * 3, cam_x=0.0), box([0] * 3, [.1] * 3, cam_x=0.02))[0]


def test_mock_frame_everything_is_on_the_desk():
    g = SceneGraphEngine().update(load_objects(MOCK)).export()
    assert {n["id"] for n in g["nodes"]} == {"desk_01", "laptop_0", "mug_0", "book_0", "multimeter_0", "glass_0"}
    assert edges(g, "on") == {(o, "on", "desk_01") for o in ("laptop_0", "mug_0", "book_0", "multimeter_0", "glass_0")}
    assert not any("desk_01" in (s, t) for s, p, t in edges(g) if p != "on")


def test_export_matches_s5_contract():
    g = SceneGraphEngine().update(load_objects(MOCK)).export()
    assert {"schema_version", "frame", "units", "size_order", "timestamp", "nodes", "edges"} <= set(g)
    assert g["frame"] == "map" and g["size_order"] == "[width_x, depth_y, height_z]"
    for n in g["nodes"]:
        assert {"id", "persistent_object_id", "names", "pose_map", "size", "state", "first_seen", "last_seen",
                "confidence", "depth_confidence"} <= set(n)
        assert len(n["pose_map"]) == 3 and len(n["size"]) == 3
    for e in g["edges"]:
        assert {"source", "predicate", "target", "relation_type", "evidence", "confidence",
                "start_time", "end_time"} <= set(e)
        assert e["evidence"], "every edge needs metric evidence"
    json.dumps(g)


def test_size_is_reordered_to_width_depth_height():
    frame = load_objects(MOCK)
    mug = next(o for o in frame["objects"] if o["object_id"] == "mug_0")
    w, h, d = mug["box_map"]["dimensions"]
    node = next(n for n in SceneGraphEngine().update(frame).export()["nodes"] if n["id"] == "mug_0")
    assert node["size"] == [pytest.approx(w, abs=1e-4), pytest.approx(d, abs=1e-4), pytest.approx(h, abs=1e-4)]


def test_moving_object_updates_node_and_closes_old_edge():
    frame = load_objects(MOCK)
    eng = SceneGraphEngine().update(frame)
    first = next(n for n in eng.export()["nodes"] if n["id"] == "mug_0")["first_seen"]

    moved = copy.deepcopy(frame)
    moved["timestamp"] += 1.0
    mug = next(o for o in moved["objects"] if o["object_id"] == "mug_0")
    mug["box_map"]["center"][2] += 0.4                         # lifted off the desk
    g = eng.update(moved).export()

    assert len([n for n in g["nodes"] if n["id"] == "mug_0"]) == 1
    node = next(n for n in g["nodes"] if n["id"] == "mug_0")
    assert node["first_seen"] == first and node["last_seen"] == moved["timestamp"]
    assert ("mug_0", "on", "desk_01") not in edges(g)
    old = next(e for e in g["edges"] if (e["source"], e["predicate"], e["target"]) == ("mug_0", "on", "desk_01"))
    assert old["end_time"] == moved["timestamp"]


def test_hidden_object_is_kept_as_occluded():
    frame = load_objects(MOCK)
    eng = SceneGraphEngine().update(frame)
    hidden = copy.deepcopy(frame)
    hidden["objects"] = [o for o in hidden["objects"] if o["object_id"] != "glass_0"]
    g = eng.update(hidden).export()
    assert next(n for n in g["nodes"] if n["id"] == "glass_0")["state"] == "occluded"
    assert ("glass_0", "on", "desk_01") in edges(g)            # not disproved, only unseen


def test_persistent_id_wins_over_object_id():
    frame = load_objects(MOCK)
    frame["objects"][1]["persistent_id"] = "mug_01"
    ids = {n["id"] for n in SceneGraphEngine().update(frame).export()["nodes"]}
    assert "mug_01" in ids and "mug_0" not in ids


def _tilt(frame, deg):
    """Simulate a wrong map TF: rotate every map-frame point about y by `deg` (desk tilts in the map)."""
    import math
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    rot = lambda p: [c * p[0] + s * p[2], p[1], -s * p[0] + c * p[2]]
    out = copy.deepcopy(frame)
    for o in out["objects"]:
        o["box_map"]["center"] = rot(o["box_map"]["center"])
    # plane (z_map = 0 in the original map) expressed through the tilted map: n_map -> rot(n_map)
    import numpy as np
    T = np.array(frame["T_map_camera"], float)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    T2 = T.copy(); T2[:3] = R @ T[:3]
    out["T_map_camera"] = T2.tolist()
    return out


def test_desk_alignment_survives_a_wrong_map_tf():
    frame = load_objects(MOCK)
    expected = edges(SceneGraphEngine().update(frame).export(), "on")
    assert len(expected) == 5
    tilted = _tilt(frame, 24.0)
    naive = SceneGraphEngine(use_support_plane=False).update(tilted).export()
    assert not edges(naive, "on")                                  # z = 0 assumption breaks
    g = SceneGraphEngine().update(tilted).export()
    assert edges(g, "on") == expected
    assert g["desk_alignment"]["method"] == "support_plane"


REAL = Path(__file__).resolve().parents[1] / "data/real"


def test_real_bag_frames_everything_on_desk_despite_placeholder_tf():
    """S2 output from S1_static_bag (S3 prompts tuned by hand). The bag's map TF is a placeholder:
    the desk is tilted ~22 deg in `map`, so only the support-plane alignment makes `on` work."""
    eng = SceneGraphEngine()
    for f in ("060", "130", "200"):
        g = eng.update(load_objects(REAL / f"s2_frame_{f}_objects.json")).export()
    assert g["desk_alignment"]["method"] == "support_plane" and g["desk_alignment"]["desk_tilt_in_map_deg"] > 10
    objs = {n["id"] for n in g["nodes"]} - {"desk_01"}
    assert len(objs) == 8
    assert {s for s, p, t in edges(g, "on") if t == "desk_01"} == objs
    assert not edges(SceneGraphEngine(use_support_plane=False).update(
        load_objects(REAL / "s2_frame_130_objects.json")).export(), "on")

"""S7 integration tests: offline parser, S6 placeholder, contracts, gatekeeper and the full pipeline."""

import copy
import json
import math

import pytest

from src.integration import contracts, rule_parser, s5_adapter
from src.integration.s6_placeholder import CentroidTracker, build_action_goal, footprint_polygon, simulate

S4_GRAPH = json.loads(open("outputs/scene_graph/frame_000_scene_graph.json", encoding="utf-8").read())
ACTION_CFG = {"agent_start": [0.25, 0.0], "exclusion_labels": ["laptop"], "exclusion_margin_m": 0.03,
              "reach_tolerance_m": 0.05, "step_m": 0.01}


# ---------------------------------------------------------------- offline parser (S5 stand-in)
@pytest.mark.parametrize("q, target, reference, negatives, positives", [
    ("Where is the red mug?", "mug", "", [], ["red"]),
    ("What is closest to the laptop?", "", "laptop", [], []),
    ("Which free chair is closest to the lidar scanner?", "chair", "lidar scanner", [], ["free"]),
    ("Find a cup that is not near the laptop", "cup", "", [{"relation": "near", "object": "laptop"}], []),
    ("Find a book far from the mug", "book", "", [{"relation": "near", "object": "mug"}], []),
    ("Go to the glass", "glass", "", [], []),
])
def test_rule_parser_matches_s5_schema(q, target, reference, negatives, positives):
    p = rule_parser.parse_query(q)
    assert set(p) == {"intent", "target", "reference", "relations", "positive_constraints", "negative_constraints"}
    assert (p["target"], p["reference"], p["negative_constraints"], p["positive_constraints"]) == \
        (target, reference, negatives, positives)


def test_s5_runs_on_s4_graph():
    r = s5_adapter.answer("Find a cup that is not near the laptop", S4_GRAPH, "rules")
    assert r["verification_status"] and r["target_id"] == "mug_0"
    assert not contracts.check_reasoning_result(r)


def test_s5_refuses_objects_not_in_graph():
    r = s5_adapter.answer("Which chair is closest to the laptop?", S4_GRAPH, "rules")
    assert r["target_id"] is None and r["final_answer"].startswith("Cannot determine")


# ---------------------------------------------------------------- S6 placeholder: tracking
def _obj(label, x, y):
    return {"semantic_label": label, "centroid": [0, 0, 1], "box_map": {"center": [x, y, 0.05]}}


def test_tracker_keeps_id_inside_gate_and_splits_outside():
    t = CentroidTracker(gate_m=0.15)
    a = t.update([_obj("mug", 0.5, 0.0), _obj("book", 0.7, -0.2)])
    assert [o["persistent_id"] for o in a] == ["mug_01", "book_01"]
    b = t.update([_obj("mug", 0.5, 0.13)])            # moved 13 cm -> same mug
    assert b[0]["persistent_id"] == "mug_01"
    c = t.update([_obj("mug", 0.5, 0.40)])            # jumped 27 cm -> new object
    assert c[0]["persistent_id"] == "mug_02"


def test_tracker_remembers_hidden_objects():
    t = CentroidTracker(gate_m=0.15, max_missed_frames=3)
    t.update([_obj("book", 0.7, -0.2)])
    for _ in range(3):
        t.update([])                                   # hidden for 3 frames
    assert t.update([_obj("book", 0.71, -0.2)])[0]["persistent_id"] == "book_01"


# ---------------------------------------------------------------- S6 placeholder: action
def _verified(target_id):
    return {"target_id": target_id, "verification_status": True}


def test_goal_through_laptop_zone_is_rejected():
    goal = build_action_goal(_verified("glass_0"), S4_GRAPH, ACTION_CFG)
    assert goal["validated"] is False and "laptop_0" in goal["reason"]
    assert not contracts.check_action_goal(goal)
    assert simulate(goal, S4_GRAPH, ACTION_CFG)["executed"] is False


def test_clear_goal_is_accepted_and_reached():
    goal = build_action_goal(_verified("mug_0"), S4_GRAPH, ACTION_CFG)
    assert goal["validated"] and len(goal["target_pose"]) == 3
    sim = simulate(goal, S4_GRAPH, ACTION_CFG)
    assert sim["success"] and sim["collisions"] == 0


def test_unverified_answer_gives_no_goal():
    goal = build_action_goal({"target_id": None, "verification_status": False}, S4_GRAPH, ACTION_CFG)
    assert goal["validated"] is False and goal["target_pose"] is None


def test_zone_is_rotated_with_s4_yaw():
    laptop = next(n for n in S4_GRAPH["nodes"] if n["id"] == "laptop_0")
    poly = footprint_polygon({**laptop, "yaw": math.pi / 2})       # quarter turn swaps the x/y extents
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    assert max(xs) - min(xs) == pytest.approx(laptop["size"][1], abs=1e-3)
    assert max(ys) - min(ys) == pytest.approx(laptop["size"][0], abs=1e-3)


def test_zone_without_yaw_is_conservative_square():
    laptop = {k: v for k, v in next(n for n in S4_GRAPH["nodes"] if n["id"] == "laptop_0").items() if k != "yaw"}
    xs = [p[0] for p in footprint_polygon(laptop)]
    assert max(xs) - min(xs) == pytest.approx(max(laptop["size"][:2]), abs=1e-3)


# ---------------------------------------------------------------- contracts / gatekeeper
def test_contract_checks_accept_team_files():
    s2 = json.loads(open("outputs/fusion_3d/frame_000_objects.json", encoding="utf-8").read())
    obs = json.loads(open("data/mock/frame_000/observation.json", encoding="utf-8").read())
    assert contracts.detect_kind(s2) == "objects" and not contracts.check_objects(s2)
    assert contracts.detect_kind(obs) == "observation" and not contracts.check_semantic_observation(obs)
    assert contracts.detect_kind(S4_GRAPH) == "scene_graph" and not contracts.check_scene_graph(S4_GRAPH)


def test_contract_checks_catch_broken_files():
    g = copy.deepcopy(S4_GRAPH)
    g["edges"][0]["target"] = "ghost_9"
    g["nodes"][1]["pose_map"] = [0.1, float("nan"), 0.2]
    errs = contracts.check_scene_graph(g)
    assert any("ghost_9" in e for e in errs) and any("pose_map" in e for e in errs)
    assert contracts.check_reasoning_result({"target_id": "mug_0", "verification_status": False,
                                             "computed_facts": "", "final_answer": "", "confidence": 0,
                                             "warnings": []})


def test_gatekeeper_flags_absolute_paths(tmp_path, monkeypatch):
    import tools.check_contracts as gk

    bad = tmp_path / "bad.py"
    home = "/home"                                     # split so this test file passes the gatekeeper itself
    bad.write_text(f'DATA = "{home}/student/desk/rgb.png"\nOK = "data/mock/rgb.png"\n')
    monkeypatch.setattr(gk, "ROOT", tmp_path)
    problems = gk.check([str(bad)])
    assert len(problems) == 1 and "bad.py:1" in problems[0]


# ---------------------------------------------------------------- whole pipeline
@pytest.fixture(scope="module")
def run_result(tmp_path_factory):
    from main_pipeline import run
    from scripts.make_demo_sequence import generate

    tmp = tmp_path_factory.mktemp("s7")
    generate(tmp / "frames", n_frames=7)
    return run(frames=tmp / "frames", query="Go to the mug", out=str(tmp / "out"), parser="rules", quiet=True)


def test_pipeline_end_to_end_produces_action_goal(run_result):
    pipe, summary = run_result
    assert summary["n_frames"] == 7 and not summary["contract_errors"]
    goal = summary["last_query"]["action_goal"]
    assert goal["target_object_id"] == "mug_01" and goal["validated"]


def test_pipeline_tracks_ids_and_occlusion(run_result):
    pipe, summary = run_result
    ids = [set(f["ids"].values()) for f in summary["frames"]]
    assert "book_01" in ids[0] and "book_01" not in ids[4] and "book_01" in ids[6]   # hidden, then back
    assert all("mug_01" in s for s in ids)                                          # mug keeps its ID
    assert not any(pid.endswith("_02") for s in ids for pid in s)


def test_pipeline_graph_changes_over_time(run_result):
    pipe, _ = run_result
    near = {(e["source"], e["target"]) for e in pipe.graph["edges"] if e["predicate"] == "near" and e["end_time"] is None}
    assert ("laptop_01", "mug_01") in near          # the mug slid next to the laptop
    r = pipe.ask("Find a cup that is not near the laptop")
    assert r["reasoning_result"]["target_id"] is None   # so no cup qualifies any more

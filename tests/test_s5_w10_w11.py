"""S5 W10-W11: propose -> verify -> correct loop, on / under / inside questions, temporal "where before?" questions."""

import pytest

from src.integration import contracts, s5_adapter
from src.scene_graph import SceneGraphEngine


def _frame(objs, ts):
    return {"timestamp": ts, "objects": [{"object_id": i, "persistent_id": i, "semantic_label": i.split("_")[0],
             "label_candidates": [i.split("_")[0]], "detector_score": 0.9, "fused_confidence": 0.8, "depth_confidence": 0.9,
             "centroid": [0, 0, 1], "box_map": {"center": c, "dimensions": [s[0], s[2], s[1]], "yaw": 0.0}} for i, c, s in objs]}


DESK = [("cup_01", [0.5, 0.0, 0.05], [0.08, 0.08, 0.10]), ("pen_01", [0.5, 0.0, 0.07], [0.012, 0.012, 0.14]),
        ("shelf_01", [0.8, 0.2, 0.25], [0.4, 0.3, 0.02]), ("box_01", [0.8, 0.2, 0.03], [0.1, 0.1, 0.06]),
        ("laptop_01", [0.7, -0.25, 0.01], [0.32, 0.22, 0.02])]


@pytest.fixture
def graph():
    eng = SceneGraphEngine(use_support_plane=False)
    eng.update(_frame(DESK, 1.0))
    moved = [o if o[0] != "cup_01" else ("cup_01", [0.3, 0.1, 0.05], o[2]) for o in DESK if o[0] != "pen_01"]
    moved.append(("pen_01", [0.3, 0.1, 0.07], [0.012, 0.012, 0.14]))       # the cup is moved with the pen in it
    eng.update(_frame(moved, 2.0))
    return eng.export()


def test_inside_and_under_questions(graph):
    r = s5_adapter.answer("Which pen is inside the cup?", graph, "rules")
    assert r["verification_status"] and r["target_id"] == "pen_01" and "xy_overlap" in r["computed_facts"]
    r = s5_adapter.answer("What is under the shelf?", graph, "rules")
    assert r["target_id"] == "box_01"
    r = s5_adapter.answer("What is under the laptop?", graph, "rules")
    assert r["target_id"] is None and r["final_answer"].startswith("Cannot determine")
    assert not contracts.check_reasoning_result(r)


def test_where_before(graph):
    r = s5_adapter.answer("Where was the cup before?", graph, "rules")
    assert r["verification_status"] and r["target_id"] == "cup_01"
    assert "x=0.50" in r["final_answer"] and "moved" in r["final_answer"]
    r = s5_adapter.answer("Where was the shelf before?", graph, "rules")
    assert "has not moved" in r["final_answer"]
    r = s5_adapter.answer("Where was the stapler before?", graph, "rules")
    assert r["target_id"] is None                                     # unknown objects are still refused


def test_correction_loop_swaps_a_wrong_parse(graph, monkeypatch):
    s5 = s5_adapter._load_s5()
    bad = {"intent": "find_object", "target": "cup", "reference": "pen", "relations": ["inside"],
           "positive_constraints": [], "negative_constraints": []}            # the LLM swapped the two objects
    monkeypatch.setattr(s5, "load_graph", lambda *a, **k: graph)
    monkeypatch.setattr(s5, "parse_query", lambda q, feedback=None: dict(bad))
    r = s5.answer_question("Which pen is inside the cup?")
    assert r["verification_status"] and r["target_id"] == "pen_01"
    assert len(r["verification_rounds"]) >= 2 and r["verification_rounds"][0]["verified"] is False
    assert any(w.startswith("Corrected after verification") for w in r["warnings"])


def test_correction_never_invents_objects(graph, monkeypatch):
    s5 = s5_adapter._load_s5()
    first = {"intent": "find_object", "target": "stapler", "reference": "", "relations": [],
             "positive_constraints": [], "negative_constraints": []}
    hallucinated = dict(first, target="box")                               # "corrected" to an object not in the question
    monkeypatch.setattr(s5, "load_graph", lambda *a, **k: graph)
    monkeypatch.setattr(s5, "parse_query", lambda q, feedback=None: dict(hallucinated if feedback else first))
    r = s5.answer_question("Where is the red stapler?")
    assert r["target_id"] is None and r["verification_rounds"][1]["facts"].startswith("rejected")


def test_feedback_reaches_the_llm(graph, monkeypatch):
    s5 = s5_adapter._load_s5()
    seen = []

    def parser(q, feedback=None):
        seen.append(feedback)
        if feedback:
            return {"intent": "find_object", "target": "pen", "reference": "cup", "relations": ["inside"],
                    "positive_constraints": [], "negative_constraints": []}
        return {"intent": "find_object", "target": "", "reference": "", "relations": [], "positive_constraints": [],
                "negative_constraints": []}

    monkeypatch.setattr(s5, "load_graph", lambda *a, **k: graph)
    monkeypatch.setattr(s5, "parse_query", parser)
    r = s5.answer_question("Which pen is inside the cup?")
    assert r["target_id"] == "pen_01" and seen[1] and "Objects in the scene" in seen[1]

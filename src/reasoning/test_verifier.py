"""Unit tests for verifier.py and the parser clean-up (no running LLM needed). Run: python3 test_verifier.py"""

import sys
from pathlib import Path

from query_parser import _normalize
from verifier import filter_not_near, find_closest, find_nodes_by_name, has_edge, load_graph, locate

graph = load_graph(Path(__file__).parent / "sample_scene_graph.json")


def test_closest_free_chair():
    r = find_closest(graph, "scanner", "chair", only_free=True)
    assert r["verification_status"] and r["target_id"] == "chair_04"
    assert "0.65m" in r["computed_facts"]


def test_free_filter_skips_occupied_chair():
    assert find_closest(graph, "person", "chair")["target_id"] == "chair_02"
    assert find_closest(graph, "person", "chair", only_free=True)["target_id"] == "chair_01"


def test_wrong_llm_guess_is_corrected():
    guess = "chair_02"
    assert find_closest(graph, "scanner", "chair", only_free=True)["target_id"] != guess


def test_not_near_laptop():
    r = filter_not_near(graph, "chair", "laptop")
    assert r["verification_status"] and r["target_id"].startswith("chair")


def test_all_candidates_blocked():
    r = filter_not_near(graph, "mug", "laptop")
    assert not r["verification_status"] and r["target_id"] is None


def test_object_is_never_compared_with_itself():
    r = filter_not_near(graph, "cup", "cup")
    assert not r["verification_status"]


def test_normalize_fixes_small_model_slips():
    slip = {"target": "cup", "reference": "laptop", "relations": [], "positive_constraints": [{"red": True}],
            "negative_constraints": [{"relation": "near", "object": "cup"}]}
    fixed = _normalize(slip)
    assert fixed["negative_constraints"][0]["object"] == "laptop" and fixed["reference"] == ""
    assert fixed["positive_constraints"] == ["red"]
    fixed = _normalize({"target": "chair", "reference": "laptop", "relations": ["not_near"]})
    assert fixed["negative_constraints"][0]["object"] == "laptop" and fixed["relations"] == []


def test_ended_edges_are_ignored():
    assert not has_edge(graph, "mug_01", "left_of", "laptop_01")
    assert has_edge(graph, "laptop_01", "left_of", "mug_01")


def test_locate_object():
    r = locate(graph, "mug")
    assert r["target_id"] == "mug_01" and "desk_01" in r["computed_facts"]


def test_unknown_object_is_not_guessed():
    assert not find_closest(graph, "banana", "chair")["verification_status"]
    assert not locate(graph, "banana")["verification_status"]


def test_occluded_object_gives_warning():
    assert locate(graph, "pen")["warnings"]


def test_name_match_uses_words_not_substrings():
    assert [n["id"] for n in find_nodes_by_name(graph, "book")] == ["book_01"]
    assert find_nodes_by_name(graph, "red mug")[0]["id"] == "mug_01"
    assert find_nodes_by_name(graph, "chairs")[0]["id"].startswith("chair")


def test_not_on_desk_checks_on_edges():
    r = filter_not_near(graph, "book", [{"relation": "on", "object": "desk"}])
    assert not r["verification_status"]


def test_closest_and_not_near_together():
    r = find_closest(graph, "scanner", "chair", only_free=True, negatives=[{"relation": "near", "object": "laptop"}])
    assert r["target_id"] == "chair_04"


def test_near_uses_distance_when_edge_is_missing():
    no_near = dict(graph, edges=[e for e in graph["edges"] if e["predicate"] != "near"])
    assert not filter_not_near(no_near, "mug", "laptop")["verification_status"]


def test_normalize_handles_strings_instead_of_lists():
    fixed = _normalize({"target": "mug", "reference": "", "relations": "closest_to",
                        "positive_constraints": "red", "negative_constraints": [{"near": "laptop"}]})
    assert fixed["relations"] == ["closest_to"] and fixed["positive_constraints"] == ["red"]
    assert fixed["negative_constraints"] == [{"relation": "near", "object": "laptop"}]
    fixed = _normalize({"target": "chair", "reference": "laptop", "relations": [],
                        "negative_constraints": [{"relation": "near", "object": "laptop"}]})
    assert fixed["reference"] == ""


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError:
                failed += 1
                print(f"FAIL {name}")
    sys.exit(1 if failed else 0)

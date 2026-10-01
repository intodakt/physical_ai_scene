"""
S5 - Geometry Verifier
-----------------------
This is the "anti-hallucination" layer. It never trusts the LLM's answer
blindly - it always re-checks it against the real 3D positions stored in
the Scene Graph JSON (produced by S4).

While S4's real graph isn't ready yet, this script reads
sample_scene_graph.json (the fake/example data) so S5's logic can be
built and tested independently.
"""

import json
import math
from pathlib import Path

GRAPH_PATH = Path(__file__).parent / "sample_scene_graph.json"


def load_graph(path: Path = GRAPH_PATH) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def find_nodes_by_name(graph: dict, text: str) -> list[dict]:
    """Find every node whose names (or synonyms) contain the given text."""
    text = text.lower().strip()
    matches = []
    for node in graph["nodes"]:
        for name_entry in node["names"]:
            if text in name_entry["text"].lower():
                matches.append(node)
                break
    return matches


def distance(a: dict, b: dict) -> float:
    """Straight-line (Euclidean) 3D distance between two node centroids."""
    ax, ay, az = a["pose_map"]
    bx, by, bz = b["pose_map"]
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)


def has_edge(graph: dict, source_id: str, predicate: str, target_id: str) -> bool:
    for edge in graph.get("edges", []):
        if edge["source"] == source_id and edge["predicate"] == predicate and edge["target"] == target_id:
            return True
    return False


def find_closest(graph: dict, reference_text: str, target_text: str,
                  only_free: bool = False) -> dict:
    """
    Core verifier function: given a reference object (e.g. "mug") and a
    target object class (e.g. "chair"), compute the REAL closest match
    using geometry - not an LLM guess.
    """
    references = find_nodes_by_name(graph, reference_text)
    if not references:
        return {
            "target_id": None,
            "computed_facts": f"No node found matching reference '{reference_text}'",
            "verification_status": False,
            "final_answer": "Cannot determine: reference object not found in the scene graph.",
        }
    reference = references[0]

    candidates = find_nodes_by_name(graph, target_text)
    if only_free:
        candidates = [c for c in candidates if c.get("state") == "free"]

    if not candidates:
        return {
            "target_id": None,
            "computed_facts": f"No candidates found matching '{target_text}'",
            "verification_status": False,
            "final_answer": "Cannot determine: no matching target objects in the scene graph.",
        }

    scored = [(c, distance(reference, c)) for c in candidates]
    scored.sort(key=lambda pair: pair[1])
    best_node, best_dist = scored[0]

    return {
        "target_id": best_node["id"],
        "computed_facts": f"distance to {reference['id']}: {best_dist:.2f}m",
        "verification_status": True,
        "final_answer": (
            f"The closest {target_text} to the {reference_text} is "
            f"{best_node['id']}, verified at {best_dist:.2f} meters."
        ),
    }


def filter_not_near(graph: dict, target_text: str, excluded_text: str) -> dict:
    """
    Handles negative-constraint questions like:
    'Find the chair that is NOT near the laptop.'
    """
    excluded_nodes = find_nodes_by_name(graph, excluded_text)
    candidates = find_nodes_by_name(graph, target_text)

    valid = []
    for c in candidates:
        blocked = any(
            has_edge(graph, c["id"], "near", ex["id"]) or has_edge(graph, ex["id"], "near", c["id"])
            for ex in excluded_nodes
        )
        if not blocked:
            valid.append(c)

    if not valid:
        return {
            "target_id": None,
            "computed_facts": f"All '{target_text}' candidates are near '{excluded_text}'",
            "verification_status": False,
            "final_answer": "Cannot determine: no valid object satisfies the constraint.",
        }

    chosen = valid[0]
    return {
        "target_id": chosen["id"],
        "computed_facts": f"'{chosen['id']}' has no 'near' edge to any '{excluded_text}' node",
        "verification_status": True,
        "final_answer": f"{chosen['id']} is a {target_text} that is NOT near the {excluded_text}.",
    }


if __name__ == "__main__":
    graph = load_graph()

    print("Test 1: closest chair to the mug")
    print(json.dumps(find_closest(graph, reference_text="mug", target_text="chair"), indent=2))

    print("\nTest 2: closest FREE chair to the lidar scanner")
    print(json.dumps(
        find_closest(graph, reference_text="scanner", target_text="chair", only_free=True),
        indent=2,
    ))

    print("\nTest 3: a chair that is NOT near the laptop")
    print(json.dumps(filter_not_near(graph, target_text="chair", excluded_text="laptop"), indent=2))

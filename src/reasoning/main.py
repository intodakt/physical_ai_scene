"""
S5 - Full Pipeline (Parser -> Verifier)
-----------------------------------------
Ties parser.py and verifier.py together: takes a plain-English question,
asks the local LLM to parse it, then verifies the LLM's intent against the
real geometry in the scene graph before returning a trusted answer.

Run:
    python main.py "Which free chair is closest to the lidar scanner?"
    python main.py "Find a chair that is not near the laptop"
"""

import json
import sys

from parser import parse_query
from verifier import load_graph, find_closest, filter_not_near


def answer_question(question: str) -> dict:
    graph = load_graph()
    parsed = parse_query(question)

    if "error" in parsed:
        return parsed

    target = parsed.get("target", "")
    reference = parsed.get("reference", "")
    negative_constraints = parsed.get("negative_constraints", [])

    # Very simple routing logic for now - Phase 3 negative-constraint handling
    # vs. Phase 2 closest-object handling. This gets smarter over time.
    if negative_constraints:
        # naive: assume the constraint names the excluded object, e.g. "near the laptop"
        excluded_text = negative_constraints[0].split("near")[-1].strip()
        result = filter_not_near(graph, target_text=target, excluded_text=excluded_text)
    else:
        only_free = "free" in question.lower()
        result = find_closest(graph, reference_text=reference, target_text=target, only_free=only_free)

    result["llm_parsed_query"] = parsed
    return result


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Which free chair is closest to the lidar scanner?"
    print(f"Question: {question}\n")
    print(json.dumps(answer_question(question), indent=2))

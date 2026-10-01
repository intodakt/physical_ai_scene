"""S5 pipeline: question -> local LLM parser -> geometry verifier -> verified answer (ReasoningResult).
Run: python3 main.py "Which free chair is closest to the lidar scanner?"   (short answer)
     python3 main.py --json "..."                                          (full ReasoningResult for S6)
"""

import json
import re
import sys

from query_parser import parse_query
from verifier import NEAR_WORDS, fail, filter_not_near, find_closest, load_graph, locate


def answer_question(question: str) -> dict:
    parsed = parse_query(question)
    if "error" in parsed:
        result = fail(parsed["error"], "the question could not be parsed.")
        result["llm_parsed_query"] = parsed
        return result

    graph = load_graph()
    target = parsed.get("target", "")
    reference = parsed.get("reference", "")
    negatives = parsed.get("negative_constraints", [])
    positives = [str(p).lower() for p in parsed.get("positive_constraints", [])]
    only_free = "free" in positives or re.search(r"\bfree\b", question.lower()) is not None

    if reference:
        result = find_closest(graph, reference, target, only_free, negatives)
    elif negatives:
        result = filter_not_near(graph, target, negatives, only_free)
    elif target:
        result = locate(graph, target)
    else:
        result = fail("no target or reference found", "the question is not clear.")

    unchecked = [p for p in positives if p != "free"]
    if unchecked and result["verification_status"]:
        result["warnings"].append(f"Could not verify: {', '.join(unchecked)} (not in scene graph data)")
    other_relations = [str(r) for r in parsed.get("relations", []) if reference and str(r).lower() not in NEAR_WORDS]
    if other_relations and result["verification_status"]:
        result["warnings"].append(f"Could not verify relation: {', '.join(other_relations)} (answer uses distance only)")
    result["llm_parsed_query"] = parsed
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    show_json = "--json" in args
    question = " ".join(a for a in args if a != "--json") or "Which free chair is closest to the lidar scanner?"
    result = answer_question(question)
    if show_json:
        print(f"Question: {question}\n")
        print(json.dumps(result, indent=2))
    else:
        print(result["final_answer"])
        for warning in result["warnings"]:
            print(f"  ! {warning}")

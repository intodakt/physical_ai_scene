"""S5 pipeline: question -> local LLM parser -> geometry verifier -> verified answer (ReasoningResult).
Run: python3 main.py "Which free chair is closest to the lidar scanner?"   (short answer)
     python3 main.py --json "..."                                          (full ReasoningResult for S6)
"""

import json
import re
import sys

from query_parser import parse_query
from verifier import (NEAR_WORDS, GraphError, fail, filter_not_near, find_closest, find_nodes_by_name, find_related,
                      graph_relation, load_graph, locate, where_before)

TEMPORAL = re.compile(r"\b(before|previously|earlier|used to be|where was|where were|originally)\b", re.IGNORECASE)
MAX_ROUNDS = 2       # propose -> verify -> (correct -> verify)


def _object_words(parsed):
    return [parsed.get("target", ""), parsed.get("reference", "")] + [str(n.get("object", "")) for n in parsed.get("negative_constraints", [])]


def _grounded(question, parsed):
    """A correction may only use object words that are in the question (no new objects invented)."""
    q = set(re.findall(r"[a-z0-9]+", question.lower()))
    return all(set(re.findall(r"[a-z0-9]+", w.lower())) <= q for w in _object_words(parsed) if w)


def _feedback(graph, parsed, result):
    names = sorted({n["names"][0]["text"] for n in graph["nodes"] if n.get("names")})
    return (f"Your JSON {json.dumps(parsed)} could not be verified: {result['computed_facts']}. "
            f"Objects in the scene: {', '.join(names)}. Re-read the question: put the object to find in \"target\" "
            f"and the object it is compared to in \"reference\". Use only words from the question. Reply with the JSON only.")


def _swap(parsed):
    if not parsed.get("target") or not parsed.get("reference"):
        return None
    out = dict(parsed, target=parsed["reference"], reference=parsed["target"])
    return out


def answer_question(question: str) -> dict:
    """Propose (LLM parse) -> verify (geometry on S4's graph) -> correct (re-ask with the verifier's reason, or swap
    target / reference) -> verify again. A correction is accepted only if it is verified and uses words from the
    question, so it can never invent an object; unknown objects are still refused."""
    parsed = parse_query(question)
    if "error" in parsed:
        result = fail(parsed["error"], "the question could not be parsed.")
        result["llm_parsed_query"] = parsed
        return result

    try:
        graph = load_graph()
    except GraphError as e:
        result = fail(str(e), "the scene graph from S4 is not available.")
        result["llm_parsed_query"] = parsed
        return result

    result = _verify(question, parsed, graph)
    rounds = [{"parsed": parsed, "verified": result["verification_status"], "facts": result["computed_facts"]}]
    if not result["verification_status"] and len(rounds) < MAX_ROUNDS:
        candidates = []
        try:
            again = parse_query(question, feedback=_feedback(graph, parsed, result))
            if "error" not in again and again != parsed:
                candidates.append(("re-asked the parser with the verifier's reason", again))
        except TypeError:                     # a parser without feedback support (offline rules parser)
            pass
        if _swap(parsed):
            candidates.append(("swapped target and reference", _swap(parsed)))
        for how, cand in candidates:
            if not _grounded(question, cand):
                rounds.append({"parsed": cand, "verified": False, "facts": "rejected: uses words not in the question"})
                continue
            second = _verify(question, cand, graph)
            rounds.append({"parsed": cand, "verified": second["verification_status"], "facts": second["computed_facts"]})
            if second["verification_status"]:
                second["warnings"].append(f"Corrected after verification ({how})")
                result, parsed = second, cand
                break
    result["llm_parsed_query"] = parsed
    result["verification_rounds"] = rounds
    return result


def _verify(question, parsed, graph):
    target = parsed.get("target", "")
    reference = parsed.get("reference", "")
    negatives = parsed.get("negative_constraints", [])
    positives = [str(p).lower() for p in parsed.get("positive_constraints", [])]
    only_free = "free" in positives or re.search(r"\bfree\b", question.lower()) is not None

    relation = next((graph_relation(r) for r in parsed.get("relations", []) if graph_relation(r)), None)
    if TEMPORAL.search(question) and (target or reference):
        result = where_before(graph, target or reference)
    elif reference and relation:
        result = find_related(graph, relation, reference, target)
    elif reference:
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
    other_relations = [str(r) for r in parsed.get("relations", [])
                       if reference and str(r).lower() not in NEAR_WORDS and not graph_relation(r)]
    if other_relations and result["verification_status"]:
        result["warnings"].append(f"Could not verify relation: {', '.join(other_relations)} (answer uses distance only)")
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

"""Geometry verifier (S5): answers spatial questions from the scene graph with real 3D math.
Input: scene graph JSON from S4 (path from S5_GRAPH, default sample_scene_graph.json).
Output: dict with target_id, computed_facts, verification_status, final_answer, confidence, warnings.
"""

import json
import math
import os
import re
import time
from pathlib import Path

GRAPH_PATH = Path(os.environ.get("S5_GRAPH", Path(__file__).parent / "sample_scene_graph.json"))
LOW_CONFIDENCE = 0.6
NEAR_THRESHOLD = 0.3  # meters, same rule as S4's "near" edges
NEAR_WORDS = {"near", "next_to", "close_to", "beside", "by", "nearby", "closest_to"}
GRAPH_RELATIONS = {"on": "on", "on_top_of": "on", "under": "under", "below": "under", "beneath": "under",
                   "inside": "inside", "in": "inside", "within": "inside", "left_of": "left_of"}


class GraphError(Exception):
    pass


def load_graph(path=GRAPH_PATH, tries=5):
    """Reads S4's graph file. S4 rewrites it every second, so a half-written file is retried."""
    error = None
    for _ in range(tries):
        try:
            with open(path) as f:
                graph = json.load(f)
            break
        except FileNotFoundError:
            raise GraphError(f"graph file not found: {path}") from None
        except json.JSONDecodeError as e:
            error = e
            time.sleep(0.1)
    else:
        raise GraphError(f"graph file is not valid JSON: {path} ({error})")
    if not isinstance(graph, dict) or not graph.get("nodes"):
        raise GraphError(f"graph file has no nodes: {path}")
    return graph


def _words(text):
    # word match, not substring: "book" must not match "notebook computer"; "chairs" -> "chair"
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", text.lower())]


def _name_score(node, query_words):
    scores = [n["score"] for n in node["names"] if set(query_words) <= set(_words(n["text"]))]
    return max(scores) if scores else 0.0


def find_nodes_by_name(graph, text):
    words = _words(text)
    if not words:
        return []
    for query in (words, words[-1:]):  # "red mug" -> fall back to the last word "mug"
        matches = [n for n in graph["nodes"] if _name_score(n, query) > 0]
        if matches:
            return sorted(matches, key=lambda n: (_name_score(n, query), _conf(n) or 0), reverse=True)
    return []


def _conf(node):
    """Node confidence as a number, or None when S4 sent no value."""
    value = node.get("confidence")
    return value if isinstance(value, (int, float)) else None


def distance(a, b):
    return math.dist(a["pose_map"], b["pose_map"])


def is_active(edge):
    return edge.get("end_time") is None


def has_edge(graph, source_id, predicate, target_id):
    return any(
        is_active(e) and e["source"] == source_id and e["predicate"] == predicate and e["target"] == target_id
        for e in graph.get("edges", [])
    )


def fail(facts, reason):
    return {
        "target_id": None,
        "computed_facts": facts,
        "verification_status": False,
        "final_answer": f"Cannot determine: {reason}",
        "confidence": 0.0,
        "warnings": [],
    }


def _warnings(*nodes):
    out = []
    for n in nodes:
        if n.get("state") == "occluded":
            out.append(f"{n['id']} is occluded (last seen {n.get('last_seen')})")
        if _conf(n) is None:
            out.append(f"{n['id']} has no confidence value")
        elif _conf(n) < LOW_CONFIDENCE:
            out.append(f"{n['id']} has low confidence ({_conf(n)})")
    return out


def _ok(target, facts, answer, nodes, extra_warnings=()):
    return {
        "target_id": target["id"],
        "computed_facts": facts,
        "verification_status": True,
        "final_answer": answer,
        "confidence": round(min((_conf(n) for n in nodes if _conf(n) is not None), default=0.0), 2),
        "warnings": _warnings(*nodes) + list(extra_warnings),
    }


def locate(graph, target_text):
    matches = find_nodes_by_name(graph, target_text)
    if not matches:
        return fail(f"no node matches '{target_text}'", f"'{target_text}' is not in the scene graph.")
    node = matches[0]
    x, y, z = node["pose_map"]
    support = next(
        (e["target"] for e in graph.get("edges", [])
         if is_active(e) and e["source"] == node["id"] and e["predicate"] == "on"),
        None,
    )
    place = f", on {support}" if support else ""
    extra = [f"{len(matches)} objects match '{target_text}', showing the most confident"] if len(matches) > 1 else []
    return _ok(
        node,
        f"pose_map: [{x:.2f}, {y:.2f}, {z:.2f}]{place}",
        f"The {target_text} is {node['id']} at x={x:.2f}, y={y:.2f}, z={z:.2f} m{place}.",
        [node],
        extra,
    )


def _relation_name(relation):
    relation = str(relation or "near").lower().strip().replace(" ", "_")
    return "near" if relation in NEAR_WORDS else relation


def _breaks_rule(graph, node, relation, others):
    for o in others:
        if relation == "near":
            if (has_edge(graph, node["id"], "near", o["id"]) or has_edge(graph, o["id"], "near", node["id"])
                    or distance(node, o) < NEAR_THRESHOLD):
                return True
        elif has_edge(graph, node["id"], relation, o["id"]):
            return True
    return False


def _apply_negatives(graph, candidates, negatives):
    """Drops candidates that break a 'NOT <relation> <object>' rule. Returns (candidates, facts, warnings, error)."""
    predicates = {e["predicate"] for e in graph.get("edges", [])}
    facts, warnings = [], []
    for neg in negatives:
        relation, text = _relation_name(neg.get("relation")), str(neg.get("object", ""))
        excluded = find_nodes_by_name(graph, text)
        if not excluded:
            return [], facts, warnings, fail(f"no node matches '{text}'", f"'{text}' is not in the scene graph.")
        ids = {e["id"] for e in excluded}
        before = len(candidates)
        candidates = [c for c in candidates if c["id"] not in ids]
        if before and not candidates:
            return [], facts, warnings, fail(f"target and '{text}' match the same object",
                                             "the question compares an object with itself.")
        if relation != "near" and relation not in predicates:
            warnings.append(f"Could not verify 'not {relation} {text}' (no '{relation}' edges in scene graph)")
            continue
        candidates = [c for c in candidates if not _breaks_rule(graph, c, relation, excluded)]
        facts.append(f"no active '{relation}' link to {', '.join(sorted(ids))}")
    return candidates, facts, warnings, None


def _as_negatives(negatives):
    return [{"relation": "near", "object": negatives}] if isinstance(negatives, str) else list(negatives)


def _rule_text(negatives):
    return " and ".join(f"NOT {_relation_name(n.get('relation')).replace('_', ' ')} the {n.get('object', '')}"
                        for n in negatives)


def find_closest(graph, reference_text, target_text="", only_free=False, negatives=()):
    refs = find_nodes_by_name(graph, reference_text)
    if not refs:
        return fail(f"no node matches reference '{reference_text}'", "the reference object is not in the scene graph.")
    ref = refs[0]
    # "what is closest to X?" compares real objects; virtual nodes (S4's desk plane) only when named
    pool = find_nodes_by_name(graph, target_text) if target_text else [n for n in graph["nodes"] if not n.get("virtual")]
    candidates = [c for c in pool if c["id"] != ref["id"]]
    if only_free:
        candidates = [c for c in candidates if c.get("state") == "free"]
    if not candidates:
        return fail(f"no candidates for '{target_text}'", "no matching objects in the scene graph.")

    negatives = _as_negatives(negatives)
    candidates, rule_facts, extra, error = _apply_negatives(graph, candidates, negatives)
    if error:
        return error
    if not candidates:
        return fail(f"all '{target_text}' candidates break: {_rule_text(negatives)}", "no object satisfies the constraint.")

    ranked = sorted(((c, distance(ref, c)) for c in candidates), key=lambda p: p[1])
    best, best_dist = ranked[0]
    ranking = ", ".join(f"{c['id']} {d:.2f}m" for c, d in ranked[:3])
    rule = f" that is {_rule_text(negatives)}" if negatives else ""
    return _ok(
        best,
        "; ".join([f"distance to {ref['id']}: {ranking}"] + rule_facts),
        f"The closest {target_text or 'object'} to the {reference_text}{rule} is {best['id']}, "
        f"verified at {best_dist:.2f} meters.",
        [ref, best],
        extra,
    )


def filter_not_near(graph, target_text, negatives, only_free=False):
    """negatives: an object name ("laptop" = NOT near the laptop) or a list of {"relation", "object"}."""
    if not target_text:
        return fail("no target given", "the question does not say which object to find.")
    negatives = _as_negatives(negatives)
    candidates = find_nodes_by_name(graph, target_text)
    if only_free:
        candidates = [c for c in candidates if c.get("state") == "free"]
    if not candidates:
        return fail(f"no candidates for '{target_text}'", "no matching objects in the scene graph.")

    valid, rule_facts, extra, error = _apply_negatives(graph, candidates, negatives)
    if error:
        return error
    if not valid:
        return fail(f"all '{target_text}' candidates break: {_rule_text(negatives)}", "no object satisfies the constraint.")

    chosen = max(valid, key=lambda n: _conf(n) or 0)
    return _ok(
        chosen,
        f"'{chosen['id']}': " + "; ".join(rule_facts) if rule_facts else f"'{chosen['id']}' kept",
        f"{chosen['id']} is a {target_text} that is {_rule_text(negatives)}.",
        [chosen],
        extra,
    )


def graph_relation(relation):
    """'under' / 'below' -> 'under' etc.; None for distance relations (near, closest_to) and unknown words."""
    return GRAPH_RELATIONS.get(str(relation or "").lower().strip().replace(" ", "_"))


def find_related(graph, relation, reference_text, target_text=""):
    """Objects X with an active S4 edge (X, relation, reference): "What is under the mug?", "Which pen is inside the cup?"."""
    refs = find_nodes_by_name(graph, reference_text)
    if not refs:
        return fail(f"no node matches reference '{reference_text}'", "the reference object is not in the scene graph.")
    ref = refs[0]
    pool = find_nodes_by_name(graph, target_text) if target_text else [n for n in graph["nodes"] if n["id"] != ref["id"]]
    ids = {n["id"]: n for n in pool}
    hits = [(ids[e["source"]], e) for e in graph.get("edges", [])
            if is_active(e) and e["predicate"] == relation and e["target"] == ref["id"] and e["source"] in ids]
    if not hits:
        return fail(f"no active '{relation}' edge to {ref['id']}" + (f" from a '{target_text}'" if target_text else ""),
                    f"nothing is {relation.replace('_', ' ')} the {reference_text}.")
    best, edge = max(hits, key=lambda h: _conf(h[0]) or 0)
    evidence = ", ".join(f"{k}={v}" for k, v in (edge.get("evidence") or {}).items())
    extra = [f"{len(hits)} objects are {relation} {ref['id']}: {', '.join(h[0]['id'] for h in hits)}"] if len(hits) > 1 else []
    return _ok(best, f"edge {best['id']} {relation} {ref['id']} ({evidence})",
               f"The {target_text or 'object'} {relation.replace('_', ' ')} the {reference_text} is {best['id']} ({evidence}).",
               [best, ref], extra)


def where_before(graph, target_text):
    """Temporal query "Where was the mug before?": previous resting place from S4's pose_history and ended edges."""
    matches = find_nodes_by_name(graph, target_text)
    if not matches:
        return fail(f"no node matches '{target_text}'", f"'{target_text}' is not in the scene graph.")
    node = matches[0]
    hist = node.get("pose_history") or []
    ended = [e for e in graph.get("edges", []) if e.get("end_time") is not None and e["source"] == node["id"]
             and e["predicate"] in ("near", "on", "under", "inside")]
    ended_txt = "; ".join(f"was {e['predicate']} {e['target']} until t={e['end_time']}" for e in ended[-3:])
    now = node["pose_map"]
    if len(hist) >= 2:
        prev, cur = hist[-2], hist[-1]
        moved = math.dist(prev["pose_map"], cur["pose_map"])
        px, py, pz = prev["pose_map"]
        facts = (f"pose_history: {len(hist)} positions; previous [{px:.2f}, {py:.2f}, {pz:.2f}] from t={prev['t']}, "
                 f"moved {moved:.2f} m at t={cur['t']}" + (f"; {ended_txt}" if ended_txt else ""))
        answer = (f"Before t={cur['t']}, {node['id']} was at x={px:.2f}, y={py:.2f}, z={pz:.2f} m; "
                  f"it moved {moved:.2f} m to x={now[0]:.2f}, y={now[1]:.2f}, z={now[2]:.2f} m.")
        return _ok(node, facts, answer, [node])
    if ended:
        return _ok(node, f"no move recorded; {ended_txt}",
                   f"{node['id']} has not moved, but its relations changed: {ended_txt}.", [node])
    first = hist[0]["t"] if hist else node.get("first_seen")
    return _ok(node, f"no move recorded since first seen (t={first})",
               f"{node['id']} has not moved since it was first seen (t={first}); it is at x={now[0]:.2f}, "
               f"y={now[1]:.2f}, z={now[2]:.2f} m.", [node])


if __name__ == "__main__":
    graph = load_graph()
    print(json.dumps(find_closest(graph, "scanner", "chair", only_free=True), indent=2))
    print(json.dumps(filter_not_near(graph, "chair", "laptop"), indent=2))
    print(json.dumps(locate(graph, "mug"), indent=2))

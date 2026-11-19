"""S5 (Sanjarbek) — 200-query test set and the four-configuration comparison (professor's guide §8).

Ground truth comes from ground-truth geometry, not from the system: every query names a *GT scene graph*,
built by the S4 rules from the tape-measured positions (eval/ground_truth/ground_truth_positions.csv), so a
reasoning error is never hidden by a perception error. (S7 measures the full chain separately.)

    # 1. GT scene graphs from measured positions (one per GT scene; a sequence of frames keeps history)
    python -m src.evaluation.s5_query_eval graphs --tf configs/sensors/measured_tf.yaml
    # 2. candidate queries from templates (40 simple, 30 negative, 40 multi-hop, 40 temporal,
    #    30 open-vocabulary description, 20 ambiguous/unsupported) -> people check and correct them
    python -m src.evaluation.s5_query_eval generate
    # 3. run the four configurations on the checked set and write the tables
    python -m src.evaluation.s5_query_eval run --methods A B C D        # A/B need Ollama
    python -m src.evaluation.s5_query_eval run --methods C D --parser rules   # offline

Configurations:
    A llm_only        the LLM sees the question and the object names only, and answers with an object id
    B llm_graph       the LLM also sees the scene graph (positions, relations, history); no verification
    C llm_verifier    LLM parse -> metric geometry check, one round, no temporal history
    D full            propose -> verify -> correct (2 rounds) + temporal history (the current S5)

gt_answer: an object id, several accepted ids "a|b", "REFUSE" (must refuse or clarify), or "POS:x,y[;NOW:x,y]"
(temporal: the previous resting position, correct within POS_TOL_M and closer to it than to the current one).

Outputs (eval/queries/ and eval/results/s5/): queries_200.csv/json, ground_truth_answers.csv,
query_results.csv, method_comparison_table.csv, accuracy_by_query_family.csv, hallucination_analysis.csv,
example_proofs.md (10), failure_cases.md (10).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..scene_graph.engine import SceneGraphEngine
from .common import COLUMNS, GT, QUERIES, as_bool, as_float, load_tf, read_csv, results_dir, write_csv, write_json
from .stats import rate

FAMILY_TARGET = {"simple": 40, "negative": 30, "multihop": 40, "temporal": 40, "open_vocab": 30, "ambiguous": 20}
POS_TOL_M = 0.05
GRAPH_DIR = QUERIES / "gt_graphs"
METHODS = {"A": "A_llm_only", "B": "B_llm_graph", "C": "C_llm_verifier", "D": "D_full"}


# ---------------------------------------------------------------- 1. GT graphs from measured positions
def _payload(rows, ts, T_map_optical=None) -> dict:
    objs = []
    for r in rows:
        c = [as_float(r["x_gt"]), as_float(r["y_gt"]), as_float(r["z_gt"])]
        size = [as_float(r.get("size_x"), 0.08), as_float(r.get("size_y"), 0.08), as_float(r.get("size_z"), 0.08)]
        cam = c
        if T_map_optical is not None:                      # camera-side x for left_of
            cam = (np.linalg.inv(T_map_optical) @ np.r_[c, 1.0])[:3].tolist()
        objs.append({"object_id": r["object_id"], "persistent_id": r["object_id"], "semantic_label": r["class"],
                     "label_candidates": [r["class"]], "detector_score": 1.0, "fused_confidence": 1.0, "depth_confidence": 1.0,
                     "centroid": cam, "box_map": {"center": c, "dimensions": [size[0], size[2], size[1]], "yaw": 0.0}})
    return {"timestamp": ts, "objects": objs}


def gt_graphs(gt_rows, tf_path=None, out: Path = GRAPH_DIR) -> list[Path]:
    """One GT graph per bag; frames of the same bag are fed in order so pose history and ended edges exist."""
    T = load_tf(tf_path) if tf_path else None
    by_bag = defaultdict(lambda: defaultdict(list))
    for r in gt_rows:
        by_bag[r["bag_id"]][r["frame_id"]].append(r)
    paths = []
    for bag, frames in sorted(by_bag.items()):
        eng = SceneGraphEngine(session_id=f"gt_{bag}", use_support_plane=False)
        for k, (fid, rows) in enumerate(sorted(frames.items())):
            eng.update(_payload(rows, float(k), T))
            p = out / f"{bag}__{fid}.json"
            eng.save(p)
            paths.append(p)
    return paths


# ---------------------------------------------------------------- 2. candidate queries (templates + oracle)
def _obj(g):
    return [n for n in g["nodes"] if not n.get("virtual") and n.get("state") != "occluded"]


def _label(n):
    return n["names"][0]["text"]


def _d(a, b):
    return math.dist(a["pose_map"], b["pose_map"])


def _edges(g, pred):
    return [e for e in g["edges"] if e.get("end_time") is None and e["predicate"] == pred]


def _unique(g):
    """Objects whose class name is unique in the scene (a clear reference)."""
    labs = defaultdict(list)
    for n in _obj(g):
        labs[_label(n)].append(n)
    return [v[0] for v in labs.values() if len(v) == 1]


def _aliases() -> dict:
    import yaml
    p = Path("src/open_vocab/configs/aliases.yaml")
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def generate(graph_paths, seed: int = 0, targets=FAMILY_TARGET) -> list[dict]:
    rng = random.Random(seed)
    pools = defaultdict(list)
    aliases = _aliases()
    absent = ["soldering iron", "hot glue gun", "vernier caliper", "stapler", "banana"]
    for gp in graph_paths:
        g = json.loads(Path(gp).read_text())
        gname = Path(gp).as_posix()
        objs, uniq = _obj(g), _unique(g)
        add = lambda fam, q, ans, tgt="", ref="", rel="", refuse=0, diff="medium", note="": pools[fam].append(
            {"family": fam, "question": q, "graph": gname, "gt_answer": ans, "gt_target": tgt, "gt_reference": ref,
             "gt_relation": rel, "expect_refusal": refuse, "difficulty": diff, "notes": note})
        for ref in uniq:
            others = [o for o in objs if o["id"] != ref["id"]]
            if not others:
                continue
            best = min(others, key=lambda o: _d(o, ref))
            ties = [o["id"] for o in others if _d(o, ref) - _d(best, ref) < 0.01]
            R = _label(ref)
            for q in (f"What is closest to the {R}?", f"Which object is nearest to the {R}?"):
                add("simple", q, "|".join(ties), "", R, "closest_to", diff="easy")
            # same-class target: "Which <cls> is closest to the <ref>?"
            for cls in {_label(o) for o in others}:
                cands = [o for o in others if _label(o) == cls]
                if len(cands) > 1:
                    b = min(cands, key=lambda o: _d(o, ref))
                    add("simple", f"Which {cls} is closest to the {R}?", b["id"], cls, R, "closest_to")
            for pred, words in (("on", "on"), ("under", "under"), ("inside", "inside")):
                hits = [e["source"] for e in _edges(g, pred) if e["target"] == ref["id"]]
                if hits:
                    add("simple", f"What is {words} the {R}?", "|".join(hits), "", R, pred)
            # negatives
            far = [o["id"] for o in others if _d(o, ref) >= 0.30]
            near = [o["id"] for o in others if _d(o, ref) < 0.30]
            for cls in sorted({_label(o) for o in others}):
                ok = [o["id"] for o in others if _label(o) == cls and o["id"] in far]
                add("negative", f"Find a {cls} that is not near the {R}.", "|".join(ok) or "REFUSE", cls, R, "not_near",
                    refuse=int(not ok))
            if near and far:
                add("negative", f"Find an object that is not near the {R}.", "|".join(far), "", R, "not_near")
            # multi-hop: closest to the object that is on / near X
            for e in _edges(g, "on"):
                if e["target"] == ref["id"]:
                    mid = next(n for n in objs if n["id"] == e["source"])
                    rest = [o for o in objs if o["id"] not in (mid["id"], ref["id"])]
                    if rest:
                        b = min(rest, key=lambda o: _d(o, mid))
                        add("multihop", f"What is closest to the object that is on the {R}?", b["id"], "", R, "closest_to(on)", diff="hard")
            for o in others:
                rest = [x for x in others if x["id"] != o["id"]]
                if not rest or _label(o) == R:
                    continue
                c1 = min(rest, key=lambda x: _d(x, o))
                if _d(c1, ref) > _d(o, ref):
                    add("multihop", f"Which object is closest to the {_label(o)} and farther from the {R} than the {_label(o)}?",
                        c1["id"], "", f"{_label(o)};{R}", "closest_to+farther", diff="hard")
        # temporal: objects with a previous resting position
        for n in objs:
            h = n.get("pose_history") or []
            if len(h) >= 2:
                px, py = h[-2]["pose_map"][:2]
                nx_, ny_ = n["pose_map"][:2]
                for q in (f"Where was the {_label(n)} before it moved?", f"Where was the {_label(n)} previously?"):
                    add("temporal", q, f"POS:{px:.3f},{py:.3f};NOW:{nx_:.3f},{ny_:.3f}", _label(n), "", "before", diff="hard")
                ended = [e for e in g["edges"] if e.get("end_time") is not None and e["source"] == n["id"] and e["predicate"] == "on"]
                for e in ended:
                    add("temporal", f"What was the {_label(n)} on before it moved?", e["target"], _label(n), "", "on@before", diff="hard")
            elif n in uniq:
                add("temporal", f"Where was the {_label(n)} before?", f"POS:{n['pose_map'][0]:.3f},{n['pose_map'][1]:.3f}",
                    _label(n), "", "before", diff="medium", note="did not move: previous = current position")
        # open-vocabulary descriptions (aliases of the class present in the scene)
        for n in uniq:
            for canon, al in aliases.items():
                if _label(n) == canon or _label(n) in al:
                    for a in [x for x in al if len(x.split()) > 1][:3]:
                        add("open_vocab", f"Where is the {a}?", n["id"], a, "", "locate")
        # ambiguous / unsupported
        labs = defaultdict(list)
        for n in objs:
            labs[_label(n)].append(n["id"])
        for cls, ids in labs.items():
            if len(ids) > 1:
                add("ambiguous", f"Find the {cls}.", "REFUSE", cls, "", "ambiguous", refuse=1, note=f"{len(ids)} instances: clarify")
        for a in absent:
            if a not in labs:
                add("ambiguous", f"Where is the {a}?", "REFUSE", a, "", "absent", refuse=1, note="not in the scene")
                if uniq:
                    add("ambiguous", f"What is closest to the {a}?", "REFUSE", "", a, "absent", refuse=1, note="reference absent")
    out = []
    for fam, n in targets.items():
        pool = pools[fam]
        rng.shuffle(pool)
        seen, pick = set(), []
        for q in pool:                                   # avoid exact duplicates (same question on the same graph)
            key = (q["question"], q["graph"])
            if key not in seen:
                seen.add(key)
                pick.append(q)
            if len(pick) >= n:
                break
        out += pick
    for k, q in enumerate(out, 1):
        q.update(query_id=f"Q_{k:03d}", gt_intent="find_object", checked="")
    return out


# ---------------------------------------------------------------- 3. the four configurations
def _llm_answer(question, graph, with_graph: bool, model=None) -> str:
    import ollama

    from ..reasoning.query_parser import MODEL_NAME
    ids = [n["id"] for n in graph["nodes"]]
    ctx = f"Objects in the scene (ids): {', '.join(ids)}."
    if with_graph:
        lines = [f"{n['id']}: at x={n['pose_map'][0]:.2f} y={n['pose_map'][1]:.2f} z={n['pose_map'][2]:.2f} m"
                 + (f", previously at {n['pose_history'][-2]['pose_map'][:2]}" if len(n.get("pose_history") or []) >= 2 else "")
                 for n in graph["nodes"]]
        rel = [f"{e['source']} {e['predicate']} {e['target']}" + ("" if e.get("end_time") is None else f" (ended t={e['end_time']})")
               for e in graph["edges"]]
        ctx = "Scene graph.\nObjects:\n" + "\n".join(lines) + "\nRelations:\n" + "\n".join(rel)
    msg = [{"role": "system", "content": "Answer questions about a tabletop scene. Reply with JSON only: "
                                         "{\"answer\": \"<object id>\"} or {\"answer\": \"NONE\"} if it cannot be answered. "
                                         "For 'where was X before' questions answer {\"answer\": \"x,y\"} with the previous position."},
           {"role": "user", "content": f"{ctx}\n\nQuestion: {question}"}]
    r = ollama.chat(model=model or MODEL_NAME, messages=msg, format="json", options={"temperature": 0})
    try:
        return str(json.loads(r["message"]["content"]).get("answer", "NONE"))
    except (json.JSONDecodeError, AttributeError):
        return "NONE"


def _s5(parser: str, rounds: int, temporal: bool):
    """S5's answer_question with the number of rounds and the temporal route switched as the config asks."""
    from ..integration import s5_adapter

    m = s5_adapter._load_s5()

    def run(question, graph):
        old_r, old_t = m.MAX_ROUNDS, m.TEMPORAL
        try:
            m.MAX_ROUNDS = rounds
            if not temporal:
                m.TEMPORAL = re.compile(r"(?!x)x")          # never matches: no history route
            return s5_adapter.answer(question, graph, parser)
        finally:
            m.MAX_ROUNDS, m.TEMPORAL = old_r, old_t
    return run


def _pos_from_facts(text: str):
    """The previous resting position S5 reports: 'previous [x, y, z]' in the facts, or the first 'x=.., y=..'
    of the final answer ('Before t=.., mug was at x=0.54, y=-0.05' / 'has not moved ... it is at x=.., y=..')."""
    m = re.search(r"previous \[([-\d.]+), ([-\d.]+)", text or "") or re.search(r"x=([-\d.]+), y=([-\d.]+)", text or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def is_correct(gt: str, pred_id, refused: bool, warned_ambiguous: bool, facts: str = "", pos=None) -> bool:
    gt = (gt or "").strip()
    if gt == "REFUSE":
        return refused or warned_ambiguous
    if refused or pred_id in (None, "", "NONE"):
        return False
    if gt.startswith("POS:"):
        prev, _, now = gt[4:].partition(";NOW:")
        x, y = (float(v) for v in prev.split(","))
        p = pos or _pos_from_facts(facts)
        if p is None or math.dist(p, (x, y)) > POS_TOL_M:
            return False
        if now:                       # a moved object: the answer must be the OLD place, not the current one
            nx_, ny_ = (float(v) for v in now.split(","))
            return math.dist(p, (x, y)) < math.dist(p, (nx_, ny_))
        return True
    return str(pred_id) in gt.split("|")


def _words(t):
    return set(re.findall(r"[a-z0-9]+", str(t or "").lower()))


def _parse_ok(parsed: dict, q: dict) -> bool:
    if not parsed or "error" in parsed:
        return False
    def same(a, b):
        A, B = _words(a), _words(b)
        return (not A and not B) or (A and B and (A <= B or B <= A))
    ref = q.get("gt_reference", "").split(";")[0]
    tgt, pref = parsed.get("target", ""), parsed.get("reference", "")
    if q["family"] == "negative":     # the constrained object may be stored as a negative constraint
        negs = " ".join(str(n.get("object", "")) for n in parsed.get("negative_constraints", []))
        return same(tgt, q.get("gt_target", "")) and (same(pref, ref) or same(negs, ref))
    return same(tgt, q.get("gt_target", "")) and same(pref, ref) or (q["family"] == "temporal" and same(tgt or pref, q.get("gt_target")))


def _grounded_ok(parsed: dict, graph: dict, q: dict):
    """Every object the question names (GT target / reference) resolves to a graph node of that class.
    '' (not applicable) for questions about objects that are not in the scene, and for descriptions."""
    from ..integration import s5_adapter
    s5_adapter._load_s5()
    import verifier  # S5's flat module, loaded by the adapter
    if q.get("gt_relation") == "absent" or q["family"] == "open_vocab":
        return ""
    texts = [parsed.get("target"), parsed.get("reference")] + [n.get("object") for n in parsed.get("negative_constraints", [])]
    for want in [q.get("gt_target"), *q.get("gt_reference", "").split(";")]:
        if not want:
            continue
        hit = False
        for t in texts:
            m = verifier.find_nodes_by_name(graph, t or "")
            if m and _words(m[0]["names"][0]["text"]) & _words(want):
                hit = True
        if not hit:
            return 0
    return 1


def run_queries(queries, methods=("C", "D"), parser="rules", model=None) -> list[dict]:
    graphs = {}
    runners = {"C": _s5(parser, 1, False), "D": _s5(parser, 2, True)}
    rows = []
    for q in queries:
        g = graphs.setdefault(q["graph"], json.loads(Path(q["graph"]).read_text()))
        proposal = None
        if "B" in methods or "A" in methods:
            try:
                proposal = {k: _llm_answer(q["question"], g, k == "B", model) for k in ("A", "B") if k in methods}
            except Exception as e:      # no Ollama server
                proposal = {k: f"ERROR {e}" for k in ("A", "B") if k in methods}
        for m in methods:
            if m in ("A", "B"):
                ans = proposal[m]
                pos = None
                if re.fullmatch(r"\s*-?[\d.]+\s*,\s*-?[\d.]+\s*", ans or ""):
                    pos = tuple(float(v) for v in ans.split(","))
                refused = ans in ("NONE", "") or ans.startswith("ERROR")
                ok = is_correct(q["gt_answer"], None if refused else ans, refused, False, pos=pos)
                rows.append({"query_id": q["query_id"], "family": q["family"], "question": q["question"], "gt_answer": q["gt_answer"],
                             "method": METHODS[m], "parsed_ok": "", "grounded_ok": "", "proposed_answer": ans, "pred_answer": ans,
                             "correct": int(ok), "proposal_wrong": int(not ok), "wrong_claim_caught": "", "correction_success": "",
                             "hallucination": int(not ok and not refused), "refused": int(refused), "proof": ""})
                continue
            r = runners[m](q["question"], g)
            rounds = r.get("verification_rounds") or [{"parsed": r.get("llm_parsed_query"), "verified": r["verification_status"]}]
            first = rounds[0]["parsed"] or {}
            refused = not r["verification_status"]
            warned = any("objects match" in w or "objects are" in w for w in r.get("warnings", []))
            ok = is_correct(q["gt_answer"], r["target_id"], refused, warned,
                            f"{r.get('computed_facts', '')} || {r.get('final_answer', '')}")
            # the proposal = what the first, unverified parse would have answered
            first_verified = rounds[0]["verified"]
            proposal_wrong = not first_verified or (len(rounds) == 1 and not ok)
            claim = (proposal or {}).get("B")                # LLM+graph claim checked by the verifier (needs Ollama)
            claim_wrong = claim is not None and not claim.startswith("ERROR") and not is_correct(q["gt_answer"], claim, claim == "NONE", False)
            rows.append({"query_id": q["query_id"], "family": q["family"], "question": q["question"], "gt_answer": q["gt_answer"],
                         "method": METHODS[m], "parsed_ok": int(_parse_ok(first, q)), "grounded_ok": _grounded_ok(first, g, q),
                         "proposed_answer": claim if claim is not None else json.dumps(first),
                         "pred_answer": r["target_id"] or "REFUSED", "correct": int(ok), "proposal_wrong": int(bool(proposal_wrong)),
                         "wrong_claim_caught": int(claim_wrong and (refused or r["target_id"] != claim)) if claim is not None else "",
                         "correction_success": int(bool(proposal_wrong) and ok and len(rounds) > 1),
                         "hallucination": int(not ok and not refused), "refused": int(refused),
                         "proof": r.get("computed_facts", ""), "final_answer": r.get("final_answer", ""),
                         "rounds": len(rounds), "parser": r.get("parser")})
    # D's proposal = what one verified round (configuration C) answered; correction = D fixed a wrong C answer
    c_ok = {r["query_id"]: int(r["correct"]) for r in rows if r["method"] == METHODS["C"]}
    for r in rows:
        if r["method"] == METHODS["D"] and r["query_id"] in c_ok:
            r["proposal_wrong"] = int(not c_ok[r["query_id"]])
            r["correction_success"] = int(not c_ok[r["query_id"]] and int(r["correct"]))
        elif r["method"] == METHODS["C"]:
            r["proposal_wrong"], r["correction_success"] = "", ""
    return rows


# ---------------------------------------------------------------- 4. tables
def summarise(rows) -> dict:
    by_m = defaultdict(list)
    for r in rows:
        by_m[r["method"]].append(r)
    comp, fam, hall = [], [], []
    for m, sub in sorted(by_m.items()):
        n = len(sub)
        num = lambda key: sum(int(r[key]) for r in sub if str(r.get(key, "")).strip() not in ("",))
        den = lambda key: sum(1 for r in sub if str(r.get(key, "")).strip() not in ("",))
        comp.append({"method": m, "queries": n,
                     "parsing_accuracy": rate(num("parsed_ok"), den("parsed_ok"))["text"] if den("parsed_ok") else "n/a",
                     "grounding_accuracy": rate(num("grounded_ok"), den("grounded_ok"))["text"] if den("grounded_ok") else "n/a",
                     "answer_accuracy": rate(num("correct"), n)["text"],
                     "hallucination_rate": rate(num("hallucination"), n)["text"],
                     "refusals": rate(num("refused"), n)["text"]})
        for f in sorted({r["family"] for r in sub}):
            fs = [r for r in sub if r["family"] == f]
            fam.append({"method": m, "family": f, "queries": len(fs), "answer_accuracy": rate(sum(int(r["correct"]) for r in fs), len(fs))["text"],
                        "hallucination_rate": rate(sum(int(r["hallucination"]) for r in fs), len(fs))["text"]})
        wrong = [r for r in sub if str(r.get("wrong_claim_caught", "")).strip() != ""]
        caught = sum(int(r["wrong_claim_caught"]) for r in wrong)
        pw = [r for r in sub if str(r.get("proposal_wrong")) == "1" and r["method"] == METHODS["D"]]
        hall.append({"method": m, "wrong_llm_claims (B)": len(wrong) and sum(1 for r in wrong if r["wrong_claim_caught"] != ""),
                     "hallucination_catch_rate": rate(caught, len(wrong))["text"] if wrong else "n/a (needs Ollama: config B proposes)",
                     "wrong_first_proposals (C answer wrong)": len(pw) if m == METHODS["D"] else "",
                     "correction_success_rate": rate(sum(int(r["correction_success"]) for r in pw), len(pw))["text"] if pw else "n/a",
                     "hallucinations_after_verification": sum(int(r["hallucination"]) for r in sub)})
    return {"comparison": comp, "by_family": fam, "hallucination": hall}


def write_md(rows, out: Path):
    D = [r for r in rows if r["method"] == METHODS["D"]]
    good = [r for r in D if int(r["correct"]) and r["proof"]][:10]
    bad = [r for r in D if not int(r["correct"])][:10]
    L = ["# S5 — 10 example proofs (configuration D)", ""]
    for r in good:
        L += [f"**{r['query_id']}** ({r['family']}) — {r['question']}", f"- answer: `{r['pred_answer']}` (GT `{r['gt_answer']}`)",
              f"- proof: {r['proof']}", ""]
    (out / "example_proofs.md").write_text("\n".join(L), encoding="utf-8")
    L = ["# S5 — 10 representative failure cases (configuration D)", "", "Fill in the *why* line for each case.", ""]
    for r in bad:
        L += [f"**{r['query_id']}** ({r['family']}) — {r['question']}", f"- system: `{r['pred_answer']}`; GT: `{r['gt_answer']}`",
              f"- facts: {r['proof']}", "- why: ", ""]
    (out / "failure_cases.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("graphs")
    g.add_argument("--gt", default=str(GT / "ground_truth_positions.csv"))
    g.add_argument("--tf")
    gen = sub.add_parser("generate")
    gen.add_argument("--graphs", nargs="*", help="GT graph JSON files (default eval/queries/gt_graphs/*.json)")
    gen.add_argument("--seed", type=int, default=0)
    r = sub.add_parser("run")
    r.add_argument("--queries", default=str(QUERIES / "queries_200.csv"))
    r.add_argument("--methods", nargs="+", default=["A", "B", "C", "D"], choices=list(METHODS))
    r.add_argument("--parser", default="auto", choices=["auto", "ollama", "rules"])
    r.add_argument("--model")
    r.add_argument("--only-checked", action="store_true", help="use only rows marked checked=1")
    a = ap.parse_args()
    if a.cmd == "graphs":
        paths = gt_graphs(read_csv(a.gt), a.tf)
        print(f"{len(paths)} GT graphs -> {GRAPH_DIR}")
    elif a.cmd == "generate":
        paths = a.graphs or sorted(GRAPH_DIR.glob("*.json"))
        qs = generate(paths, a.seed)
        write_csv(QUERIES / "queries_200.csv", qs, COLUMNS["queries"])
        write_json(QUERIES / "queries_200.json", qs)
        write_csv(QUERIES / "ground_truth_answers.csv", [{k: q[k] for k in ("query_id", "family", "gt_answer", "expect_refusal")} for q in qs])
        cnt = defaultdict(int)
        for q in qs:
            cnt[q["family"]] += 1
        print(f"{len(qs)} queries {dict(cnt)} -> {QUERIES / 'queries_200.csv'}  (check each row, set checked=1)")
    elif a.cmd == "run":
        from ..integration.s5_adapter import resolve_parser
        qs = read_csv(a.queries)
        if a.only_checked:
            qs = [q for q in qs if as_bool(q.get("checked"))]
        rows = run_queries(qs, a.methods, resolve_parser(a.parser), a.model)
        out = results_dir("s5")
        write_csv(out / "query_results.csv", rows, COLUMNS["query_results"] + ["rounds", "parser", "final_answer"])
        s = summarise(rows)
        write_csv(out / "method_comparison_table.csv", s["comparison"])
        write_csv(out / "accuracy_by_query_family.csv", s["by_family"])
        write_csv(out / "hallucination_analysis.csv", s["hallucination"])
        write_md(rows, out)
        for x in s["comparison"]:
            print(x)


if __name__ == "__main__":
    main()

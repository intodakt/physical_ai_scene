"""W12–W16 evaluation toolkit (S5 200-query evaluation)."""

import json
import math

import numpy as np
import pytest

def test_s5_answer_checks():
    from src.evaluation.s5_query_eval import is_correct

    assert is_correct("mug_01|cup_02", "cup_02", False, False)
    assert is_correct("REFUSE", None, True, False) and is_correct("REFUSE", "mug_01", False, True)
    assert not is_correct("REFUSE", "mug_01", False, False)
    assert is_correct("POS:0.54,-0.05;NOW:0.80,0.10", "mug_01", False, False, "Before t=6.0, mug_01 was at x=0.54, y=-0.05")
    assert not is_correct("POS:0.54,-0.05;NOW:0.56,-0.03", "mug_01", False, False, "it is at x=0.56, y=-0.03")


def test_s5_generate_and_run_offline(tmp_path):
    from src.evaluation.s5_query_eval import METHODS, gt_graphs, generate, run_queries, summarise

    rows = []
    for f, mx in (("f0", 0.40), ("f1", 0.75)):          # the mug moves 35 cm between the two frames
        for oid, cls, x, y in (("laptop_01", "laptop", 0.70, 0.15), ("mug_01", "mug", mx, -0.10), ("book_01", "book", 0.60, -0.30)):
            rows.append({"bag_id": "B", "frame_id": f, "object_id": oid, "class": cls, "x_gt": x, "y_gt": y, "z_gt": 0.05,
                         "size_x": 0.1, "size_y": 0.1, "size_z": 0.1})
    paths = gt_graphs(rows, out=tmp_path)
    qs = generate(paths[-1:])
    fams = {q["family"] for q in qs}
    assert {"simple", "negative", "temporal", "ambiguous"} <= fams
    res = run_queries(qs, ("C", "D"), "rules")
    assert {r["method"] for r in res} == {METHODS["C"], METHODS["D"]}
    temporal_d = [r for r in res if r["method"] == METHODS["D"] and r["family"] == "temporal" and "moved" not in r["question"]]
    assert temporal_d and all(int(r["correct"]) for r in temporal_d if "previously" in r["question"])
    assert summarise(res)["comparison"]

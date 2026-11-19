"""W12–W16 evaluation toolkit (shared statistics, S7 end-to-end, report)."""

import json
import math

import numpy as np
import pytest

from src.evaluation import stats

def test_describe_rate_prf():
    d = stats.describe([1, 2, 3, 4, 100, None, "", float("nan")])
    assert d["n"] == 5 and d["median"] == 3 and d["ci95"] is not None
    assert stats.describe([1, 2])["ci95"] is None                    # too few samples: no CI
    assert stats.rate(46, 50)["text"] == "92.0 % (46/50)"
    assert stats.rate(0, 0)["value"] is None
    p = stats.prf(8, 2, 2)
    assert p["precision"] == p["recall"] == p["f1"] == 0.8


def test_geometry_helpers():
    assert stats.centroid_error([0.414, 0.242, 0.065], [0.40, 0.25, 0.06]) == pytest.approx(0.0169, abs=1e-4)   # guide §3.2
    assert stats.iou_2d([0, 0, 2, 2], [1, 1, 3, 3]) == pytest.approx(1 / 7)
    assert stats.iou_3d_aabb([0, 0, 0], [1, 1, 1], [0, 0, 0], [1, 1, 1]) == pytest.approx(1.0)
    assert stats.cosine([1, 0], [0, 1]) == 0.0

def test_s7_template_and_failure_summary():
    from src.evaluation.s7_e2e_eval import failure_summary, task_template

    t = task_template()
    assert len(t) == 30 and [x["difficulty"] for x in t].count("hard") == 10
    rows = [{"repeat": 1, "difficulty": "easy", "success": 1, "first_failure_stage": ""},
            {"repeat": 1, "difficulty": "hard", "success": 0, "first_failure_stage": "S3"}]
    s = {r["group"]: r for r in failure_summary(rows)}
    assert s["all"]["task_success_rate"] == "50.0 % (1/2)" and s["first failure at S3"]["tasks"] == 1


def test_report_checklist_has_all_appendix_c_items():
    from src.evaluation.report import checklist

    items = checklist()
    assert len(items) == 20 and all(c["done"] in ("yes", "no") for c in items)

"""W12–W16 evaluation toolkit (S2 fusion ablation)."""

import json
import math

import numpy as np
import pytest

def test_s2_methods_and_summary():
    from src.evaluation.s2_fusion_eval import METHODS, method_configs, summarise
    from src.fusion_3d.pipeline import load_config

    cfgs = method_configs(load_config())
    assert cfgs["M1_depth_only"]["depth"]["flying_pixel_filter"]["enabled"] is False
    assert cfgs["M3_fixed_rgbd"]["depth_reliability"]["enabled"] is False and cfgs["M3_fixed_rgbd"]["fusion"]["mode"] == "fixed"
    assert cfgs["M4_adaptive_rgbd"]["depth_reliability"]["enabled"] is True
    rows = [{"method": m, "condition": "normal", "error_cm": e, "status": "ok" if e < 5 else "fail"}
            for m in METHODS for e in (1.0, 2.0, 9.0)]
    table, by_cond = summarise(rows)
    assert table[0]["median_error_cm"] == 2.0 and table[0]["failure_rate"] == "33.3 % (1/3)"

"""W12–W16 evaluation toolkit (S6 tracking + action safety)."""

import json
import math

import numpy as np
import pytest

def test_s6_tracking_metrics():
    from src.evaluation.s6_tracking_eval import metrics

    g = [{"frame_id": f"f{k}", "detection_id": f"d{k}", "gt_object_id": "mug_A", "occluded": "0", "reappeared": ""} for k in range(3)]
    g.append({"frame_id": "f3", "detection_id": "", "gt_object_id": "mug_A", "occluded": "1"})
    g.append({"frame_id": "f4", "detection_id": "d4", "gt_object_id": "mug_A", "occluded": "0", "reappeared": "1"})
    ids = {("f0", "d0"): "mug_01", ("f1", "d1"): "mug_01", ("f2", "d2"): "mug_02", ("f4", "d4"): "mug_02"}
    m = metrics(g, ids)
    assert m["id_switches"] == 1 and m["occlusion_recovery"]["text"] == "100.0 % (1/1)" and m["track_recall"]["den"] == 4


def test_s6_action_trials_on_real_graph():
    import yaml

    from src.evaluation.s6_tracking_eval import action_summary, action_trials

    cfg = yaml.safe_load(open("configs/s7_integration.yaml"))["action"]
    graph = json.load(open("outputs/scene_graph/frame_000_scene_graph.json"))
    trials = action_trials(graph, cfg)
    assert len(trials) == 60 and sum(t["gt_safe"] for t in trials) == 30
    s = {r["metric"]: r["value"] for r in action_summary(trials)}
    assert s["false_acceptance_rate"].startswith("0.0 %")       # an unsafe goal must never be accepted


def test_tracker_appearance_term_breaks_a_tie():
    from src.tracking import MultiTermTracker

    def obj(x, app):
        return {"semantic_label": "mug", "centroid": [0, 0, 1], "box_map": {"center": [x, 0.0, 0.05], "dimensions": [0.08, 0.1, 0.08]},
                "appearance": app}
    t = MultiTermTracker(w_app=2.0)
    red, blue = [1.0, 0.0], [0.0, 1.0]
    first = t.update([obj(0.50, red), obj(0.60, blue)], 0)
    ids = {o["appearance"][0]: o["persistent_id"] for o in first}
    swapped = t.update([obj(0.555, blue), obj(0.545, red)], 1)        # equidistant positions, colours decide
    assert {o["appearance"][0]: o["persistent_id"] for o in swapped} == ids

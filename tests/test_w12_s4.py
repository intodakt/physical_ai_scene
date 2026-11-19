"""W12–W16 evaluation toolkit (S4 relations, hysteresis, events)."""

import json
import math

import numpy as np
import pytest

def _payload(t, d):
    box = lambda c: {"center": c, "dimensions": [0.08, 0.1, 0.08], "yaw": 0.0}
    objs = [{"object_id": "mug_0", "persistent_id": "mug_01", "semantic_label": "mug", "centroid": [0, 0, 1], "box_map": box([0.5, 0.0, 0.05])},
            {"object_id": "book_0", "persistent_id": "book_01", "semantic_label": "book", "centroid": [0.3, 0, 1], "box_map": box([0.5 + d, 0.0, 0.05])}]
    return {"timestamp": t, "objects": objs}


def test_s4_hysteresis_reduces_flips():
    from src.evaluation.s4_relation_eval import CountingEngine

    seq = [0.29, 0.32, 0.29, 0.33, 0.28, 0.32]
    plain, hyst = CountingEngine(use_support_plane=False), CountingEngine(use_support_plane=False, near_enter_m=0.30, near_exit_m=0.35)
    for k, d in enumerate(seq):
        plain.update(_payload(k, d))
        hyst.update(_payload(k, d))
    near = lambda e: sum(v for key, v in e.switches.items() if key[1] == "near")
    assert near(plain) == 5 and near(hyst) == 0


def test_s4_score_sweep_events(tmp_path):
    from src.evaluation.s4_relation_eval import events_eval, score, sweep
    from src.scene_graph.engine import SceneGraphEngine

    run = tmp_path / "B01"
    (run / "scene_graph").mkdir(parents=True)
    eng = SceneGraphEngine(use_support_plane=False)
    eng.update(_payload(0, 0.27))
    eng.save(run / "scene_graph" / "f0_scene_graph.json")
    gt = [{"bag_id": "B01", "frame_id": "f0", "subject": "book_01", "predicate": "near", "object": "mug_01", "gt": "1", "pred": "1"},
          {"bag_id": "B01", "frame_id": "f0", "subject": "book_01", "predicate": "on", "object": "mug_01", "gt": "0", "pred": "1"}]
    acc = {r["predicate"]: r for r in score(gt)}
    assert acc["near"]["f1"] == 1.0 and acc["on"]["fp"] == 1
    sw = {r["d_near_m"]: r["f1"] for r in sweep(gt, [run])}
    assert sw[0.25] == 0.0 and sw[0.30] == 1.0
    (run / "tracking").mkdir()
    (run / "tracking" / "event_log.jsonl").write_text("\n".join(json.dumps(e) for e in [
        {"timestamp": 100.0, "event": "APPEARED", "persistent_id": "mug_01", "label": "mug"},
        {"timestamp": 114.0, "event": "MOVED", "persistent_id": "mug_01", "label": "mug"},
        {"timestamp": 120.0, "event": "MOVED", "persistent_id": "book_01", "label": "book"}]))
    rows, summ = events_eval([{"sequence_id": "B01", "object_id": "mug_A", "event": "MOVED", "t_gt": "14.2"}], [run])
    s = {r["metric"]: r for r in summ}
    assert s["event_detection_rate"]["text"] == "100.0 % (1/1)" and s["false_event_rate"]["text"] == "50.0 % (1/2)"

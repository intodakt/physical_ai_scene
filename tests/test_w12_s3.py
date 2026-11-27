"""W12–W16 evaluation toolkit (S3 detector benchmark)."""

import json
import math

import numpy as np
import pytest

GT3 = [{"image_id": "b/f1", "class": "mug", "seen_unseen": "seen", "xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10},
       {"image_id": "b/f1", "class": "digital multimeter", "seen_unseen": "unseen", "xmin": 20, "ymin": 20, "xmax": 40, "ymax": 40}]


def test_s3_matching_and_scores():
    from src.evaluation.s3_detection_eval import match, score

    pred = [{"image_id": "b/f1", "class": "cup", "xmin": 1, "ymin": 1, "xmax": 10, "ymax": 10, "pred_score": 0.9},   # alias of mug
            {"image_id": "b/f1", "class": "mug", "xmin": 50, "ymin": 50, "xmax": 60, "ymax": 60, "pred_score": 0.5}]  # FP
    m, missed = match(GT3, pred)
    assert [r["tp_fp_fn"] for r in m] == ["tp", "fp"] and missed[0]["class"] == "digital multimeter"
    comp, _ = score(GT3, {"det": pred})
    seen = next(r for r in comp if r["split"] == "seen")
    unseen = next(r for r in comp if r["split"] == "unseen")
    assert (seen["tp"], seen["fp"], unseen["fn"]) == (1, 1, 1)


def test_s3_prompt_robustness_with_fake_detector(tmp_path):
    import cv2

    from src.evaluation.s3_detection_eval import prompts_test, summarise_prompts

    (tmp_path / "b" / "f1").mkdir(parents=True)
    cv2.imwrite(str(tmp_path / "b" / "f1" / "rgb.png"), np.zeros((50, 50, 3), np.uint8))

    class Fake:
        def __init__(self, cfg):
            self.p = cfg["prompts"][-1]

        def detect(self, img):   # only the exact name finds the multimeter
            return [{"bbox": [20, 20, 40, 40], "labels": [self.p], "detector_score": 0.7}] if self.p == "digital multimeter" else []

    forms = {"digital multimeter": {"exact": "digital multimeter", "functional": "device used to measure voltage"}}
    rows, distract = prompts_test("fake", tmp_path, GT3, {"prompts": ["mug"]}, forms, Fake)
    summ = {r["prompt_type"]: r["detected"] for r in summarise_prompts(rows)}
    assert summ == {"exact": "1/1", "functional": "0/1"}
    assert {d["selected"] for d in distract} == {"digital multimeter", "nothing"}


def test_s3_evaluation_uses_the_frozen_prompt_set():
    """The default config must be the W10 frozen set (with its SHA-256), not the editable desk.json."""
    from src.evaluation.s3_detection_eval import DEFAULT_CONFIG, frozen_config

    assert DEFAULT_CONFIG.exists()
    cfg = frozen_config()
    assert cfg.get("name") == "desk_v1" and cfg.get("sha256")

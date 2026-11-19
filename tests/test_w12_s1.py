"""W12–W16 evaluation toolkit (S1 dataset, calibration, measured TF)."""

import json
import math

import numpy as np
import pytest

def test_recording_plan_and_tf():
    from src.evaluation.s1_dataset import FAMILIES, measured_tf, recording_plan

    plan = recording_plan()
    assert len(plan) == sum(f[1] for f in FAMILIES.values()) == 45
    assert len({r["bag_id"] for r in plan}) == 45
    assert {r["split"] for r in plan} == {"dev", "test"}
    T = np.array(measured_tf(1.0, 30.0)["T_map_camera_link"])
    x_axis = T[:3, 0]                                            # camera_link x = viewing direction
    assert x_axis[2] == pytest.approx(-math.sin(math.radians(30)), abs=1e-6) and T[2, 3] == 1.0


def test_calibration_error_stats():
    import cv2

    from src.sensors.calibration import board_points, calibrate

    K = np.array([[500.0, 0, 320], [0, 500, 240], [0, 0, 1]])
    views = []
    for k in range(6):
        rvec = np.array([0.2 * (k % 3 - 1), 0.15 * (k % 2), 0.05 * k])
        tvec = np.array([-0.1 + 0.02 * k, -0.06, 0.6 + 0.05 * k])
        p, _ = cv2.projectPoints(board_points(), rvec, tvec, K, np.zeros(5))
        views.append(p.reshape(-1, 2) + np.random.default_rng(k).normal(0, 0.2, (54, 2)))
    st = calibrate(views, (640, 480)).error_stats()
    assert st["n_points"] == 6 * 54 and 0 < st["mean_px"] < 1.0 and st["max_px"] >= st["median_px"]


def test_measured_tf_matches_pipeline_convention(tmp_path):
    from src.evaluation.common import load_tf
    from src.evaluation.s1_dataset import measured_tf, write_tf
    from src.fusion_3d.transforms import T_map_optical_from_static_tf

    tf = measured_tf(0.9, 40, 0.1, 0.3, 15, 2)
    A = load_tf(write_tf(tf, tmp_path / "measured_tf.yaml"))
    assert np.abs(A - T_map_optical_from_static_tf(tf["xyz"], tf["rpy"])).max() < 1e-4

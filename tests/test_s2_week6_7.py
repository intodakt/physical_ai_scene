"""Week 6 (bag loader, static sequence) and Week 7 (depth cleaning, transparent objects)."""

import json

import numpy as np
import pytest

from src.fusion_3d.depth_reliability import assess
from src.fusion_3d.evaluate import evaluate_against_ground_truth
from src.fusion_3d.object_instance import ObjectInstance3D
from src.fusion_3d.pipeline import load_config, process_frame
from src.fusion_3d.run_sequence import run_sequence
from src.preprocessing.depth_cleaning import remove_flying_pixels, temporal_median_depth
from src.preprocessing.frame_loader import load_frame, load_semantic_observations
from src.preprocessing.intrinsics import CameraIntrinsics
from src.preprocessing.mask_utils import erode
from src.preprocessing.mock_data import generate, generate_sequence

INTR = CameraIntrinsics(640, 480, 615.0, 615.0, 320.0, 240.0)


def _run(d):
    fr = load_frame(d)
    res = process_frame(fr, load_semantic_observations(d / "observation.json"), load_config())
    gt = json.loads((d / "ground_truth.json").read_text())
    ev = evaluate_against_ground_truth(res.objects, gt)
    glass = next(o for o in res.objects if o.semantic_label == "glass")
    row = next(r for r in ev["per_object"] if r["label"] == "glass")
    return res, ev, glass, row


# ------------------------------------------------------------------ depth cleaning
def test_flying_pixel_filter_removes_spikes_keeps_surfaces():
    d = np.full((60, 80), 0.8, np.float32)
    d[30, 40] = 0.95                      # isolated mixed pixel
    d[:, 60:] = 1.2                       # genuine step edge
    f = remove_flying_pixels(d)
    assert f[30, 40] == 0
    assert (f[5:-5, 5:35] == np.float32(0.8)).all() and (f[5:-5, 65:75] == np.float32(1.2)).all()


def test_temporal_median_fills_dropouts_but_not_glass():
    rng = np.random.default_rng(0)
    frames = []
    for _ in range(5):
        d = np.full((20, 20), 0.8, np.float32) + rng.normal(0, 0.002, (20, 20)).astype(np.float32)
        d[rng.random((20, 20)) < 0.1] = 0          # random dropouts
        d[:5, :5] = 0                               # always missing (glass)
        frames.append(d)
    m = temporal_median_depth(frames)
    assert (m[5:, 5:] > 0).mean() > 0.99 and (m[:5, :5] == 0).all()   # a pixel missing in ≥3/5 frames stays empty
    v = m[5:, 5:]
    assert abs(float(v[v > 0].mean()) - 0.8) < 0.002


def test_erode_shrinks_mask():
    m = np.zeros((20, 20), bool)
    m[5:15, 5:15] = True
    assert erode(m, 2).sum() == 6 * 6


# ------------------------------------------------------------------ reliability cues
def _plane_scene():
    """Camera looking straight down at a desk 0.8 m away; object 'cylinder' area in the middle."""
    depth = np.full((480, 640), 0.8, np.float32)
    mask = np.zeros((480, 640), bool)
    mask[200:280, 280:360] = True
    plane = np.array([0.0, 0.0, -1.0, 0.8])   # z = 0.8 in camera frame, normal towards camera
    return depth, mask, plane


def test_opaque_object_is_ok():
    depth, mask, plane = _plane_scene()
    depth[mask] = 0.7  # 10 cm above the desk
    r = assess(depth, mask, INTR, plane)
    assert r.status == "ok" and r.plane_leak_ratio == 0 and r.genuine_ratio > 0.99


def test_holes_are_flagged():
    depth, mask, plane = _plane_scene()
    depth[mask] = 0.7
    depth[mask & (np.random.default_rng(0).random(depth.shape) < 0.8)] = 0
    r = assess(depth, mask, INTR, plane)
    assert r.status == "transparent_suspected" and any("holes" in x for x in r.reasons)


def test_see_through_is_flagged():
    depth, mask, plane = _plane_scene()   # depth inside mask == desk: the camera saw through it
    r = assess(depth, mask, INTR, plane)
    assert r.status == "transparent_suspected" and r.plane_leak_ratio > 0.9
    assert any("see-through" in x for x in r.reasons)


def test_no_depth_is_flagged():
    depth, mask, plane = _plane_scene()
    depth[mask] = 0
    assert assess(depth, mask, INTR, plane).status == "no_depth"


# ------------------------------------------------------------------ end-to-end on mock frames
@pytest.mark.parametrize("profile,mode,fail,expect_source", [
    ("realsense", "holes", None, "depth"),          # 15 % genuine glass pixels left
    ("zed_mini", "see_through", None, "depth"),
    ("zed_mini", "see_through", 1.0, "mask_plane"),  # fully transparent: no genuine depth
    ("zed_mini", "holes", 1.0, "mask_plane"),
])
def test_glass_is_detected_and_localized(tmp_path, profile, mode, fail, expect_source):
    d = generate(tmp_path / "f", seed=3, profile=profile, glass_mode=mode, glass_failure=fail)
    res, ev, glass, row = _run(d)
    assert ev["recall"] == 1.0
    assert glass.depth_status in ("transparent_suspected", "no_depth")
    assert glass.geometry_source == expect_source
    assert row["box_center_error_m"] < 0.02
    assert glass.fusion_weights["depth"] < 0.15
    others = [o for o in res.objects if o.semantic_label != "glass"]
    assert all(o.depth_status == "ok" and o.geometry_source == "depth" for o in others)
    back = ObjectInstance3D.from_json(glass.to_json())
    assert back.depth_reliability == glass.depth_reliability


def test_static_sequence_is_stable(tmp_path):
    generate_sequence(tmp_path / "seq", n_frames=3, glass_failure=1.0)
    rep = run_sequence(tmp_path / "seq", tmp_path / "out", temporal_median=True)
    assert rep["objects_per_frame"] == [5, 5, 5]
    for lab, s in rep["stability"].items():
        assert s["detection_rate"] == 1.0
        assert s["jitter_rms_mm"] < 5.0, (lab, s)
    assert rep["stability"]["glass"]["depth_status"] == "transparent_suspected"
    assert rep["temporal_median"]["mean_box_center_error_m"] < 0.015
    assert (tmp_path / "out" / "sequence_report.json").exists()


# ------------------------------------------------------------------ ROS 2 bag
@pytest.mark.parametrize("profile", ["zed_mini", "realsense"])
def test_bag_round_trip(tmp_path, profile):
    pytest.importorskip("rosbags")
    from src.preprocessing.bag_reader import export_frames, iter_frames, write_bag

    gen_profile = "zed_mini" if profile == "zed_mini" else "realsense"
    dirs = generate_sequence(tmp_path / "seq", n_frames=3, profile=gen_profile, glass_mode="holes")
    frames = [load_frame(d) for d in dirs]
    bag = write_bag(frames, tmp_path / "bag", profile=profile)
    got = list(iter_frames(bag, profile))
    assert len(got) == 3
    for a, b in zip(frames, got):
        assert np.array_equal(a.rgb, b.rgb)
        assert b.intrinsics.fx == a.intrinsics.fx and b.intrinsics.cx == a.intrinsics.cx
        da = np.nan_to_num(a.depth_raw.astype(np.float32) * (a.intrinsics.depth_scale if a.depth_raw.dtype == np.uint16 else 1))
        db = np.nan_to_num(b.depth_raw.astype(np.float32) * (b.intrinsics.depth_scale if b.depth_raw.dtype == np.uint16 else 1))
        assert np.allclose(da, db, atol=1e-3)
    paths, stats = export_frames(bag, tmp_path / "frames", profile)
    assert stats.synced == 3 and stats.dropped == 0 and len(paths) == 3
    assert load_frame(paths[0]).rgb.shape == frames[0].rgb.shape


def test_bag_rejects_unsynced_pairs(tmp_path):
    pytest.importorskip("rosbags")
    from src.preprocessing.bag_reader import BagStats, iter_frames, write_bag

    d = generate(tmp_path / "f", profile="zed_mini")
    bag = write_bag([load_frame(d)], tmp_path / "bag", depth_offset_s=0.2)  # 200 ms apart
    st = BagStats()
    assert list(iter_frames(bag, "zed_mini", max_dt=0.02, stats=st)) == []
    assert st.dropped == 1

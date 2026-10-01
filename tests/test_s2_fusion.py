import json
import math

import numpy as np
import pytest

from src.fusion_3d.fusion import ModalityQuality, fused_confidence, fusion_weights
from src.fusion_3d.geometry import gravity_aligned_bbox
from src.fusion_3d.object_instance import ObjectInstance3D, validate
from src.fusion_3d.pipeline import load_config, process_frame
from src.preprocessing.frame_loader import SemanticObservation, SynchronizedFrame
from src.preprocessing.intrinsics import CameraIntrinsics
from src.preprocessing.mask_utils import rle_decode, rle_encode

INTR = CameraIntrinsics(640, 480, 615.0, 615.0, 320.0, 240.0)


def _flat_scene(depth_value=0.8, hole=False):
    """Box-like object 5 cm in front of a flat background."""
    depth = np.full((480, 640), depth_value, np.float32)
    mask = np.zeros((480, 640), bool)
    mask[200:280, 280:360] = True
    depth[mask] = depth_value - 0.05
    if hole:
        depth[mask] = 0.0
    rgb = np.random.default_rng(0).integers(60, 200, (480, 640, 3), dtype=np.uint8)
    frame = SynchronizedFrame(rgb=rgb, depth_raw=depth, intrinsics=INTR)
    obs = SemanticObservation(bbox=[280, 200, 359, 279], mask=mask, labels=["box"], score=0.9)
    return frame, obs


def _cfg():
    cfg = load_config()
    cfg["tf_map_camera_link"] = None
    cfg["support_plane"]["enabled"] = False
    return cfg


def test_adaptive_weight_drops_when_depth_is_poor():
    good = ModalityQuality(rgb=0.8, depth=0.95, semantic=0.9)
    bad = ModalityQuality(rgb=0.8, depth=0.10, semantic=0.9)
    wg, wb = fusion_weights(good, "adaptive"), fusion_weights(bad, "adaptive")
    assert wb["depth"] < wg["depth"]
    for w in (wg, wb):
        assert math.isclose(sum(w.values()), 1.0) and min(w.values()) >= 0
        assert w["lidar"] == 0.0  # G1 has no LiDAR


def test_fixed_weights_are_equal():
    w = fusion_weights(ModalityQuality(rgb=0.1, depth=0.9, semantic=0.5), "fixed")
    assert w["rgb"] == w["depth"] == w["semantic"] == pytest.approx(1 / 3)
    assert 0 <= fused_confidence(ModalityQuality(rgb=0.1, depth=0.9, semantic=0.5), w) <= 1


def test_missing_depth_gives_no_nan_geometry():
    # Guide §30: missing depth decreases depth weight and does not produce NaN geometry.
    frame, obs = _flat_scene(hole=True)
    res = process_frame(frame, [obs], _cfg())
    assert res.objects == []
    assert res.rejected and res.rejected[0]["depth_confidence"] == 0.0
    assert res.rejected[0]["fusion_weights"]["depth"] < 0.1


def test_flat_object_centroid_and_contract():
    frame, obs = _flat_scene()
    res = process_frame(frame, [obs], _cfg())
    assert len(res.objects) == 1
    o = res.objects[0]
    validate(o.to_dict())
    assert o.depth_confidence == 1.0
    assert o.centroid[2] == pytest.approx(0.75, abs=1e-3)
    # 80 px at 0.75 m / 615 px -> ~9.6 cm square
    assert max(o.box_dimensions) == pytest.approx(80 * 0.75 / 615, abs=0.01)


def test_outlier_removal_drops_flying_pixels():
    frame, obs = _flat_scene()
    depth = frame.depth_raw
    rng = np.random.default_rng(1)
    ys, xs = np.nonzero(obs.mask)
    idx = rng.choice(len(ys), 40, replace=False)
    depth[ys[idx], xs[idx]] = 0.75 + rng.uniform(0.1, 0.4, 40)  # stray far points
    res = process_frame(frame, [obs], _cfg())
    assert res.objects[0].aabb["max"][2] < 0.76


def test_serialize_deserialize_no_field_loss():
    # Guide §21: S2 -> S4/S6 serialize/deserialize with no field loss.
    frame, obs = _flat_scene()
    o = process_frame(frame, [obs], _cfg()).objects[0]
    s = o.to_json()
    back = ObjectInstance3D.from_json(s)
    assert back == o
    assert set(json.loads(s)) >= {"centroid", "box_dimensions", "semantic_label", "depth_confidence"}
    with pytest.raises(ValueError):
        ObjectInstance3D.from_dict({**o.to_dict(), "bogus": 1})


def test_rle_round_trip():
    m = np.random.default_rng(0).random((37, 53)) > 0.6
    m[0, 0] = True
    assert np.array_equal(rle_decode(rle_encode(m)), m)


def test_gravity_box_of_rotated_cuboid():
    rng = np.random.default_rng(0)
    p = rng.uniform([-0.1, -0.03, 0.0], [0.1, 0.03, 0.05], (3000, 3))
    a = np.deg2rad(30)
    R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    box = gravity_aligned_bbox(p @ R.T + [0.5, 0.2, 0.0])
    w, h, d = box["dimensions"]
    assert w == pytest.approx(0.2, abs=0.01)
    assert h == pytest.approx(0.05, abs=0.005)
    assert d == pytest.approx(0.06, abs=0.01)
    assert np.allclose(box["center"], [0.5, 0.2, 0.025], atol=0.01)


def test_obb_on_planar_cloud_is_not_degenerate():
    from src.fusion_3d.geometry import oriented_bbox, to_pcd

    g = np.stack(np.meshgrid(np.linspace(0, 0.2, 30), np.linspace(0, 0.1, 20)), -1).reshape(-1, 2)
    obb = oriented_bbox(to_pcd(np.c_[g, np.full(len(g), 0.7)]))
    ext = sorted(obb["extent"], reverse=True)
    assert ext[0] == pytest.approx(0.2, abs=1e-3) and ext[1] == pytest.approx(0.1, abs=1e-3)

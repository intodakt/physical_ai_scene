import numpy as np

from src.fusion_3d.projection import deproject_mask, deproject_pixels, project_points
from src.fusion_3d.transforms import (
    T_map_optical_from_static_tf,
    apply_transform,
    invert_transform,
)
from src.preprocessing.intrinsics import CameraIntrinsics, load_intrinsics

INTR = CameraIntrinsics(640, 480, 615.0, 615.0, 320.0, 240.0)


def test_known_point_projects_to_expected_pixel():
    # Guide §30: known 3D point projects to the expected pixel within tolerance.
    p = np.array([[0.10, -0.05, 0.80]])
    uv = project_points(p, INTR)[0]
    assert np.allclose(uv, [320 + 0.10 * 615 / 0.8, 240 - 0.05 * 615 / 0.8], atol=1e-6)
    back = deproject_pixels(uv[0], uv[1], 0.80, INTR)
    assert np.allclose(back, p[0], atol=1e-9)


def test_deproject_mask_uses_only_masked_valid_depth():
    depth = np.full((480, 640), 0.5, np.float32)
    depth[100, 100] = 0.0  # hole inside the mask
    mask = np.zeros_like(depth, bool)
    mask[95:105, 95:105] = True
    pts, uv = deproject_mask(depth, mask, INTR)
    assert len(pts) == 99
    assert np.all(pts[:, 2] == 0.5)
    assert not ((uv[:, 0] == 100) & (uv[:, 1] == 100)).any()


def test_fake_circle_centroid():
    # Week-3 exercise: fake depth + fake 2D circle -> 3D centre.
    depth = np.full((480, 640), 1.0, np.float32)
    v, u = np.mgrid[:480, :640]
    mask = (u - 400) ** 2 + (v - 300) ** 2 < 30 ** 2
    pts, _ = deproject_mask(depth, mask, INTR)
    c = pts.mean(0)
    assert np.allclose(c, [(400 - 320) / 615, (300 - 240) / 615, 1.0], atol=1e-3)


def test_transform_round_trip():
    # Guide §30: map -> sensor -> map returns the original point.
    T = T_map_optical_from_static_tf([0.0, 0.0, 0.8], [0.0, 0.5, 0.0])
    p = np.random.default_rng(0).normal(size=(50, 3))
    assert np.allclose(apply_transform(invert_transform(T), apply_transform(T, p)), p)


def test_optical_axis_points_down_and_forward():
    # Camera pitched down: optical +z must point forward (+x) and down (-z) in map.
    T = T_map_optical_from_static_tf([0, 0, 0.8], [0, 0.5, 0])
    z_axis = T[:3, 2]
    assert z_axis[0] > 0 and z_axis[2] < 0


def test_load_ros_camera_info_yaml(tmp_path):
    f = tmp_path / "ci.yaml"
    f.write_text("width: 640\nheight: 480\nk: [600.0, 0.0, 321.0, 0.0, 601.0, 239.0, 0.0, 0.0, 1.0]\n")
    intr = load_intrinsics(f)
    assert (intr.fx, intr.fy, intr.cx, intr.cy) == (600.0, 601.0, 321.0, 239.0)

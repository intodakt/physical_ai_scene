"""Mock S1 + S3 data so S2 can be developed before real bags/masks exist.

Builds a tabletop scene in the ``map`` frame (z up, desk top at z = 0),
renders it with Open3D ray casting from a RealSense-like camera mounted
0.6 m above the desk and pitched 45 deg down, and writes:

    <out_dir>/rgb.png                     S1 colour image
    <out_dir>/depth.png                   S1 aligned depth, uint16 millimetres
    <out_dir>/camera_intrinsics.yaml      S1 intrinsics (D435-like)
    <out_dir>/frame_meta.json             timestamp + T_map_camera (S1 TF)
    <out_dir>/semantic_observations.json  S3 SemanticObservation list (RLE masks)
    <out_dir>/ground_truth.json           true centres/sizes for evaluation

Realistic depth artefacts are added on purpose: range-dependent noise,
random dropouts, "flying pixels" on depth edges, a transparent glass with
most depth missing, and S3 masks dilated by 2 px (SAM bleed onto the desk).

Run:  python -m src.preprocessing.mock_data --out data/mock/frame_000
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import open3d as o3d
from PIL import Image

from ..fusion_3d.transforms import T_map_optical_from_static_tf
from .intrinsics import CameraIntrinsics, save_intrinsics
from .mask_utils import rle_encode

INTR = CameraIntrinsics(width=640, height=480, fx=615.0, fy=615.0, cx=320.0, cy=240.0)
CAMERA_XYZ = [0.0, 0.0, 0.6]
CAMERA_RPY = [0.0, np.deg2rad(45.0), 0.0]

# name, primitive, size, centre on desk (x, y), yaw (deg), colour, S3 labels, detector score, depth dropout
OBJECTS = [
    dict(name="laptop", kind="laptop", size=(0.22, 0.32, 0.02), xy=(0.70, 0.17), yaw=-8,
         color=(70, 70, 78), labels=["laptop", "notebook computer"], score=0.93, dropout=0.0),
    dict(name="mug", kind="cylinder", size=(0.04, 0.10), xy=(0.56, -0.10), yaw=0,
         color=(200, 60, 50), labels=["mug", "cup", "coffee mug"], score=0.88, dropout=0.0),
    dict(name="book", kind="box", size=(0.15, 0.22, 0.035), xy=(0.70, -0.26), yaw=20,
         color=(40, 90, 170), labels=["book", "notebook"], score=0.81, dropout=0.0),
    dict(name="multimeter", kind="box", size=(0.15, 0.08, 0.045), xy=(0.47, 0.10), yaw=-25,
         color=(235, 190, 30), labels=["multimeter", "remote control"], score=0.62, dropout=0.0),
    dict(name="glass", kind="cylinder", size=(0.035, 0.12), xy=(0.62, 0.36), yaw=0,
         color=(190, 215, 225), labels=["glass", "cup"], score=0.71, dropout=0.85),
]


def _rotz(yaw_deg: float) -> np.ndarray:
    a = np.deg2rad(yaw_deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


def _box(sx, sy, sz, center, yaw=0.0):
    m = o3d.geometry.TriangleMesh.create_box(sx, sy, sz)
    m.translate([-sx / 2, -sy / 2, -sz / 2])
    m.rotate(_rotz(yaw), center=[0, 0, 0])
    m.translate(center)
    return m


def _build_object(spec):
    x, y = spec["xy"]
    yaw = spec["yaw"]
    if spec["kind"] == "box":
        sx, sy, sz = spec["size"]
        return [_box(sx, sy, sz, [x, y, sz / 2], yaw)], {
            "center": [x, y, sz / 2], "dimensions_xyz": [sx, sy, sz], "yaw_deg": yaw}
    if spec["kind"] == "cylinder":
        r, h = spec["size"]
        m = o3d.geometry.TriangleMesh.create_cylinder(radius=r, height=h, resolution=48)
        m.translate([x, y, h / 2])
        return [m], {"center": [x, y, h / 2], "dimensions_xyz": [2 * r, 2 * r, h], "yaw_deg": 0}
    if spec["kind"] == "laptop":
        dx, dy, t = spec["size"]
        base = _box(dx, dy, t, [x, y, t / 2], yaw)
        # Screen hinged at the far edge, leaning back 15 deg from vertical.
        sh = 0.17
        screen = o3d.geometry.TriangleMesh.create_box(0.008, dy, sh)
        screen.translate([-0.004, -dy / 2, 0])
        lean = np.deg2rad(15)
        Ry = np.array([[np.cos(lean), 0, np.sin(lean)], [0, 1, 0], [-np.sin(lean), 0, np.cos(lean)]])
        screen.rotate(Ry, center=[0, 0, 0])
        screen.translate([dx / 2, 0, t])
        screen.rotate(_rotz(yaw), center=[0, 0, 0])
        screen.translate([x, y, 0])
        pts = np.vstack([np.asarray(base.vertices), np.asarray(screen.vertices)])
        lo, hi = pts.min(0), pts.max(0)
        return [base, screen], {"center": ((lo + hi) / 2).tolist(),
                                "dimensions_xyz": (hi - lo).tolist(), "yaw_deg": yaw}
    raise ValueError(spec["kind"])


def generate(out_dir: str | Path, seed: int = 0, timestamp: float = 1758355200.0) -> Path:
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    scene = o3d.t.geometry.RaycastingScene()
    geom_owner = {}  # geometry id -> object index (-1 desk, -2 floor)
    desk = _box(1.4, 1.2, 0.03, [0.7, 0.0, -0.015])
    floor = _box(6.0, 6.0, 0.01, [1.0, 0.0, -0.76])
    for mesh, owner in ((desk, -1), (floor, -2)):
        gid = scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
        geom_owner[gid] = owner
    gt = []
    for i, spec in enumerate(OBJECTS):
        meshes, info = _build_object(spec)
        for m in meshes:
            gid = scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(m))
            geom_owner[gid] = i
        gt.append({"name": spec["name"], **info})

    # Rays in the optical frame -> map frame
    T = T_map_optical_from_static_tf(CAMERA_XYZ, CAMERA_RPY)
    H, W = INTR.height, INTR.width
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    d_opt = np.stack([(u - INTR.cx) / INTR.fx, (v - INTR.cy) / INTR.fy, np.ones_like(u, float)], -1)
    norm = np.linalg.norm(d_opt, axis=-1, keepdims=True)
    d_opt_n = d_opt / norm
    d_map = d_opt_n @ T[:3, :3].T
    origin = np.broadcast_to(T[:3, 3], d_map.shape)
    rays = o3d.core.Tensor(np.concatenate([origin, d_map], -1).astype(np.float32))
    hit = scene.cast_rays(rays)
    t_hit = hit["t_hit"].numpy()
    gids = hit["geometry_ids"].numpy()
    normals = hit["primitive_normals"].numpy()
    hit_ok = np.isfinite(t_hit)
    depth = np.where(hit_ok, t_hit * d_opt_n[..., 2], 0.0)  # z in optical frame
    owner = np.full((H, W), -3, dtype=int)
    for gid, o in geom_owner.items():
        owner[(gids == gid) & hit_ok] = o

    # ---- RGB: Lambertian shading + texture noise -------------------------
    light = np.array([0.3, -0.4, 1.0])
    light /= np.linalg.norm(light)
    shade = 0.45 + 0.55 * np.clip(np.abs(normals @ light), 0, 1)
    base = np.zeros((H, W, 3))
    base[owner == -3] = (40, 40, 45)
    base[owner == -2] = (95, 95, 100)
    wood = 0.92 + 0.08 * np.sin(u / 7.0 + 0.3 * np.sin(v / 23.0))
    base[owner == -1] = np.array([176, 132, 88]) * wood[owner == -1][:, None]
    for i, spec in enumerate(OBJECTS):
        base[owner == i] = spec["color"]
    rgb = base * shade[..., None] + rng.normal(0, 3.0, base.shape)
    # Laptop screen glow and keyboard texture for realism
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    # ---- depth artefacts ---------------------------------------------------
    noisy = depth + rng.normal(0, 1.0, depth.shape) * (0.0008 + 0.0018 * depth ** 2)
    edges = np.zeros((H, W), bool)
    dz = np.abs(np.diff(depth, axis=0)) > 0.03
    edges[1:] |= dz
    edges[:-1] |= dz
    dx = np.abs(np.diff(depth, axis=1)) > 0.03
    edges[:, 1:] |= dx
    edges[:, :-1] |= dx
    flying = edges & (rng.random((H, W)) < 0.35)
    noisy[flying] = depth[flying] + rng.uniform(0.02, 0.12, flying.sum())  # mixed pixels
    noisy[rng.random((H, W)) < 0.015] = 0.0  # random dropouts
    for i, spec in enumerate(OBJECTS):
        if spec["dropout"] > 0:
            m = (owner == i) & (rng.random((H, W)) < spec["dropout"])
            noisy[m] = 0.0
    noisy[noisy > 4.0] = 0.0
    depth_mm = np.clip(noisy * 1000.0, 0, 65535).astype(np.uint16)

    # ---- S3 mock observations -------------------------------------------
    obs = []
    for i, spec in enumerate(OBJECTS):
        m = owner == i
        if not m.any():
            continue
        # SAM-style imprecision: dilate by 2 px
        dil = m.copy()
        for _ in range(2):
            d = dil.copy()
            d[1:] |= dil[:-1]; d[:-1] |= dil[1:]; d[:, 1:] |= dil[:, :-1]; d[:, :-1] |= dil[:, 1:]
            dil = d
        ys, xs = np.nonzero(m)
        k = len(spec["labels"])
        scores = [round(spec["score"] * (0.55 ** j), 3) for j in range(k)]
        obs.append({
            "id": f"det_{i}",
            "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "mask": rle_encode(dil),
            "labels": spec["labels"],
            "label_scores": scores,
            "score": spec["score"],
            "timestamp": timestamp,
        })

    Image.fromarray(rgb).save(out / "rgb.png")
    Image.fromarray(depth_mm).save(out / "depth.png")
    save_intrinsics(INTR, out / "camera_intrinsics.yaml")
    (out / "frame_meta.json").write_text(json.dumps({
        "timestamp": timestamp,
        "frame_id": "camera_color_optical_frame",
        "T_map_camera": T.tolist(),
        "note": "MOCK frame generated by src/preprocessing/mock_data.py (stand-in for S1 bag)",
    }, indent=2))
    (out / "semantic_observations.json").write_text(json.dumps({
        "timestamp": timestamp,
        "source": "MOCK S3 (stand-in for YOLO-World + MobileSAM)",
        "observations": obs,
    }))
    (out / "ground_truth.json").write_text(json.dumps({"frame": "map", "objects": gt}, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/mock/frame_000")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    print("mock frame written to", generate(args.out, args.seed))


if __name__ == "__main__":
    main()

"""Real-image geometry and looks for the virtual twin.

S2's 3D boxes come from depth. On dark, glossy desks most objects are ``transparent_suspected`` and
their boxes are partial (a phone measured 5 cm long). The camera image and S3's mask are still good,
and with S1's measured camera pose (``T_map_camera``) every mask pixel can be followed down its viewing
ray to the desk. That gives:

* flat objects (phones, calculators, remotes, books, pads): the footprint = minimum-area rectangle of
  the mask projected onto the plane z = top height, and a top-down photo of the object (the image
  re-sampled onto that rectangle) as its texture;
* tall objects whose depth failed (apple, mug, egg, controller): S2's own mask + desk-plane estimate
  (``src/fusion_3d/mask_plane.py``: contact line, RANSAC circle, height from the top rim);
* a cut-out of the object (RGBA crop of the mask) for a billboard standing on the desk.

All of this only changes how the twin is built and drawn; S2 still measures every rendered frame.
"""

from __future__ import annotations

import base64
import io
import json
import math
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

FLAT_WORDS = ("phone", "smartphone", "calculator", "remote", "book", "notebook", "pad", "mat", "paper", "card",
              "keyboard", "tablet", "plate", "tray", "wallet", "passport")
TALL_MAX_FLAT_M = 0.045          # a measured height below this is treated as a flat object
TEX_PX = 256


def _png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class View:
    """One recorded frame: RGB, intrinsics, camera pose (map <- optical) and S3's masks by detection id."""

    def __init__(self, frame_dir: Path, T_map_camera=None):
        from src.preprocessing.intrinsics import load_intrinsics

        self.dir = Path(frame_dir)
        self.rgb = np.array(Image.open(self.dir / "rgb.png").convert("RGB"))
        self.intr = load_intrinsics(self.dir / "camera_intrinsics.yaml")
        if T_map_camera is None:
            meta = json.loads((self.dir / "frame_meta.json").read_text(encoding="utf-8")) \
                if (self.dir / "frame_meta.json").exists() else {}
            T_map_camera = meta.get("T_map_camera")
        if T_map_camera is None:
            raise ValueError("no camera pose for this frame")
        self.T = np.asarray(T_map_camera, float)
        self.R, self.o = self.T[:3, :3], self.T[:3, 3]
        self.masks = {}
        obs = self.dir / "observation.json"
        if obs.exists():
            data = json.loads(obs.read_text(encoding="utf-8"))
            for det in data.get("detections", []):
                if det.get("mask_status", "ok") == "ok" and isinstance(det.get("mask"), str):
                    p = self.dir / det["mask"]
                    if p.exists():
                        self.masks[str(det["detection_id"])] = p

    @classmethod
    def try_open(cls, frame_dir, T_map_camera=None) -> Optional["View"]:
        try:
            return cls(frame_dir, T_map_camera)
        except Exception:
            return None

    def mask(self, det_id) -> Optional[np.ndarray]:
        p = self.masks.get(str(det_id))
        if p is None:
            return None
        m = np.array(Image.open(p).convert("L")) > 127
        if m.shape != self.rgb.shape[:2]:
            m = np.array(Image.fromarray(m.astype(np.uint8) * 255).resize(self.rgb.shape[1::-1], Image.NEAREST)) > 127
        return m if m.sum() >= 30 else None

    # -------------------------------------------------- rays and planes
    def rays_map(self, u, v) -> np.ndarray:
        i = self.intr
        d = np.stack([(np.asarray(u, float) - i.cx) / i.fx, (np.asarray(v, float) - i.cy) / i.fy, np.ones(len(u))], -1)
        return d @ self.R.T

    def to_plane(self, u, v, z: float) -> np.ndarray:
        """Map-frame XY where the viewing rays of pixels (u, v) cross the plane z."""
        d = self.rays_map(u, v)
        dz = np.where(np.abs(d[:, 2]) < 1e-9, np.nan, d[:, 2])
        t = (z - self.o[2]) / dz
        p = self.o + d * t[:, None]
        ok = np.isfinite(t) & (t > 0)
        return p[ok, :2]

    def project(self, P: np.ndarray):
        """Map-frame points -> pixel (u, v) and depth."""
        c = (P - self.o) @ self.R
        z = c[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = self.intr.fx * c[:, 0] / z + self.intr.cx
            v = self.intr.fy * c[:, 1] / z + self.intr.cy
        return u, v, z

    def plane_camera(self) -> np.ndarray:
        """The desk (map z = 0) as n.p + d = 0 in the optical frame, for S2's mask_plane estimator."""
        n = self.R.T @ np.array([0.0, 0.0, 1.0])
        p0 = self.R.T @ (np.zeros(3) - self.o)
        return np.r_[n, -float(n @ p0)]


def _plane_points(view: "View", u, v, z: float, keep_shape: bool = False) -> np.ndarray:
    """Like View.to_plane, but keeps one row per pixel (NaN where the ray misses) when keep_shape."""
    d = view.rays_map(u, v)
    dz = np.where(np.abs(d[:, 2]) < 1e-9, np.nan, d[:, 2])
    t = (z - view.o[2]) / dz
    p = (view.o + d * t[:, None])[:, :2]
    p[~(np.isfinite(t) & (t > 0))] = np.nan
    return p


def is_flat(label: str, height_m: float) -> bool:
    return any(w in label for w in FLAT_WORDS) or height_m < TALL_MAX_FLAT_M


def flat_geometry(view: View, mask: np.ndarray, height_m: float) -> Optional[dict]:
    """Footprint of a flat object from its mask projected onto its top plane, plus a top-down photo."""
    from src.fusion_3d.geometry import min_area_rect

    from src.preprocessing.mask_utils import erode

    h = float(min(max(height_m, 0.004), 0.04))
    core = erode(mask, 2)                       # undo SAM's ~2 px bleed onto the desk
    if core.sum() < 30:
        core = mask
    vs, us = np.nonzero(core)
    step = max(1, int(math.sqrt(len(us) / 6000)))
    us, vs = us[::step], vs[::step]
    pts = _plane_points(view, us + 0.5, vs + 0.5, h)
    # the camera also sees the object's front side face; on the top plane those pixels land in front of
    # the object. Per image column, the lowest mask pixel touches the desk (z = 0): nothing of the top
    # surface can lie closer to the camera than that contact point.
    fwd = view.R[:2, 2] / (np.linalg.norm(view.R[:2, 2]) or 1.0)
    cols = np.unique(us)
    H = core.shape[0]
    low = H - 1 - np.argmax(core[::-1, cols], axis=0)
    contact = _plane_points(view, cols + 0.5, low + 0.5, 0.0, keep_shape=True)
    front = dict(zip(cols.tolist(), (contact @ fwd).tolist()))
    keep = np.array([np.isfinite(p @ fwd) and p @ fwd >= front.get(int(u), -np.inf) - 1e-4 for p, u in zip(pts, us)])
    xy = pts[keep] if keep.sum() >= 20 else pts
    xy = xy[np.isfinite(xy).all(1)]
    if len(xy) < 20:
        return None
    yaw, (la, lb), (cx, cy) = min_area_rect(xy, 1.0)
    if lb > la:
        la, lb, yaw = lb, la, yaw + math.pi / 2
    if not (0.01 < la < 0.8 and 0.005 < lb < 0.6):
        return None
    # top-down texture: rows run from +a (image top) to -a, columns from +b (left) to -b, so that on the
    # page's plane (three.js) the image top points along the box's +x (yaw) direction
    res = max(la, lb) / TEX_PX
    na, nb = max(2, int(round(la / res))), max(2, int(round(lb / res)))
    a = (np.arange(na)[::-1] + 0.5) * res - la / 2
    b = (np.arange(nb)[::-1] + 0.5) * res - lb / 2
    A, B = np.meshgrid(a, b, indexing="ij")
    c, s = math.cos(yaw), math.sin(yaw)
    X, Y = cx + c * A - s * B, cy + s * A + c * B
    P = np.stack([X.ravel(), Y.ravel(), np.full(X.size, h)], -1)
    u, v, z = view.project(P)
    H, W = mask.shape
    ui, vi = np.round(u).astype(int), np.round(v).astype(int)
    ok = (z > 0) & (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
    inside = np.zeros(len(P), bool)
    inside[ok] = mask[vi[ok], ui[ok]]
    colour = np.median(view.rgb[mask], axis=0)
    tex = np.tile(colour, (len(P), 1))
    tex[inside] = view.rgb[vi[inside], ui[inside]]
    img = Image.fromarray(tex.reshape(na, nb, 3).astype(np.uint8))
    return {"xy": (float(cx), float(cy)), "yaw_deg": math.degrees(yaw), "size": (float(la), float(lb), h),
            "texture": _png(img), "fill": float(inside.mean())}


def tall_geometry(view: View, mask: np.ndarray) -> Optional[dict]:
    """S2's own mask + desk-plane estimate (round footprint + height), used when the depth failed."""
    from src.fusion_3d.mask_plane import estimate_from_mask

    est = estimate_from_mask(mask, view.intr, view.plane_camera(), view.T)
    if not est:
        return None
    w, h, _ = est["box_map"]["dimensions"]
    if not (0.01 < w < 0.5 and 0.01 < h < 0.5):
        return None
    cx, cy = est["box_map"]["center"][:2]
    return {"xy": (float(cx), float(cy)), "width": float(w), "height": float(h)}


def cutout(view: View, mask: np.ndarray) -> dict:
    """RGBA crop of the object as the camera saw it (for a billboard), and its aspect ratio."""
    vs, us = np.nonzero(mask)
    y0, y1, x0, x1 = vs.min(), vs.max() + 1, us.min(), us.max() + 1
    rgba = np.dstack([view.rgb[y0:y1, x0:x1], (mask[y0:y1, x0:x1] * 255).astype(np.uint8)])
    img = Image.fromarray(rgba, "RGBA")
    img.thumbnail((TEX_PX, TEX_PX))
    return {"png": _png(img), "aspect": float((x1 - x0) / max(1, y1 - y0))}

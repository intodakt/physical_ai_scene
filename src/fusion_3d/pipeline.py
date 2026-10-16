"""S2 per-frame pipeline: SynchronizedFrame + SemanticObservations -> ObjectInstance3D list."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from ..preprocessing.depth_cleaning import clean_depth, depth_to_meters, remove_flying_pixels, valid_depth_ratio
from ..preprocessing.frame_loader import SemanticObservation, SynchronizedFrame
from ..preprocessing.mask_utils import erode
from . import geometry as geo
from .depth_reliability import assess as assess_depth
from .depth_reliability import depth_geometry_usable
from .mask_plane import estimate_from_mask
from .fusion import (
    ModalityQuality,
    depth_quality,
    fused_confidence,
    fusion_weights,
    rgb_quality,
)
from .object_instance import ObjectInstance3D
from .projection import deproject_depth, deproject_mask
from .transforms import T_map_optical_from_static_tf, apply_transform, invert_transform

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "fusion_3d.yaml"


def load_config(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class FrameResult:
    objects: list
    rejected: list = field(default_factory=list)
    plane: Optional[np.ndarray] = None
    T_map_camera: Optional[np.ndarray] = None
    object_points: dict = field(default_factory=dict)  # object_id -> Nx3 (camera)
    raw_points: dict = field(default_factory=dict)  # object_id -> Nx3 before cleaning
    timings_ms: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "objects": [o.to_dict() for o in self.objects],
            "rejected": self.rejected,
            "support_plane": None if self.plane is None else self.plane.tolist(),
            "T_map_camera": None if self.T_map_camera is None else self.T_map_camera.tolist(),
            "timings_ms": self.timings_ms,
        }


def _resolve_tf(frame: SynchronizedFrame, cfg: dict) -> Optional[np.ndarray]:
    if frame.T_map_camera is not None:
        return frame.T_map_camera
    tf = cfg.get("tf_map_camera_link")
    if tf:
        return T_map_optical_from_static_tf(tf["xyz"], tf["rpy"])
    return None


def sensor_depth(frame: SynchronizedFrame, cfg: dict) -> np.ndarray:
    """Raw depth → metres, NaN/inf/out-of-range set to 0. This is what the sensor delivered."""
    dcfg = cfg["depth"]
    return clean_depth(depth_to_meters(frame.depth_raw, frame.intrinsics.depth_scale), dcfg["min_m"], dcfg["max_m"])


def filter_depth(depth_m: np.ndarray, cfg: dict) -> np.ndarray:
    """Optional flying-pixel filter on top of the sensor depth (used for geometry only)."""
    fp = cfg["depth"].get("flying_pixel_filter") or {}
    if fp.get("enabled", False):
        return remove_flying_pixels(depth_m, fp.get("abs_thresh_m", 0.02), fp.get("rel_thresh", 0.02))
    return depth_m


def prepare_depth(frame: SynchronizedFrame, cfg: dict) -> np.ndarray:
    return filter_depth(sensor_depth(frame, cfg), cfg)


def process_frame(
    frame: SynchronizedFrame,
    observations: list[SemanticObservation],
    cfg: Optional[dict] = None,
    fusion_mode: Optional[str] = None,
    depth_override: Optional[np.ndarray] = None,
) -> FrameResult:
    """``depth_override``: an already range-cleaned depth in metres (e.g. a temporal median).

    Reliability cues (depth_confidence, holes, see-through) are measured on the
    sensor depth; geometry uses the flying-pixel-filtered depth.
    """
    cfg = cfg or load_config()
    t0 = time.perf_counter()
    intr = frame.intrinsics
    pcfg, ccfg, fcfg = cfg["support_plane"], cfg["cleaning"], cfg["fusion"]
    rcfg = cfg.get("depth_reliability", {"enabled": False})
    mode = fusion_mode or fcfg["mode"]

    # 1. depth cleaning
    raw = depth_override if depth_override is not None else sensor_depth(frame, cfg)
    depth = filter_depth(raw, cfg)
    T = _resolve_tf(frame, cfg)
    t1 = time.perf_counter()

    # 2. support plane (desk) from the whole frame
    plane = None
    if pcfg.get("enabled", True):
        scene_pts, _ = deproject_depth(depth, intr, stride=4)
        plane = geo.fit_support_plane(scene_pts, pcfg["ransac_threshold_m"])
    t2 = time.perf_counter()

    result = FrameResult(objects=[], plane=plane, T_map_camera=T)
    label_counts: dict = {}
    for obs in observations:
        label = obs.label
        idx = label_counts.get(label, 0)
        label_counts[label] = idx + 1
        oid = f"{label.replace(' ', '_')}_{idx}"

        if obs.mask.shape != depth.shape:
            result.rejected.append({"object_id": oid, "reason": "mask/depth shape mismatch"})
            continue

        # 3. how trustworthy is the depth inside this mask? (holes / see-through)
        rel = assess_depth(raw, obs.mask, intr, plane, rcfg) if rcfg.get("enabled", True) else None
        valid_ratio = valid_depth_ratio(raw, obs.mask)
        leak = rel.plane_leak_ratio if rel else 0.0

        # 4. mask filter + deprojection + cleaning. The flying-pixel filter assumes a dense surface;
        #    on glass the few genuine pixels sit among desk pixels and would be wiped out, so
        #    suspicious objects use the unfiltered sensor depth.
        #    For the same reason only the eroded mask interior is used: SAM's border bleed onto
        #    neighbouring objects would otherwise pass as "genuine" glass points.
        suspicious = rel is not None and rel.status != "ok"
        if suspicious:
            pts, uv = deproject_mask(raw, erode(obs.mask, rcfg.get("erode_px", 3)), intr)
        else:
            pts, uv = deproject_mask(depth, obs.mask, intr)
        cols = frame.rgb[uv[:, 1], uv[:, 0]] if len(uv) else None
        result.raw_points[oid] = pts
        clean = geo.clean_object_cloud(
            pts,
            cols,
            plane=plane,
            plane_margin=pcfg["margin_m"],
            voxel_size=ccfg["voxel_size_m"],
            nb_neighbors=ccfg["outlier_nb_neighbors"],
            std_ratio=ccfg["outlier_std_ratio"],
            cluster_eps=ccfg["cluster_eps_m"],
            cluster_min_points=ccfg["cluster_min_points"],
            keep_largest_cluster=ccfg["keep_largest_cluster"],
        )

        # 5. choose the geometry source: depth points, or mask + desk plane when depth is unusable
        #    Genuine glass pixels left after desk-plane removal are still the most accurate source;
        #    only when too few survive is the object placed from its mask and the desk plane.
        use_mask_plane = suspicious and (clean.n_final < ccfg["min_points"] or not depth_geometry_usable(rel, rcfg))
        fallback = estimate_from_mask(obs.mask, intr, plane, T) if use_mask_plane and rcfg.get("mask_plane_fallback", True) else None
        geometry_source = "mask_plane" if fallback else "depth"

        # 6. quality + fusion weights
        q_rgb, rgb_details = rgb_quality(frame.rgb, obs.mask)
        q_depth = 0.0 if fallback else depth_quality(valid_ratio, clean.inlier_ratio, clean.n_final, ccfg["min_points"], leak)
        q = ModalityQuality(
            rgb=q_rgb,
            depth=q_depth,
            lidar=None,
            semantic=float(obs.score),
            details={**rgb_details, "valid_depth_ratio": valid_ratio,
                     "inlier_ratio": clean.inlier_ratio, "n_raw": clean.n_raw,
                     "n_after_plane": clean.n_after_plane, "n_final": clean.n_final},
        )
        w = fusion_weights(q, mode, fcfg.get("weight_floor", 0.0))
        rel_fields = dict(depth_status=rel.status if rel else "ok",
                          depth_reliability=rel.to_dict() if rel else {},
                          geometry_source=geometry_source)

        if fallback is None and clean.n_final < ccfg["min_points"]:
            result.rejected.append({
                "object_id": oid, "semantic_label": label,
                "reason": f"only {clean.n_final} valid 3D points (< {ccfg['min_points']})",
                "depth_confidence": valid_ratio, "fusion_weights": w, **rel_fields,
            })
            continue

        # 7. geometry
        if fallback:
            c_map = fallback["centroid_map"]
            box_map = fallback["box_map"]
            dims = box_map["dimensions"]
            Tinv = invert_transform(T)
            c = apply_transform(Tinv, np.array([c_map]))[0]
            P = np.empty((0, 3))
            obb = {"center": c.tolist(), "rotation": np.eye(3).tolist(), "extent": list(dims)}
            aabb = {}
        else:
            P = np.asarray(clean.pcd.points)
            c = geo.centroid(P)
            obb = geo.oriented_bbox(clean.pcd)
            aabb = geo.axis_aligned_bbox(P)
            c_map, box_map = None, None
            if T is not None:
                P_map = apply_transform(T, P)
                c_map = geo.centroid(P_map).tolist()
                box_map = geo.gravity_aligned_bbox(P_map)
                dims = box_map["dimensions"]
            else:
                dims = sorted(obb["extent"], reverse=True)

        result.object_points[oid] = P
        result.objects.append(
            ObjectInstance3D(
                centroid=[float(x) for x in c],
                box_dimensions=[float(x) for x in dims],
                semantic_label=label,
                depth_confidence=round(valid_ratio, 4),
                object_id=oid,
                timestamp=obs.timestamp or frame.timestamp,
                frame_id=frame.frame_id,
                source_observation_id=obs.observation_id,
                label_candidates=list(obs.labels),
                detector_score=float(obs.score),
                embedding=obs.embedding,
                bbox_2d=list(obs.bbox),
                centroid_map=c_map,
                box_map=box_map,
                obb=obb,
                aabb=aabb,
                num_points=int(len(P)),
                point_density=round(geo.point_density(len(P), obb["extent"]), 2),
                modality_quality={k: (None if v is None else round(v, 4)) for k, v in q.as_dict().items()},
                fusion_mode=mode,
                fusion_weights={k: round(v, 4) for k, v in w.items()},
                fused_confidence=round(fused_confidence(q, w), 4),
                **rel_fields,
            )
        )
    t3 = time.perf_counter()
    result.timings_ms = {
        "depth_cleaning": round((t1 - t0) * 1e3, 2),
        "support_plane": round((t2 - t1) * 1e3, 2),
        "objects": round((t3 - t2) * 1e3, 2),
        "total": round((t3 - t0) * 1e3, 2),
    }
    return result

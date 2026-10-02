"""S2 per-frame pipeline: SynchronizedFrame + SemanticObservations -> ObjectInstance3D list."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from ..preprocessing.depth_cleaning import clean_depth, depth_to_meters, valid_depth_ratio
from ..preprocessing.frame_loader import SemanticObservation, SynchronizedFrame
from . import geometry as geo
from .fusion import (
    ModalityQuality,
    depth_quality,
    fused_confidence,
    fusion_weights,
    rgb_quality,
)
from .object_instance import ObjectInstance3D
from .projection import deproject_depth, deproject_mask
from .transforms import T_map_optical_from_static_tf, apply_transform

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


def process_frame(
    frame: SynchronizedFrame,
    observations: list[SemanticObservation],
    cfg: Optional[dict] = None,
    fusion_mode: Optional[str] = None,
) -> FrameResult:
    cfg = cfg or load_config()
    t0 = time.perf_counter()
    intr = frame.intrinsics
    dcfg, pcfg, ccfg, fcfg = cfg["depth"], cfg["support_plane"], cfg["cleaning"], cfg["fusion"]
    mode = fusion_mode or fcfg["mode"]

    # 1. depth cleaning
    depth = clean_depth(depth_to_meters(frame.depth_raw, intr.depth_scale), dcfg["min_m"], dcfg["max_m"])
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

        # 3. mask filter + deprojection
        valid_ratio = valid_depth_ratio(depth, obs.mask)
        pts, uv = deproject_mask(depth, obs.mask, intr)
        cols = frame.rgb[uv[:, 1], uv[:, 0]] if len(uv) else None
        result.raw_points[oid] = pts

        # 4. cleaning
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

        # 5. quality + fusion weights
        q_rgb, rgb_details = rgb_quality(frame.rgb, obs.mask)
        q = ModalityQuality(
            rgb=q_rgb,
            depth=depth_quality(valid_ratio, clean.inlier_ratio, clean.n_final, ccfg["min_points"]),
            lidar=None,
            semantic=float(obs.score),
            details={**rgb_details, "valid_depth_ratio": valid_ratio,
                     "inlier_ratio": clean.inlier_ratio, "n_raw": clean.n_raw,
                     "n_after_plane": clean.n_after_plane, "n_final": clean.n_final},
        )
        w = fusion_weights(q, mode, fcfg.get("weight_floor", 0.0))

        if clean.n_final < ccfg["min_points"]:
            result.rejected.append({
                "object_id": oid, "semantic_label": label,
                "reason": f"only {clean.n_final} valid 3D points (< {ccfg['min_points']})",
                "depth_confidence": valid_ratio, "fusion_weights": w,
            })
            continue

        # 6. geometry
        P = np.asarray(clean.pcd.points)
        c = geo.centroid(P)
        obb = geo.oriented_bbox(clean.pcd)
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
                centroid=c.tolist(),
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
                aabb=geo.axis_aligned_bbox(P),
                num_points=int(len(P)),
                point_density=round(geo.point_density(len(P), obb["extent"]), 2),
                modality_quality={k: (None if v is None else round(v, 4)) for k, v in q.as_dict().items()},
                fusion_mode=mode,
                fusion_weights={k: round(v, 4) for k, v in w.items()},
                fused_confidence=round(fused_confidence(q, w), 4),
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

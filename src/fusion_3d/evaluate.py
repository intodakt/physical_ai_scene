"""Compare ObjectInstance3D output with mock ground truth (map frame)."""

from __future__ import annotations

import numpy as np


def evaluate_against_ground_truth(objects: list, ground_truth: dict) -> dict:
    gt = {o["name"]: o for o in ground_truth["objects"]}
    rows = []
    for obj in objects:
        d = obj if isinstance(obj, dict) else obj.to_dict()
        g = gt.get(d["semantic_label"])
        if g is None or d.get("box_map") is None:
            continue
        c_err = float(np.linalg.norm(np.array(d["box_map"]["center"]) - np.array(g["center"])))
        cm_err = float(np.linalg.norm(np.array(d["centroid_map"]) - np.array(g["center"])))
        gw, gd = sorted(g["dimensions_xyz"][:2], reverse=True)
        true_dims = [gw, g["dimensions_xyz"][2], gd]
        dim_err = np.abs(np.array(d["box_dimensions"]) - np.array(true_dims))
        rows.append({
            "object_id": d["object_id"],
            "label": d["semantic_label"],
            "centroid_error_m": round(cm_err, 4),
            "box_center_error_m": round(c_err, 4),
            "true_dims_whd": [round(x, 3) for x in true_dims],
            "est_dims_whd": [round(x, 3) for x in d["box_dimensions"]],
            "dim_abs_error_m": [round(float(x), 4) for x in dim_err],
            "depth_confidence": d["depth_confidence"],
            "fused_confidence": d["fused_confidence"],
            "num_points": d["num_points"],
        })
    found = {r["label"] for r in rows}
    return {
        "per_object": rows,
        "recall": len(found) / max(1, len(gt)),
        "mean_centroid_error_m": round(float(np.mean([r["centroid_error_m"] for r in rows])), 4) if rows else None,
        "mean_box_center_error_m": round(float(np.mean([r["box_center_error_m"] for r in rows])), 4) if rows else None,
        "missed": sorted(set(gt) - found),
    }

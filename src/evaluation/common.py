"""Shared file layout and CSV helpers for the W12–W16 evaluation.

Layout (all relative to the repository root; the bags themselves stay outside git):

    eval/
      dataset/        recording_plan.csv, dataset_manifest.csv, metadata/<bag_id>.yaml, splits.json
      ground_truth/   ground_truth_positions.csv, relation_ground_truth.csv, detection_annotations.csv,
                      tracking_ground_truth.csv, temporal_events_ground_truth.csv
      queries/        queries_200.csv (+ .json)
      tasks/          end_to_end_tasks.csv
      results/s1 … s7 one folder of CSV / PNG / JSON per member
      report/         final tables 1–7 and figures 1–9

Column lists follow Appendix A of the professor's guide.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "eval"
DATASET, GT, QUERIES, TASKS, RESULTS, REPORT = (EVAL / d for d in ("dataset", "ground_truth", "queries", "tasks", "results", "report"))

# Appendix A (+ the relation GT format of §3.3 and the S2 per-object format of §5.2)
COLUMNS = {
    "dataset_manifest": ["bag_id", "family", "date", "duration_s", "fps", "difficulty", "lighting", "objects", "unseen_objects",
                         "motion", "occlusion", "gt_available", "split", "path", "notes"],
    "ground_truth_positions": ["bag_id", "frame_id", "object_id", "class", "x_gt", "y_gt", "z_gt", "size_x", "size_y", "size_z",
                               "condition", "measured_by", "notes"],
    "s2_object_results": ["bag_id", "frame_id", "object_id", "class", "condition", "method", "x_pred", "y_pred", "z_pred",
                          "x_gt", "y_gt", "z_gt", "error_cm", "valid_depth_ratio", "depth_std_cm", "confidence", "status"],
    "detection_annotations": ["image_id", "class", "seen_unseen", "xmin", "ymin", "xmax", "ymax"],
    "detection_predictions": ["image_id", "class", "seen_unseen", "xmin", "ymin", "xmax", "ymax", "prompt_type",
                              "prompt_text", "detector", "pred_score", "tp_fp_fn"],
    "relation_ground_truth": ["bag_id", "frame_id", "time", "subject", "predicate", "object", "gt", "pred", "confidence",
                              "evidence_value", "annotator", "checked_by"],
    "temporal_events_ground_truth": ["sequence_id", "object_id", "event", "t_gt", "notes"],
    "queries": ["query_id", "family", "difficulty", "question", "graph", "gt_answer", "gt_intent", "gt_target",
                "gt_reference", "gt_relation", "expect_refusal", "checked", "notes"],
    "query_results": ["query_id", "family", "question", "gt_answer", "method", "parsed_ok", "grounded_ok", "proposed_answer",
                      "pred_answer", "correct", "proposal_wrong", "wrong_claim_caught", "correction_success",
                      "hallucination", "refused", "proof"],
    "tracking_ground_truth": ["sequence_id", "scenario", "frame_id", "gt_object_id", "pred_track_id", "occluded",
                              "reappeared", "id_switch", "association_cost", "x", "y"],
    "action_trials": ["trial_id", "kind", "target_id", "scenario", "gt_safe", "validated", "reason_code", "outcome"],
    "e2e_tasks": ["task_id", "difficulty", "frames", "question", "expect_label", "expect_safe", "gt_x", "gt_y", "gt_z",
                  "required_relation", "notes"],
    "e2e_runs": ["run_id", "task_id", "difficulty", "repeat", "success", "first_failure_stage", "reason", "p50_ms", "p95_ms",
                 "fps", "warnings"],
}


def read_csv(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values()) and not
                str(next(iter(r.values()), "")).startswith("#")]


def write_csv(path, rows: Iterable[dict], columns: list | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    cols = columns or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _fmt(r.get(k)) for k in cols})
    return path


def write_json(path, obj) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _fmt(v):
    if isinstance(v, float):
        return round(v, 5)
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v


def as_float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def as_bool(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def results_dir(member: str) -> Path:
    d = RESULTS / member.lower()
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_tf(path):
    """T_map_optical (4x4) from S1's measured_tf.yaml (T_map_camera_link) or a JSON/YAML with T_map_camera."""
    if not path:
        return None
    import numpy as np
    import yaml

    d = yaml.safe_load(Path(path).read_text())
    if "T_map_camera_link" in d:
        from ..fusion_3d.transforms import R_LINK_OPTICAL
        T = np.asarray(d["T_map_camera_link"], float)
        Topt = np.eye(4)
        Topt[:3, :3] = R_LINK_OPTICAL
        return T @ Topt                              # map <- camera_link <- optical
    return np.asarray(d.get("T_map_camera", d.get("T_map_optical")), float)

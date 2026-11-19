"""Ready-to-fill ground-truth and result templates (professor's guide Appendix A).

    python -m src.evaluation.templates            # writes eval/ground_truth/*.csv (never overwrites)

Each template has the header plus ONE example row whose first cell starts with '#'. The evaluation
scripts skip rows starting with '#', so the example can stay in the file as a format reminder.
"""

from __future__ import annotations

import csv

from .common import COLUMNS, GT, QUERIES, TASKS

EXAMPLES = {
    GT / "ground_truth_positions.csv": ("ground_truth_positions", {
        "bag_id": "#B01_static_easy_rep1", "frame_id": "frame_0060", "object_id": "mug_01", "class": "mug",
        "x_gt": 0.40, "y_gt": 0.25, "z_gt": 0.06, "size_x": 0.08, "size_y": 0.08, "size_z": 0.10, "condition": "normal",
        "measured_by": "S1", "notes": "centre measured with tape from the table origin; condition: normal|shiny|transparent|small|occluded"}),
    GT / "relation_ground_truth.csv": ("relation_ground_truth", {
        "bag_id": "#B01_static_easy_rep1", "frame_id": "frame_0060", "time": 2.0, "subject": "mug_01", "predicate": "on",
        "object": "desk", "gt": 1, "pred": "", "confidence": "", "evidence_value": "", "annotator": "S4", "checked_by": "S1"}),
    GT / "detection_annotations.csv": ("detection_annotations", {
        "image_id": "#D01_unseen_medium_rep1/frame_0030", "class": "multimeter", "seen_unseen": "unseen",
        "xmin": 412, "ymin": 230, "xmax": 520, "ymax": 330}),
    GT / "temporal_events_ground_truth.csv": ("temporal_events_ground_truth", {
        "sequence_id": "#E01_motion_easy_rep1", "object_id": "mug_01", "event": "MOVED", "t_gt": 14.2,
        "notes": "event: MOVED | PICKED_UP | PLACED_ON | REAPPEARED | OCCLUDED; t_gt = bag time (s)"}),
    GT / "tracking_ground_truth.csv": ("tracking_ground_truth", {
        "sequence_id": "#F01_occlusion_medium_rep1", "scenario": "medium_occlusion", "frame_id": 12, "gt_object_id": "mug_A",
        "pred_track_id": "mug_01", "occluded": 0, "reappeared": 0, "id_switch": "", "association_cost": "", "x": 0.41, "y": 0.22}),
    TASKS / "end_to_end_tasks.csv": ("e2e_tasks", {
        "task_id": "#T01", "difficulty": "easy", "frames": "H01_language_easy_rep1", "question": "What is closest to the laptop?",
        "expect_label": "mug", "expect_safe": 1, "gt_x": 0.40, "gt_y": 0.25, "gt_z": 0.06, "required_relation": "",
        "notes": "difficulty: easy|medium|hard; expect_safe 1 = goal should be accepted, 0 = rejected"}),
}


def write_templates(overwrite: bool = False) -> list:
    written = []
    for path, (kind, example) in EXAMPLES.items():
        if path.exists() and not overwrite:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS[kind])
            w.writeheader()
            w.writerow(example)
        written.append(path)
    QUERIES.mkdir(parents=True, exist_ok=True)
    return written


if __name__ == "__main__":
    for p in write_templates():
        print("wrote", p)

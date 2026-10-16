"""Minimal checks for the JSON contracts between modules (S7 gatekeeper).

Each ``check_*`` returns a list of problems (empty = the file honours the contract). They are
used by ``tools/check_contracts.py`` on pull requests and by the pipeline after every stage.
"""

import math


def _vec(v, n=3):
    return isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)


def _missing(d, keys, where):
    return [f"{where}: missing '{k}'" for k in keys if k not in d]


def check_semantic_observation(d: dict) -> list:
    """S3 -> S2 (s3-semantic-draft-0.1)."""
    errs = _missing(d, ("schema_version", "frame_id", "image_size", "detections"), "observation")
    for i, det in enumerate(d.get("detections", [])):
        w = f"detections[{i}]"
        errs += _missing(det, ("detection_id", "bbox", "labels", "detector_score", "mask_status", "mask"), w)
        if "bbox" in det and not _vec(det["bbox"], 4):
            errs.append(f"{w}: bbox must be 4 finite numbers")
        if isinstance(det.get("mask"), str) and (det["mask"].startswith(("/", "\\")) or ":" in det["mask"]):
            errs.append(f"{w}: mask path must be relative")
    return errs


def check_objects(d: dict) -> list:
    """S2 -> S4/S6 (*_objects.json with ObjectInstance3D entries)."""
    errs = _missing(d, ("objects",), "objects file")
    for i, o in enumerate(d.get("objects", [])):
        w = f"objects[{i}]"
        errs += _missing(o, ("centroid", "box_dimensions", "semantic_label", "depth_confidence", "object_id"), w)
        for k in ("centroid", "box_dimensions"):
            if k in o and not _vec(o[k]):
                errs.append(f"{w}: {k} must be 3 finite numbers")
        if not 0.0 <= o.get("depth_confidence", 0.0) <= 1.0:
            errs.append(f"{w}: depth_confidence outside [0, 1]")
        if o.get("box_map") is not None and not _vec(o["box_map"].get("center")):
            errs.append(f"{w}: box_map.center must be 3 finite numbers")
    return errs


def check_scene_graph(d: dict) -> list:
    """S4 -> S5."""
    errs = _missing(d, ("frame", "units", "nodes", "edges"), "scene graph")
    ids = set()
    for i, n in enumerate(d.get("nodes", [])):
        w = f"nodes[{i}]"
        errs += _missing(n, ("id", "names", "pose_map", "size", "state", "confidence"), w)
        ids.add(n.get("id"))
        for k in ("pose_map", "size"):
            if k in n and not _vec(n[k]):
                errs.append(f"{w}: {k} must be 3 finite numbers")
    for i, e in enumerate(d.get("edges", [])):
        w = f"edges[{i}]"
        errs += _missing(e, ("source", "predicate", "target", "evidence", "start_time", "end_time"), w)
        for k in ("source", "target"):
            if k in e and e[k] not in ids:
                errs.append(f"{w}: {k} '{e[k]}' is not a node")
    return errs


def check_reasoning_result(d: dict) -> list:
    """S5 -> S6."""
    errs = _missing(d, ("target_id", "computed_facts", "verification_status", "final_answer", "confidence", "warnings"),
                    "reasoning result")
    if d.get("verification_status") and not d.get("target_id"):
        errs.append("reasoning result: verified answer without target_id")
    if not d.get("verification_status") and d.get("target_id"):
        errs.append("reasoning result: unverified answer must have target_id = null")
    return errs


def check_action_goal(d: dict) -> list:
    """S6 -> virtual twin."""
    errs = _missing(d, ("target_object_id", "target_pose", "exclusion_zones", "validated"), "action goal")
    if d.get("validated") and not _vec(d.get("target_pose")):
        errs.append("action goal: validated goal needs target_pose [x, y, yaw]")
    for i, z in enumerate(d.get("exclusion_zones", [])):
        poly = z.get("polygon", [])
        if len(poly) < 3 or not all(_vec(p, 2) for p in poly):
            errs.append(f"exclusion_zones[{i}]: polygon needs >= 3 [x, y] points")
    return errs


CHECKS = {
    "observation": check_semantic_observation,
    "objects": check_objects,
    "scene_graph": check_scene_graph,
    "reasoning_result": check_reasoning_result,
    "action_goal": check_action_goal,
}


def detect_kind(d) -> str | None:
    """Guess which contract a JSON file claims to follow (by its top-level keys)."""
    if not isinstance(d, dict):
        return None
    if "detections" in d and "image_size" in d:
        return "observation"
    if isinstance(d.get("objects"), list) and all(isinstance(o, dict) and "centroid" in o for o in d["objects"]):
        return "objects"
    if "nodes" in d and "edges" in d:
        return "scene_graph"
    if "verification_status" in d:
        return "reasoning_result"
    if "exclusion_zones" in d:
        return "action_goal"
    return None

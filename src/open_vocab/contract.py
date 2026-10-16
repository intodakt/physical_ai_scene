"""Draft SemanticObservation contract and downstream file checks."""

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

SCHEMA_VERSION = "s3-semantic-draft-0.1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_observation(data):
    require(isinstance(data, dict), "Observation must be an object")
    require(data.get("schema_version") == SCHEMA_VERSION, "Unsupported schema_version")
    require(data.get("interface_status") == "draft_not_team_approved", "Unexpected interface status")
    require(isinstance(data.get("frame_id"), str) and bool(data["frame_id"].strip()), "Missing frame_id")
    require("timestamp" in data and (data["timestamp"] is None or finite_number(data["timestamp"])),
            "timestamp must be finite seconds or null")
    size = data.get("image_size", {})
    require(isinstance(size, dict), "image_size must be an object")
    width, height = size.get("width"), size.get("height")
    require(type(width) is int and width > 0 and type(height) is int and height > 0,
            "Invalid image dimensions")
    require(data.get("bbox_format") == "xyxy_original_image_pixels", "Unsupported box format")
    require(data.get("mask_format") == "png_uint8_0_255", "Unsupported mask format")
    require(data.get("path_base") == "observation_json_directory", "Unsupported path base")
    require(isinstance(data.get("detections"), list), "detections must be an array")
    seen = set()
    for item in data["detections"]:
        require(isinstance(item, dict), "Detection must be an object")
        identifier = item.get("detection_id")
        require(isinstance(identifier, str) and bool(identifier) and identifier not in seen,
                "Missing or duplicate detection_id")
        seen.add(identifier)
        box = item.get("bbox")
        require(isinstance(box, list) and len(box) == 4 and all(finite_number(v) for v in box),
                "bbox must contain four finite numbers")
        x1, y1, x2, y2 = box
        require(0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height, "bbox outside image or empty")
        labels = item.get("labels")
        require(isinstance(labels, list) and bool(labels) and
                all(isinstance(v, str) and bool(v.strip()) for v in labels), "Invalid labels")
        score = item.get("detector_score")
        require(finite_number(score) and 0 <= score <= 1, "Invalid detector_score")
        status = item.get("mask_status")
        require(status in ("ok", "empty", "missing"), "Invalid mask_status")
        require("mask" in item, "Missing mask field")
        if status == "ok":
            path = item["mask"]
            require(isinstance(path, str) and bool(path), "Expected mask path")
            require(not Path(path).is_absolute() and ".." not in Path(path).parts and
                    Path(path).suffix.lower() == ".png", "Mask must be a relative PNG path")
        else:
            require(item["mask"] is None, "Failed masks must be null")
    return data


def load_observation(path, *, require_complete=True):
    """Example S2 reader: validates JSON, paths, mask values and dimensions."""
    path = Path(path).resolve()
    data = validate_observation(json.loads(path.read_text(encoding="utf-8")))
    size = data["image_size"]
    masks = {}
    for item in data["detections"]:
        if item["mask_status"] != "ok":
            require(not require_complete, f"Incomplete mask: {item['detection_id']}")
            continue
        mask_path = (path.parent / item["mask"]).resolve()
        require(mask_path.is_relative_to(path.parent), "Mask resolves outside output folder")
        mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
        require(mask is not None, f"Cannot read mask: {mask_path}")
        require(mask.dtype == np.uint8 and mask.shape == (size["height"], size["width"]),
                "Mask type or dimensions do not match RGB")
        require(bool(np.isin(mask, [0, 255]).all()) and bool(mask.any()),
                "Mask must contain foreground and only 0/255 values")
        masks[item["detection_id"]] = mask
    return data, masks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    try:
        data, masks = load_observation(args.observation, require_complete=not args.allow_incomplete)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Validated {data['frame_id']}: {len(data['detections'])} detections, {len(masks)} masks")


if __name__ == "__main__":
    main()

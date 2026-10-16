"""Run detection, segmentation and export for one RGB frame at a time."""

import copy
import json
import time
from pathlib import Path

import cv2
import numpy as np

from .contract import SCHEMA_VERSION, finite_number, validate_observation
from .input_profile import check_input, validate_profile


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")
    for name in ("detector", "segmenter"):
        if not isinstance(config.get(name), str) or not config[name].strip():
            raise ValueError(f"Missing {name} weights")
    prompts = config.get("prompts")
    if not isinstance(prompts, list) or not prompts or any(
        not isinstance(p, str) or not p.strip() for p in prompts
    ):
        raise ValueError("prompts must be a non-empty array of names")
    config["prompts"] = list(dict.fromkeys(p.strip() for p in prompts))
    for name in ("confidence", "iou"):
        if not finite_number(config.get(name)) or not 0 <= config[name] <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
    size = config.get("image_size")
    if type(size) is not int or size <= 0 or size % 32:
        raise ValueError("image_size must be a positive multiple of 32")
    count = config.get("max_detections")
    if type(count) is not int or count <= 0:
        raise ValueError("max_detections must be a positive integer")
    if type(config.get("agnostic_nms", False)) is not bool:
        raise ValueError("agnostic_nms must be true or false")
    if "input_profile" in config:
        validate_profile(config["input_profile"])
    return config


def write_image(path, image):
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Cannot write image: {path}")


class PerceptionPipeline:
    def __init__(self, detector, segmenter, config):
        self.detector = detector
        self.segmenter = segmenter
        self.config = copy.deepcopy(config)

    def process_frame(self, image, *, frame_id, timestamp, output_dir):
        """image: uint8 HWC BGR; timestamp: source seconds or None (never wall time)."""
        if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or (
            image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 1
        ):
            raise ValueError("Expected a non-empty uint8 HWC BGR image")
        if not isinstance(frame_id, str) or not frame_id.strip():
            raise ValueError("frame_id must be a non-empty string")
        if timestamp is not None and not finite_number(timestamp):
            raise ValueError("timestamp must be finite or None")
        height, width = image.shape[:2]
        check_input(self.config, width, height)
        start = time.perf_counter()
        detections = copy.deepcopy(self.detector.detect(image))
        detection_seconds = time.perf_counter() - start
        for index, item in enumerate(detections):
            item.update(detection_id=f"det_{index:04d}", mask=None, mask_status="missing")
        observation = {
            "schema_version": SCHEMA_VERSION,
            "interface_status": "draft_not_team_approved",
            "frame_id": frame_id, "timestamp": timestamp,
            "image_size": {"width": width, "height": height},
            "bbox_format": "xyxy_original_image_pixels",
            "mask_format": "png_uint8_0_255",
            "path_base": "observation_json_directory",
            "source_image": "input.png",
            "prompts": self.config["prompts"],
            "detections": detections,
        }
        validate_observation(observation)
        if "input_profile" in self.config:
            observation["input_profile"] = copy.deepcopy(self.config["input_profile"])
        start = time.perf_counter()
        masks = self.segmenter.segment(image, [d["bbox"] for d in detections]) if detections else []
        segmentation_seconds = time.perf_counter() - start
        if len(masks) != len(detections):
            raise ValueError("Segmenter returned a different number of masks and detections")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        (output_dir / "masks").mkdir()
        annotated = image.copy()
        overlay = image.copy()
        for index, (item, mask) in enumerate(zip(detections, masks, strict=True)):
            if mask is not None:
                mask = np.asarray(mask)
                if mask.shape != (height, width) or not np.isfinite(mask).all() or not np.isin(mask, [0, 1]).all():
                    raise ValueError("Segmenter must return original-size boolean masks")
                foreground = mask.astype(bool)
                if foreground.any():
                    item["mask"] = f"masks/{item['detection_id']}.png"
                    item["mask_status"] = "ok"
                    write_image(output_dir / item["mask"], foreground.astype(np.uint8) * 255)
                    color = np.array([(47 + index * 67) % 256, (170 + index * 31) % 256,
                                      (90 + index * 97) % 256], dtype=np.uint8)
                    overlay[foreground] = (0.55 * overlay[foreground] + 0.45 * color).astype(np.uint8)
                else:
                    item["mask_status"] = "empty"
            x1, y1, x2, y2 = (int(v) for v in item["bbox"])
            label = f"{item['detection_id']} {item['labels'][0]} {item['detector_score']:.2f}"
            for canvas in (annotated, overlay):
                cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 200, 0), 2)
                cv2.putText(canvas, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.45, (0, 180, 0), 1, cv2.LINE_AA)
        observation["timing_seconds"] = {"detection": detection_seconds, "segmentation": segmentation_seconds}
        validate_observation(observation)
        write_image(output_dir / "input.png", image)
        write_image(output_dir / "annotated.jpg", annotated)
        write_image(output_dir / "segmentation.jpg", overlay)
        path = output_dir / "observation.json"
        path.write_text(json.dumps(observation, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return path

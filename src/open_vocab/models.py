"""Ultralytics adapters. Both models receive the same original BGR image."""

import math

import numpy as np


class WorldDetector:
    def __init__(self, config, device="cpu", clip_weights=None):
        from ultralytics import YOLOWorld

        self.config = config
        self.device = device
        self.model = YOLOWorld(config["detector"])
        if clip_weights is not None:
            # Use the existing local CLIP cache without downloading another copy.
            import torch
            from ultralytics.nn.text_model import CLIP
            self.model.model.clip_model = CLIP(str(clip_weights), device=torch.device("cpu"))
        self.model.set_classes(config["prompts"])

    def detect(self, image):
        result = self.model.predict(
            source=image, device=self.device, conf=self.config["confidence"],
            iou=self.config["iou"], imgsz=self.config["image_size"],
            agnostic_nms=self.config.get("agnostic_nms", False),
            max_det=self.config["max_detections"], verbose=False, save=False,
        )[0]
        detections = []
        if result.boxes is not None:
            for box, score, cls in zip(result.boxes.xyxy.cpu().tolist(),
                                       result.boxes.conf.cpu().tolist(),
                                       result.boxes.cls.cpu().tolist(), strict=True):
                detections.append({"bbox": box, "labels": [result.names[int(cls)]],
                                   "detector_score": float(score)})
        return sorted(detections, key=lambda item: item["detector_score"], reverse=True)


def ordered_masks(result, count, shape):
    """SAM's placeholder class IDs refer to input box indices, even after filtering."""
    masks = [None] * count
    if result.masks is None:
        return masks
    if result.boxes is None:
        raise ValueError("SAM returned masks without prompt indices")
    indices = result.boxes.cls.cpu().tolist()
    arrays = result.masks.data.cpu().numpy()
    seen = set()
    for raw_index, array in zip(indices, arrays, strict=True):
        if not math.isfinite(raw_index) or raw_index != int(raw_index):
            raise ValueError("Invalid SAM prompt index")
        index = int(raw_index)
        if not 0 <= index < count or index in seen:
            raise ValueError("Unexpected or duplicate SAM prompt index")
        if array.shape != shape or not np.isfinite(array).all():
            raise ValueError("SAM mask must match the original image dimensions")
        seen.add(index)
        masks[index] = array.astype(bool)
    return masks


class SamSegmenter:
    def __init__(self, weights, device="cpu"):
        from ultralytics import SAM

        self.model = SAM(weights)
        self.device = device

    def segment(self, image, boxes):
        if not boxes:
            return []
        # Do not reuse cached image features across independent frames.
        if self.model.predictor is not None:
            self.model.predictor.reset_image()
        result = self.model.predict(
            source=image, bboxes=boxes, device=self.device, imgsz=1024,
            conf=0.0, verbose=False, save=False,
        )[0]
        return ordered_masks(result, len(boxes), image.shape[:2])

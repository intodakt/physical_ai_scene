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


class GroundingDinoDetector:  # pragma: no cover - needs torch + transformers + the model weights
    """Second open-vocabulary detector for the W12 comparison (professor's guide §6.1).

    Same interface as ``WorldDetector``: ``detect(image_bgr)`` -> [{"bbox", "labels", "detector_score"}],
    with the same prompt list, confidence threshold and max detections taken from the S3 config.
    Default model: ``IDEA-Research/grounding-dino-tiny`` (HuggingFace; ~700 MB, downloaded once).
    """

    def __init__(self, config, device="cpu", model_id="IDEA-Research/grounding-dino-tiny", text_threshold=0.25):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.config, self.device, self.torch = config, device, torch
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device).eval()
        self.text_threshold = text_threshold
        self.prompts = list(config["prompts"])
        # Grounding DINO reads one lower-case text where classes are separated by " . "
        self.text = " . ".join(p.lower() for p in self.prompts) + " ."

    def _label(self, phrase: str) -> str:
        """Map the phrase the model returns back to the closest prompt (word overlap)."""
        words = set(phrase.lower().split())
        best = max(self.prompts, key=lambda p: (len(words & set(p.lower().split())), -abs(len(p) - len(phrase))))
        return best

    def detect(self, image):
        from PIL import Image

        rgb = Image.fromarray(image[:, :, ::-1].copy())
        inputs = self.processor(images=rgb, text=self.text, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            outputs = self.model(**inputs)
        size = [rgb.size[::-1]]
        try:
            res = self.processor.post_process_grounded_object_detection(
                outputs, inputs.input_ids, threshold=self.config["confidence"], text_threshold=self.text_threshold, target_sizes=size)[0]
        except TypeError:   # older transformers name the box threshold differently
            res = self.processor.post_process_grounded_object_detection(
                outputs, inputs.input_ids, box_threshold=self.config["confidence"], text_threshold=self.text_threshold, target_sizes=size)[0]
        labels = res.get("text_labels", res.get("labels"))
        dets = [{"bbox": [float(v) for v in box], "labels": [self._label(str(lab))], "detector_score": float(score)}
                for box, score, lab in zip(res["boxes"].tolist(), res["scores"].tolist(), labels)]
        dets.sort(key=lambda d: d["detector_score"], reverse=True)
        return dets[: self.config["max_detections"]]


def make_detector(name, config, device="cpu"):
    """'yolo_world' (current S3 detector) or 'grounding_dino' (W12 second baseline)."""
    if name == "yolo_world":
        return WorldDetector(config, device)
    if name == "grounding_dino":
        return GroundingDinoDetector(config, device, **({"model_id": config["grounding_dino"]} if "grounding_dino" in config else {}))
    raise ValueError(f"unknown detector {name!r}")

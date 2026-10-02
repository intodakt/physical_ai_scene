"""S3 -> S2 interface: S3's observation.json (s3-semantic-draft-0.1) loads into S2."""

import json

import numpy as np
import pytest
from PIL import Image

from src.preprocessing.frame_loader import load_semantic_observations
from src.preprocessing.mock_data import generate


def _write_s3_observation(d, statuses=("ok", "missing")):
    (d / "masks").mkdir()
    dets = []
    for i, st in enumerate(statuses):
        det = {"detection_id": f"det_{i:04d}", "bbox": [10.0, 10.0, 30.0, 40.0],
               "labels": ["coffee mug", "cup"], "detector_score": 0.8,
               "mask": None, "mask_status": st}
        if st == "ok":
            m = np.zeros((60, 80), np.uint8)
            m[10:40, 10:30] = 255
            Image.fromarray(m).save(d / "masks" / f"det_{i:04d}.png")
            det["mask"] = f"masks/det_{i:04d}.png"
        dets.append(det)
    obs = {"schema_version": "s3-semantic-draft-0.1", "interface_status": "draft_not_team_approved",
           "frame_id": "f0", "timestamp": 12.5, "image_size": {"width": 80, "height": 60},
           "bbox_format": "xyxy_original_image_pixels", "mask_format": "png_uint8_0_255",
           "path_base": "observation_json_directory", "detections": dets}
    p = d / "observation.json"
    p.write_text(json.dumps(obs))
    return p


def test_loads_s3_draft_and_skips_failed_masks(tmp_path):
    skipped = []
    obs = load_semantic_observations(_write_s3_observation(tmp_path), skipped)
    assert len(obs) == 1
    o = obs[0]
    assert o.observation_id == "det_0000" and o.label == "coffee mug"
    assert o.score == 0.8 and o.timestamp == 12.5
    assert o.mask.shape == (60, 80) and o.mask.sum() == 30 * 20
    assert skipped == [{"detection_id": "det_0001", "semantic_label": "coffee mug",
                        "reason": "S3 mask_status=missing"}]


def test_rejects_mask_size_mismatch(tmp_path):
    p = _write_s3_observation(tmp_path, ("ok",))
    data = json.loads(p.read_text())
    data["image_size"] = {"width": 100, "height": 60}
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_semantic_observations(p)


def test_mock_frame_passes_s3_contract_validator(tmp_path):
    pytest.importorskip("cv2")
    from src.open_vocab.open_vocab.contract import load_observation

    d = generate(tmp_path / "frame_000")
    data, masks = load_observation(d / "observation.json")
    assert len(masks) == len(data["detections"]) == 5

"""S3 W10-W11: frozen prompts and appearance-embedding consistency."""

import json

import numpy as np

from src.open_vocab import embeddings, freeze


def test_freeze_and_check(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"detector": "d.pt", "segmenter": "s.pt", "prompts": ["mug", "laptop"], "confidence": 0.25,
                               "iou": 0.5, "image_size": 640, "max_detections": 30}))
    fz = freeze.freeze(cfg, "t_v1", tmp_path)
    data = json.loads(fz.read_text())
    assert data["prompts"] == ["mug", "laptop"] and len(data["sha256"]) == 64
    for i, prompts in enumerate((["mug", "laptop"], ["mug", "laptop"], ["mug", "cup"])):
        d = tmp_path / "run" / f"frame_{i}"
        d.mkdir(parents=True)
        (d / "observation.json").write_text(json.dumps({"frame_id": f"f{i}", "prompts": prompts,
                                                        "detections": [{"labels": ["mug"], "detector_score": 0.5 + i / 10}]}))
    r = freeze.check_run(tmp_path / "run", fz)
    assert r["frames"] == 3 and r["frames_with_other_prompts"] == ["f2"] and not r["ok"]
    assert r["semantic_scores"]["mug"]["count"] == 3


def test_frozen_files_in_repo_match_their_configs():
    from pathlib import Path
    root = Path(freeze.__file__).parent / "configs"
    for name, src in (("desk_v1", "desk.json"), ("generic_tabletop_v1", "generic_tabletop.json")):
        frozen = json.loads((root / "frozen" / f"{name}.json").read_text())
        assert frozen["sha256"] == freeze.fingerprint(json.loads((root / src).read_text()))


def _scene(shift, rng):
    img = np.zeros((60, 90, 3), np.uint8)
    img[10:30, 10 + shift:30 + shift] = (230, 120, 180)      # pink cup
    img[35:55, 50 + shift:80 + shift] = (20, 20, 20)         # black phone
    img = np.clip(img.astype(int) + rng.integers(-8, 8, img.shape), 0, 255).astype(np.uint8)
    m1 = np.zeros(img.shape[:2], bool); m1[10:30, 10 + shift:30 + shift] = True
    m2 = np.zeros(img.shape[:2], bool); m2[35:55, 50 + shift:80 + shift] = True
    return img, {"cup_01": m1, "phone_01": m2}


def test_colour_embedding_is_consistent_per_id():
    rng, e = np.random.default_rng(0), embeddings.ColorHistEmbedder()
    frames = []
    for k in range(4):
        img, masks = _scene(k * 2, rng)
        frames.append({pid: e.embed(img, m) for pid, m in masks.items()})
    c = embeddings.consistency(frames)
    assert c["same_id_mean"] > 0.9 and c["different_id_mean"] < 0.3 and c["gap"] > 0.6

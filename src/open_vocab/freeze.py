"""S3 W10: freeze the prompt vocabulary and thresholds, and check that a run used the frozen set.

    python -m src.open_vocab.freeze --config src/open_vocab/configs/desk.json --name desk_v1
        -> src/open_vocab/configs/frozen/desk_v1.json  (prompts, thresholds, SHA-256 fingerprint)
    python -m src.open_vocab.freeze --check output/s3_semantic/<run>/ --frozen src/open_vocab/configs/frozen/desk_v1.json
        -> per frame: same prompts?  + semantic-score summary per label (mean / min / count)

Freezing means: after W10 the prompts and thresholds used for evaluation do not change any more, so
seen / unseen numbers in W12 are comparable. The fingerprint makes a silent change visible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

FROZEN_DIR = Path(__file__).resolve().parent / "configs" / "frozen"
KEYS = ("detector", "segmenter", "prompts", "confidence", "iou", "image_size", "max_detections")


def fingerprint(cfg: dict) -> str:
    body = json.dumps({k: cfg.get(k) for k in KEYS}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def freeze(config_path, name, out_dir=FROZEN_DIR) -> Path:
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    frozen = {k: cfg.get(k) for k in KEYS}
    frozen.update(name=name, source_config=Path(config_path).name, sha256=fingerprint(cfg))
    out = Path(out_dir) / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(frozen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def check_run(run_dir, frozen_path) -> dict:
    frozen = json.loads(Path(frozen_path).read_text(encoding="utf-8"))
    want = list(frozen["prompts"])
    frames, mismatched, scores = 0, [], defaultdict(list)
    for p in sorted(Path(run_dir).rglob("observation.json")):
        obs = json.loads(p.read_text(encoding="utf-8"))
        frames += 1
        if list(obs.get("prompts", [])) != want:
            mismatched.append(obs.get("frame_id", p.parent.name))
        for d in obs.get("detections", []):
            scores[d["labels"][0]].append(float(d["detector_score"]))
    sem = {lab: {"count": len(v), "mean": round(sum(v) / len(v), 3), "min": round(min(v), 3)} for lab, v in sorted(scores.items())}
    return {"frozen": frozen["name"], "sha256": frozen["sha256"], "frames": frames, "frames_with_other_prompts": mismatched,
            "ok": frames > 0 and not mismatched, "semantic_scores": sem}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--name")
    ap.add_argument("--check", help="S3 output folder to check")
    ap.add_argument("--frozen", help="frozen JSON to check against")
    a = ap.parse_args()
    if a.check:
        print(json.dumps(check_run(a.check, a.frozen), indent=2))
    else:
        print("->", freeze(a.config, a.name))


if __name__ == "__main__":
    main()

"""S3 W11: appearance embeddings per detection and their consistency over time.

Two embedders behind one interface ``embed(rgb, mask) -> unit vector``:

* ``ColorHistEmbedder`` (default, no extra dependency): hue-saturation-value histogram of the mask
  pixels (8 x 4 x 4 = 128 bins), L2-normalised. Cheap and good enough to tell a pink cup from a
  black phone; it cannot tell two identical white mugs apart.
* ``ClipEmbedder``: CLIP image embedding of the mask's box crop, via the CLIP model Ultralytics
  already uses for YOLO-World. Needs torch + the CLIP weights, so it is only constructed on demand.
  NOT run in this repository yet (no torch in CI): S3 must check the Ultralytics CLIP API on the
  live setup before using it.

Consistency (``consistency(per_frame)``): for objects with persistent IDs over several frames, the
mean cosine similarity of the same ID across frames (should be high) vs. of different IDs (should be
low). The gap is what S6 can use as an appearance cue for re-identification.
"""

from __future__ import annotations

from itertools import combinations

import cv2
import numpy as np


class ColorHistEmbedder:
    name = "hsv_hist_8x4x4"

    def __init__(self, bins=(8, 4, 4)):
        self.bins = bins

    def embed(self, rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
        m = mask.astype(bool)
        if not m.any():
            return np.zeros(int(np.prod(self.bins)))
        hsv = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2HSV)
        h = cv2.calcHist([hsv], [0, 1, 2], m.astype(np.uint8), list(self.bins), [0, 180, 0, 256, 0, 256]).ravel()
        n = np.linalg.norm(h)
        return h / n if n else h


class ClipEmbedder:  # pragma: no cover - needs torch + CLIP weights (S3's live setup)
    name = "clip"

    def __init__(self, weights="ViT-B/32", device="cpu"):
        import torch
        from ultralytics.nn.text_model import CLIP

        self.torch = torch
        self.model = CLIP(weights, device=torch.device(device))

    def embed(self, rgb, mask):
        ys, xs = np.nonzero(mask)
        crop = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        with self.torch.no_grad():
            v = self.model.encode_image(crop).cpu().numpy().ravel()   # Ultralytics CLIP wrapper
        return v / (np.linalg.norm(v) or 1.0)


def cosine(a, b) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0


def consistency(per_frame: list) -> dict:
    """``per_frame``: list of {persistent_id: embedding}. Returns same-ID vs different-ID cosine statistics."""
    same, diff = [], []
    for f in per_frame:
        for a, b in combinations(sorted(f), 2):
            diff.append(cosine(f[a], f[b]))
    for i, j in combinations(range(len(per_frame)), 2):
        for pid in set(per_frame[i]) & set(per_frame[j]):
            same.append(cosine(per_frame[i][pid], per_frame[j][pid]))
    s = float(np.mean(same)) if same else None
    d = float(np.mean(diff)) if diff else None
    return {"same_id_mean": None if s is None else round(s, 3), "same_id_min": round(min(same), 3) if same else None,
            "different_id_mean": None if d is None else round(d, 3), "different_id_max": round(max(diff), 3) if diff else None,
            "gap": None if s is None or d is None else round(s - d, 3), "pairs_same": len(same), "pairs_different": len(diff)}


def frames_consistency(frames_dir, embedder=None) -> dict:
    """Colour-embedding consistency over exported frame folders (rgb.png + observation.json + masks).

    Detections are grouped by their top label; repeated labels in one frame (two white mugs) get
    a suffix by left-to-right order, which is good enough for a static recording."""
    from pathlib import Path

    from ..preprocessing.frame_loader import load_frame, load_semantic_observations

    embedder = embedder or ColorHistEmbedder()
    per_frame = []
    for d in sorted(p for p in Path(frames_dir).iterdir() if (p / "rgb.png").exists()):
        try:
            obs = load_semantic_observations(next(d.rglob("observation.json")))
        except StopIteration:
            continue
        fr = load_frame(d)
        obs = sorted(obs, key=lambda o: o.bbox[0])
        seen, f = {}, {}
        for o in obs:
            if o.mask.shape != fr.rgb.shape[:2]:
                continue
            seen[o.label] = seen.get(o.label, 0) + 1
            f[f"{o.label}#{seen[o.label]}"] = embedder.embed(fr.rgb, o.mask)
        per_frame.append(f)
    return {"embedder": embedder.name, "frames": len(per_frame), **consistency(per_frame)}


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="S3: appearance-embedding consistency on exported frames")
    ap.add_argument("--frames", required=True, help="e.g. data/demo_store/datasets/<bag>/frames")
    print(json.dumps(frames_consistency(ap.parse_args().frames), indent=2))

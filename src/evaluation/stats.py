"""Shared statistics for the W12–W16 evaluation (professor's guide §11, Appendix B).

Every module reports with the same helpers so tables are comparable:

* ``describe(values)``  n, mean, median, sample SD, p95, max and a 95 % CI of the mean
  (the CI is left out when n < ``MIN_N_FOR_CI``: "do not report a CI if N is extremely small");
* ``rate(num, den)``    a percentage that always carries its numerator and denominator,
  e.g. ``92 % (46/50)`` (§11.3);
* ``prf(tp, fp, fn)``   precision, recall, F1;
* geometry: 3D centroid error, axis-aligned 3D IoU, 2D IoU, cosine similarity.
"""

from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence

import numpy as np

MIN_N_FOR_CI = 5


def _clean(values: Iterable) -> np.ndarray:
    out = []
    for v in values:
        if v is None or v == "":
            continue
        f = float(v)
        if math.isfinite(f):
            out.append(f)
    return np.asarray(out, dtype=float)


def describe(values: Iterable, digits: int = 3) -> dict:
    """Descriptive statistics of a list of numbers (None / NaN / '' ignored)."""
    a = _clean(values)
    n = int(a.size)
    if n == 0:
        return {"n": 0, "mean": None, "median": None, "sd": None, "p95": None, "max": None, "ci95": None}
    r = lambda x: None if x is None else round(float(x), digits)
    sd = float(a.std(ddof=1)) if n > 1 else None
    ci = None
    if n >= MIN_N_FOR_CI and sd is not None:
        half = 1.96 * sd / math.sqrt(n)
        ci = [r(a.mean() - half), r(a.mean() + half)]
    return {"n": n, "mean": r(a.mean()), "median": r(np.median(a)), "sd": r(sd),
            "p95": r(np.percentile(a, 95)), "max": r(a.max()), "ci95": ci}


def rate(num: int, den: int, digits: int = 1) -> dict:
    """A rate that keeps its counts: {'value': 0.92, 'num': 46, 'den': 50, 'text': '92.0 % (46/50)'}."""
    num, den = int(num), int(den)
    if den == 0:
        return {"value": None, "num": num, "den": den, "text": f"n/a (0/{den})"}
    v = num / den
    return {"value": round(v, 4), "num": num, "den": den, "text": f"{100 * v:.{digits}f} % ({num}/{den})"}


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r_ = tp / (tp + fn) if tp + fn else None
    f1 = 2 * p * r_ / (p + r_) if p and r_ else (0.0 if tp == 0 and fp + fn > 0 else None)
    rnd = lambda x: None if x is None else round(x, 4)
    return {"tp": int(tp), "fp": int(fp), "fn": int(fn), "precision": rnd(p), "recall": rnd(r_), "f1": rnd(f1),
            "precision_text": rate(tp, tp + fp)["text"], "recall_text": rate(tp, tp + fn)["text"]}


def centroid_error(pred: Sequence[float], gt: Sequence[float]) -> float:
    """Euclidean distance ||c_pred − c_GT||₂ in the units of the inputs."""
    return float(np.linalg.norm(np.asarray(pred, float) - np.asarray(gt, float)))


def mae(errors: Iterable) -> Optional[float]:
    a = _clean(errors)
    return float(np.mean(np.abs(a))) if a.size else None


def rmse(errors: Iterable) -> Optional[float]:
    a = _clean(errors)
    return float(np.sqrt(np.mean(a ** 2))) if a.size else None


def iou_3d_aabb(c1, s1, c2, s2) -> float:
    """IoU of two axis-aligned 3D boxes given as centre + size."""
    c1, s1, c2, s2 = (np.asarray(v, float) for v in (c1, s1, c2, s2))
    lo = np.maximum(c1 - s1 / 2, c2 - s2 / 2)
    hi = np.minimum(c1 + s1 / 2, c2 + s2 / 2)
    inter = float(np.prod(np.clip(hi - lo, 0, None)))
    union = float(np.prod(s1) + np.prod(s2) - inter)
    return inter / union if union > 0 else 0.0


def iou_2d(a, b) -> float:
    """IoU of two boxes [xmin, ymin, xmax, ymax]."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def cosine(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def keyframes(frame_ids: Sequence, every: int = 10) -> list:
    """Every ``every``-th frame (§11.4: avoid counting near-identical consecutive frames)."""
    return list(frame_ids)[::max(1, int(every))]

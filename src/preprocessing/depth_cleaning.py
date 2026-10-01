"""Depth image cleaning and quality statistics."""

from __future__ import annotations

import numpy as np


def depth_to_meters(depth_raw: np.ndarray, depth_scale: float = 0.001) -> np.ndarray:
    """Convert a raw depth image (e.g. uint16 millimetres) to float32 metres.

    Float input is assumed to already be in metres.
    """
    if np.issubdtype(depth_raw.dtype, np.floating):
        return depth_raw.astype(np.float32)
    return depth_raw.astype(np.float32) * float(depth_scale)


def clean_depth(
    depth_m: np.ndarray, min_depth: float = 0.1, max_depth: float = 3.0
) -> np.ndarray:
    """Return a copy where NaN/inf and out-of-range values are set to 0 (invalid)."""
    d = np.array(depth_m, dtype=np.float32, copy=True)
    invalid = ~np.isfinite(d) | (d < min_depth) | (d > max_depth)
    d[invalid] = 0.0
    return d


def valid_depth_mask(depth_m: np.ndarray) -> np.ndarray:
    return np.isfinite(depth_m) & (depth_m > 0)


def valid_depth_ratio(depth_m: np.ndarray, mask: np.ndarray) -> float:
    """Fraction of mask pixels that have a valid depth reading (0..1).

    This is the ``depth_confidence`` of the ObjectInstance3D contract: on shiny
    or transparent objects the RealSense returns holes and this ratio drops.
    """
    mask = mask.astype(bool)
    n = int(mask.sum())
    if n == 0:
        return 0.0
    return float(valid_depth_mask(depth_m)[mask].sum()) / n


def masked_depth_stats(depth_m: np.ndarray, mask: np.ndarray) -> dict:
    """Median / std / min / max of valid depth inside the mask (metres)."""
    vals = depth_m[mask.astype(bool) & valid_depth_mask(depth_m)]
    if vals.size == 0:
        return {"median": None, "std": None, "min": None, "max": None, "count": 0}
    return {
        "median": float(np.median(vals)),
        "std": float(np.std(vals)),
        "min": float(vals.min()),
        "max": float(vals.max()),
        "count": int(vals.size),
    }

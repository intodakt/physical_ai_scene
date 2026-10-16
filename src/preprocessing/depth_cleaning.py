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


def _shifts(a: np.ndarray, fill) -> np.ndarray:
    """Stack of the 3x3 neighbourhood of every pixel, shape (9, H, W)."""
    p = np.pad(a, 1, mode="constant", constant_values=fill)
    h, w = a.shape
    return np.stack([p[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3)])


def remove_flying_pixels(depth_m: np.ndarray, abs_thresh: float = 0.02, rel_thresh: float = 0.02) -> np.ndarray:
    """Invalidate "flying"/mixed pixels on depth discontinuities (Week 7).

    A pixel is dropped when it differs from the median of its valid 3x3
    neighbours by more than ``abs_thresh + rel_thresh * depth``. These pixels
    sit between foreground and background and create the floating points that
    otherwise survive into object clouds.
    """
    d = np.where(np.isfinite(depth_m) & (depth_m > 0), depth_m, np.nan).astype(np.float32)
    with np.errstate(all="ignore"):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(_shifts(d, np.nan), axis=0)
    out = np.nan_to_num(d, nan=0.0)
    bad = np.isfinite(d) & np.isfinite(med) & (np.abs(d - med) > abs_thresh + rel_thresh * med)
    out[bad] = 0.0
    return out


def temporal_median_depth(depths: list, min_valid_fraction: float = 0.5) -> np.ndarray:
    """Per-pixel median over a static window of frames (Week 7, static scenes only).

    Fills random dropouts and averages sensor noise; a pixel stays invalid if it
    is valid in fewer than ``min_valid_fraction`` of the frames (e.g. glass).
    """
    import warnings

    stack = np.stack([np.where(np.isfinite(d) & (d > 0), d, np.nan) for d in depths]).astype(np.float32)
    valid = np.isfinite(stack).mean(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(stack, axis=0)
    med[(valid < min_valid_fraction) | ~np.isfinite(med)] = 0.0
    return med.astype(np.float32)

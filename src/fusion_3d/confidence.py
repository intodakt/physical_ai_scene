"""Separate confidence terms for one ObjectInstance3D (Week 9 — professor's feedback §5.2–5.3).

    C_depth = r_valid · exp(−σ_Z / τ)

r_valid is the share of the mask interior whose depth really comes from the object
(``genuine_ratio``: valid depth that does not lie on the desk plane behind a see-through
object). A plain valid-pixel ratio is blind to see-through glass — the desk behind it
returns valid depth — so the genuine ratio is used instead.

σ_Z is the robust depth noise inside the mask interior: 1.4826 · MAD of the difference
between each depth pixel and the median of its 5×5 neighbourhood. It measures noise and
flicker, not the object's own depth extent, so a long laptop is not penalised.

C_det is S3's detector score; C_mask is the share of the mask that survives erosion
(thin or fragmented masks score low). C_track is filled by S6.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ..preprocessing.depth_cleaning import nanmedian_fast
from ..preprocessing.mask_utils import erode

TAU_M = 0.01
WINDOW = 5


def _local_residual(depth_m: np.ndarray, region: np.ndarray, window: int = WINDOW):
    """(crop slice, depth crop, depth − nan-median of its window×window neighbourhood) around ``region``."""
    ys, xs = np.nonzero(region)
    r = window // 2
    y0, y1 = max(0, ys.min() - r), min(depth_m.shape[0], ys.max() + r + 1)
    x0, x1 = max(0, xs.min() - r), min(depth_m.shape[1], xs.max() + r + 1)
    crop = depth_m[y0:y1, x0:x1].astype(np.float64)
    crop = np.where(np.isfinite(crop) & (crop > 0), crop, np.nan)
    pad = np.pad(crop, r, constant_values=np.nan)
    win = np.lib.stride_tricks.sliding_window_view(pad, (window, window))
    local = nanmedian_fast(win.reshape(*crop.shape, -1), axis=-1)
    return (slice(y0, y1), slice(x0, x1)), crop, crop - local


def depth_noise(depth_m: np.ndarray, interior: np.ndarray, window: int = WINDOW) -> Optional[float]:
    """1.4826 · MAD of (depth − local median) over the valid interior pixels; None if < 20 pixels."""
    if interior.sum() < 20:
        return None
    sl, _, res = _local_residual(depth_m, interior, window)
    sel = interior[sl] & np.isfinite(res)
    if sel.sum() < 20:
        return None
    res = res[sel]
    return float(1.4826 * np.median(np.abs(res - np.median(res))))


def reject_depth_spikes(depth_m: np.ndarray, mask: np.ndarray, k: float = 3.0, floor_m: float = 0.01,
                        window: int = WINDOW) -> tuple[np.ndarray, int]:
    """Zero the mask pixels whose depth deviates from the local median by more than max(k·σ_Z, floor).

    Specular highlights (a shiny mug) return isolated depth spikes; MAD-based σ_Z ignores them,
    the local median does not follow them, so they stand out. Returns (depth copy, n removed).
    """
    mask = mask.astype(bool)
    if mask.sum() < 20:
        return depth_m, 0
    sl, _, res = _local_residual(depth_m, mask, window)        # computed once (W11 speed-up)
    sel = mask[sl] & np.isfinite(res)
    if sel.sum() < 20:
        return depth_m, 0
    r = res[sel]
    sigma = float(1.4826 * np.median(np.abs(r - np.median(r))))
    bad = sel & (np.abs(res) > max(k * sigma, floor_m))
    out = depth_m.copy()
    out[sl][bad] = 0.0
    return out, int(bad.sum())


def mask_compactness(mask: np.ndarray, erode_px: int = 3) -> float:
    n = int(mask.sum())
    return float(erode(mask, erode_px).sum()) / n if n else 0.0


def confidence_terms(depth_m: np.ndarray, mask: np.ndarray, genuine_ratio: float, detector_score: float,
                     erode_px: int = 3, tau: float = TAU_M) -> dict:
    mask = mask.astype(bool)
    interior = erode(mask, erode_px)
    if interior.sum() < 20:
        interior = mask
    sigma = depth_noise(depth_m, interior)
    c_depth = 0.0 if sigma is None else float(np.clip(genuine_ratio, 0, 1) * np.exp(-sigma / tau))
    return {
        "c_det": round(float(detector_score), 4),
        "c_mask": round(mask_compactness(mask, erode_px), 4),
        "c_depth": round(c_depth, 4),
        "r_valid": round(float(genuine_ratio), 4),
        "sigma_z_m": None if sigma is None else round(sigma, 5),
        "tau_m": tau,
        "c_track": None,
    }

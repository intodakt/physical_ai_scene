"""Week 9: C_depth = r_valid·exp(−σ_Z/τ) and specular-spike rejection."""

import numpy as np

from src.fusion_3d.confidence import confidence_terms, depth_noise, reject_depth_spikes


def _plane(h=60, w=80, z=0.8, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:h, :w]
    return (z + 0.002 * xx + noise * rng.standard_normal((h, w))).astype(np.float32)


MASK = np.zeros((60, 80), bool)
MASK[10:50, 15:65] = True


def test_noise_ignores_object_extent():
    # a tilted surface spans 16 cm in depth but is noise-free: σ_Z must stay ~0
    assert depth_noise(_plane(), MASK) < 1e-4


def test_noisy_depth_lowers_c_depth():
    clean = confidence_terms(_plane(noise=0.001), MASK, genuine_ratio=0.95, detector_score=0.9)
    noisy = confidence_terms(_plane(noise=0.01), MASK, genuine_ratio=0.95, detector_score=0.9)
    assert clean["c_depth"] > 0.8 > 0.4 > noisy["c_depth"]


def test_see_through_glass_low_even_with_full_valid_depth():
    # the desk behind glass gives 100 % valid depth, but only 5 % of it is genuine glass
    t = confidence_terms(_plane(noise=0.001), MASK, genuine_ratio=0.05, detector_score=0.7)
    assert t["c_depth"] < 0.06 and t["r_valid"] == 0.05


def test_no_depth_gives_zero():
    t = confidence_terms(np.zeros((60, 80), np.float32), MASK, genuine_ratio=0.0, detector_score=0.7)
    assert t["c_depth"] == 0.0 and t["sigma_z_m"] is None


def test_spikes_removed_surface_kept():
    d = _plane(noise=0.001)
    rng = np.random.default_rng(1)
    ys, xs = np.nonzero(MASK)
    pick = rng.choice(len(ys), len(ys) // 10, replace=False)
    d[ys[pick], xs[pick]] += 0.05
    out, n = reject_depth_spikes(d, MASK)
    assert n >= 0.9 * len(pick)
    assert n <= 1.1 * len(pick)
    assert (out[ys[pick], xs[pick]] == 0).mean() > 0.9


def test_nanmedian_fast_matches_numpy():
    import warnings

    from src.preprocessing.depth_cleaning import nanmedian_fast
    rng = np.random.default_rng(3)
    for shape, axis in (((9, 40, 50), 0), ((30, 20, 25), -1)):
        a = rng.random(shape)
        a[rng.random(shape) < 0.5] = np.nan
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ref = np.nanmedian(a, axis=axis)
        assert np.allclose(nanmedian_fast(a, axis), ref, equal_nan=True)

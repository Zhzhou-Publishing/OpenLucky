"""Unit tests for the latitude-preserving tone-curve auto (auto_latitude_curve).

Guards the "宽容度矫正/曝光反差 Auto" behaviour: never increase contrast
(k<=1.0), apply a reverse-S only as strongly as needed to keep final clipping
within budget, and stay at identity when the image wouldn't clip. This is what
lets the user keep the curve on Auto instead of always dragging it to -100.
"""
import numpy as np

from cli.lib.curve.s_curve import auto_latitude_curve


def _img(values):
    """(N,) luminance -> (1, N, 3) RGB image in [0, 1]."""
    v = np.asarray(values, dtype=np.float64)
    return np.stack([v, v, v], axis=-1)[None, :, :]


def test_k_never_exceeds_one():
    rng = np.random.default_rng(0)
    img = _img(rng.uniform(0.0, 1.0, 5000))
    k = auto_latitude_curve(img, pivot=0.5, contrast=1.2)
    assert 0.4 <= k <= 1.0


def test_compresses_when_highlights_would_clip():
    # A heavy mass of near-white pixels blows out after the auto-levels stretch;
    # the latitude curve must pull it back with a reverse-S (k < 1).
    rng = np.random.default_rng(1)
    bright = np.clip(rng.normal(0.95, 0.03, 8000), 0, 1)
    dark = np.clip(rng.normal(0.05, 0.03, 2000), 0, 1)
    k = auto_latitude_curve(_img(np.concatenate([bright, dark])), pivot=0.5, contrast=1.3)
    assert k < 0.95, f"expected compression, got k={k}"


def test_identity_when_nothing_clips():
    # Midtone-only image: after the stretch only the ~0.01% tails clip, well under
    # budget, so no softening is needed and k stays ~1.0 (natural contrast).
    rng = np.random.default_rng(2)
    img = _img(np.clip(rng.normal(0.5, 0.07, 8000), 0, 1))
    k = auto_latitude_curve(img, pivot=0.5, contrast=1.0)
    assert k >= 0.95, f"expected near-identity, got k={k}"


def test_strength_zero_disables():
    rng = np.random.default_rng(3)
    bright = np.clip(rng.normal(0.95, 0.03, 8000), 0, 1)
    img = _img(np.concatenate([bright, np.zeros(2000)]))
    k = auto_latitude_curve(img, pivot=0.5, contrast=1.3, strength=0.0)
    assert abs(k - 1.0) < 1e-9

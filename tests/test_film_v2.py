"""Tests for the v2 density-domain film engine.

Covers the pure functions in ``cli.lib.process_film_functions.density`` and the
end-to-end ``algo="v2"`` pipeline in ``process_film.py`` — the implementation of
design/film-color-v2.md (density-domain colour inversion).

The v1 engine is untouched; these tests run fast on synthetic images and do not
require real film samples.
"""
import cv2
import numpy as np
import pytest

from cli.lib.process_film import process_film_bytestream_with_params
from cli.lib.process_film_functions import density as D


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_neutral_negative(height=64, width=8, t_base=0.5):
    """A neutral (grayscale) negative.

    Scene luminance v rises down the rows (0.05..0.95). Transmission
    ``T = t_base * (1 - v)``, so a brighter scene produces a denser (darker)
    negative — exactly like a color negative's neutral channel.
    """
    v = np.linspace(0.05, 0.95, height)[:, None, None].astype(np.float32)
    t = (t_base * (1.0 - v)).astype(np.float32)
    return np.broadcast_to(t, (height, width, 3)).copy()


def _encode_tiff_u16(img_0_1):
    bgr = (np.clip(img_0_1, 0, 1) * 65535.0).astype(np.uint16)[..., ::-1].copy()
    ok, buf = cv2.imencode(".tif", bgr)
    assert ok, "cv2 failed to encode the synthetic TIFF"
    return buf.tobytes()


def _decode_to_float(out_bytes):
    arr = cv2.imdecode(np.frombuffer(out_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
    return arr[..., ::-1].astype(np.float32) / 65535.0


def _run_v2(img_0_1, **kwargs):
    out = process_film_bytestream_with_params(
        _encode_tiff_u16(img_0_1),
        preset_mask_r=kwargs.get("mask_r", 127),
        preset_mask_g=kwargs.get("mask_g", 127),
        preset_mask_b=kwargs.get("mask_b", 127),
        preset_gamma=kwargs.get("gamma", 0.45),
        preset_contrast=kwargs.get("contrast", 1.0),
        preset_contrast_r=1.0,
        preset_contrast_g=1.0,
        preset_contrast_b=1.0,
        rotate_clockwise=0,
        white_balance=kwargs.get("white_balance", "auto"),
        exposure_ev=kwargs.get("exposure_ev", 0.0),
        tone_pivot=0.5,
        tone_curve=0.5,
        color_mode=kwargs.get("color_mode", "skin_protect"),
        saturation=kwargs.get("saturation", 1.0),
        is_raw=False,
        algo="v2",
    )
    assert out is not None and len(out) > 0, "v2 returned no output"
    return _decode_to_float(out)


# ── pure functions: density / mask ───────────────────────────────────────────

def test_to_density_known_values():
    d = D.to_density(np.array([1.0, 0.1, 0.01], dtype=np.float32))
    np.testing.assert_allclose(d, [0.0, 1.0, 2.0], atol=1e-4)


def test_from_density_round_trip():
    x = np.array([0.3, 0.55, 0.82], dtype=np.float32)
    np.testing.assert_allclose(D.from_density(D.to_density(x)), x, atol=1e-5)


def test_mask_to_density_values():
    d = D.mask_to_density(np.array([255, 127.5, 25.5]))
    # 255 -> transmission 1.0 -> density 0; 127.5 -> 0.5 -> 0.3010...
    np.testing.assert_allclose(d, [0.0, 0.3010299957, 1.0], atol=1e-4)


def test_subtract_mask_matches_transmission_division():
    a = np.array([0.7, 0.4, 0.2], dtype=np.float32)
    b = np.array([0.6, 0.5, 0.4], dtype=np.float32)
    # Density subtraction == transmission division.
    np.testing.assert_allclose(
        10.0 ** -(D.subtract_mask(D.to_density(a), D.to_density(b))),
        a / b,
        atol=1e-5,
    )


# ── pure functions: decross-talk ─────────────────────────────────────────────

def test_decrosstalk_preserves_neutral_after_normalization():
    # STATUS_M rows do not sum to 1, but the per-channel endpoint normalization
    # absorbs that imbalance, so a neutral ramp stays neutral end to end.
    v = np.linspace(0.1, 0.9, 64)[:, None, None].astype(np.float32)
    linear = np.broadcast_to(v, (64, 8, 3)).copy()
    d_true = D.decrosstalk(D.to_density(linear))
    lo, hi = D.estimate_density_limits(d_true)
    norm = D.normalize_density(d_true, lo, hi)
    spread = norm.max(axis=2) - norm.min(axis=2)
    assert spread.max() < 1e-3


def test_decrosstalk_disabled_is_identity():
    d = D.to_density(np.array([[0.3, 0.5, 0.7]], dtype=np.float32))
    out = D.decrosstalk(d, enabled=False)
    np.testing.assert_array_equal(out, d)


def test_decrosstalk_default_matrix_shape():
    out = D.decrosstalk(D.to_density(np.full((2, 2, 3), 0.18, dtype=np.float32)))
    assert out.shape == (2, 2, 3)
    assert np.isfinite(out).all()


# ── pure functions: endpoint estimation ──────────────────────────────────────

def test_estimate_density_limits_constant_image():
    d = D.to_density(np.full((16, 16, 3), 0.5, dtype=np.float32))
    lo, hi = D.estimate_density_limits(d)
    expected = np.full(3, -np.log10(0.5), dtype=np.float32)
    np.testing.assert_allclose(lo, expected, atol=1e-3)
    np.testing.assert_allclose(hi, expected, atol=1e-3)


def test_estimate_density_limits_ignores_white_spike():
    rng = np.random.default_rng(0)
    mid = np.clip(rng.normal(0.6, 0.02, (70, 40, 3)), 0, 1).astype(np.float32)
    white = np.full((30, 40, 3), 0.999, dtype=np.float32)
    img = np.concatenate([mid, white], axis=0)
    lo, hi = D.estimate_density_limits(D.to_density(img))
    # Without the spike guard the 30% dead-white block (density ~0.0004) would
    # steal the low endpoint; with it, the endpoint stays on the real data.
    assert np.all(lo > 0.10), f"low endpoint pulled into dead-white spike: {lo}"
    assert np.all(hi < 0.6), f"high endpoint pulled into dead-white spike: {hi}"


def test_estimate_density_limits_uses_roi():
    img = np.full((64, 64, 3), 0.5, dtype=np.float32)
    img[16:48, 16:48, :] = 0.2  # inner ROI is darker
    d = D.to_density(img)
    lo_full, _ = D.estimate_density_limits(d)
    lo_roi, _ = D.estimate_density_limits(d, roi=(16, 16, 48, 48))
    assert lo_roi[0] > lo_full[0], "ROI sampling must reflect the inner density"


def test_normalize_density_degenerate_range_no_nan():
    d = np.array([[0.5, 0.5, 0.5]], dtype=np.float32)
    out = D.normalize_density(d, np.array([0.5, 0.5, 0.5]), np.array([0.5, 0.5, 0.5]))
    assert np.isfinite(out).all()
    assert out.shape == d.shape


# ── pure functions: base estimation / transfer / post-gamma ──────────────────

def test_auto_base_mask_is_99th_percentile():
    rng = np.random.default_rng(1)
    img = np.clip(rng.normal(0.5, 0.1, (100, 100, 3)), 0, 1).astype(np.float32)
    base = D.auto_base_mask(img)
    for c in range(3):
        expected = np.percentile(img[..., c], 99.0) * 255.0
        assert abs(base[c] - expected) < 0.5


def test_srgb_round_trip():
    x = np.linspace(0.0, 1.0, 257).astype(np.float32)
    np.testing.assert_allclose(D.srgb_to_linear(D.linear_to_srgb(x)), x, atol=1e-3)
    # Endpoints pin exactly.
    assert D.srgb_to_linear(np.array([0.0, 1.0]))[0] == 0.0
    assert abs(D.srgb_to_linear(np.array([1.0]))[0] - 1.0) < 1e-6


def test_apply_post_gamma_temp_and_tint_direction():
    neutral = np.full((2, 2, 3), 0.5, dtype=np.float32)
    warm = D.apply_post_gamma_adjustments(neutral, temperature=1.0)
    magenta = D.apply_post_gamma_adjustments(neutral, tint=1.0)
    assert warm[0, 0, 0] > warm[0, 0, 2] + 0.05        # R > B
    assert magenta[0, 0, 0] > magenta[0, 0, 1] + 0.05  # R > G
    assert magenta[0, 0, 2] > magenta[0, 0, 1] + 0.05  # B > G


def test_density_luma_weights():
    # The Rec.709 weights sum to 1, so a unit density vector gives unit luma.
    ones = np.ones(3, dtype=np.float32)
    assert abs(D.density_luma(ones) - 1.0) < 1e-4
    # A single channel contributes exactly its coefficient.
    assert abs(D.density_luma(np.array([1.0, 0.0, 0.0], dtype=np.float32)) - 0.2126) < 1e-4


# ── v2 end-to-end pipeline ───────────────────────────────────────────────────

def test_v2_gray_negative_inverts_monotonically():
    out = _run_v2(_make_neutral_negative(), white_balance="none")
    rows = out.mean(axis=(1, 2))
    assert np.all(np.diff(rows) > -1e-3), "positive must rise with scene luminance"
    assert rows[-1] > rows[0], "bright scene must map to bright positive"


def test_v2_neutral_negative_stays_neutral():
    out = _run_v2(_make_neutral_negative(), white_balance="auto")
    spread = out.max(axis=2) - out.min(axis=2)
    assert spread.max() < 0.02, f"neutral input must not gain a cast: {spread.max()}"


def test_v2_temp_positive_warms_output():
    out = _run_v2(_make_neutral_negative(), white_balance=[50, 0])
    means = out.mean(axis=(0, 1))
    assert means[0] > means[2] + 0.01, f"temp>0 must warm (R>B): {means}"


def test_v2_tint_positive_pushes_magenta():
    out = _run_v2(_make_neutral_negative(), white_balance=[0, 50])
    means = out.mean(axis=(0, 1))
    assert means[0] > means[1] + 0.01, f"tint>0 must push magenta (R>G): {means}"
    assert means[2] > means[1] + 0.01, f"tint>0 must push magenta (B>G): {means}"


def test_v2_auto_base_mask_fallback_when_mask_zero():
    out = _run_v2(
        _make_neutral_negative(),
        mask_r=0, mask_g=0, mask_b=0,
        white_balance="auto",
    )
    assert np.isfinite(out).all()
    rows = out.mean(axis=(1, 2))
    assert rows[-1] > rows[0], "auto base fallback must still invert correctly"


def test_v2_exposure_shifts_brightness_in_density():
    base = _run_v2(_make_neutral_negative(), white_balance="none", exposure_ev=0.0)
    lifted = _run_v2(_make_neutral_negative(), white_balance="none", exposure_ev=1.0)
    assert lifted.mean() > base.mean() + 0.01, "+1 EV must brighten the positive"


def test_v2_runs_with_16bit_output():
    out = process_film_bytestream_with_params(
        _encode_tiff_u16(_make_neutral_negative()),
        preset_mask_r=127, preset_mask_g=127, preset_mask_b=127,
        is_raw=False, algo="v2",
    )
    assert out is not None and len(out) > 0
    arr = cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_UNCHANGED)
    assert arr.dtype == np.uint16, "16-bit input must produce 16-bit output"

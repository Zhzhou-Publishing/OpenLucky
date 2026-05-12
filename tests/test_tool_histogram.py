"""Tests for `cli.openlucky tool histogram`."""
import json
import math

import cv2
import numpy as np
import pytest


def _write_solid_png(path, r, g, b, size=64):
    img = np.zeros((size, size, 3), dtype=np.uint8)
    # cv2 writes BGR; arrange so the read-back R/G/B match expectations
    img[..., 0] = b
    img[..., 1] = g
    img[..., 2] = r
    cv2.imwrite(str(path), img)


def _write_solid_tiff_16bit(path, r, g, b, size=64):
    img = np.zeros((size, size, 3), dtype=np.uint16)
    img[..., 0] = b
    img[..., 1] = g
    img[..., 2] = r
    cv2.imwrite(str(path), img)


def _assert_payload_shape(payload):
    assert set(payload) == {"data", "visual_meta"}
    data = payload["data"]
    assert set(data) == {"red", "green", "blue", "luminosity"}
    meta = payload["visual_meta"]
    assert set(meta) == {"suggested_max_y", "is_clipped", "total_pixels"}
    return data, meta


def test_histogram_basic_rgbl_linear_counts(run_cli, output_dir, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=100, b=50, size=64)

    res = run_cli("tool", "histogram", "-i", str(src), "-m", "linear")
    assert res.returncode == 0, f"stderr: {res.stderr}"

    payload = json.loads(res.stdout)
    data, meta = _assert_payload_shape(payload)

    pixel_count = 64 * 64
    assert all(len(ch) == 256 for ch in data.values()), "8-bit input → 256 bins"

    # 3-point gaussian smoothing preserves total bin mass for interior peaks
    assert sum(data["red"]) == pixel_count
    assert sum(data["green"]) == pixel_count
    assert sum(data["blue"]) == pixel_count
    assert sum(data["luminosity"]) == pixel_count

    # Peak bin holds 0.5 of the count after [0.25, 0.5, 0.25] smoothing
    assert data["red"][200] == pixel_count // 2
    assert data["green"][100] == pixel_count // 2
    assert data["blue"][50] == pixel_count // 2

    # BT.601 luminance: 0.299*200 + 0.587*100 + 0.114*50 ≈ 124.2
    expected_l_bin = int(round(0.299 * 200 + 0.587 * 100 + 0.114 * 50))
    assert data["luminosity"][expected_l_bin] == pixel_count // 2

    assert meta["total_pixels"] == pixel_count
    assert meta["suggested_max_y"] >= max(data["red"])
    assert isinstance(meta["is_clipped"], bool)


def test_histogram_default_mode_is_log(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=100, b=50, size=64)

    res = run_cli("tool", "histogram", "-i", str(src))
    assert res.returncode == 0, res.stderr

    payload = json.loads(res.stdout)
    data, meta = _assert_payload_shape(payload)

    pixel_count = 64 * 64
    half = pixel_count // 2
    # log1p of the smoothed peak (half-count), kept at 2-decimal precision
    expected_peak = round(math.log1p(half), 2)
    assert data["red"][200] == pytest.approx(expected_peak, abs=0.01)
    assert meta["suggested_max_y"] >= expected_peak
    assert meta["total_pixels"] == pixel_count


def test_histogram_suggested_max_y_covers_data_peak(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=120, g=120, b=120, size=64)

    res = run_cli("tool", "histogram", "-i", str(src))
    assert res.returncode == 0, res.stderr

    payload = json.loads(res.stdout)
    data, meta = _assert_payload_shape(payload)

    global_peak = max(max(ch) for ch in data.values())
    # suggested_max_y must sit above the peak so the renderer never overshoots
    assert meta["suggested_max_y"] >= global_peak


def test_histogram_is_clipped_flag_for_pure_black(run_cli, tmp_path):
    src = tmp_path / "black.png"
    _write_solid_png(src, r=0, g=0, b=0, size=64)

    res = run_cli("tool", "histogram", "-i", str(src), "-m", "linear")
    assert res.returncode == 0, res.stderr

    payload = json.loads(res.stdout)
    _, meta = _assert_payload_shape(payload)
    # All pixels in bin 0 → end-bin pile-up should mark the histogram clipped
    assert meta["is_clipped"] is True


def test_histogram_is_clipped_flag_off_for_midtones(run_cli, tmp_path):
    src = tmp_path / "mid.png"
    _write_solid_png(src, r=128, g=128, b=128, size=64)

    res = run_cli("tool", "histogram", "-i", str(src), "-m", "linear")
    assert res.returncode == 0, res.stderr

    payload = json.loads(res.stdout)
    _, meta = _assert_payload_shape(payload)
    assert meta["is_clipped"] is False


def test_histogram_downsampling_collapses_bins(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=100, b=50)

    res = run_cli("tool", "histogram", "-i", str(src), "-d", "256")
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    data, _ = _assert_payload_shape(payload)
    # 8-bit native is 256, downsampling 256 is a no-op
    assert len(data["red"]) == 256


def test_histogram_gamma_shifts_bin(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=200, b=200)

    res = run_cli("tool", "histogram", "-i", str(src), "-g", "2.2", "-m", "linear")
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    data, _ = _assert_payload_shape(payload)
    # (200/255)^(1/2.2) * 255 ≈ 228
    expected_bin = int(round((200 / 255) ** (1 / 2.2) * 255))
    assert data["red"][expected_bin] > 0
    assert data["red"][200] == 0


def test_histogram_downsampling_rejects_non_power_of_two(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=10, g=10, b=10)

    res = run_cli("tool", "histogram", "-i", str(src), "-d", "384")
    assert res.returncode != 0
    assert "power of 2" in (res.stdout + res.stderr)


def test_histogram_downsampling_rejects_below_minimum(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=10, g=10, b=10)

    res = run_cli("tool", "histogram", "-i", str(src), "-d", "128")
    assert res.returncode != 0
    assert "[256, 65536]" in (res.stdout + res.stderr)


def test_histogram_rejects_missing_input(run_cli, tmp_path):
    res = run_cli("tool", "histogram", "-i", str(tmp_path / "does_not_exist.png"))
    assert res.returncode != 0
    assert "does not exist" in (res.stdout + res.stderr)


def test_histogram_16bit_tiff_native_bins(run_cli, tmp_path):
    src = tmp_path / "solid.tiff"
    _write_solid_tiff_16bit(src, r=40000, g=20000, b=10000, size=32)

    res = run_cli("tool", "histogram", "-i", str(src), "-d", "256", "-m", "linear")
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    data, meta = _assert_payload_shape(payload)

    pixel_count = 32 * 32
    assert len(data["red"]) == 256
    # Downsampled bin index for raw_val in 256-bin space = raw_val // (65536/256)
    # Smoothed peak holds 0.5 of the count
    assert data["red"][40000 // 256] == pixel_count // 2
    assert data["green"][20000 // 256] == pixel_count // 2
    assert data["blue"][10000 // 256] == pixel_count // 2
    assert meta["total_pixels"] == pixel_count


def test_histogram_rejects_old_normalization_flag(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=100, b=50)

    # `-n` was removed; argparse should reject it.
    res = run_cli("tool", "histogram", "-i", str(src), "-n", "256")
    assert res.returncode != 0

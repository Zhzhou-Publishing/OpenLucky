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


def test_histogram_basic_rgbl_counts(run_cli, output_dir, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=100, b=50, size=64)

    res = run_cli("tool", "histogram", "-i", str(src))
    assert res.returncode == 0, f"stderr: {res.stderr}"

    data = json.loads(res.stdout)
    assert len(data) == 4, "rgbl should produce 4 channels"
    assert all(len(ch) == 256 for ch in data), "8-bit input → 256 bins"

    pixel_count = 64 * 64
    assert sum(data[0]) == pixel_count
    assert sum(data[1]) == pixel_count
    assert sum(data[2]) == pixel_count
    assert sum(data[3]) == pixel_count

    assert data[0][200] == pixel_count
    assert data[1][100] == pixel_count
    assert data[2][50] == pixel_count

    # BT.601 luminance: 0.299*200 + 0.587*100 + 0.114*50 ≈ 124.2
    expected_l_bin = int(round(0.299 * 200 + 0.587 * 100 + 0.114 * 50))
    assert data[3][expected_l_bin] == pixel_count


def test_histogram_downsampling_collapses_bins(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=100, b=50)

    res = run_cli("tool", "histogram", "-i", str(src), "-d", "256")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # 8-bit native is 256, downsampling 256 is a no-op
    assert len(data[0]) == 256


def test_histogram_normalization_log(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=100, b=50)

    res = run_cli("tool", "histogram", "-i", str(src), "-n", "256", "-m", "log")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # Single non-zero bin per channel, so it should map to the normalization max
    assert max(data[0]) == 256
    assert max(data[1]) == 256
    assert max(data[2]) == 256


def test_histogram_gamma_shifts_bin(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=200, g=200, b=200)

    res = run_cli("tool", "histogram", "-i", str(src), "-g", "2.2")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # (200/255)^(1/2.2) * 255 ≈ 228
    expected_bin = int(round((200 / 255) ** (1 / 2.2) * 255))
    assert data[0][expected_bin] > 0
    assert data[0][200] == 0


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

    res = run_cli("tool", "histogram", "-i", str(src), "-d", "256", "-n", "256")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert len(data) == 4
    assert len(data[0]) == 256
    # downsampled bin index for 40000 in 256-bin space = 40000 // (65536/256) = 40000 // 256
    assert data[0][40000 // 256] == 256
    assert data[1][20000 // 256] == 256
    assert data[2][10000 // 256] == 256

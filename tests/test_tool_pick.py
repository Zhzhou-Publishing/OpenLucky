"""Tests for `cli.openlucky tool pick`."""
import json

import cv2
import numpy as np


def _write_solid_png(path, r, g, b, size=32):
    img = np.zeros((size, size, 3), dtype=np.uint8)
    # cv2 stores BGR, so order channels accordingly
    img[..., 0] = b
    img[..., 1] = g
    img[..., 2] = r
    cv2.imwrite(str(path), img)


def _write_solid_tiff_16bit(path, r, g, b, size=16):
    img = np.zeros((size, size, 3), dtype=np.uint16)
    img[..., 0] = b
    img[..., 1] = g
    img[..., 2] = r
    cv2.imwrite(str(path), img)


def test_pick_solid_8bit(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=22, g=33, b=44, size=32)

    res = run_cli("tool", "pick", "-i", str(src), "-x", "5", "-y", "10")
    assert res.returncode == 0, res.stderr

    data = json.loads(res.stdout)
    assert data["rgb"] == [22, 33, 44]
    assert data["x"] == 5
    assert data["y"] == 10
    assert data["width"] == 32
    assert data["height"] == 32
    assert data["bit_depth"] == 8
    assert data["is_raw"] is False


def test_pick_8bit_upsampled_to_16bit(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=22, g=33, b=44, size=16)

    res = run_cli("tool", "pick", "-i", str(src), "-x", "0", "-y", "0", "-f", "16")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # 8-bit upsampled to 16-bit: value * 257
    assert data["rgb"] == [22 * 257, 33 * 257, 44 * 257]
    assert data["bit_depth"] == 16


def test_pick_16bit_native(run_cli, tmp_path):
    src = tmp_path / "solid.tiff"
    _write_solid_tiff_16bit(src, r=40000, g=20000, b=10000, size=16)

    res = run_cli("tool", "pick", "-i", str(src), "-x", "3", "-y", "7", "-f", "16")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["rgb"] == [40000, 20000, 10000]
    assert data["bit_depth"] == 16
    assert data["is_raw"] is False


def test_pick_16bit_downsampled_to_8bit(run_cli, tmp_path):
    src = tmp_path / "solid.tiff"
    _write_solid_tiff_16bit(src, r=40000, g=20000, b=10000, size=16)

    res = run_cli("tool", "pick", "-i", str(src), "-x", "0", "-y", "0", "-f", "8")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["rgb"] == [round(40000 / 257), round(20000 / 257), round(10000 / 257)]
    assert data["bit_depth"] == 8


def test_pick_out_of_range(run_cli, tmp_path):
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=10, g=20, b=30, size=32)

    res = run_cli("tool", "pick", "-i", str(src), "-x", "100", "-y", "100")
    assert res.returncode != 0
    assert "out of range" in (res.stdout + res.stderr)


def test_pick_missing_input(run_cli, tmp_path):
    res = run_cli("tool", "pick", "-i", str(tmp_path / "missing.png"), "-x", "0", "-y", "0")
    assert res.returncode != 0
    assert "does not exist" in (res.stdout + res.stderr)


def test_pick_corner_pixel(run_cli, tmp_path):
    """Edge-of-bounds: last valid pixel is (width-1, height-1)."""
    src = tmp_path / "solid.png"
    _write_solid_png(src, r=99, g=88, b=77, size=32)

    res = run_cli("tool", "pick", "-i", str(src), "-x", "31", "-y", "31")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["rgb"] == [99, 88, 77]


def test_pick_gradient_returns_correct_pixel(run_cli, tmp_path):
    """A non-uniform image: confirm we read the requested pixel, not a neighbor."""
    src = tmp_path / "gradient.png"
    size = 8
    img = np.zeros((size, size, 3), dtype=np.uint8)
    for y in range(size):
        for x in range(size):
            img[y, x, 0] = 10 + x  # B
            img[y, x, 1] = 100 + y  # G
            img[y, x, 2] = 200 - x  # R
    cv2.imwrite(str(src), img)

    res = run_cli("tool", "pick", "-i", str(src), "-x", "3", "-y", "5")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # PNG is lossless; values must round-trip exactly
    assert data["rgb"] == [200 - 3, 100 + 5, 10 + 3]

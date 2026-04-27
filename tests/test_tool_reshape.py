"""Tests for `cli.openlucky tool reshape`."""
import cv2
import numpy as np
import pytest


def _decode(path):
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)


@pytest.mark.slow
def test_reshape_valid_corners(run_cli, random_none_raw_input, output_dir):
    img = _decode(random_none_raw_input)
    assert img is not None, "could not decode source image"
    h, w = img.shape[:2]
    inset = 10
    if w <= 2 * inset or h <= 2 * inset:
        pytest.skip(f"sample image too small ({w}x{h}) for reshape test")

    out = output_dir / "reshaped.png"
    res = run_cli(
        "tool", "reshape",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "-p1", f"{inset},{inset}",
        "-p2", f"{w - inset - 1},{inset}",
        "-p3", f"{w - inset - 1},{h - inset - 1}",
        "-p4", f"{inset},{h - inset - 1}",
        "-s", "800,600",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


def test_reshape_invalid_point_format(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "tool", "reshape",
        "-i", str(fake),
        "-o", str(output_dir / "out.png"),
        "-p1", "10",
        "-p2", "100,10",
        "-p3", "100,100",
        "-p4", "10,100",
        "-s", "800,600",
    )
    assert res.returncode != 0
    assert "point1" in (res.stdout + res.stderr)


def test_reshape_invalid_shape_format(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "tool", "reshape",
        "-i", str(fake),
        "-o", str(output_dir / "out.png"),
        "-p1", "10,10",
        "-p2", "100,10",
        "-p3", "100,100",
        "-p4", "10,100",
        "-s", "abc",
    )
    assert res.returncode != 0
    assert "shape" in (res.stdout + res.stderr).lower()


@pytest.mark.slow
def test_reshape_degenerate_points(run_cli, random_none_raw_input, output_dir):
    out = output_dir / "out.png"
    res = run_cli(
        "tool", "reshape",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "-p1", "10,10",
        "-p2", "10,10",
        "-p3", "10,10",
        "-p4", "10,10",
        "-s", "800,600",
    )
    assert res.returncode != 0
    assert "convex quadrilateral" in (res.stdout + res.stderr).lower()

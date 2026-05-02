"""Tests for `cli.openlucky tool resize`."""
import cv2
import numpy as np
import pytest


def _decode(path):
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)


@pytest.mark.slow
def test_resize_long_edge_fixed_value(run_cli, random_none_raw_input, output_dir):
    out = output_dir / random_none_raw_input.name
    res = run_cli(
        "tool", "resize",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "--edge", "long-edge",
        "--mode", "fixed-value",
        "--value", "200",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    img = _decode(out)
    assert img is not None
    h, w = img.shape[:2]
    assert max(h, w) == 200, f"long edge expected 200, got {max(h, w)}"


@pytest.mark.slow
def test_resize_ratio_half(run_cli, random_none_raw_input, output_dir):
    src = _decode(random_none_raw_input)
    src_h, src_w = src.shape[:2]

    out = output_dir / random_none_raw_input.name
    res = run_cli(
        "tool", "resize",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "--mode", "ratio",
        "--value", "0.5",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    img = _decode(out)
    assert img.shape[:2] == (int(src_h * 0.5), int(src_w * 0.5))


@pytest.mark.slow
@pytest.mark.parametrize("edge", ["width", "height", "short-edge"])
def test_resize_other_edges(run_cli, random_none_raw_input, output_dir, edge):
    out = output_dir / random_none_raw_input.name
    res = run_cli(
        "tool", "resize",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "--edge", edge,
        "--mode", "fixed-value",
        "--value", "200",
    )
    assert res.returncode == 0, f"edge={edge}\nstdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.slow
def test_resize_raw_appends_tif(run_cli, random_raw_input, output_dir):
    # validate_output_filename allows <input.name> as the requested output;
    # resize_image then forces a .tif suffix internally for RAW.
    requested_out = output_dir / random_raw_input.name
    actual_out = requested_out.with_suffix(".tif")
    res = run_cli(
        "tool", "resize",
        "-i", str(random_raw_input),
        "-o", str(requested_out),
        "--mode", "fixed-value",
        "--value", "200",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert actual_out.exists() and actual_out.stat().st_size > 0


def test_resize_ratio_non_numeric(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "tool", "resize",
        "-i", str(fake),
        "-o", str(output_dir / fake.name),
        "--mode", "ratio",
        "--value", "abc",
    )
    assert res.returncode != 0
    assert "Invalid value for ratio mode" in (res.stdout + res.stderr)


def test_resize_fixed_value_non_integer(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "tool", "resize",
        "-i", str(fake),
        "-o", str(output_dir / fake.name),
        "--mode", "fixed-value",
        "--value", "1.5",
    )
    assert res.returncode != 0
    assert "Invalid value for fixed-value mode" in (res.stdout + res.stderr)


@pytest.mark.slow
def test_resize_output_filename_mismatch(run_cli, random_none_raw_input, output_dir):
    # Output filename differs from input → validation should reject.
    out = output_dir / "definitely_different_name.png"
    res = run_cli(
        "tool", "resize",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "--mode", "fixed-value",
        "--value", "200",
    )
    assert res.returncode != 0
    assert "Output filename must match" in (res.stdout + res.stderr)


@pytest.mark.parametrize(
    "extra",
    [
        ["--edge", "diagonal", "--value", "100"],
        ["--mode", "percentage", "--value", "0.5"],
    ],
    ids=["bad-edge", "bad-mode"],
)
def test_resize_invalid_choices(run_cli, output_dir, tmp_path, extra):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "tool", "resize",
        "-i", str(fake),
        "-o", str(output_dir / fake.name),
        *extra,
    )
    assert res.returncode != 0


@pytest.mark.slow
def test_resize_no_value_non_raw_copy(run_cli, random_none_raw_input, output_dir):
    """Without -v, non-RAW images should be directly copied to output."""
    out = output_dir / random_none_raw_input.name
    res = run_cli(
        "tool", "resize",
        "-i", str(random_none_raw_input),
        "-o", str(out),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists()
    # File should be identical to input (direct copy)
    assert out.read_bytes() == random_none_raw_input.read_bytes()


@pytest.mark.slow
def test_resize_no_value_raw_convert_to_tiff(run_cli, random_raw_input, output_dir):
    """Without -v, RAW images should be converted to TIFF without resize."""
    out = output_dir / (random_raw_input.name + ".tif")
    res = run_cli(
        "tool", "resize",
        "-i", str(random_raw_input),
        "-o", str(out),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    # resize_image forces .tif suffix for RAW output
    actual_out = out if out.suffix == '.tif' else out.with_suffix('.tif')
    assert actual_out.exists() and actual_out.stat().st_size > 0
    assert "no resize" in (res.stdout + res.stderr)

"""Tests for `cli.openlucky tiff2jpeg`."""
import pytest


@pytest.mark.slow
def test_tiff2jpeg_converts(run_cli, random_tiff_input, output_dir):
    out = output_dir / "out.jpg"
    res = run_cli("tiff2jpeg", "-i", str(random_tiff_input), "-o", str(out))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


def test_tiff2jpeg_missing_required_args(run_cli, output_dir):
    res = run_cli("tiff2jpeg", "-o", str(output_dir / "out.jpg"))
    assert res.returncode != 0


def test_tiff2jpeg_input_missing(run_cli, output_dir, tmp_path):
    out = output_dir / "out.jpg"
    res = run_cli(
        "tiff2jpeg",
        "-i", str(tmp_path / "nope.tif"),
        "-o", str(out),
    )
    assert not out.exists(), "output should not be created on missing input"
    combined = res.stdout + res.stderr
    assert "error" in combined.lower() or res.returncode != 0

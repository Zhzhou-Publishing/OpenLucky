"""Tests for `cli.openlucky raw2tiff`."""
import pytest


@pytest.mark.slow
def test_raw2tiff_converts_to_tiff(run_cli, random_raw_input, output_dir):
    out = output_dir / "out.tif"
    res = run_cli("raw2tiff", "-i", str(random_raw_input), "-o", str(out))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


def test_raw2tiff_input_missing(run_cli, output_dir, tmp_path):
    out = output_dir / "out.tif"
    res = run_cli(
        "raw2tiff",
        "-i", str(tmp_path / "nope.nef"),
        "-o", str(out),
    )
    # Output should not be produced when the input is missing.
    assert not out.exists(), "output should not be created on missing input"
    combined = res.stdout + res.stderr
    assert "Error" in combined or res.returncode != 0


def test_raw2tiff_missing_required_args(run_cli, output_dir):
    # --input is required; argparse exits non-zero.
    res = run_cli("raw2tiff", "-o", str(output_dir / "out.tif"))
    assert res.returncode != 0

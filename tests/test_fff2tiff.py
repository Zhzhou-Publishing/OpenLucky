"""Tests for `cli.openlucky fff2tiff`."""
import pytest

import tifffile


@pytest.mark.slow
def test_fff2tiff_converts_to_single_page_tiff(run_cli, random_fff_input, output_dir):
    out = output_dir / "out.tif"
    res = run_cli("fff2tiff", "-i", str(random_fff_input), "-o", str(out))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0

    # Output must be a clean, single-page TIFF: the embedded thumbnail/preview
    # pages from the FFF should be dropped, leaving only the full-res image.
    with tifffile.TiffFile(str(out)) as src, tifffile.TiffFile(str(random_fff_input)) as orig:
        assert len(src.pages) == 1, "expected a single-page TIFF"
        out_page = src.pages[0]
        main_page = max(orig.pages, key=lambda p: int(p.shape[0]) * int(p.shape[1]))
        # Dimensions and bit depth of the main scan are preserved.
        assert out_page.shape == main_page.shape
        assert out_page.dtype == main_page.dtype


@pytest.mark.slow
def test_fff2tiff_pixels_preserved(run_cli, random_fff_input, output_dir):
    """Conversion is lossless: pixels round-trip unchanged (deflate default)."""
    out = output_dir / "out.tif"
    res = run_cli("fff2tiff", "-i", str(random_fff_input), "-o", str(out))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"

    with tifffile.TiffFile(str(random_fff_input)) as orig:
        main_page = max(orig.pages, key=lambda p: int(p.shape[0]) * int(p.shape[1]))
        src_arr = main_page.asarray()
    out_arr = tifffile.imread(str(out))
    assert (src_arr == out_arr).all(), "pixels changed during conversion"


def test_fff2tiff_normalizes_output_extension(run_cli, random_fff_input, output_dir):
    """A non-TIFF output suffix is coerced to .tif."""
    requested = output_dir / "out.bin"
    res = run_cli("fff2tiff", "-i", str(random_fff_input), "-o", str(requested))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert (output_dir / "out.tif").exists()
    assert not requested.exists()


def test_fff2tiff_input_missing(run_cli, output_dir, tmp_path):
    out = output_dir / "out.tif"
    res = run_cli(
        "fff2tiff",
        "-i", str(tmp_path / "nope.fff"),
        "-o", str(out),
    )
    assert not out.exists(), "output should not be created on missing input"
    combined = res.stdout + res.stderr
    assert "Error" in combined or res.returncode != 0


def test_fff2tiff_missing_required_args(run_cli, output_dir):
    # --input is required; argparse exits non-zero.
    res = run_cli("fff2tiff", "-o", str(output_dir / "out.tif"))
    assert res.returncode != 0

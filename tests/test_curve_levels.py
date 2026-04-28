"""Tests for `cli.openlucky curve levels`."""
import pytest


@pytest.mark.slow
def test_levels_non_raw_defaults(run_cli, random_none_raw_input, output_dir):
    out = output_dir / "leveled.png"
    res = run_cli(
        "curve", "levels",
        "-i", str(random_none_raw_input),
        "-o", str(out),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.slow
def test_levels_raw_appends_tiff(run_cli, random_raw_input, output_dir):
    requested_out = output_dir / "leveled.png"
    actual_out = output_dir / "leveled.png.tiff"
    res = run_cli(
        "curve", "levels",
        "-i", str(random_raw_input),
        "-o", str(requested_out),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert actual_out.exists() and actual_out.stat().st_size > 0


@pytest.mark.slow
def test_levels_with_clip_options(run_cli, random_none_raw_input, output_dir):
    out = output_dir / "clipped.png"
    res = run_cli(
        "curve", "levels",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "-s", "100",
        "-hl", "100",
        "-c", "red",
        "-m", "clip-only",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


def test_levels_input_missing(run_cli, output_dir, tmp_path):
    res = run_cli(
        "curve", "levels",
        "-i", str(tmp_path / "nope.png"),
        "-o", str(output_dir / "out.png"),
    )
    assert res.returncode != 0
    assert "Input file does not exist" in (res.stdout + res.stderr)


@pytest.mark.parametrize(
    "extra",
    [
        ["-c", "purple"],
        ["-m", "stretch-only"],
    ],
    ids=["bad-channel", "bad-mode"],
)
def test_levels_invalid_choices(run_cli, output_dir, tmp_path, extra):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "curve", "levels",
        "-i", str(fake),
        "-o", str(output_dir / "out.png"),
        *extra,
    )
    assert res.returncode != 0


def test_levels_non_int_shadows(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "curve", "levels",
        "-i", str(fake),
        "-o", str(output_dir / "out.png"),
        "-s", "abc",
    )
    assert res.returncode != 0

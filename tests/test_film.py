"""Tests for `cli.openlucky film`."""
import json

import pytest


@pytest.mark.slow
def test_film_non_raw_with_explicit_config(
    run_cli, random_none_raw_input, sample_config, output_dir
):
    out = output_dir / "out.png"
    res = run_cli(
        "film",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "-c", str(sample_config),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0

    preset_file = random_none_raw_input.parent / ".preset.json"
    assert preset_file.exists(), "expected .preset.json to be written"
    data = json.loads(preset_file.read_text(encoding="utf-8"))
    entry = data[random_none_raw_input.name]
    assert entry["preset"] == "kodak_ultramax_400"


@pytest.mark.slow
def test_film_raw_with_explicit_config(
    run_cli, random_raw_input, sample_config, output_dir
):
    out = output_dir / "out.tiff"
    res = run_cli(
        "film",
        "-i", str(random_raw_input),
        "-o", str(out),
        "-c", str(sample_config),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.slow
def test_film_with_rotate_clockwise(
    run_cli, random_none_raw_input, sample_config, output_dir
):
    out = output_dir / "rotated.png"
    res = run_cli(
        "film",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "-c", str(sample_config),
        "-r", "90",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.slow
def test_film_auto_searches_config_in_cwd(
    run_cli, random_none_raw_input, sample_config, output_dir, tmp_path, repo_root
):
    # Auto-search looks for config.yaml in cwd; copy fixture config there.
    cwd = tmp_path / "auto_cwd"
    cwd.mkdir()
    (cwd / "config.yaml").write_bytes(sample_config.read_bytes())

    out = output_dir / "out.png"
    # Use absolute paths so the relative cwd doesn't break input/output resolution.
    res = run_cli(
        "film",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        cwd=cwd,
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


def test_film_missing_input_file(run_cli, sample_config, output_dir, tmp_path):
    res = run_cli(
        "film",
        "-i", str(tmp_path / "does_not_exist.tif"),
        "-o", str(output_dir / "out.png"),
        "-c", str(sample_config),
    )
    assert res.returncode != 0
    assert "Input file does not exist" in (res.stdout + res.stderr)


def test_film_missing_config_file(run_cli, output_dir, tmp_path):
    # Need an existing input so we get past the input-file check.
    fake_input = tmp_path / "fake.png"
    fake_input.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "film",
        "-i", str(fake_input),
        "-o", str(output_dir / "out.png"),
        "-c", str(tmp_path / "missing.yaml"),
    )
    assert res.returncode != 0
    assert "Configuration file does not exist" in (res.stdout + res.stderr)


@pytest.mark.slow
def test_film_unknown_preset(
    run_cli, random_none_raw_input, sample_config, output_dir
):
    res = run_cli(
        "film",
        "-i", str(random_none_raw_input),
        "-o", str(output_dir / "out.png"),
        "-c", str(sample_config),
        "-p", "no_such_preset",
    )
    assert res.returncode != 0


def test_film_invalid_rotate_value(run_cli, sample_config, output_dir, tmp_path):
    fake_input = tmp_path / "fake.png"
    fake_input.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "film",
        "-i", str(fake_input),
        "-o", str(output_dir / "out.png"),
        "-c", str(sample_config),
        "-r", "45",
    )
    assert res.returncode != 0

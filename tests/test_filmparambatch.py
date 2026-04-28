"""Tests for `cli.openlucky filmparambatch`."""
import json

import pytest


@pytest.mark.slow
def test_filmparambatch_non_raw_5_values(run_cli, none_raw_input_dir, output_dir):
    res = run_cli(
        "filmparambatch",
        "-i", str(none_raw_input_dir),
        "-o", str(output_dir),
        "--param", "110,220,210,1.1,1.5",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"

    inputs = [p.name for p in none_raw_input_dir.iterdir() if p.is_file()]
    outputs = [p.name for p in output_dir.iterdir() if p.is_file()]
    for name in inputs:
        assert name in outputs

    preset_file = none_raw_input_dir / ".preset.json"
    assert preset_file.exists()
    data = json.loads(preset_file.read_text(encoding="utf-8"))
    # Pick an arbitrary entry — all should exist for processed files
    sample_entry = next(iter(data.values()))
    assert sample_entry["preset"].startswith("custom_preset_")


@pytest.mark.slow
def test_filmparambatch_non_raw_8_values(run_cli, none_raw_input_dir, output_dir):
    res = run_cli(
        "filmparambatch",
        "-i", str(none_raw_input_dir),
        "-o", str(output_dir),
        "--param", "110,220,210,1.1,1.5,1.2,1.3,1.4",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"

    preset_file = none_raw_input_dir / ".preset.json"
    data = json.loads(preset_file.read_text(encoding="utf-8"))
    sample_entry = next(iter(data.values()))
    assert sample_entry["contrast_r"] == 1.2
    assert sample_entry["contrast_g"] == 1.3
    assert sample_entry["contrast_b"] == 1.4


@pytest.mark.slow
def test_filmparambatch_explicit_output(run_cli, none_raw_input_dir, output_dir):
    res = run_cli(
        "filmparambatch",
        "-i", str(none_raw_input_dir),
        "-o", str(output_dir),
        "--param", "110,220,210,1.1,1.5",
    )
    assert res.returncode == 0
    # Ensure default <input>/output is NOT created when --output is supplied.
    assert not (none_raw_input_dir / "output").exists()
    assert any(output_dir.iterdir())


def test_filmparambatch_input_dir_missing(run_cli, output_dir, tmp_path):
    res = run_cli(
        "filmparambatch",
        "-i", str(tmp_path / "no_dir"),
        "-o", str(output_dir),
        "--param", "110,220,210,1.1,1.5",
    )
    assert res.returncode != 0
    assert "does not exist" in (res.stdout + res.stderr)


def test_filmparambatch_empty_input_dir(run_cli, output_dir, tmp_path):
    empty = tmp_path / "empty_in"
    empty.mkdir()
    res = run_cli(
        "filmparambatch",
        "-i", str(empty),
        "-o", str(output_dir),
        "--param", "110,220,210,1.1,1.5",
    )
    assert res.returncode == 0
    assert "No supported image files" in (res.stdout + res.stderr)


def test_filmparambatch_invalid_param(run_cli, output_dir, tmp_path):
    empty = tmp_path / "in"
    empty.mkdir()
    res = run_cli(
        "filmparambatch",
        "-i", str(empty),
        "-o", str(output_dir),
        "--param", "abc,1,2,3,4",
    )
    assert res.returncode != 0
    assert "Failed to parse parameters" in (res.stdout + res.stderr)


def test_filmparambatch_missing_param(run_cli, output_dir, tmp_path):
    empty = tmp_path / "in"
    empty.mkdir()
    res = run_cli(
        "filmparambatch",
        "-i", str(empty),
        "-o", str(output_dir),
    )
    assert res.returncode != 0

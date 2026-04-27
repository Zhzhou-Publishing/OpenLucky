"""Tests for `cli.openlucky filmparam`."""
import json

import pytest


@pytest.mark.slow
def test_filmparam_non_raw_with_5_values(run_cli, random_none_raw_input, output_dir):
    out = output_dir / "out.png"
    res = run_cli(
        "filmparam",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "--param", "110,220,210,1.1,1.5",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0

    preset_file = random_none_raw_input.parent / ".preset.json"
    assert preset_file.exists()
    data = json.loads(preset_file.read_text(encoding="utf-8"))
    entry = data[random_none_raw_input.name]
    assert entry["preset"].startswith("custom_preset_")


@pytest.mark.slow
def test_filmparam_non_raw_with_8_values(run_cli, random_none_raw_input, output_dir):
    out = output_dir / "out.png"
    res = run_cli(
        "filmparam",
        "-i", str(random_none_raw_input),
        "-o", str(out),
        "--param", "110,220,210,1.1,1.5,1.2,1.3,1.4",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"

    preset_file = random_none_raw_input.parent / ".preset.json"
    data = json.loads(preset_file.read_text(encoding="utf-8"))
    entry = data[random_none_raw_input.name]
    assert entry["contrast_r"] == 1.2
    assert entry["contrast_g"] == 1.3
    assert entry["contrast_b"] == 1.4


@pytest.mark.slow
def test_filmparam_raw_with_5_values(run_cli, random_raw_input, output_dir):
    out = output_dir / "out.tiff"
    res = run_cli(
        "filmparam",
        "-i", str(random_raw_input),
        "-o", str(out),
        "--param", "110,220,210,1.1,1.5",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert out.exists() and out.stat().st_size > 0


def test_filmparam_missing_param(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "filmparam",
        "-i", str(fake),
        "-o", str(output_dir / "out.png"),
    )
    assert res.returncode != 0
    assert "param is required" in (res.stdout + res.stderr)


def test_filmparam_too_few_param_values(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "filmparam",
        "-i", str(fake),
        "-o", str(output_dir / "out.png"),
        "--param", "1,2,3",
    )
    assert res.returncode != 0
    assert "Invalid parameter format" in (res.stdout + res.stderr)


def test_filmparam_non_numeric_param(run_cli, output_dir, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n")
    res = run_cli(
        "filmparam",
        "-i", str(fake),
        "-o", str(output_dir / "out.png"),
        "--param", "abc,1,2,3,4",
    )
    assert res.returncode != 0
    assert "Failed to parse parameters" in (res.stdout + res.stderr)


def test_filmparam_input_missing(run_cli, output_dir, tmp_path):
    res = run_cli(
        "filmparam",
        "-i", str(tmp_path / "nope.png"),
        "-o", str(output_dir / "out.png"),
        "--param", "110,220,210,1.1,1.5",
    )
    assert res.returncode != 0
    assert "Input file does not exist" in (res.stdout + res.stderr)

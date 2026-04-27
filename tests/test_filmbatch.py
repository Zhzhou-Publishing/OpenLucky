"""Tests for `cli.openlucky filmbatch`."""
import pytest


@pytest.mark.slow
def test_filmbatch_non_raw_default_output(
    run_cli, none_raw_input_dir, sample_config
):
    res = run_cli(
        "filmbatch",
        "-i", str(none_raw_input_dir),
        "-c", str(sample_config),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"

    default_out = none_raw_input_dir / "output"
    assert default_out.is_dir()

    inputs = sorted(p.name for p in none_raw_input_dir.iterdir() if p.is_file())
    outputs = sorted(p.name for p in default_out.iterdir() if p.is_file())
    for name in inputs:
        assert name in outputs, f"missing output for input {name}"

    preset_file = none_raw_input_dir / ".preset.json"
    assert preset_file.exists()


@pytest.mark.slow
def test_filmbatch_non_raw_explicit_output(
    run_cli, none_raw_input_dir, sample_config, output_dir
):
    res = run_cli(
        "filmbatch",
        "-i", str(none_raw_input_dir),
        "-o", str(output_dir),
        "-c", str(sample_config),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"

    inputs = [p.name for p in none_raw_input_dir.iterdir() if p.is_file()]
    outputs = [p.name for p in output_dir.iterdir() if p.is_file()]
    for name in inputs:
        assert name in outputs

    # Default <input>/output was NOT created when --output was given.
    assert not (none_raw_input_dir / "output").exists()


@pytest.mark.slow
def test_filmbatch_raw_directory(run_cli, raw_input_dir, sample_config, output_dir):
    res = run_cli(
        "filmbatch",
        "-i", str(raw_input_dir),
        "-o", str(output_dir),
        "-c", str(sample_config),
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"

    raw_inputs = [p for p in raw_input_dir.iterdir() if p.is_file()]
    outputs = [p for p in output_dir.iterdir() if p.is_file()]
    assert len(outputs) == len(raw_inputs)


def test_filmbatch_input_dir_missing(run_cli, sample_config, output_dir, tmp_path):
    res = run_cli(
        "filmbatch",
        "-i", str(tmp_path / "no_such_dir"),
        "-o", str(output_dir),
        "-c", str(sample_config),
    )
    assert res.returncode != 0
    assert "does not exist" in (res.stdout + res.stderr)


def test_filmbatch_input_is_file(run_cli, sample_config, output_dir, tmp_path):
    fake = tmp_path / "not_a_dir.txt"
    fake.write_text("hi")
    res = run_cli(
        "filmbatch",
        "-i", str(fake),
        "-o", str(output_dir),
        "-c", str(sample_config),
    )
    assert res.returncode != 0
    assert "is not a directory" in (res.stdout + res.stderr)


def test_filmbatch_empty_input_dir(run_cli, sample_config, output_dir, tmp_path):
    empty = tmp_path / "empty_in"
    empty.mkdir()
    res = run_cli(
        "filmbatch",
        "-i", str(empty),
        "-o", str(output_dir),
        "-c", str(sample_config),
    )
    # Per current behavior: exit 0 with a warning and no output produced.
    assert res.returncode == 0
    assert "No supported image files" in (res.stdout + res.stderr)


@pytest.mark.slow
def test_filmbatch_unknown_preset(
    run_cli, none_raw_input_dir, sample_config, output_dir
):
    res = run_cli(
        "filmbatch",
        "-i", str(none_raw_input_dir),
        "-o", str(output_dir),
        "-c", str(sample_config),
        "-p", "no_such_preset",
    )
    assert res.returncode != 0
    assert "not found in config file" in (res.stdout + res.stderr)

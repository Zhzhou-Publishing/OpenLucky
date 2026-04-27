"""Tests for `cli.openlucky config read`."""
import json

import pytest


def test_config_read_yaml_default(run_cli, sample_config):
    res = run_cli("config", "read", "-c", str(sample_config))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "presets:" in res.stdout


def test_config_read_json_format(run_cli, sample_config):
    res = run_cli(
        "config", "read",
        "-c", str(sample_config),
        "-f", "json",
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    parsed = json.loads(res.stdout)
    assert "presets" in parsed
    assert "kodak_ultramax_400" in parsed["presets"]


def test_config_read_auto_search_in_cwd(run_cli, sample_config, tmp_path):
    cwd = tmp_path / "cwd_with_config"
    cwd.mkdir()
    (cwd / "config.yaml").write_bytes(sample_config.read_bytes())
    res = run_cli("config", "read", cwd=cwd)
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "presets:" in res.stdout


def test_config_read_explicit_path_missing(run_cli, tmp_path):
    res = run_cli("config", "read", "-c", str(tmp_path / "no_config.yaml"))
    assert res.returncode != 0
    assert "Configuration file does not exist" in (res.stdout + res.stderr)


def test_config_read_auto_search_fails(run_cli, tmp_path):
    empty_cwd = tmp_path / "empty_cwd"
    empty_cwd.mkdir()
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    res = run_cli(
        "config", "read",
        cwd=empty_cwd,
        env_overrides={
            "HOME": str(fake_home),
            "USERPROFILE": str(fake_home),
        },
    )
    assert res.returncode != 0
    assert "Configuration file not found" in (res.stdout + res.stderr)


def test_config_read_invalid_format(run_cli, sample_config):
    res = run_cli(
        "config", "read",
        "-c", str(sample_config),
        "-f", "xml",
    )
    assert res.returncode != 0

"""Shared fixtures for the OpenLucky CLI test suite.

Run all tests:        python -m pytest
Skip slow pipelines:  python -m pytest -m "not slow"

The `input_sample_raw/` and `input_sample_none_raw/` directories are populated
by the developer with real image samples. Tests that need a sample copy the
chosen file into a tmp dir first so side-effect files (e.g. `.preset.json`)
do not pollute the source directories. Tests skip cleanly when no suitable
sample is present.
"""
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

NONE_RAW_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
RAW_EXTS = {".arw", ".cr2", ".cr3", ".nef", ".dng", ".orf", ".raf"}
TIFF_EXTS = {".tif", ".tiff"}


def _list_files(directory: Path, exts: set[str]) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in exts
    )


def _safe_name(node_name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", node_name)[:120]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def raw_sample_dir(repo_root: Path) -> Path:
    return repo_root / "tests" / "input_sample_raw"


@pytest.fixture(scope="session")
def none_raw_sample_dir(repo_root: Path) -> Path:
    return repo_root / "tests" / "input_sample_none_raw"


@pytest.fixture(scope="session")
def sample_config(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures" / "config.yaml"


@pytest.fixture
def output_dir(request) -> Path:
    """Per-test output directory under tests/output/, recreated each run."""
    out = REPO_ROOT / "tests" / "output" / _safe_name(request.node.name)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture
def run_cli(repo_root: Path):
    """Invoke `python -m cli.openlucky <args>` and return CompletedProcess.

    stdout/stderr come back as decoded strings (utf-8, errors=replace) so tests
    can do plain substring assertions.
    """
    def _run(*args, timeout=120, env_overrides=None, cwd=None):
        env = os.environ.copy()
        # Ensure the cli package resolves regardless of cwd. Tests that pass
        # cwd= for auto-search behavior would otherwise lose `-m cli.openlucky`.
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{repo_root}{os.pathsep}{existing}" if existing else str(repo_root)
        )
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            [sys.executable, "-m", "cli.openlucky", *args],
            cwd=str(cwd) if cwd else str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
    return _run


def _pick_random_copy(source_dir: Path, exts: set[str], tmp_path: Path,
                     skip_msg: str) -> Path:
    files = _list_files(source_dir, exts)
    if not files:
        pytest.skip(skip_msg)
    chosen = random.choice(files)
    dest = tmp_path / chosen.name
    shutil.copy2(chosen, dest)
    return dest


@pytest.fixture
def random_raw_input(raw_sample_dir: Path, tmp_path: Path) -> Path:
    return _pick_random_copy(
        raw_sample_dir, RAW_EXTS, tmp_path,
        f"Place RAW samples in {raw_sample_dir.relative_to(REPO_ROOT)}/ to enable",
    )


@pytest.fixture
def random_none_raw_input(none_raw_sample_dir: Path, tmp_path: Path) -> Path:
    return _pick_random_copy(
        none_raw_sample_dir, NONE_RAW_EXTS, tmp_path,
        f"Place non-RAW samples in {none_raw_sample_dir.relative_to(REPO_ROOT)}/ to enable",
    )


@pytest.fixture
def random_tiff_input(none_raw_sample_dir: Path, tmp_path: Path) -> Path:
    return _pick_random_copy(
        none_raw_sample_dir, TIFF_EXTS, tmp_path,
        f"Place a .tif/.tiff sample in {none_raw_sample_dir.relative_to(REPO_ROOT)}/ to enable",
    )


def _copy_dir_contents(source_dir: Path, exts: set[str], tmp_path: Path,
                      label: str, skip_msg: str) -> Path:
    files = _list_files(source_dir, exts)
    if not files:
        pytest.skip(skip_msg)
    dest = tmp_path / label
    dest.mkdir()
    for f in files:
        shutil.copy2(f, dest / f.name)
    return dest


@pytest.fixture
def raw_input_dir(raw_sample_dir: Path, tmp_path: Path) -> Path:
    return _copy_dir_contents(
        raw_sample_dir, RAW_EXTS, tmp_path, "raw_inputs",
        f"Place RAW samples in {raw_sample_dir.relative_to(REPO_ROOT)}/ to enable",
    )


@pytest.fixture
def none_raw_input_dir(none_raw_sample_dir: Path, tmp_path: Path) -> Path:
    return _copy_dir_contents(
        none_raw_sample_dir, NONE_RAW_EXTS, tmp_path, "none_raw_inputs",
        f"Place non-RAW samples in {none_raw_sample_dir.relative_to(REPO_ROOT)}/ to enable",
    )

"""--help smoke tests for every (sub)command. Argparse-only; no pipelines."""
import pytest


SUBCOMMAND_PATHS = [
    [],
    ["film"],
    ["filmbatch"],
    ["filmparam"],
    ["filmparambatch"],
    ["raw2tiff"],
    ["tiff2jpeg"],
    ["config"],
    ["config", "read"],
    ["tool"],
    ["tool", "resize"],
    ["tool", "reshape"],
    ["curve"],
    ["curve", "levels"],
]


@pytest.mark.parametrize(
    "path", SUBCOMMAND_PATHS,
    ids=[" ".join(p) or "(root)" for p in SUBCOMMAND_PATHS],
)
def test_help_exits_zero(run_cli, path):
    res = run_cli(*path, "--help")
    assert res.returncode == 0, (
        f"`{' '.join(path)} --help` failed with exit {res.returncode}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    assert res.stdout, f"`{' '.join(path)} --help` produced no stdout"


def test_unknown_subcommand_exits_nonzero(run_cli):
    res = run_cli("does-not-exist")
    assert res.returncode != 0

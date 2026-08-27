"""#1920: corpus-derived run artifacts stay ignored outside the repository root."""

from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", path],
        cwd=REPO_ROOT,
        check=False,
    )
    return result.returncode == 0


def test_positive_control_proves_git_check_ignore_is_live():
    assert _is_ignored("tmp/positive-control.txt")


@pytest.mark.parametrize(
    "path",
    [
        "scratchpad/toolchain.jar",
        "scratchpad/trace_arg_0.json",
        "nested/output/trace_fallacy_0.json",
        "another/worktree/reanalysis_arg_0.json",
    ],
)
def test_private_run_artifacts_are_ignored_in_nested_directories(path):
    assert _is_ignored(path), f"privacy artifact unexpectedly visible to git: {path}"


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_trace_arg_parser.py",
        "tests/test_trace_fallacy_renderer.py",
        "tests/test_reanalysis_arg_contract.py",
    ],
)
def test_neighboring_test_names_remain_visible(path):
    assert not _is_ignored(
        path
    ), f"legitimate neighboring name was over-ignored: {path}"

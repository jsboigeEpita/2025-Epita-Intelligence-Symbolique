"""Witness for #3735 — what the cleanup untracks: git's answer, from the root, narrowed by the decision.

The defect: ``cleanup_repository.py`` built the string ``git rm --cached *.jar``
and ran it through a shell, without a directory. Under ``cmd.exe`` the glob is not
expanded, git reads ``*.jar`` as a pathspec, and a pathspec ``*`` crosses ``/``:
from the repository root the call reached **32 tracked jars**, 31 of which no
ignore rule of the repository declares ignorable — 30 of them a student project's
libraries.

The repair, measured here against a **temporary repository** (the script is copied
into it at its real relative path and run as a subprocess):

- git runs as a list of arguments from the repository root, so the reach depends
  on neither the shell nor the caller's directory;
- ``--dry-run`` lists the reach path by path, and what it would untrack;
- the jar call keeps tracked every reached file the repository's own ignore rules
  do not ignore.

Every witness asserts a positive observation: the temporary repository holds a
tracked jar the call must untrack, so a run that reached nothing would fail.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.scripts.test_cleanup_roots_3726 import (
    _env,
    _git,
    _install,
    _stub_package,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = Path("scripts") / "maintenance" / "cleanup" / "cleanup_repository.py"

#: the repository's own rule (its ``.gitignore``: ``libs/*.jar``) — a jar is an
#: ignored artifact under the root ``libs/`` only
REPOSITORY_RULE = "libs/*.jar"
#: tracked, and ignored by the rule: the artifact the call is for
UNTRACKED_JAR = "libs/a.jar"
#: tracked, and ignored by no rule of the repository: the call keeps it, and names it
KEPT_JAR = "other/b.jar"
KEPT_WHY = "suivi, et aucune règle d'exclusion du dépôt ne l'ignore"
#: tracked, ignored by ``*.py[cod]``: the other calls' class, at depth
CACHED_BYTECODE = "deep/pkg/__pycache__/module.cpython-310.pyc"

#: the form the repair replaces: the command as a string, handed to a shell
SHELL_GLOB_BODY = """
    command = f"git rm --cached {pattern}"
    if dry_run:
        print(f"[dry-run] {command}")
        return True
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.returncode == 0
"""


def _tracked(repo: Path) -> set[str]:
    return set(_git(repo, "ls-files").stdout.split())


def _lines(output: str, *needles: str) -> list[str]:
    """The lines of ``output`` carrying every needle."""
    return [line for line in output.splitlines() if all(n in line for n in needles)]


def _repository(scratch: Path, rule: str, *tracked_files: str) -> Path:
    """A committed temporary repository: both scripts at their real path, ``rule``, tracked files."""
    root = _install(scratch / "repo")
    _stub_package(root)
    (root / ".gitignore").write_bytes(f"{rule}\n".encode())
    for relative in tracked_files:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"payload")
    _git(root, "init", "-q")
    _git(root, "add", "-f", "--all")
    _git(root, "commit", "-qm", "witness")
    return root


def _run(
    root: Path,
    *args: str,
    cwd: Path | None = None,
    env_extra: dict[str, str] | None = None,
) -> "subprocess.CompletedProcess[str]":
    """The copied script, as a subprocess, from ``cwd`` (the repository root by default)."""
    env = _env(root)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(root / SCRIPT_PATH), *args],
        cwd=str(cwd or root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = _repository(
        tmp_path,
        "__pycache__/\n*.py[cod]\n" + REPOSITORY_RULE,
        UNTRACKED_JAR,
        KEPT_JAR,
        CACHED_BYTECODE,
    )
    assert {UNTRACKED_JAR, KEPT_JAR, CACHED_BYTECODE} <= _tracked(
        root
    ), "the witness starts from tracked files"
    return root


# --------------------------------------------------------------------------- #
# Asks 2 and 3 — git as a list from the root, and a dry run that shows the reach
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("caller", ["the root", "a subdirectory"])
def test_the_dry_run_lists_the_reach_and_what_it_would_untrack(
    repo: Path, caller: str
) -> None:
    cwd = repo if caller == "the root" else repo / "scripts" / "maintenance"
    before = _tracked(repo)

    result = _run(repo, "--dry-run", cwd=cwd)

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert _lines(
        out, "'*.jar' atteint 2 fichier(s) suivi(s) : 1 à retirer, 1 à conserver"
    ), out
    assert _lines(out, "[dry-run] serait retiré du suivi :", UNTRACKED_JAR), out
    assert _lines(out, "[dry-run] serait conservé", KEPT_WHY, KEPT_JAR), out
    assert _lines(out, "[dry-run] serait retiré du suivi :", CACHED_BYTECODE), out
    assert _tracked(repo) == before, "a dry run changes no index"


@pytest.mark.parametrize("caller", ["the root", "a subdirectory"])
def test_the_run_untracks_the_ignored_jar_and_keeps_the_other(
    repo: Path, caller: str
) -> None:
    cwd = repo if caller == "the root" else repo / "scripts" / "maintenance"

    result = _run(repo, cwd=cwd)

    assert result.returncode == 0, result.stderr
    assert _lines(result.stdout, "Retiré du suivi :", UNTRACKED_JAR), result.stdout
    assert _lines(result.stdout, "conservé", KEPT_WHY, KEPT_JAR), result.stdout
    tracked = _tracked(repo)
    assert (
        UNTRACKED_JAR not in tracked
    ), "the artifact the rule ignores leaves the index"
    assert CACHED_BYTECODE not in tracked, "the bytecode leaves it too, at depth"
    assert KEPT_JAR in tracked, "the jar no rule ignores stays tracked"
    for relative in (UNTRACKED_JAR, KEPT_JAR, CACHED_BYTECODE):
        assert (repo / relative).is_file(), "nothing is deleted from the disk"


def _untracking_functions(source: str) -> dict[str, ast.FunctionDef]:
    """``remove_files_from_git_tracking`` and, transitively, what it calls in the module."""
    functions = {
        node.name: node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
    }
    reached: dict[str, ast.FunctionDef] = {}
    pending = ["remove_files_from_git_tracking"]
    while pending:
        name = pending.pop()
        if name in reached or name not in functions:
            continue
        reached[name] = functions[name]
        pending.extend(
            node.func.id
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        )
    return reached


def _subprocess_calls(functions: dict[str, ast.FunctionDef]) -> list[ast.Call]:
    return [
        node
        for function in functions.values()
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]


def test_the_untracking_hands_git_a_list_from_the_root() -> None:
    source = (REPO_ROOT / SCRIPT_PATH).read_text(encoding="utf-8")
    calls = _subprocess_calls(_untracking_functions(source))

    assert calls, "the untracking runs git: a guard that read no call proves nothing"
    for call in calls:
        assert call.func.attr == "run", ast.unparse(call)
        assert isinstance(
            call.args[0], ast.List
        ), "a shell reads a string; git reads a list"
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        assert "shell" not in keywords, ast.unparse(call)
        cwd = keywords.get("cwd")
        assert isinstance(cwd, ast.Name) and cwd.id == "PROJECT_ROOT", ast.unparse(call)


# --------------------------------------------------------------------------- #
# Ask 4 — the mutation control: the shell glob put back
# --------------------------------------------------------------------------- #


def _mutated(source: str) -> str:
    """The script with the shell glob put back in ``remove_files_from_git_tracking``."""
    node = next(
        item
        for item in ast.parse(source).body
        if isinstance(item, ast.FunctionDef)
        and item.name == "remove_files_from_git_tracking"
    )
    lines = source.splitlines(keepends=True)
    signature = f"def {node.name}({ast.unparse(node.args)}):\n"
    return "".join(
        [
            *lines[: node.lineno - 1],
            signature,
            SHELL_GLOB_BODY,
            *lines[node.end_lineno :],
        ]
    )


def test_the_shell_glob_form_is_seen_by_the_witness(repo: Path) -> None:
    """The mutation control the issue asks for, re-measured by every run.

    The shell glob is put back in the copy the temporary repository holds. The
    two observations the witnesses above make on the repair are then false: the
    dry run names no path, and the default run untracks the jar the decision keeps.
    """
    target = repo / SCRIPT_PATH
    target.write_bytes(_mutated(target.read_text(encoding="utf-8")).encode("utf-8"))

    dry = _run(repo, "--dry-run")

    assert dry.returncode == 0, dry.stderr
    assert (
        "[dry-run] git rm --cached *.jar" in dry.stdout
    ), "the old dry run printed the command"
    assert UNTRACKED_JAR not in dry.stdout, "and not the reach"
    assert KEPT_JAR not in dry.stdout

    result = _run(repo)

    assert result.returncode == 0, result.stderr
    assert KEPT_JAR not in _tracked(
        repo
    ), "the shell glob untracks the jar the decision keeps"
    assert UNTRACKED_JAR not in _tracked(repo)


# --------------------------------------------------------------------------- #
# The decision — read in the repository's rules, exactly
# --------------------------------------------------------------------------- #


def test_a_rule_of_the_machine_does_not_decide(repo: Path, tmp_path: Path) -> None:
    """A global excludes file belongs to a machine: it must not widen the decision."""
    excludes = tmp_path / "machine-excludes"
    excludes.write_bytes(b"*.jar\n")
    config = tmp_path / "machine-gitconfig"
    config.write_bytes(f"[core]\n\texcludesFile = {excludes.as_posix()}\n".encode())
    machine = {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"}
    plain = dict(os.environ, **machine)
    # `--no-index` : sans lui, check-ignore ne rend jamais un fichier suivi.
    control = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "--no-index", "-q", "--", KEPT_JAR],
        env=plain,
    )
    assert control.returncode == 0, "control: on that machine, git ignores the kept jar"

    result = _run(repo, env_extra=machine)

    assert result.returncode == 0, result.stderr
    assert _lines(result.stdout, "conservé", KEPT_WHY, KEPT_JAR), result.stdout
    tracked = _tracked(repo)
    assert (
        KEPT_JAR in tracked
    ), "a machine's rule must not untrack a jar no rule of the repository ignores"
    assert UNTRACKED_JAR not in tracked


def test_a_decided_path_is_taken_by_its_name_not_as_a_glob(tmp_path: Path) -> None:
    """``[1]`` is a glob to git: a decided path must not reach its lookalike."""
    bracketed, lookalike = "libs/c[1].jar", "libs/c1.jar"
    root = _repository(tmp_path, "libs/c\\[1\\].jar", bracketed, lookalike)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert _lines(
        result.stdout,
        "'*.jar' atteint 2 fichier(s) suivi(s) : 1 à retirer, 1 à conserver",
    ), result.stdout
    tracked = _tracked(root)
    assert bracketed not in tracked
    assert lookalike in tracked, "taken as a glob, c[1].jar reaches c1.jar too"

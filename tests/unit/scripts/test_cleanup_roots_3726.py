"""Witness for #3726 — the two cleanup scripts must compute the repository root.

The defect: ``cleanup_project.py`` and ``cleanup_repository.py`` live in
``scripts/maintenance/cleanup/`` and computed their root as
``Path(__file__).resolve().parent.parent.parent``, which is ``<repo>/scripts`` —
one level short. ``cleanup_project.update_gitignore()`` therefore appended to
``scripts/.gitignore`` (untracked) instead of the repository's, and
``cleanup_repository`` aimed its ``.env.example`` model at
``scripts/argumentation_analysis/.env.example``, a path git ignores.

The repair is measured here against a **temporary repository**: the two scripts are
copied into it at their real relative path and run as subprocesses, so what is
exercised is the root computation itself, not a helper imported in-process.

Every witness below asserts a positive observation before trusting it: the "nothing
outside the target" claim is backed by a planted file that the script must reach
(surviving under the old root), and a guard that read nothing would fail on that.
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CLEANUP_DIR = REPO_ROOT / "scripts" / "maintenance" / "cleanup"
SCRIPTS = ("cleanup_project.py", "cleanup_repository.py")

#: marker written by cleanup_project.update_gitignore()
APPEND_HEADER = "# Ajouté par le script de nettoyage"


def _git(root: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    """Run git inside the temporary repository, hermetic against the seat's config."""
    return subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "core.autocrlf=false",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=witness",
            "-c",
            "user.email=witness@example.invalid",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def _env(root: Path) -> "dict[str, str]":
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env["PYTHONPATH"] = str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _stub_package(root: Path) -> None:
    """``cleanup_repository`` imports ``argumentation_analysis.core.environment``."""
    package = root / "argumentation_analysis"
    (package / "core").mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_bytes(b"")
    (package / "core" / "__init__.py").write_bytes(b"")
    (package / "core" / "environment.py").write_bytes(b"")


def _install(tmp_root: Path) -> Path:
    """Copy both scripts into ``tmp_root`` at their real relative path; return the root."""
    target_dir = tmp_root / "scripts" / "maintenance" / "cleanup"
    target_dir.mkdir(parents=True)
    for name in SCRIPTS:
        shutil.copy2(CLEANUP_DIR / name, target_dir / name)
    return tmp_root


def _run(root: Path, script: str, *args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "maintenance" / "cleanup" / script),
            *args,
        ],
        cwd=str(root),
        env=_env(root),
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A temporary repository holding both scripts, a tracked-ish .gitignore, no upstream."""
    root = _install(tmp_path / "repo")
    (root / ".gitignore").write_bytes(b"existing-line\n")
    (root / "argumentation_analysis").mkdir()
    _git(root, "init", "-q")
    return root


# --------------------------------------------------------------------------- #
# cleanup_project.py — the .gitignore of the repository, not of scripts/
# --------------------------------------------------------------------------- #


def test_the_dry_run_writes_nothing_and_announces_the_repository_root(
    repo: Path,
) -> None:
    stray = repo / "stray.pyc"
    stray.write_bytes(b"")
    before = (repo / ".gitignore").read_bytes()

    result = _run(repo, "cleanup_project.py", "--dry-run")

    assert result.returncode == 0, result.stderr
    assert str(repo) in result.stdout, "the run must name the root it resolved"
    assert "[dry-run]" in result.stdout
    assert (repo / ".gitignore").read_bytes() == before
    assert not (repo / "scripts" / ".gitignore").exists()
    assert stray.exists(), "a dry run deletes nothing"
    assert not (repo / "argumentation_analysis" / "data").exists()


def test_the_run_writes_the_gitignore_the_census_names(repo: Path) -> None:
    stray = repo / "stray.pyc"
    stray.write_bytes(b"")

    result = _run(repo, "cleanup_project.py")

    assert result.returncode == 0, result.stderr
    gitignore = repo / ".gitignore"
    raw = gitignore.read_bytes()
    text = gitignore.read_text(encoding="utf-8")
    assert APPEND_HEADER in text
    assert "\n__pycache__/\n" in text
    assert text.startswith("existing-line\n"), "the existing content is preserved"
    assert b"\r\n" not in raw, "the appended lines are LF on every seat (#3723)"
    assert not (
        repo / "scripts" / ".gitignore"
    ).exists(), "the old root aimed the append at scripts/.gitignore"
    assert not stray.exists(), "the root is the repository: its temporaries are reached"
    assert (repo / "argumentation_analysis" / "data" / ".gitkeep").exists()


def test_the_option_aims_another_gitignore(repo: Path) -> None:
    result = _run(repo, "cleanup_project.py", "--gitignore", "custom/rules.gitignore")

    assert result.returncode == 0, result.stderr
    elsewhere = repo / "custom" / "rules.gitignore"
    assert elsewhere.is_file()
    assert APPEND_HEADER in elsewhere.read_text(encoding="utf-8")
    assert (repo / ".gitignore").read_bytes() == b"existing-line\n"


def test_outside_a_repository_it_refuses_instead_of_aiming_short(
    tmp_path: Path,
) -> None:
    loose = _install(tmp_path / "loose")
    _stub_package(loose)

    result = _run(loose, "cleanup_project.py", "--dry-run")

    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert "racine du dépôt introuvable" in result.stdout
    assert not (loose / ".gitignore").exists()
    assert not (loose / "scripts" / ".gitignore").exists()


# --------------------------------------------------------------------------- #
# cleanup_repository.py — the .env.example of the repository, and its dry run
# --------------------------------------------------------------------------- #


def test_the_repository_dry_run_writes_nothing(repo: Path) -> None:
    _stub_package(repo)
    (repo / "argumentation_analysis" / ".env").write_bytes(b"KEY=1\n")

    result = _run(repo, "cleanup_repository.py", "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "[dry-run]" in result.stdout
    assert not (repo / "argumentation_analysis" / ".env.example").exists()
    assert not (repo / "scripts" / "argumentation_analysis").exists()


def test_the_repository_run_writes_its_model_at_the_repository_root(repo: Path) -> None:
    _stub_package(repo)
    (repo / "argumentation_analysis" / ".env").write_bytes(b"KEY=1\n")
    stray = repo / "stray.pyc"
    stray.write_bytes(b"")
    _git(repo, "add", "-f", "stray.pyc")
    _git(repo, "commit", "-qm", "witness")
    assert "stray.pyc" in _git(repo, "ls-files").stdout

    result = _run(repo, "cleanup_repository.py")

    assert result.returncode == 0, result.stderr
    model = repo / "argumentation_analysis" / ".env.example"
    assert (
        model.is_file()
    ), "the old root wrote scripts/argumentation_analysis/.env.example"
    payload = model.read_bytes()
    assert b"\r\n" not in payload, "the model is LF on every seat (#3723)"
    assert "OPENAI_CHAT_MODEL_ID" in payload.decode("utf-8"), "the model is UTF-8"
    assert not (repo / "scripts" / "argumentation_analysis").exists()
    assert (
        "stray.pyc" not in _git(repo, "ls-files").stdout
    ), "the index is reachable from the repository root"


# --------------------------------------------------------------------------- #
# The root helper itself
# --------------------------------------------------------------------------- #


def _function_source(source: str, name: str) -> str:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"{name} not found")


def test_the_two_copies_of_the_root_helper_do_not_drift() -> None:
    sources = {
        name: (CLEANUP_DIR / name).read_text(encoding="utf-8") for name in SCRIPTS
    }
    helpers = {
        name: _function_source(text, "find_project_root")
        for name, text in sources.items()
    }
    assert (
        helpers[SCRIPTS[0]] == helpers[SCRIPTS[1]]
    ), "both scripts must resolve the root the same way"

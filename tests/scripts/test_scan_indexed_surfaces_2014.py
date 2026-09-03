"""Guard for the indexed-surface privacy scanner (#2014).

The repository's person-name detector was only ever wired to ``tests/**``.
Commit messages and PR/issue bodies — the most durable GitHub-indexed surfaces
the project has — had no guard, while ``CLAUDE.md`` covers them explicitly.
``scripts/security/scan_indexed_surfaces.py`` closes that gap.

The planted token is **derived from the shared patterns at run time**, never
written here. That keeps the spelling in the one module that carries it by
design, and keeps this file green under the ``tests/**`` sweep guard.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "security" / "scan_indexed_surfaces.py"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("_scan_indexed_surfaces", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_scan_indexed_surfaces"] = module
    spec.loader.exec_module(module)
    return module


scanner = _load_scanner()


def _alphabetic_core() -> str:
    """A purely alphabetic pattern core, so the planted token is a clean identifier."""
    for pattern in scanner.PERSON_PATTERNS:
        core = pattern.replace(r"\b", "")
        if re.fullmatch(r"[A-Za-z]+", core):
            return core
    pytest.skip("no purely alphabetic pattern core available to plant")


def test_identifier_shaped_name_is_caught(tmp_path):
    """Born-red: the form the shipped ``\b`` patterns are blind to must be caught."""
    body = tmp_path / "body.md"
    body.write_text(
        f"- migrated the `{_alphabetic_core().lower()}_only=` keyword\n",
        encoding="utf-8",
    )
    assert scanner.main(["--text-file", str(body)]) == 1


def test_the_shipped_word_boundary_patterns_would_miss_it():
    """The control that makes the test above non-vacuous.

    If the shipped patterns already caught the identifier form, the scanner would
    be redundant and its green would prove nothing. ``\b`` is a *word* boundary
    and ``_`` is a word character, so it cannot match ``core_only`` (#2012).
    """
    planted = f"the {_alphabetic_core().lower()}_only keyword"
    shipped = [re.compile(p, re.IGNORECASE) for p in scanner.PERSON_PATTERNS]
    assert sum(len(rx.findall(planted)) for rx in shipped) == 0
    assert scanner.scan_text(planted) == 1


def test_prose_occurrence_is_caught(tmp_path):
    """The easy half must still be caught — the letter boundary is a superset."""
    body = tmp_path / "body.md"
    body.write_text(f"a speech by {_alphabetic_core()} was added\n", encoding="utf-8")
    assert scanner.main(["--text-file", str(body)]) == 1


def test_clean_prose_passes(tmp_path):
    """Negative control: an opaque body must not redden."""
    body = tmp_path / "body.md"
    body.write_text(
        "- migrated corpus_A and Source_3; locations are file + line only\n",
        encoding="utf-8",
    )
    assert scanner.main(["--text-file", str(body)]) == 0


def test_substring_inside_an_ordinary_word_is_not_flagged():
    """Anti-pendulum: dropping the boundary outright produced 179 false positives."""
    core = _alphabetic_core().lower()
    assert scanner.scan_text(f"x{core}x and pre{core}ing") == 0


def test_empty_commit_range_scans_nothing_and_says_so():
    """The vacuous case, named: HEAD..HEAD has no commits, so scanned is 0.

    Stated explicitly because the previous version asserted ``== []`` on this
    range, which is true no matter whether the git path works at all.
    """
    scan = scanner.scan_commits("HEAD..HEAD")
    assert scan.findings == []
    assert scan.scanned == 0


def test_real_commit_range_actually_reads_messages(capsys):
    """Non-vacuity floor: a range with commits must report a non-zero census.

    Without this, a CI runner whose range comes back empty would print "clean"
    forever, indistinguishably from a scan that read something.
    """
    scan = scanner.scan_commits("HEAD~3..HEAD")
    assert scan.scanned == 3
    assert scan.malformed == 0
    assert scanner.main(["--commits", "HEAD~3..HEAD"]) == 0
    out = capsys.readouterr().out
    assert "scanned 3 commit message(s)" in out
    assert "clean" in out


def test_planted_name_in_a_commit_message_reddens_the_commit_path(
    tmp_path, monkeypatch, capsys
):
    """Born-red on the path CI invokes: the gate must be able to fail.

    The text path is exercised above; this one drives ``git log`` itself, which
    is what ``--commits origin/main..HEAD`` runs in the workflow.
    """
    import subprocess

    repo = tmp_path / "r"
    repo.mkdir()
    monkeypatch.chdir(repo)
    run = lambda *a: subprocess.run(a, check=True, capture_output=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    (repo / "f").write_text("x")
    run("git", "add", "f")
    run("git", "commit", "-q", "-m", "chore: clean subject with corpus_A only")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    (repo / "f").write_text("y")
    run("git", "add", "f")
    run(
        "git",
        "commit",
        "-q",
        "-m",
        f"chore: names {_alphabetic_core().lower()}_only here",
    )

    scan = scanner.scan_commits(f"{base}..HEAD")
    assert scan.scanned == 1, "the mutation must have applied before the verdict counts"
    assert len(scan.findings) == 1
    _sha, hits, in_subject, identifier = scan.findings[0]
    assert hits == 1 and in_subject and identifier
    assert scanner.main(["--commits", f"{base}..HEAD"]) == 1
    assert "LEAK" in capsys.readouterr().out

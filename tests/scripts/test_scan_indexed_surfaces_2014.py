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


def test_commit_range_scan_reports_and_stays_quiet_on_a_clean_range(capsys):
    """Smoke the git path on a range with no leak; empty range must be clean."""
    assert scanner.scan_commits("HEAD..HEAD") == []
    assert scanner.main(["--commits", "HEAD..HEAD"]) == 0
    assert "clean" in capsys.readouterr().out

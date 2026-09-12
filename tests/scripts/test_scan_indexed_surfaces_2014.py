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
    for pattern in scanner.DETECTOR_PATTERNS:
        if re.fullmatch(r"[A-Za-z]+", pattern):
            return pattern
    pytest.skip("no purely alphabetic pattern core available to plant")


def _source_pattern() -> str:
    """A corpus-identifier pattern (#2119), derived at run time like the rest.

    Never written here: the spelling lives in the one module that carries it
    by design, keeping this file green under the tests/** sweep guard.
    """
    patterns = [
        p
        for p in scanner.DETECTOR_PATTERNS
        if any(c.isdigit() for c in p) and "_" not in p
    ]
    assert patterns, "SOURCE_PATTERNS is empty: the corpus guard is vacuous"
    return patterns[0]


def _source_identifier_pattern() -> str:
    """The corpus identifier that is itself identifier-shaped (underscores)."""
    patterns = [
        p for p in scanner.DETECTOR_PATTERNS if "_" in p and any(c.isdigit() for c in p)
    ]
    assert patterns, "no underscore-shaped corpus identifier pattern loaded"
    return patterns[0]


class TestCorpusSourcePatterns2119:
    """#2119 — dataset corpus identifiers join person names in the gate.

    The gate used to read PERSON_PATTERNS only: a corpus identifier in a
    commit message or PR body passed clean. These tests plant tokens derived
    from the shared patterns at run time — if SOURCE_PATTERNS is emptied or
    the scanner stops loading it, the planted prose contains nothing the
    detectors know and the assertions fail (the guard cannot pass vacuously).
    """

    def test_corpus_identifier_in_prose_reddens(self, tmp_path):
        body = tmp_path / "body.md"
        body.write_text(
            f"benchmark row for {_source_pattern()} added\n", encoding="utf-8"
        )
        assert scanner.main(["--text-file", str(body)]) == 1

    def test_corpus_identifier_shaped_form_reddens(self, tmp_path):
        body = tmp_path / "body.md"
        body.write_text(
            f"- renamed `{_source_identifier_pattern()}_extract` fixture\n",
            encoding="utf-8",
        )
        assert scanner.main(["--text-file", str(body)]) == 1

    def test_scanner_detector_count_includes_corpus_identifiers(self):
        """Wiring guard: the loaded list is person + corpus, not person alone."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_leak_patterns_2119",
            REPO_ROOT / "argumentation_analysis" / "evaluation" / "leak_patterns.py",
        )
        leak = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(leak)
        assert len(scanner.DETECTOR_PATTERNS) == len(leak.PERSON_PATTERNS) + len(
            leak.SOURCE_PATTERNS
        )
        assert len(leak.SOURCE_PATTERNS) >= 2


def test_identifier_shaped_name_is_caught(tmp_path):
    """Born-red: the identifier form a word boundary is blind to must be caught."""
    body = tmp_path / "body.md"
    body.write_text(
        f"- migrated the `{_alphabetic_core().lower()}_only=` keyword\n",
        encoding="utf-8",
    )
    assert scanner.main(["--text-file", str(body)]) == 1


def test_scanner_consumes_the_shared_frontier_not_a_local_copy(monkeypatch):
    """The frontier must have one *source*, not merely one spelling.

    #2012 moved it into ``leak_patterns.letter_boundary``, and two copies of one
    rule is the drift that made the identifier form invisible to begin with.
    Comparing the compiled strings is not enough: a locally re-derived frontier
    produces byte-identical output and would slip through. So the shared helper
    is redirected, and the detectors must follow it — which they can only do by
    actually calling it.
    """
    monkeypatch.setattr(scanner, "letter_boundary", lambda core: f"__{core}__")
    assert [rx.pattern for rx in scanner.compile_detectors()] == [
        f"__{p}__" for p in scanner.DETECTOR_PATTERNS
    ]


def test_a_word_boundary_would_still_miss_the_identifier_form():
    """Why the frontier exists at all — the property #2012 fixed, pinned here.

    Reverting ``letter_boundary`` to a word boundary must redden this file too,
    not only the shared module's own guard: this scanner is the consumer that
    carries that rule into the commit-message gate.
    """
    core = _alphabetic_core().lower()
    planted = f"the {core}_only keyword"
    word_boundary = re.compile(rf"\b{core}\b", re.IGNORECASE)
    assert word_boundary.search(planted) is None
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
    """Non-vacuity floor, checked against an independent instrument.

    A runner whose range comes back empty would print "clean" forever,
    indistinguishable from a scan that read something. So the census must be
    non-zero *and* agree with ``git rev-list --count``: the two instruments
    disagreeing is precisely how the silent-drop of an unparsed record would
    show up.

    The count is asked for, never assumed. An earlier version hard-coded 3 for
    ``HEAD~3..HEAD``; CI checks out the pull request's *merge* commit, where
    that range spans six commits, so the assertion measured git topology rather
    than the scanner.
    """
    import subprocess

    rng = "HEAD~3..HEAD"
    expected = int(
        subprocess.run(
            ["git", "rev-list", "--count", rng], capture_output=True, text=True
        ).stdout.strip()
    )
    assert expected >= 1, "an empty range makes this control vacuous"

    scan = scanner.scan_commits(rng)
    assert scan.scanned == expected
    assert scan.malformed == 0

    scanner.main(["--commits", rng])
    assert f"scanned {expected} commit message(s)" in capsys.readouterr().out


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

#!/usr/bin/env python
"""Privacy scan for GitHub-indexed surfaces (commit messages, PR/issue bodies).

The repository already carries a person-name detector, but it is only wired to
``tests/**`` (the sweep guard) and to synthesis prose (the runtime verifier).
The three most durable indexed surfaces — commit messages on ``main``, PR bodies
and issue bodies — have no guard at all, even though the Dataset Privacy
Discipline in ``CLAUDE.md`` covers them explicitly.

This script closes that gap for anything you are about to publish.

Boundary semantics
------------------
The shared patterns bake ``\b`` into each literal. ``\b`` is a *word* boundary
and ``_`` is a word character, so ``\bName\b`` cannot match ``name_only`` —
precisely the shape a name takes when it enters code (see #2012). This script
therefore re-applies a **letter** boundary, ``(?<![A-Za-z])…(?![A-Za-z])``,
which keeps whole-word behaviour in prose *and* fires on identifier forms.
It does not modify the shared module; #2012 tracks fixing it at the source.

Output discipline
-----------------
``leak_patterns`` states that only hit *counts* may be written to committed
artifacts, never matched context. This script honours that: it reports the
surface, the location and the count, and never the matched text.

Usage
-----
    # commit messages a branch adds on top of a base
    python scripts/security/scan_indexed_surfaces.py --commits origin/main..HEAD

    # a PR body, an issue body, any prose you are about to publish
    python scripts/security/scan_indexed_surfaces.py --text-file pr_body.md
    gh pr view N --json body --jq .body | python scripts/security/scan_indexed_surfaces.py --stdin

Exit code 1 on any hit, 0 when clean.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
from typing import NamedTuple
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PATTERNS_MODULE = (
    _REPO_ROOT / "argumentation_analysis" / "evaluation" / "leak_patterns.py"
)


def _load_patterns() -> tuple[list, object]:
    """Load the shared vocabulary by path.

    Importing ``argumentation_analysis.evaluation.leak_patterns`` normally would
    execute the package ``__init__`` and pull in the LLM stack. ``leak_patterns``
    declares itself import-effect-free precisely so it can be consumed cheaply;
    loading it by path honours that and keeps this security script side-effect
    free, fast, and usable from a hook.
    """
    spec = importlib.util.spec_from_file_location("_leak_patterns", _PATTERNS_MODULE)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load shared patterns from {_PATTERNS_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.PERSON_PATTERNS), module.letter_boundary


PERSON_PATTERNS, letter_boundary = _load_patterns()


def compile_detectors() -> list[re.Pattern[str]]:
    """Compile the shared vocabulary through the shared frontier.

    The frontier is NOT re-derived here. #2012 moved it into
    ``leak_patterns.letter_boundary``; keeping a second spelling of the same
    rule in this file is exactly the drift that made the identifier form
    invisible in the first place.
    """
    return [
        re.compile(letter_boundary(pattern), re.IGNORECASE)
        for pattern in PERSON_PATTERNS
    ]


def scan_text(text: str, detectors: list[re.Pattern[str]] | None = None) -> int:
    """Total number of hits in ``text``. Never returns the matched substrings."""
    detectors = detectors or compile_detectors()
    return sum(len(rx.findall(text)) for rx in detectors)


def _identifier_shaped(text: str) -> bool:
    """True when a hit is adjacent to ``_`` — the form a word boundary misses."""
    return any(
        re.search(rf"(?<![A-Za-z]){core}_|_{core}(?![A-Za-z])", text, re.IGNORECASE)
        for core in PERSON_PATTERNS
    )


class CommitScan(NamedTuple):
    """A commit-range scan plus the census proving it was not vacuous."""

    findings: list[tuple[str, int, bool, bool]]
    scanned: int
    malformed: int


def scan_commits(rev_range: str) -> CommitScan:
    """Scan commit messages in ``rev_range``. Returns (sha, hits, in_subject, identifier)."""
    sep = "\x1e"
    proc = subprocess.run(
        ["git", "log", f"--format=%H%x1f%s%x1f%b{sep}", rev_range],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    detectors = compile_detectors()
    findings = []
    scanned = 0
    malformed = 0
    for record in proc.stdout.split(sep):
        if not record.strip():
            continue
        if record.count("\x1f") != 2:
            # Never drop silently: an unparsed record is a message we did
            # not read, so the scan is incomplete and must not read clean.
            malformed += 1
            continue
        scanned += 1
        sha, subject, body = record.split("\x1f")
        sha = sha.strip()
        hits = scan_text(subject + "\n" + body, detectors)
        if hits:
            findings.append(
                (
                    sha[:8],
                    hits,
                    scan_text(subject, detectors) > 0,
                    _identifier_shaped(subject + "\n" + body),
                )
            )
    return CommitScan(findings, scanned, malformed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--commits", metavar="RANGE", help="git revision range, e.g. origin/main..HEAD"
    )
    source.add_argument("--text-file", type=Path, help="a file of prose to scan")
    source.add_argument(
        "--stdin", action="store_true", help="read the prose from stdin"
    )
    args = parser.parse_args(argv)

    if args.commits:
        scan = scan_commits(args.commits)
        findings = scan.findings
        print(f"scanned {scan.scanned} commit message(s) in range: {args.commits}")
        for sha, hits, in_subject, identifier in findings:
            where = "SUBJECT" if in_subject else "body"
            shape = (
                " identifier-shaped (invisible to the repo's own \\b patterns)"
                if identifier
                else ""
            )
            print(f"  LEAK {sha}  hits={hits}  first-in={where}{shape}")
        if findings:
            print(
                f"\n{len(findings)} commit message(s) name a dataset source. "
                f"Rewrite them before pushing — a pushed commit message is permanent."
            )
            return 1
        if scan.malformed:
            print(
                f"{scan.malformed} record(s) could not be parsed: the scan "
                f"is incomplete and cannot certify this range."
            )
            return 1
        print("clean")
        return 0

    text = (
        sys.stdin.read() if args.stdin else args.text_file.read_text(encoding="utf-8")
    )
    detectors = compile_detectors()
    lines = text.splitlines()
    leaking = [(n, scan_text(line, detectors)) for n, line in enumerate(lines, 1)]
    leaking = [(n, h) for n, h in leaking if h]
    label = "stdin" if args.stdin else str(args.text_file)
    print(f"scanned: {label} ({len(lines)} lines)")
    for n, hits in leaking:
        print(f"  LEAK line {n}  hits={hits}")
    if leaking:
        total = sum(h for _, h in leaking)
        print(
            f"\n{total} occurrence(s) on {len(leaking)} line(s). "
            f"Rewrite them before publishing to a GitHub-indexed surface."
        )
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""The guard on committed bytes: no tracked text file gains a CR (#3727, item 50c).

The defect this exists for
--------------------------
The writer census (``verify_text_writer_line_endings.py``, #3723) fences 43
writers of a tracked file. It cannot see the writer whose target it cannot
place (173 ``runtime-*`` sites, 102 ``in-repo``), an editor, a copy, or a seat
with ``core.autocrlf=false``. All of those share one outcome: a carriage
return reaches the index. This guard reads the outcome, not the cause.

Measured on ``main`` ``0e07e8359``: **306 tracked files carry a CR in the
index** (301 ``i/crlf``, 5 ``i/mixed``) out of 5 310.

The rule
--------
**No tracked text file carries a CR in the index, outside the census of the
files that carry one today.**

* The index is what is read -- ``git ls-files --eol``, the ``i/`` column -- so
  the verdict depends neither on the seat's checkout nor on its
  ``core.autocrlf``.
* ``*.bat`` is excluded: ``.gitattributes`` pins it to CRLF.
* The census only shrinks:

  - a file that carries a CR and is not in the census reddens;
  - a census entry whose file no longer carries a CR reddens, until the entry
    is removed;
  - the census holds at most ``CENSUS_CEILING`` paths, the count measured the
    day it was written: a new carrier passes only by raising the ceiling, in a
    reviewed commit.

What this does not do
---------------------
Normalising the 306 files, and any ``.gitattributes`` rule, are two decisions
left open on #3727 (propositions 2 and 3 of #3723). A file of the census is
reported, never rewritten.

Exit codes: ``0`` clean, ``1`` violations found, ``2`` the guard could not run
(not a git checkout, git unavailable, unreadable census).

Usage::

    python scripts/security/verify_committed_line_endings.py
    python scripts/security/verify_committed_line_endings.py --verbose
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
CENSUS_FILE = Path(__file__).with_name("crlf_committed_census.txt")

# The index classes of a text file that carries a carriage return somewhere.
CARRIERS = frozenset({"crlf", "mixed"})

# Measured on ``main`` ``0e07e8359``: 306 (301 ``i/crlf``, 5 ``i/mixed``).
# The census never grows past this number.
CENSUS_CEILING = 306

# ``.gitattributes``: ``*.bat text eol=crlf`` -- a batch file's CRLF is wanted.
EXCLUDED_SUFFIXES = (".bat",)


class GuardError(RuntimeError):
    """The guard could not run: nothing was measured."""


@dataclass(frozen=True)
class Report:
    """What the index says, compared with the census."""

    tracked: int
    carriers: tuple[str, ...]
    census_size: int
    new: tuple[str, ...]
    stale: tuple[str, ...]
    census_too_large: bool

    @property
    def ok(self) -> bool:
        return not (self.new or self.stale or self.census_too_large)


def read_index_eol(repo: Path | None = None) -> dict[str, str]:
    """Every tracked path with its index class, as ``git ls-files --eol`` gives it.

    Only the ``i/`` column is kept: the class of the blob the index holds. The
    ``w/`` column -- the working tree -- is printed by git and ignored here, so
    a file normalised in a working tree but not added still counts as it is
    committed.
    """
    target = REPO_ROOT if repo is None else repo
    proc = subprocess.run(
        ["git", "-C", str(target), "ls-files", "--eol", "-z"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise GuardError(
            "git ls-files --eol failed: "
            + proc.stderr.decode("utf-8", "replace").strip()
        )
    try:
        listing = proc.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GuardError(f"git ls-files --eol output is not UTF-8: {exc}") from exc
    classes: dict[str, str] = {}
    for record in listing.split("\0"):
        if not record:
            continue
        head, separator, path = record.partition("\t")
        if not separator or not path:
            raise GuardError(f"unreadable record: {record[:80]!r}")
        tokens = head.split()
        classes[path] = tokens[0][2:] if tokens else ""
    return classes


def is_carrier(path: str, index_class: str) -> bool:
    """Whether a tracked path is a text file that carries a carriage return."""
    if index_class not in CARRIERS:
        return False
    return not path.lower().endswith(EXCLUDED_SUFFIXES)


def parse_census(text: str) -> tuple[str, ...]:
    """The census paths, in file order. A comment and a blank line are not paths.

    A path listed twice is an error rather than a harmless repeat: the second
    line would hold a stale entry invisible to its own removal.
    """
    paths: list[str] = []
    seen: set[str] = set()
    for number, line in enumerate(text.split("\n"), 1):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if entry in seen:
            raise GuardError(f"census line {number}: {entry} is listed twice")
        seen.add(entry)
        paths.append(entry)
    return tuple(paths)


def load_census(path: Path | None = None) -> tuple[str, ...]:
    target = CENSUS_FILE if path is None else path
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise GuardError(f"the census cannot be read: {exc}") from exc
    return parse_census(text)


def judge(index_eol: Mapping[str, str], census: Iterable[str]) -> Report:
    """Compare the index with the census: new carriers, stale entries, size."""
    listed = tuple(census)
    if len(set(listed)) != len(listed):
        raise GuardError("the census lists a path twice")
    carriers = tuple(sorted(p for p, c in index_eol.items() if is_carrier(p, c)))
    in_census = set(listed)
    return Report(
        tracked=len(index_eol),
        carriers=carriers,
        census_size=len(listed),
        new=tuple(p for p in carriers if p not in in_census),
        stale=tuple(p for p in listed if not is_carrier(p, index_eol.get(p, ""))),
        census_too_large=len(listed) > CENSUS_CEILING,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="list every carrier, in the census or not",
    )
    args = parser.parse_args(argv)

    try:
        index_eol = read_index_eol()
        census = load_census()
        report = judge(index_eol, census)
    except GuardError as exc:
        print(f"the guard could not run: {exc}", file=sys.stderr)
        return 2

    counted = Counter(index_eol[path] for path in report.carriers)
    print(f"tracked files: {report.tracked}")
    print(
        "carrying a CR in the index: "
        f"{len(report.carriers)} "
        f"({', '.join(f'{k}={counted[k]}' for k in sorted(counted))})"
    )
    print(f"census: {report.census_size} (ceiling {CENSUS_CEILING})")
    print(f"new carriers outside the census: {len(report.new)}")
    print(f"stale census entries: {len(report.stale)}")

    if args.verbose:
        for path in report.carriers:
            mark = "census " if path in set(census) else "NEW    "
            print(f"  {mark}{path} [{index_eol[path]}]")

    for path in report.new:
        print(
            f"VIOLATION {path}: carries a CR in the index and is not in the "
            "census -- write LF (a writer of a tracked file declares "
            'newline="\\n"), or normalise the file; do not add it to the census'
        )
    for path in report.stale:
        print(
            f"VIOLATION {path}: in the census, and no longer carries a CR in "
            "the index -- remove the entry"
        )
    if report.census_too_large:
        print(
            f"VIOLATION the census holds {report.census_size} paths, more than "
            f"the ceiling {CENSUS_CEILING}: it only shrinks"
        )

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

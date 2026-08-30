"""Guards for the CoursIA vendored-drift instrument (#1949).

Every case below is a shape the checker *actually met* on the CoursIA tree, and
two of them are shapes that silently defeated a first, naive version of it. That
matters more than coverage: a drift checker only earns its negatives once it has
produced a known-good positive, and the two defects here both turned a
byte-identical copy into a false "the copy was modified" verdict.

1. **The provenance header is not always a prefix.** Where our upstream file
   opens with a shebang, CoursIA inserted the header *after* it. Stripping
   leading lines can never recover the upstream bytes for those files, so the
   body is located by removing a contiguous *slice*.
2. **One copy lacks the final newline.** Byte-identical otherwise. Without an
   explicit tolerance it lands in ``partial`` beside a file with 358 genuinely
   absent lines — a blind spot in the discriminator, reported as a finding about
   their repository.

The negative control matters as much: a genuinely curated subset must NOT be
rescued by either tolerance, or the checker would report every partial copy as
identical and measure nothing at all.

These tests build their own synthetic upstream and vendored blobs. They never
read the CoursIA checkout (absent in CI) and never recompute a digest the way
production does — they assert the *classification*, not the arithmetic.
"""

from __future__ import annotations

from pathlib import Path

from scripts.coursia.check_vendored_drift import (
    diff_size,
    locate_body,
    parse_ledger,
    sha1_lf,
)

UPSTREAM = b"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging


def do_the_thing(x):
    return x + 1
"""

HEADER = b"""# =============================================================================
# Verbatim copy from EPITA-IS
# Source SHA1 : deadbeef
# =============================================================================
"""


def _lines(blob: bytes) -> list[bytes]:
    """Split the way ``open(path, 'rb').readlines()`` does in production."""
    return blob.splitlines(keepends=True)


def test_sha1_lf_is_insensitive_to_line_endings() -> None:
    # Their headers pin a sha1sum of LF-normalised content; a CRLF checkout of
    # the same bytes must not read as drift.
    assert sha1_lf(UPSTREAM) == sha1_lf(UPSTREAM.replace(b"\n", b"\r\n"))


def test_sha1_lf_is_not_the_git_blob_hash() -> None:
    # The control that named the right instrument: git hash-object prefixes
    # "blob <len>\0", so it cannot reproduce a header digest. If these two ever
    # agree, the checker is measuring something other than what they pinned.
    import hashlib

    git_style = hashlib.sha1(b"blob %d\x00" % len(UPSTREAM) + UPSTREAM).hexdigest()
    assert sha1_lf(UPSTREAM) != git_style


def test_prefix_header_is_located() -> None:
    vendored = HEADER + UPSTREAM
    found = locate_body(_lines(vendored), {"head": sha1_lf(UPSTREAM)})
    assert found is not None
    label, start, length, eol_fixed = found
    assert label == "head"
    assert (start, length) == (0, len(_lines(HEADER)))
    assert eol_fixed is False


def test_header_inserted_after_a_shebang_is_located() -> None:
    # Defect 1: the header sits *inside* the file, so no leading-line strip can
    # recover the upstream bytes. Three of their verbatim copies have this shape.
    up_lines = _lines(UPSTREAM)
    vendored = b"".join(up_lines[:3]) + HEADER + b"".join(up_lines[3:])

    found = locate_body(_lines(vendored), {"head": sha1_lf(UPSTREAM)})
    assert found is not None, "a mid-inserted header must still be located"
    label, start, length, eol_fixed = found
    assert label == "head"
    assert start == 3, "the slice must start where the header was inserted"
    assert length == len(_lines(HEADER))
    assert eol_fixed is False


def test_missing_final_newline_is_tolerated_and_reported() -> None:
    # Defect 2: byte-identical but for the trailing newline. It must classify as
    # identical, AND say so — silently normalising would hide a real (if
    # trivial) difference from whoever reads the table.
    vendored = HEADER + UPSTREAM.rstrip(b"\n")
    found = locate_body(_lines(vendored), {"head": sha1_lf(UPSTREAM)})
    assert found is not None
    assert found[0] == "head"
    assert found[3] is True, "the missing newline must be surfaced, not swallowed"


def test_pin_match_is_preferred_only_when_head_does_not_match() -> None:
    # A copy that is current must never be reported as merely drifted, so "head"
    # is tried first even when both digests are offered.
    drifted_head = UPSTREAM.replace(b"return x + 1", b"return x + 2")
    vendored = HEADER + UPSTREAM

    both = {"head": sha1_lf(drifted_head), "pin": sha1_lf(UPSTREAM)}
    assert locate_body(_lines(vendored), both)[0] == "pin"

    current = {"head": sha1_lf(UPSTREAM), "pin": sha1_lf(UPSTREAM)}
    assert locate_body(_lines(vendored), current)[0] == "head"


def test_a_curated_subset_is_not_rescued_by_the_tolerances() -> None:
    # The negative control. Neither the slice search nor the newline tolerance
    # may turn a copy with a function removed from its middle into "identical" —
    # that is exactly the state the checker exists to distinguish, and two of
    # their largest files are in it.
    up_lines = _lines(UPSTREAM)
    subset = b"".join(up_lines[:5])  # drops the function body entirely
    vendored = HEADER + subset

    assert locate_body(_lines(vendored), {"head": sha1_lf(UPSTREAM)}) is None


def test_a_removed_middle_slice_is_not_rescued_either() -> None:
    # Sharper negative: same length class as a header, but removed from the
    # *upstream* side. The search may only remove lines from the vendored file.
    up_lines = _lines(UPSTREAM)
    gutted = b"".join(up_lines[:3] + up_lines[5:])
    vendored = HEADER + gutted

    assert locate_body(_lines(vendored), {"head": sha1_lf(UPSTREAM)}) is None


def test_parse_ledger_reads_table_rows_and_ignores_prose(tmp_path: Path) -> None:
    notice = tmp_path / "NOTICE-EPITA"
    notice.write_text(
        "NOTICE - verbatim copies\n"
        "This paragraph mentions `_decoy.py` and a path "
        "`argumentation_analysis/core/decoy.py` in prose.\n"
        "\n"
        "| `_shared_state.py` (1121 lines) | `argumentation_analysis/core/shared_state.py` "
        "| a8025f60 (2026-07-02) |\n"
        "| `_state_manager_plugin.py` | `argumentation_analysis/core/state_manager_plugin.py` "
        "| see git log |\n",
        encoding="utf-8",
    )
    ledger = parse_ledger(notice)

    assert set(ledger) == {"_shared_state.py", "_state_manager_plugin.py"}
    assert ledger["_shared_state.py"] == (
        "argumentation_analysis/core/shared_state.py",
        "a8025f60",
    )
    # A row whose commit cell is prose ("see git log") must still map, falling
    # back to the directory-wide pin rather than dropping the file from the
    # surface — a dropped row reads as "CoursIA-original, out of scope".
    up, pin = ledger["_state_manager_plugin.py"]
    assert up == "argumentation_analysis/core/state_manager_plugin.py"
    assert pin == "a8025f60"


def test_parse_ledger_returns_empty_for_a_missing_notice(tmp_path: Path) -> None:
    assert parse_ledger(tmp_path / "does-not-exist") == {}


def test_diff_size_counts_both_directions() -> None:
    # Used only to quantify how far a `partial` copy sits from its pin, so it
    # must not read a pure deletion as zero.
    up_lines = _lines(UPSTREAM)
    shorter = b"".join(up_lines[:5])
    assert diff_size(UPSTREAM, shorter) == len(up_lines) - 5
    assert diff_size(UPSTREAM, UPSTREAM) == 0

# -*- coding: utf-8 -*-
"""Measure the drift between our upstream and the CoursIA vendored fork (#1949).

CoursIA does not consume this repository through its notebooks: it vendors a
fork of our core into
``MyIA.AI.Notebooks/SymbolicAI/Argument_Analysis/argumentation_lib/``. Their
ledger ``NOTICE-EPITA`` pins an upstream commit per file and claims the copies
are "byte-for-byte identical" at that commit. Nothing on either side ever
re-checked that claim, which is why their pin sat seven weeks behind without
anyone noticing (#1451 recommended a re-pull tag but never produced it).

This is that missing instrument. It is **read-only on both sides** and prints a
table; it never writes into the CoursIA checkout (mission CoursIA-1 is
proposal-only).

The instrument, and why the obvious one is wrong
------------------------------------------------
Their per-file headers pin a ``sha1sum`` of the **LF-normalised content**. That
is *not* a git blob hash: ``git hash-object`` prefixes ``blob <len>\\0`` and
yields a different digest, and a CRLF checkout corrupts a raw ``sha1sum``.
Three contradictory drift readings were reconciled only once the right
instrument was identified, so this script normalises line endings on both sides
and reproduces the header digest of a known-undrifted file as its own control
(``--self-check``).

Two further traps this script is built around, both measured rather than
assumed:

1. **Four header formats coexist** (``Source SHA1 : x``, ``SHA1=x``, a prose
   "Verbatim copy of ... Source commit:" block, and a ``VERBATIM PORT --``
   block). A matcher calibrated on one silently reports "no header" for the
   others -- and "no header" reads as "CoursIA-original, out of scope", which is
   exactly the wrong conclusion for a verbatim copy. So this script never parses
   the header to find the body.
2. **The header is not always a prefix.** Where upstream starts with a shebang,
   the header was inserted *after* it, so no amount of leading-line stripping
   recovers the upstream bytes. The body is therefore located by searching for a
   contiguous **slice** whose removal reproduces upstream -- a search that is
   independent of header format and position.

States
------
``identical``  the body reproduces upstream at HEAD -- no drift.
``drifted``    the body reproduces upstream at the pinned commit but not at
               HEAD. The copy is honest and simply stale by N commits.
``partial``    the body reproduces neither. Measured, not guessed: the script
               reports how many lines differ from the pin. Two of their largest
               files are curated subsets rather than whole-file copies, which
               their own size column records even though their "Verbatim
               integrity" section claims byte-for-byte equality.
``no-ledger``  present in their directory but absent from ``NOTICE-EPITA``:
               CoursIA-original glue, out of scope.

Usage
-----
    python scripts/coursia/check_vendored_drift.py
    python scripts/coursia/check_vendored_drift.py --self-check
    python scripts/coursia/check_vendored_drift.py --coursia-root D:/CoursIA
    python scripts/coursia/check_vendored_drift.py --fail-on drift
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_COURSIA = Path(os.environ.get("COURSIA_ROOT", "D:/CoursIA"))
VENDOR_REL = Path("MyIA.AI.Notebooks/SymbolicAI/Argument_Analysis/argumentation_lib")
DEFAULT_PIN = "a8025f60"

# The ledger tables the mapping as `| `_file.py` (N lines) | upstream/path.py | commit |`.
LEDGER_ROW = re.compile(
    r"^\|\s*`(?P<vend>_[\w.]+\.py)`[^|]*\|\s*`?(?P<up>[\w/.]+\.py)`?\s*\|\s*(?P<pin>[0-9a-f]{7,40}|[^|]*)\|"
)
# Any of the four header dialects that state a source digest.
HEADER_SHA1 = re.compile(r"SHA1[\s:=]+([0-9a-f]{40})", re.I)

# The header sits within the first few lines (after at most a shebang + coding
# line + blanks) and is at most this long. Both bounds are measured on their
# tree, not guessed: the widest header seen is 43 lines, deepest start is 4.
MAX_SLICE_START = 8
MAX_SLICE_LEN = 80


def sh(*args: str, cwd: Path | None = None) -> str:
    """Run a command and return stdout, or "" if it fails."""
    try:
        r = subprocess.run(args, cwd=str(cwd or REPO), capture_output=True, check=False)
    except OSError:
        return ""
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def sha1_lf(data: bytes) -> str:
    """Digest of the content with CR stripped -- the instrument their headers use."""
    return hashlib.sha1(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def upstream_blob(rev: str, path: str) -> bytes | None:
    try:
        r = subprocess.run(
            ["git", "show", f"{rev}:{path}"],
            cwd=str(REPO),
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def parse_ledger(notice: Path) -> dict[str, tuple[str, str]]:
    """vendored filename -> (upstream path, pinned commit)."""
    out: dict[str, tuple[str, str]] = {}
    if not notice.is_file():
        return out
    for line in notice.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LEDGER_ROW.match(line)
        if not m:
            continue
        pin_raw = (m.group("pin") or "").strip()
        pin_m = re.match(r"^([0-9a-f]{7,40})", pin_raw)
        out[m.group("vend")] = (m.group("up"), pin_m.group(1) if pin_m else DEFAULT_PIN)
    return out


def locate_body(
    vend_lines: list[bytes], targets: dict[str, str]
) -> tuple[str, int, int, bool] | None:
    """Find a contiguous slice whose removal reproduces one of ``targets``.

    ``targets`` maps a label ("head" / "pin") to the expected LF digest. Returns
    ``(label, start, length, eol_fixed)`` for the first match, preferring "head"
    so an up-to-date copy is never reported as merely drifted. Format-independent
    by construction: it never looks at the header text.

    ``eol_fixed`` records that the match needed a trailing newline appended. One
    of their copies is byte-identical to upstream except for a missing final
    newline; without this tolerance it lands in ``partial`` next to a file with
    358 genuinely absent lines, which is a blind spot in the discriminator, not
    a finding about their copy.
    """
    n = len(vend_lines)
    for label in ("head", "pin"):
        want = targets.get(label)
        if not want:
            continue
        for start in range(0, min(MAX_SLICE_START, n) + 1):
            for length in range(0, min(MAX_SLICE_LEN, n - start) + 1):
                body = b"".join(vend_lines[:start] + vend_lines[start + length :])
                if sha1_lf(body) == want:
                    return label, start, length, False
                if body and not body.endswith(b"\n"):
                    if sha1_lf(body + b"\n") == want:
                        return label, start, length, True
    return None


def diff_size(a: bytes, b: bytes) -> int:
    """Number of differing lines between two blobs (cheap symmetric measure)."""
    from difflib import unified_diff

    al = a.replace(b"\r\n", b"\n").decode("utf-8", "replace").splitlines()
    bl = b.replace(b"\r\n", b"\n").decode("utf-8", "replace").splitlines()
    return sum(
        1
        for line in unified_diff(al, bl, n=0)
        if line[:1] in ("+", "-") and not line.startswith(("+++", "---"))
    )


def self_check(vendor_dir: Path) -> int:
    """Prove the instrument works before trusting any of its negatives.

    Reproduces the digest a header claims for a file whose upstream has received
    no commit since the pin. A drift report from an instrument that has never
    produced a known-good positive is worth nothing.
    """
    probe = vendor_dir / "_af_handler.py"
    if not probe.is_file():
        print(f"self-check: probe file missing ({probe})", file=sys.stderr)
        return 1
    m = HEADER_SHA1.search(probe.read_text(encoding="utf-8", errors="replace")[:4000])
    if not m:
        print("self-check: probe carries no SHA1 header", file=sys.stderr)
        return 1
    claimed = m.group(1)
    blob = upstream_blob(
        DEFAULT_PIN, "argumentation_analysis/agents/core/logic/af_handler.py"
    )
    if blob is None:
        print(f"self-check: cannot read upstream at {DEFAULT_PIN}", file=sys.stderr)
        return 1
    got = sha1_lf(blob)
    # The git blob hash, computed inline (sha1 over "blob <len>\0" + content), to
    # show on every run that the obvious instrument is the wrong one.
    wrong = hashlib.sha1(b"blob %d\0" % len(blob) + blob).hexdigest()
    print("self-check probe : _af_handler.py")
    print(f"  header claims  : {claimed}")
    print(f"  sha1sum (LF)   : {got}   <- the right instrument")
    print(f"  git hash-object: {wrong}   <- would NOT match, by design")
    ok = claimed == got
    print(f"  => {'OK, instrument reproduces the pinned digest' if ok else 'FAILED'}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--coursia-root", type=Path, default=DEFAULT_COURSIA)
    p.add_argument("--rev", default="HEAD", help="our revision to compare against")
    p.add_argument(
        "--self-check",
        action="store_true",
        help="prove the digest instrument on a known-undrifted file, then exit",
    )
    p.add_argument(
        "--fail-on",
        choices=["never", "drift", "partial"],
        default="never",
        help="exit non-zero on this condition (default: report only)",
    )
    args = p.parse_args(argv)

    vendor_dir = args.coursia_root / VENDOR_REL
    if not vendor_dir.is_dir():
        print(
            f"CoursIA vendored dir not found: {vendor_dir}\n"
            "Pass --coursia-root or set COURSIA_ROOT.",
            file=sys.stderr,
        )
        return 2

    if args.self_check:
        return self_check(vendor_dir)

    ledger = parse_ledger(vendor_dir / "NOTICE-EPITA")
    if not ledger:
        print(
            f"NOTICE-EPITA unreadable or tabled no rows under {vendor_dir}.\n"
            "The ledger is their source of truth for the vendored surface; "
            "without it every file would be misreported as CoursIA-original.",
            file=sys.stderr,
        )
        return 2

    head_sha = (sh("git", "rev-parse", "--short", args.rev) or "?").strip()
    print(f"upstream {args.rev} = {head_sha}   vendored dir = {vendor_dir}")
    print(f"ledger tables {len(ledger)} file(s)\n")

    rows: list[tuple[str, str, str, str]] = []
    counts = {"identical": 0, "drifted": 0, "partial": 0, "no-ledger": 0, "unmapped": 0}

    for vend_path in sorted(vendor_dir.glob("*.py")):
        name = vend_path.name
        if name not in ledger:
            counts["no-ledger"] += 1
            rows.append(
                (name, "no-ledger", "-", "CoursIA-original glue, not in NOTICE")
            )
            continue

        up_path, pin = ledger[name]
        pin_blob = upstream_blob(pin, up_path)
        head_blob = upstream_blob(args.rev, up_path)
        if pin_blob is None and head_blob is None:
            counts["unmapped"] += 1
            rows.append((name, "unmapped", "-", f"upstream path absent: {up_path}"))
            continue

        n_commits = len(
            [
                ln
                for ln in sh(
                    "git", "rev-list", f"{pin}..{args.rev}", "--", up_path
                ).splitlines()
                if ln.strip()
            ]
        )

        with vend_path.open("rb") as fh:
            vend_lines = fh.readlines()

        targets = {}
        if head_blob is not None:
            targets["head"] = sha1_lf(head_blob)
        if pin_blob is not None:
            targets["pin"] = sha1_lf(pin_blob)

        found = locate_body(vend_lines, targets)
        eol = ", no final newline" if found and found[3] else ""
        if found and found[0] == "head":
            counts["identical"] += 1
            rows.append(
                (
                    name,
                    "identical",
                    str(n_commits),
                    f"header {found[2]}L @{found[1]}{eol}",
                )
            )
        elif found:
            counts["drifted"] += 1
            rows.append(
                (
                    name,
                    "drifted",
                    str(n_commits),
                    f"matches pin {pin[:8]}, header {found[2]}L{eol}",
                )
            )
        else:
            counts["partial"] += 1
            # Not a guess: quantify how far the copy is from the pin it claims.
            body = b"".join(vend_lines)
            delta = diff_size(pin_blob, body) if pin_blob is not None else -1
            rows.append(
                (
                    name,
                    "partial",
                    str(n_commits),
                    f"~{delta} lines differ from pin {pin[:8]} (curated subset)",
                )
            )

    w = max(len(r[0]) for r in rows) + 2
    print(f"{'file'.ljust(w)}{'state'.ljust(12)}{'commits'.rjust(8)}  note")
    print("-" * (w + 12 + 8 + 40))
    for name, state, nc, note in rows:
        print(f"{name.ljust(w)}{state.ljust(12)}{nc.rjust(8)}  {note}")

    print(
        "\n"
        + "  ".join(f"{k}={v}" for k, v in counts.items() if v)
        + f"\n\n'commits' counts upstream commits on that path between the pinned "
        f"commit and {args.rev}. A 0 there with state=drifted is impossible; a 0 "
        "with state=identical simply means we have not touched the file since "
        "they copied it -- not a distillation failure."
    )

    if args.fail_on == "drift" and (counts["drifted"] or counts["partial"]):
        return 1
    if args.fail_on == "partial" and counts["partial"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

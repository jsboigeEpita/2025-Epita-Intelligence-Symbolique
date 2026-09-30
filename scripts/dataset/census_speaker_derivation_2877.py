# -*- coding: utf-8 -*-
"""#2877 census: what the legacy-label deriver files as a ``speaker``.

The defect (#2877, data-level half of #2845): ``parse_legacy_label`` ends with a
regex that files a **bare hyphenated pair** at the head of a label as a person —
the shape a debate or a two-author series takes. Nothing on the label says which
of the two speaks, or that a series is being named at all.

This instrument reads the campaign's **stored** states (the metadata the paid
run recorded) and re-derives the same metadata from each document's label with
the parser **as it stands in the tree**. The stored column is therefore the
pre-fix record and the re-derived column is the current behaviour: one run shows
both sides, and the non-vacuity check — the re-derivation must reproduce what
was recorded — is what makes the pair comparable.

Deterministic: 0 LLM requests, 0 JVM. The encrypted corpus is read in memory and
never persisted (see ``argumentation_analysis/core/io_manager.py``).

Privacy (this file is tracked): the output carries counts, booleans and opaque
ids — **never** a label, a source name, or a metadata value. The one shape
predicate is applied in-process and reported as a number.

Usage::

    python scripts/dataset/census_speaker_derivation_2877.py --since 2026-09-29
    python scripts/dataset/census_speaker_derivation_2877.py --require-zero-series
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIR = REPO_ROOT / "analysis_kb" / "state_dumps"
RUNNER = REPO_ROOT / "scripts" / "dataset" / "run_corpus_batch.py"

# The shape the removed branch filed as a person: one whitespace-free token
# holding an unspaced hyphen between two capitalised letter runs. Read as a
# *shape* only — a double surname is legitimate, and this census does not claim
# otherwise (see #2877).
_BARE_PAIR_RE = re.compile(r"[A-ZÀ-Þ][\w'’-]+-[A-ZÀ-Þ][\w'’-]+")
_DUMP_NAME_RE = re.compile(r"\Astate_full_(?P<oid>.+?)(?:_ext(?P<idx>\d+))?\Z")


def _load_runner() -> Any:
    """Import the runner itself — never a copy of its heuristics.

    A census that re-implements the deriver measures the copy, not the code
    (the reason ``merge_source_metadata`` was extracted from ``main()``).
    """
    spec = importlib.util.spec_from_file_location("_run_corpus_batch", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _is_bare_pair(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value.split()) != 1:
        return False
    return _BARE_PAIR_RE.fullmatch(value) is not None


def _load_definitions(runner: Any) -> List[Dict[str, Any]]:
    from dotenv import load_dotenv

    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key

    load_dotenv(REPO_ROOT / ".env")
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        raise RuntimeError("TEXT_CONFIG_PASSPHRASE not set in .env")
    key = derive_encryption_key(passphrase)
    if not key:
        raise RuntimeError("cannot derive the encryption key")
    return load_extract_definitions(
        config_file=runner.ENCRYPTED_PATH,
        b64_derived_key=key.decode("utf-8"),
        raise_on_decrypt_error=True,
    )


def _derive(
    runner: Any, src_name: str, src_meta: Dict[str, Any], date_iso: str
) -> Dict[str, str]:
    """The production merge chain, verbatim (heuristics < label < explicit)."""
    merged = runner.merge_source_metadata(
        runner.merge_source_metadata(
            runner.classify_metadata(src_name, date_iso),
            runner.parse_legacy_label(src_name),
        ),
        src_meta,
    )
    return cast(Dict[str, str], merged)


def _provenance(args: argparse.Namespace, n_defs: int, n_dumps: int) -> None:
    import subprocess

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", str(Path(__file__).resolve())],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except OSError:  # pragma: no cover - git absent
        head, dirty = "unknown", "unknown"
    print("provenance")
    print(f"  HEAD: {head} (this producer dirty: {'yes' if dirty else 'no'})")
    print(
        f"  command: python scripts/dataset/{Path(__file__).name} --since {args.since or '-'}"
    )
    print(f"  parser: {RUNNER.relative_to(REPO_ROOT)} as it stands in the tree")
    print(f"  corpus definitions read in memory: {n_defs} (never persisted to disk)")
    print(f"  stored dumps in population: {n_dumps}")
    print("  LLM requests: 0 | JVM: 0")
    print("  prints: counts, booleans, opaque ids — never a metadata value")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="#2877 speaker-derivation census")
    ap.add_argument("--dumps-dir", default=str(DUMPS_DIR))
    ap.add_argument(
        "--since",
        default="",
        help="only dumps whose mtime (YYYY-MM-DD) is >= this date — an mtime "
        "filter, not an in-state timestamp: the stored state carries none",
    )
    ap.add_argument(
        "--require-zero-series",
        action="store_true",
        help="exit 1 while any re-derived speaker has the bare-pair shape",
    )
    args = ap.parse_args(argv)

    runner = _load_runner()
    from argumentation_analysis.evaluation.opaque_id import opaque_id

    definitions = _load_definitions(runner)

    by_oid: Dict[str, Tuple[str, Dict[str, Any], str]] = {}
    for definition in definitions:
        src_name = definition.get("source_name", "")
        if not src_name:
            continue
        src_meta = definition.get("metadata", {}) or {}
        date_iso = src_meta.get("date_iso", definition.get("date", ""))
        by_oid[opaque_id(src_name)] = (src_name, src_meta, date_iso)

    since = args.since.strip()
    dumps: List[Path] = []
    for path in sorted(Path(args.dumps_dir).glob("state_full_*.json")):
        if since and path.stat().st_mtime < _mtime_floor(since):
            continue
        dumps.append(path)

    _provenance(args, len(definitions), len(dumps))

    matched: List[str] = []
    unmatched: List[str] = []
    stored_speakers = 0
    derived_speakers = 0
    stored_pairs = 0
    derived_pairs = 0
    lost_speaker: List[str] = []
    regained_speaker: List[str] = []
    reproduced_ok = 0
    reproduced_checked = 0
    field_mismatches: Dict[str, int] = {}

    unmatched_speakers = 0
    unmatched_pairs = 0
    for path in dumps:
        m = _DUMP_NAME_RE.match(path.stem)
        oid = m.group("oid") if m else path.stem

        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            unmatched.append(oid)
            continue

        entry = by_oid.get(oid)
        if entry is None:
            # Kept in the population as a **stored-only** row: its source is
            # absent from the corpus revision on disk, so its label cannot be
            # re-derived. Reported rather than dropped — a shrinking denominator
            # that is not named is the defect #1903 names.
            unmatched.append(oid)
            unmatched_speakers += (
                1 if (state.get("source_metadata") or {}).get("speaker") else 0
            )
            unmatched_pairs += (
                1
                if _is_bare_pair((state.get("source_metadata") or {}).get("speaker"))
                else 0
            )
            continue

        matched.append(oid)
        src_name, src_meta, date_iso = entry
        stored = state.get("source_metadata") or {}
        derived = _derive(runner, src_name, src_meta, date_iso)

        # Non-vacuity: where the campaign recorded a field, the re-derivation
        # must reproduce it — otherwise the two columns measure different things
        # and the before/after pair says nothing.
        reproduced_checked += 1
        mismatched = [
            key
            for key in set(stored) | set(derived)
            if str(stored.get(key, "")) != str(derived.get(key, ""))
        ]
        if not mismatched:
            reproduced_ok += 1
        for key in mismatched:
            field_mismatches[key] = field_mismatches.get(key, 0) + 1

        s_val, d_val = stored.get("speaker"), derived.get("speaker")
        stored_speakers += 1 if s_val else 0
        derived_speakers += 1 if d_val else 0
        stored_pairs += 1 if _is_bare_pair(s_val) else 0
        derived_pairs += 1 if _is_bare_pair(d_val) else 0
        if s_val and not d_val:
            lost_speaker.append(oid)
        if d_val and not s_val:
            regained_speaker.append(oid)

    print("population")
    print(f"  dumps considered            : {len(dumps)}")
    print(f"  paired with a definition    : {len(matched)}")
    print(
        f"  unpaired (stored-only row)  : {len(unmatched)} {unmatched if unmatched else ''}"
    )
    if unmatched:
        print(
            f"    of those, storing a speaker: {unmatched_speakers}"
            f" (bare-pair shape: {unmatched_pairs}) — source absent from the"
            " corpus revision on disk, label not re-derivable"
        )
    print()
    print("non-vacuity — the re-derivation reproduces the recorded metadata")
    print(f"  documents compared          : {reproduced_checked}")
    print(f"  reproduced field for field  : {reproduced_ok}")
    if field_mismatches:
        for key in sorted(field_mismatches):
            print(f"    field {key}: {field_mismatches[key]} document(s) differ")
    else:
        print("    (every field identical)")
    print()
    print("speaker column                 stored(pre-fix)   re-derived(current)")
    print(
        f"  documents recording one    : {stored_speakers:>10}   {derived_speakers:>18}"
    )
    print(f"  of those, bare-pair shape  : {stored_pairs:>10}   {derived_pairs:>18}")
    print(
        f"  speaker dropped by the fix : {len(lost_speaker)} {lost_speaker if lost_speaker else ''}"
    )
    if regained_speaker:
        print(
            f"  speaker gained             : {len(regained_speaker)} {regained_speaker}"
        )
    print()
    if derived_pairs:
        print(
            f"VERDICT: {derived_pairs} re-derived speaker(s) still carry the series shape"
        )
    else:
        print("VERDICT: no re-derived speaker carries the series shape")
    if args.require_zero_series and derived_pairs:
        return 1
    return 0


def _mtime_floor(since: str) -> float:
    import datetime

    day = datetime.datetime.strptime(since, "%Y-%m-%d")
    return day.timestamp()


if __name__ == "__main__":
    sys.exit(main())

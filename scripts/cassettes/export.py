"""Export LLM cache entries from a runtime diskcache DB to JSON fixtures.

Usage::

    python scripts/cassettes/export.py <source_db_dir> <fixtures_dir>

Source DB layout (produced by `llm_cache.CachedChatCompletion` at runtime):

    <source_db_dir>/cache.db        # SQLite, opened as diskcache.Cache

Each entry has:
- key: hex sha256 string (32 chars)
- value: JSON list-of-dicts (SK-path: `_serialize_response`)
       OR JSON dict (raw-path: `_serialize_chat_completion`)

The fixtures layout is:

    <fixtures_dir>/<sha256>.json    # {"key": "...", "value": [...] or {...}}

If `value` fails the privacy audit (see ``privacy.audit_value``), the
script refuses to write that cassette and exits with code 2. A summary is
printed at the end (cassettes exported, refused, total).

Why one-file-per-cassette: PR diffs become readable; partial fixes can be
targeted; git blame stays useful. The DB format (SQLite) is opaque to the
auditor — JSON files make the privacy check possible without parsing
SQLite.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/cassettes/export.py` invocation from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import diskcache  # type: ignore[import-not-found]

from scripts.cassettes.privacy import assert_safe, audit_value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "source_dir",
        type=Path,
        help="Runtime diskcache directory (e.g. .cache/llm_responses)",
    )
    p.add_argument(
        "fixtures_dir",
        type=Path,
        help="Destination directory for JSON cassette fixtures",
    )
    p.add_argument(
        "--allow-unsafe",
        action="store_true",
        help="Skip privacy audit (DO NOT USE without explicit review, #1603)",
    )
    return p.parse_args(argv)


def export_one(db: diskcache.Cache, key: str, value, fixtures_dir: Path, *, allow_unsafe: bool) -> str:
    """Write one cassette. Returns 'ok' | 'unsafe' | 'already'."""
    out = fixtures_dir / f"{key}.json"
    if out.exists():
        return "already"
    if not allow_unsafe:
        violations = audit_value(value, source=f"cassette {key[:16]}")
        if violations:
            return "unsafe"
    out.write_text(
        json.dumps({"key": key, "value": value}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return "ok"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.source_dir.exists():
        print(f"Source DB dir does not exist: {args.source_dir}", file=sys.stderr)
        return 1
    args.fixtures_dir.mkdir(parents=True, exist_ok=True)

    db = diskcache.Cache(str(args.source_dir))
    try:
        total = len(db)
        if total == 0:
            print(f"No entries in {args.source_dir}; nothing to export.", file=sys.stderr)
            return 0

        counts: dict[str, int] = {"ok": 0, "already": 0, "unsafe": 0}
        unsafe_keys: list[str] = []
        for key in db.iterkeys():
            value = db[key]
            status = export_one(db, key, value, args.fixtures_dir, allow_unsafe=args.allow_unsafe)
            counts[status] = counts.get(status, 0) + 1
            if status == "unsafe":
                unsafe_keys.append(key[:16])
    finally:
        db.close()

    print(f"Source: {args.source_dir}")
    print(f"Fixtures: {args.fixtures_dir}")
    print(f"Total entries: {total}")
    print(f"Exported: {counts['ok']}")
    print(f"Already present: {counts['already']}")
    print(f"Refused (privacy): {counts['unsafe']}")
    if unsafe_keys:
        print(f"Refused cassettes (first 16 chars of key): {unsafe_keys}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Import LLM cassettes from JSON fixtures into a runtime diskcache DB.

Usage::

    python scripts/cassettes/import.py <fixtures_dir> <target_db_dir>

Target DB layout (consumed by `llm_cache.CachedChatCompletion` at replay):

    <target_db_dir>/cache.db        # SQLite, opened as diskcache.Cache

Each fixture file `<sha256>.json` holds ``{"key": sha256, "value": ...}``
— the ``value`` is the literal output of `_serialize_response` /
`_serialize_chat_completion`. Round-tripped through the matching
`_deserialize_*` at replay.

This is the inverse of ``export.py``. No privacy audit is run on import
because the audit ran at export time and any new cassette written to the
fixtures dir would have failed it. Re-running the export after an import
should be idempotent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/cassettes/import.py` invocation from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import diskcache  # type: ignore[import-not-found]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "fixtures_dir",
        type=Path,
        help="Directory containing <sha256>.json cassette files",
    )
    p.add_argument(
        "target_dir",
        type=Path,
        help="Runtime diskcache directory to populate (e.g. .cache/llm_responses)",
    )
    p.add_argument(
        "--purge",
        action="store_true",
        help="Purge the target DB before import (otherwise merge)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.fixtures_dir.exists():
        print(f"Fixtures dir does not exist: {args.fixtures_dir}", file=sys.stderr)
        return 1
    args.target_dir.mkdir(parents=True, exist_ok=True)

    db = diskcache.Cache(str(args.target_dir))
    try:
        if args.purge:
            db.clear()
        existing = set(db.iterkeys())

        written = 0
        skipped = 0
        bad = 0
        for path in sorted(args.fixtures_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            key = data.get("key")
            value = data.get("value")
            if not isinstance(key, str) or value is None:
                print(f"Malformed cassette: {path.name}", file=sys.stderr)
                bad += 1
                continue
            if key in existing:
                skipped += 1
                continue
            db.set(key, value)
            written += 1
    finally:
        db.close()

    print(f"Fixtures: {args.fixtures_dir}")
    print(f"Target: {args.target_dir}")
    print(f"Written: {written}")
    print(f"Skipped (already present): {skipped}")
    print(f"Malformed: {bad}")
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Cost artifact for a record run (#1603, DoD 6).

Reads a runtime record-mode diskcache DB and emits a truthful spend summary:

- total entries (unique cache keys = unique LLM requests made during the run)
- raw-path entries (dict values from ``_serialize_chat_completion``) carry the
  OpenAI ``usage`` block (prompt/completion tokens) — summed here.
- SK-path entries (list values from ``_serialize_response``) do NOT carry usage
  (the serialized ChatMessageContent has no token counters) — counted only.

A dollar estimate is printed ONLY when ``LLM_PRICE_PER_1M_IN`` /
``LLM_PRICE_PER_1M_OUT`` are set (per-1M-token USD); without them the report
stays token-only rather than guessing a price. The record job's cost gate uses
the token totals; the operator prices them against the provider's current
rate card.

Usage::

    python scripts/cassettes/cost_report.py <record_db_dir> [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import diskcache


def analyze(db_dir: Path) -> Dict[str, Any]:
    """Return the spend summary for a record-mode diskcache DB."""
    db = diskcache.Cache(str(db_dir))
    try:
        total = len(db)
        sk_path = 0
        raw_path = 0
        prompt_tokens = 0
        completion_tokens = 0
        for key in db.iterkeys():
            value = db[key]
            if isinstance(value, list):
                sk_path += 1
            elif isinstance(value, dict):
                raw_path += 1
                usage = value.get("usage") or {}
                if isinstance(usage, dict):
                    prompt_tokens += int(usage.get("prompt_tokens") or 0)
                    completion_tokens += int(usage.get("completion_tokens") or 0)
            else:
                raise ValueError(
                    f"Unexpected cache value type {type(value)!r} for {key[:16]}"
                )
    finally:
        db.close()

    in_price = os.getenv("LLM_PRICE_PER_1M_IN")
    out_price = os.getenv("LLM_PRICE_PER_1M_OUT")
    est_usd: float | None = None
    if in_price and out_price:
        est_usd = prompt_tokens / 1_000_000 * float(
            in_price
        ) + completion_tokens / 1_000_000 * float(out_price)
    return {
        "db_dir": str(db_dir),
        "total_requests": total,
        "sk_path_requests": sk_path,
        "raw_path_requests": raw_path,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "est_usd": est_usd,
        "price_note": (
            "est_usd computed from LLM_PRICE_PER_1M_IN/OUT env vars (per-1M-token USD)"
            if est_usd is not None
            else "est_usd absent — set LLM_PRICE_PER_1M_IN/OUT to price the token totals"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("db_dir", type=Path, help="Runtime diskcache dir of the record run")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    args = p.parse_args(argv)

    if not args.db_dir.exists():
        print(f"DB dir does not exist: {args.db_dir}", file=sys.stderr)
        return 1

    report = analyze(args.db_dir)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"# Cost artifact — {report['db_dir']}")
    print(f"- Total requests (unique cache keys): {report['total_requests']}")
    print(f"- Raw-path (usage available): {report['raw_path_requests']}")
    print(f"- SK-path (usage unavailable, counted only): {report['sk_path_requests']}")
    print(f"- Prompt tokens: {report['prompt_tokens']}")
    print(f"- Completion tokens: {report['completion_tokens']}")
    if report["est_usd"] is not None:
        print(f"- Estimated cost: ${report['est_usd']:.4f}")
    print(f"- {report['price_note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

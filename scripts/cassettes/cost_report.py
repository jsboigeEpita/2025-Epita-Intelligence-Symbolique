"""Cost artifact for a record run (#1603, DoD 6).

Reads a runtime record-mode diskcache DB and emits a truthful spend summary:

- total entries (unique cache keys = unique LLM requests made during the run)
- raw-path entries (dict values from ``_serialize_chat_completion``) carry the
  OpenAI ``usage`` block (prompt/completion tokens) — summed here.
- SK-path entries (list values from ``_serialize_response``) carry their
  request's usage under each item's ``metadata.usage`` — summed here too, once
  per entry (#3686; the report used to leave that half out: 163 865 and
  133 396 prompt tokens outside the total on two record runs, so outside the
  token cap that reads it). An entry whose items carry no usage block is
  counted, and named in ``sk_path_entries_without_usage``.

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


def _usage_tokens(usage: Any) -> tuple[int, int] | None:
    """(prompt, completion) of a usage block, or None when it holds no count.

    A block with one of the two counts is read, the other being 0: that is how
    the raw path always behaved, and a cap that skipped a half-filled block
    would watch less than the run spent.
    """
    if not isinstance(usage, dict):
        return None
    if "prompt_tokens" not in usage and "completion_tokens" not in usage:
        return None
    return int(usage.get("prompt_tokens") or 0), int(
        usage.get("completion_tokens") or 0
    )


def _list_entry_usage(value: list[Any]) -> tuple[int, int] | None:
    """The usage of one SK-path entry: one request, so one block.

    Semantic Kernel builds each item's metadata from its choice and from the
    whole completion, and puts the completion's ``usage`` on every item
    (``_create_chat_message_content`` and ``_get_metadata_from_chat_response``
    of ``open_ai_chat_completion_base.py``, read on 1.44.0). A list of n items
    therefore carries the same block n times: the first one found is the
    entry's, and it is counted once.
    """
    for item in value:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        found = _usage_tokens(
            metadata.get("usage") if isinstance(metadata, dict) else None
        )
        if found is not None:
            return found
    return None


def analyze(db_dir: Path) -> Dict[str, Any]:
    """Return the spend summary for a record-mode diskcache DB."""
    db = diskcache.Cache(str(db_dir))
    try:
        total = len(db)
        sk_path = 0
        raw_path = 0
        raw_tokens = [0, 0]
        sk_tokens = [0, 0]
        sk_with_usage = 0
        sk_without_usage: list[str] = []
        for key in db.iterkeys():
            value = db[key]
            if isinstance(value, list):
                sk_path += 1
                found = _list_entry_usage(value)
                if found is None:
                    sk_without_usage.append(key[:16])
                else:
                    sk_with_usage += 1
                    sk_tokens[0] += found[0]
                    sk_tokens[1] += found[1]
            elif isinstance(value, dict):
                raw_path += 1
                found = _usage_tokens(value.get("usage"))
                if found is not None:
                    raw_tokens[0] += found[0]
                    raw_tokens[1] += found[1]
            else:
                raise ValueError(
                    f"Unexpected cache value type {type(value)!r} for {key[:16]}"
                )
    finally:
        db.close()

    prompt_tokens = raw_tokens[0] + sk_tokens[0]
    completion_tokens = raw_tokens[1] + sk_tokens[1]

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
        # The two totals are what the record step's token cap reads. Each half
        # is given apart, so a reader sees what each path brought.
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "raw_path_prompt_tokens": raw_tokens[0],
        "raw_path_completion_tokens": raw_tokens[1],
        "sk_path_prompt_tokens": sk_tokens[0],
        "sk_path_completion_tokens": sk_tokens[1],
        "sk_path_entries_with_usage": sk_with_usage,
        "sk_path_entries_without_usage": sk_without_usage,
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
    print(
        "- SK-path (usage summed once per entry, read under each item's "
        f"metadata): {report['sk_path_requests']}"
    )
    print(
        f"- SK-path entries with a usage block: {report['sk_path_entries_with_usage']}"
    )
    without = report["sk_path_entries_without_usage"]
    if without:
        print(
            "- SK-path entries without usage (counted, not in the totals), "
            f"{len(without)} of them: {', '.join(without)}"
        )
    print(
        f"- Prompt tokens: {report['prompt_tokens']} "
        f"(raw-path {report['raw_path_prompt_tokens']} / "
        f"SK-path {report['sk_path_prompt_tokens']})"
    )
    print(
        f"- Completion tokens: {report['completion_tokens']} "
        f"(raw-path {report['raw_path_completion_tokens']} / "
        f"SK-path {report['sk_path_completion_tokens']})"
    )
    if report["est_usd"] is not None:
        print(f"- Estimated cost: ${report['est_usd']:.4f}")
    print(f"- {report['price_note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

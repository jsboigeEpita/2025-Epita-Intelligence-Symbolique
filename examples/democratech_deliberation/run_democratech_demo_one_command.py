"""DT-2 #1499 — One-command Democratech demo entrypoint.

The non-specialist runs ONE command and gets a readable per-proposition
deliberation verdict. Two modes, picked automatically:

1. **LIVE mode** (requires ``OPENAI_API_KEY`` or ``OPENROUTER_*``): runs the
   existing BO-2 #1486 driver (synthetic bundle, real LLM agents, ~150-200s
   per proposition). Each verdict is marked ``decided_firsthand=True``.

2. **SNAPSHOT mode** (no LLM key required): reads a pre-recorded JSON snapshot
   of a previous LIVE run, replayed as-is. Each verdict is marked
   ``decided_firsthand="PRE-RECORDED"`` (never ``True``, never silently
   confused with LIVE). The snapshot path is ``./prerecorded_snapshot.json``
   (cwd) or ``~/.cache/democratech/prerecorded_snapshot.json`` if absent.

If neither is available, exits with code 2 and a clear actionable message
(``set OPENAI_API_KEY, or drop a prerecorded_snapshot.json in the cwd``).
NEVER invents a verdict.

Anti-théâtre #1019: this script NEVER fabricates a verdict. The LIVE mode
calls the real workflow; the SNAPSHOT mode replays a file that was
previously produced by a real run (or refused outright). The output
column ``Firsthand`` always reflects the truth (``YES``, ``PRE-RECORDED``,
or ``no``).

Privacy HARD #1472: synthetic domain-public propositions only. No corpus,
no real names, no ``raw_text``. Opaque IDs on all output surfaces.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python \\
        examples/democratech_deliberation/run_democratech_demo_one_command.py

    # Limit to N propositions, or emit compact JSON
    python run_democratech_demo_one_command.py --limit 3
    python run_democratech_demo_one_command.py --json
    python run_democratech_demo_one_command.py --snapshot path/to/file.json

Exit codes:
    0 — verdict rendered (LIVE or SNAPSHOT)
    2 — no LLM key AND no snapshot found (actionable error)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEMO_DIR = Path(__file__).resolve().parent
SNAPSHOT_FILENAME = "prerecorded_snapshot.json"


def _ensure_api_key() -> Optional[str]:
    """Return the active API key or print a clear skip reason."""
    from dotenv import load_dotenv

    load_dotenv()
    if os.environ.get("OPENROUTER_API_KEY") and os.environ.get("OPENROUTER_BASE_URL"):
        return "openrouter"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def _locate_snapshot(snapshot_arg: Optional[str]) -> Optional[Path]:
    """Locate the pre-recorded snapshot, in this priority order:
    1. ``--snapshot <path>`` argument (explicit, highest priority).
    2. ``./prerecorded_snapshot.json`` (cwd, bundle-delivered).
    3. ``~/.cache/democratech/prerecorded_snapshot.json`` (user-installed).

    Returns None if nothing is found.
    """
    if snapshot_arg:
        p = Path(snapshot_arg)
        return p if p.is_file() else None

    cwd_candidate = Path.cwd() / SNAPSHOT_FILENAME
    if cwd_candidate.is_file():
        return cwd_candidate

    user_cache = Path.home() / ".cache" / "democratech" / SNAPSHOT_FILENAME
    if user_cache.is_file():
        return user_cache

    return None


def _load_snapshot(path: Path) -> Dict[str, Any]:
    """Load + minimally validate a pre-recorded snapshot.

    The snapshot format is exactly what ``run_democratech_demo.py`` produces
    when run with ``--json`` on a LIVE run. Schema:

        {
            "mode": "live",                          # provenance
            "produced_at": "2026-07-24T...",         # ISO timestamp
            "propositions": {
                "prop_A": {
                    "verdict": {
                        "decided_firsthand": True,
                        "winner": "Option A",
                        "n_methods": 12,
                        "methods": {"condorcet": "Option A", ...},
                        "consensus_rate": 0.75
                    },
                    "phase_rows": [["extract", "completed", ...], ...]
                },
                ...
            }
        }
    """
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"snapshot {path} root is not a dict")
    propositions = data.get("propositions")
    if not isinstance(propositions, dict):
        raise ValueError(f"snapshot {path} has no 'propositions' dict")
    for pid, payload in propositions.items():
        if not isinstance(payload, dict):
            raise ValueError(f"snapshot {path}: proposition {pid} is not a dict")
        verdict = payload.get("verdict")
        if not isinstance(verdict, dict):
            raise ValueError(
                f"snapshot {path}: proposition {pid} has no verdict dict"
            )
        # Anti-theater: a snapshot is always PRE-RECORDED, never LIVE.
        verdict["decided_firsthand"] = "PRE-RECORDED"
    return data


def _snapshot_to_results(
    snapshot: Dict[str, Any], limit: Optional[int]
) -> List[Dict[str, Any]]:
    """Project the snapshot dict into the demo's result-list shape."""
    out: List[Dict[str, Any]] = []
    for pid, payload in list(snapshot["propositions"].items())[
        : limit or len(snapshot["propositions"])
    ]:
        out.append(
            {
                "id": pid,
                "label": payload.get("label", pid),
                "verdict": payload["verdict"],
                "phase_rows": payload.get("phase_rows", []),
            }
        )
    return out


def _print_table(results: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 78)
    print(" DEMOCRATECH DELIBERATION — per-proposition verdict ")
    print("=" * 78)
    hdr = f"{'ID':<7} {'Firsthand':<13} {'Winner':<10} {'#Methods':<9} {'Consensus':<10}"
    print(hdr)
    print("-" * 78)
    for r in results:
        v = r["verdict"]
        firsthand = "YES" if v["decided_firsthand"] is True else (
            "PRE-RECORDED" if v["decided_firsthand"] == "PRE-RECORDED" else "no"
        )
        winner = v.get("winner") or "—"
        consensus = (
            f"{v.get('consensus_rate', 0):.2f}"
            if isinstance(v.get("consensus_rate"), (int, float))
            else "—"
        )
        print(f"{r['id']:<7} {firsthand:<13} {str(winner):<10} "
              f"{v.get('n_methods', 0):<9} {consensus:<10}")
    print("-" * 78)
    n_decided = sum(
        1 for r in results if r["verdict"]["decided_firsthand"] is True
    )
    n_prerecorded = sum(
        1 for r in results
        if r["verdict"]["decided_firsthand"] == "PRE-RECORDED"
    )
    print(
        f" {n_decided}/{len(results)} decided LIVE · "
        f"{n_prerecorded}/{len(results)} PRE-RECORDED "
        f"(anti-théâtre: never fabricated)."
    )
    if results and results[0].get("phase_rows"):
        print("\n Per-phase status (first proposition):")
        for row in results[0]["phase_rows"]:
            name, status, comp = (row + ("", "", ""))[:3]
            print(f"   {str(name):<22} {str(status):<16} {str(comp)}")
    print("=" * 78)


async def _run_live(
    limit: Optional[int], provider: str
) -> List[Dict[str, Any]]:
    """Delegate to the existing BO-2 #1486 driver (LIVE mode)."""
    sys.path.insert(0, str(DEMO_DIR))
    from run_democratech_demo import run_demo

    results: List[Dict[str, Any]] = await run_demo(limit=limit)
    return results


def _emit(results: List[Dict[str, Any]], as_json: bool) -> None:
    if as_json:
        compact = [
            {"id": r["id"], "label": r["label"], **r["verdict"]}
            for r in results
        ]
        print(json.dumps(compact, indent=2, default=str, ensure_ascii=False))
    else:
        _print_table(results)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "DT-2 #1499 — one-command Democratech demo (LIVE if LLM key, "
            "otherwise SNAPSHOT replay, otherwise actionable exit)."
        )
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit to N propositions (default: all).")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of the table.")
    parser.add_argument("--snapshot", type=str, default=None,
                        help="Explicit path to a pre-recorded snapshot JSON.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    provider = _ensure_api_key()
    snapshot_path = _locate_snapshot(args.snapshot)

    if provider is not None:
        # ─── LIVE mode: delegate to the BO-2 #1486 driver ───
        print(f"[DT-2] LLM key detected ({provider}) — LIVE mode "
              f"(BO-2 #1486 driver, ~150-200s/proposition).", file=sys.stderr)
        results = asyncio.run(_run_live(args.limit, provider))
        _emit(results, args.json)
        return 0

    if snapshot_path is not None:
        # ─── SNAPSHOT mode: replay a pre-recorded run, never invent ───
        print(f"[DT-2] No LLM key — SNAPSHOT mode ({snapshot_path}).",
              file=sys.stderr)
        snapshot = _load_snapshot(snapshot_path)
        results = _snapshot_to_results(snapshot, args.limit)
        _emit(results, args.json)
        return 0

    # ─── Neither mode is available — actionable error ───
    print(
        "[DT-2] ERROR: no LLM key AND no pre-recorded snapshot.\n"
        "  To run the demo:\n"
        "    a) Set OPENAI_API_KEY (or OPENROUTER_API_KEY + OPENROUTER_BASE_URL)\n"
        "       in .env to use LIVE mode (real LLM, slower).\n"
        "    b) Drop a 'prerecorded_snapshot.json' in the current directory\n"
        "       (or ~/.cache/democratech/) to use SNAPSHOT replay.\n"
        "       A snapshot is produced by: python "
        "run_democratech_demo.py --json > prerecorded_snapshot.json\n"
        "  Anti-théâtre: this entrypoint NEVER invents a verdict.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

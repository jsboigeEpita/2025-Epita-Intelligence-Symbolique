"""Democratech deliberation demo driver (BO-2 #1472 residual).

Runs the ``democratech`` workflow E2E over the bundle of synthetic domain-public
propositions (``synthetic_proposals.py``) and prints a READABLE per-proposition
verdict — winner, voting methods, consensus, honest-degraded flags. Bundle-able
as course / soutenance demo material.

Privacy HARD (#1472): every proposition is synthetic + domain-public. No corpus,
no real names, no ``raw_text``. Opaque IDs (prop_A..prop_E) on all output.

Anti-théâtre (#1019): the demo runs the workflow with REAL agents (no mock) and
reports each verdict's ``governance_decided_firsthand`` flag — a proposition
that fails to decide is reported as such, never fabricated.

Usage:
    conda run -n projet-is-roo-new --no-capture-output \\
        python examples/democratech_deliberation/run_democratech_demo.py

    # Limit to N propositions (default: all 5)
    python run_democratech_demo.py --limit 3

    # JSON output (machine-readable) instead of the readable table
    python run_democratech_demo.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


def _ensure_api_key() -> Optional[str]:
    """Return the active API key or print a clear skip reason."""
    from dotenv import load_dotenv

    load_dotenv()
    if os.environ.get("OPENROUTER_API_KEY") and os.environ.get("OPENROUTER_BASE_URL"):
        return "openrouter"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def _phase_output(phase_val: Any) -> Dict[str, Any]:
    if phase_val is None:
        return {}
    if hasattr(phase_val, "output"):
        return phase_val.output or {}
    if isinstance(phase_val, dict):
        return phase_val.get("output") or phase_val
    return {}


def _extract_verdict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the governance verdict + honest-degraded flags from a run result."""
    phases = result.get("phases", {}) if isinstance(result, dict) else {}
    gov = _phase_output(phases.get("democratic_vote", {}))
    verdict = gov.get("governance_verdict") or {}
    methods = dict(verdict.get("winners_per_method", {}))
    return {
        "decided_firsthand": bool(gov.get("governance_decided_firsthand")),
        "winner": verdict.get("condorcet_winner"),
        "n_methods": len(methods),
        "methods": methods,
        "consensus_rate": gov.get("consensus_rate"),
        "component_used": gov.get("component_used"),
    }


def _phase_status_table(result: Dict[str, Any]) -> List[Tuple[str, str, bool]]:
    """phase name → (status, component, degraded) for the per-phase honesty row."""
    phases = result.get("phases", {}) if isinstance(result, dict) else {}
    rows = []
    for name in sorted(phases):
        val = phases[name]
        status = getattr(val, "status", None)
        status_str = getattr(status, "value", str(status)) if status else "?"
        out = _phase_output(val)
        degraded = bool(out.get("degraded") or out.get(f"{name}_degraded"))
        comp = getattr(val, "component_used", None) or out.get("component_used") or "-"
        rows.append((name, f"{status_str}{'/DEGRADED' if degraded else ''}", comp))
    return rows


async def run_one(pid: str, text: str) -> Dict[str, Any]:
    """Run democratech on one proposition; return {verdict, phase_rows}."""
    from argumentation_analysis.workflows.democratech import run_deliberation

    result = await run_deliberation(text)
    return {
        "id": pid,
        "verdict": _extract_verdict(result),
        "phase_rows": _phase_status_table(result),
    }


async def run_demo(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    from synthetic_proposals import get_propositions

    props = get_propositions()
    items = list(props.items())[: (limit or len(props))]
    results = []
    for pid, meta in items:
        print(f"\n→ Deliberating {pid} ({meta['label']}) …", flush=True)
        res = await run_one(pid, meta["text"])
        res["label"] = meta["label"]
        results.append(res)
    return results


def _print_table(results: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 78)
    print(" DEMOCRATECH DELIBERATION — per-proposition verdict ")
    print("=" * 78)
    hdr = f"{'ID':<7} {'Firsthand':<10} {'Winner':<10} {'#Methods':<9} {'Consensus':<10}"
    print(hdr)
    print("-" * 78)
    for r in results:
        v = r["verdict"]
        firsthand = "YES" if v["decided_firsthand"] else "no"
        winner = v["winner"] or "—"
        consensus = (
            f"{v['consensus_rate']:.2f}"
            if isinstance(v["consensus_rate"], (int, float))
            else "—"
        )
        print(f"{r['id']:<7} {firsthand:<10} {str(winner):<10} "
              f"{v['n_methods']:<9} {consensus:<10}")
    print("-" * 78)
    n_decided = sum(1 for r in results if r["verdict"]["decided_firsthand"])
    print(f" {n_decided}/{len(results)} propositions decided firsthand "
          f"(anti-théâtre: undecided ones reported, never fabricated).")
    # Per-phase honesty row for the first proposition (representative).
    if results and results[0]["phase_rows"]:
        print("\n Per-phase status (first proposition, honest-degraded shown):")
        for name, status, comp in results[0]["phase_rows"]:
            print(f"   {name:<22} {status:<16} {comp}")
    print("=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description="Democratech deliberation demo.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit to N propositions (default: all 5).")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of the table.")
    args = parser.parse_args()

    provider = _ensure_api_key()
    if not provider:
        print("No LLM API key found (OPENAI_API_KEY or OPENROUTER_*). "
              "The demo needs a real LLM to deliberate. Skipping.",
              file=sys.stderr)
        return 2

    # Make the examples package importable for `from synthetic_proposals import …`.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    results = asyncio.run(run_demo(limit=args.limit))

    if args.json:
        # Strip the verbose phase_rows + methods for a compact JSON view.
        compact = [
            {
                "id": r["id"],
                "label": r["label"],
                **r["verdict"],
            }
            for r in results
        ]
        print(json.dumps(compact, indent=2, default=str, ensure_ascii=False))
    else:
        _print_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

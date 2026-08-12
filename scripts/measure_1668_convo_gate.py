"""#1668 item 5-bis — measure the conversational gate reach from a state snapshot.

The #1668 item 5-bis dispatch asked whether the conversational voie ever reaches
the ``("UNDERCUT", "REBUT", "REBUTTAL")`` gate in
``conversational_orchestrator.py:2859``. This script re-derives the verdict from
a saved state snapshot (produced by ``scripts/run_real_analysis.py --mode
conversational``) so the measure is reproducible without re-running the
expensive pipeline.

Privacy HARD: this script reads the state JSON, counts strategy values by
vocabulary class, and prints counts only. It NEVER prints, echoes, or stores
the corpus-derived strategy text itself. If you want to know which strategies
were emitted, look at the rendered report (gitignored, owner-only).

What it measures:
  - whether the conversational voie ran at all (counter_arguments populated)
  - how many counter_arguments[*].strategy match the gate vocabulary
  - how many do not, and what vocabularies they belong to (coarse class)
  - the Dung framework population (whether the gate is the only attack source
    or another branch — fallacies — also populated the framework; the
    R784/R796 finding)

Usage:
    python scripts/measure_1668_convo_gate.py STATE.json
    python scripts/measure_1668_convo_gate.py --json STATE.json
    python scripts/measure_1668_convo_gate.py --snapshots iter42_snapshots.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# The gate vocabulary as written in conversational_orchestrator.py:2859.
# The script is read-only over the vocabulary — if the producer changes,
# this string set is the single point of update.
GATE_STRATEGIES = frozenset({"UNDERCUT", "REBUT", "REBUTTAL"})

# Counter-argument strategy vocabulary (5 strategies from
# counter_argument/strategies.py:RhetoricalStrategy). Producers that emit
# these names are running in the opt-in enum path
# (invoke_callables.py:1185+1185 _COUNTER_STRATEGY_ALIASES) or via the
# deprecated fallback.
COUNTER_STRATEGIES = frozenset(
    {
        "socratic_questioning",
        "reductio_ad_absurdum",
        "analogical_counter",
        "authority_appeal",
        "statistical_evidence",
    }
)

# Debate-prompt vocabulary (collaborative_debate.py:72). Free-text producer.
DEBATE_STRATEGIES = frozenset(
    {
        "reductio ad absurdum",
        "counter-example",
        "distinction",
        "reformulation",
        "concession",
        "concession+pivot",
    }
)


def _vocab_class(strategy: str) -> str:
    """Classify a strategy value into one of the disjoint vocabularies.

    Returns one of: ``gate``, ``counter``, ``debate``, ``other`` (the bucket
    for free-form LLM-emitted names that don't match any closed vocab). The
    class is decided by the *vocabulary* used, not by whether the gate matched
    — a strategy in COUNTER_STRATEGIES is *not* in the gate's vocabulary even
    if it sounds similar to one of the 5 (e.g. ``reductio_ad_absurdum`` is not
    ``reductio ad absurdum`` and not ``REBUT``).
    """
    s = strategy.strip()
    su = s.upper()
    if su in GATE_STRATEGIES:
        return "gate"
    # Try the counter enum (case-insensitive — the producer normalizes via
    # _COUNTER_STRATEGY_ALIASES, so we accept any casing).
    if s.lower() in {x.lower() for x in COUNTER_STRATEGIES}:
        return "counter"
    if s.lower() in {x.lower() for x in DEBATE_STRATEGIES}:
        return "debate"
    return "other"


def measure_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Measure the gate reach from a state snapshot.

    Returns a dict with:
      - ``cas_present``: number of counter_arguments
      - ``strategies_total``: same (sanity)
      - ``strategies_distinct``: how many unique vocabulary values
      - ``gate_matched``: how many CAs match the gate vocabulary
      - ``gate_not_matched``: how many do not
      - ``by_vocab``: count per vocabulary class (gate/counter/debate/other)
      - ``dung_frameworks``: counts (arguments, attacks, extensions) per
        framework. The crucial point is whether attacks is non-zero — if so,
        the framework is populated despite the gate being inert (R784).
    """
    cas = state.get("counter_arguments") or []
    if not isinstance(cas, list):
        cas = []
    strats = [ca.get("strategy", "") for ca in cas if isinstance(ca, dict)]
    matched = sum(1 for s in strats if s.strip().upper() in GATE_STRATEGIES)
    by_vocab: Dict[str, int] = {"gate": 0, "counter": 0, "debate": 0, "other": 0}
    for s in strats:
        by_vocab[_vocab_class(s)] += 1

    dung_frameworks = state.get("dung_frameworks") or {}
    dung_summary: Dict[str, Dict[str, int]] = {}
    if isinstance(dung_frameworks, dict):
        for df_id, entry in dung_frameworks.items():
            if not isinstance(entry, dict):
                continue
            args = entry.get("arguments") or []
            attacks = entry.get("attacks") or []
            exts = entry.get("extensions") or {}
            dung_summary[str(df_id)] = {
                "arguments": len(args) if hasattr(args, "__len__") else 0,
                "attacks": len(attacks) if hasattr(attacks, "__len__") else 0,
                "extensions": len(exts) if hasattr(exts, "__len__") else 0,
            }

    return {
        "cas_present": len(cas),
        "strategies_total": len(strats),
        "strategies_distinct": len({s for s in strats if s}),
        "gate_matched": matched,
        "gate_not_matched": len(cas) - matched,
        "by_vocab": by_vocab,
        "dung_frameworks": dung_summary,
    }


def _looks_like_state(obj: Any) -> bool:
    """Detect a state export vs an LLM-Judge wrapper."""
    if not isinstance(obj, dict):
        return False
    if "state_snapshot" in obj and isinstance(obj["state_snapshot"], dict):
        return True
    return any(
        k in obj
        for k in (
            "dung_frameworks",
            "counter_arguments",
            "identified_arguments",
            "formal_synthesis_reports",
        )
    )


def _load(path: str, snapshots: bool, jsonl: bool) -> List[Dict[str, Any]]:
    states: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        if snapshots:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if _looks_like_state(obj):
                    states.append(obj.get("state_snapshot", obj))
        elif jsonl:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if _looks_like_state(obj):
                    states.append(obj.get("state_snapshot", obj))
        else:
            try:
                obj = json.load(f)
                if _looks_like_state(obj):
                    states.append(obj.get("state_snapshot", obj))
            except json.JSONDecodeError:
                f.seek(0)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if _looks_like_state(obj):
                        states.append(obj.get("state_snapshot", obj))
    return states


def _render(measurements: List[Dict[str, Any]], as_json: bool) -> str:
    if as_json:
        return json.dumps(measurements, ensure_ascii=False, indent=2)
    lines: List[str] = []
    for i, m in enumerate(measurements):
        lines.append(f"--- measurement #{i + 1} ---")
        lines.append(f"  counter_arguments: {m['cas_present']}")
        lines.append(
            f"  strategies: {m['strategies_total']} total, "
            f"{m['strategies_distinct']} distinct"
        )
        lines.append(
            f'  gate ("UNDERCUT","REBUT","REBUTTAL"): '
            f"{m['gate_matched']} matched / {m['gate_not_matched']} not matched"
        )
        bv = m["by_vocab"]
        lines.append(
            f"  vocab class: gate={bv['gate']}, counter={bv['counter']}, "
            f"debate={bv['debate']}, other={bv['other']}"
        )
        if m["dung_frameworks"]:
            lines.append("  dung_frameworks:")
            for df_id, summary in m["dung_frameworks"].items():
                lines.append(
                    f"    {df_id}: args={summary['arguments']}, "
                    f"attacks={summary['attacks']}, "
                    f"extensions={summary['extensions']}"
                )
        lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="+", help="state JSON file(s)")
    parser.add_argument(
        "--snapshots",
        action="store_true",
        help="paths are LLM-Judge iter*_snapshots.jsonl (one JSON per line)",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="paths are JSONL where each line is a state export",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    all_measurements: List[Dict[str, Any]] = []
    for path in args.paths:
        states = _load(path, args.snapshots, args.jsonl)
        if not states:
            print(f"{path}: no state payload found", file=sys.stderr)
            return 2
        for s in states:
            all_measurements.append(measure_state(s))

    print(_render(all_measurements, args.json))
    return 0


if __name__ == "__main__":
    sys.exit(main())

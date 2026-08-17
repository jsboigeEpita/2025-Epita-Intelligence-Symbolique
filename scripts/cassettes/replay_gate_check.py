"""Fail-loud gate for the LLM replay lane (#1603, DoD 4/5).

Reads the stats JSON written by ``replay_stats_plugin`` and enforces the
anti-vacuité contract of a replay run:

- ``live == 0`` — no outbound API call happened (anti-#1019);
- ``hit >= 1`` — the lane actually replayed from the cassettes. A lane
  that never consults the cache would be vacuously green;
- ``miss_replay == 0`` — every lookup found its cassette. A miss means a
  cassette is missing or its key drifted (the degenerate substitution of
  DoD 5); the lane must go red, not silently degrade — the extract phase
  swallows ``LLMCacheMiss`` into a heuristic fallback, so pytest alone
  stays green on a substituted cassette (constat D, #1603).

Usage::

    python -m scripts.cassettes.replay_gate_check <stats.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_REQUIRED_COUNTERS = ("live", "hit", "miss_record", "miss_replay")


def check(stats: Dict[str, Any]) -> List[str]:
    """Return the list of violations (empty == the lane replayed honestly)."""
    violations: List[str] = []
    if stats.get("live", 0) != 0:
        violations.append(
            f"live={stats['live']}: outbound API call(s) during replay — "
            "anti-#1019 (a cache miss fell through to the provider)"
        )
    if stats.get("hit", 0) < 1:
        violations.append(
            f"hit={stats.get('hit', 0)}: the lane never replayed from the "
            "cassettes — vacuous green (lane does not consult the cache)"
        )
    if stats.get("miss_replay", 0) != 0:
        violations.append(
            f"miss_replay={stats['miss_replay']}: replay cache miss(es) — "
            "a cassette is missing or its key drifted (degenerate "
            "substitution, or record/replay key asymmetry); the run "
            "degraded silently, not replayed"
        )
    return violations


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(
            "usage: python -m scripts.cassettes.replay_gate_check <stats.json>",
            file=sys.stderr,
        )
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(
            f"stats file not found: {path} — did the lane run with -p scripts.cassettes.replay_stats_plugin and REPLAY_GATE=1?",
            file=sys.stderr,
        )
        return 2
    stats = json.loads(path.read_text(encoding="utf-8"))
    missing = [c for c in _REQUIRED_COUNTERS if c not in stats]
    if missing:
        print(f"stats file {path} lacks counters: {missing}", file=sys.stderr)
        return 2

    print(
        f"[replay-gate] live={stats['live']} hit={stats['hit']} "
        f"miss_record={stats['miss_record']} miss_replay={stats['miss_replay']}"
    )
    violations = check(stats)
    if violations:
        print("REPLAY GATE FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("replay gate OK: live==0, hit>=1, miss_replay==0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

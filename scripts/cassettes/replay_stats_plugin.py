"""Pytest plugin: capture llm_cache counters for the replay lane (#1603).

Active only when ``REPLAY_GATE=1`` (explicit mode — a plain run is
untouched). At session start it resets the ``llm_cache`` counters so the
dump reflects THIS session only; at session finish it writes the counters
to ``REPLAY_STATS_OUT`` (JSON, default ``.cache/replay_stats.json``).

Mid-session resets are neutralized (measured on the first CI replay run
``32057140447``: the cache's own unit tests reset/flip the counters, so a
naive session-finish dump reported ``hit=0 miss_replay=1`` while the log
carried dozens of misses — the tail after the last reset, not the session).
The plugin wraps ``reset_cache_stats`` to accumulate the pre-reset values
into a session total first; tests still observe zeros after their reset
(unchanged outcome), the lane's dump survives. Observer-only, same
principle as the record-mode pass-through.

The enforcement lives in ``replay_gate_check.py``, a separate CLI step in
the lane workflow. A ``pytest_sessionfinish`` hook cannot reliably fail
the session's exit status, and embedding the check where it cannot fire
would make the gate look armed when it is not (family #1556: 0 propre is
indistinguishable from 0 débranché).

Load with::

    pytest ... -p scripts.cassettes.replay_stats_plugin
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_SESSION_TOTALS: dict[str, int] = {
    "hit": 0,
    "miss_record": 0,
    "miss_replay": 0,
    "live": 0,
}


def _accumulate(stats: dict[str, int]) -> None:
    for key in _SESSION_TOTALS:
        _SESSION_TOTALS[key] += int(stats.get(key, 0))


def pytest_sessionstart(session: Any) -> None:
    if os.getenv("REPLAY_GATE") != "1":
        return
    import argumentation_analysis.services.llm_cache as llm_cache

    llm_cache.reset_cache_stats()
    _orig_reset = llm_cache.reset_cache_stats

    def accumulating_reset() -> None:
        _accumulate(llm_cache.get_cache_stats())
        _orig_reset()

    llm_cache.reset_cache_stats = accumulating_reset


def pytest_sessionfinish(session: Any, exitstatus: Any) -> None:
    if os.getenv("REPLAY_GATE") != "1":
        return
    import argumentation_analysis.services.llm_cache as llm_cache

    _accumulate(llm_cache.get_cache_stats())
    stats = dict(_SESSION_TOTALS)
    out = Path(os.getenv("REPLAY_STATS_OUT", ".cache/replay_stats.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    # Loud one-line summary so the lane log carries the verdict even before
    # the gate check step runs.
    print(
        f"\n[replay-stats] live={stats['live']} hit={stats['hit']} "
        f"miss_record={stats['miss_record']} miss_replay={stats['miss_replay']}"
    )

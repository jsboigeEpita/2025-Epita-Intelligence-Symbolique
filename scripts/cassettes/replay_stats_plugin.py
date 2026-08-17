"""Pytest plugin: capture llm_cache counters for the replay lane (#1603).

Active only when ``REPLAY_GATE=1`` (explicit mode — a plain run is
untouched). At session start it resets the ``llm_cache`` counters so the
dump reflects THIS session only; at session finish it writes the counters
to ``REPLAY_STATS_OUT`` (JSON, default ``.cache/replay_stats.json``).

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


def pytest_sessionstart(session: Any) -> None:
    if os.getenv("REPLAY_GATE") != "1":
        return
    import argumentation_analysis.services.llm_cache as llm_cache

    llm_cache.reset_cache_stats()


def pytest_sessionfinish(session: Any, exitstatus: Any) -> None:
    if os.getenv("REPLAY_GATE") != "1":
        return
    import argumentation_analysis.services.llm_cache as llm_cache

    stats = llm_cache.get_cache_stats()
    out = Path(os.getenv("REPLAY_STATS_OUT", ".cache/replay_stats.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    # Loud one-line summary so the lane log carries the verdict even before
    # the gate check step runs.
    print(
        f"\n[replay-stats] live={stats['live']} hit={stats['hit']} "
        f"miss_record={stats['miss_record']} miss_replay={stats['miss_replay']}"
    )

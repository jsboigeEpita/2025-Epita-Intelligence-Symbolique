"""Stats-capture hardening tests for the replay lane plugin (#1603).

The first CI replay run (32057140447) proved the naive dump wrong: the
cache's own unit tests reset the counters mid-session, so the session-finish
file carried only the tail after the last reset (hit=0, miss_replay=1) while
the log carried dozens of misses. The plugin now wraps ``reset_cache_stats``
to accumulate pre-reset values into a session total.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from scripts.cassettes import replay_stats_plugin

_ZEROS: dict[str, int] = {
    "hit": 0,
    "miss_record": 0,
    "miss_replay": 0,
    "live": 0,
}


class _Session:
    """Minimal stand-in for the pytest Session object."""


def _set_counters(**values: int) -> None:
    import argumentation_analysis.services.llm_cache as llm_cache

    obj = llm_cache._cache_stats
    for key, val in values.items():
        setattr(obj, key, val)


def test_mid_session_reset_keeps_session_totals(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REPLAY_GATE", "1")
    out = tmp_path / "stats.json"
    monkeypatch.setenv("REPLAY_STATS_OUT", str(out))

    import argumentation_analysis.services.llm_cache as llm_cache

    original_reset = llm_cache.reset_cache_stats
    with patch.object(replay_stats_plugin, "_SESSION_TOTALS", dict(_ZEROS)):
        replay_stats_plugin.pytest_sessionstart(_Session())
        try:
            # Lane activity, then a test resets the counters (as the cache's
            # own unit tests do mid-session), then more lane activity.
            _set_counters(hit=3, miss_replay=2)
            llm_cache.reset_cache_stats()
            _set_counters(hit=5, miss_replay=1)
            llm_cache.reset_cache_stats()
            _set_counters(hit=8)
            replay_stats_plugin.pytest_sessionfinish(_Session(), exitstatus=0)
        finally:
            llm_cache.reset_cache_stats = original_reset

    dumped = json.loads(out.read_text(encoding="utf-8"))
    assert dumped["hit"] == 3 + 5 + 8
    assert dumped["miss_replay"] == 2 + 1
    # After their own reset, mid-session tests observe zeros — the observer
    # changes no outcome (verified at the second reset above: hit went 3→5
    # fresh, not 3→8).


def test_plugin_inactive_without_gate(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without REPLAY_GATE=1 the plugin touches nothing (plain runs)."""
    monkeypatch.delenv("REPLAY_GATE", raising=False)
    out = tmp_path / "stats.json"
    monkeypatch.setenv("REPLAY_STATS_OUT", str(out))

    import argumentation_analysis.services.llm_cache as llm_cache

    before = llm_cache.get_cache_stats()
    replay_stats_plugin.pytest_sessionstart(_Session())
    replay_stats_plugin.pytest_sessionfinish(_Session(), exitstatus=0)
    assert not out.exists()
    assert llm_cache.get_cache_stats() == before


def test_accumulate_sums_only_known_counters() -> None:
    with patch.object(replay_stats_plugin, "_SESSION_TOTALS", dict(_ZEROS)):
        replay_stats_plugin._accumulate({"hit": 2, "live": 1, "unrelated": 99})
        assert replay_stats_plugin._SESSION_TOTALS["hit"] == 2
        assert replay_stats_plugin._SESSION_TOTALS["live"] == 1
        assert "unrelated" not in replay_stats_plugin._SESSION_TOTALS

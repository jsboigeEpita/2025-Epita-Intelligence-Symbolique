"""Gate check tests for the LLM replay lane (#1603 DoD 4/5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.cassettes import replay_gate_check


def _ok() -> dict[str, int]:
    return {"live": 0, "hit": 7, "miss_record": 0, "miss_replay": 0}


def test_honest_replay_passes() -> None:
    assert replay_gate_check.check(_ok()) == []


def test_live_call_is_a_violation() -> None:
    stats = _ok() | {"live": 1}
    viol = replay_gate_check.check(stats)
    assert len(viol) == 1
    assert "live=1" in viol[0]


def test_zero_hits_is_a_violation() -> None:
    """Anti-vacuité (family #1556): a lane that never consults the cache
    is not a replay — hit must be >= 1."""
    stats = _ok() | {"hit": 0}
    viol = replay_gate_check.check(stats)
    assert len(viol) == 1
    assert "vacuous" in viol[0]


def test_replay_miss_is_a_violation() -> None:
    """DoD 5: a substituted (key-drifted) cassette makes the lane red —
    the extract phase swallows LLMCacheMiss into a heuristic fallback, so
    pytest alone stays green (constat D). The gate must not."""
    stats = _ok() | {"miss_replay": 21}
    viol = replay_gate_check.check(stats)
    assert len(viol) == 1
    assert "miss_replay=21" in viol[0]


def test_all_counters_violate_together() -> None:
    stats = _ok() | {"live": 3, "hit": 0, "miss_replay": 5}
    assert len(replay_gate_check.check(stats)) == 3


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ok_file = tmp_path / "ok.json"
    ok_file.write_text('{"live": 0, "hit": 3, "miss_record": 0, "miss_replay": 0}')
    assert replay_gate_check.main([str(ok_file)]) == 0

    bad_file = tmp_path / "bad.json"
    bad_file.write_text('{"live": 0, "hit": 0, "miss_record": 0, "miss_replay": 2}')
    assert replay_gate_check.main([str(bad_file)]) == 1

    assert replay_gate_check.main([str(tmp_path / "absent.json")]) == 2
    assert replay_gate_check.main([]) == 2

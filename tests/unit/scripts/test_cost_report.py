"""Unit tests for the record-run cost artifact (#1603 DoD 6)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import diskcache
import pytest

from scripts.cassettes import cost_report


def _seed_db(db_dir: Path, entries: Dict[str, Any]) -> None:
    db = diskcache.Cache(str(db_dir))
    try:
        for key, value in entries.items():
            db.set(key, value)
    finally:
        db.close()


def test_analyze_sums_raw_path_usage_and_counts_sk_path(tmp_path: Path) -> None:
    entries = {
        "a"
        * 64: {  # raw path — carries usage
            "model": "gpt-5-mini",
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        },
        "b"
        * 64: {  # raw path — usage absent
            "model": "gpt-5-mini",
        },
        "c"
        * 64: [  # SK path — list value, no usage
            {"role": "assistant", "content": "hello"},
        ],
    }
    _seed_db(tmp_path / "db", entries)

    report = cost_report.analyze(tmp_path / "db")

    assert report["total_requests"] == 3
    assert report["raw_path_requests"] == 2
    assert report["sk_path_requests"] == 1
    assert report["prompt_tokens"] == 100
    assert report["completion_tokens"] == 20
    assert report["est_usd"] is None  # no pricing env → token-only report


def test_analyze_estimates_usd_when_pricing_env_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PRICE_PER_1M_IN", "1.0")
    monkeypatch.setenv("LLM_PRICE_PER_1M_OUT", "4.0")
    _seed_db(
        tmp_path / "db",
        {"a" * 64: {"usage": {"prompt_tokens": 500_000, "completion_tokens": 250_000}}},
    )

    report = cost_report.analyze(tmp_path / "db")

    assert report["est_usd"] == pytest.approx(0.5 + 1.0)  # 0.5M*$1 + 0.25M*$4


def test_analyze_rejects_unexpected_value_type(tmp_path: Path) -> None:
    _seed_db(tmp_path / "db", {"a" * 64: 42})
    with pytest.raises(ValueError):
        cost_report.analyze(tmp_path / "db")


def test_analyze_empty_db(tmp_path: Path) -> None:
    _seed_db(tmp_path / "db", {})
    report = cost_report.analyze(tmp_path / "db")
    assert report["total_requests"] == 0
    assert report["prompt_tokens"] == 0
    assert report["completion_tokens"] == 0

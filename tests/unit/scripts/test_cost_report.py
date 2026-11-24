"""Unit tests for the record-run cost artifact (#1603 DoD 6)."""

from __future__ import annotations

import json
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


# --- #3686: the SK-path half of the usage ------------------------------------
#
# The report used to sum the raw-path half alone and print the SK-path entries
# as « usage unavailable, counted only ». The entries carry their usage: under
# ``metadata.usage`` of each item. Measured on two record runs (43684055967,
# 45351057154): 163 865 and 133 396 prompt tokens were outside the total and
# outside the token cap that reads it.

RAW_USAGE = {"prompt_tokens": 100, "completion_tokens": 20}
SK_USAGE = {"prompt_tokens": 50, "completion_tokens": 7}


def _sk_entry(usage: dict[str, int] | None, choices: int = 1) -> list[dict[str, Any]]:
    """One SK-path cache value: the ChatMessageContent list of one request.

    Semantic Kernel builds each choice's metadata from the choice and from the
    completion, ``_get_metadata_from_chat_response`` putting the completion's
    ``usage`` on every one of them. So ``choices`` items carry the same block
    ``choices`` times.
    """
    items = []
    for _ in range(choices):
        item: dict[str, Any] = {"role": "assistant", "content": "answer"}
        if usage is not None:
            item["metadata"] = {
                "id": "chatcmpl-0001",
                "created": 1,
                "system_fingerprint": None,
                "logprobs": None,
                "usage": dict(usage),
            }
        items.append(item)
    return items


def test_analyze_sums_the_usage_of_a_dict_entry_and_of_a_list_entry(
    tmp_path: Path,
) -> None:
    _seed_db(
        tmp_path / "db",
        {
            "a" * 64: {"model": "m", "usage": dict(RAW_USAGE)},  # raw path
            "b" * 64: _sk_entry(SK_USAGE),  # SK path
        },
    )

    report = cost_report.analyze(tmp_path / "db")

    assert report["prompt_tokens"] == 150
    assert report["completion_tokens"] == 27


def test_the_two_halves_are_read_apart(tmp_path: Path) -> None:
    _seed_db(
        tmp_path / "db",
        {
            "a" * 64: {"usage": dict(RAW_USAGE)},
            "b" * 64: _sk_entry(SK_USAGE),
            "c" * 64: _sk_entry(None),
        },
    )

    report = cost_report.analyze(tmp_path / "db")

    assert report["raw_path_requests"] == 1
    assert report["sk_path_requests"] == 2
    assert report["raw_path_prompt_tokens"] == 100
    assert report["raw_path_completion_tokens"] == 20
    assert report["sk_path_prompt_tokens"] == 50
    assert report["sk_path_completion_tokens"] == 7
    assert report["sk_path_entries_with_usage"] == 1
    assert report["prompt_tokens"] == 150
    assert report["completion_tokens"] == 27


def test_a_list_entry_is_one_request_so_its_usage_counts_once(tmp_path: Path) -> None:
    # Two choices of one completion: the same block twice is one request's.
    _seed_db(tmp_path / "db", {"b" * 64: _sk_entry(SK_USAGE, choices=2)})

    report = cost_report.analyze(tmp_path / "db")

    assert report["sk_path_requests"] == 1
    assert report["prompt_tokens"] == 50
    assert report["completion_tokens"] == 7


def test_a_list_entry_is_read_from_the_item_that_carries_the_usage(
    tmp_path: Path,
) -> None:
    value = _sk_entry(None, choices=1)
    value.append(_sk_entry(SK_USAGE)[0])
    _seed_db(tmp_path / "db", {"b" * 64: value})

    report = cost_report.analyze(tmp_path / "db")

    assert report["prompt_tokens"] == 50
    assert report["completion_tokens"] == 7


def test_the_usage_is_read_under_the_metadata_not_beside_it(tmp_path: Path) -> None:
    # The same counts at the item's top level are not where the block sits.
    _seed_db(
        tmp_path / "db",
        {"b" * 64: [{"role": "assistant", "content": "a", "usage": dict(SK_USAGE)}]},
    )

    report = cost_report.analyze(tmp_path / "db")

    assert report["prompt_tokens"] == 0
    assert report["completion_tokens"] == 0


def test_a_list_entry_without_usage_is_counted_and_named(tmp_path: Path) -> None:
    _seed_db(
        tmp_path / "db",
        {
            "a" * 64: {"usage": dict(RAW_USAGE)},
            "b" * 64: _sk_entry(None),
            "c" * 64: _sk_entry(None),
        },
    )

    report = cost_report.analyze(tmp_path / "db")

    assert report["sk_path_requests"] == 2
    assert report["sk_path_entries_with_usage"] == 0
    assert report["sk_path_entries_without_usage"] == ["b" * 16, "c" * 16]
    assert report["prompt_tokens"] == 100
    assert report["completion_tokens"] == 20


def test_the_entries_left_out_are_named_in_one_order_whatever_the_store(
    tmp_path: Path,
) -> None:
    # The store hands its keys back in database sort order (``Cache.iterkeys``:
    # ``ORDER BY key ASC``), whatever order they were written in; the names
    # come out in that order, and one store gives one report.
    keys = [chr(ord("b") + i) * 64 for i in range(12)]
    _seed_db(tmp_path / "db", {key: _sk_entry(None) for key in reversed(keys)})

    first = cost_report.analyze(tmp_path / "db")
    again = cost_report.analyze(tmp_path / "db")

    assert first["sk_path_entries_without_usage"] == [key[:16] for key in keys]
    assert first == again


def test_an_entry_with_usage_is_not_named_as_one_without(tmp_path: Path) -> None:
    _seed_db(tmp_path / "db", {"b" * 64: _sk_entry(SK_USAGE)})

    report = cost_report.analyze(tmp_path / "db")

    assert report["sk_path_entries_without_usage"] == []


def test_a_block_with_one_count_only_is_still_read(tmp_path: Path) -> None:
    _seed_db(
        tmp_path / "db",
        {
            "a" * 64: {"usage": {"prompt_tokens": 100}},
            "b" * 64: _sk_entry({"completion_tokens": 7}),
        },
    )

    report = cost_report.analyze(tmp_path / "db")

    assert report["prompt_tokens"] == 100
    assert report["completion_tokens"] == 7
    assert report["sk_path_entries_with_usage"] == 1


def test_the_dollar_estimate_covers_the_sk_path_half(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PRICE_PER_1M_IN", "1.0")
    monkeypatch.setenv("LLM_PRICE_PER_1M_OUT", "4.0")
    _seed_db(tmp_path / "db", {"b" * 64: _sk_entry(SK_USAGE)})

    report = cost_report.analyze(tmp_path / "db")

    assert report["est_usd"] == pytest.approx(50 / 1e6 * 1.0 + 7 / 1e6 * 4.0)


def test_the_json_the_cap_step_reads_carries_the_whole_total(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_db(
        tmp_path / "db",
        {"a" * 64: {"usage": dict(RAW_USAGE)}, "b" * 64: _sk_entry(SK_USAGE)},
    )

    code = cost_report.main([str(tmp_path / "db"), "--json"])

    out = capsys.readouterr().out
    assert code == 0
    report = json.loads(out)
    assert report["prompt_tokens"] + report["completion_tokens"] == 177


def test_the_report_names_the_entries_its_totals_leave_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_db(
        tmp_path / "db",
        {"a" * 64: {"usage": dict(RAW_USAGE)}, "b" * 64: _sk_entry(None)},
    )

    code = cost_report.main([str(tmp_path / "db")])

    out = capsys.readouterr().out
    assert code == 0
    assert "usage unavailable" not in out
    assert "b" * 16 in out
    assert "without usage" in out


def test_the_record_step_cap_reads_the_two_total_fields() -> None:
    # #3686 DoD 4: the cap step needs no edit — it sums the report's two
    # total fields. Pinned so that the two stay the totals of both halves.
    workflow = (
        Path(__file__).resolve().parents[3]
        / ".github"
        / "workflows"
        / "record-llm-cassettes.yml"
    ).read_text(encoding="utf-8")
    assert (
        "['prompt_tokens'] + json.load(open('cost_report.json'))['completion_tokens']"
        in workflow
    )

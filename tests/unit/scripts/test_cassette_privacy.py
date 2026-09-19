"""Privacy audit tests for LLM cassettes (#1603).

Covers the blocking rules in ``scripts/cassettes/privacy.py`` plus the
metadata-key exemption added for versioned model ids ("gpt-5-mini-2025-08-07"
must NOT trip the historical-date heuristic — it is a model version stamp,
not corpus prose).
"""

from __future__ import annotations

import pytest

from scripts.cassettes.privacy import audit_value


def test_forbidden_key_is_blocked() -> None:
    viol = audit_value({"raw_text": "secret", "value": "ok"}, source="t")
    assert any("forbidden key 'raw_text'" in v for v in viol)


def test_source_name_hint_is_blocked() -> None:
    viol = audit_value(
        {"content": "Cet argument reprend la position de Macron sur le sujet."},
        source="t",
    )
    assert any("source-name hint" in v for v in viol)


def test_historical_year_in_prose_is_blocked() -> None:
    viol = audit_value(
        {"content": "Le discours du 15 mars 1940 marque un tournant."},
        source="t",
    )
    assert any("historical-year hint" in v for v in viol)


def test_currency_amount_does_not_trip_date_heuristic() -> None:
    # Regression #1603 harvest: governance-scenario responses carry budget
    # figures ("€2000 to run an inter-city tournament", "un budget de 2000 €").
    # A monetary amount is not a date — the refusal was a false positive.
    assert (
        audit_value(
            {"content": "Position: Spend €2000 to run an inter-city tournament."},
            source="t",
        )
        == []
    )
    assert (
        audit_value(
            {"content": "Le club propose un budget de 2000 € pour l'année."},
            source="t",
        )
        == []
    )


def test_currency_word_amount_does_not_trip_date_heuristic() -> None:
    # Regression #2300: the #1603 symbols-only exemption refused every
    # cassette of the two deliberation tests on « 2000 euros » — the natural
    # French spelling of an amount — blocking the replay band on a measured
    # false-positive class. A denomination word glued to the digits is an
    # amount, not a date.
    assert (
        audit_value(
            {"content": "Organiser un tournoi pour 2000 euros au club."},
            source="t",
        )
        == []
    )
    assert (
        audit_value(
            {"content": "The grant of 3000 dollars covers both options."},
            source="t",
        )
        == []
    )


def test_year_without_currency_marker_stays_blocked() -> None:
    # The exemption requires a currency marker glued to the digits: a bare
    # year in prose, or a year followed by anything else, keeps tripping —
    # that is the actual political-date leak channel.
    viol = audit_value(
        {"content": "Le plan fut adopté, comme en 2021 ailleurs, après 2017."},
        source="t",
    )
    assert any("historical-year hint 2021" in v for v in viol)
    assert any("historical-year hint 2017" in v for v in viol)
    # A year followed by a non-currency word is NOT an amount.
    viol2 = audit_value(
        {"content": "Le rapport 2000 annuel fut publié."},
        source="t",
    )
    assert any("historical-year hint 2000" in v for v in viol2)


def test_versioned_model_id_does_not_trip_date_heuristic() -> None:
    # Regression #1603: raw-path cassettes carry model="gpt-5-mini-2025-08-07"
    # (>= 20 chars, contains the current year) — the metadata exemption must
    # keep the whole cassette clean.
    raw = {
        "model": "gpt-5-mini-2025-08-07",
        "id": "chatcmpl-ABC2025def",
        "created": 1755436800,
        "object": "chat.completion",
        "system_fingerprint": "fp_2025_abc",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Réponse synthétique."},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    assert audit_value(raw, source="t") == []


def test_content_inside_choices_is_still_audited() -> None:
    raw = {
        "model": "gpt-5-mini-2025-08-07",
        "choices": [
            {"message": {"role": "assistant", "content": "Macron a parlé en 1940."}}
        ],
    }
    viol = audit_value(raw, source="t")
    assert any("source-name hint" in v for v in viol)
    assert any("historical-year hint" in v for v in viol)

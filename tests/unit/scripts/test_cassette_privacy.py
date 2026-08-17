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

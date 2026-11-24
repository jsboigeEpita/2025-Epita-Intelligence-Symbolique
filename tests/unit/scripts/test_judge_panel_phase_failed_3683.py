"""#3683 — the judge's health table counts a cut read, not a healthy arm.

Measured (issue #3683): ``_persona_read_failed`` returns ``False`` on a
``no_llm`` record without ``degraded`` — the shape of the 12 recorded
``coverage_review`` records whose phase died at its 300 s budget — and also
on ``{"status": "timeout"}``, the status #3681 now writes for the first
reading. ``FAILED_PERSONA_STATUSES`` knew only ``llm_error`` and
``parse_error``. A document whose read was CUT therefore got no
``persona_failed`` row: the table called the arm healthy.

The contract pinned here:

* ``timeout`` and ``phase_failed`` — the two statuses #3681 (item 42) and
  #3683 (item 43) write on an executor-level failure — are read failures,
  for the four keys the instrument already reads;
* ``no_llm``, ``empty_input``, ``no_reading``, ``no_document`` remain honest
  absences and name nothing;
* ``cross_passage_consistency`` keeps its own vocabulary and stays out of
  the persona census (#3599): a cut check is a named absence in the note,
  not a failed persona read;
* nothing becomes a refusal: ``DEGRADED_ARM_REFUSAL_THRESHOLD`` is
  unchanged and ``pipeline_degraded`` does not learn the flag.

Born red on ``main`` ``de05227f3``: the eight per-key witnesses fail. The
controls legitimately pass before and after. No network, no dataset, no key:
``arm_health`` reads a synthetic state dict. **Zero paid call.**
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset import judge_panel as jp  # noqa: E402

ACTS_RENDERED = {
    "act1_framing": "Acte I rendu sur ce document.",
    "act2_narrative": "Acte II rendu sur ce document.",
    "act3_conclusion": "Acte III rendu sur ce document.",
}

# The four keys the instrument reads, and the executor's own message each
# record carries after #3683 — a cut is a defect class of its own, with its
# budget named, never « no LLM, by design ».
CUT_RECORDS = {
    "strategic_read": {
        "players": [],
        "options": [],
        "preferences": {},
        "reading": "",
        "game": {},
        "status": "timeout",
        "basis": "model_knowledge",
        "error": "TimeoutError: phase 'strategist' exceeded its 180s budget",
    },
    "historical_context": {
        "situation": "",
        "items": [],
        "status": "timeout",
        "basis": "model_knowledge",
        "error": "TimeoutError: phase 'historian' exceeded its 120s budget",
    },
    "defining_moves": {
        "moves": [],
        "dropped_quotes": 0,
        "status": "timeout",
        "error": "TimeoutError: phase 'first_reading' exceeded its 180s budget",
        "read_scope": {},
        "basis": "first_reading",
    },
    "coverage_review": {
        "status": "timeout",
        "items": [],
        "examined": 0,
        "dropped": {},
        "reason": "TimeoutError: phase 'coverage' exceeded its 300s budget",
        "basis": "coverage_review",
    },
}


def _health(persona: dict) -> dict:
    return jp.arm_health({"state": {**ACTS_RENDERED, **persona}})


class TestACutReadIsNamedOnEveryKey:
    @pytest.mark.parametrize("key,record", sorted(CUT_RECORDS.items()))
    def test_a_timeout_record_names_the_read(self, key: str, record: dict):
        health = _health({key: record})
        assert health["persona_failed"] == [jp.PERSONA_READ_STATUS_KEYS[key]], health

    @pytest.mark.parametrize("key,record", sorted(CUT_RECORDS.items()))
    def test_a_phase_failed_record_names_the_read(self, key: str, record: dict):
        health = _health({key: dict(record, status="phase_failed")})
        assert health["persona_failed"] == [jp.PERSONA_READ_STATUS_KEYS[key]], health

    def test_the_two_statuses_are_named_constants(self):
        """The instrument reads the vocabulary the executor writes, in one
        place — not a literal scattered at the call sites."""
        assert "timeout" in jp.FAILED_PERSONA_STATUSES
        assert "phase_failed" in jp.FAILED_PERSONA_STATUSES
        assert "llm_error" in jp.FAILED_PERSONA_STATUSES
        assert "parse_error" in jp.FAILED_PERSONA_STATUSES


class TestTheHonestAbsencesAreStillNotFailures:
    @pytest.mark.parametrize("key", sorted(CUT_RECORDS))
    @pytest.mark.parametrize(
        "status", ("no_llm", "empty_input", "no_reading", "no_document")
    )
    def test_an_honest_absence_names_nothing(self, key: str, status: str):
        assert _health({key: {"status": status}})["persona_failed"] == []

    @pytest.mark.parametrize("key", sorted(CUT_RECORDS))
    def test_a_successful_read_names_nothing(self, key: str):
        assert _health({key: {"status": "ok"}})["persona_failed"] == []

    def test_a_cut_read_without_a_degraded_marker_is_still_named(self):
        """The measured shape: no ``degraded`` key at all, because the
        executor wrote the record, not the persona's invoke."""
        record = CUT_RECORDS["coverage_review"]
        assert "degraded" not in record
        assert _health({"coverage_review": record})["persona_failed"] == [
            "coverage_review"
        ]


class TestTheScopeDoesNotMove:
    def test_cross_passage_stays_out_of_the_persona_census(self):
        """A cut check names its cause in the note; it is not a persona."""
        for reason in ("phase_budget_exceeded", "phase_failed"):
            health = _health(
                {
                    "cross_passage_consistency": {
                        "status": "unreachable",
                        "reason": reason,
                    }
                }
            )
            assert health["persona_failed"] == [], health

    def test_a_cut_read_is_not_a_refusal(self):
        health = _health({"coverage_review": CUT_RECORDS["coverage_review"]})
        assert health["pipeline_degraded"] is False
        assert jp.DEGRADED_ARM_REFUSAL_THRESHOLD == 2

    def test_the_keys_read_are_the_four_of_3599(self):
        assert jp.PERSONA_READ_STATUS_KEYS == {
            "strategic_read": "strategist",
            "historical_context": "historian",
            "defining_moves": "first_reading",
            "coverage_review": "coverage_review",
        }

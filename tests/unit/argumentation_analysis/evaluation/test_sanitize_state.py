"""Tests for argumentation_analysis.evaluation.sanitize_state."""

import json
from pathlib import Path

import pytest

from argumentation_analysis.evaluation.sanitize_state import sanitize_state

GOLDEN_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "golden"
    / "fixtures"
    / "spectacular"
    / "doc_a_golden.json"
)


@pytest.fixture
def golden_state():
    with open(GOLDEN_FIXTURE, encoding="utf-8") as f:
        data = json.load(f)
    return data["state_snapshot"]


class TestSanitizeTopLevel:
    def test_raw_text_stripped(self, golden_state):
        result = sanitize_state(golden_state)
        assert "raw_text" not in result

    def test_full_text_stripped(self):
        state = {"full_text": "sensitive", "count": 5}
        result = sanitize_state(state)
        assert "full_text" not in result
        assert result["count"] == 5

    def test_source_name_stripped(self):
        state = {"source_name": "Secret Speaker", "score": 0.9}
        result = sanitize_state(state)
        assert "source_name" not in result

    def test_all_sensitive_fields_stripped(self):
        state = {
            "raw_text": "x",
            "full_text": "x",
            "full_text_segment": "x",
            "raw_text_snippet": "x",
            "source_name": "x",
            "document_name": "x",
            "author": "x",
            "date_iso": "x",
            "url": "x",
        }
        result = sanitize_state(state)
        for field in state:
            assert field not in result


class TestSanitizeOpaqueReplace:
    def test_source_id_opaque(self):
        state = {"source_id": "Real Name"}
        result = sanitize_state(state)
        assert result["source_id"] != "Real Name"
        assert len(result["source_id"]) == 8

    def test_source_id_stable(self):
        state = {"source_id": "Same Name"}
        a = sanitize_state(state)
        b = sanitize_state(state)
        assert a["source_id"] == b["source_id"]


class TestSanitizePreserved:
    def test_counts_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        assert "summary" not in result  # top-level summary is outside state_snapshot
        # Check that analysis_tasks (counts) are preserved
        if "analysis_tasks" in golden_state:
            assert "analysis_tasks" in result

    def test_scores_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        if "argument_quality_scores" in golden_state:
            assert "argument_quality_scores" in result
            assert (
                result["argument_quality_scores"]
                == golden_state["argument_quality_scores"]
            )

    def test_structures_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        # Dung frameworks should be fully preserved (no text)
        if "dung_frameworks" in golden_state:
            assert "dung_frameworks" in result
            assert result["dung_frameworks"] == golden_state["dung_frameworks"]

    def test_belief_data_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        if "jtms_beliefs" in golden_state:
            assert "jtms_beliefs" in result


class TestSanitizeNarrative:
    def test_narrative_replaced_with_length(self, golden_state):
        result = sanitize_state(golden_state)
        if "narrative_synthesis" in golden_state:
            narr = result["narrative_synthesis"]
            assert isinstance(narr, dict)
            assert "length" in narr
            assert narr["length"] == len(golden_state["narrative_synthesis"])
            assert narr["stripped"] is True


class TestSanitizeCounterArguments:
    def test_counter_content_stripped(self, golden_state):
        result = sanitize_state(golden_state)
        if "counter_arguments" in result:
            for ca in result["counter_arguments"]:
                assert "counter_content" not in ca
                assert "generated_text" not in ca
                # strategy and strength should survive
                assert "strategy" in ca


class TestSanitizeIdempotence:
    def test_idempotent(self):
        state = {
            "raw_text": "secret",
            "source_id": "Name",
            "narrative_synthesis": "A long narrative paragraph.",
            "counter_arguments": [
                {"strategy": "reductio", "counter_content": "text", "strength": 0.8}
            ],
            "score": 0.9,
        }
        first = sanitize_state(state)
        second = sanitize_state(first)
        # Stripped fields stay stripped; scores survive
        assert first["score"] == second["score"] == 0.9
        assert "raw_text" not in second

    def test_idempotent_on_golden(self, golden_state):
        first = sanitize_state(golden_state)
        second = sanitize_state(first)
        # Scores and structures must survive both passes
        assert first["argument_quality_scores"] == second["argument_quality_scores"]
        assert first["dung_frameworks"] == second["dung_frameworks"]


class TestSanitizeIdentifiedArguments:
    def test_arguments_text_stripped(self):
        state = {
            "identified_arguments": {
                "arg1": "Sensitive argument text",
                "arg2": "Another text",
            }
        }
        result = sanitize_state(state)
        assert "identified_arguments" in result
        for v in result["identified_arguments"].values():
            assert isinstance(v, dict)
            assert v["text_stripped"] is True

    def test_non_string_values_preserved(self):
        state = {
            "identified_arguments": {
                "arg1": {"score": 0.9, "type": "premise"},
            }
        }
        result = sanitize_state(state)
        assert result["identified_arguments"]["arg1"] == {
            "score": 0.9,
            "type": "premise",
        }

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


# ---------------------------------------------------------------------------
# Epic #1258 Track 3 (#1261) — export guard must be watertight on a
# de-anonymized state (real names + readable symbols live in the working
# state; this is the boundary where they are scrubbed).
# ---------------------------------------------------------------------------

# A single nominative marker planted in every NL-bearing field. If it survives
# sanitize_state, the guard leaks. This is the "thé au polonium" test.
LEAK = "NominativeLeakToken"


def _deanonymized_state() -> dict:
    """A synthetic de-anonymized state with LEAK planted in every NL field."""
    return {
        # Opaque-replace (top-level identifier)
        "source_id": LEAK,
        # Narrative fields (strings -> {length, stripped})
        "narrative_synthesis": f"{LEAK} narrative synthesis text",
        "act1_framing": f"{LEAK} act one framing",
        "act2_narrative": f"{LEAK} act two narrative",
        "act3_conclusion": f"{LEAK} act three conclusion",
        "final_conclusion": f"{LEAK} final conclusion",
        # Dict-of-dicts (nominative sub-key dropped)
        "identified_fallacies": {
            "fallacy_1": {
                "type": "ad_hominem",
                "justification": LEAK,
                "family": "relevance",
            }
        },
        "belief_sets": {
            "pl_bs_1": {"logic_type": "PL", "content": f"{LEAK} belief set content"}
        },
        # List-of-dicts (nominative sub-keys dropped)
        "counter_arguments": [
            {
                "id": "ca_1",
                "strategy": "reductio",  # must survive
                "counter_content": LEAK,
                "original_argument": LEAK,
                "generated_text": LEAK,
            }
        ],
        "extracts": [{"id": "extract_1", "name": "n", "content": LEAK}],
        "debate_transcripts": [
            {
                "id": "debate_1",
                "topic": LEAK,
                "proponent_move": LEAK,
                "opponent_move": LEAK,
            }
        ],
        "transcription_segments": [{"id": "ts_1", "text": LEAK, "speaker": LEAK}],
        "neural_fallacy_scores": [{"id": "nf_1", "label": "x", "text_segment": LEAK}],
        "analysis_trace": [{"phase": "p", "agent": "a", "summary": LEAK}],
        "nl_to_logic_translations": [
            {
                "id": "nll_1",
                "original_text": LEAK,
                "formula": "p & q",
                "variables": {"p": LEAK, "q": LEAK},  # symbol_mapping
            }
        ],
        "semantic_index_refs": [{"id": "si_1", "query": LEAK, "snippet": LEAK}],
        "formal_synthesis_reports": [{"id": "fsyn_1", "summary": LEAK}],
        # Struct-valued NL field (reduced to counts)
        "stakes_and_stakeholders": {
            "stakes": [LEAK, LEAK],
            "stakeholders": [LEAK],
            "rhetorical_register": LEAK,
            "discursive_arena": LEAK,
        },
        # Preserved aggregates (must survive untouched, no token anyway)
        "argument_quality_scores": {"arg_1": {"overall": 5.0}},
        "dung_frameworks": {"dung_1": {"arguments": ["x"], "attacks": []}},
        "score": 0.9,
    }


class TestSanitizeDeAnonymizedState:
    """The guard must leave zero nominative content on a real-name state."""

    def test_no_nominative_leak_anywhere(self):
        result = sanitize_state(_deanonymized_state())
        blob = json.dumps(result, ensure_ascii=False)
        assert LEAK not in blob, f"Nominative leak detected in sanitized state: {blob}"

    def test_aggregates_survive(self):
        result = sanitize_state(_deanonymized_state())
        # Quantitative aggregates must survive the scrub.
        assert result["argument_quality_scores"]["arg_1"]["overall"] == 5.0
        assert result["dung_frameworks"] == {
            "dung_1": {"arguments": ["x"], "attacks": []}
        }
        assert result["score"] == 0.9
        # strategy survived counter_arguments scrub.
        assert result["counter_arguments"][0]["strategy"] == "reductio"

    def test_idempotent_on_deanonymized(self):
        first = sanitize_state(_deanonymized_state())
        second = sanitize_state(first)
        assert json.dumps(second, ensure_ascii=False).count(LEAK) == 0


class TestSanitizeNarrativeActs:
    def test_acts_replaced_with_length(self):
        for field in ("act1_framing", "act2_narrative", "act3_conclusion"):
            state = {field: f"{LEAK} content here"}
            result = sanitize_state(state)
            assert isinstance(result[field], dict)
            assert result[field]["length"] == len(f"{LEAK} content here")
            assert result[field]["stripped"] is True

    def test_final_conclusion_replaced_with_length(self):
        state = {"final_conclusion": f"{LEAK} the conclusion"}
        result = sanitize_state(state)
        assert isinstance(result["final_conclusion"], dict)
        assert result["final_conclusion"]["stripped"] is True

    def test_none_conclusion_left_as_none(self):
        state = {"final_conclusion": None}
        result = sanitize_state(state)
        assert result["final_conclusion"] is None


class TestSanitizeDictOfDicts:
    def test_fallacy_justification_dropped(self):
        state = {
            "identified_fallacies": {
                "f1": {"type": "ad_hominem", "justification": LEAK, "family": "x"}
            }
        }
        result = sanitize_state(state)
        entry = result["identified_fallacies"]["f1"]
        assert "justification" not in entry
        assert entry["type"] == "ad_hominem"  # structure preserved

    def test_belief_set_content_dropped(self):
        state = {"belief_sets": {"bs1": {"logic_type": "PL", "content": LEAK}}}
        result = sanitize_state(state)
        entry = result["belief_sets"]["bs1"]
        assert "content" not in entry
        assert entry["logic_type"] == "PL"


class TestSanitizeLists:
    def test_extracts_content_dropped(self):
        # Regression: extracts was registered with an empty text-key set, so
        # nothing was scrubbed. content must now be removed.
        state = {"extracts": [{"id": "e1", "name": "n", "content": LEAK}]}
        result = sanitize_state(state)
        assert "content" not in result["extracts"][0]
        assert result["extracts"][0]["name"] == "n"

    def test_transcription_text_and_speaker_dropped(self):
        state = {
            "transcription_segments": [
                {"id": "t1", "text": LEAK, "speaker": LEAK, "start_time": 0.0}
            ]
        }
        result = sanitize_state(state)
        seg = result["transcription_segments"][0]
        assert "text" not in seg
        assert "speaker" not in seg
        assert seg["start_time"] == 0.0

    def test_analysis_trace_summary_dropped(self):
        state = {"analysis_trace": [{"phase": "p", "agent": "a", "summary": LEAK}]}
        result = sanitize_state(state)
        assert "summary" not in result["analysis_trace"][0]
        assert result["analysis_trace"][0]["agent"] == "a"


class TestSanitizeSymbolMapping:
    def test_variables_opacified(self):
        state = {
            "nl_to_logic_translations": [
                {
                    "id": "n1",
                    "original_text": LEAK,
                    "formula": "p & q",
                    "variables": {"p": "rain is wet", "q": "street wet"},
                }
            ]
        }
        result = sanitize_state(state)
        entry = result["nl_to_logic_translations"][0]
        # original_text dropped
        assert "original_text" not in entry
        # atom keys preserved, NL meanings opacified (8-char hex), no leak
        variables = entry["variables"]
        assert set(variables.keys()) == {"p", "q"}
        assert all(isinstance(v, str) and len(v) == 8 for v in variables.values())
        assert "rain" not in json.dumps(variables)


class TestSanitizeStakes:
    def test_stakes_reduced_to_counts(self):
        state = {
            "stakes_and_stakeholders": {
                "stakes": [LEAK, LEAK, LEAK],
                "stakeholders": [LEAK],
                "rhetorical_register": LEAK,
                "discursive_arena": LEAK,
            }
        }
        result = sanitize_state(state)
        summary = result["stakes_and_stakeholders"]
        assert summary["stakes_count"] == 3
        assert summary["stakeholders_count"] == 1
        assert summary["has_rhetorical_register"] is True
        assert summary["has_discursive_arena"] is True
        assert summary["stripped"] is True
        assert LEAK not in json.dumps(summary)

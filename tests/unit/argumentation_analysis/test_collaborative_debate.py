"""Tests for the collaborative multi-agent debate pipeline (#175).

Validates:
- Agent role definitions and prompt structure
- JSON response parsing (clean, fenced, malformed)
- Fallback when no API key is available
- State writer populates debate transcripts and workflow results
- Full collaborative invoke with mocked LLM responses
- Workflow builder produces correct phase structure
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.orchestration.collaborative_debate import (
    COLLABORATIVE_ROLES,
    _fallback_collaborative,
    _invoke_collaborative_analysis,
    _parse_json_response,
    _write_collaborative_to_state,
    build_collaborative_analysis_workflow,
)

# --- Role definitions ---


class TestCollaborativeRoles:
    def test_all_roles_defined(self):
        expected = {"critic", "validator", "devils_advocate", "synthesizer"}
        assert set(COLLABORATIVE_ROLES.keys()) == expected

    def test_each_role_has_required_fields(self):
        for role_name, role_def in COLLABORATIVE_ROLES.items():
            assert "name" in role_def, f"Missing name for {role_name}"
            assert "system_prompt" in role_def, f"Missing system_prompt for {role_name}"
            assert (
                len(role_def["system_prompt"]) > 50
            ), f"System prompt too short for {role_name}"

    def test_roles_request_json_output(self):
        for role_name, role_def in COLLABORATIVE_ROLES.items():
            assert (
                "JSON" in role_def["system_prompt"]
            ), f"Role {role_name} should request JSON output"


# --- JSON parsing ---


class TestJsonParsing:
    def test_clean_json(self):
        raw = '{"key": "value", "number": 42}'
        result = _parse_json_response(raw, "test")
        assert result == {"key": "value", "number": 42}

    def test_json_with_markdown_fence(self):
        raw = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result = _parse_json_response(raw, "test")
        assert result == {"key": "value"}

    def test_json_with_generic_fence(self):
        raw = 'Text\n```\n{"result": true}\n```'
        result = _parse_json_response(raw, "test")
        assert result == {"result": True}

    def test_json_embedded_in_text(self):
        raw = 'Here is my analysis: {"score": 4.5, "valid": true} end.'
        result = _parse_json_response(raw, "test")
        assert result["score"] == 4.5

    def test_malformed_json_returns_raw(self):
        raw = "This is not JSON at all"
        result = _parse_json_response(raw, "test_role")
        assert result["parse_error"] is True
        assert result["role"] == "test_role"
        assert "This is not" in result["raw_response"]


# --- Fallback (no API key) ---


class TestFallbackCollaborative:
    def test_fallback_returns_valid_structure(self):
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument"},
                    {"text": "Second argument"},
                ]
            }
        }
        result = _fallback_collaborative("test text", context)
        assert result["interaction_type"] == "fallback_heuristic"
        assert result["final_quality_score"] == 3.0
        assert len(result["surviving_arguments"]) == 2
        assert result["agents_involved"] == []

    def test_fallback_empty_arguments(self):
        result = _fallback_collaborative("test text", {})
        assert result["surviving_arguments"] == []
        assert result["interaction_type"] == "fallback_heuristic"


# --- State writer ---


class TestStateWriter:
    def test_writes_debate_transcript(self):
        state = MagicMock()
        state.add_debate_transcript = MagicMock(return_value="debate_1")
        state.set_workflow_results = MagicMock()

        output = {
            "agent_outputs": {
                "critic": {"critiques": [], "overall_rigor": 3},
                "validator": {"validations": [], "overall_validity": 0.7},
            },
            "final_quality_score": 4.0,
            "new_insights": ["insight 1"],
            "surviving_arguments": [{"argument": "A1", "confidence": 0.8}],
            "defeated_arguments": [],
            "agents_involved": ["critic", "validator"],
        }

        _write_collaborative_to_state(output, state, {})

        state.add_debate_transcript.assert_called_once()
        call_args = state.add_debate_transcript.call_args
        assert call_args[1]["topic"] == "collaborative_multi_agent_analysis"
        assert len(call_args[1]["exchanges"]) == 2

        state.set_workflow_results.assert_called_once()
        wf_args = state.set_workflow_results.call_args
        assert wf_args[0][0] == "collaborative_analysis"
        assert wf_args[0][1]["final_quality_score"] == 4.0

    def test_handles_none_output(self):
        state = MagicMock()
        _write_collaborative_to_state(None, state, {})
        state.add_debate_transcript.assert_not_called()

    def test_handles_empty_dict(self):
        state = MagicMock()
        _write_collaborative_to_state({}, state, {})
        # Empty dict is falsy — should not write
        state.add_debate_transcript.assert_not_called()

    def test_skips_error_outputs(self):
        state = MagicMock()
        state.add_debate_transcript = MagicMock(return_value="debate_1")
        state.set_workflow_results = MagicMock()

        output = {
            "agent_outputs": {
                "critic": {"error": "LLM timeout", "role": "critic"},
                "validator": {"validations": [], "overall_validity": 0.5},
            },
            "final_quality_score": 2.0,
            "new_insights": [],
            "surviving_arguments": [],
            "defeated_arguments": [],
            "agents_involved": ["critic", "validator"],
        }

        _write_collaborative_to_state(output, state, {})
        call_args = state.add_debate_transcript.call_args
        # Only validator should be in exchanges (critic had error)
        assert len(call_args[1]["exchanges"]) == 1


# --- Full invoke with mocked LLM ---


def _mock_llm_response(content: str):
    """Create a mock OpenAI response."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


CRITIC_RESPONSE = json.dumps(
    {
        "critiques": [
            {
                "argument": "A1",
                "weakness": "Lacks empirical evidence",
                "severity": "medium",
                "suggestion": "Add data sources",
            }
        ],
        "overall_rigor": 3,
        "reasoning": "Arguments need more evidence",
    }
)

VALIDATOR_RESPONSE = json.dumps(
    {
        "validations": [
            {
                "argument": "A1",
                "evidence_status": "mixed",
                "logical_validity": "valid",
                "confidence": 0.6,
                "evidence_notes": "Some support found",
            }
        ],
        "overall_validity": 0.6,
        "reasoning": "Logically sound but evidence is mixed",
    }
)

DA_RESPONSE = json.dumps(
    {
        "counter_arguments": [
            {
                "target": "A1",
                "strategy": "counter-example",
                "counter": "Consider case X where this fails",
                "strength": "moderate",
            }
        ],
        "most_vulnerable": "A1",
        "reasoning": "A1 can be challenged with real counter-examples",
    }
)

SYNTHESIS_RESPONSE = json.dumps(
    {
        "surviving_arguments": [
            {
                "argument": "A1",
                "confidence": 0.65,
                "survived_challenges": ["logical validity check"],
            }
        ],
        "defeated_arguments": [],
        "new_insights": ["Evidence quality matters more than logical form"],
        "consensus_areas": ["A1 is logically valid"],
        "unresolved_disputes": ["empirical support level"],
        "final_quality_score": 4,
        "reasoning": "A1 survives but needs stronger evidence",
    }
)


class TestInvokeCollaborativeAnalysis:
    @pytest.mark.asyncio
    async def test_full_collaborative_flow(self):
        """Test the full 4-agent collaborative flow with mocked LLM."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _mock_llm_response(CRITIC_RESPONSE),
                _mock_llm_response(VALIDATOR_RESPONSE),
                _mock_llm_response(DA_RESPONSE),
                _mock_llm_response(SYNTHESIS_RESPONSE),
            ]
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Education spending correlates with economic growth"},
                    {"text": "Countries with higher education invest more"},
                ]
            },
            "phase_quality_output": {
                "per_argument_scores": {
                    "arg_1": {"note_finale": 6.5},
                    "arg_2": {"note_finale": 5.0},
                }
            },
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), patch(
            "openai.AsyncOpenAI",
            return_value=mock_client,
        ):
            result = await _invoke_collaborative_analysis("test text", context)

        assert result["interaction_type"] == "sequential_collaborative"
        assert result["final_quality_score"] == 4
        assert len(result["new_insights"]) == 1
        assert len(result["surviving_arguments"]) == 1
        assert len(result["agents_involved"]) == 4

        # Verify all 4 LLM calls were made
        assert mock_client.chat.completions.create.call_count == 4

    @pytest.mark.asyncio
    async def test_no_api_key_uses_fallback(self):
        """Without API key, should use heuristic fallback."""
        context = {"phase_extract_output": {"arguments": [{"text": "Test argument"}]}}

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            result = await _invoke_collaborative_analysis("test text", context)

        assert result["interaction_type"] == "fallback_heuristic"

    @pytest.mark.asyncio
    async def test_handles_llm_failure_gracefully(self):
        """If one agent fails, the others should still run."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("API timeout"),  # Critic fails
                _mock_llm_response(VALIDATOR_RESPONSE),
                _mock_llm_response(DA_RESPONSE),
                _mock_llm_response(SYNTHESIS_RESPONSE),
            ]
        )

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Test argument for resilience testing"}]
            }
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), patch(
            "openai.AsyncOpenAI",
            return_value=mock_client,
        ):
            result = await _invoke_collaborative_analysis("test text", context)

        # Should still complete — critic output will have error
        assert "critic" in result["agent_outputs"]
        assert "error" in result["agent_outputs"]["critic"]
        assert result["interaction_type"] == "sequential_collaborative"

    @pytest.mark.asyncio
    async def test_sentence_split_fallback(self):
        """When no arguments in extract, should fall back to sentence splitting."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _mock_llm_response(CRITIC_RESPONSE),
                _mock_llm_response(VALIDATOR_RESPONSE),
                _mock_llm_response(DA_RESPONSE),
                _mock_llm_response(SYNTHESIS_RESPONSE),
            ]
        )

        context = {"phase_extract_output": {}}
        long_text = "First sentence about policy. Second sentence about economics. Third point on education."

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), patch(
            "openai.AsyncOpenAI",
            return_value=mock_client,
        ):
            result = await _invoke_collaborative_analysis(long_text, context)

        assert result["interaction_type"] == "sequential_collaborative"


# --- Workflow builder ---


class TestWorkflowBuilder:
    def test_builds_3_phase_workflow(self):
        workflow = build_collaborative_analysis_workflow()
        assert workflow.name == "collaborative_analysis"
        assert len(workflow.phases) == 3

    def test_phase_names_and_capabilities(self):
        workflow = build_collaborative_analysis_workflow()
        phase_map = {p.name: p.capability for p in workflow.phases}
        assert phase_map["extract"] == "fact_extraction"
        assert phase_map["quality"] == "argument_quality"
        assert phase_map["collaborative"] == "collaborative_analysis"

    def test_dependency_chain(self):
        workflow = build_collaborative_analysis_workflow()
        phase_map = {p.name: p for p in workflow.phases}
        assert phase_map["extract"].depends_on == []
        assert phase_map["quality"].depends_on == ["extract"]
        assert phase_map["collaborative"].depends_on == ["quality"]


# --- Integration: capability state writer in unified pipeline ---


class TestCapabilityStateWriterRegistered:
    def test_collaborative_analysis_in_writers(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "collaborative_analysis" in CAPABILITY_STATE_WRITERS

    def test_collaborative_in_workflow_catalog(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        catalog = get_workflow_catalog()
        assert "collaborative" in catalog

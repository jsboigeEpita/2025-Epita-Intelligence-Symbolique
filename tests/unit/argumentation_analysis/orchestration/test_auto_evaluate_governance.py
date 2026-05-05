"""Tests for #294 — auto-evaluate counter-arguments + auto-trigger governance vote.

Verifies that:
1. Counter-arguments are automatically evaluated after generation
2. Governance auto-runs social_choice_vote when positions are available
3. State writer uses evaluation scores and vote results
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCounterArgumentAutoEvaluation:
    """Tests for #294 — counter-argument auto-evaluation."""

    def test_evaluate_counter_arguments_adds_evaluation(self):
        """Each LLM counter-argument gets an evaluation dict with 5 criteria."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _evaluate_counter_arguments,
        )

        counters = [
            {
                "counter_argument": "Cet argument repose sur une fausse prémisse car les données montrent le contraire.",
                "strategy_used": "counter-example",
                "target_argument": "Le PIB croît grâce aux baisses d'impôts.",
                "strength": "strong",
            },
            {
                "counter_argument": "Court.",
                "strategy_used": "distinction",
                "target_argument": "Test argument.",
                "strength": "weak",
            },
        ]

        result = _evaluate_counter_arguments(counters, "Original text")

        # Both should have evaluation dicts
        assert "evaluation" in result[0]
        eval0 = result[0]["evaluation"]
        assert "overall_score" in eval0
        assert "relevance" in eval0
        assert "logical_strength" in eval0
        assert "persuasiveness" in eval0
        assert "originality" in eval0
        assert "clarity" in eval0
        assert "recommendations" in eval0
        assert 0.0 <= eval0["overall_score"] <= 1.0

        assert "evaluation" in result[1]

    def test_evaluate_counter_arguments_skips_empty(self):
        """Counter-arguments without counter_argument field are skipped."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _evaluate_counter_arguments,
        )

        counters = [
            {"strategy_used": "reductio"},  # missing counter_argument
            {
                "counter_argument": "Un bon contre-argument avec des preuves solides.",
                "strategy_used": "reductio ad absurdum",
                "strength": "moderate",
            },
        ]

        result = _evaluate_counter_arguments(counters, "Test")

        assert "evaluation" not in result[0]  # skipped
        assert "evaluation" in result[1]

    def test_evaluate_counter_arguments_handles_all_strategies(self):
        """All 5 strategy types map to proper CounterArgumentType."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _evaluate_counter_arguments,
        )

        strategies = [
            "reductio ad absurdum",
            "counter-example",
            "distinction",
            "reformulation",
            "concession",
        ]

        for strategy in strategies:
            counters = [
                {
                    "counter_argument": f"Contre-argument utilisant {strategy} avec des preuves.",
                    "strategy_used": strategy,
                    "strength": "moderate",
                }
            ]
            result = _evaluate_counter_arguments(counters, "Test text")
            assert "evaluation" in result[0], f"Failed for strategy: {strategy}"

    async def test_invoke_counter_includes_evaluation(self):
        """_invoke_counter_argument output includes evaluation in each counter."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_counter_argument,
        )

        mock_plugin = MagicMock()
        mock_plugin.parse_argument.return_value = '{"premise": "test"}'
        mock_plugin.suggest_strategy.return_value = '{"strategy_name": "test"}'

        llm_response = json.dumps(
            [
                {
                    "counter_argument": "Bon contre-argument avec des preuves solides.",
                    "strategy_used": "counter-example",
                    "target_argument": "Test argument",
                    "strength": "strong",
                }
            ]
        )

        mock_message = MagicMock()
        mock_message.content = llm_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentPlugin",
            return_value=mock_plugin,
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            context = {
                "phase_extract_output": {"arguments": [{"text": "Test argument"}]},
            }
            result = await _invoke_counter_argument("Test", context)

        assert "llm_counter_arguments" in result
        ca = result["llm_counter_arguments"][0]
        assert "evaluation" in ca
        assert 0.0 <= ca["evaluation"]["overall_score"] <= 1.0


class TestGovernanceAutoVote:
    """Tests for #294 — governance auto-triggers social_choice_vote."""

    async def test_governance_runs_vote_with_positions(self):
        """Governance auto-runs Copeland vote when positions are available."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_governance,
        )

        mock_plugin = MagicMock()
        mock_plugin.list_governance_methods.return_value = '["majority", "copeland"]'
        mock_plugin.detect_conflicts_fn.return_value = "[]"
        mock_plugin.social_choice_vote.return_value = json.dumps(
            {
                "winner": "agent_1",
                "copeland_scores": {"agent_1": 2, "agent_2": 1, "agent_3": 0},
            }
        )

        with patch(
            "argumentation_analysis.plugins.governance_plugin.GovernancePlugin",
            return_value=mock_plugin,
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
            return_value=(None, None),
        ):
            context = {
                "phase_extract_output": {
                    "arguments": [
                        {"text": "Arg 1"},
                        {"text": "Arg 2"},
                        {"text": "Arg 3"},
                    ]
                },
            }
            result = await _invoke_governance("Test", context)

        assert "vote_result" in result
        assert result["vote_result"]["winner"] == "agent_1"
        mock_plugin.social_choice_vote.assert_called_once()

    async def test_governance_no_vote_with_single_position(self):
        """Governance skips vote when less than 2 positions."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_governance,
        )

        mock_plugin = MagicMock()
        mock_plugin.list_governance_methods.return_value = '["majority"]'
        mock_plugin.detect_conflicts_fn.return_value = "[]"

        with patch(
            "argumentation_analysis.plugins.governance_plugin.GovernancePlugin",
            return_value=mock_plugin,
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
            return_value=(None, None),
        ):
            context = {
                "phase_extract_output": {"arguments": [{"text": "Single arg"}]},
            }
            result = await _invoke_governance("Test", context)

        assert "vote_result" not in result or result.get("vote_result") is None


class TestStateWriterEvaluationScore:
    """Tests for #294 — state writer uses evaluation scores."""

    def test_counter_state_writer_uses_evaluation_score(self):
        """State writer prefers evaluation.overall_score over strength map."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_counter_argument_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="test")
        output = {
            "llm_counter_arguments": [
                {
                    "counter_argument": "Good counter",
                    "target_argument": "Original",
                    "strategy_used": "distinction",
                    "strength": "weak",  # would map to 0.3
                    "evaluation": {
                        "overall_score": 0.72,  # should be used instead
                        "relevance": 0.8,
                        "logical_strength": 0.7,
                    },
                }
            ]
        }
        _write_counter_argument_to_state(output, state, {})

        assert len(state.counter_arguments) == 1
        assert state.counter_arguments[0]["score"] == 0.72

    def test_counter_state_writer_fallback_without_evaluation(self):
        """State writer falls back to strength map without evaluation."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_counter_argument_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="test")
        output = {
            "llm_counter_arguments": [
                {
                    "counter_argument": "Counter",
                    "target_argument": "Original",
                    "strategy_used": "test",
                    "strength": "strong",
                }
            ]
        }
        _write_counter_argument_to_state(output, state, {})

        assert len(state.counter_arguments) == 1
        assert state.counter_arguments[0]["score"] == 0.9  # strong → 0.9

    def test_governance_state_writer_uses_vote_winner(self):
        """Governance state writer uses vote_result winner and Copeland scores."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_governance_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="test")
        output = {
            "available_methods": ["majority", "copeland"],
            "positions": {"agent_1": "pos1", "agent_2": "pos2"},
            "conflicts": [],
            "resolutions": [],
            "vote_result": {
                "winner": "agent_1",
                "copeland_scores": {"agent_1": 1, "agent_2": 0},
            },
        }
        _write_governance_to_state(output, state, {})

        assert len(state.governance_decisions) == 1
        decision = state.governance_decisions[0]
        assert decision["winner"] == "agent_1"
        assert decision["scores"]["agent_1"] == 1.0

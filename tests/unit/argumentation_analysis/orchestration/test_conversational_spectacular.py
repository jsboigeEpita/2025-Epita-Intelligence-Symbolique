"""Tests for conversational orchestrator spectacular mode — #363.

Verifies that run_conversational_analysis uses UnifiedAnalysisState when
spectacular=True and produces result format matching the unified pipeline.
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)


@pytest.fixture
def mock_conversational_deps():
    """Patch all external dependencies of run_conversational_analysis."""
    with patch(
        "argumentation_analysis.orchestration.conversational_orchestrator.sk"
    ) as mock_sk, patch(
        "argumentation_analysis.orchestration.conversational_orchestrator"
        ".ConversationalTraceAnalyzer"
    ) as mock_trace_cls, patch(
        "argumentation_analysis.orchestration.conversational_orchestrator"
        ".create_conversational_agents"
    ) as mock_create, patch.dict(
        "os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_CHAT_MODEL_ID": "test"}
    ):
        mock_kernel = MagicMock()
        mock_sk.Kernel.return_value = mock_kernel

        mock_trace = MagicMock()
        mock_trace.generate_report.return_value = {}
        mock_trace_cls.return_value = mock_trace

        mock_agent = MagicMock()
        mock_agent.name = "ProjectManager"
        mock_create.return_value = [mock_agent]

        yield {
            "sk": mock_sk,
            "kernel": mock_kernel,
            "trace_cls": mock_trace_cls,
            "trace": mock_trace,
            "create": mock_create,
            "agent": mock_agent,
        }


class TestSpectacularStateUpgrade:
    """Verify UnifiedAnalysisState is used in spectacular mode."""

    @pytest.mark.asyncio
    async def test_spectacular_true_uses_unified_state(self, mock_conversational_deps):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_phase",
            new_callable=AsyncMock,
        ) as mock_run_phase, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._resolve_phase_conflicts",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._retract_fallacious_beliefs",
            return_value=None,
        ):
            mock_run_phase.return_value = [
                {"phase": "test", "turn": 1, "agent": "PM", "content": "done"}
            ]

            # Mock _should_add_reanalysis_phase to skip re-analysis
            with patch(
                "argumentation_analysis.orchestration.conversational_orchestrator"
                "._should_add_reanalysis_phase",
                return_value=False,
            ):
                result = await run_conversational_analysis(
                    "test text", spectacular=True
                )

        assert result["workflow_name"] == "spectacular_analysis"
        assert isinstance(result["unified_state"], UnifiedAnalysisState)

    @pytest.mark.asyncio
    async def test_spectacular_false_uses_rhetorical_state(
        self, mock_conversational_deps
    ):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_phase",
            new_callable=AsyncMock,
        ) as mock_run_phase, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._resolve_phase_conflicts",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._retract_fallacious_beliefs",
            return_value=None,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._should_add_reanalysis_phase",
            return_value=False,
        ):
            mock_run_phase.return_value = []

            result = await run_conversational_analysis("test text", spectacular=False)

        assert result["workflow_name"] == "conversational"
        assert isinstance(result["unified_state"], RhetoricalAnalysisState)
        assert not isinstance(result["unified_state"], UnifiedAnalysisState)


class TestSpectacularResultFormat:
    """Verify result format matches unified pipeline output."""

    @pytest.mark.asyncio
    async def test_result_has_unified_pipeline_keys(self, mock_conversational_deps):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_phase",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._resolve_phase_conflicts",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._retract_fallacious_beliefs",
            return_value=None,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._should_add_reanalysis_phase",
            return_value=False,
        ):
            result = await run_conversational_analysis("test text", spectacular=True)

        # Unified pipeline expects these keys
        assert "workflow_name" in result
        assert "phases" in result
        assert "summary" in result
        assert "unified_state" in result
        assert "state_snapshot" in result
        assert "capabilities_used" in result
        assert "capabilities_missing" in result

        # Summary format
        summary = result["summary"]
        assert "completed" in summary
        assert "failed" in summary
        assert "skipped" in summary
        assert "total" in summary
        assert "total_messages" in summary

    @pytest.mark.asyncio
    async def test_result_has_coverage_metrics(self, mock_conversational_deps):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_phase",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._resolve_phase_conflicts",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._retract_fallacious_beliefs",
            return_value=None,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._should_add_reanalysis_phase",
            return_value=False,
        ):
            result = await run_conversational_analysis("test text", spectacular=True)

        assert "state_non_empty_fields" in result
        assert "state_total_fields" in result
        assert "state_coverage_pct" in result
        assert isinstance(result["state_coverage_pct"], float)


class TestSpectacularCapabilityMapping:
    """Verify agent→capability mapping from conversation log."""

    @pytest.mark.asyncio
    async def test_capabilities_extracted_from_conversation(
        self, mock_conversational_deps
    ):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        conv_log = [
            {"phase": "P1", "agent": "ExtractAgent", "content": "found args"},
            {"phase": "P1", "agent": "InformalAgent", "content": "found fallacies"},
            {"phase": "P2", "agent": "FormalAgent", "content": "formalized"},
            {"phase": "P2", "agent": "QualityAgent", "content": "scored"},
            {"phase": "P3", "agent": "CounterAgent", "content": "countered"},
            {"phase": "P3", "agent": "DebateAgent", "content": "debated"},
            {"phase": "P3", "agent": "GovernanceAgent", "content": "voted"},
        ]

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_phase",
            new_callable=AsyncMock,
            return_value=conv_log,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._resolve_phase_conflicts",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._retract_fallacious_beliefs",
            return_value=None,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._should_add_reanalysis_phase",
            return_value=False,
        ):
            result = await run_conversational_analysis("test text", spectacular=True)

        caps = result["capabilities_used"]
        assert "fact_extraction" in caps
        assert "neural_fallacy_detection" in caps
        assert "fol_reasoning" in caps
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps
        assert "adversarial_debate" in caps
        assert "governance_simulation" in caps


class TestUnifiedAnalysisStateFields:
    """Verify UnifiedAnalysisState has all expected fields."""

    def test_unified_state_field_count(self):
        state = UnifiedAnalysisState("test text")
        snapshot = state.get_state_snapshot(summarize=False)
        # Must have ≥ 28 fields for spectacular coverage
        assert (
            len(snapshot) >= 28
        ), f"UnifiedAnalysisState has {len(snapshot)} fields, need >= 28"

    def test_unified_state_inherits_rhetorical(self):
        state = UnifiedAnalysisState("test text")
        assert isinstance(state, RhetoricalAnalysisState)
        assert isinstance(state, UnifiedAnalysisState)

    def test_spectacular_fields_present(self):
        state = UnifiedAnalysisState("test text")
        spectacular_fields = [
            "counter_arguments",
            "argument_quality_scores",
            "jtms_beliefs",
            "dung_frameworks",
            "governance_decisions",
            "debate_transcripts",
            "neural_fallacy_scores",
            "fol_analysis_results",
            "propositional_analysis_results",
            "modal_analysis_results",
            "formal_synthesis_reports",
            "nl_to_logic_translations",
            "workflow_results",
        ]
        for field in spectacular_fields:
            assert hasattr(state, field), f"Missing field: {field}"

    def test_state_populates_to_28_plus(self):
        """Simulate mock population and verify >= 28 fields are non-empty."""
        state = UnifiedAnalysisState("test text")

        # Simulate what agents would populate in spectacular mode
        state.analysis_tasks["t1"] = "Extract arguments"
        state.identified_arguments["a1"] = "Claim X is true"
        state.identified_fallacies["f1"] = {"type": "ad_hominem"}
        state.extracts.append({"claim": "test"})
        state.counter_arguments.append({"strategy": "reductio"})
        state.argument_quality_scores["a1"] = {"overall": 0.7}
        state.jtms_beliefs["b1"] = {"status": "IN"}
        state.dung_frameworks["d1"] = {"extensions": {}}
        state.governance_decisions.append({"method": "majority"})
        state.debate_transcripts.append({"round": 1})
        state.neural_fallacy_scores.append({"score": 0.9})
        state.fol_analysis_results.append({"formula": "forall x P(x)"})
        state.propositional_analysis_results.append({"formula": "p -> q"})
        state.modal_analysis_results.append({"formula": "[]p"})
        state.formal_synthesis_reports.append({"summary": "ok"})
        state.nl_to_logic_translations.append({"nl": "test", "formal": "P"})
        state.workflow_results["test"] = {"status": "done"}
        state.belief_sets["bs1"] = {"logic_type": "FOL"}
        state.query_log.append({"query": "test"})
        state.answers["t1"] = {"answer_text": "result"}
        state.final_conclusion = "Text is fallacious"
        # Extended spectacular fields
        state.ranking_results.append({"ranked": ["a1"]})
        state.aspic_results.append({"arguments": []})
        state.dialogue_results.append({"move": "assert"})
        state.probabilistic_results.append({"prob": 0.8})
        state.bipolar_results.append({"support": []})
        state.semantic_index_refs.append({"ref_id": "r1"})
        state.transcription_segments.append({"text": "seg"})

        snapshot = state.get_state_snapshot(summarize=False)
        non_empty = sum(
            1 for v in snapshot.values() if v and v not in ([], {}, "", None, 0)
        )
        assert (
            non_empty >= 28
        ), f"Only {non_empty}/{len(snapshot)} fields non-empty after mock population"

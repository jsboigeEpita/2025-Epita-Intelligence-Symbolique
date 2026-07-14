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
        # Non-formal agents map purely from participation (no degradation
        # concept) — these remain in capabilities_used.
        assert "fact_extraction" in caps
        assert "neural_fallacy_detection" in caps
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps
        assert "adversarial_debate" in caps
        assert "governance_simulation" in caps
        # Constat n°5 (#1355): FormalAgent participated here, but the mocked
        # _run_phase populated NO formal result entries in state — so the
        # formal axes are NOT reported as ``used`` (that was the bug). With
        # empty formal state, they are ``missing`` (participated, no entry).
        # The genuine-vs-degraded distinction is covered directly by
        # TestConstat5FormalCapabilityHonesty below.
        assert "fol_reasoning" not in caps
        assert "modal_logic" not in caps
        assert "propositional_logic" not in caps
        assert "nl_to_logic_translation" not in caps
        assert "fol_reasoning" in result["capabilities_missing"]
        assert result["capabilities_degraded"] == [] or all(
            c not in ("fol_reasoning", "modal_logic", "propositional_logic")
            for c in result["capabilities_degraded"]
        )


class TestConstat5FormalCapabilityHonesty:
    """Constat n°5 (#1355): degraded formal axes ≠ used — DI synthetic tests.

    Proves the honest split without any JVM/LLM: ``_classify_formal_capabilities``
    crosses FormalAgent participation with the REAL per-axis decision status
    already recorded in state. A degraded axis (``unavailable:*`` token or empty
    theory) is never reported as ``used`` (anti-théâtre #1019).
    """

    def _make_state(self) -> "UnifiedAnalysisState":
        return UnifiedAnalysisState("corpus_A synthetic")

    def test_degraded_fol_not_used(self):
        """FOL degraded (no-translation) → fol_reasoning in degraded, not used."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _classify_formal_capabilities,
        )

        state = self._make_state()
        state.add_fol_analysis_result(
            [], None, [], 0.0, message="unavailable:no-translation — empty theory"
        )
        used, degraded, missing = _classify_formal_capabilities(state)
        assert "fol_reasoning" not in used
        assert "fol_reasoning" in degraded
        assert "fol_reasoning" not in missing
        # No formulas produced anywhere → nl_to_logic degraded (attempted, failed)
        assert "nl_to_logic_translation" not in used
        assert "nl_to_logic_translation" in degraded

    def test_genuine_fol_is_used(self):
        """FOL genuine decision → fol_reasoning + nl_to_logic_translation used."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _classify_formal_capabilities,
        )

        state = self._make_state()
        state.add_fol_analysis_result(
            ["forall x (P(x) -> Q(x))"], True, ["Q(x) derived"], 0.9
        )
        used, degraded, missing = _classify_formal_capabilities(state)
        assert "fol_reasoning" in used
        assert "fol_reasoning" not in degraded
        assert "nl_to_logic_translation" in used

    def test_modal_solver_oom_split_is_the_crux(self):
        """modal unavailable:no-solver keeps formulas → modal degraded BUT
        nl_to_logic_translation used (translation succeeded, solver failed).

        This is the crux distinction: translation-success ≠ solver-success.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _classify_formal_capabilities,
        )

        state = self._make_state()
        # Formulas present (translation worked) but solver OOM'd.
        state.add_modal_analysis_result(
            ["[]p", "<>q"], None, [], message="unavailable:no-solver — SPASS OOM"
        )
        used, degraded, missing = _classify_formal_capabilities(state)
        assert "modal_logic" not in used
        assert "modal_logic" in degraded
        # Translation DID produce formulas → nl_to_logic is genuine.
        assert "nl_to_logic_translation" in used
        assert "nl_to_logic_translation" not in degraded

    def test_missing_when_no_entries(self):
        """FormalAgent participated but no formal entries → all four missing."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _classify_formal_capabilities,
        )

        state = self._make_state()  # empty
        used, degraded, missing = _classify_formal_capabilities(state)
        assert used == set()
        assert degraded == set()
        assert missing == {
            "fol_reasoning",
            "modal_logic",
            "propositional_logic",
            "nl_to_logic_translation",
        }

    def test_mixed_fol_genuine_modal_degraded_per_axis(self):
        """Per-axis independence: FOL genuine + modal degraded in one run."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _classify_formal_capabilities,
        )

        state = self._make_state()
        state.add_fol_analysis_result(["forall x P(x)"], True, [], 0.8)
        state.add_modal_analysis_result(
            [], None, [], message="unavailable:no-translation — empty"
        )
        used, degraded, missing = _classify_formal_capabilities(state)
        assert "fol_reasoning" in used
        assert "modal_logic" in degraded
        assert "modal_logic" not in used
        assert "fol_reasoning" not in degraded
        # FOL produced formulas → nl_to_logic used.
        assert "nl_to_logic_translation" in used

    def test_parse_fail_fol_is_degraded(self):
        """FOL unavailable:parse-fail (formulas produced but unparseable)
        → degraded. Verifies the unavailable:* prefix contract."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _formal_axis_genuine,
        )

        # Even if formulas leaked non-empty, the unavailable: prefix marks
        # the axis degraded (the prover decided nothing).
        assert not _formal_axis_genuine(
            [{"formulas": ["forall x P(x)"], "message": "unavailable:parse-fail"}]
        )
        assert _formal_axis_genuine([{"formulas": ["forall x P(x)"], "message": None}])
        # Empty theory with no degradation token is NOT genuine (#1019).
        assert not _formal_axis_genuine([{"formulas": [], "message": None}])


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

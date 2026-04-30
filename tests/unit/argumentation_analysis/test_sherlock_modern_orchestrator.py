"""Tests for Modern Sherlock Orchestrator (#357).

Validates that the orchestrator:
- Uses >=5 agents
- Produces an investigation trace with >=7 steps
- Builds a reasoning chain
- Tracks hypotheses
- Produces a solution
- Works without LLM (template-based fallbacks)
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
    SherlockModernOrchestrator,
    InvestigationResult,
    InvestigationStep,
    build_sherlock_modern_workflow,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


SAMPLE_DISCOURSE = (
    "Le professeur affirme que le changement climatique est un canular. "
    "Il cite une etude non peer-reviewee et attaque personnellement les "
    "scientifiques du GIEC. Malgre des preuves contradictoires, il "
    "maintient sa position avec conviction."
)


class TestSherlockModernOrchestrator:
    """Tests for the main orchestrator class."""

    def test_investigate_returns_result(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert isinstance(result, InvestigationResult)

    def test_uses_at_least_5_agents(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert result.agent_count >= 5, (
            f"Expected >= 5 agents, got {result.agent_count}: {result.agents_used}"
        )

    def test_agents_include_required_types(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        agents_lower = [a.lower() for a in result.agents_used]
        assert any("extract" in a for a in agents_lower), f"Missing ExtractAgent in {result.agents_used}"
        assert any("fallacy" in a or "informal" in a for a in agents_lower), f"Missing fallacy agent in {result.agents_used}"
        assert any("quality" in a for a in agents_lower), f"Missing quality agent in {result.agents_used}"
        assert any("counter" in a for a in agents_lower), f"Missing counter-arg agent in {result.agents_used}"
        assert any("jtms" in a for a in agents_lower), f"Missing JTMS in {result.agents_used}"
        assert any("atms" in a for a in agents_lower), f"Missing ATMS in {result.agents_used}"

    def test_trace_has_7_steps(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert len(result.trace) >= 7, (
            f"Expected >= 7 trace steps, got {len(result.trace)}"
        )

    def test_trace_steps_have_required_fields(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        for step in result.trace:
            assert "step" in step
            assert "phase" in step
            assert "agent" in step
            assert "findings" in step
            assert "conclusion" in step

    def test_trace_phases_cover_pipeline(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        phases = [s["phase"] for s in result.trace]
        expected = [
            "extraction", "fallacy_detection", "quality_evaluation",
            "cross_examination", "belief_tracking",
            "hypothesis_branching", "solution_synthesis",
        ]
        for expected_phase in expected:
            assert expected_phase in phases, f"Missing phase: {expected_phase}"

    def test_reasoning_chain_built(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert len(result.reasoning_chain) >= 7
        for conclusion in result.reasoning_chain:
            assert isinstance(conclusion, str)
            assert len(conclusion) > 10

    def test_solution_not_empty(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert isinstance(result.solution, str)
        assert len(result.solution) > 0

    def test_state_populated(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert orch.state is not None
        assert orch.state.raw_text == SAMPLE_DISCOURSE

    def test_state_provided_at_init(self):
        state = UnifiedAnalysisState("pre-existing state")
        orch = SherlockModernOrchestrator(state=state)
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert orch.state is state

    def test_with_context(self):
        orch = SherlockModernOrchestrator()
        ctx = {"test_key": "test_value"}
        result = _run(orch.investigate(SAMPLE_DISCOURSE, context=ctx))
        assert isinstance(result, InvestigationResult)

    def test_hypotheses_list(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert isinstance(result.hypotheses, list)

    def test_no_llm_calls_template_fallback(self):
        """Verify the orchestrator works with all invoke_callables patched out."""
        orch = SherlockModernOrchestrator()
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator._invoke_safe",
            new_callable=AsyncMock,
        ) as mock_invoke:
            async def fake_invoke(func_name, text, fallback):
                return dict(fallback)

            mock_invoke.side_effect = fake_invoke
            result = _run(orch.investigate(SAMPLE_DISCOURSE))
            assert result.agent_count >= 5
            assert len(result.trace) >= 7


class TestInvestigationResult:
    """Tests for the InvestigationResult dataclass."""

    def test_default_values(self):
        result = InvestigationResult()
        assert result.trace == []
        assert result.reasoning_chain == []
        assert result.agents_used == []
        assert result.agent_count == 0
        assert result.hypotheses == []
        assert result.solution == ""

    def test_with_values(self):
        result = InvestigationResult(
            trace=[{"step": 1}],
            reasoning_chain=["conclusion"],
            agents_used=["Agent1"],
            agent_count=1,
        )
        assert len(result.trace) == 1
        assert result.agent_count == 1


class TestInvestigationStep:
    """Tests for the InvestigationStep dataclass."""

    def test_creation(self):
        step = InvestigationStep(
            step=1, phase="test", agent="Agent",
            findings={"k": "v"}, conclusion="test conclusion",
        )
        assert step.step == 1
        assert step.phase == "test"

    def test_defaults(self):
        step = InvestigationStep(step=1, phase="test", agent="Agent")
        assert step.findings == {}
        assert step.conclusion == ""


class TestBuildSherlockModernWorkflow:
    """Tests for the workflow builder function."""

    def test_returns_workflow_or_none(self):
        wf = build_sherlock_modern_workflow()
        # May be None if workflow_dsl unavailable, but shouldn't crash
        if wf is not None:
            assert hasattr(wf, "phases")
            assert len(wf.phases) >= 5

    def test_workflow_name(self):
        wf = build_sherlock_modern_workflow()
        if wf is not None:
            assert wf.name == "sherlock_modern"

    def test_workflow_phases_include_core(self):
        wf = build_sherlock_modern_workflow()
        if wf is not None:
            phase_names = [p.name for p in wf.phases]
            assert "extract" in phase_names
            assert "quality" in phase_names
            assert "counter" in phase_names

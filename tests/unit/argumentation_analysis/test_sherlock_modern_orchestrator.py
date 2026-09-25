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


@pytest.mark.slow
class TestSherlockModernOrchestrator:
    """Tests for the main orchestrator class.

    Instantiates the full SherlockModernOrchestrator and runs end-to-end
    multi-agent investigations (~25 min / 13 tests, max ~155s each in the
    CI tally run 28582260688). These are integration-style checks, not unit
    tests; marked `slow` so the per-push gate excludes them (#1336, R535).
    """

    def test_investigate_returns_result(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert isinstance(result, InvestigationResult)

    def test_uses_at_least_5_agents(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert (
            result.agent_count >= 5
        ), f"Expected >= 5 agents, got {result.agent_count}: {result.agents_used}"

    def test_agents_include_required_types(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        agents_lower = [a.lower() for a in result.agents_used]
        assert any(
            "extract" in a for a in agents_lower
        ), f"Missing ExtractAgent in {result.agents_used}"
        assert any(
            "fallacy" in a or "informal" in a for a in agents_lower
        ), f"Missing fallacy agent in {result.agents_used}"
        assert any(
            "quality" in a for a in agents_lower
        ), f"Missing quality agent in {result.agents_used}"
        assert any(
            "counter" in a for a in agents_lower
        ), f"Missing counter-arg agent in {result.agents_used}"
        assert any(
            "jtms" in a for a in agents_lower
        ), f"Missing JTMS in {result.agents_used}"
        assert any(
            "atms" in a for a in agents_lower
        ), f"Missing ATMS in {result.agents_used}"

    def test_trace_has_7_steps(self):
        orch = SherlockModernOrchestrator()
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert (
            len(result.trace) >= 7
        ), f"Expected >= 7 trace steps, got {len(result.trace)}"

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
            "extraction",
            "fallacy_detection",
            "quality_evaluation",
            "cross_examination",
            "belief_tracking",
            "hypothesis_branching",
            "solution_synthesis",
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

    def test_all_callables_failing_still_produces_a_trace(self):
        """#2543: with every phase callable failing, the investigation still
        completes — but as FAILED steps, never as empty findings. The former
        contract returned each phase's fallback dict, which the phases narrated
        as results ("Detected 0", "0.0/10"); reverting to that swallow makes
        this test red (see TestPhaseFailureFailLoud2543)."""
        orch = SherlockModernOrchestrator()

        async def failing_phase(func_name, text):
            return None, "RuntimeError: no service"

        orch._invoke_phase = failing_phase
        result = _run(orch.investigate(SAMPLE_DISCOURSE))
        assert result.agent_count >= 5
        assert len(result.trace) == 7
        assert all(s["findings"].get("failed") for s in result.trace)
        assert len(orch.state.errors) == 7


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
            step=1,
            phase="test",
            agent="Agent",
            findings={"k": "v"},
            conclusion="test conclusion",
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


class TestCoherentThreeStateRewriter:
    """#1650 (R790 item 2, rewriter): the hypothesis builder must PRESERVE the
    absence of the ``coherent`` key rather than stamping ``False``. The previous
    ``ctx.get("coherent", False)`` destroyed the absence BEFORE any reader could
    see it, making every downstream reader's "absent" branch unreachable —
    theater. These tests arm the rewriter in isolation (no LLM/JVM): mock
    _invoke_safe to inject a context lacking the key, assert the built
    hypothesis lacks the key too. Substitution control: reverting to
    ``ctx.get("coherent", False)`` turns the first test red."""

    @pytest.mark.asyncio
    async def test_absent_coherent_key_is_preserved_not_stamped_false(self):
        async def fake_invoke_phase(func_name, text):
            return (
                {
                    "atms_contexts": [
                        {"hypothesis_id": "h_nokey", "assumptions": ["a"]}
                    ],
                    "has_contradictions": False,
                },
                None,
            )

        orch = SherlockModernOrchestrator()
        orch._invoke_phase = fake_invoke_phase
        await orch._phase_hypothesis_branching("text")
        assert len(orch._hypotheses) == 1
        # The absent key is preserved — NOT stamped to False. (Reverting the
        # rewriter to ctx.get("coherent", False) makes this assertion fail.)
        assert "coherent" not in orch._hypotheses[0]

    @pytest.mark.asyncio
    async def test_present_coherent_key_is_carried_through(self):
        async def fake_invoke_phase(func_name, text):
            return (
                {
                    "atms_contexts": [
                        {"hypothesis_id": "h_t", "coherent": True, "assumptions": []},
                        {"hypothesis_id": "h_f", "coherent": False, "assumptions": []},
                    ],
                    "has_contradictions": True,
                },
                None,
            )

        orch = SherlockModernOrchestrator()
        orch._invoke_phase = fake_invoke_phase
        await orch._phase_hypothesis_branching("text")
        by_id = {h["id"]: h for h in orch._hypotheses}
        assert by_id["h_t"]["coherent"] is True
        assert by_id["h_f"]["coherent"] is False


class TestPhaseFailureFailLoud2543:
    """#2543 — a phase whose callable raised (or does not exist) is a FAILED
    phase: exception in the trace and the state, no fallback persisted, no
    empty finding narrated. The former ``_invoke_safe`` returned the phase's
    fallback dict on any exception, which the phase then treated as its
    result. Every test here is born-red on main; restoring the fallback
    swallow (or the ``type`` reader key) turns it red again."""

    PHASES = [
        # (phase method, phase label, agent, ctx key written on success)
        ("_phase_extraction", "extraction", "ExtractAgent", "phase_extract_output"),
        (
            "_phase_fallacy_detection",
            "fallacy_detection",
            "InformalAnalysisAgent",
            "phase_hierarchical_fallacy_output",
        ),
        (
            "_phase_quality",
            "quality_evaluation",
            "ArgumentQualityEvaluator",
            "phase_quality_output",
        ),
        (
            "_phase_cross_examination",
            "cross_examination",
            "CounterArgumentAgent",
            "phase_counter_output",
        ),
        ("_phase_belief_tracking", "belief_tracking", "JTMS", "phase_jtms_output"),
        (
            "_phase_hypothesis_branching",
            "hypothesis_branching",
            "ATMS",
            "phase_atms_output",
        ),
        (
            "_phase_solution_synthesis",
            "solution_synthesis",
            "NarrativeSynthesisPlugin",
            "phase_narrative_synthesis_output",
        ),
    ]

    @staticmethod
    def _orch():
        return SherlockModernOrchestrator(state=UnifiedAnalysisState("text"))

    @pytest.mark.parametrize("method,phase,agent,ctx_key", PHASES)
    async def test_raising_callable_gives_failed_phase(
        self, method, phase, agent, ctx_key
    ):
        """Born-red per shape: the phase records a failed step carrying the
        exception, writes no ctx key, and logs the error in the state."""

        async def failing(func_name, text):
            return None, "RuntimeError: boom"

        orch = self._orch()
        orch._invoke_phase = failing
        args = () if method == "_phase_solution_synthesis" else ("text",)
        await getattr(orch, method)(*args)
        step = orch._trace[-1]
        assert step.findings.get("failed") is True
        assert "RuntimeError" in step.findings.get("error", "")
        assert step.conclusion.startswith(f"Phase '{phase}' did not run")
        assert ctx_key not in orch._ctx, "a failed phase must not publish a result"
        assert orch.state.errors, "failure must be recorded in the state"
        assert orch.state.errors[-1]["agent_name"] == agent

    async def test_quality_failure_writes_no_score_and_no_zero_note(self):
        """The quality fallback (``note_finale: 0.0``) was a score nothing
        computed — on failure nothing reaches the state's quality surface."""

        async def failing(func_name, text):
            return None, "RuntimeError: boom"

        orch = self._orch()
        orch._invoke_phase = failing
        await orch._phase_quality("text")
        assert orch.state.argument_quality_scores == {}
        step = orch._trace[-1]
        assert "0.0/10" not in step.conclusion

    async def test_fallacy_failure_does_not_narrate_detected_zero(self):
        async def failing(func_name, text):
            return None, "RuntimeError: boom"

        orch = self._orch()
        orch._invoke_phase = failing
        await orch._phase_fallacy_detection("text")
        step = orch._trace[-1]
        assert "Detected 0" not in step.conclusion
        assert step.findings.get("fallacy_count") is None

    async def test_real_invoke_phase_catches_a_raising_callable(self):
        """Mutation control on the seam itself: with the REAL ``_invoke_phase``
        (no instance override), a callable that raises is caught and named —
        reintroducing the fallback swallow here turns this red."""
        orch = self._orch()
        with patch(
            "argumentation_analysis.orchestration.invoke_callables._invoke_jtms",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            await orch._phase_belief_tracking("text")
        step = orch._trace[-1]
        assert step.findings.get("failed") is True
        assert (
            "RuntimeError" in step.findings["error"]
            and "boom" in step.findings["error"]
        )
        assert "phase_jtms_output" not in orch._ctx
        assert orch.state.errors

    async def test_missing_callable_is_a_failure_not_a_silent_fallback(self):
        """``_invoke_extract`` never existed in invoke_callables — the old
        contract silently returned the fallback (without even a log) and the
        extraction phase never ran."""
        orch = self._orch()
        result, error = await orch._invoke_phase("_invoke_extract", "text")
        assert result is None
        assert "_invoke_extract" in (error or "")
        assert "not found" in (error or "")

    async def test_extraction_phase_calls_the_real_fact_extraction_callable(self):
        """The extraction phase must request the callable the registry wires
        for ``fact_extraction`` (registry_setup.py: ``_invoke_fact_extraction``)
        — not the phantom ``_invoke_extract`` name."""
        with patch(
            "argumentation_analysis.orchestration.invoke_callables"
            "._invoke_fact_extraction",
            new=AsyncMock(
                return_value={
                    "claims": [{"text": "claim one"}],
                    "arguments": [{"text": "arg one"}],
                }
            ),
        ) as mock_extract:
            orch = self._orch()
            await orch._phase_extraction("text")
        mock_extract.assert_awaited_once()
        assert orch._ctx["phase_extract_output"]["claims"][0]["text"] == "claim one"
        assert "Identified 2 element(s)" in orch._trace[-1].conclusion

    async def test_fallacy_step_reads_the_key_the_detector_writes(self):
        """The detector's items carry ``fallacy_type``
        (fallacy_workflow_plugin.py emits that key); the step used to read
        ``type`` and rendered ``Detected 3 ... ()`` on real runs."""

        async def detector_shaped(func_name, text):
            return (
                {
                    "fallacies": [
                        {"fallacy_type": "ad_hominem"},
                        {"fallacy_type": "straw_man"},
                        {"fallacy_type": "ad_hominem"},
                    ],
                    "total": 3,
                },
                None,
            )

        orch = self._orch()
        orch._invoke_phase = detector_shaped
        await orch._phase_fallacy_detection("text")
        step = orch._trace[-1]
        assert step.findings["fallacy_count"] == 3
        assert sorted(step.findings["types"]) == ["ad_hominem", "straw_man"]
        assert "ad_hominem" in step.conclusion
        assert not step.conclusion.endswith("().")

    async def test_degraded_extraction_status_is_surfaced(self):
        """Review #2660: ``_invoke_fact_extraction`` does not RAISE on failure
        — it returns the heuristic sentence split with
        ``extraction_status="failed:<reason>"`` (#1290). The phase used to
        narrate that degraded split as a normal finding; the degradation
        channel must be surfaced instead."""

        async def degraded(func_name, text):
            return (
                {
                    "claims": [{"text": "c1"}, {"text": "c2"}],
                    "arguments": [],
                    "extraction_status": "failed:no-openai-client",
                },
                None,
            )

        orch = self._orch()
        orch._invoke_phase = degraded
        await orch._phase_extraction("text")
        step = orch._trace[-1]
        assert step.findings.get("extraction_status") == "failed:no-openai-client"
        assert "failed:no-openai-client" in step.conclusion

    async def test_ok_extraction_keeps_the_conclusion_unchanged(self):
        """Contre-pendule: a healthy extraction (status "ok" or absent) keeps
        the exact pre-change conclusion shape — no degradation suffix, no
        status key in the findings."""

        async def healthy(func_name, text):
            return {"claims": [{"text": "c1"}], "arguments": [{"text": "a1"}]}, None

        orch = self._orch()
        orch._invoke_phase = healthy
        await orch._phase_extraction("text")
        step = orch._trace[-1]
        assert step.findings["claims_found"] == 1
        assert step.findings["arguments_found"] == 1
        assert "extraction_status" not in step.findings
        assert step.conclusion == (
            "Identified 2 element(s) for investigation (1 claims, 1 arguments)."
        )

    async def test_solution_names_the_phases_that_did_not_run(self):
        async def failing(func_name, text):
            return None, "RuntimeError: boom"

        orch = self._orch()
        orch._invoke_phase = failing
        result = await orch.investigate("text")
        assert "Phases that did not run" in result.solution
        for _, phase, _, _ in self.PHASES:
            assert phase in result.solution

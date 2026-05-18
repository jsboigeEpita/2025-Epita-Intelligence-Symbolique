"""Tests for orchestrator state-growth validation hook (#597).

Verifies:
- _get_growth_fingerprint returns correct counters
- _validate_state_growth detects zero-delta in growth-expecting phases
- _run_phase triggers re-prompt when no growth (mock agent)
- enable_growth_validation=False disables re-prompting
- Telemetry re_prompt_count appears in messages
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.orchestration.conversational_orchestrator import (
    _get_growth_fingerprint,
    _validate_state_growth,
    _run_phase,
    _GROWTH_EXPECTING_PATTERNS,
    _RE_PROMPT_FEEDBACK,
)


class TestGrowthFingerprint:
    """_get_growth_fingerprint returns a tuple of key state counters."""

    def test_none_state(self):
        assert _get_growth_fingerprint(None) == (0,)

    def test_empty_state(self):
        state = MagicMock()
        state.identified_arguments = {}
        state.identified_fallacies = {}
        state.counter_arguments = []
        state.jtms_beliefs = {}
        state.dung_frameworks = {}
        state.aspic_results = []
        state.belief_revision_results = []
        state.nl_to_logic_translations = []
        state.fol_analysis_results = []
        state.propositional_analysis_results = []
        state.modal_analysis_results = []
        fp = _get_growth_fingerprint(state)
        assert all(c == 0 for c in fp)
        assert len(fp) == 11

    def test_state_with_arguments(self):
        state = MagicMock()
        state.identified_arguments = {"arg_1": "test", "arg_2": "test2"}
        state.identified_fallacies = {}
        state.counter_arguments = []
        state.jtms_beliefs = {}
        state.dung_frameworks = {}
        state.aspic_results = []
        state.belief_revision_results = []
        state.nl_to_logic_translations = []
        state.fol_analysis_results = []
        state.propositional_analysis_results = []
        state.modal_analysis_results = []
        fp = _get_growth_fingerprint(state)
        assert fp[0] == 2  # identified_arguments count

    def test_fingerprint_changes_on_growth(self):
        state = MagicMock()
        state.identified_arguments = {}
        state.identified_fallacies = {}
        state.counter_arguments = []
        state.jtms_beliefs = {}
        state.dung_frameworks = {}
        state.aspic_results = []
        state.belief_revision_results = []
        state.nl_to_logic_translations = []
        state.fol_analysis_results = []
        state.propositional_analysis_results = []
        state.modal_analysis_results = []
        before = _get_growth_fingerprint(state)

        state.identified_arguments = {"arg_1": "new argument"}
        after = _get_growth_fingerprint(state)
        assert after != before


class TestValidateStateGrowth:
    """_validate_state_growth returns False when growth-expecting phase has zero delta."""

    def test_growth_phase_with_no_delta(self):
        fp = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert _validate_state_growth(fp, fp, "Extraction & Detection") is False

    def test_growth_phase_with_delta(self):
        before = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        after = (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert _validate_state_growth(before, after, "Extraction & Detection") is True

    def test_non_growth_phase_always_passes(self):
        fp = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert _validate_state_growth(fp, fp, "Formal Analysis & Quality") is True
        assert _validate_state_growth(fp, fp, "Synthesis & Debate") is True

    def test_re_analysis_is_growth_phase(self):
        fp = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert _validate_state_growth(fp, fp, "Re-Analysis") is False

    def test_reanalysis_is_growth_phase(self):
        fp = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert _validate_state_growth(fp, fp, "Reanalysis") is False

    def test_detection_is_growth_phase(self):
        fp = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert _validate_state_growth(fp, fp, "Fallacy Detection") is False


class TestRunPhaseGrowthHook:
    """Integration: _run_phase re-prompts when agent produces no state change."""

    @pytest.fixture
    def mock_state(self):
        state = MagicMock()
        state.identified_arguments = {}
        state.identified_fallacies = {}
        state.counter_arguments = []
        state.jtms_beliefs = {}
        state.dung_frameworks = {}
        state.aspic_results = []
        state.belief_revision_results = []
        state.nl_to_logic_translations = []
        state.fol_analysis_results = []
        state.propositional_analysis_results = []
        state.modal_analysis_results = []
        state._next_agent_designated = None
        state.final_conclusion = None
        return state

    def _make_noop_agent(self, name: str = "MockAgent"):
        """Agent that returns content but never modifies state."""
        agent = MagicMock()
        agent.name = name
        response = MagicMock()
        response.content = "I analyzed the text but did not register any findings."
        agent.invoke = MagicMock(return_value=AsyncIterator([response]))
        return agent

    def _make_growth_agent(self, state, name: str = "GrowthAgent"):
        """Agent that adds an argument when invoked."""
        call_count = 0

        def make_invoke():
            nonlocal call_count

            async def _invoke(history):
                nonlocal call_count
                call_count += 1
                resp = MagicMock()
                if call_count == 1:
                    resp.content = "Analyzing text..."
                else:
                    # Simulate growth on re-prompt
                    state.identified_arguments = {"arg_1": "new argument"}
                    resp.content = "Added argument via add_identified_argument"
                yield resp

            return _invoke

        agent = MagicMock()
        agent.name = name
        agent.invoke = MagicMock(side_effect=make_invoke())
        return agent

    @pytest.mark.asyncio
    async def test_no_re_prompt_when_disabled(self, mock_state):
        """When enable_growth_validation=False, no re-prompts occur."""
        agent = self._make_noop_agent()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.AgentGroupChat",
            create=True,
            side_effect=ImportError("disabled for test"),
        ):
            messages = await _run_phase(
                [agent],
                "Test prompt",
                max_turns=2,
                phase_name="Extraction & Detection",
                state=mock_state,
                enable_growth_validation=False,
            )

        re_prompts = [m for m in messages if m.get("re_prompt")]
        growth_msgs = [m for m in messages if m.get("type") == "growth_validation"]
        assert len(re_prompts) == 0
        assert len(growth_msgs) == 0

    @pytest.mark.asyncio
    async def test_re_prompt_triggers_on_no_growth(self, mock_state):
        """In growth-expecting phase, no-growth turn triggers re-prompt."""
        agent = self._make_growth_agent(mock_state)

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.AgentGroupChat",
            create=True,
            side_effect=ImportError("disabled for test"),
        ):
            messages = await _run_phase(
                [agent],
                "Test prompt",
                max_turns=2,
                phase_name="Extraction & Detection",
                state=mock_state,
                enable_growth_validation=True,
                growth_re_prompt_limit=2,
            )

        # Should have at least one re_prompt entry
        re_prompts = [m for m in messages if m.get("re_prompt")]
        assert len(re_prompts) >= 1, f"Expected re-prompt, got messages: {messages}"

        # Growth happened on re-prompt
        assert len(mock_state.identified_arguments) == 1

        # Telemetry present
        growth_msgs = [m for m in messages if m.get("type") == "growth_validation"]
        assert len(growth_msgs) == 1
        assert growth_msgs[0]["re_prompt_count"] >= 1

    @pytest.mark.asyncio
    async def test_no_re_prompt_in_non_growth_phase(self, mock_state):
        """Synthesis phase should NOT trigger re-prompts."""
        agent = self._make_noop_agent()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.AgentGroupChat",
            create=True,
            side_effect=ImportError("disabled for test"),
        ):
            messages = await _run_phase(
                [agent],
                "Test prompt",
                max_turns=2,
                phase_name="Synthesis & Debate",
                state=mock_state,
                enable_growth_validation=True,
            )

        re_prompts = [m for m in messages if m.get("re_prompt")]
        growth_msgs = [m for m in messages if m.get("type") == "growth_validation"]
        assert len(re_prompts) == 0
        assert len(growth_msgs) == 0

    @pytest.mark.asyncio
    async def test_backward_compat_default_is_enabled(self, mock_state):
        """Default enable_growth_validation=True preserves new behavior."""
        agent = self._make_growth_agent(mock_state)

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.AgentGroupChat",
            create=True,
            side_effect=ImportError("disabled for test"),
        ):
            messages = await _run_phase(
                [agent],
                "Test prompt",
                max_turns=2,
                phase_name="Extraction & Detection",
                state=mock_state,
            )

        # Growth happened via re-prompt
        assert len(mock_state.identified_arguments) == 1


class AsyncIterator:
    """Helper to wrap a list as an async iterator for mock agent.invoke()."""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration

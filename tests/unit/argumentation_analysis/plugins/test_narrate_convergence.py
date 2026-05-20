"""Tests for Track CC: LLM prose layer over convergent synthesis (#636).

Validates that narrate_convergence:
- Falls back gracefully to template narrative when no kernel is configured
- Falls back when no convergent verdicts exist (score < 2)
- Falls back on LLM exception
- Calls invoke_prompt with a grounded prompt when verdicts + kernel available
- Returns LLM prose when the call succeeds
- _build_prose_prompt embeds arg IDs and method names from evidence
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    NarrativeSynthesisPlugin,
    _build_prose_prompt,
    build_convergent_synthesis,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_kernel():
    """Minimal mock kernel exposing async invoke_prompt."""
    kernel = MagicMock()
    kernel.invoke_prompt = AsyncMock(return_value="Mocked LLM prose output.")
    return kernel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _convergent_state() -> UnifiedAnalysisState:
    """State with arg_1 flagged by 3 independent methods (convergence score=3)."""
    state = UnifiedAnalysisState("Test discourse for LLM prose narration.")
    state.add_argument("A weak argument susceptible to multiple analytical methods.")
    # Signal 1: fallacy targeting arg_1
    state.add_fallacy("straw_man", "Distortion of original position.", "arg_1")
    # Signal 2: low quality score (< QUALITY_WEAK_THRESHOLD=5.0)
    state.add_quality_score("arg_1", {"clarte": 2.0, "coherence": 2.5}, 2.5)
    # Signal 3: counter-argument with target_arg_id
    state.add_counter_argument(
        "A weak argument susceptible to multiple analytical methods.",
        "This argument misrepresents the opposing view.",
        "reductio",
        0.8,
        "arg_1",
    )
    return state


def _convergent_state_json() -> str:
    state = _convergent_state()
    return json.dumps(
        {
            "identified_arguments": {
                k: (v if isinstance(v, dict) else {"description": str(v)})
                for k, v in (state.identified_arguments or {}).items()
            },
            "identified_fallacies": state.identified_fallacies or {},
            "argument_quality_scores": state.argument_quality_scores or {},
            "counter_arguments": state.counter_arguments or [],
            "jtms_beliefs": {},
            "dung_frameworks": {},
        },
        ensure_ascii=False,
        default=str,
    )


def _single_method_state_json() -> str:
    """State with arg_1 flagged by 1 method only — no convergence."""
    return json.dumps(
        {
            "identified_arguments": {"arg_1": {"description": "solo arg"}},
            "identified_fallacies": {
                "f1": {
                    "type": "ad_hominem",
                    "justification": "attack on person",
                    "target_argument_id": "arg_1",
                }
            },
            "argument_quality_scores": {},
            "counter_arguments": [],
            "jtms_beliefs": {},
            "dung_frameworks": {},
        }
    )


# ---------------------------------------------------------------------------
# _build_prose_prompt
# ---------------------------------------------------------------------------


class TestBuildProsePrompt:
    """_build_prose_prompt embeds grounded evidence in the prompt."""

    def test_contains_arg_id(self):
        state = _convergent_state()
        synthesis = build_convergent_synthesis(state)
        prompt = _build_prose_prompt(synthesis)
        assert "arg_1" in prompt

    def test_contains_method_names(self):
        state = _convergent_state()
        synthesis = build_convergent_synthesis(state)
        prompt = _build_prose_prompt(synthesis)
        assert "sophisme" in prompt
        assert "qualite faible" in prompt

    def test_contains_structural_conclusion(self):
        state = _convergent_state()
        synthesis = build_convergent_synthesis(state)
        prompt = _build_prose_prompt(synthesis)
        assert synthesis["conclusion"] in prompt

    def test_no_convergence_shows_placeholder(self):
        state = UnifiedAnalysisState("test")
        state.add_argument("strong arg")
        synthesis = build_convergent_synthesis(state)
        assert not synthesis["convergent_verdicts"]
        prompt = _build_prose_prompt(synthesis)
        assert "no convergent" in prompt.lower()

    def test_returns_str(self):
        state = _convergent_state()
        synthesis = build_convergent_synthesis(state)
        assert isinstance(_build_prose_prompt(synthesis), str)


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


class TestNarrateConvergenceFallback:
    """narrate_convergence falls back gracefully in all failure modes."""

    @pytest.mark.asyncio
    async def test_fallback_no_kernel_returns_str(self):
        plugin = NarrativeSynthesisPlugin(kernel=None)
        result = await plugin.narrate_convergence(state_json=_convergent_state_json())
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_fallback_no_verdicts_no_llm_call(self, fake_kernel):
        """Single-method arg (score=1) → no convergence → invoke_prompt not called."""
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        result = await plugin.narrate_convergence(
            state_json=_single_method_state_json()
        )
        fake_kernel.invoke_prompt.assert_not_called()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_fallback_on_llm_exception(self, fake_kernel):
        """invoke_prompt raises → graceful fallback, no exception propagated."""
        fake_kernel.invoke_prompt = AsyncMock(side_effect=RuntimeError("API down"))
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        result = await plugin.narrate_convergence(state_json=_convergent_state_json())
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_fallback_on_empty_llm_response(self, fake_kernel):
        """Empty LLM string → fallback to template narrative."""
        fake_kernel.invoke_prompt = AsyncMock(return_value="")
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        result = await plugin.narrate_convergence(state_json=_convergent_state_json())
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_fallback_on_bad_json(self):
        """Malformed JSON → parsed as empty state → template narrative."""
        plugin = NarrativeSynthesisPlugin(kernel=None)
        result = await plugin.narrate_convergence(state_json="not-json{{{")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# LLM prose path (mock kernel)
# ---------------------------------------------------------------------------


class TestNarrateConvergenceWithMockedKernel:
    """narrate_convergence calls invoke_prompt and surfaces its prose."""

    @pytest.mark.asyncio
    async def test_llm_prose_returned(self, fake_kernel):
        expected = "Mocked LLM prose: convergent analysis of arg_1."
        fake_kernel.invoke_prompt = AsyncMock(return_value=expected)
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        result = await plugin.narrate_convergence(state_json=_convergent_state_json())
        assert expected in result

    @pytest.mark.asyncio
    async def test_invoke_prompt_called_once(self, fake_kernel):
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        await plugin.narrate_convergence(state_json=_convergent_state_json())
        fake_kernel.invoke_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_prompt_contains_arg_id_and_method(self, fake_kernel):
        """The prompt passed to invoke_prompt contains evidence details."""
        captured: list = []

        async def capture(prompt, **kwargs):
            captured.append(prompt)
            return "prose"

        fake_kernel.invoke_prompt = capture
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        await plugin.narrate_convergence(state_json=_convergent_state_json())

        assert captured, "invoke_prompt was not called"
        prompt = captured[0]
        assert "arg_1" in prompt
        assert "sophisme" in prompt

    @pytest.mark.asyncio
    async def test_result_is_always_str(self, fake_kernel):
        """str() is called on invoke_prompt result."""
        fake_kernel.invoke_prompt = AsyncMock(return_value=42)
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        result = await plugin.narrate_convergence(state_json=_convergent_state_json())
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Plugin construction
# ---------------------------------------------------------------------------


class TestNarrativeSynthesisPluginInit:
    """NarrativeSynthesisPlugin accepts optional kernel without breaking BB."""

    def test_no_kernel_default(self):
        plugin = NarrativeSynthesisPlugin()
        assert plugin._kernel is None

    def test_kernel_stored(self, fake_kernel):
        plugin = NarrativeSynthesisPlugin(kernel=fake_kernel)
        assert plugin._kernel is fake_kernel

    def test_synthesize_still_works(self):
        plugin = NarrativeSynthesisPlugin()
        result = plugin.synthesize(state_json="{}")
        assert isinstance(result, str)

    def test_convergent_synthesize_still_works(self):
        plugin = NarrativeSynthesisPlugin()
        result = plugin.convergent_synthesize(state_json="{}")
        data = json.loads(result)
        assert "narrative" in data
        assert "convergent_verdicts" in data


# ---------------------------------------------------------------------------
# Integration (requires real LLM — skipped without API key)
# ---------------------------------------------------------------------------


@pytest.mark.requires_api
class TestNarrateConvergenceIntegration:
    """Integration test with real LLM service (skipped without API key)."""

    @pytest.mark.asyncio
    async def test_real_llm_returns_non_empty_prose(self):
        from semantic_kernel import Kernel
        from argumentation_analysis.core.llm_service import create_llm_service

        kernel = Kernel()
        kernel.add_service(create_llm_service("narration_test"))
        plugin = NarrativeSynthesisPlugin(kernel=kernel)
        result = await plugin.narrate_convergence(state_json=_convergent_state_json())
        assert isinstance(result, str)
        assert len(result) > 0, "Expected non-empty prose from LLM"

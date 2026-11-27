"""#3658 items 46a and 46b — a cut act names its cut, and the acts carry their
own ceiling.

**46a.** On the c22 panel every act stopped at exactly 8 192 tokens, and the
record said *« le LLM n'a rien produit »* — a cause the code had not observed.
A cap spent on the route's reasoning before the first word is not a mute
model, and an act cut mid-text was not recorded at all: seven documents came
out with an empty act, one was PASSED by the #3458 guard with two truncated
acts. ``weave`` now reads the call's OWN ``finish_reason`` (the item-41 idiom,
#3658 item 36d) and names the cut in both shapes.

**46b.** The shared ``PHASE_MAX_TOKENS`` (8 192) was measured on JSON phases;
the acts write prose after a reasoning pass and get their own ``ACT_MAX_TOKENS``.

**46f.** 46b sized that value on ``180 / 2 = 90 s`` per call. The deadline the
transport actually applies is *not* 90 s: ``PhaseBudgetTransport`` rewrites each
attempt's timeout to ``compose_attempt_deadline(180)`` = **80 s**
(``(180 - 10 - 10) / 2``, capped at the 90 s client default), so a call that ran
to a 16 384-token cap spent 76 to 80 s and could expire instead of stopping on
``length`` — retried, billed twice, act empty and unreported. The value is now
derived **from that composed deadline**, which the witness below reads on the
production seam (the workflow definition for the budget, ``network_utils`` for
the composition) rather than from a copy of the arithmetic.

Seat-free: doubles and fakes only, zero network, zero paid call.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents.utils.finish_reason import FinishReason

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.config.settings import settings
from argumentation_analysis.core.utils.network_utils import (
    PhaseBudgetTransport,
    phase_attempt_budget,
    phase_transport_observer,
)
from argumentation_analysis.orchestration.workflows import build_spectacular_workflow
from argumentation_analysis.reporting.restitution.llm_weaving import (
    MUTE_FAILURE,
    cut_code,
    weave,
)


def _double(text, finish_reason=None, cap=None):
    """A plain callable exposing the finish reason, as a test double does."""

    async def call(prompt: str) -> str:
        return text

    call.last_finish_reason = finish_reason
    call.last_max_tokens = cap
    return call


# ---------------------------------------------------------------------------
# 46a — the cut is named, in both shapes
# ---------------------------------------------------------------------------


class TestTheCutIsNamed:
    def test_an_empty_cut_says_the_cut_not_a_mute_model(self):
        outcome = asyncio.run(weave("p", _double("", "length", 16_384), "Acte II"))
        assert outcome.narrative == ""
        assert "finish_reason=length" in outcome.failure
        assert "plafond 16384" in outcome.failure
        assert outcome.failure != MUTE_FAILURE
        # ``cut`` is the same reason: the caller files it under the act's code.
        assert outcome.cut == outcome.failure

    def test_a_truncated_cut_keeps_its_text_and_records_the_cut(self):
        outcome = asyncio.run(
            weave("p", _double("un récit coupé", "length", 16_384), "Acte II")
        )
        assert outcome.narrative == "un récit coupé"
        assert outcome.failure == ""
        assert "coupé au milieu du texte" in outcome.cut

    def test_the_wording_does_not_claim_prose_that_survived(self):
        """The two shapes are distinct facts: nothing kept, or truncated."""
        empty = asyncio.run(weave("p", _double("", "length", 8_192), "Acte I"))
        cut = asyncio.run(weave("p", _double("début", "length", 8_192), "Acte I"))
        assert "rien n'a été produit" in empty.failure
        assert "rien n'a été produit" not in cut.cut
        assert empty.cut != cut.cut

    def test_a_stopped_call_that_is_not_a_length_stays_a_mute_model(self):
        """Control: the new signal does not over-reach — only ``length`` cuts."""
        outcome = asyncio.run(weave("p", _double("", "stop", 16_384), "Acte II"))
        assert outcome.failure == MUTE_FAILURE
        assert outcome.cut == ""

    def test_a_double_that_exposes_nothing_is_not_a_cut(self):
        """A callable with no finish reason says nothing about the call; the
        motif must not be invented from its silence."""
        outcome = asyncio.run(weave("p", _double(""), "Acte II"))
        assert outcome.failure == MUTE_FAILURE
        assert outcome.cut == ""

    def test_the_enum_and_the_string_are_one_signal(self):
        """SK hands a ``FinishReason`` str-enum; the raw path hands a string.
        ``length`` is read either way — the seam is one seam."""
        from_enum = asyncio.run(
            weave("p", _double("", FinishReason.LENGTH, 16_384), "Acte II")
        )
        from_str = asyncio.run(weave("p", _double("", "length", 16_384), "Acte II"))
        assert from_enum.cut and from_enum.cut == from_str.cut

    def test_the_code_is_per_act(self):
        """Distinct acts file distinct codes: a global 'a cut happened' key
        would lose which act the reader is missing."""
        assert cut_code("act1_framing") != cut_code("act2_narrative")
        assert cut_code("act2_narrative") == "act2_narrative_cut_length"


# ---------------------------------------------------------------------------
# 46a + 46b — the SK path, captured where the acts really call it
# ---------------------------------------------------------------------------


class _FakeResult:
    """SK's ``FunctionResult`` shape: the completion OBJECT survives in
    ``value``, and ``str()`` is its text (SK's ``__str__`` takes ``value[0]``)."""

    def __init__(self, text: str, reason) -> None:
        self.value = [SimpleNamespace(finish_reason=reason)]
        self._text = text

    def __str__(self) -> str:
        return self._text


class _FakeKernel:
    """Stands in for ``semantic_kernel.Kernel`` at the act call sites."""

    captured: list = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def add_service(self, service) -> None:  # noqa: D401 - nothing to do
        pass

    def get_prompt_execution_settings_from_service_id(self, service_id):
        # The REAL settings class the acts receive in production — no network:
        # the service is never called, only its settings are serialised.
        kernel = Kernel()
        kernel.add_service(
            OpenAIChatCompletion(
                service_id="fake-openai",
                ai_model_id="fake-model",
                api_key="test-key-not-a-secret",
            )
        )
        return kernel.get_prompt_execution_settings_from_service_id("fake-openai")

    async def invoke_prompt(self, **kwargs):
        _FakeKernel.captured.append(kwargs["settings"])
        return _FakeResult("un récit court.", FinishReason.LENGTH)


_RESULT = SimpleNamespace(
    narrative="un récit court.",
    status="woven",
    gate_verdict=None,
    degraded={},
    degraded_reasons={},
    read_license={},
    # act1's own carriers; empty is the honest value and each invoke reads them.
    interpretive_question="",
    announced_checks=[],
    conclusion="",
)

ACTS = [
    (
        "act1_framing",
        "argumentation_analysis.reporting.restitution.act1_framing_plugin"
        ".build_act1_framing",
        ic._invoke_act1_framing,
    ),
    (
        "act2_narrative",
        "argumentation_analysis.reporting.restitution.act2_narrative_plugin"
        ".build_act2_narrative",
        ic._invoke_act2_narrative,
    ),
    (
        "act3_conclusion",
        "argumentation_analysis.reporting.restitution.act3_conclusion_plugin"
        ".build_act3_conclusion",
        ic._invoke_act3_conclusion,
    ),
]


@pytest.mark.parametrize(("name", "target", "invoke"), ACTS)
def test_each_act_carries_its_own_ceiling(monkeypatch, name, target, invoke):
    """The captured settings of each act carry ACT_MAX_TOKENS — serialised, so
    the wire form is what is read, not a field assignment that never leaves."""
    monkeypatch.setattr("semantic_kernel.Kernel", _FakeKernel)
    monkeypatch.setattr(
        "argumentation_analysis.core.llm_service.create_llm_service",
        lambda service_id=None: object(),
    )
    _FakeKernel.captured = []
    seen = []

    async def builder(state, llm_callable=None):
        seen.append(llm_callable)
        return _RESULT

    with patch(target, builder):
        asyncio.run(invoke("un texte", {}))

    assert seen and seen[0] is not None, f"{name}: no callable was wired"
    asyncio.run(seen[0]("un prompt"))

    settings = _FakeKernel.captured[-1]
    assert settings.prepare_settings_dict().get("max_tokens") == 13_824
    assert settings.prepare_settings_dict().get("max_tokens") == ic._ACT_MAX_TOKENS


@pytest.mark.parametrize(("name", "target", "invoke"), ACTS)
def test_each_act_exposes_the_finish_reason_of_its_call(
    monkeypatch, name, target, invoke
):
    """46a's seam on the production path: the callable the act received now
    reports the call's own stop, and the cap it spent."""
    monkeypatch.setattr("semantic_kernel.Kernel", _FakeKernel)
    monkeypatch.setattr(
        "argumentation_analysis.core.llm_service.create_llm_service",
        lambda service_id=None: object(),
    )
    _FakeKernel.captured = []
    seen = []

    async def builder(state, llm_callable=None):
        seen.append(llm_callable)
        return _RESULT

    with patch(target, builder):
        asyncio.run(invoke("un texte", {}))

    callable_ = seen[0]
    asyncio.run(callable_("un prompt"))
    assert callable_.last_finish_reason == FinishReason.LENGTH
    assert callable_.last_max_tokens == 13_824


class TestTheCeilingDecision:
    def test_the_act_ceiling_is_the_sized_value(self):
        """Pinned: a silent change to the number reddens, as it did for the
        shared cap. The arithmetic lives at the constant's comment."""
        assert ic._ACT_MAX_TOKENS == 13_824

    def test_the_act_ceiling_is_named_apart_from_the_phase_cap(self):
        """The shared value was measured on JSON phases; the acts are prose
        after reasoning. One number for both is what failed at c22."""
        assert ic._ACT_MAX_TOKENS != ic._PHASE_MAX_TOKENS

    def test_the_act_ceiling_rides_the_declared_field(self):
        """The SK 1.44 finding (R1204) still holds for the act cap: a key
        added after construction is never serialised."""
        settings = _FakeKernel().get_prompt_execution_settings_from_service_id("x")
        out = ic._with_phase_max_tokens(settings, cap=ic._ACT_MAX_TOKENS)
        assert out.prepare_settings_dict().get("max_tokens") == 13_824

    def test_zero_still_omits_the_param(self, monkeypatch):
        monkeypatch.setattr(ic, "_ACT_MAX_TOKENS", 0)
        settings = _FakeKernel().get_prompt_execution_settings_from_service_id("x")
        out = ic._with_phase_max_tokens(settings, cap=ic._ACT_MAX_TOKENS)
        assert "max_tokens" not in out.prepare_settings_dict()


# ---------------------------------------------------------------------------
# 46f — the ceiling is bounded by the deadline the transport really applies
# ---------------------------------------------------------------------------

ACT_NAMES = ("act1_framing", "act2_narrative", "act3_conclusion")

#: c22's measured throughput, taken at the LOW end of the 205-215 tok/s range:
#: the slow end is the one that binds a deadline (8 192 tokens in 38-40 s).
RATE_TOKENS_PER_SECOND = 205.0
#: 46b's own allowance for prompt handling and the first token, per call.
PROMPT_ALLOWANCE_SECONDS = 12.0
#: The largest per-call completion measured so far (doc_J, Act II: 26 225
#: completion tokens over 2 calls) — the cap must keep covering it.
MEASURED_MAX_PER_CALL = 13_100


class _RecordingTransport(httpx.AsyncBaseTransport):
    """Records the request ``PhaseBudgetTransport`` passes down."""

    def __init__(self) -> None:
        self.requests: list = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, content=b"{}")


async def _deadline_the_transport_applies(budget: float):
    """The read deadline one attempt really gets, read on the production seam.

    The budget is published exactly as ``workflow_dsl`` publishes it, then
    ``PhaseBudgetTransport`` — the transport the acts' HTTP client is wired
    onto — rewrites the request's timeout. Both what it recorded and what it
    wrote into ``extensions["timeout"]`` come back, so the witness below never
    re-runs the arithmetic itself.
    """
    observer: dict = {}
    inner = _RecordingTransport()
    transport = PhaseBudgetTransport(inner)
    token_budget = phase_attempt_budget.set(float(budget))
    token_observer = phase_transport_observer.set(observer)
    try:
        await transport.handle_async_request(
            httpx.Request(
                "POST",
                "https://example.invalid/v1/chat/completions",
                extensions={"timeout": httpx.Timeout(settings.network.default_timeout)},
            )
        )
    finally:
        phase_transport_observer.reset(token_observer)
        phase_attempt_budget.reset(token_budget)
    return float(observer["attempt_deadline"]), inner.requests[-1].extensions["timeout"]


def _the_acts_budget() -> float:
    """The smallest phase budget the three acts declare, read from the
    workflow the panel runs — never from a copy of the number."""
    workflow = build_spectacular_workflow()
    budgets = {
        phase.name: float(phase.timeout_seconds)
        for phase in workflow.phases
        if phase.name in ACT_NAMES and phase.timeout_seconds is not None
    }
    assert set(budgets) == set(ACT_NAMES), f"acts missing a budget: {budgets}"
    return min(budgets.values())


class TestTheCeilingFitsTheAttemptDeadline:
    """46b sized the cap on ``180 / 2``; the transport applies 80 s, not 90."""

    def test_the_three_acts_still_declare_a_budget_to_build_the_witness_on(self):
        """Control: with no declared budget the witness below would compare
        against nothing and pass for the wrong reason."""
        assert _the_acts_budget() > 0

    def test_the_applied_deadline_is_the_composed_one(self):
        composed, applied = asyncio.run(
            _deadline_the_transport_applies(_the_acts_budget())
        )
        assert composed == applied["read"], (
            "the recorded deadline and the one written to the wire disagree: "
            f"{composed} vs {applied}"
        )
        assert composed < settings.network.default_timeout, (
            f"{composed}s does not bind: the phase budget no longer constrains "
            "the acts, so this witness measures nothing"
        )

    def test_a_call_that_runs_to_the_cap_fits_inside_that_deadline(self):
        composed, _applied = asyncio.run(
            _deadline_the_transport_applies(_the_acts_budget())
        )
        generation = ic._ACT_MAX_TOKENS / RATE_TOKENS_PER_SECOND
        assert generation + PROMPT_ALLOWANCE_SECONDS <= composed, (
            f"a call spending all {ic._ACT_MAX_TOKENS} tokens takes "
            f"{generation:.1f}s at {RATE_TOKENS_PER_SECOND:.0f} tok/s; with "
            f"{PROMPT_ALLOWANCE_SECONDS:.0f}s of prompt handling that exceeds the "
            f"{composed:.1f}s attempt deadline, so it can expire instead of "
            "stopping on 'length' — retried, billed twice, act empty and unreported"
        )

    def test_the_cap_still_covers_the_largest_call_measured(self):
        """The trade-off is named, not taken silently: fitting the deadline
        must not walk under what the acts already need."""
        assert ic._ACT_MAX_TOKENS >= MEASURED_MAX_PER_CALL, (
            f"{ic._ACT_MAX_TOKENS} is below the {MEASURED_MAX_PER_CALL}-token "
            "per-call maximum already measured: the acts would now be cut "
            "where they used to complete"
        )

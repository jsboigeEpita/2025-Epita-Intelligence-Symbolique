"""#2331 — the production quality phase constructs its evaluator WITH its
agentic wiring, and the degraded paths are named and traced in STATE.

Guard design (dispatch R1032 DoD): the assertion lives at the CONSTRUCTION
site, never on scores — refutation counts legitimately fluctuate between
passes (7↔9 of 12 measured), so a score-count guard would read as flake.
The double substitution: (1) the evaluator class is replaced by a spy that
records what it was CONSTRUCTED with, (2) the LLM-callable factory is
replaced by a counter — and the guard asserts the construction received the
callable AND that it was invoked through the wiring (a decorative, never
called wiring would pass a weaker guard).

The phase is resolved through the PRODUCTION registry path
    (setup_registry -> find_for_capability("argument_quality") -> .invoke)
not imported as a private symbol — the guard must redden if the wiring stops
travelling the dispatch production actually uses.

Born-red proof (stash procedure): applied alone on today's main, the first
test fails at ``last_agentic_llm is counting_llm`` — main constructs the
evaluator bare, the spy records None.
"""

import threading
import time
from typing import Any, Dict, Optional

import pytest

import argumentation_analysis.orchestration.invoke_callables as invoke_callables
from argumentation_analysis.agents.core.quality import quality_evaluator as qe_module
from argumentation_analysis.orchestration.registry_setup import setup_registry

_UNSET: Any = object()

_MINIMAL_EVAL = {
    "note_finale": 1.0,
    "note_max_applicable": 1.0,
    "scores_par_vertu": {"clarte": 1.0},
    "statuts_par_vertu": {"clarte": "evaluee"},
}


class _WiringSpyEvaluator:
    """Records construction-time wiring; mirrors the sentinel semantics of
    the real ``evaluate`` (explicit per-call value, including None, wins)."""

    last_agentic_llm: Any = "__never_constructed__"
    llm_invocations: int = 0

    def __init__(
        self, detectors: Optional[Dict] = None, agentic_llm: Any = None
    ) -> None:
        self._wired = agentic_llm
        _WiringSpyEvaluator.last_agentic_llm = agentic_llm

    def evaluate(
        self,
        text: str,
        agentic_llm: Any = _UNSET,
        context_level: Any = None,
    ) -> Dict[str, Any]:
        effective = self._wired if agentic_llm is _UNSET else agentic_llm
        if effective is not None:
            effective(text)
            _WiringSpyEvaluator.llm_invocations += 1
        return dict(_MINIMAL_EVAL)


class _TraceSpyState:
    """Minimal state: records trace entries so a test can assert that the
    degradation is traced IN STATE, not only in a log."""

    def __init__(self) -> None:
        self.entries: list[Dict[str, Any]] = []

    def add_trace_entry(self, **kwargs: Any) -> None:
        self.entries.append(kwargs)


def _production_quality_invoke():
    """Resolve the quality phase invoke the way production dispatch does."""
    registry = setup_registry(include_optional=False)
    matches = registry.find_for_capability("argument_quality")
    invokes = [m for m in matches if getattr(m, "invoke", None) is not None]
    assert invokes, "no production invoke registered for argument_quality"
    return invokes[0].invoke


def _context(n_args: int = 3, state: Any = None) -> Dict[str, Any]:
    args = [
        {"text": f"Argument numero {i} : une affirmation suffisamment longue."}
        for i in range(1, n_args + 1)
    ]
    ctx: Dict[str, Any] = {"phase_extract_output": {"arguments": args}}
    if state is not None:
        ctx["_state_object"] = state
    return ctx


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kill the (#290) enrichment pass's client — the verdict must be decided
    by the substituted doubles, never a collateral network call (#1583)."""
    monkeypatch.setattr(invoke_callables, "_get_openai_client", lambda: (None, ""))


async def test_construction_site_wires_a_live_agentic_llm(monkeypatch):
    """THE guard — the production phase constructs the evaluator with a
    non-None agentic callable, and that callable is actually invoked."""
    invoke = _production_quality_invoke()

    calls = {"n": 0}

    def counting_llm(prompt: str) -> str:
        calls["n"] += 1
        return "1.0"

    _WiringSpyEvaluator.last_agentic_llm = "__never_constructed__"
    _WiringSpyEvaluator.llm_invocations = 0
    monkeypatch.setattr(qe_module, "ArgumentQualityEvaluator", _WiringSpyEvaluator)
    # raising=False: on pre-#2331 main the factory does not exist yet — the
    # test must still reach the CONSTRUCTION assertion, not die patching.
    monkeypatch.setattr(
        invoke_callables,
        "_make_agentic_llm_callable",
        lambda: (counting_llm, "stub", "stub-model"),
        raising=False,
    )
    _no_network(monkeypatch)

    out = await invoke("fallback text", _context())

    assert _WiringSpyEvaluator.last_agentic_llm is counting_llm, (
        "construction site received no wiring — the phase builds the "
        "evaluator bare (#2331)"
    )
    assert (
        _WiringSpyEvaluator.llm_invocations >= 1
    ), "wiring is decorative: the constructed callable was never invoked"
    assert out["agentic_wiring"]["mode"] == "wired"
    assert out["agentic_wiring"]["units_degraded"] == {}


async def test_no_route_is_a_named_degraded_path_traced_in_state(monkeypatch):
    """No key/no route ⇒ explicit lexical fallback, traced in the STATE
    output and the state trace — never only in a log."""
    invoke = _production_quality_invoke()

    _WiringSpyEvaluator.last_agentic_llm = "__never_constructed__"
    _WiringSpyEvaluator.llm_invocations = 0
    monkeypatch.setattr(qe_module, "ArgumentQualityEvaluator", _WiringSpyEvaluator)
    monkeypatch.setattr(
        invoke_callables,
        "_make_agentic_llm_callable",
        lambda: (None, "no_route", ""),
        raising=False,
    )
    _no_network(monkeypatch)
    state = _TraceSpyState()

    out = await invoke("fallback text", _context(state=state))

    assert _WiringSpyEvaluator.last_agentic_llm is None  # honest construction
    assert _WiringSpyEvaluator.llm_invocations == 0  # zero model calls
    assert out["per_argument_scores"], "lexical fallback produced no scores"
    assert out["agentic_wiring"]["mode"] == "degraded_no_route"
    assert out["agentic_wiring"]["units_degraded"] == {}
    summaries = [e.get("summary", "") for e in state.entries]
    assert any(
        "degraded_no_route" in s for s in summaries
    ), f"degraded mode not traced in state: {summaries}"


async def test_agentic_unit_failure_degrades_that_unit_in_state(monkeypatch):
    """A unit whose agentic chain fails (AgenticDetectorError) falls back to
    lexical for THAT unit; the reason lands in the state output. Provenance
    decides: model output absent ⇒ degraded, but never silent."""
    from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
        AgenticDetectorError,
    )

    invoke = _production_quality_invoke()

    class _FailingThenLexicalEvaluator(_WiringSpyEvaluator):
        wired_calls = 0
        lexical_calls = 0

        def evaluate(
            self,
            text: str,
            agentic_llm: Any = _UNSET,
            context_level: Any = None,
        ) -> Dict[str, Any]:
            effective = self._wired if agentic_llm is _UNSET else agentic_llm
            if effective is not None:
                _FailingThenLexicalEvaluator.wired_calls += 1
                raise AgenticDetectorError("simulated unparseable chain step")
            _FailingThenLexicalEvaluator.lexical_calls += 1
            return dict(_MINIMAL_EVAL)

    def stub_llm(prompt: str) -> str:
        return "1.0"

    monkeypatch.setattr(
        qe_module, "ArgumentQualityEvaluator", _FailingThenLexicalEvaluator
    )
    monkeypatch.setattr(
        invoke_callables,
        "_make_agentic_llm_callable",
        lambda: (stub_llm, "stub", "stub-model"),
        raising=False,
    )
    _no_network(monkeypatch)

    out = await invoke("fallback text", _context(n_args=3))

    assert _FailingThenLexicalEvaluator.wired_calls == 3
    assert _FailingThenLexicalEvaluator.lexical_calls == 3
    degraded = out["agentic_wiring"]["units_degraded"]
    assert set(degraded) == {"arg_1", "arg_2", "arg_3"}
    assert all(v.startswith("AgenticDetectorError") for v in degraded.values())
    assert out["agentic_wiring"]["mode"] == "wired"  # route intact, units degraded
    assert set(out["per_argument_scores"]) == {"arg_1", "arg_2", "arg_3"}


async def test_concurrency_is_explicitly_bounded_and_enforced(monkeypatch):
    """The bound is an explicit wiring parameter (≤ the 8-units/doc phase cap)
    and the semaphore actually enforces it at runtime."""
    invoke = _production_quality_invoke()
    bound = invoke_callables._AGENTIC_QUALITY_MAX_WORKERS
    assert isinstance(bound, int) and 1 <= bound <= 8

    class _TrackingEvaluator(_WiringSpyEvaluator):
        lock = threading.Lock()
        in_flight = 0
        max_in_flight = 0

        def evaluate(
            self,
            text: str,
            agentic_llm: Any = _UNSET,
            context_level: Any = None,
        ) -> Dict[str, Any]:
            with _TrackingEvaluator.lock:
                _TrackingEvaluator.in_flight += 1
                _TrackingEvaluator.max_in_flight = max(
                    _TrackingEvaluator.max_in_flight,
                    _TrackingEvaluator.in_flight,
                )
            time.sleep(0.05)
            try:
                return super().evaluate(text, agentic_llm, context_level)
            finally:
                with _TrackingEvaluator.lock:
                    _TrackingEvaluator.in_flight -= 1

    def stub_llm(prompt: str) -> str:
        return "1.0"

    _TrackingEvaluator.max_in_flight = 0
    monkeypatch.setattr(qe_module, "ArgumentQualityEvaluator", _TrackingEvaluator)
    monkeypatch.setattr(
        invoke_callables,
        "_make_agentic_llm_callable",
        lambda: (stub_llm, "stub", "stub-model"),
        raising=False,
    )
    _no_network(monkeypatch)

    out = await invoke("fallback text", _context(n_args=8))

    assert set(out["per_argument_scores"]) == {
        f"arg_{i}" for i in range(1, 9)
    }  # 8 units/doc cap still holds
    assert (
        _TrackingEvaluator.max_in_flight <= bound
    ), f"observed {_TrackingEvaluator.max_in_flight} > declared bound {bound}"
    assert _TrackingEvaluator.max_in_flight >= 2, "no parallelism observed"


def test_agentic_callable_routes_through_the_raw_cache_2324(monkeypatch, tmp_path):
    """#2324 — le callable agentic passe par le seam BO-3 (#1473).

    Mesuré sur le replay du test de délégation : ce callable partait en
    direct — 12-14 POSTs /v1/chat/completions en LIVE par run « replay »,
    egress non-nul dans une bande qui attend 0, et phase qualité
    non-déterministe au rejeu. Né-rouge EN VALEURS : avant réparation, le
    client double est appelé en direct et aucune ``LLMCacheMiss`` ne monte ;
    après, en replay sur un cache vide, l'appel lève ``LLMCacheMiss`` et le
    client double reste VIERGE — jamais de live silencieux.
    """
    import openai as openai_module
    from argumentation_analysis.services.llm_cache import (
        LLMCacheMiss,
        reset_raw_cache,
    )

    monkeypatch.setenv("LLM_CACHE_MODE", "replay")
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path))
    reset_raw_cache()

    class _Msg:
        content = "1.0"

    class _Choice:
        message = _Msg()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        calls: list = []

        def create(self, **kwargs):
            _Completions.calls.append(kwargs)
            return _Response()

    class _Chat:
        completions = _Completions()

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = _Chat()

    _Completions.calls.clear()
    monkeypatch.setattr(
        invoke_callables,
        "_resolve_llm_route",
        lambda: ("sk-test-local", "https://example.invalid", "gpt-5.6-luna", "openai"),
    )
    monkeypatch.setattr(openai_module, "OpenAI", _FakeOpenAI)

    agentic_llm, route, model_id = invoke_callables._make_agentic_llm_callable()
    assert (
        agentic_llm is not None
    ), f"aucun callable construit (route={route!r}) — le test ne mesure rien"

    with pytest.raises(LLMCacheMiss):
        agentic_llm("un prompt de detecteur")

    assert not _Completions.calls, (
        f"le callable est parti en LIVE malgré le mode replay "
        f"(seam BO-3 contourné) : {_Completions.calls}"
    )
    reset_raw_cache()

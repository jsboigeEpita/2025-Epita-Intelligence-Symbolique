"""#2095 — the AI Shield must not report "no threat" for a text it never read.

Three independent silences on the same theme, pinned here in one file so the
contrast is visible in a single read:

1+2. `LLMValidatorLayer` returned `score=0.0` — the value that means "safe" —
     both when no API key was configured and when the provider raised. The
     caller could not tell an unanalysed text from a clean one. The layer now
     RAISES; the Shield's fail-open policy decides, and `error_type` names the
     failure. The pair (score 0.0, passed True) still appears under fail-open —
     that is the policy working — but it now carries the name of the error, so
     it is no longer indistinguishable from a clean pass.

3.   `validate_input` drives a blocking OpenAI client. It now runs off the
     event-loop thread at the single async production boundary
     (`_invoke_ai_shield`), rather than making the whole `ShieldLayer.validate`
     ABC async for one blocking leaf.

4.   A `blocked` verdict was an ordinary COMPLETED phase, so the phases
     downstream ran on input the shield had refused. It is now a terminal
     verdict, and the skip reason names the shield — not the #1909
     non-argumentative stop that shares the same code path.

5.   `state.ai_shield_results` was written and never read in production. It has
     a read-only reader now, which returns the latest verdict without appending.

Every fixture is synthetic (privacy HARD); no dataset content, no network, no
JVM. The provider is faked at the module the layer imports it from.
"""

import threading
from typing import Any, Dict, List

import pytest

from argumentation_analysis.core.capability_registry import CapabilityRegistry
from argumentation_analysis.orchestration.invoke_callables import _invoke_ai_shield
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowBuilder,
    WorkflowExecutor,
)
from argumentation_analysis.services.ai_shield import Shield, ShieldLayer
from argumentation_analysis.services.ai_shield.layers.llm_validator import (
    LLMValidatorLayer,
)


def _unavailable() -> type:
    """The exception class #2095 introduces — imported HERE, not at module level.

    On the original tree a module-level import of a symbol that does not exist
    yet collapses this whole file into a single collection error, and a
    né-rouge that reddens as one error proves nothing about which tests measure
    what. Local import keeps the failure per-test.
    """
    from argumentation_analysis.services.ai_shield.layers.llm_validator import (
        LLMValidatorUnavailable,
    )

    return LLMValidatorUnavailable


SYNTHETIC_INPUT = "Question de test synthetique, aucun contenu de corpus."

# The provider stub is installed where the layer imports it (`from openai
# import OpenAI`, resolved at call time) — patching anywhere else would leave
# the real constructor in place and hit the network.
OPENAI_SITE = "openai.OpenAI"


@pytest.fixture(autouse=True)
def _no_llm_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test in this file may reach a provider.

    `LLMValidatorLayer.__init__` falls back to `os.environ["OPENAI_API_KEY"]`
    when handed an empty string. With the repo's `.env` loaded, that fallback
    found a real key, so the "no key" tests did not raise — they made a live
    call (measured: 2 requests to api.openai.com, flagged by the #1787 egress
    gate). Clearing the variables is what makes "no key" mean no key.
    """
    for var in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)


class _RecordingLayer(ShieldLayer):
    """A layer that records which thread it ran on, then passes everything."""

    def __init__(self) -> None:
        super().__init__(name="thread_probe", threshold=1.0)
        self.thread_ident: int | None = None

    def validate(self, text: str, **kwargs: Any) -> Any:
        self.thread_ident = threading.get_ident()
        return self._make_result(score=0.0)


# --- items 1 + 2: an unanalysed text is not a clean text ---------------------


class TestValidatorFailureIsNamed:
    def test_missing_key_raises_instead_of_scoring_zero(self) -> None:
        """Item 2: no key used to render `score=0.0` ("no threat")."""
        layer = LLMValidatorLayer(api_key="")
        with pytest.raises(_unavailable()):
            layer.validate(SYNTHETIC_INPUT)

    def test_provider_failure_propagates_with_its_own_type(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Item 1: a generic LLM failure must not become a threat score either.

        The layer adds no `except` — the provider's exception travels with its
        own type so `LayerResult.error_type` reports what actually broke.
        """

        def _boom(**kwargs: Any) -> Any:
            raise ConnectionError("synthetic provider outage")

        monkeypatch.setattr(OPENAI_SITE, _boom, raising=True)
        layer = LLMValidatorLayer(api_key="sk-synthetic-not-a-real-key")
        with pytest.raises(ConnectionError):
            layer.validate(SYNTHETIC_INPUT)

    def test_fail_open_shield_names_the_failure_it_swallowed(self) -> None:
        """The fail-open path still runs — with the error NAMED.

        This is the case the issue is about: before, `passed=True` with a score
        of 0.0 and nothing else was byte-identical to "clean text". The pair is
        still allowed to pass here (that is what fail-open means), but the
        result now carries the exception type and a reason that says so.
        """
        shield = Shield(layers=[LLMValidatorLayer(api_key="")], fail_open=True)

        result = shield.validate_input(SYNTHETIC_INPUT)

        assert result.blocked is False, "fail_open lets the run continue"
        layer_errors = [lr for lr in result.layer_results if lr.error_type]
        assert len(layer_errors) == 1, "the swallowed error must be recorded"
        assert layer_errors[0].error_type == "LLMValidatorUnavailable"
        assert "no API key" in layer_errors[0].reason

    def test_fail_closed_shield_blocks_when_the_validator_cannot_run(self) -> None:
        """The same failure under `strict` must refuse the input."""
        shield = Shield(layers=[LLMValidatorLayer(api_key="")], fail_open=False)

        result = shield.validate_input(SYNTHETIC_INPUT)

        assert result.blocked is True
        assert result.layer_results[0].error_type == "LLMValidatorUnavailable"

    def test_a_real_verdict_is_still_returned(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control: the raise is not unconditional.

        Without this, every test above would also pass on a layer that simply
        threw on any input — the instrument would measure nothing.
        """

        class _Response:
            choices = [
                type(
                    "Choice",
                    (),
                    {
                        "finish_reason": "stop",
                        "message": type(
                            "Msg",
                            (),
                            {
                                "content": (
                                    '{"threat_score": 0.91, '
                                    '"categories": ["prompt_injection"], '
                                    '"explanation": "synthetic"}'
                                )
                            },
                        )(),
                    },
                )()
            ]

        class _Completions:
            def create(self, **kwargs: Any) -> Any:
                return _Response()

        class _Client:
            def __init__(self, **kwargs: Any) -> None:
                self.chat = type("Chat", (), {"completions": _Completions()})()

        monkeypatch.setattr(OPENAI_SITE, _Client, raising=True)
        layer = LLMValidatorLayer(api_key="sk-synthetic-not-a-real-key")

        result = layer.validate(SYNTHETIC_INPUT)

        assert result.score == pytest.approx(0.91)
        assert result.passed is False
        assert result.details["categories"] == ["prompt_injection"]


# --- item 3: the blocking call runs off the event loop -----------------------


class TestShieldCallIsOffloaded:
    async def test_validate_input_runs_off_the_event_loop_thread(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The single blocking leaf is offloaded, not the whole ABC.

        Measured by thread identity: a layer invoked inline observes the event
        loop's own thread. `asyncio.to_thread` gives it a worker thread.
        """
        probe = _RecordingLayer()
        monkeypatch.setattr(
            "argumentation_analysis.services.ai_shield.load_preset",
            lambda *args, **kwargs: Shield(layers=[probe], fail_open=True),
        )
        loop_thread = threading.get_ident()

        output = await _invoke_ai_shield(SYNTHETIC_INPUT, {})

        assert probe.thread_ident is not None, "the layer must have run"
        assert probe.thread_ident != loop_thread, (
            "a blocking provider call on the event loop stalls every "
            "concurrent phase (#2095 item 3)"
        )
        assert output["shield_available"] is True


# --- item 4: a blocked verdict stops the pipeline ---------------------------


SHIELD_BLOCKED_OUTPUT: Dict[str, Any] = {
    "shield_available": True,
    "blocked": True,
    "overall_score": 0.93,
    "passed": False,
    "reason": "Layer llm_validator error: LLMValidatorUnavailable",
    "layer_results": [
        {"layer": "llm_validator", "score": 0.93, "passed": False, "error_type": None}
    ],
}

SHIELD_CLEAN_OUTPUT: Dict[str, Any] = {
    "shield_available": True,
    "blocked": False,
    "overall_score": 0.02,
    "passed": True,
    "reason": "",
    "layer_results": [{"layer": "heuristic", "score": 0.02, "passed": True}],
}


def _registry(shield_output: Any, spy: List[str], shield_capability: str) -> Any:
    async def shield_invoke(text: str, context: Dict[str, Any]) -> Any:
        spy.append("shield")
        return shield_output

    async def quality_invoke(text: str, context: Dict[str, Any]) -> Any:
        spy.append("quality")
        return {"score": 0.5}

    registry = CapabilityRegistry()
    registry.register_agent(
        name="synthetic_shield",
        agent_class=type("AS", (), {}),
        capabilities=[shield_capability],
        invoke=shield_invoke,
    )
    registry.register_agent(
        name="synthetic_quality",
        agent_class=type("QA", (), {}),
        capabilities=["argument_quality"],
        invoke=quality_invoke,
    )
    return registry


def _shield_workflow(
    shield_capability: str = "input_validation", optional: bool = False
) -> Any:
    return (
        WorkflowBuilder("shield_2095")
        .add_phase("shield", capability=shield_capability, optional=optional)
        .add_phase("quality", capability="argument_quality", depends_on=["shield"])
        .build()
    )


class TestBlockedVerdictStopsThePipeline:
    async def test_blocked_shield_leaves_descendants_skipped(self) -> None:
        """The forbidden continuation, pinned.

        Before the fix the shield phase was an ordinary COMPLETED phase: the
        `quality` provider was invoked on an input the shield had refused.
        """
        spy: List[str] = []
        executor = WorkflowExecutor(
            _registry(SHIELD_BLOCKED_OUTPUT, spy, "input_validation")
        )

        results = await executor.execute(_shield_workflow(), input_data=SYNTHETIC_INPUT)

        assert results["shield"].status == PhaseStatus.COMPLETED
        assert results["shield"].terminal is True
        assert results["quality"].status == PhaseStatus.SKIPPED
        assert spy == [
            "shield"
        ], "no descendant may consume an input the shield refused (#2095)"

    async def test_the_skip_reason_names_the_shield_not_the_1909_stop(self) -> None:
        """Two terminal COMPLETED senses share one code path — keep them apart.

        The #1909 non-argumentative stop and the #2095 shield block are both
        terminal COMPLETED phases, so the descendant skip is produced by the
        same branch. Without a dedicated wording the shield block is logged as
        "non-argumentative input", naming a classification that never happened.
        """
        spy: List[str] = []
        executor = WorkflowExecutor(
            _registry(SHIELD_BLOCKED_OUTPUT, spy, "input_validation")
        )

        results = await executor.execute(_shield_workflow(), input_data=SYNTHETIC_INPUT)

        reason = results["quality"].error or ""
        assert "shield verdict" in reason
        assert "non-argumentative" not in reason, (
            "the shield did not classify the document; the #1909 wording would "
            "attribute to it a decision it never made"
        )

    async def test_a_clean_verdict_does_not_stop_anything(self) -> None:
        """Counterweight guard: the stop keys on the verdict, not on the phase.

        A shield that ran and passed must leave the pipeline intact — otherwise
        the fix would block every run that enables the shield at all.
        """
        spy: List[str] = []
        executor = WorkflowExecutor(
            _registry(SHIELD_CLEAN_OUTPUT, spy, "input_validation")
        )

        results = await executor.execute(_shield_workflow(), input_data=SYNTHETIC_INPUT)

        assert results["shield"].terminal is False
        assert results["quality"].status == PhaseStatus.COMPLETED
        assert spy == ["shield", "quality"]

    async def test_absent_provider_is_skipped_not_read_as_a_negative_verdict(
        self,
    ) -> None:
        """`optional=True` means "no provider", which is not a `blocked` verdict.

        The DoD calls this confusion out by name: a phase that can never run
        must not be mistaken for one that ran and refused.
        """
        spy: List[str] = []
        registry = _registry(SHIELD_BLOCKED_OUTPUT, spy, "input_validation")
        # Unregister the shield's capability: the executor finds no provider.
        registry.unregister("synthetic_shield")
        executor = WorkflowExecutor(registry)

        results = await executor.execute(
            _shield_workflow(optional=True), input_data=SYNTHETIC_INPUT
        )

        assert results["shield"].status == PhaseStatus.SKIPPED
        assert results["shield"].terminal is False
        assert results["quality"].status == PhaseStatus.COMPLETED
        assert spy == ["quality"]


# --- item 4, production form: the barrier must exist in the INJECTED workflow ---

# The tests above pin the executor's skip branch on graphs whose shield edge
# was written by hand. Production never writes that edge by hand: it calls
# `_inject_shield_phase`, which for a long time appended `shield` as a root
# SIBLING — same DAG level as the original roots, no `depends_on` edge
# anywhere — so the terminal verdict was inert outside these tests (R995
# review). The class below exercises the workflow that function actually
# returns.


def _inject(original: Any) -> Any:
    """The injector #2095's rework introduces — imported HERE, not at module
    level, so that on the pre-fix tree the failure is per-test and not a
    single collection error that would mask which tests measure what."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        _inject_shield_phase,
    )

    return _inject_shield_phase(original)


def _multi_root_original() -> Any:
    """A workflow shaped like production: two independent roots plus a child.

    Every phase is a root or hangs off one — exactly the shape the injector
    must gate without touching the non-roots.
    """
    return (
        WorkflowBuilder("original_2095")
        .add_phase("root_a", capability="argument_quality")
        .add_phase("root_b", capability="adversarial_debate")
        .add_phase("child", capability="governance_simulation", depends_on=["root_a"])
        .build()
    )


def _multi_root_registry(shield_output: Any, spy: List[str]) -> Any:
    async def shield_invoke(text: str, context: Dict[str, Any]) -> Any:
        spy.append("shield")
        return shield_output

    async def root_a_invoke(text: str, context: Dict[str, Any]) -> Any:
        spy.append("root_a")
        return {"score": 0.5}

    async def root_b_invoke(text: str, context: Dict[str, Any]) -> Any:
        spy.append("root_b")
        return {"winner": "root_b"}

    async def child_invoke(text: str, context: Dict[str, Any]) -> Any:
        spy.append("child")
        return {"consensus": 0.9}

    registry = CapabilityRegistry()
    for name, caps, fn in (
        ("synthetic_shield", ["input_validation"], shield_invoke),
        ("synthetic_root_a", ["argument_quality"], root_a_invoke),
        ("synthetic_root_b", ["adversarial_debate"], root_b_invoke),
        ("synthetic_child", ["governance_simulation"], child_invoke),
    ):
        registry.register_agent(
            name=name,
            agent_class=type(name, (), {}),
            capabilities=caps,
            invoke=fn,
        )
    return registry


class TestShieldInjectionIsARealBarrier:
    def test_every_root_is_gated_and_only_the_roots(self) -> None:
        """The injected workflow carries the edge the old comment only claimed.

        Before the rework the injector appended `shield` beside the roots and
        said "after shield" in a comment; the DAG contained no such order. The
        proof is the execution order of the workflow it returns: shield alone
        at level 0, the original roots one level later.
        """
        injected = _inject(_multi_root_original())

        assert injected.get_execution_order() == [
            ["shield"],
            ["root_a", "root_b"],
            ["child"],
        ]
        # Non-roots are untouched: they inherit the gate transitively.
        child = injected.get_phase("child")
        assert child is not None and child.depends_on == ["root_a"]

    def test_the_original_workflow_is_not_mutated(self) -> None:
        """The handed-in definition may be shared — gate copies, never writes.

        A mutated original would leak `depends_on=["shield"]` into every later
        run of a pre-built workflow, even ones that never enable the shield.
        """
        original = _multi_root_original()
        _inject(original)

        for name in ("root_a", "root_b"):
            phase = original.get_phase(name)
            assert (
                phase is not None and phase.depends_on == []
            ), f"{name} was mutated in place — the injector must copy roots"
        assert original.get_execution_order() == [["root_a", "root_b"], ["child"]]

    async def test_blocked_verdict_prevents_every_original_root_from_starting(
        self,
    ) -> None:
        """The forbidden continuation, on the workflow production builds.

        Two independent roots, so the assertion is "no root ran", not "the one
        root I wired didn't". The child must fall with them: it has no
        substrate once its dependency was skipped.
        """
        spy: List[str] = []
        executor = WorkflowExecutor(_multi_root_registry(SHIELD_BLOCKED_OUTPUT, spy))

        results = await executor.execute(
            _inject(_multi_root_original()), input_data=SYNTHETIC_INPUT
        )

        assert results["shield"].status == PhaseStatus.COMPLETED
        assert results["shield"].terminal is True
        for name in ("root_a", "root_b", "child"):
            assert (
                results[name].status == PhaseStatus.SKIPPED
            ), f"{name} must not consume an input the shield refused"
        assert spy == ["shield"]

    async def test_a_clean_verdict_lets_the_injected_roots_run(self) -> None:
        """Counterweight: the barrier keys on the verdict, not on the phase.

        A shield that ran and passed must leave the gated pipeline running —
        otherwise enabling the shield would disable the analysis.
        """
        spy: List[str] = []
        executor = WorkflowExecutor(_multi_root_registry(SHIELD_CLEAN_OUTPUT, spy))

        results = await executor.execute(
            _inject(_multi_root_original()), input_data=SYNTHETIC_INPUT
        )

        for name in ("shield", "root_a", "root_b", "child"):
            assert results[name].status == PhaseStatus.COMPLETED
        assert results["shield"].terminal is False
        assert sorted(spy) == ["child", "root_a", "root_b", "shield"]

    async def test_a_skipped_shield_lets_the_injected_roots_run(self) -> None:
        """`optional=True` survives the barrier: no provider is not a verdict.

        This is the DoD's named confusion, now at the injection boundary: the
        gate must open for a phase that could not run, and only close on one
        that ran and refused.
        """
        spy: List[str] = []
        registry = _multi_root_registry(SHIELD_BLOCKED_OUTPUT, spy)
        registry.unregister("synthetic_shield")
        executor = WorkflowExecutor(registry)

        results = await executor.execute(
            _inject(_multi_root_original()), input_data=SYNTHETIC_INPUT
        )

        assert results["shield"].status == PhaseStatus.SKIPPED
        assert results["shield"].terminal is False
        for name in ("root_a", "root_b", "child"):
            assert results[name].status == PhaseStatus.COMPLETED
        assert "shield" not in spy


# --- item 5: the verdict has a reader ---------------------------------------


class _State:
    """Minimal stand-in: the reader touches this one attribute only."""

    def __init__(self, entries: Any) -> None:
        self.ai_shield_results = entries


class TestShieldVerdictReader:
    def test_reads_the_verdict_without_appending(self) -> None:
        """Read-only is the point: copying the writer would double every run.

        A workflow can invoke a shield phase twice (`input_validation` plus
        `output_filtering`); a reader that appended would grow the list by one
        on every read and report the wrong count forever after.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _shield_verdict,
        )

        state = _State([SHIELD_BLOCKED_OUTPUT])

        verdict = _shield_verdict(state)

        assert verdict is not None
        assert verdict["blocked"] is True
        assert verdict["overall_score"] == pytest.approx(0.93)
        assert len(state.ai_shield_results) == 1, "the reader must not append"

    def test_returns_the_latest_entry(self) -> None:
        """Entries are appended in run order; the pipeline acted on the last."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _shield_verdict,
        )

        state = _State([SHIELD_CLEAN_OUTPUT, SHIELD_BLOCKED_OUTPUT])

        verdict = _shield_verdict(state)

        assert verdict is not None
        assert verdict["blocked"] is True

    def test_extracts_the_error_types_of_the_layers_that_raised(self) -> None:
        """A `blocked` verdict must not hide WHICH layer failed (#2144)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _shield_verdict,
        )

        blocked_with_error = {
            **SHIELD_BLOCKED_OUTPUT,
            "layer_results": [
                {"layer": "heuristic", "score": 0.0, "passed": True},
                {
                    "layer": "llm_validator",
                    "score": 1.0,
                    "passed": False,
                    "error_type": "LLMValidatorUnavailable",
                },
            ],
        }
        state = _State([blocked_with_error])

        verdict = _shield_verdict(state)

        assert verdict is not None
        assert verdict["error_types"] == ["LLMValidatorUnavailable"]

    @pytest.mark.parametrize(
        "entries",
        [None, [], "not-a-list", [None], [["not", "a", "dict"]]],
        ids=["missing", "empty", "not-a-list", "entry-not-a-dict", "entry-a-list"],
    )
    def test_answers_none_when_the_shield_never_ran(self, entries: Any) -> None:
        """Absent, empty and malformed all mean "no verdict" — never a crash."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _shield_verdict,
        )

        assert _shield_verdict(_State(entries)) is None

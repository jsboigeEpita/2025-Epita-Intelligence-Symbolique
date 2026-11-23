"""#3658 item 36b — the persona calls that sent NO cap carry the shared one.

The coordinator's free doc_J re-run (R1205, comment 7082191642) measured where
a persona call without its own ``max_completion_tokens`` lands: the strategist
(2 calls on 2), ``coverage_review`` and ``cross_passage_consistency`` all
stopped at exactly 4 096 tokens — claudish's ingress default for an uncapped
call — and the strategist's two stops left the phase in ``parse_error``.

The #3670 doctrine applies to this seam unchanged: the ONE shared ceiling
(``PHASE_MAX_TOKENS``, measured from the phases that carried our configured
cap) rides every call site that had none. A site's OWN cap still wins (the
first reading's inventory bound, #3511); ``PHASE_MAX_TOKENS=0`` omits the key
entirely (the pre-fix wire form).

Born red: on ``main`` the persona call sent no cap key at all, so the capture
witnesses below failed on every named site.

Measured alongside (read-only, this PR changes nothing there): the ``fol``
phase (Pass 1 signature + Pass 2 formula batches) and the hierarchical
fallacy descent (``create_llm_service`` sets no default; the plugin's
``OpenAIPromptExecutionSettings`` carry only ``function_choice_behavior``)
also send NO cap — their measured stops (3 on 7 calls, 12 on 293) stopped at
the same route default — and neither path reads ``finish_reason``: a
``length`` stop is kept, never retried.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from argumentation_analysis.orchestration import invoke_callables as ic

_OPENAI_BASE_URL = "https://api.openai.com/v1"

#: The sites the measured pass named, plus the historian — the fourth persona
#: with no cap of its own. It had no stop on that pass, but it rides the same
#: seam: capping only the three that happened to stop would leave the fourth
#: one route-default away from the same failure.
UNCAPPED_PERSONA_SITES = (
    "strategist",
    "coverage_review",
    "cross_passage_consistency",
    "historian",
)


class _FakeCompletion:
    """The minimal shape the persona callable reads off the reply."""

    def __init__(self, content: str = "{}") -> None:
        self.choices = [
            SimpleNamespace(
                index=0,
                message=SimpleNamespace(role="assistant", content=content),
                finish_reason="stop",
            )
        ]


class _StubClient:
    """A client whose ``chat.completions.create`` RECORDS its kwargs."""

    def __init__(self) -> None:
        self.recorded: List[Dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> _FakeCompletion:
        self.recorded.append(kwargs)
        return _FakeCompletion()


def _route_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the canonical resolver at an openai-compatible base URL.

    The route is read from the environment by ``resolve_chat_endpoint`` — the
    resolver every client is built from — so the witness sets the environment
    rather than a private knob: the seam the run really uses.
    """
    for name in (
        "OPENROUTER_BASE_URL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_CHAT_MODEL_ID",
        "ANTHROPIC_CHAT_MODEL_ID",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-36b")
    monkeypatch.setenv("OPENAI_BASE_URL", _OPENAI_BASE_URL)
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "model-36b")
    # the cache is off: the witness measures the request the SDK receives
    monkeypatch.setenv("LLM_CACHE_MODE", "off")


async def _persona_wire_kwargs(
    monkeypatch: pytest.MonkeyPatch, site: str, **builder_kwargs: Any
) -> Dict[str, Any]:
    """Run one persona call through the stub client; return its wire kwargs."""
    client = _StubClient()
    monkeypatch.setattr(ic, "_get_openai_client", lambda: (client, "model-36b"))
    callable_, reason = ic._build_persona_callable(site, **builder_kwargs)
    assert callable_ is not None, f"no persona callable: {reason}"
    await callable_("prompt asking for ONLY this JSON")
    assert client.recorded, "the persona call never reached the stub client"
    return client.recorded[0]


class TestTheKnobTheSitesRide:
    """The shared ceiling is the one #3670 measured, not a new number."""

    def test_the_shared_phase_cap_is_the_measured_default(self) -> None:
        assert ic._PHASE_MAX_TOKENS == 8192, (
            "the persona seam rides PHASE_MAX_TOKENS — if this default moves, "
            "it is a decision this witness must be re-measured against"
        )


class TestUncappedPersonasCarryTheSharedCap:
    """The wire form: every persona with no cap of its own sends the shared one."""

    @pytest.mark.parametrize("site", UNCAPPED_PERSONA_SITES)
    async def test_the_call_carries_the_shared_cap(
        self, monkeypatch: pytest.MonkeyPatch, site: str
    ) -> None:
        _route_env(monkeypatch)
        kwargs = await _persona_wire_kwargs(monkeypatch, site)
        assert kwargs.get("max_completion_tokens") == ic._PHASE_MAX_TOKENS, (
            f"{site}: the persona call sent no shared cap "
            f"(max_completion_tokens={kwargs.get('max_completion_tokens')!r}) "
            "— an uncapped call stops at the route's ingress default, which "
            "left the strategist in parse_error on the measured doc_J pass"
        )

    async def test_a_sites_own_cap_still_wins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The first reading's OWN bound (#3511) is not overridden by the
        shared ceiling — precedence, not coincidence of values."""
        _route_env(monkeypatch)
        kwargs = await _persona_wire_kwargs(
            monkeypatch, "first_reading", max_completion_tokens=4321
        )
        assert kwargs.get("max_completion_tokens") == 4321, (
            "a site's own cap lost to the shared one — the first reading's "
            "inventory bound is a decision, not a default"
        )

    async def test_zero_omits_the_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``PHASE_MAX_TOKENS=0`` is the documented escape hatch: the key is
        ABSENT, not None — sending ``max_completion_tokens=None`` is a
        different request."""
        _route_env(monkeypatch)
        monkeypatch.setattr(ic, "_PHASE_MAX_TOKENS", 0)
        kwargs = await _persona_wire_kwargs(monkeypatch, "strategist")
        assert (
            "max_completion_tokens" not in kwargs
        ), "PHASE_MAX_TOKENS=0 must omit the key entirely (pre-fix wire form)"


class _Capture:
    """3511-style funnel capture: kwargs as the guarded funnel receives them."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.kwargs: Dict[str, Any] = {}

        async def fake_guarded(client: Any, **kwargs: Any) -> _FakeCompletion:
            self.kwargs.update(kwargs)
            return _FakeCompletion()

        monkeypatch.setattr(ic, "_get_openai_client", lambda: (object(), "model-36b"))
        monkeypatch.setattr(
            ic,
            "_resolve_llm_route",
            lambda: (None, _OPENAI_BASE_URL, "model-36b"),
        )
        monkeypatch.setattr(ic, "_guarded_chat_completion", fake_guarded)


class TestTheInvokePathsDeliverTheCap:
    """End-to-end per site: the invoke (the seam the run actually calls)
    builds its persona and the call carries the shared cap."""

    async def test_strategist_invoke(self, monkeypatch: pytest.MonkeyPatch) -> None:
        capture = _Capture(monkeypatch)
        state = SimpleNamespace(raw_text="Le orateur affirme que X.")
        await ic._invoke_strategic_read(state.raw_text, {"_state_object": state})
        assert capture.kwargs.get("max_completion_tokens") == ic._PHASE_MAX_TOKENS, (
            "the strategist's call (2 stops on 2, phase left in parse_error) "
            "still sends no cap"
        )

    async def test_coverage_review_invoke(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        capture = _Capture(monkeypatch)
        document = "La these est que X. Le texte continue par un developpement."
        state = SimpleNamespace(
            raw_text=document,
            identified_arguments={},
            argument_provenance={},
            analysis_coverage={},
            defining_moves={
                "moves": [
                    {
                        "slot": "thesis",
                        "quote": "La these est que X.",
                        "offset": 0,
                        "kind": "thesis",
                        "basis": "first_reading",
                    }
                ],
                "status": "ok",
                "basis": "first_reading",
            },
        )
        await ic._invoke_coverage_review(document, {"_state_object": state})
        assert (
            capture.kwargs.get("max_completion_tokens") == ic._PHASE_MAX_TOKENS
        ), "the coverage_review call (a measured 4 096 stop) still sends no cap"

    async def test_cross_passage_invoke(self, monkeypatch: pytest.MonkeyPatch) -> None:
        capture = _Capture(monkeypatch)
        document = "La these est que X. Un pilier ensuite."
        state = SimpleNamespace(
            raw_text=document,
            defining_moves={
                "moves": [
                    {
                        "slot": "thesis",
                        "quote": "La these est que X.",
                        "offset": 0,
                        "kind": "thesis",
                        "basis": "first_reading",
                    }
                ],
                "status": "ok",
                "basis": "first_reading",
            },
        )

        class _StubBridge:
            def check_consistency(
                self, belief_set: str, logic_type: str = "propositional"
            ) -> Any:
                return True, "SAT"

        import argumentation_analysis.agents.core.logic.tweety_bridge as tb

        monkeypatch.setattr(tb, "TweetyBridge", _StubBridge)
        await ic._invoke_cross_passage_consistency(document, {"_state_object": state})
        assert capture.kwargs.get("max_completion_tokens") == ic._PHASE_MAX_TOKENS, (
            "the cross_passage_consistency call (a measured 4 096 stop) still "
            "sends no cap"
        )

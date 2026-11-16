"""#3600 — the five JSON personas send the ONE per-provider ``response_format``.

The persona route (``_build_persona_callable``) built its request without a
``response_format``, while the repository already owns that decision in ONE
place (#3096): ``resolved_json_response_format()`` answers
``{"type": "json_object"}`` on an openai-compatible endpoint and NOTHING on the
anthropic endpoint (where ``json_object`` is a measured 400 — probes 20/10).

The witness below is a STUB CLIENT that records the kwargs of a persona call —
the wire form, not a shape read back from a log. It states two things:

* on an openai-compatible base URL, the persona call carries
  ``response_format == {"type": "json_object"}``;
* on an anthropic base URL, the persona call carries NO ``response_format``
  key at all — sending ``response_format=None`` is a different request, so the
  key must be absent, not None.

The five personas (historian, first reading, cross-passage consistency check,
coverage review, strategist) all ask for JSON in their prompts, which is what
the openai ``json_object`` mode requires in the messages.

Born red: before the fix the persona call carried no ``response_format`` on
either route, so the first assertion failed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from argumentation_analysis.core import endpoint_compat
from argumentation_analysis.orchestration import invoke_callables as ic

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"


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


def _route_env(monkeypatch: pytest.MonkeyPatch, base_url: str) -> None:
    """Point the canonical resolver at ``base_url`` and nowhere else.

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
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-3600")
    monkeypatch.setenv("OPENAI_BASE_URL", base_url)
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "model-3600")
    # the cache is off: the witness measures the request the SDK receives
    monkeypatch.setenv("LLM_CACHE_MODE", "off")


async def _persona_call(monkeypatch: pytest.MonkeyPatch, site: str) -> Dict[str, Any]:
    """Run one persona call through the stub client; return its kwargs."""
    client = _StubClient()
    monkeypatch.setattr(ic, "_get_openai_client", lambda: (client, "model-3600"))
    callable_, reason = ic._build_persona_callable(site)
    assert callable_ is not None, f"no persona callable: {reason}"
    await callable_("prompt asking for ONLY this JSON")
    assert client.recorded, "the persona call never reached the stub client"
    return client.recorded[0]


class TestPersonaSendsTheOneDecision:
    """The persona call carries the decision #3096 owns."""

    async def test_openai_compatible_persona_sends_json_object(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _route_env(monkeypatch, _OPENAI_BASE_URL)
        kwargs = await _persona_call(monkeypatch, "historian")
        assert kwargs.get("response_format") == {"type": "json_object"}, (
            "the persona call sent no json_object mode: "
            f"response_format={kwargs.get('response_format')!r}"
        )

    async def test_anthropic_persona_sends_no_response_format_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The anthropic row is prompt-only JSON: the KEY is absent.

        ``response_format=None`` is not the same request as no key, so the
        witness checks the absence of the key, not its value.
        """
        _route_env(monkeypatch, _ANTHROPIC_BASE_URL)
        kwargs = await _persona_call(monkeypatch, "strategist")
        assert "response_format" not in kwargs, (
            "the persona call sent a response_format on the anthropic route "
            f"(a measured 400 there): {kwargs.get('response_format')!r}"
        )


class TestMutationControl:
    """The witness sees the DECISION, not an accident."""

    async def test_the_decision_table_is_what_governs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mutation: the table always answers json_object → the anthropic row
        sends the key → the anthropic witness goes red."""
        _route_env(monkeypatch, _ANTHROPIC_BASE_URL)
        monkeypatch.setattr(
            endpoint_compat,
            "json_response_format",
            lambda base_url, schema_name=None, schema=None: {"type": "json_object"},
        )
        kwargs = await _persona_call(monkeypatch, "strategist")
        assert "response_format" in kwargs, (
            "the mutated decision did not change the wire form — the witness "
            "would not see a regression here"
        )


class TestTheFivePromptsAskForJson:
    """The json_object mode requires the word in the messages (#3600 ask 1a).

    Measured on the prompt builders, not on a recorded corpus document: the
    prompts are code, the corpus is not.
    """

    def _prompt_texts(self) -> Dict[str, str]:
        from argumentation_analysis.agents.core.context.historian import (
            HISTORIAN_PROMPT,
        )
        from argumentation_analysis.agents.core.context.strategist import (
            STRATEGIST_PROMPT,
        )
        from argumentation_analysis.agents.core.reading.coverage_review import (
            COVERAGE_REVIEW_PROMPT,
        )
        from argumentation_analysis.agents.core.reading.cross_passage import (
            _translation_prompt,
        )
        from argumentation_analysis.agents.core.reading.first_reading import (
            build_first_reading_prompt,
        )

        return {
            "historian": HISTORIAN_PROMPT,
            "first_reading": build_first_reading_prompt("Le orateur A affirme que X."),
            "cross_passage_consistency": _translation_prompt(
                [{"id": "p1", "quote": "Le orateur A affirme que X."}]
            ),
            "coverage_review": COVERAGE_REVIEW_PROMPT,
            "strategist": STRATEGIST_PROMPT,
        }

    @pytest.mark.parametrize(
        "site",
        [
            "historian",
            "first_reading",
            "cross_passage_consistency",
            "coverage_review",
            "strategist",
        ],
    )
    def test_prompt_states_json(self, site: str) -> None:
        prompt = self._prompt_texts()[site]
        assert "json" in prompt.lower(), (
            f"{site}: the prompt does not mention JSON — the openai "
            "json_object mode rejects a message that does not"
        )


class TestNoPerSiteFlag:
    """One father: the persona route has no site-specific switch."""

    def test_persona_callable_has_no_response_format_parameter(self) -> None:
        import inspect

        params = inspect.signature(ic._build_persona_callable).parameters
        assert "response_format" not in params, (
            "the persona seam grew a per-site parameter — the decision belongs "
            "to endpoint_compat, not to a call site"
        )

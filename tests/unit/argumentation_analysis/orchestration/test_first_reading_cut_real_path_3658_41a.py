"""#3658 item 41(a) — the missing witness for the REAL 36d capture path.

#3677 delivered the capture but its witnesses drove the producer with a test
double exposing ``last_finish_reason`` directly: nothing measured that the
PRODUCTION callable — ``_build_persona_callable``, the seam the run actually
calls — records the envelope's finish reason and the cap it spent. The
coordinator's dispatch (R1207) asks for exactly that witness: an SDK-shaped
envelope with ``finish_reason="length"`` goes through the real builder, the
returned callable carries ``last_finish_reason`` and ``last_max_tokens``, and
the reading's record names the cut.

The witness reddens if the capture is removed (mutation control measured in
the PR body: one mutation per captured attribute).

Seat-free: invented text, no key on the wire (a stub client records the call
and the cache is off), no network.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List

import pytest

from argumentation_analysis.agents.core.reading import build_first_reading
from argumentation_analysis.orchestration import invoke_callables as ic

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_CAP = 8192

#: Invented document — a real shape, never a corpus sentence.
_DOC = (
    "The speaker opens with a concession: the policy cost the region dearly. "
    "Then the speech claims the effort was worth it, resting on one figure. "
    "It closes by urging the audience to pick a side."
)


class _Envelope:
    """The minimal SDK reply shape the persona callable reads."""

    def __init__(self, content: str, finish_reason: str) -> None:
        self.choices = [
            SimpleNamespace(
                index=0,
                message=SimpleNamespace(role="assistant", content=content),
                finish_reason=finish_reason,
            )
        ]


class _StubClient:
    """A client whose ``chat.completions.create`` replays one envelope."""

    def __init__(self, envelope: _Envelope) -> None:
        self.envelope = envelope
        self.recorded: List[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> _Envelope:
        self.recorded.append(kwargs)
        return self.envelope


def _cut_answer() -> str:
    """A well-formed answer whose quotes the invented document carries."""
    return json.dumps(
        {
            "thesis": {
                "reading": "The effort was worth it",
                "quote": "the effort was worth it",
            },
            "moves": [
                {
                    "reading": "The opening concession",
                    "quote": "the policy cost the region dearly",
                }
            ],
        }
    )


def _route_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the canonical resolver at an openai-compatible base URL.

    The route is read from the environment by the resolver every client is
    built from, so the witness sets the environment rather than a private
    knob: the seam the run really uses (same shape as the 36b witness).
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
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-41a")
    monkeypatch.setenv("OPENAI_BASE_URL", _OPENAI_BASE_URL)
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "model-41a")
    # the cache is off: the witness measures the envelope the callable reads
    monkeypatch.setenv("LLM_CACHE_MODE", "off")


async def _real_callable(monkeypatch: pytest.MonkeyPatch, finish_reason: str):
    client = _StubClient(_Envelope(_cut_answer(), finish_reason))
    monkeypatch.setattr(ic, "_get_openai_client", lambda: (client, "model-41a"))
    llm, reason = ic._build_persona_callable(
        "first_reading", max_completion_tokens=_CAP
    )
    assert llm is not None, f"no persona callable: {reason}"
    await llm("prompt asking for ONLY this JSON")
    assert client.recorded, "the persona call never reached the stub client"
    return llm


class TestTheRealPersonaPathNamesTheCut:
    """The production callable records the envelope's own finish reason."""

    async def test_a_length_envelope_is_captured_on_the_real_callable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _route_env(monkeypatch)
        llm = await _real_callable(monkeypatch, "length")
        assert llm.last_finish_reason == "length", (
            "the production persona callable did not record the envelope's "
            "finish_reason — the reading cannot name a cut it never saw"
        )
        assert llm.last_max_tokens == _CAP, (
            "the production persona callable did not record the cap the call "
            "spent — the record cannot tell an 8 192 stop from a 4 096 one"
        )

    async def test_a_stop_envelope_is_captured_as_not_cut(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control: a complete call reads ``stop``, never degraded."""
        _route_env(monkeypatch)
        llm = await _real_callable(monkeypatch, "stop")
        assert llm.last_finish_reason == "stop"
        state = SimpleNamespace(raw_text=_DOC)
        result = await build_first_reading(state, llm)
        assert result.status == "ok", result.status
        assert not result.to_state().get("degraded"), result.to_state()

    async def test_the_reading_records_degraded_through_the_real_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End to end on the production seam: envelope → capture → record."""
        _route_env(monkeypatch)
        llm = await _real_callable(monkeypatch, "length")
        state = SimpleNamespace(raw_text=_DOC)
        result = await build_first_reading(state, llm)
        assert result.status == "ok", result.status
        payload = result.to_state()
        assert payload.get("degraded") is True, payload
        reason = payload.get("degraded_reason", "")
        assert "finish_reason=length" in reason, reason
        assert f"cap {_CAP}" in reason, reason

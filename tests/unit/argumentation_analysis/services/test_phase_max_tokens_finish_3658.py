"""#3658 follow-up (R1203 dispatch, item 36) — explicit caps + the late finish reason.

(1) The call sites that sent NO explicit max_tokens (the structured-arg
translator behind DeLP/ASPIC, and the three restitution acts) stopped at
claudish's 4096 ingress default on the measured doc_J pass. They now carry
the shared PHASE_MAX_TOKENS ceiling (measured: the phases that carried our
configured cap used 8192). A capture witness reads the settings/kwargs.

(2) _account_sk_usage read the finish reason only up to the FIRST
usage-carrying message: a streamed reply whose usage rides an early chunk
with `length` on the last was counted under calls_without_finish_reason.
The finish pass now covers ALL messages before usage is recorded.

Seat-free: stubs and fakes only, zero network.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.orchestration import structured_arg_translator as sat
from argumentation_analysis.services import llm_cache


class _FakeSettings:
    """The SK settings shape the acts pin the cap on."""

    def __init__(self, extension_data=None):
        self.extension_data = dict(extension_data or {})


class TestExplicitPhaseCaps:
    def test_an_act_without_a_cap_receives_the_shared_ceiling(self):
        settings = _FakeSettings()
        out = ic._with_phase_max_tokens(settings)
        assert out.extension_data["max_tokens"] == 8192

    def test_an_explicit_cap_always_wins(self):
        settings = _FakeSettings({"max_tokens": 12345})
        out = ic._with_phase_max_tokens(settings)
        assert out.extension_data["max_tokens"] == 12345

    def test_the_zero_override_adds_nothing(self, monkeypatch):
        monkeypatch.setattr(ic, "_PHASE_MAX_TOKENS", 0)
        settings = _FakeSettings()
        out = ic._with_phase_max_tokens(settings)
        assert "max_tokens" not in out.extension_data

    async def test_the_translator_sends_an_explicit_cap(self, monkeypatch):
        """Capture witness over the translator's real call path (DeLP/ASPIC):
        the kwargs reaching the guarded completion carry max_tokens."""
        captured: Dict[str, Any] = {}

        async def _fake_guarded(client, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
            )

        monkeypatch.setattr(ic, "_guarded_chat_completion", _fake_guarded)
        monkeypatch.setattr(ic, "_get_openai_client", lambda: (object(), "fake-model"))
        monkeypatch.setattr(ic, "_get_determinism_params", lambda *a, **k: {})
        monkeypatch.setattr(ic, "_parse_json_from_llm", lambda raw: {})
        monkeypatch.setattr(sat, "resolved_json_response_format", lambda *a: (None, ""))
        await sat._llm_extract_relations(
            "a text", ["argument one", "argument two"], "supports"
        )
        assert captured.get("max_tokens") == 8192, captured.keys()


class TestTheLateFinishReason:
    def _stream(self):
        """Usage on the FIRST chunk, `length` on the LAST (the R1203 case)."""
        first = SimpleNamespace(
            finish_reason=None,
            metadata={"usage": {"prompt_tokens": 10, "completion_tokens": 4096}},
        )
        middle = SimpleNamespace(finish_reason=None, metadata={})
        last = SimpleNamespace(finish_reason="length", metadata={})
        return [first, middle, last]

    def test_the_length_on_the_last_message_is_recorded(self, monkeypatch):
        recorded: List[Dict[str, Any]] = []

        def _record(_self, prompt, completion, cost, **kwargs):
            recorded.append(kwargs)

        # UsageStats is slots/frozen: patch at the CLASS level.
        monkeypatch.setattr(type(llm_cache._usage_stats), "record", _record)
        llm_cache._account_sk_usage(self._stream(), model="fake-model")
        assert len(recorded) == 1
        assert recorded[0].get("finish_reason") == "length", recorded

    def test_usage_is_still_counted_once(self, monkeypatch):
        recorded: List[Dict[str, Any]] = []
        monkeypatch.setattr(
            type(llm_cache._usage_stats),
            "record",
            lambda self, *a, **k: recorded.append(k),
        )
        llm_cache._account_sk_usage(self._stream(), model="fake-model")
        assert len(recorded) == 1

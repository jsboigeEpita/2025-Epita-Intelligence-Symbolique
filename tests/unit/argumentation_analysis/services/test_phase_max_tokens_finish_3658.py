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
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.orchestration import structured_arg_translator as sat
from argumentation_analysis.services import llm_cache


def _real_act_settings():
    """The settings the acts receive in production: the class a kernel with an
    OpenAI-compatible service answers (no network — the service is never called)."""
    kernel = Kernel()
    kernel.add_service(
        OpenAIChatCompletion(
            service_id="fake-openai",
            ai_model_id="fake-model",
            api_key="test-key-not-a-secret",
        )
    )
    return kernel.get_prompt_execution_settings_from_service_id("fake-openai")


class TestExplicitPhaseCaps:
    def test_the_cap_reaches_the_serialised_request(self):
        """On the real class, the cap must survive prepare_settings_dict() —
        an extension_data key added after construction does not (SK 1.34 seat,
        1.44 gate, coordinator review R1204)."""
        settings = _real_act_settings()
        out = ic._with_phase_max_tokens(settings)
        assert out.prepare_settings_dict().get("max_tokens") == 8192

    def test_an_explicit_cap_always_wins(self):
        settings = _real_act_settings()
        settings.max_tokens = 12345
        out = ic._with_phase_max_tokens(settings)
        assert out.prepare_settings_dict().get("max_tokens") == 12345

    def test_the_zero_override_adds_nothing(self, monkeypatch):
        monkeypatch.setattr(ic, "_PHASE_MAX_TOKENS", 0)
        settings = _real_act_settings()
        out = ic._with_phase_max_tokens(settings)
        assert "max_tokens" not in out.prepare_settings_dict()

    def test_a_class_spelling_it_max_completion_tokens_is_capped(self):
        class _MctOnly:
            def __init__(self):
                self.max_completion_tokens = None

        out = ic._with_phase_max_tokens(_MctOnly())
        assert out.max_completion_tokens == 8192

    def test_a_class_without_any_cap_field_is_named_once(self, monkeypatch):
        warnings: List[str] = []
        monkeypatch.setattr(
            ic.logger, "warning", lambda *a, **k: warnings.append(str(a))
        )
        monkeypatch.setattr(ic, "_cap_barren_types", [])

        class _Barren:
            pass

        out = ic._with_phase_max_tokens(_Barren())
        assert not hasattr(out, "max_tokens")
        assert len(warnings) == 1 and "_Barren" in warnings[0], warnings
        # named once: a second barren object of the same class stays silent
        ic._with_phase_max_tokens(_Barren())
        assert len(warnings) == 1, warnings

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

"""#3124 — the local_llm phase record names what happened on a real call.

Measured on the coordinator's seat (main ``23cf6df02``, 2026-10-21): one real
call of ``_invoke_local_llm`` on doc_A (56 430 chars) returned
``status: error, wall: 60.2 s, error: "", model: None``. The phase reaches
the endpoint since #3117, but the record is unactionable:

- the error is ``str(exc)`` and an ``httpx.ReadTimeout`` stringifies to
  ``""`` — "error" with nothing to act on, while the 60.2 s wall matches the
  service's fixed ``timeout=60.0``;
- the whole document was sent in one call under that fixed budget, although
  the docstring promised "optionally include upstream extract results";
- the record names the REQUESTED model; the response's own ``model`` field
  (the served model — the alias is served by another model by design) is
  buried in a stringified envelope;
- ``local_llm_results`` has no reader (write-only since #834).

Witnesses (offline, zero spend):

- transport-level: a stubbed ``httpx.MockTransport`` whose chat call raises
  ``httpx.ReadTimeout("")`` — through the REAL ``LocalLLMService``, so the
  formatting is exercised where ``str(exc)`` used to be written;
- phase-level: the stub service raises, and the record names the type and the
  configured budget;
- provenance: a stubbed response announcing model B while model A was
  requested records BOTH, and stores the message content, not the envelope;
- input decision: with an extracted population the phase sends the selected
  units (the #2850 selection) and records it; without one it sends a bounded
  window and records that instead.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, AsyncMock, patch

import httpx
import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm
from argumentation_analysis.services import (
    local_llm_service as local_llm_service_module,
)
from argumentation_analysis.services.local_llm_service import LocalLLMService

CONFIGURED_MODEL = "stub-requested-model-3124"


@pytest.fixture(autouse=True)
def configured_endpoint(monkeypatch):
    monkeypatch.setenv("SELF_HOSTED_LLM_ENDPOINT", "http://local-stub-3124.test/v1")
    monkeypatch.setenv("SELF_HOSTED_LLM_API_KEY", "synthetic-key-3124")
    monkeypatch.setenv("SELF_HOSTED_LLM_MODEL", CONFIGURED_MODEL)
    monkeypatch.delenv("SELF_HOSTED_LLM_TIMEOUT", raising=False)


def _stub_service(answer: Any = None, raises: BaseException | None = None) -> MagicMock:
    spy = MagicMock()
    spy.is_available = AsyncMock(return_value=True)
    spy.model = CONFIGURED_MODEL
    if raises is not None:
        spy.chat_completion = AsyncMock(side_effect=raises)
    else:
        spy.chat_completion = AsyncMock(
            return_value=(
                answer
                if answer is not None
                else {
                    "model": "stub-served-model-3124",
                    "choices": [
                        {
                            "message": {"content": "synthetic local answer"},
                            "finish_reason": "stop",
                        }
                    ],
                }
            )
        )
    return spy


class TestTheErrorNamesWhatHappened:
    async def test_a_read_timeout_through_the_real_service_is_named(self, monkeypatch):
        """DoD 1: the transport raises ReadTimeout whose str() is empty."""

        def respond(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("")  # the empty-message case, exactly

        real_client = httpx.AsyncClient
        service = LocalLLMService(
            endpoint="http://local-stub-3124.test/v1", timeout=60.0
        )

        def local_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
            return real_client(transport=httpx.MockTransport(respond), **kwargs)

        with patch("httpx.AsyncClient", side_effect=local_client):
            result = await service.chat_completion(
                [{"role": "user", "content": "synthetic"}]
            )

        assert result["error"] == "ReadTimeout after 60 s", result["error"]
        assert result["error"] != ""

    async def test_the_phase_record_names_the_type_and_the_budget(self, monkeypatch):
        """DoD 1: the budget comes from configuration, and the record says it."""
        monkeypatch.setenv("SELF_HOSTED_LLM_TIMEOUT", "5")
        spy = _stub_service(raises=httpx.ReadTimeout(""))

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=spy,
        ):
            result = await _invoke_local_llm("synthetic", {})

        assert result["status"] == "error"
        assert "ReadTimeout" in result["error"], result
        assert (
            "5 s" in result["error"]
        ), f"the record must name the configured budget, got {result['error']!r}"
        assert result["timeout_s"] == 5.0

    def test_describe_exception_covers_the_other_shapes(self):
        describe_exception = local_llm_service_module.describe_exception
        assert describe_exception(ValueError("boom")) == "ValueError: boom"
        assert (
            describe_exception(RuntimeError(""), timeout=30.0)
            == "RuntimeError (no message)"
        )
        assert describe_exception(httpx.ConnectError("")) == "ConnectError (no message)"


class TestServedModelAndContent:
    async def test_the_record_carries_both_models_and_the_content(self):
        answer = {
            "model": "stub-served-model-3124",
            "choices": [
                {
                    "message": {"content": "the local tier's answer"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        spy = _stub_service(answer=answer)
        state = UnifiedAnalysisState("synthetic")

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=spy,
        ):
            result = await _invoke_local_llm("synthetic", {"_state_object": state})

        assert result["status"] == "completed"
        assert result["model"] == CONFIGURED_MODEL, "the requested (alias) model"
        assert (
            result["served_model"] == "stub-served-model-3124"
        ), "the record must name the model that answered, read from the response"
        assert result["response"] == "the local tier's answer", (
            "the message content is stored, not the stringified envelope "
            f"({result['response']!r})"
        )


class TestThePhaseDecidesWhatItSends:
    def _state_with_units(self, count: int) -> UnifiedAnalysisState:
        state = UnifiedAnalysisState("DOC-SENTINEL " + "filler " * 4000)
        state.identified_arguments = {
            f"arg_{i}": f"Unit argument number {i} says one thing"
            for i in range(1, count + 1)
        }
        state.argument_provenance = {
            f"arg_{i}": {"producer": "llm_extract", "offset": i * 7}
            for i in range(1, count + 1)
        }
        return state

    async def test_with_units_the_phase_sends_the_selection_not_the_document(self):
        spy = _stub_service()
        state = self._state_with_units(30)

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=spy,
        ):
            result = await _invoke_local_llm(state.raw_text, {"_state_object": state})

        assert result["input_mode"] == "selected_units"
        assert result["input_units"] == 12, "the unit budget the phase declares"
        assert result["input_units_total"] == 30

        sent = spy.chat_completion.call_args.kwargs.get("messages") or (
            spy.chat_completion.call_args.args[0]
            if spy.chat_completion.call_args.args
            else []
        )
        user_message = next(m["content"] for m in sent if m.get("role") == "user")
        assert (
            "DOC-SENTINEL" not in user_message
        ), "the whole document must not ride the prompt when a population exists"
        assert "Unit argument number" in user_message
        assert result["input_length"] == len(user_message)

    async def test_without_units_a_bounded_window_is_sent_and_recorded(self):
        spy = _stub_service()
        document = "HEAD-SENTINEL " + "x" * 20000 + " TAIL-SENTINEL"
        state = UnifiedAnalysisState(document)

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=spy,
        ):
            result = await _invoke_local_llm(document, {"_state_object": state})

        assert result["input_mode"] == "document_window"
        assert result["input_truncated"] is True
        assert result["input_chars_total"] == len(document)
        assert result["input_length"] == 12000, "the declared window"

        sent = spy.chat_completion.call_args.kwargs.get("messages") or (
            spy.chat_completion.call_args.args[0]
            if spy.chat_completion.call_args.args
            else []
        )
        user_message = next(m["content"] for m in sent if m.get("role") == "user")
        assert user_message == document[:12000]

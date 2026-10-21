"""#3113 — the local_llm phase reads the configuration it is given.

Before the repair, ``_invoke_local_llm`` built ``LocalLLMService()`` on its
fixed ``localhost:5001`` default: on any seat without a server there, the
phase could only skip, and the skip reason named an endpoint nobody
configured. The service now comes from the ``SELF_HOSTED_LLM_*`` triple the
self-hosted tier already declares (the same one
``_invoke_camembert_fallacy`` reads — one endpoint, one name), and the skip
distinguishes the two facts: ``not_configured`` (nothing declared) from
``endpoint_unavailable`` (declared and unreachable).

All witnesses are offline: the phase-level ones spy on the service class,
the probe one rides a stubbed httpx transport. Zero spend, zero network.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, AsyncMock, patch

import httpx
import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm
from argumentation_analysis.services.local_llm_service import LocalLLMService

CONFIGURED_ENDPOINT = "http://local-stub-3113.test/v1"
CONFIGURED_KEY = "synthetic-key-3113"
CONFIGURED_MODEL = "stub-model-3113"

TRIPLE = {
    "SELF_HOSTED_LLM_ENDPOINT": CONFIGURED_ENDPOINT,
    "SELF_HOSTED_LLM_API_KEY": CONFIGURED_KEY,
    "SELF_HOSTED_LLM_MODEL": CONFIGURED_MODEL,
}


def _service_spy() -> MagicMock:
    spy = MagicMock()
    spy.is_available = AsyncMock(return_value=True)
    spy.chat_completion = AsyncMock(return_value={"content": "stub"})
    spy.model = CONFIGURED_MODEL
    return spy


class TestThePhaseReadsTheConfiguration:
    async def test_the_service_is_built_from_the_configured_endpoint(self, monkeypatch):
        """The configured triple decides the endpoint — not localhost:5001."""
        for name, value in TRIPLE.items():
            monkeypatch.setenv(name, value)
        spy = _service_spy()

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=spy,
        ) as cls:
            await _invoke_local_llm("texte synthétique", {})

        cls.assert_called_once()
        kwargs = cls.call_args.kwargs
        assert (
            kwargs.get("endpoint") == CONFIGURED_ENDPOINT
        ), f"the phase must reach the configured endpoint, got {kwargs!r}"
        assert kwargs.get("api_key") == CONFIGURED_KEY
        assert kwargs.get("model") == CONFIGURED_MODEL

    async def test_unconfigured_skips_with_a_distinct_reason(self, monkeypatch):
        """Nothing declared ⇒ 'not_configured' — a different fact from
        'configured, unreachable', and no service is built to probe."""
        for name in TRIPLE:
            monkeypatch.delenv(name, raising=False)
        spy = _service_spy()
        state = UnifiedAnalysisState("texte synthétique")

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=spy,
        ) as cls:
            result = await _invoke_local_llm(
                "texte synthétique", {"_state_object": state}
            )

        assert result["status"] == "skipped: not_configured"
        cls.assert_not_called()  # nothing is configured: no probe is owed
        assert state.local_llm_results == [result]

    async def test_configured_but_unreachable_keeps_its_own_reason(self, monkeypatch):
        for name, value in TRIPLE.items():
            monkeypatch.setenv(name, value)
        spy = MagicMock()
        spy.is_available = AsyncMock(return_value=False)
        spy.model = CONFIGURED_MODEL

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=spy,
        ):
            result = await _invoke_local_llm("texte synthétique", {})

        assert result["status"] == "skipped: endpoint_unavailable"


class TestTheProbeAuthenticates:
    async def test_the_availability_probe_sends_the_key(self):
        """The probe authenticates like the chat call (#3113).

        A mutation dropping the Authorization header from ``is_available``
        turns this witness red: the recorded headers are the probe's own.
        """

        def respond(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"data": []})

        seen: list[httpx.Request] = []
        real_client = httpx.AsyncClient
        service = LocalLLMService(endpoint=CONFIGURED_ENDPOINT, api_key=CONFIGURED_KEY)

        def local_client(*args: Any, **kwargs: Dict[str, Any]) -> httpx.AsyncClient:
            return real_client(transport=httpx.MockTransport(respond), **kwargs)

        with patch("httpx.AsyncClient", side_effect=local_client):
            assert await service.is_available() is True

        assert len(seen) == 1 and seen[0].url.path.endswith("/models")
        assert seen[0].headers.get("Authorization") == f"Bearer {CONFIGURED_KEY}", (
            "the probe carries the configured key — a key-less /models probe "
            "reads a protected endpoint as down whatever the key says (#3113)"
        )


@pytest.mark.parametrize("probe_ok", [True, False])
async def test_probe_verdict_follows_the_status_code(probe_ok: bool):
    """The probe reads the endpoint's answer, not its mere existence."""

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200 if probe_ok else 401, json={})

    real_client = httpx.AsyncClient
    service = LocalLLMService(endpoint=CONFIGURED_ENDPOINT, api_key=CONFIGURED_KEY)

    def local_client(*args: Any, **kwargs: Dict[str, Any]) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(respond), **kwargs)

    with patch("httpx.AsyncClient", side_effect=local_client):
        assert await service.is_available() is probe_ok

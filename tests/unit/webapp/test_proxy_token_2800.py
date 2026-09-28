"""The proxy supplies its own rotating token, never the browser's token."""

import importlib
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles


@pytest.mark.asyncio
async def test_proxy_replaces_browser_token_per_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Import the proxy without requiring the unrelated React build artifact.
    if "interface_web.app" not in sys.modules:
        original_init = StaticFiles.__init__

        def static_init(self: StaticFiles, **kwargs: Any) -> None:
            original_init(self, **{**kwargs, "check_dir": False})

        with monkeypatch.context() as patch:
            patch.setattr(StaticFiles, "__init__", static_init)
            proxy = importlib.import_module("interface_web.app")
    else:
        proxy = importlib.import_module("interface_web.app")
    calls = []

    class FakeClient:
        async def request(self, **kwargs: Any) -> SimpleNamespace:
            calls.append(kwargs)
            return SimpleNamespace(content=b"ok", status_code=200, headers={})

    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "http",
        "path": "/api/fallacies",
        "raw_path": b"/api/fallacies",
        "query_string": b"",
        "headers": [(b"host", b"localhost"), (b"x-shield-token", b"browser-token")],
        "server": ("localhost", 5003),
        "client": ("127.0.0.1", 1234),
        "app": SimpleNamespace(state=SimpleNamespace(http_client=FakeClient())),
    }
    request = Request(scope)
    monkeypatch.setattr(request, "body", AsyncMock(return_value=b"{}"))
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "server-token")
    assert isinstance(await proxy.api_proxy(request), Response)
    assert calls[0]["headers"].get("x-shield-token") == "server-token"
    assert "host" not in calls[0]["headers"]
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "rotated-token")
    await proxy.api_proxy(request)
    assert calls[1]["headers"].get("x-shield-token") == "rotated-token"
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN")
    await proxy.api_proxy(request)
    assert "x-shield-token" not in calls[2]["headers"]

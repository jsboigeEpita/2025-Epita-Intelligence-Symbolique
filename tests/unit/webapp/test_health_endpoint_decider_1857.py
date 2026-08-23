"""#1857 — the deep-check verdict must read ``backend.health_endpoint``.

``backend.health_endpoint`` is a configurable key. Only ONE of its readers
honors it: the startup probe (:309). The deep-check list
``API_ENDPOINTS_TO_CHECK`` and — the one that DECIDES — the
``health_endpoint_ok`` verdict compare against hardcoded ``"/api/health"``
literals. The field is configurable; the reader that decides doesn't read it.

The defect is latent, masked by the live app's generosity: ``api.main`` serves
both ``/health`` and ``/api/health`` (the latter only through ``_IncludedRouter``
dynamic matching), so the verdict is True whatever the key says. It wakes the
moment someone does exactly what the key claims to allow — serve only the
configured path.

Mask removed here: the probe app below serves ``/health`` and ``/api/endpoints``
and deliberately does NOT serve ``/api/health``. Routes are resolved at RUNTIME
by real HTTP requests against a live server — never by walking ``app.routes``,
which ``_IncludedRouter`` blinds (#1853's lesson).

Degenerate substitution: on the pre-fix tree the first test is red (the verdict
demands the absent ``/api/health`` literal); post-fix it is green because the
verdict follows the key. The second test must stay green on BOTH trees — it
guards the other direction (a configured path the app does not serve must
still fail the check), so "always True" cannot pass as a fix.
"""

import argparse
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
import yaml
from fastapi import FastAPI

from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def probe_server():
    """A real uvicorn server whose ONLY routes are /health and /api/endpoints.

    Runtime resolution is the point: the orchestrator's deep-check issues real
    HTTP requests, and the served/absent question must be answered by the
    server, not by inspecting route tables.
    """
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "operational"}

    @app.get("/api/endpoints")
    def endpoints():
        return {"endpoints": []}

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "probe server failed to start"
    yield server
    server.should_exit = True
    thread.join(timeout=10)


def _make_orchestrator(tmp_path: Path, health_endpoint: str) -> UnifiedWebOrchestrator:
    config = {
        "webapp": {"name": "t", "version": "0", "environment": "test"},
        "backend": {
            "enabled": True,
            "module": "api.main:app",
            "start_port": 9100,
            "fallback_ports": [9101],
            "timeout_seconds": 5,
            "health_endpoint": health_endpoint,
        },
        "frontend": {
            "enabled": False,
            "path": "x",
            "port": 3000,
            "start_command": "npm start",
            "timeout_seconds": 5,
        },
        "playwright": {"enabled": False},
        "logging": {
            "level": "ERROR",
            "file": str(tmp_path / "orchestrator_test.log"),
        },
        "cleanup": {"auto_cleanup": False},
    }
    config_path = tmp_path / "webapp_config.yml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    args = argparse.Namespace(
        config=str(config_path),
        log_level="ERROR",
        headless=True,
        visible=False,
        timeout=1,
        no_trace=True,
    )
    return UnifiedWebOrchestrator(args=args)


class TestVerdictReadsTheKey:
    async def test_configured_path_served_verdict_true(self, probe_server, tmp_path):
        """health_endpoint=/health on an app that serves ONLY /health:
        the verdict must be True — the decider followed the key."""
        orchestrator = _make_orchestrator(tmp_path, "/health")
        orchestrator.app_info.backend_url = (
            f"http://127.0.0.1:{_server_port(probe_server)}"
        )
        assert await orchestrator._check_all_api_endpoints() is True

    async def test_configured_path_not_served_verdict_false(
        self, probe_server, tmp_path
    ):
        """health_endpoint=/api/health on an app that does NOT serve it:
        the verdict must be False. Guards against an "always True" fix —
        green on the pre-fix tree and must stay green after."""
        orchestrator = _make_orchestrator(tmp_path, "/api/health")
        orchestrator.app_info.backend_url = (
            f"http://127.0.0.1:{_server_port(probe_server)}"
        )
        assert await orchestrator._check_all_api_endpoints() is False


def _server_port(server) -> int:
    """The bound port of a uvicorn.Server started with port=0 semantics."""
    # uvicorn.Config was given an explicit free port; recover it from the
    # server's socket to avoid racing a second _free_port() call.
    for srv in getattr(server, "servers", []) or []:
        for sock in getattr(srv, "sockets", []) or []:
            return sock.getsockname()[1]
    raise AssertionError("no bound socket found on probe server")

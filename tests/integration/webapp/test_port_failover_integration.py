"""Port failover — the #1853 behavior this file promised since 2025-06-12.

This file (and its two siblings) was born 0-byte in ``727ae7c72`` and never
filled — a scaffold promise over a load-bearing orchestrator feature
(#2330). The docstring of ``UnifiedWebOrchestrator`` says "Démarrage/arrêt
backend FastAPI avec failover de ports (#1853)" and ``_start_backend``
traces "[BACKEND] DEMARRAGE BACKEND — Lancement avec failover de ports".

Measured against the pre-#2330 code, that promise is NOT kept:
``MinimalBackendManager.start`` attempts exactly ONE port (``port_override
or random free``) and returns ``{"success": False}`` on failure — no retry,
no fallback walk. ``fallback_ports`` is read only at cleanup time. A busy
``start_port`` therefore means a dead webapp (and, when the port's occupant
answers the health endpoint, a health check that can pass against the WRONG
server).

These tests hold the documented contract, both halves:

* a busy ``start_port`` → the backend binds the first FREE fallback port;
* a free ``start_port`` → it is used directly (failover is not an excuse to
  abandon the configured port).

The port is occupied by the REAL fake backend (an aiohttp server answering
``/api/health`` with 200) — the worst-case occupant, not a bare socket.
Integration-grade: starts the live ``api.main:app`` backend (JVM bootstrap
included — #1853 calibration), ~20 s per boot. No LLM, no network beyond
localhost.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from argumentation_analysis.webapp.orchestrator import (
    UnifiedWebOrchestrator,
    WebAppStatus,
)

FAKE_BACKEND = Path(__file__).parent / "fake_backend.py"
START_PORT = 9030
FALLBACK_PORTS = [9031, 9032]


@pytest.fixture
def failover_config(webapp_config):
    config = webapp_config
    config["backend"]["start_port"] = START_PORT
    config["backend"]["fallback_ports"] = list(FALLBACK_PORTS)
    config["backend"]["timeout_seconds"] = 60  # #1853: live target boot, JVM included
    config["frontend"]["enabled"] = False
    config["playwright"]["enabled"] = False
    return config


@pytest.fixture
def orchestrator(failover_config, test_config_path, mocker):
    """Like the lifecycle fixture, but for the failover-shaped config."""
    import argparse

    import yaml

    mocker.patch(
        "argumentation_analysis.webapp.orchestrator.UnifiedWebOrchestrator._setup_signal_handlers"
    )
    with open(test_config_path, "w") as f:
        yaml.dump(failover_config, f)
    mock_args = argparse.Namespace(
        config=str(test_config_path),
        log_level="DEBUG",
        headless=True,
        visible=False,
        timeout=5,
        no_trace=False,  # the failover decision IS the traced behavior
    )
    return UnifiedWebOrchestrator(args=mock_args)


@pytest.fixture
def occupied_start_port():
    """Run the fake aiohttp backend ON the configured start port — an
    occupant that ANSWERS health checks (the wrong-server hazard), not a
    bare bound socket. Polls until it ACCEPTS a connection: the port must
    be occupied BEFORE the orchestrator's pre-check runs, or the test
    races the bind."""
    import socket
    import time

    proc = subprocess.Popen(
        [sys.executable, str(FAKE_BACKEND), str(START_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            with socket.socket() as s:
                s.settimeout(0.2)
                if s.connect_ex(("127.0.0.1", START_PORT)) == 0:
                    break
            time.sleep(0.2)
        else:
            raise RuntimeError("fake backend never came up on the start port")
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=10)


class TestPortFailover:
    def test_busy_start_port_falls_back_to_the_first_free_port(
        self, orchestrator, occupied_start_port
    ):
        """The documented #1853 contract: a busy start_port → the backend
        binds the fallback, the webapp starts, and the occupant is left
        alone."""

        async def run_test():
            success = await orchestrator.start_webapp()
            try:
                assert success, (
                    "start_webapp() failed although a fallback port "
                    f"({FALLBACK_PORTS[0]}) was free — the documented "
                    "failover did not happen"
                )
                assert orchestrator.app_info.backend_port == FALLBACK_PORTS[0]
                assert orchestrator.app_info.backend_url == (
                    f"http://localhost:{FALLBACK_PORTS[0]}"
                )
                # the decision is TRACED — an operator reading the trace sees
                # why the port changed
                assert any(
                    "PORT OCCUPE" in entry.action and str(START_PORT) in entry.details
                    for entry in orchestrator.trace_log
                ), "the failover decision must appear in the trace log"
                # the occupant survives: failover relocates, never kills —
                # the pre-start cleanup spares processes it does not own
                assert occupied_start_port.poll() is None
            finally:
                await orchestrator.stop_webapp()

        asyncio.run(run_test())

    def test_free_start_port_is_used_directly(self, orchestrator):
        """The anti-pendulum half: failover must not abandon the configured
        port when it is free."""

        async def run_test():
            success = await orchestrator.start_webapp()
            try:
                assert success
                assert orchestrator.app_info.backend_port == START_PORT
                assert orchestrator.app_info.status == WebAppStatus.RUNNING
            finally:
                await orchestrator.stop_webapp()

        asyncio.run(run_test())

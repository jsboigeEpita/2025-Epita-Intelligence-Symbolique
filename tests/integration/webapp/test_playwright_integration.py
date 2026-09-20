"""Playwright wiring — the orchestrator's own browser launch, really driven.

This file was born 0-byte in ``727ae7c72`` and never filled (#2330), while
the infrastructure it promised to exercise is fully provisioned:
``playwright`` + ``pytest-playwright`` in environment.yml, a ``playwright``
marker in pytest.ini, and real launch/close methods on the orchestrator
(``_launch_playwright_browser`` / ``_close_playwright_browser``) that the
docstring advertises as "Exécution tests Playwright intégrés".

The test drives the REAL wiring — ``async_playwright().start()``, browser
launch from the config, headless — and then navigates a real page against
the fake backend's health endpoint, asserting the response body. If the
chromium binary is absent (a machine that never ran ``playwright install``),
the test fails with the launch error rather than skipping: a browser E2E
that silently skips is a green that proves nothing (#1019 family).

Marker: ``playwright`` (pytest.ini). Localhost only, no LLM.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator

FAKE_BACKEND = Path(__file__).parent / "fake_backend.py"


@pytest.fixture
def orchestrator(webapp_config, test_config_path, mocker):
    """Playwright-shaped: the browser enabled, everything else off. The
    signal-handler patch matches the lifecycle fixture (win32 log-only
    branch is held by test_signal_handling.py)."""
    import argparse

    import yaml

    mocker.patch(
        "argumentation_analysis.webapp.orchestrator.UnifiedWebOrchestrator._setup_signal_handlers"
    )
    webapp_config["frontend"]["enabled"] = False
    webapp_config["playwright"] = {"enabled": True, "browser": "chromium"}
    with open(test_config_path, "w") as f:
        yaml.dump(webapp_config, f)
    mock_args = argparse.Namespace(
        config=str(test_config_path),
        log_level="DEBUG",
        headless=True,
        visible=False,
        timeout=5,
        no_trace=True,
    )
    return UnifiedWebOrchestrator(args=mock_args)


@pytest.fixture
def fake_backend_port():
    """The fake backend on a dynamic free port — the navigation target."""
    import socket

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, str(FAKE_BACKEND), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # wait for the fake backend to accept connections (it logs its
        # startup line; polling the socket is faster and shape-agnostic)
        import time

        for _ in range(50):
            with socket.socket() as s:
                s.settimeout(0.2)
                if s.connect_ex(("localhost", port)) == 0:
                    break
            time.sleep(0.2)
        else:
            proc.terminate()
            raise RuntimeError("fake backend never came up")
        yield port
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.mark.playwright
class TestOrchestratorBrowserWiring:
    def test_launch_navigate_close_against_the_fake_backend(
        self, orchestrator, fake_backend_port
    ):
        """The real launch path (config-driven), a real navigation with a
        body assertion, and the real close path leaving no browser behind."""

        async def run_test():
            orchestrator.headless = True
            await orchestrator._launch_playwright_browser()
            try:
                assert orchestrator.browser is not None, (
                    "the config enables playwright — a browser must have "
                    "launched (a missing binary must FAIL here, not skip)"
                )
                context = await orchestrator.browser.new_context()
                page = await context.new_page()
                response = await page.goto(
                    f"http://localhost:{fake_backend_port}/api/health"
                )
                assert response is not None and response.status == 200
                payload = await response.json()
                assert payload == {"status": "ok"}
                await context.close()
            finally:
                await orchestrator._close_playwright_browser()
            assert orchestrator.browser is None
            assert orchestrator.playwright is None

        asyncio.run(run_test())

    def test_disabled_config_launches_nothing(self, orchestrator):
        """The anti-pendulum half: ``enabled: False`` must not spawn a
        browser behind the caller's back."""

        async def run_test():
            orchestrator.config["playwright"]["enabled"] = False
            await orchestrator._launch_playwright_browser()
            assert orchestrator.browser is None
            assert orchestrator.playwright is None

        asyncio.run(run_test())

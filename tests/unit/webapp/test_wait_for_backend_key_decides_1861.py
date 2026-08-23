"""#1861 — in this fork too, ``backend.health_endpoint`` decides the probe.

``BackendManager._wait_for_backend`` carried a substring special case: a
caller passing ``app_module`` containing ``"api.main"`` forced the probe to
``/health``, overriding the configured key. The branch was dead today (its
only caller, :318, passes no ``app_module``) but armed by the obvious
refactor — ``start_with_failover`` already holds the module in hand. #1858
decided for the canonical fork that the key decides; the branch was a
dormant contradiction of that decision, so it was removed (decision written
at the site).

Witness, run against unmodified main: a real server serving ONLY the
configured path ``/custom-health``, manager key ``/custom-health`` —
``_wait_for_backend(port, app_module="api.main:app")`` probed the literal
instead (log: "Attente backend sur http://127.0.0.1:<p>/health") and
returned False despite the configured path being served. The armed call
cannot survive the fix by design — the parameter is gone — so the born-red
member committed here is the signature pin (third test), red on main,
green after removal.

Mask removed as in #1857: the probe server below serves ``/custom-health``
and deliberately serves NEITHER literal (``/health`` nor ``/api/health``),
and served/absent is answered at RUNTIME by real HTTP requests.
"""

import inspect
import logging
import socket
import subprocess
import sys
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI

from scripts.apps.webapp.backend_manager import BackendManager


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def probe_server():
    """A real uvicorn server whose ONLY route is /custom-health.

    The configured key points at a path that is neither literal, so a probe
    following the key succeeds and a probe following any literal fails.
    """
    app = FastAPI()

    @app.get("/custom-health")
    def custom_health():
        return {"status": "operational"}

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


def _server_port(server) -> int:
    for srv in getattr(server, "servers", []) or []:
        for sock in getattr(srv, "sockets", []) or []:
            return sock.getsockname()[1]
    raise AssertionError("no bound socket found on probe server")


def _make_manager(health_endpoint: str) -> BackendManager:
    """A manager whose process is a live sleeper (poll() -> None)."""
    manager = BackendManager(
        {"health_endpoint": health_endpoint, "timeout_seconds": 3},
        logging.getLogger("t1861"),
    )
    manager.process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"]
    )
    return manager


def _reap(manager: BackendManager):
    if manager.process is not None and manager.process.poll() is None:
        manager.process.kill()
        manager.process.wait()


class TestKeyDecides:
    async def test_configured_path_served_probe_true(self, probe_server):
        """health_endpoint=/custom-health on a server that serves ONLY that
        path: the probe must succeed — it followed the key."""
        manager = _make_manager("/custom-health")
        try:
            assert await manager._wait_for_backend(_server_port(probe_server)) is True
        finally:
            _reap(manager)

    async def test_configured_path_not_served_probe_false(self, probe_server):
        """health_endpoint=/health on a server that does NOT serve it (it is
        the literal the removed special case used to force): the probe must
        fail. Guards an "always True" fix — green before and after."""
        manager = _make_manager("/health")
        try:
            assert await manager._wait_for_backend(_server_port(probe_server)) is False
        finally:
            _reap(manager)


def test_no_substrate_special_case_parameter():
    """Born-red on main: the ``app_module`` escape hatch is gone, so the
    substring override cannot be re-armed by a caller."""
    params = inspect.signature(BackendManager._wait_for_backend).parameters
    assert "app_module" not in params

"""#1853 — the webapp launchers must point at a callable ASGI target.

The orchestrator's uvicorn target was ``argumentation_analysis.services.
web_api.app:app`` — a module archived in March (#217) that still imports
cleanly and exports a symbol *named* ``app`` whose value is ``None``. The
process starts, listens, and answers HTTP 500 on every route: an inventory
by name cannot see the death, and "the process started" is exactly the wrong
control (#1853's trap).

This control probes what uvicorn will actually load — in a subprocess, so
the heavy ``api.main`` import (and its entry-point ``load_dotenv()``) never
seeds the pytest session (#1794) — and asserts, for each declared surface:

1. the module imports and the symbol is **callable**;
2. when the target is a FastAPI app, every GET path the config or the
   orchestrator will probe (health endpoint, ``API_ENDPOINTS_TO_CHECK``)
   is **actually served** — the 500-wall and the 404-wall are both named.

Degenerate substitution: on the pre-fix tree the YAML still names the
archived module, ``callable(app)`` is False, and this file is red naming
``None``; post-fix it is green. A naive module-only fix (``api.main:app``
while ``/api/health`` stays configured) also stays red here — the route
probe is the discriminator the issue demands.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WEBAPP_CONFIG = REPO_ROOT / "config" / "webapp_config.yml"

_MINIMAL_ENV_KEYS = (
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "TEMP",
    "TMP",
    "COMSPEC",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "APPDATA",
)

_PROBE = r"""
import importlib
import json
import sys

module_spec = sys.argv[1]
get_paths = [p for p in sys.argv[2].split("|") if p]

mod_name, _, sym = module_spec.partition(":")
sym = sym or "app"
try:
    module = importlib.import_module(mod_name)
except Exception as exc:
    print(json.dumps({"importable": False, "error": f"{type(exc).__name__}: {exc}"}))
    raise SystemExit(0)

obj = getattr(module, sym, None)
out = {
    "importable": True,
    "symbol": sym,
    "callable": callable(obj),
    "value": repr(obj)[:100],
}
from fastapi.applications import FastAPI

if isinstance(obj, FastAPI):
    from fastapi.testclient import TestClient

    client = TestClient(obj, raise_server_exceptions=False)
    codes = {p: client.get(p).status_code for p in get_paths}
    out["fastapi"] = True
    # api.main wraps its routers in a custom _IncludedRouter whose sub-routes
    # only materialize at request time — a static app.routes walk is blind to
    # them, so "is this path served" must be probed at runtime. 404 = absent,
    # anything else (200/405/422/500) = the route exists.
    out["served"] = {p: (code != 404) for p, code in codes.items()}
    out["status_codes"] = codes
print(json.dumps(out))
"""


def _probe(module_spec: str, get_paths) -> dict:
    env = {k: os.environ[k] for k in _MINIMAL_ENV_KEYS if k in os.environ}
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", _PROBE, module_spec, "|".join(get_paths)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=240,
    )
    assert result.returncode == 0, f"probe crashed:\n{result.stderr[-2000:]}"
    for line in result.stdout.splitlines():
        if line.startswith("{"):
            return json.loads(line)
    pytest.fail(f"probe produced no verdict:\nstdout={result.stdout[-500:]}")


def _yaml_backend() -> dict:
    import yaml

    with open(WEBAPP_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["backend"]


@pytest.fixture(scope="module")
def verdict():
    """One subprocess import shared by the module's tests.

    The probe targets the YAML's declared module and the union of every GET
    path the orchestrator machinery will request: the configured health
    endpoint plus ``UnifiedWebOrchestrator.API_ENDPOINTS_TO_CHECK``.
    """
    from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator

    backend = _yaml_backend()
    module_spec = backend["module"]
    health = backend.get("health_endpoint", "/health")
    paths = {health} | {
        e["path"]
        for e in UnifiedWebOrchestrator.API_ENDPOINTS_TO_CHECK
        if e.get("method", "GET").upper() == "GET"
    }
    return _probe(module_spec, sorted(paths))


class TestConfiguredTargetIsCallable:
    def test_module_imports_and_symbol_is_callable(self, verdict):
        assert verdict.get(
            "importable"
        ), f"declared module fails to import: {verdict.get('error')}"
        assert verdict.get("callable"), (
            "the declared uvicorn target is NOT callable — the launchers point at "
            f"a dead symbol (value: {verdict.get('value')}). A process started on it "
            "serves 500 on every route (#1853)."
        )


class TestConfiguredPathsAreServed:
    def test_health_endpoint_is_a_real_route(self, verdict):
        if not verdict.get("fastapi"):
            pytest.skip("target is not a FastAPI app — route probe does not apply")
        backend = _yaml_backend()
        health = backend.get("health_endpoint", "/health")
        served = verdict.get("served", {})
        assert served.get(health) is True, (
            f"configured health_endpoint {health} is not served by the target — "
            f"the startup check would 404 forever. Served map: {served}"
        )

    def test_orchestrator_deep_check_paths_are_real_routes(self, verdict):
        if not verdict.get("fastapi"):
            pytest.skip("target is not a FastAPI app — route probe does not apply")
        served = verdict.get("served", {})
        dead = {p: ok for p, ok in served.items() if not ok}
        assert not dead, (
            "API_ENDPOINTS_TO_CHECK probes paths the target does not serve — "
            f"the deep check would mark the backend dead: {dead}"
        )

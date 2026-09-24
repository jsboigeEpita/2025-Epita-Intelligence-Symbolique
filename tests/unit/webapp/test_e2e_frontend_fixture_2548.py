# -*- coding: utf-8 -*-
"""#2548: what the ``e2e_servers`` fixture serves as its frontend, and what it
says when the frontend does not come up.

The fixture ran ``npm start``, which the e2e lane never installed, slept 15 s
and yielded ``http://localhost:8085``. Nothing answered there: 25 Playwright
tests failed on ``ERR_CONNECTION_REFUSED`` (run 35969872851), and the cause
was only in a log the lane did not upload.
"""

import os
import re
import sys
from pathlib import Path

import pytest

from tests import conftest as root_conftest

_REPO = Path(__file__).resolve().parents[3]


def _built(project_root):
    build = project_root / root_conftest._E2E_FRONTEND_DIR / "build"
    build.mkdir(parents=True)
    (build / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    return project_root


def test_the_frontend_is_the_app_that_serves_the_build():
    command = root_conftest._e2e_frontend_command("127.0.0.1", "8085")

    assert command[1:] == [
        "-m",
        "uvicorn",
        "interface_web.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8085",
    ]
    assert "npm" not in " ".join(command)


def test_the_frontend_relays_to_the_backend_it_is_given(tmp_path):
    env = root_conftest._e2e_frontend_env("http://localhost:8095", tmp_path)

    assert (env["FASTAPI_HOST"], env["FASTAPI_PORT"]) == ("localhost", "8095")
    assert env["PYTHONPATH"] == str(tmp_path)


def test_a_missing_build_is_named_before_anything_starts(tmp_path, monkeypatch):
    started = []
    monkeypatch.setattr(
        root_conftest.subprocess, "Popen", lambda *a, **k: started.append(a)
    )

    with pytest.raises(RuntimeError) as raised:
        root_conftest._start_e2e_frontend(
            "http://127.0.0.1:9", "http://127.0.0.1:8095", tmp_path, tmp_path
        )

    assert "npm run build" in str(raised.value)
    assert "index.html is missing" in str(raised.value)
    assert started == []


def test_a_frontend_that_exits_makes_the_fixture_raise_with_its_log(
    tmp_path, monkeypatch
):
    """The guard #2548 asks for: the frontend command exits at once. The
    fixture raises with what it printed, instead of yielding a dead URL."""
    monkeypatch.setattr(
        root_conftest,
        "_e2e_frontend_command",
        lambda host, port: [
            sys.executable,
            "-c",
            "import sys; print('frontend probe 2548 cannot start', file=sys.stderr);"
            " sys.exit(5)",
        ],
    )
    logs = tmp_path / "logs"
    logs.mkdir()

    with pytest.raises(RuntimeError) as raised:
        root_conftest._start_e2e_frontend(
            "http://127.0.0.1:9", "http://127.0.0.1:8095", _built(tmp_path), logs
        )

    assert "code 5" in str(raised.value)
    assert "frontend probe 2548 cannot start" in str(raised.value)


def test_a_frontend_that_never_answers_times_out_with_its_log(tmp_path):
    """A process that runs but serves nothing: the wait ends at its bound, and
    the message carries the log."""
    log_path = tmp_path / "frontend_server.log"
    with open(log_path, "w") as log:
        process = root_conftest.subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys, time; print('listening nowhere', flush=True);"
                " time.sleep(60)",
            ],
            stdout=log,
            stderr=log,
        )
        try:
            with pytest.raises(TimeoutError) as raised:
                root_conftest._wait_for_server(
                    "http://127.0.0.1:9",
                    process,
                    timeout=5,
                    log_path=log_path,
                    path="/",
                )
        finally:
            root_conftest._kill_process(process)

    assert "listening nowhere" in str(raised.value)


def _ui_fallacy_timeout_ms():
    api_js = (
        _REPO / root_conftest._E2E_FRONTEND_DIR / "src" / "services" / "api.js"
    ).read_text(encoding="utf-8")
    match = re.search(r"FALLACY_TIMEOUT_MS\s*=\s*(\d+)", api_js)
    assert match, "FALLACY_TIMEOUT_MS is no longer declared in services/api.js"
    return int(match.group(1))


def _relay_module():
    """``interface_web.app``, which mounts the React build when imported.

    Without ``build/`` the import raises. The gate builds the app (ci.yml,
    "Build React frontend", #1403), so there a missing build is a failure,
    not a reason to skip.
    """
    build = _REPO / root_conftest._E2E_FRONTEND_DIR / "build"
    if not build.is_dir():
        if os.environ.get("CI"):
            pytest.fail(
                "the gate builds the React app before the tests; without "
                "build/, interface_web.app cannot be imported"
            )
        pytest.skip(
            "interface_web.app mounts the React build when imported: run "
            "`npm ci` then `npm run build` in "
            f"{root_conftest._E2E_FRONTEND_DIR.as_posix()}"
        )
    from interface_web import app as relay

    return relay


def test_the_relay_outwaits_the_app_it_serves():
    """The relay must not answer 504 while the React app is still waiting.

    Measured on #2548's branch: fallacy detection on the stress text took
    37 s, and the relay answered 504 at 30 s.
    """
    relay = _relay_module()

    assert relay.PROXY_READ_TIMEOUT_SECONDS * 1000 > _ui_fallacy_timeout_ms()


async def test_the_relay_client_uses_that_timeout():
    relay = _relay_module()

    async with relay.lifespan(relay.app):
        timeout = relay.app.state.http_client.timeout

    assert timeout.read == relay.PROXY_READ_TIMEOUT_SECONDS
    assert timeout.connect == 5.0

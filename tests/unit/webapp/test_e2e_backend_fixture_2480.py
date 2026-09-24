# -*- coding: utf-8 -*-
"""#2480: what the ``e2e_servers`` fixture gives its backend, and what it says
when the backend stops.

The fixture started a module archived in February. The process exited at once,
and the fixture reported ``'NoneType' object has no attribute 'decode'``: the
server's output goes to a log file, so ``communicate()`` returns ``None``. The
cause (``No module named 'services.web_api_from_libs'``) was only in the log.

The fixture also read the ``.env`` a second time over its own environment, so a
value the caller set, an emptied key included, was overwritten (#2472).
"""

import os
import subprocess
import sys

import pytest

from tests import conftest as root_conftest


def _exited(tmp_path, code):
    """A server that writes its cause to its log and exits, as the archived
    module did."""
    log_path = tmp_path / "backend_server.log"
    with open(log_path, "w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys; print('No module named probe_2480', file=sys.stderr);"
                f" sys.exit({code})",
            ],
            stdout=log,
            stderr=log,
        )
        process.wait(timeout=60)
    return process, log_path


def test_the_helpers_come_from_the_conftest_pytest_loaded(request):
    """The import above reuses the loaded conftest; it does not run it twice."""
    loaded = [
        plugin
        for plugin in request.config.pluginmanager.get_plugins()
        if getattr(plugin, "__file__", "")
        .replace("\\", "/")
        .endswith("/tests/conftest.py")
    ]
    assert loaded == [root_conftest]


def test_a_backend_that_exits_names_its_cause(tmp_path):
    process, log_path = _exited(tmp_path, 3)

    with pytest.raises(RuntimeError) as raised:
        root_conftest._wait_for_server(
            "http://127.0.0.1:9", process, timeout=30, log_path=log_path
        )

    assert "code 3" in str(raised.value)
    assert "No module named probe_2480" in str(raised.value)


def test_a_backend_that_exits_without_a_log_is_still_a_premature_exit(tmp_path):
    """``main`` raised ``AttributeError`` here, which named no server at all."""
    process, _ = _exited(tmp_path, 4)

    with pytest.raises(RuntimeError) as raised:
        root_conftest._wait_for_server("http://127.0.0.1:9", process, timeout=30)

    assert "code 4" in str(raised.value)


def test_the_backend_environment_keeps_what_the_caller_set(tmp_path, monkeypatch):
    """The project root holds a ``.env`` that disagrees with the caller. The
    backend gets the caller's values, and the fixture adds only its own keys."""
    (tmp_path / ".env").write_text(
        'OPENAI_API_KEY="from the file"\nCALLER_2480="from the file"\n'
        'FILE_ONLY_2480="from the file"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("CALLER_2480", "from the caller")
    monkeypatch.delenv("FILE_ONLY_2480", raising=False)

    env = root_conftest._e2e_backend_env("8095", tmp_path)

    assert env["OPENAI_API_KEY"] == ""
    assert env["CALLER_2480"] == "from the caller"
    assert "FILE_ONLY_2480" not in env
    changed = {name for name in env if env[name] != os.environ.get(name)}
    assert changed <= {"PORT", "PYTHONPATH", "FORCE_MOCK_LLM"}, changed
    assert env["PORT"] == "8095"


def test_the_backend_command_serves_the_live_app():
    command = root_conftest._e2e_backend_command("127.0.0.1", "8095")

    assert command[:4] == [sys.executable, "-m", "uvicorn", "api.main:app"]
    assert command[command.index("--port") + 1] == "8095"
    assert command[command.index("--host") + 1] == "127.0.0.1"

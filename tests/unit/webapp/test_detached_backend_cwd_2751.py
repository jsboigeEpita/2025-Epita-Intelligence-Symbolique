"""The detached launcher must resolve and serve its target from the child cwd."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from http.client import HTTPConnection

from scripts.orchestration.orchestrate_webapp_detached import create_backend_config

ROOT = Path(__file__).resolve().parents[3]


def _clean_env():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GH_TOKEN"):
        env[name] = ""
    return env


def test_detached_backend_imports_from_its_actual_cwd():
    config = create_backend_config()
    result = subprocess.run(
        [sys.executable, "-c", "import importlib; importlib.import_module('api.main')"],
        cwd=config.working_dir,
        env=_clean_env(),
        capture_output=True,
        text=True,
        timeout=35,
    )
    assert result.returncode == 0, result.stderr[-1000:]


def test_detached_backend_serves_health_from_its_actual_cwd(tmp_path):
    config = create_backend_config()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    command = list(config.command)
    command[0] = sys.executable
    command[command.index("--port") + 1] = str(port)
    command[command.index("--host") + 1] = "127.0.0.1"
    error_log = tmp_path / "backend-stderr.log"
    with error_log.open("wb") as errors:
        process = subprocess.Popen(
            command,
            cwd=config.working_dir,
            env=_clean_env(),
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(
                    f"Backend exited {process.returncode}: "
                    f"{error_log.read_text(errors='replace')[-1000:]}"
                )
            connection = HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                connection.request("GET", "/health")
                response = connection.getresponse()
                response.read()
                if response.status == 200:
                    return
            except (OSError, TimeoutError):
                pass
            finally:
                connection.close()
            time.sleep(0.25)
        raise AssertionError(
            "Backend did not become health-ready within 45s: "
            + error_log.read_text(errors="replace")[-1000:]
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

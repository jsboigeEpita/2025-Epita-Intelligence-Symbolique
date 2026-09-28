"""Direct CLI backend port survives Uvicorn's reload child (#2749)."""

import http.server
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import psutil

ROOT = Path(__file__).resolve().parents[3]


class Backend(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/probe":
            self.send_error(404)
            return
        body = b"backend-9000"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_direct_cli_proxies_to_requested_port_after_reload(tmp_path):
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Backend) as backend:
        backend_port = backend.server_address[1]
        thread = threading.Thread(target=backend.serve_forever, daemon=True)
        thread.start()
        port = _free_port()
        env = os.environ.copy()
        env["FASTAPI_PORT"] = "8095"
        env["OPENAI_API_KEY"] = ""
        env["OPENROUTER_API_KEY"] = ""
        env.pop("PYTHONPATH", None)
        error_log = tmp_path / "proxy-stderr.log"
        with error_log.open("wb") as errors:
            proxy = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "interface_web" / "app.py"),
                    "--port",
                    str(port),
                    "--fastapi-port",
                    str(backend_port),
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=errors,
            )
        try:
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                if proxy.poll() is not None:
                    raise AssertionError(error_log.read_text(errors="replace")[-1000:])
                try:
                    with urlopen(
                        f"http://127.0.0.1:{port}/api/probe", timeout=1
                    ) as response:
                        assert response.read() == b"backend-9000"
                        return
                except URLError:
                    time.sleep(0.2)
            raise AssertionError(error_log.read_text(errors="replace")[-1000:])
        finally:
            parent = psutil.Process(proxy.pid)
            children = parent.children(recursive=True) if parent.is_running() else []
            for child in children:
                child.terminate()
            if proxy.poll() is None:
                proxy.terminate()
            _, alive = psutil.wait_procs(children, timeout=5)
            for child in alive:
                child.kill()
            try:
                proxy.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proxy.kill()
                proxy.wait(timeout=5)
            backend.shutdown()
            thread.join(timeout=5)

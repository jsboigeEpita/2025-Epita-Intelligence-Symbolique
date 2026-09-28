"""Controls for the ``/api/analyze`` and ``/api/fallacies`` e2e smokes (#2756).

The smokes run only in the extended e2e lane, against live servers. These
controls run their real test methods in the gate, against a local stub
backend: a 200 with the success envelope passes, a 502 fails, a refused
connection raises, and a disabled servers fixture is an explicit skip.
"""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

# Import the module, not the class: a Test* class in this module's globals
# would be collected here and ask for the live e2e_servers fixture.
from tests.e2e.python import test_webapp_api_investigation as smoke

SUCCESS = {
    "analysis_id": "abc12345",
    "status": "success",
    "results": {
        "argument_structure": {"premises": ["p"], "conclusion": "c"},
        "suggestions": [],
        "summary": "ok",
        "extraction_path": "stub",
        "metadata": {},
    },
}
UPSTREAM = {
    "error_code": "upstream_error",
    "detail": "Analysis service failed: stub",
    "degraded": False,
    "context": {},
}


@pytest.fixture
def stub_backend():
    """Start a local backend answering every POST with a fixed response."""
    servers = []

    def _start(status, body):
        payload = json.dumps(body).encode("utf-8")

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield _start
    for server in servers:
        server.shutdown()
        server.server_close()


@pytest.fixture
def refused_url():
    """A URL on a local port nothing listens on."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}"


class TestAnalyzeSmokeControls:
    def test_success_envelope_passes(self, stub_backend):
        url = stub_backend(200, SUCCESS)
        smoke.TestWebAppAPIInvestigation().test_api_analyze_endpoint(
            (url, None), "synthetic-token"
        )

    def test_upstream_502_fails(self, stub_backend):
        url = stub_backend(502, UPSTREAM)
        with pytest.raises(AssertionError, match="answered 502"):
            smoke.TestWebAppAPIInvestigation().test_api_analyze_endpoint(
                (url, None), "synthetic-token"
            )

    def test_200_without_a_structure_fails(self, stub_backend):
        body = {
            **SUCCESS,
            "results": {**SUCCESS["results"], "argument_structure": None},
        }
        url = stub_backend(200, body)
        with pytest.raises(AssertionError):
            smoke.TestWebAppAPIInvestigation().test_api_analyze_endpoint(
                (url, None), "synthetic-token"
            )

    def test_refused_connection_is_not_a_skip(self, refused_url):
        with pytest.raises(requests.exceptions.ConnectionError):
            smoke.TestWebAppAPIInvestigation().test_api_analyze_endpoint(
                (refused_url, None), "synthetic-token"
            )

    def test_disabled_fixture_is_an_explicit_skip(self):
        with pytest.raises(pytest.skip.Exception, match="disable-e2e-servers-fixture"):
            smoke.TestWebAppAPIInvestigation().test_api_analyze_endpoint(
                (None, None), "synthetic-token"
            )


class TestFallaciesSmokeControls:
    def test_refused_connection_is_not_a_pass(self, refused_url):
        with pytest.raises(requests.exceptions.ConnectionError):
            smoke.TestWebAppAPIInvestigation().test_api_fallacies_endpoint(
                (refused_url, None), "synthetic-token"
            )

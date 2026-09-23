"""The egress report tells network egress from in-process test doubles (#2422).

The counter hooks ``Client.send``, above the transport, so a request answered
by a ``MockTransport`` or a replaced transport is recorded like one that left
the machine. Before #2422 the report did not tell them apart: six requests
answered in memory by a test's own transport read as "LLM hosts hit:
api.openai.com". Each entry now carries ``transport``: ``network`` when the
request reached httpx's own network transport, ``in_process`` otherwise.

The positive control for ``network`` is a disposable server on 127.0.0.1:
the request crosses a real socket without leaving the machine.
"""

import http.server
import json
import threading
from types import SimpleNamespace

import httpx
import pytest

from tests.llm_egress_counter import (
    LLMEgressCounter,
    LLMEgressPlugin,
    get_counter,
)

LLM_URL = "https://api.openai.com/v1/chat/completions"


class _Ok(http.server.BaseHTTPRequestHandler):
    def _answer(self):
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 — http.server API
        self._answer()

    def do_POST(self):  # noqa: N802 — http.server API
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self._answer()

    def log_message(self, *args):
        pass


@pytest.fixture
def local_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Ok)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _session_counter():
    counter = get_counter()
    assert counter is not None, "session counter not activated (#1787)"
    return counter


def _entries(counter, test_name, host):
    return [
        r
        for r in counter.snapshot()["requests"]
        if r["test"].endswith(test_name) and r["host"] == host
    ]


def _mock_transport():
    return httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": 1}))


async def test_mock_transport_request_is_in_process():
    counter = _session_counter()
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        await client.post(LLM_URL, json={"p": 1})
    entries = _entries(
        counter, "test_mock_transport_request_is_in_process", "api.openai.com"
    )
    assert [(r["class"], r["transport"]) for r in entries] == [("llm", "in_process")]


async def test_real_async_transport_request_is_network(local_server):
    counter = _session_counter()
    async with httpx.AsyncClient(trust_env=False) as client:
        response = await client.get(f"{local_server}/probe")
    assert response.json() == {"ok": True}
    entries = _entries(
        counter, "test_real_async_transport_request_is_network", "127.0.0.1"
    )
    assert [r["transport"] for r in entries] == ["network"], entries


def test_real_sync_transport_request_is_network(local_server):
    counter = _session_counter()
    with httpx.Client(trust_env=False) as client:
        assert client.get(f"{local_server}/probe").status_code == 200
    entries = _entries(
        counter, "test_real_sync_transport_request_is_network", "127.0.0.1"
    )
    assert [r["transport"] for r in entries] == ["network"], entries


async def test_transport_subclass_that_never_calls_the_network_is_in_process():
    """A double built on the real class but overriding the send stays in process."""
    counter = _session_counter()

    class _Canned(httpx.AsyncHTTPTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, json={"ok": 1}, request=request)

    async with httpx.AsyncClient(transport=_Canned()) as client:
        await client.post(LLM_URL, json={"p": 1})
    entries = _entries(
        counter,
        "test_transport_subclass_that_never_calls_the_network_is_in_process",
        "api.openai.com",
    )
    assert [r["transport"] for r in entries] == ["in_process"], entries


async def test_transport_subclass_that_delegates_to_the_network_is_network(
    local_server,
):
    """A wrapper transport (retries, logging) that calls the real one is network."""
    counter = _session_counter()

    class _Wrapping(httpx.AsyncHTTPTransport):
        async def handle_async_request(self, request):
            return await super().handle_async_request(request)

    async with httpx.AsyncClient(transport=_Wrapping(), trust_env=False) as client:
        await client.get(f"{local_server}/probe")
    entries = _entries(
        counter,
        "test_transport_subclass_that_delegates_to_the_network_is_network",
        "127.0.0.1",
    )
    assert [r["transport"] for r in entries] == ["network"], entries


async def test_the_gate_total_still_counts_doubles():
    """``total`` stays the conservative gate metric: a double still adds one."""
    counter = _session_counter()
    before = counter.total()
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        await client.post(LLM_URL, json={"p": 1})
    assert counter.total() == before + 1


class _Reporter:
    def __init__(self):
        self.lines = []
        self.config = SimpleNamespace(option=SimpleNamespace(xmlpath=None))

    def write_sep(self, sep, line):
        self.lines.append(line)

    def write_line(self, line):
        self.lines.append(line)


def _record(counter, url, network):
    entry = counter.observe_request(url, "POST")
    if network:
        from tests.llm_egress_counter import _CURRENT_ENTRY

        token = _CURRENT_ENTRY.set(entry)
        try:
            counter.observe_network_transport()
        finally:
            _CURRENT_ENTRY.reset(token)
    counter.observe_outcome(entry, response=SimpleNamespace(status_code=200))


def test_terminal_summary_names_only_network_hosts_as_hit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    counter = LLMEgressCounter(frozenset({"api.openai.com", "openrouter.ai"}))
    counter.current_test = "t::double"
    for _ in range(6):
        _record(counter, LLM_URL, network=False)
    counter.current_test = "t::live"
    _record(counter, "https://openrouter.ai/api/v1/chat/completions", network=True)

    reporter = _Reporter()
    LLMEgressPlugin(counter).pytest_terminal_summary(reporter, 0)

    assert "7 watched-LLM request(s)" in reporter.lines[0]
    assert "1 network, 6 in-process double" in reporter.lines[0]
    assert "LLM hosts hit: openrouter.ai" in reporter.lines
    assert (
        "LLM hosts answered by an in-process double: api.openai.com" in reporter.lines
    )
    report = json.loads(
        next(tmp_path.glob("llm_egress_report.*.json")).read_text(encoding="utf-8")
    )
    assert report["total"] == 7  # existing field, unchanged meaning
    assert report["llm_by_transport"] == {"network": 1, "in_process": 6}
    assert report["per_test_llm_network"] == {"t::live": 1}


def test_terminal_summary_with_doubles_only_names_no_host_as_hit(tmp_path, monkeypatch):
    """#2422 DoD 1: six doubled requests no longer read as a host hit."""
    monkeypatch.chdir(tmp_path)
    counter = LLMEgressCounter(frozenset({"api.openai.com"}))
    counter.current_test = "t::double"
    for _ in range(6):
        _record(counter, LLM_URL, network=False)

    reporter = _Reporter()
    LLMEgressPlugin(counter).pytest_terminal_summary(reporter, 0)

    assert not [line for line in reporter.lines if line.startswith("LLM hosts hit")]
    assert (
        "LLM hosts answered by an in-process double: api.openai.com" in reporter.lines
    )


async def test_real_httpx2_transport_request_is_network(local_server):
    """httpx2 is the transport openai>=3.x uses in CI (#1591): its network
    transport must be marked too, or every CI request would read in_process."""
    httpx2 = pytest.importorskip("httpx2")
    counter = _session_counter()
    async with httpx2.AsyncClient(trust_env=False) as client:
        await client.get(f"{local_server}/probe")
    entries = _entries(
        counter, "test_real_httpx2_transport_request_is_network", "127.0.0.1"
    )
    assert [r["transport"] for r in entries] == ["network"], entries

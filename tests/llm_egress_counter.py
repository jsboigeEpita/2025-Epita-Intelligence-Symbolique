"""LLM egress counter (#1787) — observation-only instrument for pytest sessions.

Counts outgoing HTTP requests to LLM endpoints while the gate runs. The success
value is 0: the gate runs under ``-m "not slow and not requires_api"``, so a test
that legitimately needs a model carries the marker and is already excluded — any
outgoing request during the gate is a leak by construction (#1591, #1787).

Because 0 is also what the counter reads when it is NOT wired (hook not
installed, transport replaced, client on an uninstrumented path), the non-vacuity
control in ``tests/unit/test_llm_egress_counter.py`` is part of the instrument:
it emits one request through each covered path and asserts the counter sees it.
That test runs inside the gate, so every gate report self-attests liveness: its
own row in the per-test breakdown must show the control requests.

Observation only — never blocks. Blocking is a gate (legitimate after #1591),
not an instrument. No pricing: a count, not an amount.
"""

import json
import os
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

DEFAULT_HOSTS = ("api.openai.com", "openrouter.ai")

# Env vars that carry an LLM endpoint URL (defaults + configured endpoints,
# including local/self-hosted ones — they cost no OpenRouter credits but are
# LLM egress and count).
_ENV_URL_VARS = (
    "OPENAI_BASE_URL",
    "BASE_URL",
    "OPENROUTER_BASE_URL",
    "AZURE_OPENAI_ENDPOINT",
    "OPENAI_BASE_URL_2",
    "OPENAI_BASE_URL_3",
    "OPENAI_BASE_URL_4",
    "SELF_HOSTED_LLM_ENDPOINT",
    "SELF_HOSTED_LLM_MINI_ENDPOINT",
)

SESSION_BUCKET = "(session)"


def llm_hosts_from_env() -> frozenset:
    """Default LLM hosts + hosts parsed from endpoint env vars (deduped)."""
    hosts = set(DEFAULT_HOSTS)
    for var in _ENV_URL_VARS:
        raw = os.getenv(var, "").strip()
        if not raw:
            continue
        candidate = urlparse(raw if "://" in raw else f"https://{raw}").hostname
        if candidate:
            hosts.add(candidate.lower())
    return frozenset(hosts)


class LLMEgressCounter:
    """Thread-safe tally of outgoing requests to LLM hosts, per test.

    Records (test, host, method, path) per request — never bodies or headers
    (privacy discipline: test names and URL paths only, no corpus content).
    """

    def __init__(self, hosts: frozenset) -> None:
        self._hosts = hosts
        self._lock = threading.Lock()
        self._requests: List[Dict[str, str]] = []
        self._per_test: "OrderedDict[str, int]" = OrderedDict()
        self.current_test: Optional[str] = None
        self._installed = False
        self._orig_client_send = None
        self._orig_async_send = None

    # ── observation core ──────────────────────────────────────────────

    def _matches(self, host: Optional[str]) -> bool:
        if not host:
            return False
        host = host.lower()
        for known in self._hosts:
            if host == known or host.endswith("." + known):
                return True
        return False

    def observe_request(self, url: Any, method: str) -> None:
        """Called from the httpx send wrappers. Must never raise into a test."""
        try:
            raw = str(url)
            parsed = urlparse(raw)
            host = parsed.hostname
            if not self._matches(host):
                return
            entry = {
                "test": self.current_test or SESSION_BUCKET,
                "host": host,
                "method": method,
                "path": parsed.path or "/",
            }
            with self._lock:
                self._requests.append(entry)
                self._per_test[entry["test"]] = self._per_test.get(entry["test"], 0) + 1
        except Exception:  # noqa: BLE001 — instrument must not break the measured run
            pass

    # ── install / uninstall (class-level httpx patch) ─────────────────

    def install(self) -> None:
        if self._installed:
            return
        import httpx

        counter = self

        def _client_send(client_self, request, **kwargs):
            counter.observe_request(request.url, request.method)
            return counter._orig_client_send(client_self, request, **kwargs)

        async def _async_send(client_self, request, **kwargs):
            counter.observe_request(request.url, request.method)
            return await counter._orig_async_send(client_self, request, **kwargs)

        self._orig_client_send = httpx.Client.send
        self._orig_async_send = httpx.AsyncClient.send
        httpx.Client.send = _client_send  # type: ignore[assignment]
        httpx.AsyncClient.send = _async_send  # type: ignore[assignment]
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        import httpx

        httpx.Client.send = self._orig_client_send  # type: ignore[assignment]
        httpx.AsyncClient.send = self._orig_async_send  # type: ignore[assignment]
        self._orig_client_send = None
        self._orig_async_send = None
        self._installed = False

    # ── reporting ─────────────────────────────────────────────────────

    def total(self) -> int:
        with self._lock:
            return len(self._requests)

    def per_test(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._per_test)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            requests = [dict(r) for r in self._requests]
            per_test = dict(self._per_test)
        return {
            "total": len(requests),
            "hosts_watched": sorted(self._hosts),
            "per_test": per_test,
            "requests": requests,
        }


# ── session singleton ──────────────────────────────────────────────────

_SESSION_COUNTER: Optional[LLMEgressCounter] = None


def activate() -> LLMEgressCounter:
    """Install the counter for this pytest session (idempotent)."""
    global _SESSION_COUNTER
    if _SESSION_COUNTER is None:
        _SESSION_COUNTER = LLMEgressCounter(llm_hosts_from_env())
        _SESSION_COUNTER.install()
    return _SESSION_COUNTER


def get_counter() -> Optional[LLMEgressCounter]:
    """The session counter, or None when not activated (plain pytest import)."""
    return _SESSION_COUNTER


def write_report(counter: LLMEgressCounter, config: Any) -> Optional[Path]:
    """Write ``llm_egress_report.json`` next to the junitxml artifact (or CWD)."""
    data = counter.snapshot()
    data["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    xmlpath = getattr(getattr(config, "option", None), "xmlpath", None)
    target_dir = Path(xmlpath).parent if xmlpath else Path(".")
    out = target_dir / "llm_egress_report.json"
    try:
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
    except OSError:
        return None


class LLMEgressPlugin:
    """Pytest plugin wiring the counter: attribution, report, artifact."""

    def __init__(self, counter: LLMEgressCounter) -> None:
        self.counter = counter

    def pytest_runtest_setup(self, item: Any) -> None:
        self.counter.current_test = item.nodeid

    def pytest_runtest_teardown(self, item: Any) -> None:
        # Post-test emissions (session-scope fixture teardown, loop cleanup)
        # bucket to "(session)" — attributing them to the just-finished test
        # would miscount.
        self.counter.current_test = None

    def pytest_terminal_summary(self, terminalreporter: Any, exitstatus: Any) -> None:
        snap = self.counter.snapshot()
        total = snap["total"]
        line = f"LLM egress (#1787): {total} request(s) to LLM hosts during this session (gate expectation: 0)"
        terminalreporter.write_sep("=", line)
        if total:
            terminalreporter.write_line("Per-test breakdown (test -> requests):")
            for test, count in sorted(snap["per_test"].items(), key=lambda kv: -kv[1]):
                terminalreporter.write_line(f"  {count:5d}  {test}")
            hosts = sorted({r["host"] for r in snap["requests"]})
            terminalreporter.write_line(f"Hosts hit: {', '.join(hosts)}")
            report_path = write_report(self.counter, terminalreporter.config)
            if report_path:
                terminalreporter.write_line(f"Full report: {report_path}")
        else:
            terminalreporter.write_line(
                "0 — indistinguishable from an unwired counter unless the "
                "non-vacuity control (tests/unit/test_llm_egress_counter.py) "
                "ran in this session and shows its control requests in the "
                "report/artifact."
            )
            report_path = write_report(self.counter, terminalreporter.config)
            if report_path:
                terminalreporter.write_line(f"Report (empty): {report_path}")

    def pytest_sessionfinish(self, session: Any) -> None:
        self.counter.uninstall()

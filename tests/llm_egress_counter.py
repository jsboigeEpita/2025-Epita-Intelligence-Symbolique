"""LLM egress counter (#1787, 3-state #1591) — observation-only pytest instrument.

Counts outgoing HTTP requests during the gate in three classes, so that an
absent env var produces "unknown host seen" instead of silence (#1591):

- ``llm``     — request to a watched LLM host. Watched = defaults
                (api.openai.com, openrouter.ai) + hosts parsed from endpoint
                env vars. THE gate metric: expectation 0 (the gate runs under
                ``-m "not slow and not requires_api"``, so any LLM call is a
                leak by construction, #1591/#1787).
- ``nonllm``  — request to a known non-LLM host (test infra: tika, github,
                pypi). Counted for completeness, not a leak.
- ``unknown`` — anything else. NOT ignored: a request to a self-hosted/localhost
                LLM endpoint whose env var is absent from this environment
                lands here — visible, auditable, never silently dropped
                (coordinator R825: "0 propre ≡ 0 débranché", un cran plus bas
                — the hook is wired, but its host list shrinks with the env).

Because the ``llm`` success value is 0 — exactly what an unwired counter
reads — the non-vacuity controls in ``tests/unit/test_llm_egress_counter.py``
are part of the instrument: they emit one request per covered path and assert
the counter sees it. They run inside the gate, so every gate report
self-attests liveness through their own rows.

Each request also carries a ``transport`` field (#2422): ``network`` when it
reached httpx's (or httpx2's) own network transport, ``in_process`` otherwise —
a ``MockTransport``, a replaced transport, an ASGI app. The hook sits on
``Client.send``, above the transport, so it sees doubles too: that is what lets
the non-vacuity controls prove liveness without spending, and it is also why a
report that did not tell the two apart read test doubles as "LLM hosts hit".
The gate metric ``total`` still counts every watched-LLM request, doubles
included: ``in_process`` means "never reached the httpx network transport",
and a third-party transport doing its own I/O would read the same, so the
split informs the reader and never lowers the gate's count.

Observation only — never blocks. Blocking is a gate (legitimate after #1591),
not an instrument. No pricing: a count, not an amount. The gate that blocks
is ``scripts/ci/llm_egress_gate.py`` (#2444): the CI job fails when the
report's ``per_test_llm_network`` is not empty, and names the tests.
"""

import contextvars

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

# Non-LLM hosts the test infrastructure legitimately contacts. Deliberately
# minimal: anything not here and not LLM-watched surfaces as "unknown".
# "testserver" is the ASGI/starlette TestClient base host — in-process loopback
# exercising the app object, never external egress (first CI run with the
# 3-state counter showed 141 of them drowning the unknown bucket).
KNOWN_NON_LLM_HOSTS = frozenset(
    {
        "tika.open-webui.myia.io",
        "api.github.com",
        "github.com",
        "raw.githubusercontent.com",
        "objects.githubusercontent.com",
        "pypi.org",
        "files.pythonhosted.org",
        "testserver",
    }
)

CLASS_LLM = "llm"
CLASS_NON_LLM = "nonllm"
CLASS_UNKNOWN = "unknown"

SESSION_BUCKET = "(session)"

TRANSPORT_NETWORK = "network"
TRANSPORT_IN_PROCESS = "in_process"

# The entry of the send in progress, so the network transport it reaches (if
# any) can mark it. A context variable follows the send into the transport
# within one task or thread, and does not leak across concurrent sends.
_CURRENT_ENTRY: "contextvars.ContextVar[Optional[Dict[str, Any]]]" = (
    contextvars.ContextVar("llm_egress_current_entry", default=None)
)


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
    """Thread-safe tally of outgoing requests, 3-state classified, per test.

    Records (test, host, method, path, class) per request — never bodies or
    headers (privacy discipline: test names and URL paths only, no corpus
    content).
    """

    def __init__(self, hosts: frozenset) -> None:
        self._hosts = hosts
        self._lock = threading.Lock()
        self._requests: List[Dict[str, str]] = []
        self._per_test: "OrderedDict[str, int]" = OrderedDict()  # llm only
        self._per_test_unknown: "OrderedDict[str, int]" = OrderedDict()
        self.current_test: Optional[str] = None
        self._installed = False
        self._patched_mods: List[Any] = []
        # Immutable snapshot of patched transport names, set at install and
        # never cleared: uninstall() empties _patched_mods before the terminal
        # report reads it (sessionfinish -> terminal_summary), which made
        # `transports_patched` read [] in the report (#1591).
        self._transports_names: List[str] = []
        self._orig_sends: Dict[Any, Any] = {}
        self._orig_transports: Dict[Any, Any] = {}

    # ── observation core ──────────────────────────────────────────────

    def _classify(self, host: Optional[str]) -> Optional[str]:
        """Return 'llm' | 'nonllm' | 'unknown', or None when host unparsable."""
        if not host:
            return None
        host = host.lower()
        for known in self._hosts:
            if host == known or host.endswith("." + known):
                return CLASS_LLM
        if host in KNOWN_NON_LLM_HOSTS:
            return CLASS_NON_LLM
        return CLASS_UNKNOWN

    def observe_request(self, url: Any, method: str) -> Optional[Dict[str, Any]]:
        """Called from the httpx send wrappers. Must never raise into a test.

        Returns the recorded entry so the wrapper can attach the outcome of
        the send to it (``observe_outcome``), or ``None`` when unclassified.
        """
        try:
            raw = str(url)
            parsed = urlparse(raw)
            host = parsed.hostname
            klass = self._classify(host)
            if klass is None:
                return None
            entry = {
                "test": self.current_test or SESSION_BUCKET,
                "host": host,
                "method": method,
                "path": parsed.path or "/",
                "class": klass,
                # Until the network transport marks it (#2422).
                "transport": TRANSPORT_IN_PROCESS,
            }
            with self._lock:
                self._requests.append(entry)
                if klass == CLASS_LLM:
                    self._per_test[entry["test"]] = (
                        self._per_test.get(entry["test"], 0) + 1
                    )
                elif klass == CLASS_UNKNOWN:
                    self._per_test_unknown[entry["test"]] = (
                        self._per_test_unknown.get(entry["test"], 0) + 1
                    )
            return entry
        except Exception:  # noqa: BLE001 — instrument must not break the measured run
            return None

    def observe_outcome(
        self,
        entry: Optional[Dict[str, Any]],
        response: Any = None,
        error: Optional[BaseException] = None,
    ) -> None:
        """Attach the send's outcome to its entry: HTTP status, or the error type.

        #2391: without it the report said *that* a request left, never *how*
        it came back. A 400 answered to every tool-carrying call was visible
        only when a test failed and pytest printed its captured log; in a
        passing test (or a record run) the same 400s were silent, and a
        degraded fallback looked exactly like a healthy call. Must never
        raise into a test.
        """
        if entry is None:
            return
        try:
            with self._lock:
                if error is not None:
                    entry["error"] = type(error).__name__
                else:
                    entry["status"] = int(response.status_code)
        except Exception:  # noqa: BLE001 — instrument must not break the measured run
            pass

    @staticmethod
    def observe_network_transport() -> None:
        """Mark the send in progress as having reached a network transport (#2422).

        Called from the wrapped ``handle_request`` / ``handle_async_request`` of
        httpx's own ``HTTPTransport`` / ``AsyncHTTPTransport`` classes. Must
        never raise into a test.
        """
        try:
            entry = _CURRENT_ENTRY.get()
            if entry is not None:
                entry["transport"] = TRANSPORT_NETWORK
        except Exception:  # noqa: BLE001 — instrument must not break the measured run
            pass

    # ── install / uninstall (class-level httpx + httpx2 patch) ─────────
    #
    # openai>=3.x dropped its httpx dependency for httpx2 (requires_dist of
    # openai 3.1.0: httpx2<3,>=2.7.0 — no httpx). CI resolves openai 3.1.0
    # (environment.yml is unpinned), so every SDK call that does NOT inject
    # an httpx client leaves via httpx2.AsyncClient.send there. Patching
    # httpx only made the CI gate read a false 0 for exactly those calls
    # (#1591 livrable 0: run 32048104455 "3 requests" = 3 controls only,
    # while the 12 openrouter-class leaks fired uncounted). httpx2 is absent
    # from local envs — hence the guarded import, not a hard dependency.

    def _make_wrappers(self, mod):
        counter = self

        def _client_send(client_self, request, **kwargs):
            entry = counter.observe_request(request.url, request.method)
            token = _CURRENT_ENTRY.set(entry)
            try:
                response = counter._orig_sends[(mod, "sync")](
                    client_self, request, **kwargs
                )
            except BaseException as exc:
                counter.observe_outcome(entry, error=exc)
                raise
            finally:
                _CURRENT_ENTRY.reset(token)
            counter.observe_outcome(entry, response=response)
            return response

        async def _async_send(client_self, request, **kwargs):
            entry = counter.observe_request(request.url, request.method)
            token = _CURRENT_ENTRY.set(entry)
            try:
                response = await counter._orig_sends[(mod, "async")](
                    client_self, request, **kwargs
                )
            except BaseException as exc:
                counter.observe_outcome(entry, error=exc)
                raise
            finally:
                _CURRENT_ENTRY.reset(token)
            counter.observe_outcome(entry, response=response)
            return response

        return _client_send, _async_send

    def _make_transport_wrappers(self, mod):
        counter = self

        def _handle_request(transport_self, request):
            counter.observe_network_transport()
            return counter._orig_transports[(mod, "sync")](transport_self, request)

        async def _handle_async_request(transport_self, request):
            counter.observe_network_transport()
            return await counter._orig_transports[(mod, "async")](
                transport_self, request
            )

        return _handle_request, _handle_async_request

    def _patch_network_transports(self, mod) -> None:
        """Wrap the network transport classes of ``mod`` (#2422).

        The class objects are captured here, at install, so a test that
        rebinds the name ``httpx.AsyncHTTPTransport`` to a double does not
        reach the wrapper: its requests stay ``in_process``, as they should.
        """
        try:
            sync_cls = mod.HTTPTransport
            async_cls = mod.AsyncHTTPTransport
            self._orig_transports[(mod, "sync")] = sync_cls.handle_request
            self._orig_transports[(mod, "async")] = async_cls.handle_async_request
            self._orig_transports[(mod, "classes")] = (sync_cls, async_cls)
            handle, handle_async = self._make_transport_wrappers(mod)
            sync_cls.handle_request = handle  # type: ignore[assignment]
            async_cls.handle_async_request = handle_async  # type: ignore[assignment]
        except AttributeError:
            for key in ((mod, "sync"), (mod, "async"), (mod, "classes")):
                self._orig_transports.pop(key, None)

    def install(self) -> None:
        if self._installed:
            return
        import httpx

        self._orig_sends = {}
        self._orig_transports = {}
        self._patched_mods = []
        try:
            import httpx2  # noqa: F401 — openai>=3.x transport (CI)

            mods = (httpx, httpx2)
        except ImportError:
            mods = (httpx,)
        for mod in mods:
            try:
                self._orig_sends[(mod, "sync")] = mod.Client.send
                self._orig_sends[(mod, "async")] = mod.AsyncClient.send
                client_send, async_send = self._make_wrappers(mod)
                mod.Client.send = client_send  # type: ignore[assignment]
                mod.AsyncClient.send = async_send  # type: ignore[assignment]
                self._patched_mods.append(mod)
            except AttributeError:
                continue
            self._patch_network_transports(mod)
        self._transports_names = [m.__name__ for m in self._patched_mods]
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        for mod in self._patched_mods:
            mod.Client.send = self._orig_sends[(mod, "sync")]  # type: ignore[assignment]
            mod.AsyncClient.send = self._orig_sends[(mod, "async")]  # type: ignore[assignment]
            classes = self._orig_transports.get((mod, "classes"))
            if classes is not None:
                sync_cls, async_cls = classes
                sync_cls.handle_request = self._orig_transports[(mod, "sync")]
                async_cls.handle_async_request = self._orig_transports[(mod, "async")]
        self._patched_mods = []
        self._orig_sends = {}
        self._orig_transports = {}
        self._installed = False

    # ── reporting ─────────────────────────────────────────────────────

    def total(self) -> int:
        """LLM-watched request count — the gate metric (expectation 0)."""
        with self._lock:
            return sum(1 for r in self._requests if r["class"] == CLASS_LLM)

    def per_test(self) -> Dict[str, int]:
        """LLM-watched requests per test (leak ventilation)."""
        with self._lock:
            return dict(self._per_test)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            requests = [dict(r) for r in self._requests]
            per_test = dict(self._per_test)
            per_test_unknown = dict(self._per_test_unknown)
        totals = {c: 0 for c in (CLASS_LLM, CLASS_NON_LLM, CLASS_UNKNOWN)}
        llm_by_transport = {TRANSPORT_NETWORK: 0, TRANSPORT_IN_PROCESS: 0}
        per_test_llm_network: Dict[str, int] = {}
        llm_outcomes: Dict[str, int] = {}
        per_test_llm_not_ok: Dict[str, int] = {}
        for r in requests:
            totals[r["class"]] += 1
            if r["class"] != CLASS_LLM:
                continue
            transport = r.get("transport", TRANSPORT_IN_PROCESS)
            llm_by_transport[transport] = llm_by_transport.get(transport, 0) + 1
            if transport == TRANSPORT_NETWORK:
                per_test_llm_network[r["test"]] = (
                    per_test_llm_network.get(r["test"], 0) + 1
                )
            outcome = _outcome_label(r)
            llm_outcomes[outcome] = llm_outcomes.get(outcome, 0) + 1
            if not outcome.startswith("2"):
                per_test_llm_not_ok[r["test"]] = (
                    per_test_llm_not_ok.get(r["test"], 0) + 1
                )
        return {
            "total": totals[CLASS_LLM],
            "totals_by_class": totals,
            "hosts_watched": sorted(self._hosts),
            "transports_patched": list(self._transports_names),
            "per_test": per_test,
            "per_test_unknown": per_test_unknown,
            "llm_outcomes": llm_outcomes,
            "per_test_llm_not_ok": per_test_llm_not_ok,
            # #2422: which watched-LLM requests reached a network transport.
            # ``total`` above still counts both.
            "llm_by_transport": llm_by_transport,
            "per_test_llm_network": per_test_llm_network,
            "requests": requests,
        }


def _outcome_label(entry: Dict[str, Any]) -> str:
    """``"200"``, ``"400"``… ; ``"error:<Type>"`` ; ``"none"`` if no outcome was seen."""
    if "status" in entry:
        return str(entry["status"])
    if "error" in entry:
        return f"error:{entry['error']}"
    return "none"


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
    """Write the egress report next to the junitxml artifact (or CWD).

    A session with ``--junitxml`` is (by construction) the gate; it writes the
    canonical ``llm_egress_report.json`` the CI artifact uploads. A session
    WITHOUT one is nested — a worker spawned by a launcher (a second, unfiltered
    pytest session). Before #1872 both wrote the same canonical name, so a child
    overwrote the gate's tally exactly when the leak made that tally matter. The
    nested session writes a per-process distinct path instead, leaving the
    parent's canonical report intact.
    """
    data = counter.snapshot()
    data["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    xmlpath = getattr(getattr(config, "option", None), "xmlpath", None)
    if xmlpath:
        out = Path(xmlpath).parent / "llm_egress_report.json"
    else:
        out = Path(f"llm_egress_report.{os.getpid()}.json")
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
        t = snap["totals_by_class"]
        by_transport = snap["llm_by_transport"]
        line = (
            f"LLM egress (#1787): {t['llm']} watched-LLM request(s) "
            f"(gate expectation: 0; {by_transport[TRANSPORT_NETWORK]} network, "
            f"{by_transport[TRANSPORT_IN_PROCESS]} in-process double) · "
            f"{t['nonllm']} known non-LLM · {t['unknown']} UNKNOWN host"
        )
        terminalreporter.write_sep("=", line)
        if t["llm"]:
            network = snap["per_test_llm_network"]
            terminalreporter.write_line(
                "Per-test LLM breakdown (test -> requests, of which network):"
            )
            for test, count in sorted(snap["per_test"].items(), key=lambda kv: -kv[1]):
                terminalreporter.write_line(
                    f"  {count:5d}  {test}  (network: {network.get(test, 0)})"
                )
            # #2422: "hosts hit" names only what reached a network transport;
            # a host answered by a test double is listed apart, as such.
            for label, transport in (
                ("LLM hosts hit", TRANSPORT_NETWORK),
                ("LLM hosts answered by an in-process double", TRANSPORT_IN_PROCESS),
            ):
                hosts = sorted(
                    {
                        r["host"]
                        for r in snap["requests"]
                        if r["class"] == CLASS_LLM
                        and r.get("transport", TRANSPORT_IN_PROCESS) == transport
                    }
                )
                if hosts:
                    terminalreporter.write_line(f"{label}: {', '.join(hosts)}")
            outcomes = ", ".join(
                f"{label}×{n}" for label, n in sorted(snap["llm_outcomes"].items())
            )
            terminalreporter.write_line(f"LLM response outcomes: {outcomes}")
            if snap["per_test_llm_not_ok"]:
                terminalreporter.write_line(
                    "Per-test LLM responses that were not 2xx (test -> count):"
                )
                for test, count in sorted(
                    snap["per_test_llm_not_ok"].items(), key=lambda kv: -kv[1]
                ):
                    terminalreporter.write_line(f"  {count:5d}  {test}")
        elif not any("test_llm_egress_counter" in t_ for t_ in snap["per_test"]):
            terminalreporter.write_line(
                "0 LLM requests and the non-vacuity control did NOT run in this "
                "session — this 0 is indistinguishable from an unwired counter "
                "(tests/unit/test_llm_egress_counter.py must run for liveness)."
            )
        if t["unknown"]:
            terminalreporter.write_line(
                "UNKNOWN hosts seen (not watched-LLM, not known infra — if an "
                "endpoint env var is absent here, its requests surface here):"
            )
            unknown_hosts: Dict[str, int] = {}
            for r in snap["requests"]:
                if r["class"] == CLASS_UNKNOWN:
                    unknown_hosts[r["host"]] = unknown_hosts.get(r["host"], 0) + 1
            for host, n in sorted(unknown_hosts.items(), key=lambda kv: -kv[1]):
                terminalreporter.write_line(f"  {n:5d}  {host}")
        report_path = write_report(self.counter, terminalreporter.config)
        if report_path:
            terminalreporter.write_line(f"Egress report: {report_path}")

    def pytest_sessionfinish(self, session: Any) -> None:
        self.counter.uninstall()

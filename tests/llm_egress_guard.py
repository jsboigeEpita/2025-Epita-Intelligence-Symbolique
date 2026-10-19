"""Execution-time hermeticity guard (#3069).

A test that is NOT marked ``requires_api`` must not emit a network request
to a watched-LLM host — outside record mode. The incident (#3069, seat
po-2025): an ad-hoc ``-k "atms or governance or 2850 or trace"`` with
``-m "not requires_api"`` burned 586 live calls because three trace-structure
sherlock tests and eight ``debate_governance`` parametrizations carry no
marker and run the real pipeline whenever a seat's ``.env`` holds a key.
``-m`` deselects only MARKED tests; nothing failed; the egress counter
reported the spend post hoc.

This plugin is the policy consumer of the observation-only counter
(#1787): it subscribes to the per-entry notification (``on_entry``) and
enforces at run time —

- the offending test FAILS (its passed ``call`` report is flipped with a
  message naming host and request count), and
- ``session.shouldstop`` is set, so the run halts after the current test
  instead of letting the rest of the ``-k`` selection repeat the leak.

Why flip the report rather than raise inside ``Client.send``: the counter's
contract is "never blocks" (its wrappers wrap every httpx send — raising
there puts blocking into the instrument), and the openai client's retry
loop retries client-side exceptions silently (#2936). The guard therefore
lets the request path complete untouched and enforces at the report
boundary: a future unmarked spender costs one detection (the single test
body that exposed it), never a whole selection — the known spenders are
made hermetic by the same PR.

Exemptions (each carries its reason):
- ``requires_api`` marker — the test declares it measures live LLM behavior;
  the live band and the cassette record runs are exactly this population.
- ``LLM_CACHE_MODE=record`` (``llm_cache.get_cache_mode()``) — record runs
  spend by design; replay mode never leaks network by construction (a cache
  miss raises, it does not fall through to the wire).
- ``in_process`` transport — a request answered by a test double never left
  the machine (#2422); the counter's own non-vacuity controls live here.
- the ``(session)`` bucket — emissions between tests (fixture teardown, loop
  cleanup) are not attributable to a test and stay a report matter.
- non-``llm`` classes — the guard polices watched-LLM egress only; unknown
  hosts remain the counter's audit surface, not a per-test failure.

Known edge, accepted: a seat whose endpoint env vars point at loopback (a
local proxy) makes 127.0.0.1 a *watched* host, so the transport-liveness
controls (``test_llm_egress_transport_2422.py``) would trip this guard on
such a seat. Those controls exercise the real socket deliberately and never
leave the machine; if that seat exists, mark them — measured first, not
speculatively (#3049 recipe).
"""

from typing import Any, Dict, List

import pytest

from tests.llm_egress_counter import (
    CLASS_LLM,
    SESSION_BUCKET,
    TRANSPORT_NETWORK,
    LLMEgressCounter,
)

_MARKER = "requires_api"


class LLMEgressGuard:
    """Fail unmarked tests that make live watched-LLM requests (#3069)."""

    def __init__(self, counter: LLMEgressCounter) -> None:
        self.counter = counter
        self._violations: Dict[str, List[Dict[str, str]]] = {}
        self._marked: Dict[str, bool] = {}
        self._items: Dict[str, Any] = {}
        counter.on_entry = self._on_entry

    # ── policy (invoked by the counter, once per completed request) ────

    def _record_mode(self) -> bool:
        """True when the run records cassettes — spending is the point then."""
        try:
            from argumentation_analysis.services.llm_cache import RECORD, get_cache_mode

            return get_cache_mode() == RECORD
        except Exception:  # noqa: BLE001 — bad mode value: fail open, never block
            return False

    def _on_entry(self, entry: Dict[str, Any]) -> None:
        nodeid = entry.get("test")
        if entry.get("class") != CLASS_LLM:
            return
        if entry.get("transport") != TRANSPORT_NETWORK:
            return
        if not nodeid or nodeid == SESSION_BUCKET:
            return
        if self._record_mode():
            return
        if self._marked.get(nodeid):
            return
        self._violations.setdefault(nodeid, []).append(
            {"host": str(entry.get("host")), "path": str(entry.get("path"))}
        )
        # Halt the run after this test — the rest of the selection must not
        # repeat the leak (586-call incident was one -k away from more).
        item = self._items.get(nodeid)
        if item is not None:
            item.session.shouldstop = (
                f"hermeticity guard (#3069): {nodeid} made a live LLM request "
                f"to {entry.get('host')} without the requires_api marker — "
                "make the test hermetic or mark it, see #3069"
            )

    # ── pytest plugin surface ──────────────────────────────────────────

    def pytest_runtest_setup(self, item: Any) -> None:
        self._items[item.nodeid] = item
        self._marked[item.nodeid] = item.get_closest_marker(_MARKER) is not None

    def pytest_runtest_teardown(self, item: Any) -> None:
        self._items.pop(item.nodeid, None)
        self._marked.pop(item.nodeid, None)
        # Violations stay: the call report (makereport) and the terminal
        # summary read them after teardown.

    def _violation_longrepr(self, nodeid: str, violations: List[Dict[str, str]]) -> str:
        hosts = sorted({v["host"] for v in violations})
        return (
            f"Hermeticity violation (#3069): {nodeid} made {len(violations)} "
            f"live LLM request(s) to {', '.join(hosts)} without the "
            "requires_api marker. Either the test measures real LLM behavior "
            "— then mark it requires_api — or it asserts structure and must "
            "be hermetic (neutralize the LLM env / double at the boundary)."
        )

    def flip_report_if_violated(self, report: Any, nodeid: str) -> None:
        """Flip a PASSED call report to failed when its test violated.

        Split out of the hookwrapper so the policy is unit-testable without
        pluggy machinery.
        """
        violations = self._violations.get(nodeid)
        if not violations or not report.passed:
            return
        report.outcome = "failed"
        report.longrepr = self._violation_longrepr(nodeid, violations)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: Any, call: Any):
        outcome = yield
        if call.when != "call":
            return
        self.flip_report_if_violated(outcome.get_result(), item.nodeid)

    def pytest_terminal_summary(self, terminalreporter: Any, exitstatus: Any) -> None:
        if not self._violations:
            return
        terminalreporter.write_sep(
            "=",
            f"hermeticity guard (#3069): {len(self._violations)} unmarked "
            "test(s) made live LLM requests",
        )
        for nodeid, violations in sorted(self._violations.items()):
            hosts = sorted({v["host"] for v in violations})
            terminalreporter.write_line(
                f"  {nodeid}: {len(violations)} request(s) to {', '.join(hosts)}"
            )
        terminalreporter.write_line(
            "  Fix: hermetic double at the LLM boundary, or the requires_api "
            "marker when the test truly measures live behavior (#3069)."
        )

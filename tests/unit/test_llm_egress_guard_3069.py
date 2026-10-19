"""Hermeticity guard tests (#3069).

The guard is the policy consumer of the observation-only egress counter
(#1787): an UNMARKED test that emits a network request to a watched-LLM
host fails, the session stops, record mode and the ``requires_api`` marker
exempt. These tests drive the instrument→guard seam directly (entries fed
through the real counter, no socket) — the real-population mutation (an
unmarked live spender failed end-to-end) is demonstrated in the PR body via
a loopback endpoint env var, zero external spend.
"""

from types import SimpleNamespace

import pytest

from tests.llm_egress_counter import (
    _CURRENT_ENTRY,
    LLMEgressCounter,
)
from tests.llm_egress_guard import LLMEgressGuard

LLM_URL = "https://api.openai.com/v1/chat/completions"


class _FakeMarker:
    """Truthy stand-in for a pytest Mark."""


class _FakeItem:
    def __init__(self, nodeid: str, marked: bool = False) -> None:
        self.nodeid = nodeid
        self._marked = marked
        self.session = SimpleNamespace(shouldstop=None)

    def get_closest_marker(self, name: str):
        return _FakeMarker() if (self._marked and name == "requires_api") else None


class _FakeReport:
    def __init__(self, passed: bool) -> None:
        self.outcome = "passed" if passed else "failed"
        self.passed = passed
        self.longrepr = None


def _guard() -> "tuple[LLMEgressCounter, LLMEgressGuard]":
    """Fresh counter (no httpx patching) + guard wired to its notifications."""
    counter = LLMEgressCounter(frozenset({"api.openai.com", "openrouter.ai"}))
    return counter, LLMEgressGuard(counter)


def _feed(counter: LLMEgressCounter, test: str, url: str, *, network: bool):
    """Drive one full entry through the real observation chain."""
    counter.current_test = test
    entry = counter.observe_request(url, "POST")
    assert entry is not None, "url must classify (llm/nonllm/unknown)"
    if network:
        token = _CURRENT_ENTRY.set(entry)
        try:
            counter.observe_network_transport()
        finally:
            _CURRENT_ENTRY.reset(token)
    counter.observe_outcome(entry, response=SimpleNamespace(status_code=200))
    counter.current_test = None
    return entry


def test_unmarked_network_llm_request_fails_the_report_and_stops_the_session():
    counter, guard = _guard()
    item = _FakeItem("tests/x.py::test_spender")
    guard.pytest_runtest_setup(item)

    _feed(counter, "tests/x.py::test_spender", LLM_URL, network=True)

    assert "tests/x.py::test_spender" in guard._violations
    assert item.session.shouldstop, "the run must halt after the offender"
    report = _FakeReport(passed=True)
    guard.flip_report_if_violated(report, "tests/x.py::test_spender")
    assert report.outcome == "failed"
    assert "requires_api" in report.longrepr and "api.openai.com" in report.longrepr


def test_the_counter_notification_reaches_the_guard():
    """The seam: entries observed by the counter trigger the guard policy."""
    counter, guard = _guard()
    guard.pytest_runtest_setup(_FakeItem("tests/x.py::test_t"))
    _feed(counter, "tests/x.py::test_t", LLM_URL, network=True)
    assert guard._violations["tests/x.py::test_t"][0]["host"] == "api.openai.com"


def test_requires_api_marker_is_exempt():
    counter, guard = _guard()
    guard.pytest_runtest_setup(_FakeItem("tests/x.py::test_live", marked=True))
    _feed(counter, "tests/x.py::test_live", LLM_URL, network=True)
    assert not guard._violations


def test_in_process_double_is_exempt():
    """A request answered by a double never left the machine (#2422)."""
    counter, guard = _guard()
    guard.pytest_runtest_setup(_FakeItem("tests/x.py::test_double"))
    _feed(counter, "tests/x.py::test_double", LLM_URL, network=False)
    assert not guard._violations


def test_non_llm_host_is_exempt():
    counter, guard = _guard()
    guard.pytest_runtest_setup(_FakeItem("tests/x.py::test_infra"))
    _feed(counter, "tests/x.py::test_infra", "https://api.github.com/x", network=True)
    assert not guard._violations


def test_session_bucket_is_exempt():
    """Emissions between tests are a report matter, not a test failure."""
    counter, guard = _guard()
    _feed(counter, "(session)", LLM_URL, network=True)
    assert not guard._violations


def test_record_mode_is_exempt(monkeypatch: pytest.MonkeyPatch):
    """LLM_CACHE_MODE=record spends by design — the guard stands down."""
    counter, guard = _guard()
    monkeypatch.setenv("LLM_CACHE_MODE", "record")
    guard.pytest_runtest_setup(_FakeItem("tests/x.py::test_recorder"))
    _feed(counter, "tests/x.py::test_recorder", LLM_URL, network=True)
    assert not guard._violations


def test_replay_mode_does_not_exempt(monkeypatch: pytest.MonkeyPatch):
    """Replay must never reach the wire; a network request there is a leak."""
    counter, guard = _guard()
    monkeypatch.setenv("LLM_CACHE_MODE", "replay")
    guard.pytest_runtest_setup(_FakeItem("tests/x.py::test_replayed"))
    _feed(counter, "tests/x.py::test_replayed", LLM_URL, network=True)
    assert "tests/x.py::test_replayed" in guard._violations


def test_an_already_failed_report_is_not_rewritten():
    counter, guard = _guard()
    guard.pytest_runtest_setup(_FakeItem("tests/x.py::test_broken"))
    _feed(counter, "tests/x.py::test_broken", LLM_URL, network=True)
    report = _FakeReport(passed=False)
    guard.flip_report_if_violated(report, "tests/x.py::test_broken")
    assert report.outcome == "failed" and report.longrepr is None


# ── census mode (#3074) — record every offender, stop at none ────────────


def test_census_mode_records_without_stopping(monkeypatch: pytest.MonkeyPatch):
    """The census needs the whole population of one run, not the first one."""
    monkeypatch.setenv("LLM_EGRESS_GUARD_CENSUS", "1")
    counter, guard = _guard()
    item = _FakeItem("tests/x.py::test_census_spender")
    guard.pytest_runtest_setup(item)

    _feed(counter, "tests/x.py::test_census_spender", LLM_URL, network=True)

    assert "tests/x.py::test_census_spender" in guard._violations
    assert item.session.shouldstop is None, "census records; it never stops the run"
    report = _FakeReport(passed=True)
    guard.flip_report_if_violated(report, "tests/x.py::test_census_spender")
    assert report.outcome == "passed", "the census measures attempts, not tests"


def test_census_mode_lists_several_offenders_in_one_pass(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("LLM_EGRESS_GUARD_CENSUS", "true")
    counter, guard = _guard()
    for nodeid in ("tests/x.py::test_a", "tests/x.py::test_b"):
        guard.pytest_runtest_setup(_FakeItem(nodeid))
        _feed(counter, nodeid, LLM_URL, network=True)
    assert set(guard._violations) == {"tests/x.py::test_a", "tests/x.py::test_b"}


def test_enforcing_mode_is_the_default(monkeypatch: pytest.MonkeyPatch):
    """Control: the same feed without the switch still stops the session."""
    monkeypatch.delenv("LLM_EGRESS_GUARD_CENSUS", raising=False)
    counter, guard = _guard()
    item = _FakeItem("tests/x.py::test_enforced")
    guard.pytest_runtest_setup(item)
    _feed(counter, "tests/x.py::test_enforced", LLM_URL, network=True)
    assert item.session.shouldstop, "the enforcing form remains the default"

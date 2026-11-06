"""#3447 — the async transport drives the breaker itself, not through tornado.

The merged #3440 repair routed ``ResilientAsyncTransport`` through
``network_breaker.call_async(_inner)``. Two measured properties of that call
made it unfit for the hot path:

1. ``CircuitBreaker.call_async`` is built on ``tornado.gen.coroutine``.
   ``tornado`` is declared neither in ``environment.yml`` nor in
   ``pyproject.toml``: ``pybreaker.gen`` is ``None`` without it, and the
   transport depends on a package nothing installs.
2. The same ``call_async`` holds ``self._lock`` (a ``threading.RLock``) for
   the whole HTTP request, so concurrent calls from several threads or loops
   serialise on the first one's latency.

The repair keeps pybreaker's state machine — it is what counts, opens at
``fail_max`` and half-opens at ``reset_timeout`` — and drives it around the
``await`` with its own primitives (``CircuitBreakerState.call`` does exactly
that: gate, call, ``_handle_error`` / ``_handle_success``). The witnesses
below are the issue's: ``tornado`` neutralised, the lock free while the
request is in flight, and the #3440 probes still holding (a stalled attempt
is replayed, the breaker counts the failure, a trip keeps the next call off
the wire).

Born red on the #3435/#3440 tree: ``call_async`` is on the hot path (a live
``ast.Attribute``), ``pybreaker.gen = None`` makes that call raise instead of
answering, and a probe thread cannot take the lock while the request is in
flight.
"""

import ast
import asyncio
import threading
from pathlib import Path

import httpx
import pybreaker
import pytest

import argumentation_analysis.core.utils.network_utils as network_utils
from argumentation_analysis.core.utils.network_utils import ResilientAsyncTransport

SOURCE_PATH = Path(network_utils.__file__).resolve()


def _fresh_breaker(monkeypatch, fail_max: int = 3, reset_timeout: float = 60.0):
    """A breaker owned by the test, installed where the transport reads it."""
    breaker = pybreaker.CircuitBreaker(fail_max=fail_max, reset_timeout=reset_timeout)
    monkeypatch.setattr(network_utils, "network_breaker", breaker)
    return breaker


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://example.test/v1/chat/completions")


class _CountingTransport(httpx.AsyncBaseTransport):
    """Answers (or stalls) on the first calls, then succeeds.

    ``counters_seen`` records the breaker's failure counter as read from
    inside the call, which is the only place the intermediate count is
    visible: a success resets it before the caller gets control back.
    """

    def __init__(self, fail_calls: int = 1, error: Exception = None):
        self.fail_calls = fail_calls
        self.calls = 0
        self.counters_seen = []
        self.error = error or httpx.ReadTimeout("simulated stall")

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        self.counters_seen.append(network_utils.network_breaker._state_storage.counter)
        if self.calls <= self.fail_calls:
            raise self.error
        return httpx.Response(200, json={"ok": True}, request=request)


def _client(transport: httpx.AsyncBaseTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ResilientAsyncTransport(transport))


# --- 1. the dependency: no tornado on the hot path ------------------------


class TestNoTornadoOnTheHotPath:
    def test_the_module_never_calls_call_async(self):
        """Structural: ``call_async`` is the tornado door — it stays shut.

        Asserted on the AST, not on the text: the repair's own comments name
        ``call_async`` to explain why it is gone, and a text search would
        count the explanation as the defect.
        """
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        offenders = [
            (node.lineno, ast.unparse(node))
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "call_async"
        ]
        assert offenders == [], f"call_async is back on the hot path: {offenders}"

    async def test_the_transport_answers_with_pybreaker_gen_none(self, monkeypatch):
        """``pybreaker.gen is None`` is the no-tornado state; the transport lives.

        The control below proves the simulation bites: under the same patch
        ``call_async`` — the pre-repair path — cannot even build its wrapper.
        """
        monkeypatch.setattr(pybreaker, "gen", None)
        monkeypatch.setattr(pybreaker, "HAS_TORNADO_SUPPORT", False)
        _fresh_breaker(monkeypatch)

        with pytest.raises((AttributeError, TypeError)):
            pybreaker.CircuitBreaker().call_async(lambda: None)

        base = _CountingTransport(fail_calls=0)
        async with _client(base) as client:
            response = await client.post(
                "https://example.test/v1/chat/completions", json={"model": "x"}
            )
        assert response.status_code == 200
        assert base.calls == 1


# --- 2. the lock: not held while the request is in flight ------------------


class TestTheLockIsFreeWhileTheRequestIsInFlight:
    async def test_another_thread_can_take_the_lock_during_the_request(
        self, monkeypatch
    ):
        """The repair's second property, measured from inside the call.

        With ``call_async`` the calling thread holds the ``RLock`` across the
        ``await``; another thread waits for it and times out. Here the probe
        thread must acquire it immediately while the "network" is still
        pending — an ``RLock`` re-entry test from the same thread would not
        witness anything, so the probe runs in its own thread.
        """
        _fresh_breaker(monkeypatch)
        observed = []

        class _SlowTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request):
                box = {}

                def probe() -> None:
                    got = network_utils.network_breaker._lock.acquire(timeout=0.3)
                    box["acquired"] = got
                    if got:
                        network_utils.network_breaker._lock.release()

                thread = threading.Thread(target=probe)
                thread.start()
                await asyncio.sleep(0.5)  # the request is in flight here
                thread.join()
                observed.append(box.get("acquired"))
                return httpx.Response(200, json={"ok": True}, request=request)

        async with _client(_SlowTransport()) as client:
            response = await client.post(
                "https://example.test/v1/chat/completions", json={"model": "x"}
            )
        assert response.status_code == 200
        assert observed == [True], "the breaker lock was held during the request"


# --- 3. the #3440 probes must still hold ----------------------------------


class TestTheBreakerStillDoesItsJob:
    async def test_a_stalled_attempt_is_replayed_and_counted(self, monkeypatch):
        """One stall, then the retry answers — and the stall was counted.

        The counter read inside the second call is the measurement: 1 means
        the failure reached the breaker before the success reset it.
        """
        breaker = _fresh_breaker(monkeypatch, fail_max=3)
        base = _CountingTransport(fail_calls=1)
        async with _client(base) as client:
            response = await client.post(
                "https://example.test/v1/chat/completions", json={"model": "x"}
            )
        assert base.calls == 2, "the retry did not reach the wire"
        assert base.counters_seen == [0, 1], "the failure was not counted"
        assert response.status_code == 200
        assert breaker.current_state == "closed"
        assert breaker._state_storage.counter == 0

    async def test_a_trip_opens_the_breaker_and_the_next_call_stays_off_the_wire(
        self, monkeypatch
    ):
        """``fail_max`` is still the trip point, and an open breaker refuses."""
        breaker = _fresh_breaker(monkeypatch, fail_max=1, reset_timeout=60.0)
        base = _CountingTransport(fail_calls=99)

        with pytest.raises(pybreaker.CircuitBreakerError):
            async with _client(base) as client:
                await client.post(
                    "https://example.test/v1/chat/completions", json={"model": "x"}
                )
        assert breaker.current_state == "open"
        calls_at_trip = base.calls

        with pytest.raises(pybreaker.CircuitBreakerError):
            async with _client(base) as client:
                await client.post(
                    "https://example.test/v1/chat/completions", json={"model": "x"}
                )
        assert base.calls == calls_at_trip, "an open breaker let the call through"

    async def test_the_half_open_trial_closes_the_breaker(self, monkeypatch):
        """After ``reset_timeout``, one call is allowed through and closes it."""
        breaker = _fresh_breaker(monkeypatch, fail_max=1, reset_timeout=0.05)
        base = _CountingTransport(fail_calls=1)

        with pytest.raises(pybreaker.CircuitBreakerError):
            async with _client(base) as client:
                await client.post(
                    "https://example.test/v1/chat/completions", json={"model": "x"}
                )
        assert breaker.current_state == "open"

        await asyncio.sleep(0.1)  # past reset_timeout
        async with _client(base) as client:
            response = await client.post(
                "https://example.test/v1/chat/completions", json={"model": "x"}
            )
        assert response.status_code == 200
        assert breaker.current_state == "closed"
        assert base.calls == 2

    def test_the_pybreaker_primitives_the_repair_relies_on_still_exist(self):
        """A pybreaker bump must redden here, not in production.

        The repair reads three private names (``_handle_error``,
        ``_handle_success``, ``_state_storage.opened_at``). If a version
        drops one, every request would raise ``AttributeError``; this test
        turns that into a design decision at upgrade time.
        """
        for state in (
            pybreaker.CircuitClosedState,
            pybreaker.CircuitHalfOpenState,
            pybreaker.CircuitOpenState,
        ):
            assert callable(getattr(state, "_handle_error", None)), state.__name__
            assert callable(getattr(state, "_handle_success", None)), state.__name__

        breaker = pybreaker.CircuitBreaker(fail_max=1, reset_timeout=0.05)
        assert hasattr(breaker, "_lock")
        assert hasattr(breaker._state_storage, "opened_at")
        assert hasattr(breaker, "reset_timeout")

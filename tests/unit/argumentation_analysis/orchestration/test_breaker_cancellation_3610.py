"""#3610 — a phase-budget cancellation is not a breaker failure.

The phase executor enforces its budget by cancelling the task, and every
LLM call still in flight then receives ``asyncio.CancelledError`` inside
``_call_through_breaker``. The pre-fix helper handed every
``BaseException`` to pybreaker's ``_handle_error``, which counts it as a
service failure: five cancelled calls opened the process-wide
``network_breaker`` (``fail_max=5``, ``reset_timeout=60``), and the phases
that came next were refused with ``CircuitBreakerError`` — reported by the
OpenAI SDK as ``Connection error.`` although nothing had gone wrong on the
wire (panel cycle c16, doc_E).

The witnesses below are the issue's, run against the real module breaker:

1. seven in-flight calls cancelled by an enclosing ``wait_for`` (the way
   the phase budget does it) leave the breaker ``closed`` with its counter
   untouched, and the next call goes through;
2. the positive control: five genuine transport failures
   (``httpx.ConnectError``) still open the breaker — the fix does not
   blind it;
3. a cancellation neither increments nor resets a counter built by real
   failures (``exclude=`` would reset it: in pybreaker 1.4.1 an excluded
   exception is handled as a success).

Born red on ``main`` ``458f798ac``: witness 1 saw the breaker ``open``
with a counter of 7 and the next call refused.
"""

import asyncio

import httpx
import pybreaker
import pytest

import argumentation_analysis.core.utils.network_utils as network_utils
from argumentation_analysis.core.utils.network_utils import _call_through_breaker


@pytest.fixture(autouse=True)
def _reset_the_module_breaker():
    """Hand each test the shared breaker closed, with its counters at zero.

    ``close()`` alone is not enough: in pybreaker 1.4.1 it resets the
    SUCCESS counter only — the failure counter survives it. It is reset
    explicitly here, before and after each test, so no state leaks to other
    tests (the #3447 file swaps in its own breaker; these witnesses measure
    the module-global one, the one the process shares).
    """
    network_utils.network_breaker.close()
    network_utils.network_breaker._state_storage.reset_counter()
    yield
    network_utils.network_breaker.close()
    network_utils.network_breaker._state_storage.reset_counter()


async def _slow_call():
    """An LLM call in flight: it never answers in time."""
    await asyncio.sleep(30)
    return "never"


async def _failing_call():
    """A genuine transport failure: what the wire reports."""
    raise httpx.ConnectError("simulated transport failure")


async def _fast_call():
    return "ok"


class TestCancellationIsNotAFailure:
    async def test_seven_cancelled_calls_leave_the_breaker_closed(self):
        """Witness 1: a budget cancellation is the caller withdrawing.

        Seven concurrent calls through ``_call_through_breaker`` are
        cancelled the way the phase budget does it — by an enclosing
        ``wait_for`` timeout. None of that is evidence about the service,
        so the breaker must stay closed with its counter untouched, and
        the next, unrelated call must go through. The boundary also accepts
        ``CircuitBreakerError`` because on the unfixed code the trip
        surfaces exactly there; on the fixed code only the TimeoutError
        can occur.
        """
        assert network_utils.network_breaker.current_state == "closed"

        async def phase():
            await asyncio.gather(*(_call_through_breaker(_slow_call) for _ in range(7)))

        with pytest.raises(
            (asyncio.TimeoutError, TimeoutError, pybreaker.CircuitBreakerError)
        ):
            await asyncio.wait_for(phase(), timeout=0.2)
        await asyncio.sleep(0.05)  # let the cancelled handlers run

        assert network_utils.network_breaker.current_state == "closed"
        assert network_utils.network_breaker.fail_counter == 0
        assert await _call_through_breaker(_fast_call) == "ok"


class TestRealFailuresStillOpenTheBreaker:
    async def test_five_transport_failures_open_the_breaker(self):
        """Witness 2 (positive control): the fix does not blind the breaker.

        Five genuine transport failures (``fail_max`` is 5) must still trip
        it: the fifth raises ``CircuitBreakerError`` on the trip, the state
        becomes ``open``, and the next call is refused before it leaves the
        machine.
        """
        assert network_utils.network_breaker.fail_max == 5

        for _ in range(4):
            with pytest.raises(httpx.ConnectError):
                await _call_through_breaker(_failing_call)
        with pytest.raises(pybreaker.CircuitBreakerError):
            await _call_through_breaker(_failing_call)
        assert network_utils.network_breaker.current_state == "open"

        with pytest.raises(pybreaker.CircuitBreakerError):
            await _call_through_breaker(_fast_call)


class TestCancellationIsNotASuccessEither:
    async def test_a_cancellation_does_not_reset_a_counter_of_real_failures(self):
        """Witness 3: a cancellation is not evidence of health either.

        Three genuine failures build the counter to 3. A cancelled call
        afterwards must leave that counter exactly where it is: not 4
        (counted as a failure — the pre-fix defect) and not 0 (handled as a
        success — what pybreaker's ``exclude=`` would do in 1.4.1).
        """
        for _ in range(3):
            with pytest.raises(httpx.ConnectError):
                await _call_through_breaker(_failing_call)
        assert network_utils.network_breaker.fail_counter == 3

        with pytest.raises(
            (asyncio.TimeoutError, TimeoutError, pybreaker.CircuitBreakerError)
        ):
            await asyncio.wait_for(_call_through_breaker(_slow_call), timeout=0.2)
        await asyncio.sleep(0.05)  # let the cancelled handler run

        assert network_utils.network_breaker.current_state == "closed"
        assert network_utils.network_breaker.fail_counter == 3

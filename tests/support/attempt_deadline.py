"""The attempt deadline the transport really applies (#3435, #3658 46f / 46h).

The same measurement serves two witnesses: 46f's (the acts' ceiling) and 46h's
(the population of completion caps). It is read on the PRODUCTION seam — the
phase budget is published the way ``workflow_dsl`` publishes it, and
``PhaseBudgetTransport`` rewrites the request's timeout — so no witness re-runs
``compose_attempt_deadline``'s arithmetic by hand, and a change to the
composition moves every witness with it.

``budget=None`` is the "no phase budget published" case, which is what a phase
declaring no ``timeout_seconds`` produces: the transport passes the request
unchanged and the client's ``default_timeout`` is the deadline.

Seat free: one in-process transport double, zero network, zero key.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Tuple

import httpx

from argumentation_analysis.config.settings import settings
from argumentation_analysis.core.utils.network_utils import (
    PhaseBudgetTransport,
    phase_attempt_budget,
    phase_transport_observer,
)

#: c22's measured throughput, taken at the LOW end of the 205-215 tok/s range:
#: the slow end is the one that binds a deadline (8 192 tokens in 38-40 s).
RATE_TOKENS_PER_SECOND = 205.0
#: 46b's own allowance for prompt handling and the first token, per call.
PROMPT_ALLOWANCE_SECONDS = 12.0


class _RecordingTransport(httpx.AsyncBaseTransport):
    """Records the request ``PhaseBudgetTransport`` passes down."""

    def __init__(self) -> None:
        self.requests: list = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, content=b"{}")


def _read_deadline(extension: Any) -> float:
    """The read timeout a request carries, whatever shape it is in.

    httpcore wants a MAPPING (#3450), and the client may hand a
    ``httpx.Timeout``; both say the same thing for our one number.
    """
    if isinstance(extension, dict):
        value = extension.get("read")
    else:
        value = getattr(extension, "read", None)
    return float(value)


async def deadline_the_transport_applies(
    budget: Optional[float],
) -> Tuple[Optional[float], float]:
    """``(deadline the transport recorded, read timeout written to the wire)``.

    ``budget=None`` publishes nothing, exactly as a phase with no
    ``timeout_seconds`` does; the recorded deadline is then ``None`` and the
    wire keeps the client's own timeout.
    """
    observer: dict = {}
    inner = _RecordingTransport()
    transport = PhaseBudgetTransport(inner)
    token_observer = phase_transport_observer.set(observer)
    token_budget = phase_attempt_budget.set(
        None if budget is None else float(budget)
    )
    try:
        await transport.handle_async_request(
            httpx.Request(
                "POST",
                "https://example.invalid/v1/chat/completions",
                extensions={
                    "timeout": httpx.Timeout(settings.network.default_timeout)
                },
            )
        )
    finally:
        phase_transport_observer.reset(token_observer)
        phase_attempt_budget.reset(token_budget)
    recorded = observer.get("attempt_deadline")
    return (
        None if recorded is None else float(recorded),
        _read_deadline(inner.requests[-1].extensions["timeout"]),
    )


def effective_deadline(budget: Optional[float]) -> float:
    """The deadline a call in a phase with ``budget`` really has, in seconds.

    A phase that declares no budget (``None``) is bounded by the client's
    ``default_timeout``, which is what the transport leaves on the wire.
    """
    recorded, applied = asyncio.run(deadline_the_transport_applies(budget))
    if recorded is not None and recorded != applied:
        raise AssertionError(
            "the deadline the transport recorded and the one it wrote disagree: "
            f"{recorded} vs {applied}"
        )
    return applied

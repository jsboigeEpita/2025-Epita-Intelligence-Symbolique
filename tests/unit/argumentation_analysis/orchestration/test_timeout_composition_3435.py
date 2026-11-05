"""#3435 — the phase budget and the client's own retry must compose.

Measured on the cycle-2 panel: ``act1_framing`` completes in 13.3–38.6 s on
the 8 healthy documents, but on one document a single call stalled and the
phase budget (180 s) killed the act with NO retry. The arithmetic of the
defect: ``default_timeout`` = 90 s per request, tenacity retries 3 times
with 2–10 s backoff, so ONE hung attempt followed by ONE retry needs at
least 90 + 2 + 90 = 182 s — more than the 180 s budget. The retry the
client promises can never complete inside the phase that pays for it.

The repair composes the deadlines (the rule lives in ONE place,
``network_utils.compose_attempt_deadline``): when the executor publishes a
phase budget, each transport attempt is clamped so that at least one retry
fits. At the production budget: (180 − 10 − 10) / 2 = 80 s per attempt —
two attempts plus the worst backoff take 170 s ≤ 180 s, and 80 s is still
2× the worst measured healthy duration, so a healthy run never feels the
clamp. The clamp never RAISES a timeout; a phase without a budget keeps
today's behaviour byte-for-byte.

Born red on ``c6e25c2e1``: none of ``compose_attempt_deadline``,
``PhaseBudgetTransport``, ``phase_attempt_budget`` exists — the import
fails. The production-geometry arithmetic (182 > 180 vs 170 ≤ 180) is pure
constants and is asserted below as the rule's own test.
"""

import asyncio
import ast
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import httpx
import pytest

from argumentation_analysis.config.settings import settings
from argumentation_analysis.core.utils.network_utils import (
    PHASE_ATTEMPT_FLOOR_SECONDS,
    PHASE_COMPOSITION_MARGIN_SECONDS,
    PhaseBudgetTransport,
    ResilientAsyncTransport,
    compose_attempt_deadline,
    get_resilient_async_client,
    phase_attempt_budget,
    phase_transport_observer,
)

# The issue's measured numbers — the calibration basis of the rule.
WORST_HEALTHY_ACT_SECONDS = 38.6
PRODUCTION_BUDGET_SECONDS = 180.0
PRODUCTION_DEFAULT_TIMEOUT = 90.0


# --- the rule ------------------------------------------------------------


class TestTheRule:
    def test_the_production_budget_admits_a_retry(self):
        """2 × deadline + worst backoff + margin ≤ budget, at every production budget."""
        worst_wait = float(settings.network.retry_wait_max)
        for budget in (120.0, 180.0, 420.0, 600.0):
            deadline = compose_attempt_deadline(budget)
            assert (
                2 * deadline + worst_wait + PHASE_COMPOSITION_MARGIN_SECONDS <= budget
            ), f"budget {budget}: two attempts + backoff do not fit"

    def test_the_180s_budget_clamps_below_the_client_default(self):
        """The defect's arithmetic, repaired: 90 + 2 + 90 = 182 > 180 must not stand.

        At the production budget the clamp BINDS — the composed deadline
        (80 s) is strictly below the configured per-request default (90 s).
        This is the one-line statement of the measured defect: without the
        clamp, one hung attempt plus one retry cannot fit the budget.
        """
        deadline = compose_attempt_deadline(PRODUCTION_BUDGET_SECONDS)
        assert deadline < settings.network.default_timeout
        assert deadline == pytest.approx(80.0)

    def test_a_healthy_act_never_feels_the_clamp(self):
        """80 s is ≥ 2× the worst measured healthy duration (38.6 s)."""
        deadline = compose_attempt_deadline(PRODUCTION_BUDGET_SECONDS)
        assert deadline >= 2 * WORST_HEALTHY_ACT_SECONDS

    def test_the_clamp_never_raises_a_timeout(self):
        """A generous budget keeps the configured default — min(), never more."""
        assert compose_attempt_deadline(600.0) == settings.network.default_timeout

    def test_a_small_budget_floors_at_a_viable_attempt(self):
        """The floor exists for test-scale budgets; production never binds it."""
        assert compose_attempt_deadline(6.0) == PHASE_ATTEMPT_FLOOR_SECONDS


# --- the transport ---------------------------------------------------------


class _StallingBaseTransport(httpx.AsyncBaseTransport):
    """A base transport that HONOURS the per-attempt deadline it is given.

    Reads ``request.extensions["timeout"]`` exactly as httpcore does (the
    mechanism the clamp relies on), sleeps past it, then raises the
    exception a genuinely hung request raises (``httpx.ReadTimeout``, a
    ``httpx.RequestError`` subclass — retryable by tenacity). Calls after
    ``stall_calls`` answer immediately: the shape the issue names — « a
    fake LLM that stalls on its first call and answers on its second ».
    """

    def __init__(self, stall_calls: int = 1):
        self.stall_calls = stall_calls
        self.calls = 0
        self.seen_deadlines = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        timeout_value = request.extensions.get("timeout")
        read_deadline = getattr(timeout_value, "read", None)
        if read_deadline is None and timeout_value is not None:
            read_deadline = timeout_value.get("read")
        self.seen_deadlines.append(read_deadline)
        if self.calls <= self.stall_calls:
            await asyncio.sleep(read_deadline + 0.3)
            raise httpx.ReadTimeout(
                f"simulated hang past the {read_deadline}s attempt deadline"
            )
        return httpx.Response(200, json={"ok": True}, request=request)


def _witness_client(stall_calls: int) -> httpx.AsyncClient:
    """The production retry layer over the clamped transport over the fake."""
    return httpx.AsyncClient(
        transport=ResilientAsyncTransport(
            PhaseBudgetTransport(_StallingBaseTransport(stall_calls))
        ),
        timeout=settings.network.default_timeout,
    )


class TestTheTransport:
    async def test_a_stalled_attempt_gets_its_retry_inside_the_budget(self):
        """THE witness: stall once, answer on the retry — inside the budget.

        Budget 6 s → deadline 1.5 s: attempt 1 fires at ~1.8 s, tenacity
        waits ~2 s, attempt 2 answers. The wall stays under the budget, the
        response is obtained, and the observer says 2 attempts.
        """
        observer: Dict[str, Any] = {"attempts": 0}
        budget_token = phase_attempt_budget.set(6.0)
        observer_token = phase_transport_observer.set(observer)
        client = _witness_client(stall_calls=1)
        try:
            t0 = time.perf_counter()
            response = await client.post("http://llm.test/v1/chat/completions")
            wall = time.perf_counter() - t0
        finally:
            phase_attempt_budget.reset(budget_token)
            phase_transport_observer.reset(observer_token)
            await client.aclose()
        assert response.status_code == 200
        assert wall < 6.0, f"the retry must land inside the budget (wall {wall:.2f}s)"
        # The transport's REAL call counter, not the observer's bookkeeping:
        # the base transport was entered twice — the retry happened.
        base = client._transport.transport.transport
        assert base.calls == 2
        assert observer["attempts"] == 2
        assert observer["attempt_deadline"] == pytest.approx(1.5)

    async def test_the_deadline_the_transport_hands_down_is_the_composed_one(self):
        """The clamp is what the base transport sees: 1.5 s, not the 90 s default."""
        observer: Dict[str, Any] = {"attempts": 0}
        budget_token = phase_attempt_budget.set(6.0)
        observer_token = phase_transport_observer.set(observer)
        client = _witness_client(stall_calls=1)
        try:
            await client.post("http://llm.test/v1/chat/completions")
        finally:
            phase_attempt_budget.reset(budget_token)
            phase_transport_observer.reset(observer_token)
            await client.aclose()
        seen = getattr(client._transport.transport.transport, "seen_deadlines")
        assert seen[0] == pytest.approx(1.5)

    async def test_no_budget_keeps_todays_deadline_byte_for_byte(self):
        """Without a published budget the request passes through untouched."""
        client = _witness_client(stall_calls=0)
        try:
            response = await client.post("http://llm.test/v1/chat/completions")
        finally:
            await client.aclose()
        assert response.status_code == 200
        base = client._transport.transport.transport
        assert base.calls == 1
        # The client's own default flows through the clamp unchanged.
        assert base.seen_deadlines[0] == pytest.approx(settings.network.default_timeout)

    def test_the_production_chain_wires_the_clamp_under_the_retry_layer(self):
        """get_resilient_async_client: retry OUTSIDE, clamp INSIDE — per attempt."""
        client = get_resilient_async_client()
        chain = []
        node: Any = client._transport
        while node is not None:
            chain.append(type(node).__name__)
            node = getattr(node, "transport", None) or getattr(
                node, "_wrapped_transport", None
            )
        # The clamp sits strictly between the retry layer and the base.
        assert "ResilientAsyncTransport" in chain
        assert "PhaseBudgetTransport" in chain
        assert chain.index("ResilientAsyncTransport") < chain.index(
            "PhaseBudgetTransport"
        )
        assert chain[-1] == "AsyncHTTPTransport"


# --- the executor ----------------------------------------------------------


class _Provider:
    """A phase provider whose invoke goes through the real transport chain."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def invoke(self, phase_input: Any, ctx: Dict[str, Any]) -> Any:
        return await self._client.post("http://llm.test/v1/chat/completions")


def _executor() -> Any:
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor

    return WorkflowExecutor(registry=SimpleNamespace())


def _budgeted_phase() -> Any:
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowPhase

    return WorkflowPhase(
        name="act1_framing",
        capability="act1_framing",
        timeout_seconds=6.0,
    )


class TestTheExecutor:
    async def test_the_act_is_produced_when_a_call_stalls_once(self):
        """The promise: the executor's wait_for no longer eats the retry."""
        client = _witness_client(stall_calls=1)
        executor = _executor()
        phase = _budgeted_phase()
        t0 = time.perf_counter()
        output, attempts = await executor._invoke_with_retry(
            phase, _Provider(client), None, {}
        )
        wall = time.perf_counter() - t0
        await client.aclose()
        assert output.status_code == 200
        assert attempts == 1  # the EXECUTOR attempted once; the retry was the client's
        assert wall < 6.0

    async def test_the_lost_act_names_its_cause(self):
        """When the act is lost anyway, the error says what it observed."""
        from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor

        client = _witness_client(stall_calls=99)  # always stalls
        executor = _executor()
        phase = _budgeted_phase()
        with pytest.raises(asyncio.TimeoutError) as excinfo:
            await executor._invoke_with_retry(phase, _Provider(client), None, {})
        await client.aclose()
        exc = excinfo.value
        assert getattr(exc, "llm_attempts", None) == 2
        assert getattr(exc, "attempt_deadline", None) == pytest.approx(1.5)
        message = WorkflowExecutor._build_phase_error_message(exc, "act1_framing", 6.0)
        assert "exceeded its 6.0s budget" in message
        assert "after 2 transport attempt(s)" in message
        assert "clamped to 1.5s" in message

    async def test_the_published_budget_does_not_leak_to_the_next_phase(self):
        """The contextvar resets: an unbudgeted phase after a budgeted one is unclamped."""
        from argumentation_analysis.orchestration.workflow_dsl import WorkflowPhase

        client = _witness_client(stall_calls=0)
        executor = _executor()
        budgeted = WorkflowPhase(
            name="act1_framing", capability="act1_framing", timeout_seconds=6.0
        )
        unbudgeted = WorkflowPhase(name="after", capability="act1_framing")
        await executor._invoke_with_retry(budgeted, _Provider(client), None, {})
        output, _ = await executor._invoke_with_retry(
            unbudgeted, _Provider(client), None, {}
        )
        await client.aclose()
        assert output.status_code == 200
        base = client._transport.transport.transport
        # The second call ran with NO clamp: the client default, not 1.5 s.
        assert base.seen_deadlines[-1] == pytest.approx(
            settings.network.default_timeout
        )


# --- the census -------------------------------------------------------------


def _decorator_name(dec: Any) -> str:
    """`network_breaker`, `mod.network_breaker(...)` — all spell one name."""
    node = dec
    while isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


class TestTheCensus:
    def test_no_network_breaker_decorator_on_an_async_def_anywhere(self):
        """AST census guard (#3435 review ask).

        pybreaker's decorator wraps an ``async def`` into a SYNC callable,
        which hides the coroutine from tenacity's async detection — that
        stacking was the inert retry. The breaker must be driven via its
        ``call_async`` API INSIDE a tenacity-decorated method, never stacked
        as a decorator on an ``async def``. This walks the package's AST —
        no import — so it sees every file, loaded or not.

        Born red on ``origin/main``: the offender was
        ``network_utils.ResilientAsyncTransport.handle_async_request``
        (``@async_retry_on_network_error`` over ``@network_breaker`` on an
        ``async def``) — the exact site this PR repairs. The five SYNC
        stacking sites (``download_file`` + four ``fetch_service``
        functions) are legitimate: the sync wrapper does not hide a
        coroutine from sync tenacity.
        """
        import argumentation_analysis

        package_root = Path(argumentation_analysis.__file__).resolve().parent
        offenders = []
        for path in sorted(package_root.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) and any(
                    _decorator_name(d) == "network_breaker" for d in node.decorator_list
                ):
                    offenders.append(f"{path.relative_to(package_root)}:{node.lineno}")
        assert offenders == [], (
            "pybreaker stacked as a decorator on an async def (the inert-retry "
            f"shape) at: {offenders} — drive it with call_async inside a "
            "tenacity-decorated method instead"
        )

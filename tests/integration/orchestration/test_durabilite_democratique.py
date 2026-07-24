"""DT-1 #1499 anti-theater tests for the Democratech critical path.

These tests verify three guarantees from the DT-1 spec:
1. Retry/backoff actually retries on transient exceptions and surfaces
   ``attempts`` on the result (anti-theater: no silent retry on logic bugs).
2. Optional phases that exhaust their retry budget surface ``degraded=True``
   with status=FAILED, NOT a silent COMPLÉTÉE pass.
3. The FastAPI error surface returns a typed envelope (error_code, detail,
   degraded, context) instead of opaque HTTP 500 strings.

Privacy: all synthetic. No corpus, no LLM key required.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    RetryConfig,
    WorkflowExecutor,
    WorkflowPhase,
)


# ---------------------------------------------------------------------------
# Fake capability provider — first ``fail_count`` calls raise transient,
# then succeed. Used to assert retry actually retries.
# ---------------------------------------------------------------------------


class _TransientProvider:
    """Provider whose .invoke raises ConnectionError N times, then returns."""

    def __init__(self, name: str, output: Any, fail_count: int) -> None:
        self.name = name
        self._output = output
        self._remaining_failures = fail_count
        self.call_count = 0

    async def invoke(self, _input_data: Any, _ctx: Dict[str, Any]) -> Any:
        self.call_count += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise ConnectionError(f"simulated transient #{self.call_count}")
        return self._output


class _LogicBugProvider:
    """Provider whose .invoke always raises a non-retryable error."""

    name = "logic_bug"  # WorkflowPhase references provider.name on failure

    async def invoke(self, _input_data: Any, _ctx: Dict[str, Any]) -> Any:
        raise ValueError("logic bug — not transient")


# Minimal in-memory registry surface so WorkflowExecutor can resolve
# capabilities without booting the real CapabilityRegistry.


class _FakeRegistry:
    def __init__(self, providers_by_cap: Dict[str, List[Any]]) -> None:
        self._providers_by_cap = providers_by_cap

    def find_for_capability(self, capability: str) -> List[Any]:
        return list(self._providers_by_cap.get(capability, []))


def _make_executor(providers_by_cap: Dict[str, List[Any]]) -> WorkflowExecutor:
    return WorkflowExecutor(registry=_FakeRegistry(providers_by_cap))


# ---------------------------------------------------------------------------
# 1. Retry actually retries, and reports attempts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_succeeds_after_two_transient_failures() -> None:
    provider = _TransientProvider(
        name="counter", output={"counter": "ok"}, fail_count=2
    )
    phase = WorkflowPhase(
        name="counter",
        capability="counter_argument",
        optional=True,
        retry_config=RetryConfig(
            max_attempts=4, initial_delay_seconds=0.0, backoff_factor=1.0
        ),
    )
    executor = _make_executor({"counter_argument": [provider]})
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowDefinition

    wf_def = WorkflowDefinition(name="test_retry", phases=[phase])
    results = await executor.execute(wf_def, input_data="hello")

    res = results["counter"]
    assert res.status == PhaseStatus.COMPLETED
    assert res.attempts == 3, f"expected 3 attempts, got {res.attempts}"
    assert provider.call_count == 3
    assert res.output == {"counter": "ok"}
    assert res.degraded is False  # succeeded cleanly


@pytest.mark.asyncio
async def test_no_silent_retry_on_logic_bug() -> None:
    """Anti-theater #1019: ValueError must NOT be retried."""
    provider = _LogicBugProvider()
    phase = WorkflowPhase(
        name="quality",
        capability="argument_quality",
        optional=False,
        retry_config=RetryConfig(
            max_attempts=5, initial_delay_seconds=0.0
        ),
    )
    executor = _make_executor({"argument_quality": [provider]})
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowDefinition

    wf_def = WorkflowDefinition(name="test_no_retry_bug", phases=[phase])
    results = await executor.execute(wf_def, input_data="hello")

    res = results["quality"]
    assert res.status == PhaseStatus.FAILED
    assert res.degraded is False  # non-optional => loud FAILED, not degraded
    assert res.attempts == 1  # no retry on non-retryable exception
    assert "logic bug" in (res.error or "")


# ---------------------------------------------------------------------------
# 2. Optional phase exhaustion surfaces degraded=True loudly
# ---------------------------------------------------------------------------


class _AlwaysTransientProvider:
    name = "transient"

    def __init__(self) -> None:
        self.call_count = 0

    async def invoke(self, _input_data: Any, _ctx: Dict[str, Any]) -> Any:
        self.call_count += 1
        raise ConnectionError(f"always transient #{self.call_count}")


@pytest.mark.asyncio
async def test_optional_phase_exhaustion_surfaces_degraded_loudly() -> None:
    provider = _AlwaysTransientProvider()
    phase = WorkflowPhase(
        name="local_llm",
        capability="local_llm",
        optional=True,
        retry_config=RetryConfig(
            max_attempts=3, initial_delay_seconds=0.0
        ),
    )
    executor = _make_executor({"local_llm": [provider]})
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowDefinition

    wf_def = WorkflowDefinition(
        name="test_degraded", phases=[phase]
    )
    results = await executor.execute(wf_def, input_data="hello")

    res = results["local_llm"]
    # Anti-theater: optional phase that exhausted retry must keep status
    # FAILED (NOT silently flipped to COMPLETED). degraded=True is the
    # signal the consumer reads.
    assert res.status == PhaseStatus.FAILED
    assert res.degraded is True
    assert res.attempts == 3
    assert provider.call_count == 3


# ---------------------------------------------------------------------------
# 3. FastAPI legible error surface
# ---------------------------------------------------------------------------


def test_api_error_envelope_shape() -> None:
    from api.errors import (
        APIError,
        DegradedError,
        UpstreamError,
        ValidationError,
        TimeoutError_,
    )

    # Each subclass produces the documented envelope shape.
    for exc, expected_code in [
        (ValidationError("bad payload"), "validation_error"),
        (UpstreamError("LLM down", context={"phase": "extract"}), "upstream_error"),
        (TimeoutError_("over budget"), "timeout_error"),
        (DegradedError("partial", degraded=True), "degraded_result"),
    ]:
        env = exc.to_envelope()
        assert set(env.keys()) == {"error_code", "detail", "degraded", "context"}
        assert env["error_code"] == expected_code
        assert env["detail"]


def test_api_error_status_codes() -> None:
    from api.errors import (
        DegradedError,
        ServiceUnavailableError,
        TimeoutError_,
        UpstreamError,
        ValidationError,
    )

    assert ValidationError("x").status_code == 400
    assert UpstreamError("x").status_code == 502
    assert TimeoutError_("x").status_code == 504
    assert ServiceUnavailableError("x").status_code == 503
    assert DegradedError("x").status_code == 200


def test_api_error_handler_registers_on_app() -> None:
    """The handler must be wired so FastAPI translates APIError to JSON."""
    from fastapi import FastAPI
    from api.errors import APIError, install_error_handlers

    app = FastAPI()
    install_error_handlers(app)
    # The handler dict holds an entry per registered exception class.
    handler_dict = app.exception_handlers
    assert APIError in handler_dict, (
        "install_error_handlers did not register the APIError handler"
    )
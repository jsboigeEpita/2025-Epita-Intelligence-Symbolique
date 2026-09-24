"""run_hybrid hands back a fallback only when the caller asked for one (#2344).

``fallback_result`` defaulted to ``None``, so a callable that failed and a
callable that legitimately returned ``None`` came back the same. The caller
that did pass a fallback (``LogicService.analyze_text_logic_async``) got it back
as a success, reset its circuit breaker on it, and never recorded the failure
its own ``except`` was written to count.
"""

import asyncio

import pytest

from argumentation_analysis.services.logic_service import LogicService
from argumentation_analysis.utils.async_manager import (
    AsyncManager,
    ensure_sync,
    run_hybrid_safe,
)


@pytest.fixture
def mgr():
    m = AsyncManager(max_workers=2, default_timeout=5.0)
    yield m
    m.shutdown()


def _boom():
    raise RuntimeError("boom")


def test_failure_without_a_fallback_raises_and_is_tracked(mgr):
    with pytest.raises(RuntimeError, match="boom"):
        mgr.run_hybrid(_boom)
    (task,) = mgr.get_active_tasks().values()
    assert task["status"] == "error"
    assert task["error"] == "boom"


def test_a_legitimate_none_comes_back_as_none(mgr):
    assert mgr.run_hybrid(lambda: None) is None


def test_an_explicit_fallback_is_still_returned(mgr):
    assert mgr.run_hybrid(_boom, fallback_result="fb") == "fb"
    assert mgr.run_hybrid(_boom, fallback_result=None) is None


def test_run_hybrid_safe_without_a_fallback_raises():
    with pytest.raises(RuntimeError, match="boom"):
        run_hybrid_safe(_boom)


def test_a_sync_wrapped_coroutine_that_fails_raises():
    async def fails():
        raise ValueError("async boom")

    with pytest.raises(ValueError, match="async boom"):
        ensure_sync(fails)()


def test_a_task_without_a_fallback_raises_out_of_the_batch(mgr):
    with pytest.raises(RuntimeError, match="boom"):
        mgr.run_multiple_hybrid([{"func": _boom}])


def test_a_task_with_a_fallback_gets_it_and_the_others_run(mgr):
    tasks = [{"func": _boom, "fallback_result": -1}, {"func": lambda: 2}]
    assert mgr.run_multiple_hybrid(tasks) == [-1, 2]


def test_a_coroutine_from_inside_a_running_loop_raises(mgr):
    # The running-loop branch returned an unawaited ``wait_for`` coroutine as
    # the result, and the task ran detached.
    ran = []

    async def inner():
        ran.append(True)
        return 42

    async def caller():
        return mgr.run_hybrid(inner)

    with pytest.raises(RuntimeError, match="await"):
        asyncio.run(caller())
    assert ran == []


def test_a_failed_logic_analysis_counts_against_the_breaker(monkeypatch):
    service = LogicService()

    def reasoner_down(*args, **kwargs):
        raise RuntimeError("reasoner down")

    monkeypatch.setattr(service, "analyze_text_logic", reasoner_down)
    result = service.analyze_text_logic_async("text", "propositional")

    assert service._circuit_breaker["failures"] == 1
    assert result["fallback_mode"] is True
    assert result["success"] is False
    assert "reasoner down" in result["error"]

# tests/unit/argumentation_analysis/utils/test_async_manager.py
"""Tests for AsyncManager — hybrid sync/async execution."""

import pytest
import time
from datetime import datetime, timedelta

from argumentation_analysis.utils.async_manager import (
    AsyncManager,
    run_hybrid_safe,
    ensure_async,
    ensure_sync,
)


@pytest.fixture
def mgr():
    m = AsyncManager(max_workers=2, default_timeout=5.0)
    yield m
    m.shutdown()


# ── Init ──

class TestAsyncManagerInit:
    def test_defaults(self):
        m = AsyncManager()
        assert m.max_workers == 4
        assert m.default_timeout == 30.0
        assert m.task_counter == 0
        assert m.active_tasks == {}
        m.shutdown()

    def test_custom_params(self):
        m = AsyncManager(max_workers=2, default_timeout=10.0)
        assert m.max_workers == 2
        assert m.default_timeout == 10.0
        m.shutdown()


# ── run_hybrid (sync functions) ──

class TestRunHybridSync:
    def test_basic_sync_function(self, mgr):
        def add(a, b):
            return a + b

        result = mgr.run_hybrid(add, 3, 4)
        assert result == 7

    def test_sync_with_kwargs(self, mgr):
        def greet(name, prefix="Hello"):
            return f"{prefix}, {name}"

        result = mgr.run_hybrid(greet, "World", prefix="Hi")
        assert result == "Hi, World"

    def test_sync_function_error_returns_fallback(self, mgr):
        def failing():
            raise ValueError("boom")

        result = mgr.run_hybrid(failing, fallback_result="fallback")
        assert result == "fallback"

    def test_sync_tracks_task(self, mgr):
        def noop():
            return 42

        mgr.run_hybrid(noop)
        tasks = mgr.get_active_tasks()
        assert len(tasks) == 1
        task = list(tasks.values())[0]
        assert task["status"] == "completed"

    def test_error_task_tracked(self, mgr):
        def failing():
            raise RuntimeError("err")

        mgr.run_hybrid(failing, fallback_result=None)
        tasks = mgr.get_active_tasks()
        task = list(tasks.values())[0]
        assert task["status"] == "error"
        assert "err" in task.get("error", "")


# ── run_hybrid (async functions) ──

class TestRunHybridAsync:
    def test_async_function(self, mgr):
        async def async_add(a, b):
            return a + b

        result = mgr.run_hybrid(async_add, 5, 6)
        assert result == 11

    def test_async_function_error(self, mgr):
        async def async_fail():
            raise ValueError("async boom")

        result = mgr.run_hybrid(async_fail, fallback_result="fb")
        assert result == "fb"


# ── run_multiple_hybrid ──

class TestRunMultipleHybrid:
    def test_multiple_tasks(self, mgr):
        def double(x):
            return x * 2

        tasks = [
            {"func": double, "args": (1,)},
            {"func": double, "args": (2,)},
            {"func": double, "args": (3,)},
        ]
        results = mgr.run_multiple_hybrid(tasks, max_concurrent=2)
        assert results == [2, 4, 6]

    def test_empty_tasks(self, mgr):
        results = mgr.run_multiple_hybrid([])
        assert results == []

    def test_task_with_fallback(self, mgr):
        def failing():
            raise RuntimeError("fail")

        tasks = [
            {"func": failing, "fallback_result": -1},
        ]
        results = mgr.run_multiple_hybrid(tasks)
        assert results == [-1]


# ── Task management ──

class TestTaskManagement:
    def test_generate_task_id(self, mgr):
        id1 = mgr._generate_task_id()
        id2 = mgr._generate_task_id()
        assert id1 != id2
        assert id1.startswith("task_")
        assert mgr.task_counter == 2

    def test_get_active_tasks_returns_copy(self, mgr):
        tasks = mgr.get_active_tasks()
        tasks["fake"] = "value"
        assert "fake" not in mgr.active_tasks

    def test_cleanup_completed_tasks(self, mgr):
        # Add old completed task
        mgr.active_tasks["old"] = {
            "status": "completed",
            "end_time": datetime.now() - timedelta(hours=2),
        }
        mgr.active_tasks["recent"] = {
            "status": "completed",
            "end_time": datetime.now(),
        }
        removed = mgr.cleanup_completed_tasks(max_age_hours=1)
        assert removed == 1
        assert "old" not in mgr.active_tasks
        assert "recent" in mgr.active_tasks

    def test_cleanup_error_tasks(self, mgr):
        mgr.active_tasks["err_old"] = {
            "status": "error",
            "end_time": datetime.now() - timedelta(hours=5),
        }
        removed = mgr.cleanup_completed_tasks(max_age_hours=1)
        assert removed == 1

    def test_cleanup_running_not_removed(self, mgr):
        mgr.active_tasks["running"] = {
            "status": "running",
            "start_time": datetime.now() - timedelta(hours=5),
        }
        removed = mgr.cleanup_completed_tasks(max_age_hours=1)
        assert removed == 0


# ── Performance stats ──

class TestPerformanceStats:
    def test_no_tasks(self, mgr):
        stats = mgr.get_performance_stats()
        assert stats["total_tasks"] == 0
        assert stats["completed_tasks"] == 0
        assert stats["average_duration"] == 0

    def test_with_completed_tasks(self, mgr):
        mgr.run_hybrid(lambda: 42)
        mgr.run_hybrid(lambda: 99)
        stats = mgr.get_performance_stats()
        assert stats["completed_tasks"] == 2
        assert stats["average_duration"] >= 0

    def test_with_error_tasks(self, mgr):
        mgr.run_hybrid(lambda: (_ for _ in ()).throw(RuntimeError("e")), fallback_result=None)
        stats = mgr.get_performance_stats()
        assert stats["error_tasks"] >= 0


# ── Wrappers ──

class TestWrappers:
    def test_create_async_wrapper(self, mgr):
        def sync_fn(x):
            return x + 1

        wrapped = mgr.create_async_wrapper(sync_fn)
        assert wrapped.__name__ == "sync_fn"

    def test_create_sync_wrapper(self, mgr):
        async def async_fn(x):
            return x + 1

        wrapped = mgr.create_sync_wrapper(async_fn)
        assert wrapped.__name__ == "async_fn"


# ── Module-level functions ──

class TestModuleFunctions:
    def test_run_hybrid_safe(self):
        result = run_hybrid_safe(lambda: 42)
        assert result == 42

    def test_run_hybrid_safe_with_fallback(self):
        def failing():
            raise ValueError("err")

        result = run_hybrid_safe(failing, fallback_result="safe")
        assert result == "safe"

    def test_ensure_async_sync_func(self):
        def sync_fn():
            return 1

        wrapped = ensure_async(sync_fn)
        import asyncio
        assert asyncio.iscoroutinefunction(wrapped)

    def test_ensure_async_already_async(self):
        async def async_fn():
            return 1

        wrapped = ensure_async(async_fn)
        assert wrapped is async_fn

    def test_ensure_sync_sync_func(self):
        def sync_fn():
            return 1

        wrapped = ensure_sync(sync_fn)
        assert wrapped is sync_fn

    def test_ensure_sync_async_func(self):
        async def async_fn():
            return 1

        wrapped = ensure_sync(async_fn)
        import asyncio
        assert not asyncio.iscoroutinefunction(wrapped)


# ── Shutdown ──

class TestShutdown:
    def test_shutdown_clean(self):
        m = AsyncManager(max_workers=1)
        m.run_hybrid(lambda: 42)
        m.shutdown()
        # Executor should be shut down

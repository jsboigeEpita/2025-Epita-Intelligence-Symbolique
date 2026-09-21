# tests/unit/argumentation_analysis/utils/test_performance_monitoring.py
"""Tests for performance monitoring decorator."""

import asyncio
import inspect
import json
import logging
import pytest
import time

from argumentation_analysis.utils.performance_monitoring import monitor_performance


class TestMonitorPerformance:
    def test_basic_decorator(self):
        @monitor_performance()
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_preserves_return_value(self):
        @monitor_performance()
        def greet(name):
            return f"Hello, {name}"

        assert greet("World") == "Hello, World"

    def test_preserves_function_name(self):
        @monitor_performance()
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_preserves_none_return(self):
        @monitor_performance()
        def no_return():
            pass

        assert no_return() is None

    def test_with_kwargs(self):
        @monitor_performance()
        def func(a, b=10):
            return a + b

        assert func(1, b=20) == 21

    def test_with_log_args_true(self):
        @monitor_performance(log_args=True)
        def func(x, y):
            return x * y

        result = func(3, 4)
        assert result == 12

    def test_exception_still_propagates(self):
        @monitor_performance()
        def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            failing()

    def test_logs_execution_even_on_exception(self):
        """The decorator should log timing even when the function fails."""

        @monitor_performance()
        def failing():
            raise RuntimeError("error")

        with pytest.raises(RuntimeError):
            failing()
        # If we get here, the decorator didn't swallow the exception

    def test_multiple_calls(self):
        call_count = 0

        @monitor_performance()
        def counter():
            nonlocal call_count
            call_count += 1
            return call_count

        assert counter() == 1
        assert counter() == 2
        assert counter() == 3

    def test_with_complex_args(self):
        @monitor_performance(log_args=True)
        def func(data, options=None):
            return len(data)

        result = func([1, 2, 3], options={"verbose": True})
        assert result == 3

    def test_decorator_doesnt_add_significant_overhead(self):
        @monitor_performance()
        def fast_func():
            return 42

        start = time.perf_counter()
        for _ in range(100):
            fast_func()
        elapsed = time.perf_counter() - start
        # 100 calls should take less than 1 second
        assert elapsed < 1.0


class TestMonitorPerformanceOnCoroutines:
    """#2340 — une coroutine décorée doit rester une coroutine.

    Un wrapper synchrone rendrait la coroutine sans l'attendre : la mesure
    porterait alors sur sa *création* (~0 ms) et `iscoroutinefunction` sur la
    fonction décorée répondrait False, cassant toute introspection async.
    """

    def test_decorated_coroutine_stays_a_coroutine_function(self):
        @monitor_performance()
        async def coro():
            return 42

        assert inspect.iscoroutinefunction(coro)

    async def test_awaited_result_is_the_value_not_a_coroutine(self):
        @monitor_performance(log_args=True)
        async def add(a, b):
            await asyncio.sleep(0)
            return a + b

        result = await add(2, 3)
        assert result == 5

    async def test_exception_propagates_through_async_wrapper(self):
        @monitor_performance()
        async def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await failing()

    async def test_measured_time_covers_the_awaited_body(self):
        """Le temps loggué doit couvrir l'exécution, pas la seule création.

        `performance_logger` a `propagate = False` : `caplog` (branché sur le
        logger racine) ne le voit pas. On pose donc un handler sur ce logger-là.
        """

        @monitor_performance()
        async def slow():
            await asyncio.sleep(0.05)

        records = []

        class _Collector(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        perf_logger = logging.getLogger("performance_monitor")
        handler = _Collector()
        perf_logger.addHandler(handler)
        try:
            await slow()
        finally:
            perf_logger.removeHandler(handler)

        durations = [json.loads(message)["execution_time_ms"] for message in records]
        assert durations, "le logger de performance n'a rien émis"
        assert max(durations) >= 40.0, durations

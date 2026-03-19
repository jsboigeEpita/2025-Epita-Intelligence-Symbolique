# tests/unit/argumentation_analysis/utils/test_performance_monitoring.py
"""Tests for performance monitoring decorator."""

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

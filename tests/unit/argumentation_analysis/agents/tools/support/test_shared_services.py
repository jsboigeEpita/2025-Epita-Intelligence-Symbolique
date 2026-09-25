# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.tools.support.shared_services
Covers get_configured_logger, ServiceRegistry, ConfigManager.
"""

import pytest
import logging
import subprocess
import sys
from pathlib import Path

from argumentation_analysis.agents.tools.support.shared_services import (
    get_configured_logger,
    ServiceRegistry,
    ConfigManager,
)

# ============================================================
# get_configured_logger
# ============================================================


class TestGetConfiguredLogger:
    def test_returns_logger(self):
        logger = get_configured_logger("test_logger")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self):
        logger = get_configured_logger("my_module")
        assert logger.name == "my_module"

    def test_different_names_different_loggers(self):
        l1 = get_configured_logger("mod_a")
        l2 = get_configured_logger("mod_b")
        assert l1 is not l2
        assert l1.name != l2.name

    def test_same_name_same_logger(self):
        l1 = get_configured_logger("same")
        l2 = get_configured_logger("same")
        assert l1 is l2

    def test_leaves_the_root_logger_alone(self):
        """#2346: a library helper does not configure the process's root logger.

        Run in a fresh interpreter: pytest's own handlers are on the root
        logger here, and ``basicConfig`` is a no-op once one exists. The root
        handlers are dropped after the import, so the check measures the call
        alone.
        """
        repo = Path(__file__).resolve().parents[6]
        done = subprocess.run(
            [
                sys.executable,
                "-c",
                "import logging\n"
                "from argumentation_analysis.agents.tools.support.shared_services"
                " import get_configured_logger\n"
                "logging.getLogger().handlers.clear()\n"
                "get_configured_logger('x')\n"
                "print(len(logging.getLogger().handlers))",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert done.returncode == 0, done.stderr[-2000:]
        assert done.stdout.strip().splitlines()[-1] == "0"


# ============================================================
# ServiceRegistry
# ============================================================


class TestServiceRegistry:
    def setup_method(self):
        """Clear registry before each test."""
        ServiceRegistry.reset()

    def test_get_creates_instance(self):
        class MyService:
            pass

        svc = ServiceRegistry.get(MyService)
        assert isinstance(svc, MyService)

    def test_get_returns_same_instance(self):
        class MyService:
            pass

        svc1 = ServiceRegistry.get(MyService)
        svc2 = ServiceRegistry.get(MyService)
        assert svc1 is svc2

    def test_different_services_different_instances(self):
        class ServiceA:
            pass

        class ServiceB:
            pass

        a = ServiceRegistry.get(ServiceA)
        b = ServiceRegistry.get(ServiceB)
        assert a is not b
        assert type(a) != type(b)

    def test_service_with_init(self):
        class CounterService:
            instances = 0

            def __init__(self):
                CounterService.instances += 1

        CounterService.instances = 0
        ServiceRegistry.get(CounterService)
        ServiceRegistry.get(CounterService)
        assert CounterService.instances == 1  # Only created once

    def test_reset_forgets_the_instances(self):
        class MyService:
            pass

        first = ServiceRegistry.get(MyService)
        ServiceRegistry.reset()
        assert ServiceRegistry.get(MyService) is not first


# ============================================================
# ConfigManager
# ============================================================


class TestConfigManager:
    def setup_method(self):
        """Clear config cache before each test."""
        ConfigManager.reset()

    def test_load_config(self):
        result = ConfigManager.load_config("test_cfg", lambda: {"key": "value"})
        assert result == {"key": "value"}

    def test_load_config_cached(self):
        call_count = 0

        def loader():
            nonlocal call_count
            call_count += 1
            return {"data": call_count}

        r1 = ConfigManager.load_config("cached_cfg", loader)
        r2 = ConfigManager.load_config("cached_cfg", loader)
        assert r1 == r2
        assert call_count == 1

    def test_load_config_force_reload(self):
        call_count = 0

        def loader():
            nonlocal call_count
            call_count += 1
            return {"version": call_count}

        r1 = ConfigManager.load_config("reload_cfg", loader)
        r2 = ConfigManager.load_config("reload_cfg", loader, force_reload=True)
        assert call_count == 2
        assert r1["version"] == 1
        assert r2["version"] == 2

    def test_different_configs_independent(self):
        r1 = ConfigManager.load_config("cfg_a", lambda: "A")
        r2 = ConfigManager.load_config("cfg_b", lambda: "B")
        assert r1 == "A"
        assert r2 == "B"

    def test_load_config_with_none_value(self):
        result = ConfigManager.load_config("none_cfg", lambda: None)
        assert result is None

    def test_a_failed_load_is_retried(self):
        """#2346: a loader that returns None loaded nothing; the next call retries."""
        results = iter([None, {"loaded": True}])
        assert ConfigManager.load_config("flaky", lambda: next(results)) is None
        assert ConfigManager.load_config("flaky", lambda: next(results)) == {
            "loaded": True
        }

    def test_a_failed_reload_drops_the_previous_value(self):
        ConfigManager.load_config("cfg", lambda: {"v": 1})
        assert ConfigManager.load_config("cfg", lambda: None, force_reload=True) is None
        assert ConfigManager.load_config("cfg", lambda: {"v": 2}) == {"v": 2}

    def test_reset_forgets_the_configs(self):
        ConfigManager.load_config("cfg", lambda: {"v": 1})
        ConfigManager.reset()
        assert ConfigManager.load_config("cfg", lambda: {"v": 2}) == {"v": 2}


def test_the_root_conftest_resets_the_caches_after_every_test(request):
    """#2346: one autouse fixture empties both caches; no test file rolls its own."""
    assert "reset_shared_services" in request.fixturenames

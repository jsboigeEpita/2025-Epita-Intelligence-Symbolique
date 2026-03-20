# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.services.flask_service_integration
Covers FlaskServiceIntegrator: init, health status, service management.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Patch heavy imports before importing the module
import sys

_mock_logic = MagicMock()
_mock_group_chat = MagicMock()
_orig_logic = sys.modules.get("argumentation_analysis.services.logic_service")
_orig_gc = sys.modules.get("argumentation_analysis.orchestration.group_chat")
sys.modules["argumentation_analysis.services.logic_service"] = _mock_logic
sys.modules["argumentation_analysis.orchestration.group_chat"] = _mock_group_chat

from argumentation_analysis.services.flask_service_integration import (
    FlaskServiceIntegrator,
    service_integrator,
    init_flask_services,
    get_flask_service,
)

# Restore originals
if _orig_logic is not None:
    sys.modules["argumentation_analysis.services.logic_service"] = _orig_logic
else:
    sys.modules.pop("argumentation_analysis.services.logic_service", None)
if _orig_gc is not None:
    sys.modules["argumentation_analysis.orchestration.group_chat"] = _orig_gc
else:
    sys.modules.pop("argumentation_analysis.orchestration.group_chat", None)


# ============================================================
# Initialization
# ============================================================


class TestInit:
    def test_default_init(self):
        integrator = FlaskServiceIntegrator()
        assert integrator.app is None
        assert integrator.services == {}
        assert integrator.health_status == {}
        assert integrator.initialization_errors == []

    def test_init_with_app(self):
        mock_app = MagicMock()
        integrator = FlaskServiceIntegrator(app=mock_app)
        assert integrator.app is mock_app


# ============================================================
# get_health_status
# ============================================================


class TestGetHealthStatus:
    def test_empty_services(self):
        integrator = FlaskServiceIntegrator()
        status = integrator.get_health_status()
        assert status["status"] == "healthy"  # 0/0 = all healthy
        assert status["services_count"]["total"] == 0
        assert status["services_count"]["healthy"] == 0

    def test_all_healthy(self):
        integrator = FlaskServiceIntegrator()
        integrator.health_status = {
            "svc1": {"status": "healthy"},
            "svc2": {"status": "healthy"},
        }
        status = integrator.get_health_status()
        assert status["status"] == "healthy"
        assert status["services_count"]["total"] == 2
        assert status["services_count"]["healthy"] == 2
        assert status["services_count"]["unhealthy"] == 0

    def test_some_unhealthy(self):
        integrator = FlaskServiceIntegrator()
        integrator.health_status = {
            "svc1": {"status": "healthy"},
            "svc2": {"status": "error"},
        }
        status = integrator.get_health_status()
        assert status["status"] == "degraded"
        assert status["services_count"]["unhealthy"] == 1

    def test_has_timestamp(self):
        integrator = FlaskServiceIntegrator()
        status = integrator.get_health_status()
        assert "timestamp" in status

    def test_has_services_list(self):
        integrator = FlaskServiceIntegrator()
        integrator.health_status = {"svc1": {"status": "healthy"}}
        status = integrator.get_health_status()
        assert "svc1" in status["services"]

    def test_has_initialization_errors(self):
        integrator = FlaskServiceIntegrator()
        integrator.initialization_errors = ["error1"]
        status = integrator.get_health_status()
        assert status["initialization_errors"] == ["error1"]


# ============================================================
# get_detailed_health_status
# ============================================================


class TestGetDetailedHealthStatus:
    def test_has_timestamp(self):
        integrator = FlaskServiceIntegrator()
        status = integrator.get_detailed_health_status()
        assert "timestamp" in status

    def test_has_services_copy(self):
        integrator = FlaskServiceIntegrator()
        integrator.health_status = {"svc": {"status": "ok"}}
        status = integrator.get_detailed_health_status()
        assert status["services"] == {"svc": {"status": "ok"}}
        # Should be a copy, not same dict
        assert status["services"] is not integrator.health_status

    def test_has_initialization_errors(self):
        integrator = FlaskServiceIntegrator()
        integrator.initialization_errors = ["e1", "e2"]
        status = integrator.get_detailed_health_status()
        assert status["initialization_errors"] == ["e1", "e2"]


# ============================================================
# get_service_health
# ============================================================


class TestGetServiceHealth:
    def test_existing_service(self):
        integrator = FlaskServiceIntegrator()
        integrator.health_status = {
            "logic_service": {"status": "healthy", "last_check": "2024-01-01"}
        }
        result = integrator.get_service_health("logic_service")
        assert result["service_name"] == "logic_service"
        assert result["status"] == "healthy"
        assert "timestamp" in result

    def test_nonexistent_service(self):
        integrator = FlaskServiceIntegrator()
        result = integrator.get_service_health("nonexistent")
        assert "error" in result
        assert "available_services" in result


# ============================================================
# get_service
# ============================================================


class TestGetService:
    def test_existing_service(self):
        integrator = FlaskServiceIntegrator()
        mock_svc = MagicMock()
        integrator.services["logic_service"] = mock_svc
        assert integrator.get_service("logic_service") is mock_svc

    def test_nonexistent_service(self):
        integrator = FlaskServiceIntegrator()
        assert integrator.get_service("nonexistent") is None


# ============================================================
# is_service_healthy
# ============================================================


class TestIsServiceHealthy:
    def test_healthy(self):
        integrator = FlaskServiceIntegrator()
        integrator.health_status = {"svc": {"status": "healthy"}}
        assert integrator.is_service_healthy("svc") is True

    def test_unhealthy(self):
        integrator = FlaskServiceIntegrator()
        integrator.health_status = {"svc": {"status": "error"}}
        assert integrator.is_service_healthy("svc") is False

    def test_unknown_service(self):
        integrator = FlaskServiceIntegrator()
        assert integrator.is_service_healthy("unknown") is False


# ============================================================
# _register_services_to_app
# ============================================================


class TestRegisterServicesToApp:
    def test_no_app_raises(self):
        integrator = FlaskServiceIntegrator()
        with pytest.raises(ValueError, match="App Flask"):
            integrator._register_services_to_app()

    def test_registers_logic_service(self):
        integrator = FlaskServiceIntegrator()
        integrator.app = MagicMock()
        mock_svc = MagicMock()
        integrator.services["logic_service"] = mock_svc
        integrator._register_services_to_app()
        assert integrator.app.logic_service is mock_svc

    def test_registers_group_chat(self):
        integrator = FlaskServiceIntegrator()
        integrator.app = MagicMock()
        mock_gc = MagicMock()
        integrator.services["group_chat_orchestration"] = mock_gc
        integrator._register_services_to_app()
        assert integrator.app.group_chat_orchestration is mock_gc

    def test_registers_self(self):
        integrator = FlaskServiceIntegrator()
        integrator.app = MagicMock()
        integrator._register_services_to_app()
        assert integrator.app.service_integrator is integrator


# ============================================================
# _perform_initial_healthcheck
# ============================================================


class TestPerformInitialHealthcheck:
    def test_updates_healthy_service(self):
        integrator = FlaskServiceIntegrator()
        mock_svc = MagicMock()
        mock_svc.get_service_status.return_value = {"active": True}
        integrator.services = {"svc1": mock_svc}
        integrator.health_status = {"svc1": {"status": "healthy"}}
        integrator._perform_initial_healthcheck()
        assert "detailed_status" in integrator.health_status["svc1"]

    def test_handles_service_without_status_method(self):
        integrator = FlaskServiceIntegrator()
        mock_svc = MagicMock(spec=[])  # No get_service_status
        integrator.services = {"svc1": mock_svc}
        integrator.health_status = {"svc1": {"status": "healthy"}}
        integrator._perform_initial_healthcheck()
        # Should not crash; no update to detailed_status
        assert integrator.health_status["svc1"]["status"] == "healthy"

    def test_handles_healthcheck_error(self):
        integrator = FlaskServiceIntegrator()
        mock_svc = MagicMock()
        mock_svc.get_service_status.side_effect = RuntimeError("boom")
        integrator.services = {"svc1": mock_svc}
        integrator.health_status = {"svc1": {"status": "healthy"}}
        integrator._perform_initial_healthcheck()
        assert integrator.health_status["svc1"]["status"] == "error"
        assert "boom" in integrator.health_status["svc1"]["error"]


# ============================================================
# refresh_health_status
# ============================================================


class TestRefreshHealthStatus:
    def test_returns_health_status(self):
        integrator = FlaskServiceIntegrator()
        result = integrator.refresh_health_status()
        assert "status" in result
        assert "services_count" in result


# ============================================================
# Module-level utilities
# ============================================================


class TestModuleUtilities:
    def test_service_integrator_singleton(self):
        assert isinstance(service_integrator, FlaskServiceIntegrator)

    def test_get_flask_service_delegates(self):
        service_integrator.services["test_svc"] = "mock_value"
        try:
            assert get_flask_service("test_svc") == "mock_value"
        finally:
            service_integrator.services.pop("test_svc", None)

    def test_get_flask_service_returns_none_for_missing(self):
        assert get_flask_service("nonexistent_svc_xyz") is None

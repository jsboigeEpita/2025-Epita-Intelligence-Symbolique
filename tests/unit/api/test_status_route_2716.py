"""#2716: ``GET /api/status`` answered 500, and the failure stuck.

Three defects, one route:

* ``get_analysis_service`` asked the manager ``is_ready()``, a method
  ``OrchestrationServiceManager`` never had (``579edd022``). The first call
  raised on every seat, hence the 500. ``initialize()``'s own answer was
  discarded.
* The manager was cached **before** that check, so every later call served the
  refused manager: the route answered 200 ``degraded`` with no cause, and never
  initialized again.
* ``_initialize_specialized_orchestrators`` built ``CluedoExtendedOrchestrator``
  without the ``settings`` its constructor requires, so ``initialize()``
  returned False whenever ``enable_specialized_orchestrators`` was on, which is
  its default.

The route's only test swapped the dependency for the mock, and the manager's
tests switch the specialized orchestrators off, so the real dependency never
met the default settings. These witnesses run both.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.dependencies import AnalysisService, get_analysis_service
from argumentation_analysis.config.settings import settings
from argumentation_analysis.orchestration.service_manager import (
    OrchestrationServiceManager,
)


@pytest.fixture
def no_cached_manager(monkeypatch):
    """Each test starts, and leaves, without a process-wide manager."""
    monkeypatch.setattr(dependencies, "_global_service_manager", None)
    yield
    manager = dependencies._global_service_manager
    if manager is not None:
        asyncio.run(manager.shutdown())


def _initialize_returning(answer, calls):
    async def initialize(self):
        calls.append(self)
        if answer:
            self._initialized = True
        else:
            self.setup_failures["probe_2716"] = "RuntimeError: refused on purpose"
        return answer

    return initialize


def test_the_status_route_does_not_answer_500(monkeypatch, no_cached_manager):
    """The real dependency, the real manager, the default settings."""
    from api.main import app

    assert settings.service_manager.enable_specialized_orchestrators
    monkeypatch.setattr(app, "dependency_overrides", {})

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/status")

    assert response.status_code == 200, response.text
    body = response.json()
    manager = dependencies._global_service_manager
    assert manager is not None and manager.is_available()
    # Seat-dependent (a keyless seat names its missing LLM service), but the
    # route states it either way.
    assert body["service_status"]["setup_failures"] == manager.setup_failures
    expected = "degraded" if manager.setup_failures else "operational"
    assert body["status"] == expected, body


def test_an_initialized_manager_is_served(monkeypatch, no_cached_manager):
    calls = []
    monkeypatch.setattr(
        OrchestrationServiceManager, "initialize", _initialize_returning(True, calls)
    )

    service = asyncio.run(get_analysis_service())

    assert isinstance(service, AnalysisService)
    assert service.is_available()
    assert len(calls) == 1


def test_a_refused_manager_is_neither_served_nor_cached(monkeypatch, no_cached_manager):
    calls = []
    monkeypatch.setattr(
        OrchestrationServiceManager, "initialize", _initialize_returning(False, calls)
    )

    for attempt in (1, 2):
        with pytest.raises(RuntimeError) as raised:
            asyncio.run(get_analysis_service())
        message = str(raised.value)
        assert "initialize()" in message, message
        assert "probe_2716" in message, message
        assert len(calls) == attempt

    assert dependencies._global_service_manager is None
    assert all(manager._shutdown for manager in calls)


def test_a_failed_step_is_named_in_the_refusal(monkeypatch, no_cached_manager):
    """The real initialize(): a step that raises is named, not only logged."""

    async def fail(self):
        raise RuntimeError("probe_2716 step failure")

    monkeypatch.setattr(
        OrchestrationServiceManager, "_initialize_specialized_orchestrators", fail
    )

    with pytest.raises(RuntimeError, match="probe_2716 step failure"):
        asyncio.run(get_analysis_service())
    assert dependencies._global_service_manager is None


def test_the_status_details_measure_the_llm_service():
    manager = OrchestrationServiceManager()
    manager.setup_failures["llm_service"] = "ValueError: no key on this seat"

    details = AnalysisService(manager).get_status_details()

    assert details["llm_enabled"] is False
    assert details["setup_failures"] == {
        "llm_service": "ValueError: no key on this seat"
    }


def test_an_incomplete_setup_is_degraded_not_operational():
    from api.endpoints import status_endpoint

    manager = OrchestrationServiceManager()
    manager._initialized = True
    manager.setup_failures["informal_plugin"] = "RuntimeError: not registered"

    response = asyncio.run(status_endpoint(AnalysisService(manager)))

    assert response.status == "degraded"
    assert response.service_status["setup_failures"] == {
        "informal_plugin": "RuntimeError: not registered"
    }


def test_initialize_builds_the_cluedo_orchestrator_with_default_settings():
    manager = OrchestrationServiceManager()
    try:
        assert asyncio.run(manager.initialize()) is True, manager.setup_failures
        assert manager.cluedo_orchestrator is not None
        assert manager.cluedo_orchestrator.settings is settings
    finally:
        asyncio.run(manager.shutdown())

"""
Tests unitaires pour OrchestrationServiceManager et ServiceManagerState.

Couvre:
- ServiceManagerState: session ID, uptime, activity tracking
- OrchestrationServiceManager.__init__: default construction
- get_status: status report (async)
- is_available: availability checks
- get_status_details: detailed status
- analyze_text: validation (not initialized, empty text)
- shutdown: clean shutdown (async)

Issue: #36 (test coverage)
"""

import pytest
import asyncio
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


# ========================================================================
# ServiceManagerState
# ========================================================================


class TestServiceManagerState:
    """Tests for ServiceManagerState."""

    def _make_state(self):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerState,
        )
        return ServiceManagerState()

    def test_init_creates_session_id(self):
        state = self._make_state()
        assert state.session_id is not None
        # Verify it's a valid UUID
        uuid.UUID(state.session_id)

    def test_init_sets_start_time(self):
        before = datetime.now()
        state = self._make_state()
        after = datetime.now()
        assert before <= state.start_time <= after

    def test_init_empty_services(self):
        state = self._make_state()
        assert state.active_services == {}
        assert state.service_states == {}

    def test_update_activity_changes_timestamp(self):
        state = self._make_state()
        old_activity = state.last_activity
        # Small delay to ensure timestamp differs
        import time
        time.sleep(0.01)
        state.update_activity()
        assert state.last_activity >= old_activity

    def test_get_uptime_positive(self):
        state = self._make_state()
        uptime = state.get_uptime()
        assert uptime >= 0.0

    def test_unique_session_ids(self):
        state1 = self._make_state()
        state2 = self._make_state()
        assert state1.session_id != state2.session_id


# ========================================================================
# OrchestrationServiceManager
# ========================================================================


class TestOrchestrationServiceManager:
    """Tests for OrchestrationServiceManager (non-async methods + init)."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )
        return OrchestrationServiceManager(enable_logging=False)

    # --- __init__ ---

    def test_init_default_state(self, manager):
        assert manager._initialized is False
        assert manager._shutdown is False
        assert manager.state is not None
        assert manager.state.session_id is not None

    def test_init_managers_none(self, manager):
        assert manager.strategic_manager is None
        assert manager.tactical_manager is None
        assert manager.operational_manager is None

    def test_init_orchestrators_none(self, manager):
        assert manager.cluedo_orchestrator is None
        assert manager.conversation_orchestrator is None
        assert manager.llm_orchestrator is None
        assert manager.fact_checking_orchestrator is None

    def test_init_middleware_none(self, manager):
        assert manager.middleware is None

    def test_init_kernel_none(self, manager):
        assert manager.kernel is None

    def test_init_with_taxonomy_path(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )
        mgr = OrchestrationServiceManager(
            enable_logging=False, taxonomy_file_path="/some/path.csv"
        )
        assert mgr.taxonomy_file_path == "/some/path.csv"

    # --- is_available ---

    def test_is_available_not_initialized(self, manager):
        assert manager.is_available() is False

    def test_is_available_after_init_flag(self, manager):
        manager._initialized = True
        assert manager.is_available() is True

    def test_is_available_after_shutdown(self, manager):
        manager._initialized = True
        manager._shutdown = True
        assert manager.is_available() is False

    # --- __str__ and __repr__ ---

    def test_str_contains_session_id(self, manager):
        s = str(manager)
        assert manager.state.session_id in s
        assert "initialized=False" in s

    def test_repr_contains_uptime(self, manager):
        r = repr(manager)
        assert "uptime=" in r

    # --- get_status_details ---

    def test_get_status_details_not_initialized(self, manager):
        details = manager.get_status_details()
        assert details["overall_status"] == "unavailable"
        assert details["initialized"] is False
        assert details["shutdown_initiated"] is False
        assert "session_id" in details
        assert "uptime_seconds" in details

    def test_get_status_details_initialized(self, manager):
        manager._initialized = True
        details = manager.get_status_details()
        assert details["overall_status"] == "available"
        assert details["initialized"] is True


# ========================================================================
# Async tests for OrchestrationServiceManager
# ========================================================================


class TestOrchestrationServiceManagerAsync:
    """Async tests for OrchestrationServiceManager."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )
        return OrchestrationServiceManager(enable_logging=False)

    # --- get_status ---

    async def test_get_status_not_initialized(self, manager):
        status = await manager.get_status()
        assert status["initialized"] is False
        assert "session_id" in status
        assert "uptime_seconds" in status
        assert "last_activity" in status
        assert "active_services" in status

    async def test_get_status_all_services_false(self, manager):
        status = await manager.get_status()
        services = status["active_services"]
        assert services["strategic_manager"] is False
        assert services["tactical_manager"] is False
        assert services["operational_manager"] is False
        assert services["middleware"] is False

    # --- analyze_text ---

    async def test_analyze_text_not_initialized_raises(self, manager):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )
        with pytest.raises(ServiceManagerError, match="non initialisé"):
            await manager.analyze_text("Test text")

    async def test_analyze_text_empty_text_raises(self, manager):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )
        manager._initialized = True
        with pytest.raises(ServiceManagerError, match="vide"):
            await manager.analyze_text("")

    async def test_analyze_text_whitespace_only_raises(self, manager):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )
        manager._initialized = True
        with pytest.raises(ServiceManagerError, match="vide"):
            await manager.analyze_text("   ")

    # --- shutdown ---

    async def test_shutdown_sets_flag(self, manager):
        await manager.shutdown()
        assert manager._shutdown is True

    async def test_shutdown_idempotent(self, manager):
        await manager.shutdown()
        await manager.shutdown()  # Should not raise
        assert manager._shutdown is True

    async def test_shutdown_with_components(self, manager):
        """Shutdown should call shutdown() on all components that have it."""
        mock_component = MagicMock()
        mock_component.shutdown = MagicMock(return_value=None)  # sync shutdown

        manager.cluedo_orchestrator = mock_component
        await manager.shutdown()

        mock_component.shutdown.assert_called_once()
        assert manager._shutdown is True

    async def test_shutdown_with_async_component(self, manager):
        """Shutdown handles async shutdown methods correctly."""
        mock_component = MagicMock()
        mock_component.shutdown = AsyncMock()

        manager.llm_orchestrator = mock_component
        await manager.shutdown()

        mock_component.shutdown.assert_awaited_once()

    # --- initialize (error path) ---

    async def test_initialize_already_initialized(self, manager):
        manager._initialized = True
        result = await manager.initialize()
        assert result is True  # Returns True without re-initializing

    async def test_initialize_bootstrap_failure(self, manager):
        """When bootstrap fails, initialize returns False."""
        with patch(
            "argumentation_analysis.orchestration.service_manager.initialize_project_environment",
            return_value=None
        ):
            result = await manager.initialize()
            assert result is False


# ========================================================================
# ServiceManagerError
# ========================================================================


class TestServiceManagerError:
    """Tests for ServiceManagerError exception class."""

    def test_is_exception(self):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )
        assert issubclass(ServiceManagerError, Exception)

    def test_can_be_raised_and_caught(self):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )
        with pytest.raises(ServiceManagerError, match="test message"):
            raise ServiceManagerError("test message")

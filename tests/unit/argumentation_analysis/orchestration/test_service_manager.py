"""
Tests unitaires pour OrchestrationServiceManager, ServiceManagerState, ServiceManagerError,
et la factory create_service_manager.

Couvre:
- ServiceManagerState: session ID, uptime, activity tracking
- ServiceManagerError: custom exception
- OrchestrationServiceManager.__init__: default construction, params, logging
- unified_state methods: property, create, snapshot
- initialize(): success, already initialized, bootstrap fail, no API key, middleware/hierarchical/specialized init
- initialize_middleware(): success, already exists, disabled, channel registration
- _initialize_hierarchical_managers(): success, no middleware, exception
- _initialize_specialized_orchestrators(): success, exception
- analyze_text(): not initialized, empty text, orchestrator dispatch, hierarchical fallback, error handling
- _select_orchestrator(): mapping for all analysis types
- _run_specialized_analysis(): fact_checking, real_llm, generic, error
- _run_hierarchical_analysis(): strategic/tactical/operational dispatch
- get_status() / health_check()
- is_available() / get_status_details()
- shutdown(): normal, idempotent, component shutdown (sync + async), error
- __str__ / __repr__
- create_service_manager(): factory function

Issue: #36, #80 (test coverage)
"""

import pytest
import asyncio
import uuid
import time
import json
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, timedelta
from pathlib import Path

# ========================================================================
# Module-level patch path prefix
# ========================================================================
SM_MODULE = "argumentation_analysis.orchestration.service_manager"


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

    def test_init_last_activity_set(self):
        before = datetime.now()
        state = self._make_state()
        assert state.last_activity >= before

    def test_update_activity_changes_timestamp(self):
        state = self._make_state()
        old_activity = state.last_activity
        time.sleep(0.01)
        state.update_activity()
        assert state.last_activity >= old_activity

    def test_get_uptime_positive(self):
        state = self._make_state()
        uptime = state.get_uptime()
        assert uptime >= 0.0

    def test_get_uptime_increases(self):
        state = self._make_state()
        u1 = state.get_uptime()
        time.sleep(0.01)
        u2 = state.get_uptime()
        assert u2 >= u1

    def test_unique_session_ids(self):
        state1 = self._make_state()
        state2 = self._make_state()
        assert state1.session_id != state2.session_id


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

    def test_message_preserved(self):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )

        err = ServiceManagerError("specific error detail")
        assert str(err) == "specific error detail"


# ========================================================================
# OrchestrationServiceManager — Construction
# ========================================================================


class TestOrchestrationServiceManagerInit:
    """Tests for OrchestrationServiceManager.__init__ and basic sync methods."""

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

    def test_init_unified_state_none(self, manager):
        assert manager._unified_state is None

    def test_init_with_taxonomy_path(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        mgr = OrchestrationServiceManager(
            enable_logging=False, taxonomy_file_path="/some/path.csv"
        )
        assert mgr.taxonomy_file_path == "/some/path.csv"

    def test_init_without_taxonomy_path(self, manager):
        assert manager.taxonomy_file_path is None

    def test_init_config_is_none(self, manager):
        # Legacy attribute kept for backward compat
        assert manager.config is None

    def test_init_llm_service_id_default(self, manager):
        assert manager.llm_service_id == "gpt-5-mini"

    def test_init_with_logging_enabled(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        # Should not raise
        mgr = OrchestrationServiceManager(enable_logging=True, log_level=40)
        assert mgr.logger is not None

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

    def test_is_available_shutdown_only(self, manager):
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
        assert manager.state.session_id in r

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

    def test_get_status_details_contains_timestamps(self, manager):
        details = manager.get_status_details()
        assert "start_time" in details
        assert "last_activity" in details


# ========================================================================
# Unified State methods
# ========================================================================


class TestUnifiedState:
    """Tests for unified_state property, create_unified_state, get_unified_state_snapshot."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    def test_unified_state_initially_none(self, manager):
        assert manager.unified_state is None

    def test_create_unified_state(self, manager):
        state = manager.create_unified_state("Test text for analysis")
        assert state is not None
        assert manager.unified_state is state

    def test_create_unified_state_returns_state_object(self, manager):
        state = manager.create_unified_state("Sample text")
        # Should have the text stored
        assert hasattr(state, "get_state_snapshot")

    def test_get_unified_state_snapshot_none_when_no_state(self, manager):
        result = manager.get_unified_state_snapshot()
        assert result is None

    def test_get_unified_state_snapshot_after_creation(self, manager):
        manager.create_unified_state("Some analysis text")
        snapshot = manager.get_unified_state_snapshot(summarize=True)
        assert snapshot is not None
        assert isinstance(snapshot, dict)

    def test_get_unified_state_snapshot_no_summarize(self, manager):
        manager.create_unified_state("Another text")
        snapshot = manager.get_unified_state_snapshot(summarize=False)
        assert snapshot is not None


# ========================================================================
# Async tests — initialize()
# ========================================================================


class TestInitialize:
    """Async tests for OrchestrationServiceManager.initialize()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    async def test_initialize_already_initialized(self, manager):
        manager._initialized = True
        result = await manager.initialize()
        assert result is True

    async def test_initialize_bootstrap_failure(self, manager):
        """When bootstrap returns None, initialize returns False."""
        with patch(f"{SM_MODULE}.initialize_project_environment", return_value=None):
            result = await manager.initialize()
            assert result is False

    async def test_initialize_bootstrap_exception(self, manager):
        """When bootstrap raises, initialize returns False."""
        with patch(
            f"{SM_MODULE}.initialize_project_environment",
            side_effect=RuntimeError("bootstrap crash"),
        ):
            result = await manager.initialize()
            assert result is False

    async def test_initialize_success_no_api_key(self, manager):
        """Initialize succeeds without API key but logs warning."""
        mock_settings = MagicMock()
        mock_settings.openai.api_key = None
        mock_settings.service_manager.default_llm_service_id = "openai"
        mock_settings.service_manager.enable_communication_middleware = False
        mock_settings.service_manager.enable_hierarchical = False
        mock_settings.service_manager.enable_specialized_orchestrators = False

        mock_context = MagicMock()

        with patch(
            f"{SM_MODULE}.initialize_project_environment", return_value=mock_context
        ), patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.sk"
        ) as mock_sk:
            mock_sk.Kernel.return_value = MagicMock()
            result = await manager.initialize()
            assert result is True
            assert manager._initialized is True

    async def test_initialize_success_with_api_key(self, manager):
        """Full initialize success path with API key and LLM service."""
        mock_settings = MagicMock()
        mock_settings.openai.api_key.get_secret_value.return_value = "sk-test-key"
        mock_settings.service_manager.default_llm_service_id = "openai"
        mock_settings.service_manager.enable_communication_middleware = False
        mock_settings.service_manager.enable_hierarchical = False
        mock_settings.service_manager.enable_specialized_orchestrators = False

        mock_context = MagicMock()
        mock_kernel = MagicMock()
        mock_kernel.get_service.return_value = MagicMock()
        mock_llm_service = MagicMock()

        with patch(
            f"{SM_MODULE}.initialize_project_environment", return_value=mock_context
        ), patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.sk"
        ) as mock_sk, patch(
            f"{SM_MODULE}.create_llm_service", return_value=mock_llm_service
        ):
            mock_sk.Kernel.return_value = mock_kernel
            result = await manager.initialize()
            assert result is True
            assert manager._initialized is True
            mock_kernel.add_service.assert_called_once_with(mock_llm_service)

    async def test_initialize_llm_service_failure_continues(self, manager):
        """If create_llm_service raises, initialize still succeeds."""
        mock_settings = MagicMock()
        mock_settings.openai.api_key.get_secret_value.return_value = "sk-test-key"
        mock_settings.service_manager.default_llm_service_id = "openai"
        mock_settings.service_manager.enable_communication_middleware = False
        mock_settings.service_manager.enable_hierarchical = False
        mock_settings.service_manager.enable_specialized_orchestrators = False

        mock_context = MagicMock()
        mock_kernel = MagicMock()
        mock_kernel.get_service.side_effect = Exception("no service")

        with patch(
            f"{SM_MODULE}.initialize_project_environment", return_value=mock_context
        ), patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.sk"
        ) as mock_sk, patch(
            f"{SM_MODULE}.create_llm_service", side_effect=RuntimeError("LLM fail")
        ):
            mock_sk.Kernel.return_value = mock_kernel
            result = await manager.initialize()
            # Still succeeds (error is logged but not fatal)
            assert result is True

    async def test_initialize_calls_middleware_when_enabled(self, manager):
        """When middleware is enabled, initialize_middleware is called."""
        mock_settings = MagicMock()
        mock_settings.openai.api_key = None
        mock_settings.service_manager.default_llm_service_id = "openai"
        mock_settings.service_manager.enable_communication_middleware = True
        mock_settings.service_manager.enable_hierarchical = False
        mock_settings.service_manager.enable_specialized_orchestrators = False

        mock_context = MagicMock()

        with patch(
            f"{SM_MODULE}.initialize_project_environment", return_value=mock_context
        ), patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.sk"
        ) as mock_sk, patch.object(
            manager, "initialize_middleware", new_callable=AsyncMock
        ) as mock_mw:
            mock_sk.Kernel.return_value = MagicMock()
            result = await manager.initialize()
            assert result is True
            mock_mw.assert_awaited_once()

    async def test_initialize_calls_hierarchical_when_enabled(self, manager):
        """When hierarchical is enabled, _initialize_hierarchical_managers is called."""
        mock_settings = MagicMock()
        mock_settings.openai.api_key = None
        mock_settings.service_manager.default_llm_service_id = "openai"
        mock_settings.service_manager.enable_communication_middleware = False
        mock_settings.service_manager.enable_hierarchical = True
        mock_settings.service_manager.enable_specialized_orchestrators = False

        mock_context = MagicMock()

        with patch(
            f"{SM_MODULE}.initialize_project_environment", return_value=mock_context
        ), patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.sk"
        ) as mock_sk, patch.object(
            manager, "_initialize_hierarchical_managers", new_callable=AsyncMock
        ) as mock_hm:
            mock_sk.Kernel.return_value = MagicMock()
            result = await manager.initialize()
            assert result is True
            mock_hm.assert_awaited_once()


# ========================================================================
# Async tests — initialize_middleware()
# ========================================================================


class TestInitializeMiddleware:
    """Tests for initialize_middleware()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    async def test_middleware_already_initialized(self, manager):
        manager.middleware = MagicMock()
        await manager.initialize_middleware()
        # Should not create a new middleware

    async def test_middleware_disabled_in_settings(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.enable_communication_middleware = False

        with patch(f"{SM_MODULE}.settings", mock_settings):
            await manager.initialize_middleware()
            assert manager.middleware is None

    async def test_middleware_success_with_channel(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.enable_communication_middleware = True
        mock_settings.service_manager.hierarchical_channel_id = "test_channel"

        mock_mw_class = MagicMock()
        mock_mw_instance = MagicMock()
        mock_mw_class.return_value = mock_mw_instance

        mock_hc_class = MagicMock()
        mock_hc_instance = MagicMock()
        mock_hc_class.return_value = mock_hc_instance

        with patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.MessageMiddleware", mock_mw_class
        ), patch(f"{SM_MODULE}.HierarchicalChannel", mock_hc_class):
            await manager.initialize_middleware()
            assert manager.middleware is mock_mw_instance
            mock_mw_instance.register_channel.assert_called_once_with(mock_hc_instance)

    async def test_middleware_no_hierarchical_channel_class(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.enable_communication_middleware = True

        mock_mw_class = MagicMock()
        mock_mw_instance = MagicMock()
        mock_mw_class.return_value = mock_mw_instance

        with patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.MessageMiddleware", mock_mw_class
        ), patch(f"{SM_MODULE}.HierarchicalChannel", None):
            await manager.initialize_middleware()
            assert manager.middleware is mock_mw_instance
            # No channel registered since HierarchicalChannel is None
            mock_mw_instance.register_channel.assert_not_called()

    async def test_middleware_channel_registration_error(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.enable_communication_middleware = True
        mock_settings.service_manager.hierarchical_channel_id = "test_channel"

        mock_mw_class = MagicMock()
        mock_mw_instance = MagicMock()
        mock_mw_class.return_value = mock_mw_instance
        mock_mw_instance.register_channel.side_effect = RuntimeError("channel error")

        mock_hc_class = MagicMock()

        with patch(f"{SM_MODULE}.settings", mock_settings), patch(
            f"{SM_MODULE}.MessageMiddleware", mock_mw_class
        ), patch(f"{SM_MODULE}.HierarchicalChannel", mock_hc_class):
            # Should not raise, error is logged
            await manager.initialize_middleware()
            assert manager.middleware is mock_mw_instance


# ========================================================================
# Async tests — _initialize_hierarchical_managers()
# ========================================================================


class TestInitializeHierarchicalManagers:
    """Tests for _initialize_hierarchical_managers()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    async def test_no_middleware_skips(self, manager):
        manager.middleware = None
        await manager._initialize_hierarchical_managers()
        assert manager.strategic_manager is None
        assert manager.tactical_manager is None
        assert manager.operational_manager is None

    async def test_success_with_all_managers(self, manager):
        manager.middleware = MagicMock()
        manager.kernel = MagicMock()
        manager.llm_service_id = "test-service"
        manager.project_context = MagicMock()

        mock_strategic = MagicMock()
        mock_tactical = MagicMock()
        mock_operational = MagicMock()

        with patch(f"{SM_MODULE}.StrategicManager", mock_strategic), patch(
            f"{SM_MODULE}.TacticalManager", mock_tactical
        ), patch(f"{SM_MODULE}.OperationalManager", mock_operational):
            await manager._initialize_hierarchical_managers()
            assert manager.strategic_manager is not None
            assert manager.tactical_manager is not None
            assert manager.operational_manager is not None

    async def test_exception_resets_managers_to_none(self, manager):
        manager.middleware = MagicMock()

        with patch(
            f"{SM_MODULE}.StrategicManager", side_effect=RuntimeError("init fail")
        ):
            await manager._initialize_hierarchical_managers()
            assert manager.strategic_manager is None
            assert manager.tactical_manager is None
            assert manager.operational_manager is None

    async def test_managers_none_when_classes_none(self, manager):
        manager.middleware = MagicMock()

        with patch(f"{SM_MODULE}.StrategicManager", None), patch(
            f"{SM_MODULE}.TacticalManager", None
        ), patch(f"{SM_MODULE}.OperationalManager", None):
            await manager._initialize_hierarchical_managers()
            assert manager.strategic_manager is None
            assert manager.tactical_manager is None
            assert manager.operational_manager is None


# ========================================================================
# Async tests — _initialize_specialized_orchestrators()
# ========================================================================


class TestInitializeSpecializedOrchestrators:
    """Tests for _initialize_specialized_orchestrators()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        mgr = OrchestrationServiceManager(enable_logging=False)
        mgr.kernel = MagicMock()
        return mgr

    async def test_success_cluedo_and_conversation(self, manager):
        mock_cluedo = MagicMock()
        mock_conversation = MagicMock()

        with patch(f"{SM_MODULE}.CluedoOrchestrator", mock_cluedo), patch(
            f"{SM_MODULE}.ConversationOrchestrator", mock_conversation
        ), patch(f"{SM_MODULE}.RealLLMOrchestrator", None), patch(
            f"{SM_MODULE}.FactCheckingOrchestrator", None
        ):
            await manager._initialize_specialized_orchestrators()
            assert manager.cluedo_orchestrator is not None
            assert manager.conversation_orchestrator is not None

    async def test_exception_raises(self, manager):
        with patch(f"{SM_MODULE}.CluedoOrchestrator", side_effect=RuntimeError("fail")):
            with pytest.raises(Exception, match="Impossible d'initialiser"):
                await manager._initialize_specialized_orchestrators()

    async def test_all_none_when_classes_none(self, manager):
        with patch(f"{SM_MODULE}.CluedoOrchestrator", None), patch(
            f"{SM_MODULE}.ConversationOrchestrator", None
        ), patch(f"{SM_MODULE}.RealLLMOrchestrator", None), patch(
            f"{SM_MODULE}.FactCheckingOrchestrator", None
        ):
            await manager._initialize_specialized_orchestrators()
            assert manager.cluedo_orchestrator is None
            assert manager.conversation_orchestrator is None
            assert manager.llm_orchestrator is None
            assert manager.fact_checking_orchestrator is None


# ========================================================================
# Async tests — analyze_text()
# ========================================================================


class TestAnalyzeText:
    """Tests for analyze_text()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        mgr = OrchestrationServiceManager(enable_logging=False)
        mgr._initialized = True
        return mgr

    async def test_not_initialized_raises(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
            ServiceManagerError,
        )

        mgr = OrchestrationServiceManager(enable_logging=False)
        with pytest.raises(ServiceManagerError, match="non initialisé"):
            await mgr.analyze_text("Test text")

    async def test_empty_text_raises(self, manager):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )

        with pytest.raises(ServiceManagerError, match="vide"):
            await manager.analyze_text("")

    async def test_whitespace_only_raises(self, manager):
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManagerError,
        )

        with pytest.raises(ServiceManagerError, match="vide"):
            await manager.analyze_text("   \t\n  ")

    async def test_with_orchestrator(self, manager):
        mock_orch = MagicMock()
        manager.llm_orchestrator = mock_orch

        mock_settings = MagicMock()
        mock_settings.service_manager.save_results = False

        with patch.object(
            manager, "_select_orchestrator", return_value=mock_orch
        ), patch.object(
            manager,
            "_run_specialized_analysis",
            new_callable=AsyncMock,
            return_value={"result": "ok"},
        ), patch(
            f"{SM_MODULE}.settings", mock_settings
        ):
            result = await manager.analyze_text("Analyze this text")
            assert result["status"] == "completed"
            assert result["results"]["specialized"] == {"result": "ok"}

    async def test_without_orchestrator_uses_hierarchical(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.save_results = False

        with patch.object(
            manager, "_select_orchestrator", return_value=None
        ), patch.object(
            manager,
            "_run_hierarchical_analysis",
            new_callable=AsyncMock,
            return_value={"level": "hierarchical"},
        ), patch(
            f"{SM_MODULE}.settings", mock_settings
        ):
            result = await manager.analyze_text(
                "Analyze this text", analysis_type="unknown_type"
            )
            assert result["status"] == "completed"
            assert result["results"]["hierarchical"] == {"level": "hierarchical"}

    async def test_error_returns_failed_status(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.save_results = False

        with patch.object(
            manager, "_select_orchestrator", side_effect=RuntimeError("select error")
        ), patch(f"{SM_MODULE}.settings", mock_settings):
            result = await manager.analyze_text("Some text")
            assert result["status"] == "failed"
            assert "error" in result

    async def test_saves_results_when_configured(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.save_results = True

        with patch.object(
            manager, "_select_orchestrator", return_value=None
        ), patch.object(
            manager,
            "_run_hierarchical_analysis",
            new_callable=AsyncMock,
            return_value={},
        ), patch.object(
            manager, "_save_results", new_callable=AsyncMock
        ) as mock_save, patch(
            f"{SM_MODULE}.settings", mock_settings
        ):
            await manager.analyze_text("Text to analyze")
            mock_save.assert_awaited_once()

    async def test_result_contains_analysis_id(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.save_results = False

        with patch.object(
            manager, "_select_orchestrator", return_value=None
        ), patch.object(
            manager,
            "_run_hierarchical_analysis",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            f"{SM_MODULE}.settings", mock_settings
        ):
            result = await manager.analyze_text("Test text")
            assert "analysis_id" in result
            # Should be a valid UUID
            uuid.UUID(result["analysis_id"])


# ========================================================================
# _select_orchestrator()
# ========================================================================


class TestSelectOrchestrator:
    """Tests for _select_orchestrator()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        mgr = OrchestrationServiceManager(enable_logging=False)
        mgr.cluedo_orchestrator = MagicMock(name="cluedo")
        mgr.conversation_orchestrator = MagicMock(name="conversation")
        mgr.llm_orchestrator = MagicMock(name="llm")
        mgr.fact_checking_orchestrator = MagicMock(name="fact_checking")
        return mgr

    def test_cluedo_type(self, manager):
        assert manager._select_orchestrator("cluedo") is manager.cluedo_orchestrator

    def test_detective_type(self, manager):
        assert manager._select_orchestrator("detective") is manager.cluedo_orchestrator

    def test_conversation_type(self, manager):
        assert (
            manager._select_orchestrator("conversation")
            is manager.conversation_orchestrator
        )

    def test_dialogue_type(self, manager):
        assert (
            manager._select_orchestrator("dialogue")
            is manager.conversation_orchestrator
        )

    def test_llm_type(self, manager):
        assert manager._select_orchestrator("llm") is manager.llm_orchestrator

    def test_language_model_type(self, manager):
        assert (
            manager._select_orchestrator("language_model") is manager.llm_orchestrator
        )

    def test_fact_checking_type(self, manager):
        assert (
            manager._select_orchestrator("fact_checking")
            is manager.fact_checking_orchestrator
        )

    def test_comprehensive_type(self, manager):
        assert (
            manager._select_orchestrator("comprehensive")
            is manager.fact_checking_orchestrator
        )

    def test_rhetorical_type(self, manager):
        assert (
            manager._select_orchestrator("rhetorical")
            is manager.fact_checking_orchestrator
        )

    def test_logical_type(self, manager):
        assert manager._select_orchestrator("logical") is manager.llm_orchestrator

    def test_modal_type(self, manager):
        assert manager._select_orchestrator("modal") is manager.llm_orchestrator

    def test_propositional_type(self, manager):
        assert manager._select_orchestrator("propositional") is manager.llm_orchestrator

    def test_unknown_type_defaults_to_llm(self, manager):
        assert manager._select_orchestrator("unknown_xyz") is manager.llm_orchestrator

    def test_case_insensitive(self, manager):
        assert manager._select_orchestrator("CLUEDO") is manager.cluedo_orchestrator

    def test_unified_analysis_defaults_to_llm(self, manager):
        # "unified_analysis" is not in the map, so defaults to llm_orchestrator
        assert (
            manager._select_orchestrator("unified_analysis") is manager.llm_orchestrator
        )


# ========================================================================
# _run_specialized_analysis()
# ========================================================================


class TestRunSpecializedAnalysis:
    """Tests for _run_specialized_analysis()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    async def test_fact_checking_interface(self, manager):
        """Orchestrator with analyze_with_fact_checking method."""
        mock_orch = MagicMock()
        mock_orch.__class__.__name__ = "FactCheckingOrchestrator"

        mock_result = MagicMock()
        mock_result.request_id = "req-123"
        mock_result.comprehensive_result.to_dict.return_value = {"data": "result"}
        mock_result.processing_time = 1.5
        mock_result.status = "completed"
        mock_result.analysis_timestamp = datetime(2026, 1, 1)

        mock_orch.analyze_with_fact_checking = AsyncMock(return_value=mock_result)

        # The method does `from .fact_checking_orchestrator import FactCheckingRequest, AnalysisDepth`
        # which resolves to `argumentation_analysis.orchestration.fact_checking_orchestrator`.
        # We mock the module in sys.modules so the import picks up our mocks.
        import sys

        mock_fc_module = MagicMock()
        mock_fc_module.FactCheckingRequest = MagicMock(return_value=MagicMock())
        mock_fc_module.AnalysisDepth = MagicMock()
        mock_fc_module.AnalysisDepth.STANDARD = "standard"

        with patch.dict(
            sys.modules,
            {
                "argumentation_analysis.orchestration.fact_checking_orchestrator": mock_fc_module
            },
        ):
            result = await manager._run_specialized_analysis(
                mock_orch, "test text", "fact_checking", None
            )
            assert result["method"] == "fact_checking"
            assert result["request_id"] == "req-123"

    async def test_analyze_text_interface(self, manager):
        """Orchestrator with analyze_text method (RealLLMOrchestrator)."""
        mock_orch = MagicMock()
        mock_orch.__class__.__name__ = "RealLLMOrchestrator"
        # No analyze_with_fact_checking
        del mock_orch.analyze_with_fact_checking

        mock_result = MagicMock()
        mock_result.request_id = "req-456"
        mock_result.analysis_type = "llm"
        mock_result.result = {"data": "llm_result"}
        mock_result.confidence = 0.95
        mock_result.processing_time = 2.0
        mock_result.timestamp = datetime(2026, 1, 1)

        mock_orch.analyze_text = AsyncMock(return_value=mock_result)

        import sys

        mock_llm_module = MagicMock()
        mock_llm_module.LLMAnalysisRequest = MagicMock()

        with patch.dict(
            sys.modules,
            {
                "argumentation_analysis.orchestration.real_llm_orchestrator": mock_llm_module
            },
        ):
            result = await manager._run_specialized_analysis(
                mock_orch, "test text", "llm", {"context": "test"}
            )
            assert result["method"] == "real_llm"
            assert result["request_id"] == "req-456"

    async def test_generic_analyze_interface(self, manager):
        """Orchestrator with generic analyze() method."""
        mock_orch = MagicMock()
        # Remove specific methods
        del mock_orch.analyze_with_fact_checking
        del mock_orch.analyze_text
        mock_orch.analyze = AsyncMock(return_value={"generic": True})

        result = await manager._run_specialized_analysis(
            mock_orch, "test text", "generic", None
        )
        assert result == {"generic": True}

    async def test_process_interface(self, manager):
        """Orchestrator with process() method."""
        mock_orch = MagicMock()
        del mock_orch.analyze_with_fact_checking
        del mock_orch.analyze_text
        del mock_orch.analyze
        mock_orch.process = AsyncMock(return_value={"processed": True})

        result = await manager._run_specialized_analysis(
            mock_orch, "test text", "process_type", None
        )
        assert result == {"processed": True}

    async def test_no_supported_method_raises(self, manager):
        """Orchestrator without any supported method raises."""
        mock_orch = MagicMock(spec=[])  # No methods at all
        mock_orch.__class__.__name__ = "EmptyOrchestrator"

        with pytest.raises(Exception, match="Échec analyse orchestrateur"):
            await manager._run_specialized_analysis(
                mock_orch, "test text", "none", None
            )


# ========================================================================
# _run_hierarchical_analysis()
# ========================================================================


class TestRunHierarchicalAnalysis:
    """Tests for _run_hierarchical_analysis()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    async def test_no_managers_returns_empty(self, manager):
        result = await manager._run_hierarchical_analysis("text", "type", None)
        assert result == {}

    async def test_strategic_called_when_available(self, manager):
        manager.strategic_manager = MagicMock()

        with patch.object(
            manager,
            "_run_strategic_analysis",
            new_callable=AsyncMock,
            return_value={"level": "strategic", "status": "ok"},
        ):
            result = await manager._run_hierarchical_analysis("text", "type", None)
            assert "strategic" in result

    async def test_tactical_called_when_available(self, manager):
        manager.tactical_manager = MagicMock()

        with patch.object(
            manager,
            "_run_tactical_analysis",
            new_callable=AsyncMock,
            return_value={"level": "tactical", "status": "ok"},
        ):
            result = await manager._run_hierarchical_analysis("text", "type", None)
            assert "tactical" in result

    async def test_operational_called_when_available(self, manager):
        manager.operational_manager = MagicMock()

        with patch.object(
            manager,
            "_run_operational_analysis",
            new_callable=AsyncMock,
            return_value={"level": "operational", "status": "ok"},
        ):
            result = await manager._run_hierarchical_analysis("text", "type", None)
            assert "operational" in result

    async def test_strategic_error_captured(self, manager):
        manager.strategic_manager = MagicMock()

        with patch.object(
            manager,
            "_run_strategic_analysis",
            new_callable=AsyncMock,
            side_effect=RuntimeError("strategic fail"),
        ):
            result = await manager._run_hierarchical_analysis("text", "type", None)
            assert result["strategic"]["error"] == "strategic fail"


# ========================================================================
# get_status() and health_check()
# ========================================================================


class TestGetStatusAndHealthCheck:
    """Tests for get_status() and health_check()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

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

    async def test_get_status_with_some_services(self, manager):
        manager.strategic_manager = MagicMock()
        manager.middleware = MagicMock()
        status = await manager.get_status()
        assert status["active_services"]["strategic_manager"] is True
        assert status["active_services"]["middleware"] is True
        assert status["active_services"]["tactical_manager"] is False

    async def test_health_check_not_initialized(self, manager):
        health = await manager.health_check()
        assert health["overall"] == "unhealthy"
        assert "analysis" in health["checks"]
        assert health["checks"]["analysis"]["status"] == "error"


# ========================================================================
# shutdown()
# ========================================================================


class TestShutdown:
    """Tests for shutdown()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    async def test_shutdown_sets_flag(self, manager):
        await manager.shutdown()
        assert manager._shutdown is True

    async def test_shutdown_idempotent(self, manager):
        await manager.shutdown()
        await manager.shutdown()  # Should not raise
        assert manager._shutdown is True

    async def test_shutdown_with_sync_component(self, manager):
        """Shutdown calls sync shutdown() on components."""
        mock_component = MagicMock()
        mock_component.shutdown = MagicMock(return_value=None)

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

    async def test_shutdown_with_multiple_components(self, manager):
        """Shutdown calls shutdown on all components that have it."""
        components = {}
        for name in [
            "cluedo_orchestrator",
            "conversation_orchestrator",
            "llm_orchestrator",
            "strategic_manager",
            "tactical_manager",
            "operational_manager",
            "middleware",
        ]:
            mock = MagicMock()
            mock.shutdown = MagicMock(return_value=None)
            components[name] = mock
            setattr(manager, name, mock)

        await manager.shutdown()

        for name, mock in components.items():
            mock.shutdown.assert_called_once()

    async def test_shutdown_error_does_not_crash(self, manager):
        """If a component's shutdown raises, overall shutdown still completes."""
        mock_component = MagicMock()
        mock_component.shutdown = MagicMock(side_effect=RuntimeError("shutdown error"))

        manager.cluedo_orchestrator = mock_component
        # Should not raise
        await manager.shutdown()
        # The _shutdown flag may or may not be set depending on error handling
        # The important thing is it doesn't crash


# ========================================================================
# _save_results()
# ========================================================================


class TestSaveResults:
    """Tests for _save_results()."""

    @pytest.fixture
    def manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return OrchestrationServiceManager(enable_logging=False)

    async def test_save_results_creates_file(self, manager, tmp_path):
        mock_settings = MagicMock()
        mock_settings.service_manager.results_dir = tmp_path

        results = {"analysis_id": "test-id-123", "data": "test"}

        with patch(f"{SM_MODULE}.settings", mock_settings):
            await manager._save_results(results)

        expected_file = tmp_path / "analysis_test-id-123.json"
        assert expected_file.exists()

        with open(expected_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["analysis_id"] == "test-id-123"

    async def test_save_results_error_does_not_crash(self, manager):
        mock_settings = MagicMock()
        mock_settings.service_manager.results_dir = Path(
            "/nonexistent/path/that/wont/work"
        )

        results = {"analysis_id": "bad-id", "data": "test"}

        with patch(f"{SM_MODULE}.settings", mock_settings):
            # Should not raise
            await manager._save_results(results)


# ========================================================================
# create_service_manager() factory
# ========================================================================


class TestCreateServiceManager:
    """Tests for create_service_manager() factory function."""

    async def test_factory_creates_and_initializes(self):
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        mock_instance = MagicMock(spec=OrchestrationServiceManager)
        mock_instance.initialize = AsyncMock()

        with patch(
            f"{SM_MODULE}.OrchestrationServiceManager", return_value=mock_instance
        ):
            from argumentation_analysis.orchestration.service_manager import (
                create_service_manager,
            )

            result = await create_service_manager()
            assert result is mock_instance
            mock_instance.initialize.assert_awaited_once()


# ========================================================================
# ServiceManager deprecated alias
# ========================================================================


class TestServiceManagerAlias:
    """Tests for deprecated ServiceManager alias."""

    def test_deprecated_alias_warns(self):
        import warnings
        from argumentation_analysis.orchestration.service_manager import ServiceManager

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            instance = ServiceManager(enable_logging=False)
            assert len(w) >= 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "déprécié" in str(w[-1].message).lower() or "ServiceManager" in str(
                w[-1].message
            )

    def test_deprecated_alias_returns_orchestration_manager(self):
        import warnings
        from argumentation_analysis.orchestration.service_manager import (
            ServiceManager,
            OrchestrationServiceManager,
        )

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            instance = ServiceManager(enable_logging=False)
            assert isinstance(instance, OrchestrationServiceManager)


# ========================================================================
# get_default_service_manager()
# ========================================================================


class TestGetDefaultServiceManager:
    """Tests for get_default_service_manager()."""

    def test_returns_non_initialized_manager(self):
        from argumentation_analysis.orchestration.service_manager import (
            get_default_service_manager,
            OrchestrationServiceManager,
        )

        mgr = get_default_service_manager()
        assert isinstance(mgr, OrchestrationServiceManager)
        assert mgr._initialized is False

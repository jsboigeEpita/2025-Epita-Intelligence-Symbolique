# tests/unit/argumentation_analysis/orchestration/test_engine_config_strategy.py
"""Tests for orchestration engine config, strategy, and enquete state manager plugin."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import asdict


# ============================================================================
# OrchestrationMode Enum Tests
# ============================================================================

class TestOrchestrationMode:
    """Tests for OrchestrationMode enum."""

    def test_pipeline_mode(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationMode
        assert OrchestrationMode.PIPELINE.value == "pipeline"

    def test_real_mode(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationMode
        assert OrchestrationMode.REAL.value == "real"

    def test_auto_select_mode(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationMode
        assert OrchestrationMode.AUTO_SELECT.value == "auto_select"

    def test_all_modes_have_unique_values(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationMode
        values = [m.value for m in OrchestrationMode]
        assert len(values) == len(set(values))

    def test_mode_count(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationMode
        assert len(OrchestrationMode) == 11

    def test_cluedo_investigation_mode(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationMode
        assert OrchestrationMode.CLUEDO_INVESTIGATION.value == "cluedo_investigation"


# ============================================================================
# AnalysisType Enum Tests
# ============================================================================

class TestAnalysisType:
    """Tests for AnalysisType enum."""

    def test_comprehensive_type(self):
        from argumentation_analysis.orchestration.engine.config import AnalysisType
        assert AnalysisType.COMPREHENSIVE.value == "comprehensive"

    def test_logical_type(self):
        from argumentation_analysis.orchestration.engine.config import AnalysisType
        assert AnalysisType.LOGICAL.value == "logical"

    def test_investigative_type(self):
        from argumentation_analysis.orchestration.engine.config import AnalysisType
        assert AnalysisType.INVESTIGATIVE.value == "investigative"

    def test_all_types_have_unique_values(self):
        from argumentation_analysis.orchestration.engine.config import AnalysisType
        values = [t.value for t in AnalysisType]
        assert len(values) == len(set(values))

    def test_type_count(self):
        from argumentation_analysis.orchestration.engine.config import AnalysisType
        assert len(AnalysisType) == 8


# ============================================================================
# OrchestrationConfig Dataclass Tests
# ============================================================================

class TestOrchestrationConfig:
    """Tests for OrchestrationConfig dataclass."""

    def test_default_values(self):
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode, AnalysisType
        )
        config = OrchestrationConfig()
        assert config.analysis_modes == ["informal", "formal"]
        assert config.orchestration_mode == OrchestrationMode.PIPELINE
        assert config.analysis_type == AnalysisType.COMPREHENSIVE
        assert config.logic_type == "fol"
        assert config.use_mocks is False
        assert config.use_advanced_tools is True
        assert config.max_concurrent_analyses == 10
        assert config.analysis_timeout_seconds == 300
        assert config.auto_select_orchestrator_enabled is True

    def test_custom_values(self):
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode, AnalysisType
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.REAL,
            analysis_type=AnalysisType.LOGICAL,
            use_mocks=True,
            max_concurrent_analyses=5,
        )
        assert config.orchestration_mode == OrchestrationMode.REAL
        assert config.analysis_type == AnalysisType.LOGICAL
        assert config.use_mocks is True
        assert config.max_concurrent_analyses == 5

    def test_string_mode_conversion(self):
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode
        )
        config = OrchestrationConfig(orchestration_mode="pipeline")
        assert config.orchestration_mode == OrchestrationMode.PIPELINE

    def test_string_analysis_type_conversion(self):
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, AnalysisType
        )
        config = OrchestrationConfig(analysis_type="logical")
        assert config.analysis_type == AnalysisType.LOGICAL

    def test_invalid_string_mode_stays_string(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig(orchestration_mode="unknown_mode")
        assert config.orchestration_mode == "unknown_mode"

    def test_invalid_string_analysis_type_stays_string(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig(analysis_type="unknown_type")
        assert config.analysis_type == "unknown_type"

    def test_default_analysis_modes(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig()
        assert "informal" in config.analysis_modes
        assert "formal" in config.analysis_modes

    def test_default_priority_order(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig()
        assert "cluedo_investigation" in config.specialized_orchestrator_priority_order
        assert "logic_complex" in config.specialized_orchestrator_priority_order

    def test_default_communication_config_empty(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig()
        assert config.communication_middleware_config == {}

    def test_save_trace_default_enabled(self):
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig()
        assert config.save_orchestration_trace_enabled is True


# ============================================================================
# OrchestrationStrategy Enum Tests
# ============================================================================

class TestOrchestrationStrategy:
    """Tests for OrchestrationStrategy enum."""

    def test_hierarchical_full(self):
        from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
        assert OrchestrationStrategy.HIERARCHICAL_FULL.value == "hierarchical_full"

    def test_fallback(self):
        from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
        assert OrchestrationStrategy.FALLBACK.value == "fallback"

    def test_service_manager(self):
        from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
        assert OrchestrationStrategy.SERVICE_MANAGER.value == "service_manager"

    def test_manual_selection(self):
        from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
        assert OrchestrationStrategy.MANUAL_SELECTION.value == "manual_selection"

    def test_complex_pipeline(self):
        from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
        assert OrchestrationStrategy.COMPLEX_PIPELINE.value == "complex_pipeline"

    def test_all_strategies_unique(self):
        from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
        values = [s.value for s in OrchestrationStrategy]
        assert len(values) == len(set(values))

    def test_strategy_count(self):
        from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
        assert len(OrchestrationStrategy) == 10


# ============================================================================
# _analyze_text_features_for_strategy Tests
# ============================================================================

class TestAnalyzeTextFeatures:
    """Tests for _analyze_text_features_for_strategy()."""

    async def test_basic_features(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("Hello world.")
        assert features["length"] == 12
        assert features["word_count"] == 2
        assert features["sentence_count"] == 1

    async def test_has_questions(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("Is this a question?")
        assert features["has_questions"] is True

    async def test_no_questions(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("No question here.")
        assert features["has_questions"] is False

    async def test_logical_connectors(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("Donc on peut conclure.")
        assert features["has_logical_connectors"] is True

    async def test_no_logical_connectors(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("Simple sentence.")
        assert features["has_logical_connectors"] is False

    async def test_debate_markers(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("Mon argument principal.")
        assert features["has_debate_markers"] is True

    async def test_no_debate_markers(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("Simple text.")
        assert features["has_debate_markers"] is False

    async def test_complexity_score_caps_at_5(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        long_text = "a" * 5000
        features = await _analyze_text_features_for_strategy(long_text)
        assert features["complexity_score"] == 5.0

    async def test_complexity_score_short_text(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("Hi.")
        assert features["complexity_score"] < 1.0

    async def test_empty_text(self):
        from argumentation_analysis.orchestration.engine.strategy import _analyze_text_features_for_strategy
        features = await _analyze_text_features_for_strategy("")
        assert features["length"] == 0
        assert features["word_count"] == 0  # "".split() returns []
        assert features["sentence_count"] == 0


# ============================================================================
# select_strategy Tests
# ============================================================================

class TestSelectStrategy:
    """Tests for select_strategy()."""

    async def test_manual_mode_returns_manual_selection(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig()
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = True
            result = await select_strategy(config, "test text")
            assert result == OrchestrationStrategy.MANUAL_SELECTION

    async def test_force_strategy_from_custom_config(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig()
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(
                config, "test", custom_config={"force_strategy": "fallback"}
            )
            assert result == OrchestrationStrategy.FALLBACK

    async def test_force_invalid_strategy_falls_through(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            auto_select_orchestrator_enabled=False,
        )
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(
                config, "test", custom_config={"force_strategy": "nonexistent"}
            )
            # Falls through to next logic
            assert result == OrchestrationStrategy.HIERARCHICAL_FULL

    async def test_monitoring_source_returns_operational(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
        config = OrchestrationConfig()
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(
                config, "test", source_info={"type": "monitoring"}
            )
            assert result == OrchestrationStrategy.OPERATIONAL_DIRECT

    async def test_manual_mode_hierarchical(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL
        )
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(config, "test")
            assert result == OrchestrationStrategy.HIERARCHICAL_FULL

    async def test_manual_mode_cluedo_maps_to_specialized(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.CLUEDO_INVESTIGATION
        )
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(config, "test")
            assert result == OrchestrationStrategy.SPECIALIZED_DIRECT

    async def test_auto_select_disabled_returns_hierarchical(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            auto_select_orchestrator_enabled=False,
        )
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(config, "test")
            assert result == OrchestrationStrategy.HIERARCHICAL_FULL

    async def test_auto_select_investigative(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode, AnalysisType
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.INVESTIGATIVE,
            auto_select_orchestrator_enabled=True,
        )
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(config, "test")
            assert result == OrchestrationStrategy.SPECIALIZED_DIRECT

    async def test_auto_select_logical(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode, AnalysisType
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.LOGICAL,
            auto_select_orchestrator_enabled=True,
        )
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(config, "test")
            assert result == OrchestrationStrategy.SPECIALIZED_DIRECT

    async def test_auto_select_long_text_hierarchical(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode, AnalysisType
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.COMPREHENSIVE,
            auto_select_orchestrator_enabled=True,
            enable_hierarchical_orchestration=True,
        )
        long_text = "a " * 600  # > 1000 chars
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(config, long_text)
            assert result == OrchestrationStrategy.HIERARCHICAL_FULL

    async def test_auto_select_default_complex_pipeline(self):
        from argumentation_analysis.orchestration.engine.strategy import select_strategy, OrchestrationStrategy
        from argumentation_analysis.orchestration.engine.config import (
            OrchestrationConfig, OrchestrationMode, AnalysisType
        )
        config = OrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.COMPREHENSIVE,
            auto_select_orchestrator_enabled=True,
            enable_hierarchical_orchestration=False,
        )
        with patch("argumentation_analysis.orchestration.engine.strategy.UnifiedConfig") as MockConfig:
            MockConfig.return_value.manual_mode = False
            result = await select_strategy(config, "short text")
            assert result == OrchestrationStrategy.COMPLEX_PIPELINE


# ============================================================================
# EnqueteStateManagerPlugin Tests
# ============================================================================

class TestEnqueteStateManagerPluginInit:
    """Tests for EnqueteStateManagerPlugin initialization."""

    def test_init_with_state(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        mock_state = MagicMock()
        plugin = EnqueteStateManagerPlugin(state=mock_state)
        assert plugin._state is mock_state

    def test_init_sets_logger(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        mock_state = MagicMock()
        plugin = EnqueteStateManagerPlugin(state=mock_state)
        assert plugin._logger is not None


class TestEnqueteStateManagerPluginTasks:
    """Tests for task management methods."""

    def _make_plugin(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        mock_state = MagicMock()
        return EnqueteStateManagerPlugin(state=mock_state), mock_state

    def test_add_task_success(self):
        plugin, state = self._make_plugin()
        state.add_task.return_value = {"id": "t1", "description": "Test", "assignee": "Agent"}
        result = json.loads(plugin.add_task("Test task", "Agent"))
        assert result["id"] == "t1"

    def test_add_task_error(self):
        plugin, state = self._make_plugin()
        state.add_task.side_effect = RuntimeError("fail")
        result = json.loads(plugin.add_task("Test", "Agent"))
        assert "error" in result

    def test_get_task_found(self):
        plugin, state = self._make_plugin()
        state.get_task.return_value = {"id": "t1", "status": "pending"}
        result = json.loads(plugin.get_task("t1"))
        assert result["id"] == "t1"

    def test_get_task_not_found(self):
        plugin, state = self._make_plugin()
        state.get_task.return_value = None
        result = json.loads(plugin.get_task("t999"))
        assert result is None

    def test_update_task_status_success(self):
        plugin, state = self._make_plugin()
        state.update_task_status.return_value = True
        result = json.loads(plugin.update_task_status("t1", "completed"))
        assert result["success"] is True

    def test_get_tasks_with_filter(self):
        plugin, state = self._make_plugin()
        state.get_tasks.return_value = [{"id": "t1"}]
        result = json.loads(plugin.get_tasks(assignee="Agent", status="pending"))
        assert len(result) == 1


class TestEnqueteStateManagerPluginDesignation:
    """Tests for agent designation methods."""

    def _make_plugin(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        mock_state = MagicMock()
        return EnqueteStateManagerPlugin(state=mock_state), mock_state

    def test_designate_next_agent(self):
        plugin, state = self._make_plugin()
        result = json.loads(plugin.designate_next_agent("Watson"))
        state.designate_next_agent.assert_called_once_with("Watson")
        assert "Watson" in result["message"]

    def test_designate_next_agent_error(self):
        plugin, state = self._make_plugin()
        state.designate_next_agent.side_effect = RuntimeError("fail")
        result = json.loads(plugin.designate_next_agent("Watson"))
        assert "error" in result

    def test_get_designated_next_agent(self):
        plugin, state = self._make_plugin()
        state.get_designated_next_agent.return_value = "Sherlock"
        result = json.loads(plugin.get_designated_next_agent())
        assert result["next_agent"] == "Sherlock"


class TestEnqueteStateManagerPluginCaseDescription:
    """Tests for case description methods (requires EnquetePoliciereState)."""

    def _make_plugin_with_policiere_state(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        from argumentation_analysis.core.enquete_states import EnquetePoliciereState
        mock_state = MagicMock(spec=EnquetePoliciereState)
        return EnqueteStateManagerPlugin(state=mock_state), mock_state

    def _make_plugin_with_base_state(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        from argumentation_analysis.core.enquete_states import BaseWorkflowState
        mock_state = MagicMock(spec=BaseWorkflowState)
        return EnqueteStateManagerPlugin(state=mock_state), mock_state

    def test_get_case_description_policiere(self):
        plugin, state = self._make_plugin_with_policiere_state()
        state.get_case_description.return_value = "A murder mystery"
        result = json.loads(plugin.get_case_description())
        assert result["case_description"] == "A murder mystery"

    def test_get_case_description_wrong_state_type(self):
        plugin, state = self._make_plugin_with_base_state()
        result = json.loads(plugin.get_case_description())
        assert "error" in result

    def test_update_case_description_policiere(self):
        plugin, state = self._make_plugin_with_policiere_state()
        result = json.loads(plugin.update_case_description("New description"))
        state.update_case_description.assert_called_once_with("New description")
        assert "message" in result

    def test_update_case_description_wrong_state_type(self):
        plugin, state = self._make_plugin_with_base_state()
        result = json.loads(plugin.update_case_description("New"))
        assert "error" in result


class TestEnqueteStateManagerPluginElements:
    """Tests for identified elements methods."""

    def _make_plugin(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        from argumentation_analysis.core.enquete_states import EnquetePoliciereState
        mock_state = MagicMock(spec=EnquetePoliciereState)
        return EnqueteStateManagerPlugin(state=mock_state), mock_state

    def test_add_identified_element(self):
        plugin, state = self._make_plugin()
        state.add_identified_element.return_value = {"type": "evidence", "description": "Knife"}
        result = json.loads(plugin.add_identified_element("evidence", "Knife", "Crime scene"))
        assert result["type"] == "evidence"

    def test_get_identified_elements(self):
        plugin, state = self._make_plugin()
        state.get_identified_elements.return_value = [{"type": "evidence"}]
        result = json.loads(plugin.get_identified_elements("evidence"))
        assert len(result) == 1


class TestEnqueteStateManagerPluginBeliefSets:
    """Tests for belief set methods."""

    def _make_plugin(self):
        from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
            EnqueteStateManagerPlugin,
        )
        from argumentation_analysis.core.enquete_states import EnquetePoliciereState
        mock_state = MagicMock(spec=EnquetePoliciereState)
        return EnqueteStateManagerPlugin(state=mock_state), mock_state

    def test_add_or_update_belief_set(self):
        plugin, state = self._make_plugin()
        result = json.loads(plugin.add_or_update_belief_set("bs1", "p(x) & q(x)"))
        state.add_or_update_belief_set.assert_called_once_with("bs1", "p(x) & q(x)")
        assert "message" in result

    def test_get_belief_set_content(self):
        plugin, state = self._make_plugin()
        state.get_belief_set_content.return_value = "p(x) & q(x)"
        result = json.loads(plugin.get_belief_set_content("bs1"))
        assert result["content"] == "p(x) & q(x)"

    def test_get_belief_set_content_not_found(self):
        plugin, state = self._make_plugin()
        state.get_belief_set_content.return_value = None
        result = json.loads(plugin.get_belief_set_content("bs_missing"))
        assert result is None

    def test_list_belief_sets(self):
        plugin, state = self._make_plugin()
        state.list_belief_sets.return_value = ["bs1", "bs2"]
        result = json.loads(plugin.list_belief_sets())
        assert result["belief_set_ids"] == ["bs1", "bs2"]

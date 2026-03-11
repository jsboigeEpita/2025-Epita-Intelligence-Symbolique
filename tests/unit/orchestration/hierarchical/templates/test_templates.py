# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.templates
Covers BaseAgent (agent_template), BaseOrchestrationStrategy (strategy_template),
BaseAnalysisType (analysis_type_template), BaseAnalysisTool (analysis_tool_template).
"""

import pytest

from argumentation_analysis.orchestration.hierarchical.templates.agent_template import (
    BaseAgent,
    AGENT_CONFIG_EXAMPLE,
)
from argumentation_analysis.orchestration.hierarchical.templates.strategy_template import (
    BaseOrchestrationStrategy,
    STRATEGY_CONFIG_EXAMPLE,
)
from argumentation_analysis.orchestration.hierarchical.templates.analysis_type_template import (
    BaseAnalysisType,
    ANALYSIS_TYPE_CONFIG_EXAMPLE,
)
from argumentation_analysis.orchestration.hierarchical.templates.analysis_tool_template import (
    BaseAnalysisTool,
    ANALYSIS_TOOL_CONFIG_EXAMPLE,
)


# ============================================================
# BaseAgent (agent_template)
# ============================================================

class TestBaseAgent:
    def test_init_with_name(self):
        agent = BaseAgent({"name": "test_agent"})
        assert agent.name == "test_agent"

    def test_init_default_name(self):
        agent = BaseAgent({})
        assert agent.name == "base_agent"

    def test_config_stored(self):
        cfg = {"name": "a", "extra": 42}
        agent = BaseAgent(cfg)
        assert agent.config is cfg

    def test_process_raises(self):
        agent = BaseAgent({})
        with pytest.raises(NotImplementedError):
            agent.process("some input")

    def test_validate_input_default_true(self):
        agent = BaseAgent({})
        assert agent.validate_input("anything") is True

    def test_get_status(self):
        agent = BaseAgent({"name": "my_agent"})
        status = agent.get_status()
        assert status["name"] == "my_agent"
        assert status["status"] == "ready"
        assert status["last_processed"] is None

    def test_config_example_structure(self):
        assert "name" in AGENT_CONFIG_EXAMPLE
        assert "type" in AGENT_CONFIG_EXAMPLE
        assert "capabilities" in AGENT_CONFIG_EXAMPLE


# ============================================================
# BaseOrchestrationStrategy (strategy_template)
# ============================================================

class TestBaseOrchestrationStrategy:
    def test_init_with_name(self):
        s = BaseOrchestrationStrategy({"name": "my_strategy"})
        assert s.name == "my_strategy"

    def test_init_default_name(self):
        s = BaseOrchestrationStrategy({})
        assert s.name == "base_strategy"

    def test_priority_rules(self):
        s = BaseOrchestrationStrategy({"priority_rules": {"a": 1}})
        assert s.priority_rules == {"a": 1}

    def test_plan_execution_raises(self):
        s = BaseOrchestrationStrategy({})
        with pytest.raises(NotImplementedError):
            s.plan_execution([])

    def test_allocate_resources_raises(self):
        s = BaseOrchestrationStrategy({})
        with pytest.raises(NotImplementedError):
            s.allocate_resources([])

    def test_handle_conflicts_default(self):
        s = BaseOrchestrationStrategy({})
        conflicts = ["c1", "c2"]
        results = s.handle_conflicts(conflicts)
        assert len(results) == 2
        assert results[0]["conflict"] == "c1"
        assert results[0]["resolution"] == "default_resolution"

    def test_handle_conflicts_empty(self):
        s = BaseOrchestrationStrategy({})
        assert s.handle_conflicts([]) == []

    def test_get_strategy_status(self):
        s = BaseOrchestrationStrategy({"name": "test"})
        status = s.get_strategy_status()
        assert status["name"] == "test"
        assert status["status"] == "active"
        assert status["current_tasks"] == []

    def test_config_example_structure(self):
        assert "name" in STRATEGY_CONFIG_EXAMPLE
        assert "type" in STRATEGY_CONFIG_EXAMPLE
        assert "priority_rules" in STRATEGY_CONFIG_EXAMPLE


# ============================================================
# BaseAnalysisType (analysis_type_template)
# ============================================================

class TestBaseAnalysisType:
    def test_init_with_name(self):
        t = BaseAnalysisType({"name": "my_analysis"})
        assert t.name == "my_analysis"

    def test_init_default_name(self):
        t = BaseAnalysisType({})
        assert t.name == "base_analysis_type"

    def test_dependencies(self):
        t = BaseAnalysisType({"dependencies": ["dep1", "dep2"]})
        assert t.dependencies == ["dep1", "dep2"]

    def test_dependencies_default_empty(self):
        t = BaseAnalysisType({})
        assert t.dependencies == []

    def test_analyze_raises(self):
        t = BaseAnalysisType({})
        with pytest.raises(NotImplementedError):
            t.analyze("input", {})

    def test_validate_config_valid(self):
        t = BaseAnalysisType({"name": "x", "type": "y", "parameters": {}})
        assert t.validate_configuration() is True

    def test_validate_config_missing_keys(self):
        t = BaseAnalysisType({"name": "x"})
        assert t.validate_configuration() is False

    def test_get_expected_results(self):
        t = BaseAnalysisType({"name": "test_type"})
        results = t.get_expected_results()
        assert results["analysis_type"] == "test_type"

    def test_config_example_structure(self):
        assert "name" in ANALYSIS_TYPE_CONFIG_EXAMPLE
        assert "type" in ANALYSIS_TYPE_CONFIG_EXAMPLE
        assert "parameters" in ANALYSIS_TYPE_CONFIG_EXAMPLE


# ============================================================
# BaseAnalysisTool (analysis_tool_template)
# ============================================================

class TestBaseAnalysisTool:
    def test_init_with_name(self):
        t = BaseAnalysisTool({"name": "my_tool"})
        assert t.name == "my_tool"

    def test_init_default_name(self):
        t = BaseAnalysisTool({})
        assert t.name == "base_analysis_tool"

    def test_config_stored(self):
        cfg = {"name": "t", "extra": True}
        t = BaseAnalysisTool(cfg)
        assert t.config is cfg

    def test_analyze_raises(self):
        t = BaseAnalysisTool({})
        with pytest.raises(NotImplementedError):
            t.analyze("input")

    def test_validate_input_default_true(self):
        t = BaseAnalysisTool({})
        assert t.validate_input("anything") is True

    def test_get_results(self):
        t = BaseAnalysisTool({"name": "my_tool"})
        results = t.get_results()
        assert results["tool"] == "my_tool"
        assert results["status"] == "completed"

    def test_config_example_structure(self):
        assert "name" in ANALYSIS_TOOL_CONFIG_EXAMPLE
        assert "type" in ANALYSIS_TOOL_CONFIG_EXAMPLE
        assert "parameters" in ANALYSIS_TOOL_CONFIG_EXAMPLE

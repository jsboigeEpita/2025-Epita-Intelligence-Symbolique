# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.core.informal.informal_agent_adapter
Covers InformalAgent adapter: init, tools, capabilities, analysis, categorization.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# Patch the SK import so that InformalAnalysisAgent doesn't try to use SK
with patch(
    "argumentation_analysis.agents.core.informal.informal_agent_adapter.InformalAnalysisAgent",
    MagicMock(side_effect=Exception("SK not available")),
):
    from argumentation_analysis.agents.core.informal.informal_agent_adapter import (
        InformalAgent,
    )


# ============================================================
# Initialization
# ============================================================

class TestInformalAgentInit:
    def test_default_init(self):
        agent = InformalAgent()
        assert agent.agent_id == "InformalAgent"
        assert agent.agent_name == "InformalAgent"
        assert agent.tools == {}
        assert agent.strict_validation is False

    def test_custom_agent_id(self):
        agent = InformalAgent(agent_id="custom_id")
        assert agent.agent_id == "custom_id"
        assert agent.agent_name == "custom_id"  # Falls back to agent_id

    def test_custom_agent_name(self):
        agent = InformalAgent(agent_name="custom_name")
        assert agent.agent_name == "custom_name"
        assert agent.agent_id == "custom_name"  # Falls back to agent_name

    def test_both_id_and_name(self):
        agent = InformalAgent(agent_id="my_id", agent_name="my_name")
        assert agent.agent_id == "my_id"
        assert agent.agent_name == "my_name"

    def test_tools_stored(self):
        tools = {"fallacy_detector": MagicMock(), "contextual_analyzer": MagicMock()}
        agent = InformalAgent(tools=tools)
        assert agent.tools == tools

    def test_strict_validation_no_tools_raises(self):
        with pytest.raises(ValueError, match="Aucun outil"):
            InformalAgent(strict_validation=True, tools={})

    def test_strict_validation_with_tools_ok(self):
        agent = InformalAgent(
            strict_validation=True, tools={"fallacy_detector": MagicMock()}
        )
        assert agent.strict_validation is True

    def test_sk_agent_none_when_sk_unavailable(self):
        agent = InformalAgent()
        assert agent._sk_agent is None


# ============================================================
# get_available_tools
# ============================================================

class TestGetAvailableTools:
    def test_empty_tools(self):
        agent = InformalAgent()
        assert agent.get_available_tools() == []

    def test_returns_tool_names(self):
        tools = {"fallacy_detector": MagicMock(), "contextual_analyzer": MagicMock()}
        agent = InformalAgent(tools=tools)
        result = agent.get_available_tools()
        assert set(result) == {"fallacy_detector", "contextual_analyzer"}

    def test_single_tool(self):
        agent = InformalAgent(tools={"severity_evaluator": MagicMock()})
        assert agent.get_available_tools() == ["severity_evaluator"]


# ============================================================
# get_agent_capabilities
# ============================================================

class TestGetAgentCapabilities:
    def test_no_tools_all_false(self):
        agent = InformalAgent()
        caps = agent.get_agent_capabilities()
        assert caps["fallacy_detection"] is False
        assert caps["contextual_analysis"] is False
        assert caps["rhetorical_analysis"] is False
        assert caps["complex_analysis"] is False
        assert caps["severity_evaluation"] is False

    def test_fallacy_detector_present(self):
        agent = InformalAgent(tools={"fallacy_detector": MagicMock()})
        caps = agent.get_agent_capabilities()
        assert caps["fallacy_detection"] is True
        assert caps["contextual_analysis"] is False

    def test_all_tools_present(self):
        tools = {
            "fallacy_detector": MagicMock(),
            "contextual_analyzer": MagicMock(),
            "rhetorical_analyzer": MagicMock(),
            "complex_analyzer": MagicMock(),
            "severity_evaluator": MagicMock(),
        }
        agent = InformalAgent(tools=tools)
        caps = agent.get_agent_capabilities()
        assert all(caps.values())

    def test_returns_dict_with_five_keys(self):
        agent = InformalAgent()
        caps = agent.get_agent_capabilities()
        assert len(caps) == 5
        expected = {
            "fallacy_detection",
            "contextual_analysis",
            "rhetorical_analysis",
            "complex_analysis",
            "severity_evaluation",
        }
        assert set(caps.keys()) == expected


# ============================================================
# _categorize_fallacies (pure logic)
# ============================================================

class TestCategorizeFallacies:
    def test_empty_list(self):
        agent = InformalAgent()
        result = agent._categorize_fallacies([])
        assert all(v == [] for v in result.values())

    def test_ad_hominem_in_relevance(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "ad_hominem"}]
        result = agent._categorize_fallacies(fallacies)
        assert "ad_hominem" in result["RELEVANCE"]

    def test_appel_autorite_in_relevance(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "appel_autorite"}]
        result = agent._categorize_fallacies(fallacies)
        assert "appel_autorite" in result["RELEVANCE"]

    def test_appel_emotion_in_relevance(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "appel_emotion"}]
        result = agent._categorize_fallacies(fallacies)
        assert "appel_emotion" in result["RELEVANCE"]

    def test_generalisation_hative_in_induction(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "generalisation_hative"}]
        result = agent._categorize_fallacies(fallacies)
        assert "generalisation_hative" in result["INDUCTION"]

    def test_pente_glissante_in_causalite(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "pente_glissante"}]
        result = agent._categorize_fallacies(fallacies)
        assert "pente_glissante" in result["CAUSALITE"]

    def test_fausse_cause_in_causalite(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "fausse_cause"}]
        result = agent._categorize_fallacies(fallacies)
        assert "fausse_cause" in result["CAUSALITE"]

    def test_faux_dilemme_in_presupposition(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "faux_dilemme"}]
        result = agent._categorize_fallacies(fallacies)
        assert "faux_dilemme" in result["PRESUPPOSITION"]

    def test_unknown_fallacy_in_autres(self):
        agent = InformalAgent()
        fallacies = [{"fallacy_type": "unknown_type"}]
        result = agent._categorize_fallacies(fallacies)
        assert "unknown_type" in result["AUTRES"]

    def test_missing_fallacy_type_key(self):
        agent = InformalAgent()
        fallacies = [{"name": "something"}]
        result = agent._categorize_fallacies(fallacies)
        # Empty string after .get default goes to AUTRES
        assert "" in result["AUTRES"]

    def test_mixed_categories(self):
        agent = InformalAgent()
        fallacies = [
            {"fallacy_type": "ad_hominem"},
            {"fallacy_type": "pente_glissante"},
            {"fallacy_type": "faux_dilemme"},
        ]
        result = agent._categorize_fallacies(fallacies)
        assert "ad_hominem" in result["RELEVANCE"]
        assert "pente_glissante" in result["CAUSALITE"]
        assert "faux_dilemme" in result["PRESUPPOSITION"]

    def test_no_duplicate_in_category(self):
        agent = InformalAgent()
        fallacies = [
            {"fallacy_type": "ad_hominem"},
            {"fallacy_type": "ad_hominem"},
        ]
        result = agent._categorize_fallacies(fallacies)
        assert result["RELEVANCE"].count("ad_hominem") == 1

    def test_all_six_categories_present(self):
        agent = InformalAgent()
        result = agent._categorize_fallacies([])
        expected = {"RELEVANCE", "INDUCTION", "CAUSALITE", "AMBIGUITE", "PRESUPPOSITION", "AUTRES"}
        assert set(result.keys()) == expected

    def test_case_normalization(self):
        agent = InformalAgent()
        # The adapter lowercases and replaces spaces with underscores
        fallacies = [{"fallacy_type": "Ad Hominem"}]
        result = agent._categorize_fallacies(fallacies)
        assert "ad_hominem" in result["RELEVANCE"]


# ============================================================
# analyze_text (degraded mode — no SK agent)
# ============================================================

class TestAnalyzeText:
    def test_basic_result_structure(self):
        agent = InformalAgent()
        result = agent.analyze_text("Some argument text")
        assert "fallacies" in result
        assert "analysis_timestamp" in result

    def test_no_tools_empty_fallacies(self):
        agent = InformalAgent()
        result = agent.analyze_text("text")
        assert result["fallacies"] == []

    def test_with_fallacy_detector_detect_method(self):
        detector = MagicMock()
        detector.detect.return_value = [{"fallacy_type": "ad_hominem", "confidence": 0.9}]
        agent = InformalAgent(tools={"fallacy_detector": detector})
        result = agent.analyze_text("Tu as tort car tu es bête")
        assert len(result["fallacies"]) == 1
        assert result["fallacies"][0]["fallacy_type"] == "ad_hominem"

    def test_with_fallacy_detector_no_detect_method(self):
        detector = MagicMock(spec=[])  # No methods
        detector.return_value = [{"fallacy_type": "test"}]
        agent = InformalAgent(tools={"fallacy_detector": detector})
        result = agent.analyze_text("text")
        # Falls back to getattr(detector, 'return_value', [])
        assert isinstance(result["fallacies"], list)

    def test_context_included_when_provided(self):
        agent = InformalAgent()
        result = agent.analyze_text("text", context="political debate")
        assert result["context"] == "political debate"

    def test_no_context_key_when_none(self):
        agent = InformalAgent()
        result = agent.analyze_text("text")
        assert "context" not in result

    def test_timestamp_is_iso_format(self):
        agent = InformalAgent()
        result = agent.analyze_text("text")
        ts = result["analysis_timestamp"]
        # Should be parseable as ISO datetime
        datetime.fromisoformat(ts)


# ============================================================
# perform_complete_analysis
# ============================================================

class TestPerformCompleteAnalysis:
    def test_basic_structure(self):
        agent = InformalAgent()
        result = agent.perform_complete_analysis("Some text")
        assert "fallacies" in result
        assert "contextual_analysis" in result
        assert "categories" in result

    def test_no_tools_empty_contextual(self):
        agent = InformalAgent()
        result = agent.perform_complete_analysis("text", context="debate")
        assert result["contextual_analysis"] == {}

    def test_with_contextual_analyzer(self):
        ctx_analyzer = MagicMock()
        ctx_analyzer.analyze_context.return_value = {"context_type": "political"}
        agent = InformalAgent(
            tools={"contextual_analyzer": ctx_analyzer}
        )
        result = agent.perform_complete_analysis("text", context="debate")
        assert result["contextual_analysis"] == {"context_type": "political"}

    def test_contextual_analyzer_error_handled(self):
        ctx_analyzer = MagicMock()
        ctx_analyzer.analyze_context.side_effect = RuntimeError("fail")
        agent = InformalAgent(tools={"contextual_analyzer": ctx_analyzer})
        result = agent.perform_complete_analysis("text", context="debate")
        assert result["contextual_analysis"] == {}

    def test_categories_empty_when_no_fallacies(self):
        agent = InformalAgent()
        result = agent.perform_complete_analysis("text")
        assert result["categories"] == {}

    def test_categories_populated_with_fallacies(self):
        detector = MagicMock()
        detector.detect.return_value = [{"fallacy_type": "ad_hominem"}]
        agent = InformalAgent(tools={"fallacy_detector": detector})
        result = agent.perform_complete_analysis("Tu as tort car tu es bête")
        assert "categories" in result
        assert isinstance(result["categories"], dict)

    def test_no_context_skips_contextual(self):
        ctx_analyzer = MagicMock()
        agent = InformalAgent(tools={"contextual_analyzer": ctx_analyzer})
        result = agent.perform_complete_analysis("text")
        # No context provided → contextual_analysis = {}
        ctx_analyzer.analyze_context.assert_not_called()
        assert result["contextual_analysis"] == {}


# ============================================================
# _get_timestamp
# ============================================================

class TestGetTimestamp:
    def test_returns_string(self):
        agent = InformalAgent()
        ts = agent._get_timestamp()
        assert isinstance(ts, str)

    def test_is_valid_iso(self):
        agent = InformalAgent()
        ts = agent._get_timestamp()
        dt = datetime.fromisoformat(ts)
        assert isinstance(dt, datetime)

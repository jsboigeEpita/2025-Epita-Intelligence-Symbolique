# tests/unit/argumentation_analysis/core/test_enums.py
"""Tests for orchestration enums."""

import pytest

from argumentation_analysis.core.enums import OrchestrationMode, AnalysisType


class TestOrchestrationMode:
    def test_pipeline_value(self):
        assert OrchestrationMode.PIPELINE.value == "pipeline"

    def test_real_value(self):
        assert OrchestrationMode.REAL.value == "real"

    def test_conversation_value(self):
        assert OrchestrationMode.CONVERSATION.value == "conversation"

    def test_hierarchical_full(self):
        assert OrchestrationMode.HIERARCHICAL_FULL.value == "hierarchical_full"

    def test_strategic_only(self):
        assert OrchestrationMode.STRATEGIC_ONLY.value == "strategic_only"

    def test_tactical_coordination(self):
        assert OrchestrationMode.TACTICAL_COORDINATION.value == "tactical_coordination"

    def test_operational_direct(self):
        assert OrchestrationMode.OPERATIONAL_DIRECT.value == "operational_direct"

    def test_cluedo_investigation(self):
        assert OrchestrationMode.CLUEDO_INVESTIGATION.value == "cluedo_investigation"

    def test_logic_complex(self):
        assert OrchestrationMode.LOGIC_COMPLEX.value == "logic_complex"

    def test_adaptive_hybrid(self):
        assert OrchestrationMode.ADAPTIVE_HYBRID.value == "adaptive_hybrid"

    def test_auto_select(self):
        assert OrchestrationMode.AUTO_SELECT.value == "auto_select"

    def test_total_members(self):
        assert len(OrchestrationMode) == 11

    def test_from_value(self):
        assert OrchestrationMode("pipeline") == OrchestrationMode.PIPELINE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            OrchestrationMode("nonexistent")


class TestAnalysisType:
    def test_comprehensive(self):
        assert AnalysisType.COMPREHENSIVE.value == "comprehensive"

    def test_rhetorical(self):
        assert AnalysisType.RHETORICAL.value == "rhetorical"

    def test_logical(self):
        assert AnalysisType.LOGICAL.value == "logical"

    def test_investigative(self):
        assert AnalysisType.INVESTIGATIVE.value == "investigative"

    def test_fallacy_focused(self):
        assert AnalysisType.FALLACY_FOCUSED.value == "fallacy_focused"

    def test_argument_structure(self):
        assert AnalysisType.ARGUMENT_STRUCTURE.value == "argument_structure"

    def test_debate_analysis(self):
        assert AnalysisType.DEBATE_ANALYSIS.value == "debate_analysis"

    def test_custom(self):
        assert AnalysisType.CUSTOM.value == "custom"

    def test_total_members(self):
        assert len(AnalysisType) == 8

    def test_from_value(self):
        assert AnalysisType("logical") == AnalysisType.LOGICAL

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AnalysisType("nonexistent")

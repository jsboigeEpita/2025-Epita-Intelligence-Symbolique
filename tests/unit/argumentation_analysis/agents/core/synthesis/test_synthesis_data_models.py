"""
Tests for synthesis data models (LogicAnalysisResult, InformalAnalysisResult, UnifiedReport).
"""

import json
import pytest
from datetime import datetime

from argumentation_analysis.agents.core.synthesis.data_models import (
    LogicAnalysisResult,
    InformalAnalysisResult,
    UnifiedReport,
)

# =====================================================================
# LogicAnalysisResult Tests
# =====================================================================


class TestLogicAnalysisResult:
    """Tests for LogicAnalysisResult dataclass."""

    def test_default_initialization(self):
        """Verify default values are correctly initialized."""
        result = LogicAnalysisResult()
        assert result.propositional_result is None
        assert result.first_order_result is None
        assert result.modal_result is None
        assert result.logical_validity is None
        assert result.consistency_check is None
        assert result.satisfiability is None
        assert result.formulas_extracted == []
        assert result.queries_executed == []
        assert result.processing_time_ms == 0.0
        assert isinstance(result.analysis_timestamp, str)

    def test_full_initialization(self):
        """Verify full initialization with all fields."""
        result = LogicAnalysisResult(
            propositional_result="P -> Q is valid",
            first_order_result="∀x∃y P(x,y)",
            modal_result="□P → P",
            logical_validity=True,
            consistency_check=True,
            satisfiability=True,
            formulas_extracted=["P -> Q", "Q -> R"],
            queries_executed=["query1", "query2"],
            processing_time_ms=150.5,
        )
        assert result.propositional_result == "P -> Q is valid"
        assert result.logical_validity is True
        assert len(result.formulas_extracted) == 2
        assert result.processing_time_ms == 150.5

    def test_to_dict(self):
        """Verify serialization to dictionary."""
        result = LogicAnalysisResult(
            propositional_result="Test result",
            logical_validity=False,
            formulas_extracted=["F1", "F2"],
        )
        data = result.to_dict()
        assert data["propositional_result"] == "Test result"
        assert data["logical_validity"] is False
        assert data["formulas_extracted"] == ["F1", "F2"]
        assert "analysis_timestamp" in data

    def test_formulas_extracted_append(self):
        """Verify formulas can be added after initialization."""
        result = LogicAnalysisResult()
        result.formulas_extracted.append("P -> Q")
        result.formulas_extracted.append("¬P ∨ Q")
        assert len(result.formulas_extracted) == 2

    def test_processing_time_update(self):
        """Verify processing time can be updated."""
        result = LogicAnalysisResult()
        assert result.processing_time_ms == 0.0
        result.processing_time_ms = 250.75
        assert result.processing_time_ms == 250.75


# =====================================================================
# InformalAnalysisResult Tests
# =====================================================================


class TestInformalAnalysisResult:
    """Tests for InformalAnalysisResult dataclass."""

    def test_default_initialization(self):
        """Verify default values are correctly initialized."""
        result = InformalAnalysisResult()
        assert result.fallacies_detected == []
        assert result.arguments_structure is None
        assert result.rhetorical_devices == []
        assert result.argument_strength is None
        assert result.persuasion_level is None
        assert result.credibility_score is None
        assert result.text_segments_analyzed == []
        assert result.context_factors == {}
        assert result.processing_time_ms == 0.0
        assert isinstance(result.analysis_timestamp, str)

    def test_full_initialization(self):
        """Verify full initialization with all fields."""
        result = InformalAnalysisResult(
            fallacies_detected=[{"type": "ad_hominem", "severity": "high"}],
            arguments_structure="Premise -> Conclusion",
            rhetorical_devices=["hyperbole", "metaphor"],
            argument_strength=0.8,
            persuasion_level="Élevé",
            credibility_score=0.75,
            text_segments_analyzed=["segment1", "segment2"],
            context_factors={"audience": "general"},
            processing_time_ms=200.0,
        )
        assert len(result.fallacies_detected) == 1
        assert result.arguments_structure == "Premise -> Conclusion"
        assert result.argument_strength == 0.8
        assert result.persuasion_level == "Élevé"

    def test_to_dict(self):
        """Verify serialization to dictionary."""
        result = InformalAnalysisResult(
            fallacies_detected=[{"type": "straw_man"}],
            argument_strength=0.5,
        )
        data = result.to_dict()
        assert data["fallacies_detected"] == [{"type": "straw_man"}]
        assert data["argument_strength"] == 0.5
        assert "analysis_timestamp" in data

    def test_fallacies_detected_multiple(self):
        """Verify multiple fallacies can be stored."""
        result = InformalAnalysisResult()
        result.fallacies_detected.append({"type": "ad_hominem"})
        result.fallacies_detected.append({"type": "straw_man"})
        result.fallacies_detected.append({"type": "appeal_to_authority"})
        assert len(result.fallacies_detected) == 3

    def test_context_factors_update(self):
        """Verify context factors dictionary can be updated."""
        result = InformalAnalysisResult()
        result.context_factors["audience"] = "experts"
        result.context_factors["domain"] = "politics"
        assert result.context_factors["audience"] == "experts"
        assert result.context_factors["domain"] == "politics"


# =====================================================================
# UnifiedReport Tests
# =====================================================================


class TestUnifiedReport:
    """Tests for UnifiedReport dataclass."""

    def test_minimal_initialization(self):
        """Verify minimal initialization with required fields."""
        logic = LogicAnalysisResult()
        informal = InformalAnalysisResult()
        report = UnifiedReport(
            original_text="Test argument text.",
            logic_analysis=logic,
            informal_analysis=informal,
        )
        assert report.original_text == "Test argument text."
        assert report.logic_analysis is logic
        assert report.informal_analysis is informal
        assert report.executive_summary == ""
        assert report.contradictions_identified == []
        assert report.recommendations == []
        assert isinstance(report.synthesis_timestamp, str)

    def test_full_initialization(self):
        """Verify full initialization with all optional fields."""
        logic = LogicAnalysisResult(logical_validity=True)
        informal = InformalAnalysisResult(argument_strength=0.9)
        report = UnifiedReport(
            original_text="Full test argument.",
            logic_analysis=logic,
            informal_analysis=informal,
            executive_summary="Test summary",
            coherence_assessment="High",
            contradictions_identified=["Contradiction 1"],
            overall_validity=True,
            confidence_level=0.95,
            recommendations=["Improve clarity"],
            logic_informal_alignment=0.8,
            analysis_completeness=0.9,
            total_processing_time_ms=500.0,
        )
        assert report.executive_summary == "Test summary"
        assert report.overall_validity is True
        assert report.confidence_level == 0.95
        assert len(report.recommendations) == 1
        assert report.total_processing_time_ms == 500.0

    def test_to_dict(self):
        """Verify serialization to dictionary."""
        logic = LogicAnalysisResult(propositional_result="Valid")
        informal = InformalAnalysisResult(argument_strength=0.7)
        report = UnifiedReport(
            original_text="Test text",
            logic_analysis=logic,
            informal_analysis=informal,
            overall_validity=True,
        )
        data = report.to_dict()
        assert data["original_text"] == "Test text"
        assert data["overall_validity"] is True
        assert "logic_analysis" in data
        assert "informal_analysis" in data

    def test_to_json(self):
        """Verify JSON serialization."""
        logic = LogicAnalysisResult()
        informal = InformalAnalysisResult()
        report = UnifiedReport(
            original_text="Argument text",
            logic_analysis=logic,
            informal_analysis=informal,
        )
        json_str = report.to_json(indent=2)
        parsed = json.loads(json_str)
        assert parsed["original_text"] == "Argument text"
        assert "synthesis_timestamp" in parsed

    def test_get_summary_statistics(self):
        """Verify summary statistics calculation."""
        logic = LogicAnalysisResult(
            formulas_extracted=["F1", "F2", "F3"],
        )
        informal = InformalAnalysisResult(
            fallacies_detected=[{"type": "fallacy1"}, {"type": "fallacy2"}],
        )
        report = UnifiedReport(
            original_text="This is a test argument with some text.",
            logic_analysis=logic,
            informal_analysis=informal,
            contradictions_identified=["C1", "C2"],
            recommendations=["R1", "R2", "R3"],
            overall_validity=False,
            confidence_level=0.7,
        )
        stats = report.get_summary_statistics()
        assert stats["text_length"] == len("This is a test argument with some text.")
        assert stats["formulas_count"] == 3
        assert stats["fallacies_count"] == 2
        assert stats["contradictions_count"] == 2
        assert stats["recommendations_count"] == 3
        assert stats["overall_validity"] is False
        assert stats["confidence_level"] == 0.7

    def test_synthesis_version_default(self):
        """Verify default synthesis version."""
        logic = LogicAnalysisResult()
        informal = InformalAnalysisResult()
        report = UnifiedReport(
            original_text="Test",
            logic_analysis=logic,
            informal_analysis=informal,
        )
        assert report.synthesis_version == "1.0.0"

    def test_logic_informal_alignment(self):
        """Verify logic-informal alignment score."""
        logic = LogicAnalysisResult()
        informal = InformalAnalysisResult()
        report = UnifiedReport(
            original_text="Test",
            logic_analysis=logic,
            informal_analysis=informal,
            logic_informal_alignment=0.85,
        )
        assert report.logic_informal_alignment == 0.85


# =====================================================================
# Integration Tests
# =====================================================================


class TestDataModelsIntegration:
    """Integration tests for data model interactions."""

    def test_create_unified_report_from_results(self):
        """Verify creating a complete unified report."""
        logic = LogicAnalysisResult(
            propositional_result="Valid structure",
            logical_validity=True,
            formulas_extracted=["P", "P->Q"],
        )
        informal = InformalAnalysisResult(
            fallacies_detected=[],
            argument_strength=0.9,
            arguments_structure="Clear structure",
        )
        report = UnifiedReport(
            original_text="Valid argument text.",
            logic_analysis=logic,
            informal_analysis=informal,
        )
        assert report.logic_analysis.logical_validity is True
        assert report.informal_analysis.argument_strength == 0.9

    def test_json_serialization_roundtrip(self):
        """Verify JSON serialization and deserialization preserves data."""
        logic = LogicAnalysisResult(
            propositional_result="Test",
            logical_validity=True,
        )
        informal = InformalAnalysisResult(
            fallacies_detected=[{"type": "test"}],
        )
        report = UnifiedReport(
            original_text="Original",
            logic_analysis=logic,
            informal_analysis=informal,
        )
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["original_text"] == "Original"
        assert parsed["logic_analysis"]["propositional_result"] == "Test"
        assert len(parsed["informal_analysis"]["fallacies_detected"]) == 1

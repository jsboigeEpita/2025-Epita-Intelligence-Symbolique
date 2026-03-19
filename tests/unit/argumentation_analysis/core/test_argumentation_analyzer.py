# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.core.argumentation_analyzer
Covers ArgumentationAnalyzer: degraded mode, basic analysis, features, validation.
"""

import sys
import pytest
from unittest.mock import MagicMock

# The module imports UnifiedTextAnalysisPipeline from pipelines.unified_text_analysis
# which has a deep import chain (bootstrap.get_fallacy_detector, etc.).
# We inject mocks into sys.modules BEFORE importing the analyzer module.
_mock_pipeline_mod = MagicMock()
_mock_pipeline_mod.UnifiedTextAnalysisPipeline = MagicMock(
    side_effect=Exception("pipeline unavailable")
)
_mock_pipeline_mod.UnifiedAnalysisConfig = MagicMock(
    side_effect=Exception("config unavailable")
)

_mock_analysis_service_mod = MagicMock()
_mock_analysis_service_mod.AnalysisService = MagicMock(
    side_effect=Exception("service unavailable")
)

# Save originals if they exist
_orig_pipeline = sys.modules.get(
    "argumentation_analysis.pipelines.unified_text_analysis"
)
_orig_service = sys.modules.get(
    "argumentation_analysis.services.web_api.services.analysis_service"
)

sys.modules["argumentation_analysis.pipelines.unified_text_analysis"] = (
    _mock_pipeline_mod
)
sys.modules["argumentation_analysis.services.web_api.services.analysis_service"] = (
    _mock_analysis_service_mod
)

from argumentation_analysis.core.argumentation_analyzer import (
    ArgumentationAnalyzer,
    Analyzer,
)

# Restore originals (or remove mocks) so other tests aren't affected
if _orig_pipeline is not None:
    sys.modules["argumentation_analysis.pipelines.unified_text_analysis"] = (
        _orig_pipeline
    )
else:
    sys.modules.pop("argumentation_analysis.pipelines.unified_text_analysis", None)

if _orig_service is not None:
    sys.modules["argumentation_analysis.services.web_api.services.analysis_service"] = (
        _orig_service
    )
else:
    sys.modules.pop(
        "argumentation_analysis.services.web_api.services.analysis_service", None
    )


# ============================================================
# Initialization (degraded mode)
# ============================================================


class TestInit:
    def test_default_init_degraded(self):
        """Constructor succeeds in degraded mode when deps fail."""
        analyzer = ArgumentationAnalyzer()
        assert analyzer.pipeline is None
        assert analyzer.analysis_service is None

    def test_custom_config(self):
        analyzer = ArgumentationAnalyzer(config={"enable_fallacy_detection": False})
        assert analyzer.config["enable_fallacy_detection"] is False

    def test_empty_config_default(self):
        analyzer = ArgumentationAnalyzer()
        assert analyzer.config == {}

    def test_alias_is_same_class(self):
        assert Analyzer is ArgumentationAnalyzer


# ============================================================
# _basic_analysis (pure logic)
# ============================================================


class TestBasicAnalysis:
    def test_text_length(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("Hello world")
        assert result["text_length"] == 11

    def test_word_count(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("one two three")
        assert result["word_count"] == 3

    def test_sentence_count_periods(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("First. Second. Third.")
        assert result["sentences"] == 3

    def test_sentence_count_mixed_punctuation(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("Really? Yes! Done.")
        assert result["sentences"] == 3

    def test_analysis_type_is_fallback(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("text")
        assert result["analysis_type"] == "basic_fallback"

    def test_message_present(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("text")
        assert "message" in result
        assert (
            "basique" in result["message"].lower()
            or "basic" in result["message"].lower()
        )

    def test_empty_text(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("")
        assert result["text_length"] == 0
        # "".split() returns [] → word_count = 0
        assert result["word_count"] == 0

    def test_no_sentences(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer._basic_analysis("no punctuation at all")
        assert result["sentences"] == 0


# ============================================================
# analyze_text
# ============================================================


class TestAnalyzeText:
    def test_empty_text_returns_error(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer.analyze_text("")
        assert result["status"] == "failed"
        assert "error" in result

    def test_whitespace_text_returns_error(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer.analyze_text("   ")
        assert result["status"] == "failed"

    def test_none_text_returns_error(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer.analyze_text(None)
        assert result["status"] == "failed"

    def test_degraded_mode_uses_basic(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer.analyze_text("Some valid text here.")
        assert result["status"] == "success"
        assert "analysis" in result
        # In degraded mode, no pipeline or service available
        assert "basic" in result["analysis"]

    def test_result_contains_text(self):
        analyzer = ArgumentationAnalyzer()
        result = analyzer.analyze_text("argument text")
        assert result["text"] == "argument text"

    def test_with_pipeline_available(self):
        analyzer = ArgumentationAnalyzer()
        mock_pipeline = MagicMock()
        mock_pipeline.analyze_text.return_value = {"fallacies": []}
        analyzer.pipeline = mock_pipeline
        result = analyzer.analyze_text("text to analyze")
        assert "unified" in result["analysis"]
        mock_pipeline.analyze_text.assert_called_once_with("text to analyze")

    def test_with_analysis_service_available(self):
        analyzer = ArgumentationAnalyzer()
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {"quality": "high"}
        analyzer.analysis_service = mock_service
        result = analyzer.analyze_text("text")
        assert "service" in result["analysis"]

    def test_service_error_handled_gracefully(self):
        analyzer = ArgumentationAnalyzer()
        mock_service = MagicMock()
        mock_service.analyze_text.side_effect = RuntimeError("service down")
        analyzer.analysis_service = mock_service
        analyzer.pipeline = MagicMock()
        analyzer.pipeline.analyze_text.return_value = {"ok": True}
        result = analyzer.analyze_text("text")
        assert result["status"] == "success"
        # Service failed but pipeline succeeded
        assert "unified" in result["analysis"]

    def test_options_passed_to_service(self):
        analyzer = ArgumentationAnalyzer()
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {}
        analyzer.analysis_service = mock_service
        analyzer.analyze_text("text", options={"depth": "full"})
        mock_service.analyze_text.assert_called_once_with("text", {"depth": "full"})


# ============================================================
# get_available_features
# ============================================================


class TestGetAvailableFeatures:
    def test_degraded_mode_only_basic(self):
        analyzer = ArgumentationAnalyzer()
        features = analyzer.get_available_features()
        assert "basic_analysis" in features
        assert "unified_pipeline" not in features
        assert "analysis_service" not in features

    def test_with_pipeline(self):
        analyzer = ArgumentationAnalyzer()
        analyzer.pipeline = MagicMock()
        features = analyzer.get_available_features()
        assert "unified_pipeline" in features
        assert "basic_analysis" in features

    def test_with_service(self):
        analyzer = ArgumentationAnalyzer()
        analyzer.analysis_service = MagicMock()
        features = analyzer.get_available_features()
        assert "analysis_service" in features
        assert "basic_analysis" in features

    def test_all_features(self):
        analyzer = ArgumentationAnalyzer()
        analyzer.pipeline = MagicMock()
        analyzer.analysis_service = MagicMock()
        features = analyzer.get_available_features()
        assert len(features) == 3
        assert set(features) == {
            "unified_pipeline",
            "analysis_service",
            "basic_analysis",
        }


# ============================================================
# validate_configuration
# ============================================================


class TestValidateConfiguration:
    def test_degraded_mode_partial(self):
        analyzer = ArgumentationAnalyzer()
        validation = analyzer.validate_configuration()
        assert validation["status"] == "partial"
        assert validation["components"]["pipeline"] is False
        assert validation["components"]["analysis_service"] is False

    def test_has_warnings_in_degraded(self):
        analyzer = ArgumentationAnalyzer()
        validation = analyzer.validate_configuration()
        assert len(validation["warnings"]) == 2

    def test_valid_when_all_components(self):
        analyzer = ArgumentationAnalyzer()
        analyzer.pipeline = MagicMock()
        analyzer.analysis_service = MagicMock()
        validation = analyzer.validate_configuration()
        assert validation["status"] == "valid"
        assert validation["warnings"] == []

    def test_partial_with_only_pipeline(self):
        analyzer = ArgumentationAnalyzer()
        analyzer.pipeline = MagicMock()
        validation = analyzer.validate_configuration()
        assert validation["status"] == "partial"
        assert validation["components"]["pipeline"] is True
        assert validation["components"]["analysis_service"] is False
        assert len(validation["warnings"]) == 1

    def test_components_dict_has_both_keys(self):
        analyzer = ArgumentationAnalyzer()
        validation = analyzer.validate_configuration()
        assert "pipeline" in validation["components"]
        assert "analysis_service" in validation["components"]


# ============================================================
# create_analysis_state
# ============================================================


class TestCreateAnalysisState:
    def test_raises_without_initial_text(self):
        """RhetoricalAnalysisState requires initial_text — create_analysis_state fails."""
        analyzer = ArgumentationAnalyzer()
        with pytest.raises(TypeError):
            analyzer.create_analysis_state()

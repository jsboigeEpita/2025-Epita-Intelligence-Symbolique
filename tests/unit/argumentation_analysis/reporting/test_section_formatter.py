# tests/unit/argumentation_analysis/reporting/test_section_formatter.py
"""Tests for UnifiedReportTemplate — rendering in markdown, console, json, html."""

import json
import pytest
from datetime import datetime

from argumentation_analysis.reporting.section_formatter import UnifiedReportTemplate
from argumentation_analysis.reporting.models import ReportMetadata


@pytest.fixture
def metadata():
    return ReportMetadata(
        source_component="TestOrchestrator",
        analysis_type="rhetoric",
        generated_at=datetime(2026, 1, 1, 12, 0),
        version="1.0.0",
        generator="TestGenerator",
        template_name="test",
    )


@pytest.fixture
def basic_data():
    return {
        "title": "Test Report",
        "summary": {
            "rhetorical_sophistication": "high",
            "manipulation_level": "medium",
            "logical_validity": "strong",
            "confidence_score": 0.85,
        },
    }


@pytest.fixture
def rich_data(basic_data):
    return {
        **basic_data,
        "metadata": {
            "source_description": "Putin speech",
            "source_type": "political",
            "text_length": 5000,
            "processing_time_ms": 1234,
        },
        "informal_analysis": {
            "fallacies": [
                {"type": "Ad Hominem", "confidence": 0.9, "severity": "Critique"},
                {"type": "Straw Man", "confidence": 0.7, "severity": "Modéré"},
            ],
            "rhetorical_patterns": [{"pattern": "emotional_appeal"}],
        },
        "performance_metrics": {
            "total_execution_time_ms": 2345,
            "memory_usage_mb": 128,
        },
    }


# ── __init__ ──

class TestInit:
    def test_default_config(self):
        t = UnifiedReportTemplate({})
        assert t.name == "default"
        assert t.format_type == "markdown"
        assert t.sections == []

    def test_custom_config(self):
        t = UnifiedReportTemplate({
            "name": "custom",
            "format": "json",
            "sections": ["s1"],
            "metadata": {"key": "val"},
        })
        assert t.name == "custom"
        assert t.format_type == "json"


# ── render ──

class TestRender:
    def test_render_markdown(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(basic_data, metadata)
        assert isinstance(result, str)
        assert "Test Report" in result

    def test_render_console(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "console"})
        result = t.render(basic_data, metadata)
        assert isinstance(result, str)
        assert "=" * 60 in result

    def test_render_json(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "json"})
        result = t.render(basic_data, metadata)
        parsed = json.loads(result)
        assert "report_metadata" in parsed

    def test_render_html(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "html"})
        result = t.render(basic_data, metadata)
        assert "<!DOCTYPE html>" in result
        assert "<html" in result

    def test_render_unsupported_format(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "xml"})
        with pytest.raises(ValueError, match="Format non supporté"):
            t.render(basic_data, metadata)


# ── _render_markdown ──

class TestRenderMarkdown:
    def test_contains_title(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(basic_data, metadata)
        assert "# Test Report" in result

    def test_contains_metadata_section(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(basic_data, metadata)
        assert "TestOrchestrator" in result
        assert "rhetoric" in result

    def test_contains_summary(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(basic_data, metadata)
        assert "high" in result
        assert "medium" in result
        assert "0.85" in result

    def test_with_analysis_metadata(self, metadata, rich_data):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(rich_data, metadata)
        assert "Putin speech" in result
        assert "5000" in result

    def test_with_fallacies(self, metadata, rich_data):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(rich_data, metadata)
        assert "Ad Hominem" in result

    def test_default_title_when_missing(self, metadata):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render({}, metadata)
        assert "TESTORCHESTRATOR" in result

    def test_with_orchestration_summary(self, metadata):
        data = {
            "summary": {
                "orchestration_summary": {
                    "agents_count": 5,
                    "orchestration_time_ms": 999,
                    "execution_status": "success",
                },
            },
        }
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(data, metadata)
        assert "5" in result

    def test_with_orchestration_results(self, metadata):
        data = {
            "orchestration_results": {
                "execution_plan": {
                    "strategy": "sequential",
                    "steps": [{"agent": "FallacyAgent", "description": "Detect fallacies"}],
                },
                "agent_results": {
                    "FallacyAgent": {
                        "status": "success",
                        "execution_time_ms": 500,
                        "metrics": {"processed_items": 10, "confidence_score": 0.9},
                    },
                },
            },
        }
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(data, metadata)
        assert "sequential" in result
        assert "FallacyAgent" in result

    def test_with_performance_metrics(self, metadata, rich_data):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render(rich_data, metadata)
        assert "2345" in result


# ── _render_console ──

class TestRenderConsole:
    def test_compact_format(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "console"})
        result = t.render(basic_data, metadata)
        assert "[STATS]" in result
        assert "[WARN]" in result
        assert "[LOGIC]" in result

    def test_fallacies_limited_to_3(self, metadata):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {"type": f"Fallacy_{i}", "confidence": 0.5, "severity": "Faible"}
                    for i in range(5)
                ],
            },
        }
        t = UnifiedReportTemplate({"format": "console"})
        result = t.render(data, metadata)
        assert "et 2 autres" in result

    def test_severity_icons(self, metadata):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {"type": "Critical One", "confidence": 0.9, "severity": "Critique"},
                ],
            },
        }
        t = UnifiedReportTemplate({"format": "console"})
        result = t.render(data, metadata)
        assert "[CRIT]" in result


# ── _render_json ──

class TestRenderJson:
    def test_valid_json(self, metadata, rich_data):
        t = UnifiedReportTemplate({"format": "json"})
        result = t.render(rich_data, metadata)
        parsed = json.loads(result)
        assert parsed["report_metadata"]["source_component"] == "TestOrchestrator"
        assert parsed["title"] == "Test Report"

    def test_preserves_all_data(self, metadata, rich_data):
        t = UnifiedReportTemplate({"format": "json"})
        result = t.render(rich_data, metadata)
        parsed = json.loads(result)
        assert "informal_analysis" in parsed
        assert "performance_metrics" in parsed


# ── _render_html ──

class TestRenderHtml:
    def test_html_structure(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "html"})
        result = t.render(basic_data, metadata)
        assert "<html" in result
        assert "</html>" in result
        assert "<style>" in result
        assert "</body>" in result

    def test_contains_component_badge(self, metadata, basic_data):
        t = UnifiedReportTemplate({"format": "html"})
        result = t.render(basic_data, metadata)
        assert "component-badge" in result
        assert "TestOrchestrator" in result

    def test_with_fallacies_html(self, metadata, rich_data):
        t = UnifiedReportTemplate({"format": "html"})
        result = t.render(rich_data, metadata)
        assert "Ad Hominem" in result


# ── Edge Cases ──

class TestEdgeCases:
    def test_empty_data(self, metadata):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render({}, metadata)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_summary(self, metadata):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render({"summary": {}}, metadata)
        assert "N/A" in result

    def test_empty_fallacies_list(self, metadata):
        data = {"informal_analysis": {"fallacies": []}}
        t = UnifiedReportTemplate({"format": "console"})
        result = t.render(data, metadata)
        assert "[FALLACIES] Sophismes détectés: 0" in result

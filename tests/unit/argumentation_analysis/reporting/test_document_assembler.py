# tests/unit/argumentation_analysis/reporting/test_document_assembler.py
"""Tests for ReportMetadata, UnifiedReportTemplate, and document assembly helpers."""

import json
import pytest
from datetime import datetime

from argumentation_analysis.reporting.document_assembler import (
    ReportMetadata,
    UnifiedReportTemplate,
)


# ── ReportMetadata ──

class TestReportMetadata:
    def test_required_fields(self):
        m = ReportMetadata(
            source_component="orchestrator",
            analysis_type="rhetoric",
            generated_at=datetime(2026, 1, 1, 12, 0),
        )
        assert m.source_component == "orchestrator"
        assert m.analysis_type == "rhetoric"
        assert m.generated_at == datetime(2026, 1, 1, 12, 0)

    def test_defaults(self):
        m = ReportMetadata(
            source_component="c", analysis_type="a", generated_at=datetime.now()
        )
        assert m.version == "1.0.0"
        assert m.generator == "UnifiedReportGeneration"
        assert m.format_type == "markdown"
        assert m.template_name == "default"

    def test_custom_values(self):
        m = ReportMetadata(
            source_component="pipeline",
            analysis_type="LLM",
            generated_at=datetime.now(),
            version="2.0.0",
            generator="CustomGenerator",
            format_type="html",
            template_name="custom_template",
        )
        assert m.version == "2.0.0"
        assert m.generator == "CustomGenerator"
        assert m.format_type == "html"
        assert m.template_name == "custom_template"


# ── UnifiedReportTemplate Init ──

class TestTemplateInit:
    def test_default_config(self):
        t = UnifiedReportTemplate({})
        assert t.name == "default"
        assert t.format_type == "markdown"
        assert t.sections == []
        assert t.metadata == {}
        assert t.custom_renderers == {}

    def test_custom_config(self):
        config = {
            "name": "custom",
            "format": "html",
            "sections": ["summary", "fallacies"],
            "metadata": {"key": "val"},
            "custom_renderers": {"xml": lambda d: "<xml/>"},
        }
        t = UnifiedReportTemplate(config)
        assert t.name == "custom"
        assert t.format_type == "html"
        assert len(t.sections) == 2
        assert t.metadata["key"] == "val"


# ── Render Dispatch ──

class TestRenderDispatch:
    @pytest.fixture
    def metadata(self):
        return ReportMetadata(
            source_component="test", analysis_type="unit", generated_at=datetime(2026, 1, 1)
        )

    def test_markdown_format(self, metadata):
        t = UnifiedReportTemplate({"format": "markdown"})
        result = t.render({}, metadata)
        assert "# " in result  # Has a heading
        assert "test" in result  # Component name appears

    def test_console_format(self, metadata):
        t = UnifiedReportTemplate({"format": "console"})
        result = t.render({}, metadata)
        assert "=" * 60 in result

    def test_json_format(self, metadata):
        t = UnifiedReportTemplate({"format": "json"})
        result = t.render({"key": "value"}, metadata)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert "report_metadata" in parsed

    def test_html_format(self, metadata):
        t = UnifiedReportTemplate({"format": "html"})
        result = t.render({}, metadata)
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result

    def test_unsupported_format_raises(self, metadata):
        t = UnifiedReportTemplate({"format": "xml"})
        with pytest.raises(ValueError, match="Format non supporté"):
            t.render({}, metadata)


# ── Markdown Rendering ──

class TestMarkdownRendering:
    @pytest.fixture
    def template(self):
        return UnifiedReportTemplate({"format": "markdown"})

    @pytest.fixture
    def metadata(self):
        return ReportMetadata(
            source_component="orchestrator",
            analysis_type="rhetoric",
            generated_at=datetime(2026, 3, 1, 10, 30),
            version="1.0.0",
        )

    def test_title_from_data(self, template, metadata):
        result = template.render({"title": "My Custom Title"}, metadata)
        assert "# My Custom Title" in result

    def test_default_title(self, template, metadata):
        result = template.render({}, metadata)
        assert "RAPPORT D'ANALYSE" in result

    def test_metadata_section(self, template, metadata):
        result = template.render({}, metadata)
        assert "orchestrator" in result
        assert "rhetoric" in result
        assert "1.0.0" in result

    def test_analysis_metadata(self, template, metadata):
        data = {"metadata": {"source_description": "Test file", "text_length": 500}}
        result = template.render(data, metadata)
        assert "Test file" in result
        assert "500" in result

    def test_summary_section(self, template, metadata):
        data = {
            "summary": {
                "rhetorical_sophistication": "high",
                "manipulation_level": "medium",
                "logical_validity": "valid",
            }
        }
        result = template.render(data, metadata)
        assert "high" in result
        assert "medium" in result

    def test_orchestration_summary(self, template, metadata):
        data = {
            "summary": {
                "orchestration_summary": {
                    "agents_count": 5,
                    "orchestration_time_ms": 1234,
                }
            }
        }
        result = template.render(data, metadata)
        assert "5" in result
        assert "1234" in result

    def test_informal_analysis_with_fallacies(self, template, metadata):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {
                        "type": "Ad Hominem",
                        "text_fragment": "You are wrong because...",
                        "explanation": "Attacks the person",
                        "severity": "Critique",
                        "confidence": 0.85,
                    }
                ]
            }
        }
        result = template.render(data, metadata)
        assert "Ad Hominem" in result
        assert "85" in result  # 0.85 formatted as percentage

    def test_fallacy_alternative_confidence(self, template, metadata):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {
                        "type": "Straw Man",
                        "confidence": 0,
                        "score": 0.72,
                    }
                ]
            }
        }
        result = template.render(data, metadata)
        assert "72" in result

    def test_fallacy_zero_confidence(self, template, metadata):
        data = {
            "informal_analysis": {
                "fallacies": [{"type": "Test", "confidence": 0}]
            }
        }
        result = template.render(data, metadata)
        assert "Non calculée" in result

    def test_formal_analysis_success(self, template, metadata):
        data = {
            "formal_analysis": {
                "logic_type": "propositional",
                "status": "success",
                "belief_set_summary": {
                    "is_consistent": True,
                    "formulas_validated": 3,
                    "formulas_total": 5,
                },
            }
        }
        result = template.render(data, metadata)
        assert "propositional" in result
        assert "Cohérente" in result
        assert "3" in result

    def test_formal_analysis_failure(self, template, metadata):
        data = {"formal_analysis": {"logic_type": "", "status": "failed"}}
        result = template.render(data, metadata)
        assert "Diagnostic" in result

    def test_formal_analysis_queries(self, template, metadata):
        data = {
            "formal_analysis": {
                "logic_type": "FOL",
                "status": "success",
                "queries": [
                    {"query": "P(x)", "result": "Entailed"},
                    {"query": "Q(y)", "result": "Not Entailed"},
                ],
            }
        }
        result = template.render(data, metadata)
        assert "P(x)" in result
        assert "Entailed" in result

    def test_conversation_string(self, template, metadata):
        data = {"conversation": "Hello world"}
        result = template.render(data, metadata)
        assert "Hello world" in result

    def test_conversation_list(self, template, metadata):
        data = {
            "conversation": [
                {"user": "Question?", "system": "Answer."},
            ]
        }
        result = template.render(data, metadata)
        assert "Question?" in result
        assert "Answer." in result

    def test_performance_metrics(self, template, metadata):
        data = {
            "performance_metrics": {
                "total_execution_time_ms": 5000,
                "memory_usage_mb": 256,
                "active_agents_count": 3,
                "success_rate": 0.95,
            }
        }
        result = template.render(data, metadata)
        assert "5000" in result
        assert "256" in result
        assert "95" in result

    def test_recommendations_section(self, template, metadata):
        data = {"recommendations": ["Fix bug A", "Optimize B"]}
        result = template.render(data, metadata)
        assert "Fix bug A" in result


# ── Console Rendering ──

class TestConsoleRendering:
    @pytest.fixture
    def template(self):
        return UnifiedReportTemplate({"format": "console"})

    @pytest.fixture
    def metadata(self):
        return ReportMetadata(
            source_component="system", analysis_type="analysis", generated_at=datetime.now()
        )

    def test_header_bar(self, template, metadata):
        result = template.render({}, metadata)
        assert result.startswith("=" * 60)

    def test_summary_stats(self, template, metadata):
        data = {
            "summary": {
                "rhetorical_sophistication": "high",
                "manipulation_level": "low",
                "logical_validity": "valid",
            }
        }
        result = template.render(data, metadata)
        assert "[STATS]" in result
        assert "[WARN]" in result
        assert "[LOGIC]" in result

    def test_fallacies_display(self, template, metadata):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {"type": "t", "severity": "Critique", "confidence": 0.9},
                    {"type": "t", "severity": "Élevé", "confidence": 0.7},
                    {"type": "t", "severity": "Modéré", "confidence": 0.5},
                    {"type": "t", "severity": "Faible", "confidence": 0.3},
                    {"type": "t", "severity": "Unknown", "confidence": 0.2},
                ]
            }
        }
        result = template.render(data, metadata)
        assert "[FALLACIES]" in result
        assert "[CRIT]" in result
        # Only first 3 shown, rest summarized
        assert "et 2 autres" in result

    def test_performance(self, template, metadata):
        data = {
            "performance_metrics": {
                "total_execution_time_ms": 1234,
                "memory_usage_mb": 512,
            }
        }
        result = template.render(data, metadata)
        assert "[PERF]" in result
        assert "1234" in result


# ── JSON Rendering ──

class TestJsonRendering:
    @pytest.fixture
    def template(self):
        return UnifiedReportTemplate({"format": "json"})

    @pytest.fixture
    def metadata(self):
        return ReportMetadata(
            source_component="test", analysis_type="test", generated_at=datetime(2026, 1, 1)
        )

    def test_valid_json(self, template, metadata):
        data = {"key": "value", "nested": {"a": 1}}
        result = template.render(data, metadata)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["nested"]["a"] == 1

    def test_metadata_injected(self, template, metadata):
        result = template.render({}, metadata)
        parsed = json.loads(result)
        assert parsed["report_metadata"]["source_component"] == "test"

    def test_unicode_preserved(self, template, metadata):
        data = {"text": "Élevé résultat français"}
        result = template.render(data, metadata)
        assert "Élevé" in result


# ── HTML Rendering ──

class TestHtmlRendering:
    @pytest.fixture
    def template(self):
        return UnifiedReportTemplate({"format": "html"})

    @pytest.fixture
    def metadata(self):
        return ReportMetadata(
            source_component="pipeline", analysis_type="LLM", generated_at=datetime(2026, 1, 1)
        )

    def test_html_structure(self, template, metadata):
        result = template.render({}, metadata)
        assert "<!DOCTYPE html>" in result
        assert "<html lang='fr'>" in result
        assert "</html>" in result
        assert "<head>" in result
        assert "</body>" in result

    def test_title_in_html(self, template, metadata):
        result = template.render({}, metadata)
        assert "pipeline" in result
        assert "LLM" in result

    def test_metadata_section_html(self, template, metadata):
        data = {"metadata": {"source_description": "A test source"}}
        result = template.render(data, metadata)
        assert "A test source" in result

    def test_summary_html(self, template, metadata):
        data = {
            "summary": {
                "rhetorical_sophistication": "moderate",
                "manipulation_level": "low",
            }
        }
        result = template.render(data, metadata)
        assert "moderate" in result

    def test_fallacies_html(self, template, metadata):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {
                        "type": "Ad Hominem",
                        "text_fragment": "Test",
                        "explanation": "Attacks person",
                        "confidence": 0.9,
                        "severity": "critique",
                    }
                ]
            }
        }
        result = template.render(data, metadata)
        assert "Ad Hominem" in result
        assert "severity-critique" in result

    def test_performance_html(self, template, metadata):
        data = {
            "performance_metrics": {
                "total_execution_time_ms": 999,
                "memory_usage_mb": 128,
                "success_rate": 0.88,
            }
        }
        result = template.render(data, metadata)
        assert "999" in result
        assert "128" in result


# ── Helper Methods ──

class TestHelperMethods:
    @pytest.fixture
    def template(self):
        return UnifiedReportTemplate({"format": "markdown"})

    def test_extract_sk_retry_attempts_with_pattern(self, template):
        text = "tentative de conversion 1/3 predicate 'test_pred' has not been declared"
        result = template._extract_sk_retry_attempts(text)
        assert len(result) > 0

    def test_extract_sk_retry_attempts_empty(self, template):
        result = template._extract_sk_retry_attempts("no retry info here")
        assert result == {}

    def test_extract_sk_retry_known_predicates(self, template):
        text = "error with constantanalyser_faits_avec_rigueur in system"
        result = template._extract_sk_retry_attempts(text)
        assert len(result) > 0

    def test_extract_error_context_found(self, template):
        text = "some prefix predicate 'test' has not been declared some suffix"
        result = template._extract_error_context(text, "predicate")
        assert "non déclaré" in result.lower() or "not declared" in result.lower() or "déclaré" in result.lower()

    def test_extract_error_context_not_found(self, template):
        result = template._extract_error_context("some text", "nonexistent_xyz")
        assert "non trouvé" in result.lower()

    def test_extract_tweety_errors_predicate(self, template):
        text = "predicate 'myPred' has not been declared in the system"
        errors = template._extract_tweety_errors(text)
        assert len(errors) >= 1
        assert "mypred" in errors[0]  # _extract_tweety_errors lowercases

    def test_extract_tweety_errors_conversion(self, template):
        text = "conversion/validation error in tweety"
        errors = template._extract_tweety_errors(text)
        assert any("conversion" in e.lower() for e in errors)

    def test_extract_tweety_errors_generic(self, template):
        text = "an error with tweety backend"
        errors = template._extract_tweety_errors(text)
        assert len(errors) >= 1

    def test_extract_tweety_errors_none(self, template):
        errors = template._extract_tweety_errors("nothing special here")
        assert errors == []

    def test_is_generic_recommendation_true(self, template):
        assert template._is_generic_recommendation("Analyse orchestrée complétée avec succès") is True
        assert template._is_generic_recommendation("Examen des insights avancés recommandé pour l'avenir") is True

    def test_is_generic_recommendation_false(self, template):
        assert template._is_generic_recommendation("Fix the modal logic conversion") is False

    def test_count_modal_failures_none(self, template):
        assert template._count_modal_failures({}) == 0
        assert template._count_modal_failures({"messages": []}) == 0

    def test_count_modal_failures_found(self, template):
        log = {
            "messages": [
                {"agent": "ModalLogicAgent", "message": "erreur de conversion"},
                {"agent": "ModalLogicAgent", "message": "échec de la tentative"},
                {"agent": "OtherAgent", "message": "erreur non comptée"},
            ]
        }
        assert template._count_modal_failures(log) == 2

    def test_generate_contextual_recommendations_critical(self, template):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {"type": "Ad Hominem", "severity": "Critique", "confidence": 0.9},
                ]
            }
        }
        recs = template._generate_contextual_recommendations(data)
        assert any("URGENCE" in r for r in recs)

    def test_generate_contextual_recommendations_high_confidence(self, template):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {"type": "Straw Man", "severity": "Modéré", "confidence": 0.85},
                ]
            }
        }
        recs = template._generate_contextual_recommendations(data)
        assert any("forte confiance" in r for r in recs)

    def test_generate_contextual_recommendations_many_fallacies(self, template):
        data = {
            "informal_analysis": {
                "fallacies": [
                    {"type": f"F{i}", "severity": "Modéré", "confidence": 0.5}
                    for i in range(5)
                ]
            }
        }
        recs = template._generate_contextual_recommendations(data)
        assert any("Densité" in r for r in recs)

    def test_generate_contextual_recommendations_slow(self, template):
        data = {
            "performance_metrics": {"total_execution_time_ms": 50000},
            "informal_analysis": {"fallacies": []},
        }
        recs = template._generate_contextual_recommendations(data)
        assert any("performances" in r.lower() or "Optimiser" in r for r in recs)

    def test_generate_contextual_recommendations_no_issues(self, template):
        data = {
            "informal_analysis": {"fallacies": []},
            "formal_analysis": {"logic_type": "FOL", "status": "success"},
            "orchestration_analysis": {"status": "success"},
        }
        recs = template._generate_contextual_recommendations(data)
        assert any("sans problèmes" in r or "approfondie" in r for r in recs)

    def test_logic_failure_diagnostic_with_modal(self, template):
        data = {
            "orchestration_analysis": {
                "conversation_log": {
                    "messages": [
                        {"agent": "ModalLogicAgent", "message": "erreur de conversion Tweety"},
                    ]
                }
            }
        }
        lines = template._generate_logic_failure_diagnostic(data)
        assert any("ModalLogicAgent" in l for l in lines)

    def test_logic_failure_diagnostic_no_data(self, template):
        lines = template._generate_logic_failure_diagnostic({})
        assert len(lines) > 0
        assert any("non exécutée" in l or "échouée" in l for l in lines)

    def test_logic_failure_diagnostic_high_exec_time(self, template):
        data = {"performance_metrics": {"total_execution_time_ms": 25000}}
        lines = template._generate_logic_failure_diagnostic(data)
        assert any("retry" in l.lower() or "élevé" in l.lower() for l in lines)


# ── Orchestration Sections ──

class TestOrchestrationRendering:
    @pytest.fixture
    def template(self):
        return UnifiedReportTemplate({"format": "markdown"})

    @pytest.fixture
    def metadata(self):
        return ReportMetadata(
            source_component="test", analysis_type="test", generated_at=datetime(2026, 1, 1)
        )

    def test_orchestration_results(self, template, metadata):
        data = {
            "orchestration_results": {
                "execution_plan": {
                    "strategy": "sequential",
                    "steps": [
                        {"agent": "AgentA", "description": "Step 1"},
                        {"agent": "AgentB", "description": "Step 2"},
                    ],
                },
                "agent_results": {
                    "AgentA": {
                        "status": "success",
                        "execution_time_ms": 500,
                        "metrics": {"processed_items": 10, "confidence_score": 0.95},
                    }
                },
            }
        }
        result = template.render(data, metadata)
        assert "sequential" in result
        assert "AgentA" in result
        assert "500" in result

    def test_orchestration_analysis_list_log(self, template, metadata):
        data = {
            "orchestration_analysis": {
                "status": "success",
                "type": "multi-agent",
                "processing_time_ms": 1234,
                "conversation_log": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "retry attempt here"},
                ],
            }
        }
        result = template.render(data, metadata)
        assert "1234" in result

    def test_orchestration_analysis_dict_log(self, template, metadata):
        data = {
            "orchestration_analysis": {
                "status": "partial",
                "conversation_log": {
                    "messages": [
                        {"agent": "ModalLogicAgent", "message": "tentative de conversion 1/3 échouée"},
                    ]
                },
            }
        }
        result = template.render(data, metadata)
        assert "Retry" in result or "retry" in result or "SK" in result

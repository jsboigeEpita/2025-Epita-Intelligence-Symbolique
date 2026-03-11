# tests/unit/argumentation_analysis/services/test_logic_service.py
"""Tests for LogicService — logic analysis, caching, circuit breaker, validation."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from argumentation_analysis.services.logic_service import LogicService


@pytest.fixture
def service():
    return LogicService()


@pytest.fixture
def initialized_service(service):
    service.initialize_logic_agents()
    return service


# ── __init__ ──

class TestInit:
    def test_initial_state(self, service):
        assert service.active_sessions == {}
        assert service.logic_agents == {}
        assert service.analysis_cache == {}
        assert service._fallback_enabled is True
        assert service._circuit_breaker["failures"] == 0
        assert service._health_status["status"] == "initializing"


# ── initialize_logic_agents ──

class TestInitializeLogicAgents:
    def test_default_config(self, service):
        result = service.initialize_logic_agents()
        assert result is True
        assert "propositional" in service.logic_agents
        assert "first_order" in service.logic_agents
        assert "modal" in service.logic_agents
        assert service._health_status["status"] == "healthy"

    def test_custom_config(self, service):
        config = {"custom_logic": {"enabled": True, "priority": 1}}
        result = service.initialize_logic_agents(config)
        assert result is True
        assert "custom_logic" in service.logic_agents


# ── analyze_text_logic ──

class TestAnalyzeTextLogic:
    def test_propositional_analysis(self, initialized_service):
        result = initialized_service.analyze_text_logic("p implies q", "propositional")
        assert result["success"] is True
        assert result["logic_type"] == "propositional"
        assert result["belief_set"] is not None

    def test_first_order_analysis(self, initialized_service):
        result = initialized_service.analyze_text_logic("forall x P(x)", "first_order")
        assert result["success"] is True
        assert result["logic_type"] == "first_order"

    def test_modal_analysis(self, initialized_service):
        result = initialized_service.analyze_text_logic("necessarily p", "modal")
        assert result["success"] is True
        assert result["logic_type"] == "modal"

    def test_auto_detection_propositional(self, initialized_service):
        result = initialized_service.analyze_text_logic("simple proposition", "auto")
        assert result["success"] is True
        assert result["logic_type"] == "propositional"

    def test_auto_detection_fol(self, initialized_service):
        result = initialized_service.analyze_text_logic("forall x exists y", "auto")
        assert result["logic_type"] == "first_order"

    def test_auto_detection_modal(self, initialized_service):
        result = initialized_service.analyze_text_logic("necessarily true", "auto")
        assert result["logic_type"] == "modal"

    def test_cache_hit(self, initialized_service):
        result1 = initialized_service.analyze_text_logic("cached text", "propositional")
        result2 = initialized_service.analyze_text_logic("cached text", "propositional")
        assert result1["analysis_id"] == result2["analysis_id"]

    def test_unsupported_logic_type(self, initialized_service):
        result = initialized_service.analyze_text_logic("text", "quantum_logic")
        assert result["success"] is False
        assert result["error"] is not None


# ── validate_formula ──

class TestValidateFormula:
    def test_propositional(self, service):
        valid, msg = service.validate_formula("p => q", "propositional")
        assert valid is True

    def test_fol(self, service):
        valid, msg = service.validate_formula("forall X: P(X)", "first_order")
        assert valid is True

    def test_modal(self, service):
        valid, msg = service.validate_formula("[]p", "modal")
        assert valid is True

    def test_unsupported_type(self, service):
        valid, msg = service.validate_formula("formula", "unknown")
        assert valid is False
        assert "non supporté" in msg


# ── execute_query ──

class TestExecuteQuery:
    def test_propositional_query(self, service):
        result = service.execute_query("bs1", "p", "propositional")
        assert result["success"] is True
        assert result["accepted"] is True
        assert "ACCEPTED" in result["message"]

    def test_fol_query(self, service):
        result = service.execute_query("bs1", "P(a)", "first_order")
        assert result["success"] is True
        assert result["accepted"] is True

    def test_modal_query(self, service):
        result = service.execute_query("bs1", "[]p", "modal")
        assert result["success"] is True
        assert result["accepted"] is True

    def test_unsupported_type(self, service):
        result = service.execute_query("bs1", "q", "quantum")
        assert result["success"] is False

    def test_execution_time_tracked(self, service):
        result = service.execute_query("bs1", "p", "propositional")
        assert result["execution_time"] >= 0


# ── get_service_status ──

class TestGetServiceStatus:
    def test_initial_status(self, service):
        status = service.get_service_status()
        assert status["service_name"] == "LogicService"
        assert "timestamp" in status

    def test_healthy_after_init(self, initialized_service):
        status = initialized_service.get_service_status()
        assert status["status"] == "healthy"

    def test_status_includes_performance_stats(self, initialized_service):
        status = initialized_service.get_service_status()
        assert "performance_stats" in status
        assert "circuit_breaker" in status
        assert "cache_stats" in status


# ── clear_cache ──

class TestClearCache:
    def test_clears_cache(self, initialized_service):
        initialized_service.analyze_text_logic("text", "propositional")
        assert len(initialized_service.analysis_cache) > 0
        result = initialized_service.clear_cache()
        assert result is True
        assert len(initialized_service.analysis_cache) == 0


# ── Circuit Breaker ──

class TestCircuitBreaker:
    def test_initially_closed(self, service):
        assert service._is_circuit_breaker_open() is False

    def test_opens_after_max_failures(self, service):
        for _ in range(5):
            service._record_circuit_breaker_failure()
        assert service._is_circuit_breaker_open() is True

    def test_resets_after_timeout(self, service):
        for _ in range(5):
            service._record_circuit_breaker_failure()
        # Simulate 6 minutes ago
        service._circuit_breaker["last_failure"] = datetime.now() - timedelta(minutes=6)
        assert service._is_circuit_breaker_open() is False

    def test_reset_clears_state(self, service):
        service._record_circuit_breaker_failure()
        service._reset_circuit_breaker()
        assert service._circuit_breaker["failures"] == 0
        assert service._circuit_breaker["last_failure"] is None


# ── Fallback ──

class TestFallback:
    def test_fallback_result(self, service):
        result = service._get_fallback_analysis_result("text", "propositional")
        assert result["fallback_mode"] is True
        assert result["success"] is True

    def test_fallback_with_error(self, service):
        result = service._get_fallback_analysis_result("text", "propositional", "test error")
        assert result["error"] == "test error"

    def test_fallback_disabled(self, service):
        service._fallback_enabled = False
        result = service._get_fallback_analysis_result("text", "propositional")
        assert result["success"] is False
        assert "désactivé" in result["interpretation"]

    def test_enable_fallback_mode(self, service):
        service.enable_fallback_mode(False)
        assert service._fallback_enabled is False
        service.enable_fallback_mode(True)
        assert service._fallback_enabled is True


# ── analyze_text_logic_async ──

class TestAnalyzeTextLogicAsync:
    def test_async_with_circuit_breaker_open(self, service):
        for _ in range(5):
            service._record_circuit_breaker_failure()
        result = service.analyze_text_logic_async("text", "propositional")
        assert result["fallback_mode"] is True

    def test_async_normal(self, initialized_service):
        result = initialized_service.analyze_text_logic_async("text", "propositional")
        # Should return either normal or fallback result
        assert "analysis_id" in result


# ── execute_multiple_queries_async ──

class TestExecuteMultipleQueriesAsync:
    def test_multiple_queries(self, service):
        queries = [
            {"belief_set_id": "bs1", "query": "p", "logic_type": "propositional"},
            {"belief_set_id": "bs2", "query": "q", "logic_type": "first_order"},
        ]
        results = service.execute_multiple_queries_async(queries)
        assert len(results) == 2


# ── validate_and_sanitize_input ──

class TestValidateAndSanitizeInput:
    def test_valid_input(self, service):
        valid, text, lt = service.validate_and_sanitize_input("hello", "propositional")
        assert valid is True
        assert text == "hello"
        assert lt == "propositional"

    def test_invalid_logic_type_defaults_auto(self, service):
        valid, text, lt = service.validate_and_sanitize_input("hello", "quantum")
        assert valid is True
        assert lt == "auto"

    def test_empty_text(self, service):
        valid, text, lt = service.validate_and_sanitize_input("", "propositional")
        assert valid is False

    def test_none_text(self, service):
        valid, text, lt = service.validate_and_sanitize_input(None, "propositional")
        assert valid is False

    def test_text_truncated(self, service):
        long_text = "A" * 20000
        valid, text, lt = service.validate_and_sanitize_input(long_text, "propositional")
        assert valid is True
        assert len(text) == 10000

    def test_text_stripped(self, service):
        valid, text, lt = service.validate_and_sanitize_input("  hello  ", "propositional")
        assert text == "hello"


# ── _determine_logic_type ──

class TestDetermineLogicType:
    @pytest.mark.parametrize("text,expected", [
        ("forall x P(x)", "first_order"),
        ("exists y Q(y)", "first_order"),
        ("∀x P(x)", "first_order"),
        ("∃y Q(y)", "first_order"),
        ("necessarily p", "modal"),
        ("possibly q", "modal"),
        ("□p", "modal"),
        ("◇q", "modal"),
        ("simple text", "propositional"),
    ])
    def test_detection(self, service, text, expected):
        result = service._determine_logic_type(text)
        assert result == expected


# ── shutdown ──

class TestShutdown:
    def test_shutdown_clears_state(self, initialized_service):
        initialized_service.analyze_text_logic("text", "propositional")
        initialized_service.active_sessions["s1"] = {}
        initialized_service.shutdown()
        assert len(initialized_service.analysis_cache) == 0
        assert len(initialized_service.active_sessions) == 0
        assert initialized_service._health_status["status"] == "shutdown"


# ── Integration ──

class TestLogicServiceIntegration:
    def test_full_workflow(self, service):
        """Init, analyze, validate, query, status, clear, shutdown."""
        service.initialize_logic_agents()

        result = service.analyze_text_logic("forall x: P(x) => Q(x)", "auto")
        assert result["success"] is True
        assert result["logic_type"] == "first_order"

        valid, msg = service.validate_formula("P(a)", "first_order")
        assert valid is True

        qr = service.execute_query("bs1", "P(a)", "first_order")
        assert qr["success"] is True

        status = service.get_service_status()
        assert status["status"] == "healthy"
        assert status["cached_analyses"] >= 1

        service.clear_cache()
        assert len(service.analysis_cache) == 0

        service.shutdown()
        assert service._health_status["status"] == "shutdown"

    def test_degraded_status_on_circuit_breaker(self, initialized_service):
        for _ in range(5):
            initialized_service._record_circuit_breaker_failure()
        status = initialized_service.get_service_status()
        assert status["status"] == "degraded"

"""
Tests unitaires pour les modeles de donnees de real_llm_orchestrator.py.

Couvre:
- LLMAnalysisRequest / LLMAnalysisResult dataclasses

Issue: #36 (test coverage)

DEPRECATION NOTICE (#215):
RealLLMOrchestrator has been archived. Its behavior tests have been removed.
Use tests for UnifiedPipeline or ConversationOrchestrator instead.

Only the dataclass tests (TestLLMAnalysisRequest, TestLLMAnalysisResult) remain.
"""

from dataclasses import asdict
from datetime import datetime

# ============================================================================
# Dataclass tests
# ============================================================================


class TestLLMAnalysisRequest:
    """Tests for the LLMAnalysisRequest dataclass."""

    def test_basic_creation(self):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Hello", analysis_type="syntactic")
        assert req.text == "Hello"
        assert req.analysis_type == "syntactic"
        assert req.context is None
        assert req.parameters is None
        assert req.timeout == 30

    def test_full_creation(self):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(
            text="Test",
            analysis_type="semantic",
            context={"domain": "politics"},
            parameters={"depth": 3},
            timeout=60,
        )
        assert req.context == {"domain": "politics"}
        assert req.parameters == {"depth": 3}
        assert req.timeout == 60

    def test_asdict(self):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="x", analysis_type="y")
        d = asdict(req)
        assert d["text"] == "x"
        assert d["analysis_type"] == "y"


class TestLLMAnalysisResult:
    """Tests for the LLMAnalysisResult dataclass."""

    def test_basic_creation(self):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisResult,
        )

        now = datetime.now()
        res = LLMAnalysisResult(
            request_id="req_1",
            analysis_type="syntactic",
            result={"success": True},
            confidence=0.95,
            processing_time=1.23,
            timestamp=now,
        )
        assert res.request_id == "req_1"
        assert res.confidence == 0.95
        assert res.metadata is None

    def test_with_metadata(self):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisResult,
        )

        res = LLMAnalysisResult(
            request_id="req_2",
            analysis_type="semantic",
            result={},
            confidence=0.5,
            processing_time=0.1,
            timestamp=datetime.now(),
            metadata={"error": False},
        )
        assert res.metadata == {"error": False}

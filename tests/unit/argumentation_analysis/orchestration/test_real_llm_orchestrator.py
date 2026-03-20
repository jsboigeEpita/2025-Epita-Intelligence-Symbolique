"""
Tests unitaires pour argumentation_analysis/orchestration/real_llm_orchestrator.py.

Couvre:
- LLMAnalysisRequest / LLMAnalysisResult dataclasses
- RealLLMOrchestrator init, config, metrics, cache
- analyze_text dispatch to 11 analysis types
- batch_analyze with semaphore limiting
- orchestrate_analysis flow
- Error handling and edge cases

Issue: #36 (test coverage)
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict
from datetime import datetime

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def orchestrator():
    """Create a RealLLMOrchestrator with no kernel (basic analyzers only)."""
    with patch(
        "argumentation_analysis.orchestration.real_llm_orchestrator.SemanticArgumentAnalyzer"
    ):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            RealLLMOrchestrator,
        )

        orch = RealLLMOrchestrator(mode="test", kernel=None, config=None)
        return orch


@pytest.fixture
def initialized_orchestrator(orchestrator):
    """Return an orchestrator that has been marked as initialized with basic analyzers."""
    orchestrator.is_initialized = True
    orchestrator.unified_analyzer = orchestrator._create_unified_analyzer()
    orchestrator.syntactic_analyzer = orchestrator._create_basic_syntactic_analyzer()
    orchestrator.semantic_analyzer = orchestrator._create_basic_semantic_analyzer()
    orchestrator.pragmatic_analyzer = orchestrator._create_basic_pragmatic_analyzer()
    orchestrator.entity_extractor = orchestrator._create_basic_entity_extractor()
    orchestrator.relation_extractor = orchestrator._create_basic_relation_extractor()
    orchestrator.consistency_validator = (
        orchestrator._create_basic_consistency_validator()
    )
    orchestrator.coherence_validator = orchestrator._create_basic_coherence_validator()
    return orchestrator


@pytest.fixture
def request_obj():
    """Create a simple LLMAnalysisRequest."""
    from argumentation_analysis.orchestration.real_llm_orchestrator import (
        LLMAnalysisRequest,
    )

    return LLMAnalysisRequest(
        text="Tous les hommes sont mortels. Socrate est un homme.",
        analysis_type="syntactic",
    )


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


# ============================================================================
# RealLLMOrchestrator construction
# ============================================================================


class TestRealLLMOrchestratorInit:
    """Tests for RealLLMOrchestrator initialization."""

    def test_default_mode(self, orchestrator):
        assert orchestrator.mode == "test"

    def test_default_config_values(self, orchestrator):
        cfg = orchestrator.config
        assert cfg["max_concurrent_analyses"] == 10
        assert cfg["cache_enabled"] is True
        assert cfg["retry_attempts"] == 3
        assert "unified_analysis" in cfg["analysis_types"]

    def test_custom_config(self):
        with patch(
            "argumentation_analysis.orchestration.real_llm_orchestrator.SemanticArgumentAnalyzer"
        ):
            from argumentation_analysis.orchestration.real_llm_orchestrator import (
                RealLLMOrchestrator,
            )

            custom = {"max_concurrent_analyses": 5, "cache_enabled": False}
            orch = RealLLMOrchestrator(config=custom)
            assert orch.config["max_concurrent_analyses"] == 5
            assert orch.config["cache_enabled"] is False

    def test_not_initialized_on_creation(self, orchestrator):
        assert orchestrator.is_initialized is False

    def test_empty_metrics_on_creation(self, orchestrator):
        m = orchestrator.metrics
        assert m["total_requests"] == 0
        assert m["successful_analyses"] == 0
        assert m["failed_analyses"] == 0
        assert m["cache_hits"] == 0
        assert m["cache_misses"] == 0
        assert m["average_processing_time"] == 0.0

    def test_empty_cache_on_creation(self, orchestrator):
        assert orchestrator.analysis_cache == {}

    def test_no_active_sessions(self, orchestrator):
        assert orchestrator.active_sessions == {}


# ============================================================================
# Metrics and cache management
# ============================================================================


class TestMetricsAndCache:
    """Tests for metrics tracking and cache operations."""

    def test_get_metrics_returns_copy(self, orchestrator):
        m = orchestrator.get_metrics()
        m["total_requests"] = 999
        assert orchestrator.metrics["total_requests"] == 0

    def test_reset_metrics(self, orchestrator):
        orchestrator.metrics["total_requests"] = 10
        orchestrator.metrics["successful_analyses"] = 8
        orchestrator.reset_metrics()
        assert orchestrator.metrics["total_requests"] == 0
        assert orchestrator.metrics["successful_analyses"] == 0

    def test_clear_cache(self, orchestrator):
        orchestrator.analysis_cache["key"] = "value"
        orchestrator.clear_cache()
        assert len(orchestrator.analysis_cache) == 0

    def test_get_status(self, orchestrator):
        status = orchestrator.get_status()
        assert status["is_initialized"] is False
        assert status["active_sessions"] == 0
        assert status["cache_size"] == 0

    def test_update_average_processing_time_first(self, orchestrator):
        orchestrator.metrics["successful_analyses"] = 1
        orchestrator._update_average_processing_time(2.0)
        assert orchestrator.metrics["average_processing_time"] == 2.0

    def test_update_average_processing_time_running(self, orchestrator):
        orchestrator.metrics["successful_analyses"] = 3
        orchestrator.metrics["average_processing_time"] = 1.0
        orchestrator._update_average_processing_time(4.0)
        # (1.0 * 2 + 4.0) / 3 = 2.0
        assert abs(orchestrator.metrics["average_processing_time"] - 2.0) < 0.01

    def test_cache_key_deterministic(self, orchestrator, request_obj):
        key1 = orchestrator._generate_cache_key(request_obj)
        key2 = orchestrator._generate_cache_key(request_obj)
        assert key1 == key2

    def test_cache_key_differs_for_different_text(self, orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        r1 = LLMAnalysisRequest(text="Hello", analysis_type="syntactic")
        r2 = LLMAnalysisRequest(text="World", analysis_type="syntactic")
        assert orchestrator._generate_cache_key(r1) != orchestrator._generate_cache_key(
            r2
        )

    def test_cache_roundtrip(self, orchestrator, request_obj):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisResult,
        )

        result = LLMAnalysisResult(
            request_id="r1",
            analysis_type="syntactic",
            result={"ok": True},
            confidence=0.9,
            processing_time=0.5,
            timestamp=datetime.now(),
        )
        orchestrator._cache_result(request_obj, result)
        cached = orchestrator._get_cached_result(request_obj)
        assert cached is result

    def test_cache_miss_returns_none(self, orchestrator, request_obj):
        assert orchestrator._get_cached_result(request_obj) is None


# ============================================================================
# Initialize
# ============================================================================


class TestInitialize:
    """Tests for the initialize() async method."""

    async def test_initialize_without_kernel_raises(self, orchestrator):
        """Without a kernel, _create_real_logical_analyzer raises ValueError."""
        result = await orchestrator.initialize()
        # initialize catches all exceptions and returns False
        assert result is False
        assert orchestrator.is_initialized is False

    async def test_initialize_with_mocked_kernel(self):
        """With a properly mocked kernel and patched logical analyzer, initialize succeeds."""
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            RealLLMOrchestrator,
        )
        from semantic_kernel.connectors.ai.chat_completion_client_base import (
            ChatCompletionClientBase,
        )

        mock_kernel = MagicMock()
        mock_service = MagicMock(spec=ChatCompletionClientBase)
        mock_kernel.services = {"default": mock_service}

        with patch(
            "argumentation_analysis.orchestration.real_llm_orchestrator.SemanticArgumentAnalyzer"
        ):
            orch = RealLLMOrchestrator(kernel=mock_kernel)
            # Patch _create_real_logical_analyzer to avoid PropositionalLogicAgent init issues
            orch._create_real_logical_analyzer = lambda: MagicMock()
            result = await orch.initialize()
            assert result is True
            assert orch.is_initialized is True


# ============================================================================
# Basic analyzer factories
# ============================================================================


class TestBasicAnalyzerFactories:
    """Tests for the _create_basic_*_analyzer factory methods."""

    def test_unified_analyzer(self, orchestrator):
        a = orchestrator._create_unified_analyzer()
        result = a.analyze_text("Test text.")
        assert "overall_quality" in result
        assert "structure_analysis" in result

    def test_syntactic_analyzer(self, orchestrator):
        a = orchestrator._create_basic_syntactic_analyzer()
        result = a.analyze("One. Two. Three.")
        assert "sentence_count" in result
        # split(".") on "One. Two. Three." gives 4 parts (trailing empty)
        assert result["sentence_count"] >= 3

    def test_semantic_analyzer(self, orchestrator):
        a = orchestrator._create_basic_semantic_analyzer()
        result = a.analyze("Complex vocabulary analysis.")
        assert result["vocabulary_complexity"] == "medium"

    def test_pragmatic_analyzer(self, orchestrator):
        a = orchestrator._create_basic_pragmatic_analyzer()
        result = a.analyze("I promise to help.", context={"formal": True})
        assert "speech_acts" in result

    def test_entity_extractor(self, orchestrator):
        a = orchestrator._create_basic_entity_extractor()
        entities = a.extract("Paris is a city.")
        assert isinstance(entities, list)
        assert len(entities) > 0

    def test_relation_extractor(self, orchestrator):
        a = orchestrator._create_basic_relation_extractor()
        relations = a.extract("A implies B.")
        assert isinstance(relations, list)

    def test_consistency_validator(self, orchestrator):
        a = orchestrator._create_basic_consistency_validator()
        result = a.validate("Consistent statement.")
        assert result["is_consistent"] is True

    def test_coherence_validator(self, orchestrator):
        a = orchestrator._create_basic_coherence_validator()
        result = a.validate("Coherent text.")
        assert result["is_coherent"] is True


# ============================================================================
# analyze_text dispatch
# ============================================================================


class TestAnalyzeText:
    """Tests for analyze_text() with various analysis types."""

    async def test_syntactic_analysis(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="One. Two.", analysis_type="syntactic")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.analysis_type == "syntactic"
        assert result.result["success"] is True
        assert result.confidence > 0

    async def test_semantic_analysis(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Deep meaning.", analysis_type="semantic")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["success"] is True
        assert result.result["analysis_type"] == "semantic"

    async def test_pragmatic_analysis(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="I promise.", analysis_type="pragmatic")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["success"] is True

    async def test_entity_extraction(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Paris.", analysis_type="entity_extraction")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["success"] is True
        assert "entities" in result.result

    async def test_relation_extraction(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(
            text="A implies B.", analysis_type="relation_extraction"
        )
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["success"] is True

    async def test_consistency_validation(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(
            text="Statement.", analysis_type="consistency_validation"
        )
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["success"] is True

    async def test_coherence_validation(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Text.", analysis_type="coherence_validation")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["success"] is True

    async def test_unified_analysis(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(
            text="Full analysis.", analysis_type="unified_analysis"
        )
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["success"] is True
        assert "results" in result.result

    async def test_simple_alias_maps_to_unified(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Simple.", analysis_type="simple")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.result["analysis_type"] == "unified_analysis"

    async def test_unsupported_type_returns_error(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Bad.", analysis_type="nonexistent_type")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.confidence == 0.0
        assert "error" in result.result

    async def test_string_input_auto_wraps(self, initialized_orchestrator):
        """When a plain string is passed, it should be wrapped in LLMAnalysisRequest."""
        result = await initialized_orchestrator.analyze_text(
            "Just a string.", analysis_type="syntactic"
        )
        assert result.analysis_type == "syntactic"
        assert result.result["success"] is True

    async def test_auto_initializes_if_needed(self, orchestrator):
        """analyze_text should call initialize() if not yet initialized."""
        orchestrator.initialize = AsyncMock(return_value=True)
        # After mocked init, set up basic analyzers
        orchestrator.is_initialized = False

        async def mock_init():
            orchestrator.is_initialized = True
            orchestrator.unified_analyzer = orchestrator._create_unified_analyzer()
            orchestrator.syntactic_analyzer = (
                orchestrator._create_basic_syntactic_analyzer()
            )
            orchestrator.semantic_analyzer = (
                orchestrator._create_basic_semantic_analyzer()
            )
            orchestrator.pragmatic_analyzer = (
                orchestrator._create_basic_pragmatic_analyzer()
            )
            orchestrator.entity_extractor = (
                orchestrator._create_basic_entity_extractor()
            )
            orchestrator.relation_extractor = (
                orchestrator._create_basic_relation_extractor()
            )
            orchestrator.consistency_validator = (
                orchestrator._create_basic_consistency_validator()
            )
            orchestrator.coherence_validator = (
                orchestrator._create_basic_coherence_validator()
            )
            return True

        orchestrator.initialize = mock_init
        result = await orchestrator.analyze_text("Test", analysis_type="syntactic")
        assert result.result["success"] is True


# ============================================================================
# Caching behavior
# ============================================================================


class TestCachingBehavior:
    """Tests for cache integration in analyze_text."""

    async def test_cache_hit_returns_cached(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
            LLMAnalysisResult,
        )

        req = LLMAnalysisRequest(text="Cached text.", analysis_type="syntactic")

        # Pre-populate cache
        cached = LLMAnalysisResult(
            request_id="cached_1",
            analysis_type="syntactic",
            result={"from_cache": True},
            confidence=0.99,
            processing_time=0.0,
            timestamp=datetime.now(),
        )
        initialized_orchestrator._cache_result(req, cached)

        result = await initialized_orchestrator.analyze_text(req)
        assert result.result.get("from_cache") is True
        assert initialized_orchestrator.metrics["cache_hits"] == 1

    async def test_cache_miss_increments_counter(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Not cached.", analysis_type="syntactic")
        await initialized_orchestrator.analyze_text(req)
        assert initialized_orchestrator.metrics["cache_misses"] == 1

    async def test_cache_disabled(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        initialized_orchestrator.config["cache_enabled"] = False
        req = LLMAnalysisRequest(text="No cache.", analysis_type="syntactic")
        await initialized_orchestrator.analyze_text(req)
        # No cache_hits or cache_misses should be updated
        assert initialized_orchestrator.metrics["cache_hits"] == 0
        assert initialized_orchestrator.metrics["cache_misses"] == 0

    async def test_successful_analysis_updates_metrics(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Metrics test.", analysis_type="syntactic")
        await initialized_orchestrator.analyze_text(req)
        m = initialized_orchestrator.metrics
        assert m["total_requests"] == 1
        assert m["successful_analyses"] == 1
        # Processing time may be 0.0 for fast in-process analyzers
        assert m["average_processing_time"] >= 0


# ============================================================================
# batch_analyze
# ============================================================================


class TestBatchAnalyze:
    """Tests for batch_analyze() method."""

    async def test_batch_analyze_multiple(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        requests = [
            LLMAnalysisRequest(text="First.", analysis_type="syntactic"),
            LLMAnalysisRequest(text="Second.", analysis_type="semantic"),
            LLMAnalysisRequest(text="Third.", analysis_type="coherence_validation"),
        ]
        results = await initialized_orchestrator.batch_analyze(requests)
        assert len(results) == 3
        for r in results:
            assert r.result["success"] is True

    async def test_batch_analyze_empty(self, initialized_orchestrator):
        results = await initialized_orchestrator.batch_analyze([])
        assert results == []

    async def test_batch_analyze_with_error(self, initialized_orchestrator):
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        requests = [
            LLMAnalysisRequest(text="Good.", analysis_type="syntactic"),
            LLMAnalysisRequest(text="Bad.", analysis_type="nonexistent_type"),
        ]
        results = await initialized_orchestrator.batch_analyze(requests)
        assert len(results) == 2
        # First should succeed, second has error in result
        assert results[0].result["success"] is True
        assert "error" in results[1].result


# ============================================================================
# orchestrate_analysis
# ============================================================================


class TestOrchestrateAnalysis:
    """Tests for orchestrate_analysis() high-level method."""

    async def test_orchestrate_returns_synthesis(self, initialized_orchestrator):
        result = await initialized_orchestrator.orchestrate_analysis("Test text.")
        assert "final_synthesis" in result
        assert "analysis_results" in result
        assert "processing_time_ms" in result

    async def test_orchestrate_includes_rhetorical(self, initialized_orchestrator):
        result = await initialized_orchestrator.orchestrate_analysis("With analyzers.")
        assert "rhetorical" in result["analysis_results"]

    async def test_orchestrate_auto_initializes(self, orchestrator):
        """orchestrate_analysis should call initialize() if needed."""
        orchestrator.is_initialized = False

        async def mock_init():
            orchestrator.is_initialized = True
            orchestrator.semantic_analyzer = (
                orchestrator._create_basic_semantic_analyzer()
            )
            return True

        orchestrator.initialize = mock_init
        result = await orchestrator.orchestrate_analysis("Auto init test.")
        assert "final_synthesis" in result


# ============================================================================
# Error handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in analyze_text."""

    async def test_failed_analysis_returns_error_result(self, initialized_orchestrator):
        """When an analyzer raises, analyze_text returns error result, not exception."""
        # Make syntactic analyzer raise
        initialized_orchestrator.syntactic_analyzer = MagicMock()
        initialized_orchestrator.syntactic_analyzer.analyze.side_effect = RuntimeError(
            "boom"
        )

        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Will fail.", analysis_type="syntactic")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.confidence == 0.0
        assert "error" in result.result
        assert initialized_orchestrator.metrics["failed_analyses"] == 1

    async def test_failed_analysis_has_request_id(self, initialized_orchestrator):
        initialized_orchestrator.syntactic_analyzer = MagicMock()
        initialized_orchestrator.syntactic_analyzer.analyze.side_effect = ValueError(
            "err"
        )

        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            LLMAnalysisRequest,
        )

        req = LLMAnalysisRequest(text="Error.", analysis_type="syntactic")
        result = await initialized_orchestrator.analyze_text(req)
        assert result.request_id.startswith("req_")
        assert result.processing_time >= 0


# ============================================================================
# _analyze_logical (requires kernel)
# ============================================================================


class TestLogicalAnalysis:
    """Tests for _analyze_logical which requires PropositionalLogicAgent."""

    async def test_logical_without_proper_agent(self, initialized_orchestrator):
        """When logical_analyzer is not PropositionalLogicAgent, returns error."""
        initialized_orchestrator.logical_analyzer = (
            MagicMock()
        )  # Not a PropositionalLogicAgent

        result = await initialized_orchestrator._analyze_logical("Test", {}, {})
        assert result["success"] is False
        assert "error" in result

# -*- coding: utf-8 -*-
"""
Unit tests for argumentation_analysis.orchestration.fact_checking_orchestrator.

Tests cover:
- FactCheckingRequest dataclass
- FactCheckingResponse dataclass
- FactCheckingOrchestrator class (init, analysis, metrics, health)
- Module-level singleton/convenience functions
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from enum import Enum

# ---------------------------------------------------------------------------
# We import the real AnalysisDepth enum so tests stay close to production.
# Everything else that touches external services is mocked.
# ---------------------------------------------------------------------------
from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
    AnalysisDepth,
)

# ---------------------------------------------------------------------------
# Module path constant for patching
# ---------------------------------------------------------------------------
MOD = "argumentation_analysis.orchestration.fact_checking_orchestrator"


# ---------------------------------------------------------------------------
# Helpers to build mock objects used across many tests
# ---------------------------------------------------------------------------


def _make_mock_comprehensive_result(**overrides):
    """Return a MagicMock that behaves like ComprehensiveAnalysisResult."""
    result = MagicMock()
    result.text_analyzed = overrides.get("text_analyzed", "sample text")
    result.analysis_timestamp = overrides.get(
        "analysis_timestamp", datetime(2026, 1, 1)
    )
    result.analysis_depth = overrides.get("analysis_depth", AnalysisDepth.STANDARD)
    result.family_results = overrides.get("family_results", {})
    result.factual_claims = overrides.get("factual_claims", [])
    result.fact_check_results = overrides.get("fact_check_results", [])
    result.overall_assessment = overrides.get("overall_assessment", {})
    result.strategic_insights = overrides.get("strategic_insights", {})
    result.recommendations = overrides.get("recommendations", [])
    result.to_dict.return_value = {"mocked": True}
    return result


def _make_verification_result(status_value="verified_true", confidence=0.9):
    """Return a mock verification result with .status.value and .confidence."""
    r = MagicMock()
    r.status.value = status_value
    r.confidence = confidence
    r.to_dict.return_value = {"status": status_value, "confidence": confidence}
    return r


def _build_plugin_registry():
    """Return a plugin_registry dict with mock taxonomy and verification plugins."""
    taxonomy = MagicMock()
    taxonomy.detect_and_classify = AsyncMock(return_value=[])
    taxonomy.get_family_statistics = AsyncMock(return_value={})
    taxonomy.detect_fallacies_with_families = MagicMock(return_value=[])

    verification = MagicMock()
    verification.verify_claims = AsyncMock(return_value=[])

    return {
        "taxonomy_explorer": taxonomy,
        "external_verification": verification,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the module-level singleton before each test."""
    import argumentation_analysis.orchestration.fact_checking_orchestrator as mod

    mod._global_fact_checking_orchestrator = None
    yield
    mod._global_fact_checking_orchestrator = None


@pytest.fixture
def plugin_registry():
    return _build_plugin_registry()


@pytest.fixture
def mock_family_analyzer():
    analyzer = MagicMock()
    analyzer.analyze_comprehensive = AsyncMock(
        return_value=_make_mock_comprehensive_result()
    )
    return analyzer


@pytest.fixture
def orchestrator(plugin_registry, mock_family_analyzer):
    """Build a fully-mocked FactCheckingOrchestrator."""
    with patch(f"{MOD}.get_family_analyzer", return_value=mock_family_analyzer), patch(
        f"{MOD}.FactClaimExtractor"
    ) as mock_extractor_cls:
        mock_extractor_cls.return_value = MagicMock()
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingOrchestrator,
        )

        orch = FactCheckingOrchestrator(
            plugin_registry=plugin_registry,
            api_config={"key": "value"},
        )
    # Replace family_analyzer with our controlled mock
    orch.family_analyzer = mock_family_analyzer
    return orch


# ===========================================================================
# 1. FactCheckingRequest
# ===========================================================================


class TestFactCheckingRequest:
    """Tests for the FactCheckingRequest dataclass."""

    def test_defaults(self):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        req = FactCheckingRequest(text="Hello world")
        assert req.text == "Hello world"
        assert req.analysis_depth == AnalysisDepth.STANDARD
        assert req.enable_fact_checking is True
        assert req.max_claims == 10
        assert req.max_fallacies == 15
        assert req.api_config is None
        assert req.context is None

    def test_custom_values(self):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        req = FactCheckingRequest(
            text="Test",
            analysis_depth=AnalysisDepth.EXPERT,
            enable_fact_checking=False,
            max_claims=5,
            max_fallacies=20,
            api_config={"api_key": "abc"},
            context={"source": "unit_test"},
        )
        assert req.analysis_depth == AnalysisDepth.EXPERT
        assert req.enable_fact_checking is False
        assert req.max_claims == 5
        assert req.max_fallacies == 20
        assert req.api_config == {"api_key": "abc"}
        assert req.context == {"source": "unit_test"}

    def test_all_analysis_depths(self):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        for depth in AnalysisDepth:
            req = FactCheckingRequest(text="t", analysis_depth=depth)
            assert req.analysis_depth is depth


# ===========================================================================
# 2. FactCheckingResponse
# ===========================================================================


class TestFactCheckingResponse:
    """Tests for the FactCheckingResponse dataclass."""

    def test_init_basic(self):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingResponse,
        )

        comp = _make_mock_comprehensive_result()
        ts = datetime(2026, 3, 1, 12, 0, 0)
        resp = FactCheckingResponse(
            request_id="req-1",
            text_analyzed="short text",
            analysis_timestamp=ts,
            comprehensive_result=comp,
            processing_time=1.23,
            status="completed",
        )
        assert resp.request_id == "req-1"
        assert resp.status == "completed"
        assert resp.error_message is None
        assert resp.processing_time == 1.23

    def test_to_dict_short_text(self):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingResponse,
        )

        comp = _make_mock_comprehensive_result()
        ts = datetime(2026, 3, 1, 12, 0, 0)
        resp = FactCheckingResponse(
            request_id="req-2",
            text_analyzed="short",
            analysis_timestamp=ts,
            comprehensive_result=comp,
            processing_time=0.5,
            status="completed",
        )
        d = resp.to_dict()
        assert d["text_analyzed"] == "short"
        assert d["request_id"] == "req-2"
        assert d["status"] == "completed"
        assert d["analysis_timestamp"] == ts.isoformat()
        assert d["comprehensive_result"] == {"mocked": True}

    def test_to_dict_truncates_long_text(self):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingResponse,
        )

        long_text = "A" * 300
        comp = _make_mock_comprehensive_result()
        resp = FactCheckingResponse(
            request_id="req-3",
            text_analyzed=long_text,
            analysis_timestamp=datetime.now(),
            comprehensive_result=comp,
            processing_time=0.1,
            status="completed",
        )
        d = resp.to_dict()
        assert len(d["text_analyzed"]) == 203  # 200 chars + "..."
        assert d["text_analyzed"].endswith("...")

    def test_to_dict_with_error(self):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingResponse,
        )

        comp = _make_mock_comprehensive_result()
        resp = FactCheckingResponse(
            request_id="req-err",
            text_analyzed="text",
            analysis_timestamp=datetime.now(),
            comprehensive_result=comp,
            processing_time=0.0,
            status="error",
            error_message="Something failed",
        )
        d = resp.to_dict()
        assert d["status"] == "error"
        assert d["error_message"] == "Something failed"


# ===========================================================================
# 3. FactCheckingOrchestrator.__init__
# ===========================================================================


class TestOrchestratorInit:
    """Tests for FactCheckingOrchestrator initialization."""

    def test_init_with_plugin_registry(self, plugin_registry):
        with patch(f"{MOD}.get_family_analyzer") as mock_gfa, patch(
            f"{MOD}.FactClaimExtractor"
        ):
            mock_gfa.return_value = MagicMock()
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                FactCheckingOrchestrator,
            )

            orch = FactCheckingOrchestrator(plugin_registry=plugin_registry)

        assert orch.taxonomy_plugin is plugin_registry["taxonomy_explorer"]
        assert orch.verification_plugin is plugin_registry["external_verification"]
        assert orch.analysis_count == 0
        assert orch.error_count == 0

    def test_init_without_registry_uses_singletons(self):
        mock_tm = MagicMock()
        mock_vs = MagicMock()
        with patch(f"{MOD}.get_taxonomy_manager", return_value=mock_tm), patch(
            f"{MOD}.get_verification_service", return_value=mock_vs
        ), patch(f"{MOD}.get_family_analyzer") as mock_gfa, patch(
            f"{MOD}.FactClaimExtractor"
        ):
            mock_gfa.return_value = MagicMock()
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                FactCheckingOrchestrator,
            )

            orch = FactCheckingOrchestrator()

        assert orch.taxonomy_plugin is mock_tm
        assert orch.verification_plugin is mock_vs

    def test_init_raises_if_taxonomy_missing(self):
        registry = {"taxonomy_explorer": None, "external_verification": MagicMock()}
        with patch(f"{MOD}.FactClaimExtractor"):
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                FactCheckingOrchestrator,
            )

            with pytest.raises(ValueError, match="taxonomy_explorer"):
                FactCheckingOrchestrator(plugin_registry=registry)

    def test_init_raises_if_verification_missing(self):
        registry = {"taxonomy_explorer": MagicMock(), "external_verification": None}
        with patch(f"{MOD}.FactClaimExtractor"):
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                FactCheckingOrchestrator,
            )

            with pytest.raises(ValueError, match="external_verification"):
                FactCheckingOrchestrator(plugin_registry=registry)

    def test_init_api_config_defaults_to_empty_dict(self, plugin_registry):
        with patch(f"{MOD}.get_family_analyzer") as mock_gfa, patch(
            f"{MOD}.FactClaimExtractor"
        ):
            mock_gfa.return_value = MagicMock()
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                FactCheckingOrchestrator,
            )

            orch = FactCheckingOrchestrator(plugin_registry=plugin_registry)
        assert orch.api_config == {}

    def test_backward_compat_aliases(self, plugin_registry):
        with patch(f"{MOD}.get_family_analyzer") as mock_gfa, patch(
            f"{MOD}.FactClaimExtractor"
        ):
            mock_gfa.return_value = MagicMock()
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                FactCheckingOrchestrator,
            )

            orch = FactCheckingOrchestrator(plugin_registry=plugin_registry)
        assert orch.taxonomy_manager is orch.taxonomy_plugin
        assert orch.verification_service is orch.verification_plugin


# ===========================================================================
# 4. analyze_with_fact_checking
# ===========================================================================


class TestAnalyzeWithFactChecking:
    """Tests for the main analysis method."""

    async def test_success(self, orchestrator, mock_family_analyzer):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        req = FactCheckingRequest(text="Test text for analysis")
        resp = await orchestrator.analyze_with_fact_checking(req)

        assert resp.status == "completed"
        assert resp.text_analyzed == "Test text for analysis"
        assert resp.error_message is None
        assert resp.processing_time >= 0
        mock_family_analyzer.analyze_comprehensive.assert_awaited_once()

    async def test_updates_metrics_on_success(self, orchestrator):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        assert orchestrator.analysis_count == 0
        req = FactCheckingRequest(text="Test")
        await orchestrator.analyze_with_fact_checking(req)
        assert orchestrator.analysis_count == 1
        assert orchestrator.total_processing_time >= 0  # may be 0.0 on fast machines
        assert orchestrator.error_count == 0

    async def test_error_handling(self, orchestrator, mock_family_analyzer):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        mock_family_analyzer.analyze_comprehensive.side_effect = RuntimeError("boom")
        req = FactCheckingRequest(text="Test")
        resp = await orchestrator.analyze_with_fact_checking(req)

        assert resp.status == "error"
        assert resp.error_message == "boom"
        assert orchestrator.error_count == 1

    async def test_error_response_contains_comprehensive_result(
        self, orchestrator, mock_family_analyzer
    ):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        mock_family_analyzer.analyze_comprehensive.side_effect = ValueError("bad input")
        req = FactCheckingRequest(text="Test", analysis_depth=AnalysisDepth.BASIC)

        with patch(f"{MOD}.ComprehensiveAnalysisResult") as mock_car:
            mock_car.return_value = _make_mock_comprehensive_result()
            resp = await orchestrator.analyze_with_fact_checking(req)

        assert resp.status == "error"
        assert resp.comprehensive_result is not None

    async def test_request_id_is_uuid(self, orchestrator):
        import uuid
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        req = FactCheckingRequest(text="Test")
        resp = await orchestrator.analyze_with_fact_checking(req)
        # Should be a valid UUID
        uuid.UUID(resp.request_id)


# ===========================================================================
# 5. quick_fact_check
# ===========================================================================


class TestQuickFactCheck:
    """Tests for the quick_fact_check method."""

    async def test_success_with_claims(self, orchestrator, plugin_registry):
        mock_claim = MagicMock()
        orchestrator.fact_extractor.extract_factual_claims.return_value = [mock_claim]

        mock_verif = _make_verification_result("verified_true", 0.95)
        plugin_registry["external_verification"].verify_claims = AsyncMock(
            return_value=[mock_verif]
        )

        result = await orchestrator.quick_fact_check(
            "Some text with facts", max_claims=3
        )

        assert result["status"] == "completed"
        assert result["claims_count"] == 1
        assert len(result["verifications"]) == 1
        assert "summary" in result
        assert result["processing_time"] >= 0

    async def test_no_claims_found(self, orchestrator):
        orchestrator.fact_extractor.extract_factual_claims.return_value = []

        result = await orchestrator.quick_fact_check("No facts here")

        assert result["status"] == "no_claims"
        assert "message" in result

    async def test_error_handling(self, orchestrator):
        orchestrator.fact_extractor.extract_factual_claims.side_effect = Exception(
            "fail"
        )

        result = await orchestrator.quick_fact_check("Some text")

        assert result["status"] == "error"
        assert result["error"] == "fail"
        assert "processing_time" in result

    async def test_max_claims_passed_to_extractor(self, orchestrator):
        orchestrator.fact_extractor.extract_factual_claims.return_value = []
        await orchestrator.quick_fact_check("text", max_claims=7)
        orchestrator.fact_extractor.extract_factual_claims.assert_called_once_with(
            "text", 7
        )


# ===========================================================================
# 6. analyze_fallacy_families_only
# ===========================================================================


class TestAnalyzeFallacyFamiliesOnly:
    """Tests for fallacy-only analysis."""

    async def test_success(self, orchestrator, plugin_registry):
        mock_fallacy = MagicMock()
        mock_fallacy.to_dict.return_value = {"type": "ad_hominem"}
        plugin_registry["taxonomy_explorer"].detect_and_classify = AsyncMock(
            return_value=[mock_fallacy]
        )
        plugin_registry["taxonomy_explorer"].get_family_statistics = AsyncMock(
            return_value={"emotional_appeals": 1}
        )

        result = await orchestrator.analyze_fallacy_families_only(
            "Argument with fallacy", depth=AnalysisDepth.COMPREHENSIVE
        )

        assert result["status"] == "completed"
        assert len(result["fallacies_detected"]) == 1
        assert result["analysis_depth"] == "comprehensive"
        assert result["processing_time"] >= 0

    async def test_no_fallacies(self, orchestrator, plugin_registry):
        plugin_registry["taxonomy_explorer"].detect_and_classify = AsyncMock(
            return_value=[]
        )
        plugin_registry["taxonomy_explorer"].get_family_statistics = AsyncMock(
            return_value={}
        )

        result = await orchestrator.analyze_fallacy_families_only("Clean argument")

        assert result["status"] == "completed"
        assert result["fallacies_detected"] == []

    async def test_error_handling(self, orchestrator, plugin_registry):
        plugin_registry["taxonomy_explorer"].detect_and_classify = AsyncMock(
            side_effect=RuntimeError("taxonomy error")
        )

        result = await orchestrator.analyze_fallacy_families_only("text")

        assert result["status"] == "error"
        assert "taxonomy error" in result["error"]

    async def test_default_depth(self, orchestrator, plugin_registry):
        plugin_registry["taxonomy_explorer"].detect_and_classify = AsyncMock(
            return_value=[]
        )
        plugin_registry["taxonomy_explorer"].get_family_statistics = AsyncMock(
            return_value={}
        )

        result = await orchestrator.analyze_fallacy_families_only("text")
        assert result["analysis_depth"] == "standard"


# ===========================================================================
# 7. _generate_quick_summary
# ===========================================================================


class TestGenerateQuickSummary:
    """Tests for the summary generation helper."""

    def test_empty_results(self, orchestrator):
        summary = orchestrator._generate_quick_summary([])
        assert summary["total_claims"] == 0
        assert summary["verified_true"] == 0
        assert summary["average_confidence"] == 0.0
        assert summary["credibility_score"] == 0.0

    def test_all_verified_true(self, orchestrator):
        results = [
            _make_verification_result("verified_true", 0.9),
            _make_verification_result("verified_true", 0.8),
        ]
        summary = orchestrator._generate_quick_summary(results)
        assert summary["verified_true"] == 2
        assert summary["verified_false"] == 0
        assert summary["credibility_score"] == 1.0
        assert summary["average_confidence"] == pytest.approx(0.85)

    def test_all_verified_false(self, orchestrator):
        results = [
            _make_verification_result("verified_false", 0.7),
            _make_verification_result("verified_false", 0.6),
        ]
        summary = orchestrator._generate_quick_summary(results)
        assert summary["verified_false"] == 2
        assert summary["credibility_score"] == pytest.approx(0.2)  # 1.0 - 1.0*0.8

    def test_mixed_statuses(self, orchestrator):
        results = [
            _make_verification_result("verified_true", 0.9),
            _make_verification_result("verified_false", 0.8),
            _make_verification_result("disputed", 0.5),
            _make_verification_result("unverifiable", 0.3),
        ]
        summary = orchestrator._generate_quick_summary(results)
        assert summary["verified_true"] == 1
        assert summary["verified_false"] == 1
        assert summary["disputed"] == 1
        assert summary["unverifiable"] == 1
        assert summary["total_claims"] == 4
        # false_ratio = 1/4 = 0.25, disputed_ratio = 1/4 = 0.25
        # credibility = max(0, 1.0 - 0.25*0.8 - 0.25*0.4) = 1.0 - 0.2 - 0.1 = 0.7
        assert summary["credibility_score"] == pytest.approx(0.7)
        assert summary["average_confidence"] == pytest.approx(0.625)

    def test_unknown_status_counted_as_unverifiable(self, orchestrator):
        results = [_make_verification_result("some_unknown_status", 0.5)]
        summary = orchestrator._generate_quick_summary(results)
        assert summary["unverifiable"] == 1
        assert summary["verified_true"] == 0


# ===========================================================================
# 8. batch_analyze
# ===========================================================================


class TestBatchAnalyze:
    """Tests for batch analysis."""

    async def test_multiple_texts(self, orchestrator, mock_family_analyzer):
        texts = ["Text A", "Text B", "Text C"]
        results = await orchestrator.batch_analyze(texts)

        assert len(results) == 3
        for r in results:
            assert r.status == "completed"
        # Each text triggers one call
        assert mock_family_analyzer.analyze_comprehensive.await_count == 3

    async def test_handles_exceptions_in_batch(
        self, orchestrator, mock_family_analyzer
    ):
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("fail on second")
            return _make_mock_comprehensive_result()

        mock_family_analyzer.analyze_comprehensive = AsyncMock(side_effect=side_effect)

        texts = ["Text A", "Text B", "Text C"]

        with patch(f"{MOD}.ComprehensiveAnalysisResult") as mock_car:
            mock_car.return_value = _make_mock_comprehensive_result()
            results = await orchestrator.batch_analyze(texts)

        assert len(results) == 3
        # The second one should be an error (caught by analyze_with_fact_checking)
        statuses = [r.status for r in results]
        assert "error" in statuses

    async def test_empty_batch(self, orchestrator):
        results = await orchestrator.batch_analyze([])
        assert results == []

    async def test_batch_uses_given_depth(self, orchestrator, mock_family_analyzer):
        await orchestrator.batch_analyze(["text"], analysis_depth=AnalysisDepth.EXPERT)
        call_kwargs = mock_family_analyzer.analyze_comprehensive.call_args
        # The depth is passed via the request to analyze_with_fact_checking
        # which calls family_analyzer.analyze_comprehensive(text=..., depth=...)
        assert call_kwargs.kwargs.get("depth") == AnalysisDepth.EXPERT


# ===========================================================================
# 9. get_performance_metrics
# ===========================================================================


class TestPerformanceMetrics:
    """Tests for performance metrics."""

    def test_initial_metrics(self, orchestrator):
        metrics = orchestrator.get_performance_metrics()
        assert metrics["total_analyses"] == 0
        assert metrics["average_processing_time"] == 0.0
        assert metrics["error_count"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["success_rate"] == 1.0

    async def test_metrics_after_analysis(self, orchestrator):
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        await orchestrator.analyze_with_fact_checking(FactCheckingRequest(text="Test"))
        metrics = orchestrator.get_performance_metrics()
        assert metrics["total_analyses"] == 1
        assert metrics["total_processing_time"] >= 0  # may be 0.0 on fast machines
        assert metrics["error_count"] == 0
        assert metrics["success_rate"] == 1.0

    async def test_metrics_after_error(self, orchestrator, mock_family_analyzer):
        """After one error, error_count is 1 but analysis_count stays 0
        (the source only increments analysis_count on success).
        With analysis_count=0, error_rate defaults to 0.0."""
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        mock_family_analyzer.analyze_comprehensive.side_effect = Exception("err")

        with patch(f"{MOD}.ComprehensiveAnalysisResult") as mock_car:
            mock_car.return_value = _make_mock_comprehensive_result()
            await orchestrator.analyze_with_fact_checking(
                FactCheckingRequest(text="Test")
            )

        metrics = orchestrator.get_performance_metrics()
        assert metrics["error_count"] == 1
        # analysis_count is 0 (only incremented on success), so error_rate = 0.0
        assert metrics["total_analyses"] == 0
        assert metrics["error_rate"] == 0.0

    async def test_metrics_mixed_success_and_error(
        self, orchestrator, mock_family_analyzer
    ):
        """After one success + one error, error_rate = 1/1 = 1.0 (only successes counted)."""
        from argumentation_analysis.orchestration.fact_checking_orchestrator import (
            FactCheckingRequest,
        )

        # First call succeeds
        await orchestrator.analyze_with_fact_checking(FactCheckingRequest(text="ok"))

        # Second call fails
        mock_family_analyzer.analyze_comprehensive.side_effect = Exception("err")
        with patch(f"{MOD}.ComprehensiveAnalysisResult") as mock_car:
            mock_car.return_value = _make_mock_comprehensive_result()
            await orchestrator.analyze_with_fact_checking(
                FactCheckingRequest(text="fail")
            )

        metrics = orchestrator.get_performance_metrics()
        assert metrics["total_analyses"] == 1
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == 1.0
        assert metrics["success_rate"] == 0.0


# ===========================================================================
# 10. health_check
# ===========================================================================


class TestHealthCheck:
    """Tests for the health_check method."""

    async def test_healthy_state(self, orchestrator):
        orchestrator.fact_extractor.extract_factual_claims.return_value = [MagicMock()]
        orchestrator.taxonomy_manager.detect_fallacies_with_families.return_value = []

        health = await orchestrator.health_check()

        assert health["status"] == "healthy"
        assert "timestamp" in health
        assert health["components"]["fact_extractor"]["status"] == "ok"
        assert health["components"]["family_analyzer"]["status"] == "ok"

    async def test_extractor_error(self, orchestrator):
        orchestrator.fact_extractor.extract_factual_claims.side_effect = Exception(
            "broken"
        )
        orchestrator.taxonomy_manager.detect_fallacies_with_families.return_value = []

        health = await orchestrator.health_check()

        assert health["components"]["fact_extractor"]["status"] == "error"
        assert "broken" in health["components"]["fact_extractor"]["error"]

    async def test_taxonomy_fallback_to_plugin(self, orchestrator, plugin_registry):
        # Sync service call fails -> falls back to async plugin
        orchestrator.taxonomy_manager.detect_fallacies_with_families.side_effect = (
            Exception("sync fail")
        )
        plugin_registry["taxonomy_explorer"].detect_and_classify = AsyncMock(
            return_value=[MagicMock()]
        )
        orchestrator.fact_extractor.extract_factual_claims.return_value = []

        health = await orchestrator.health_check()

        assert health["components"]["taxonomy_plugin"]["status"] == "ok"


# ===========================================================================
# 11. get_api_config / update_api_config
# ===========================================================================


class TestApiConfig:
    """Tests for API config getter/setter."""

    def test_get_api_config_returns_copy(self, orchestrator):
        config = orchestrator.get_api_config()
        assert config == {"key": "value"}
        # Modifying copy should not affect original
        config["new_key"] = "new_value"
        assert "new_key" not in orchestrator.api_config

    def test_update_api_config(self, orchestrator):
        orchestrator.update_api_config({"new_key": "new_val"})
        assert orchestrator.api_config["new_key"] == "new_val"
        # Original key should still be present
        assert orchestrator.api_config["key"] == "value"

    def test_update_api_config_overwrites_existing(self, orchestrator):
        orchestrator.update_api_config({"key": "overwritten"})
        assert orchestrator.api_config["key"] == "overwritten"


# ===========================================================================
# 12. Module-level singleton & convenience functions
# ===========================================================================


class TestModuleLevelFunctions:
    """Tests for singleton factory and convenience functions."""

    def test_get_taxonomy_manager_shim(self):
        with patch(
            "argumentation_analysis.services.fallacy_taxonomy_service.get_taxonomy_manager",
            return_value="tm_instance",
        ):
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                get_taxonomy_manager,
            )

            result = get_taxonomy_manager()
            assert result == "tm_instance"

    def test_get_verification_service_shim(self):
        with patch(
            "argumentation_analysis.services.fact_verification_service.get_verification_service",
            return_value="vs_instance",
        ):
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                get_verification_service,
            )

            result = get_verification_service()
            assert result == "vs_instance"

    def test_singleton_factory_creates_once(self):
        mock_tm = MagicMock()
        mock_vs = MagicMock()
        with patch(f"{MOD}.get_taxonomy_manager", return_value=mock_tm), patch(
            f"{MOD}.get_verification_service", return_value=mock_vs
        ), patch(f"{MOD}.get_family_analyzer") as mock_gfa, patch(
            f"{MOD}.FactClaimExtractor"
        ):
            mock_gfa.return_value = MagicMock()
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                get_fact_checking_orchestrator,
            )

            orch1 = get_fact_checking_orchestrator(api_config={"k": "v"})
            orch2 = get_fact_checking_orchestrator()
            assert orch1 is orch2

    async def test_quick_analyze_text(self):
        mock_orch = MagicMock()
        mock_resp = MagicMock()
        mock_resp.to_dict.return_value = {"result": "ok"}
        mock_orch.analyze_with_fact_checking = AsyncMock(return_value=mock_resp)

        with patch(f"{MOD}.get_fact_checking_orchestrator", return_value=mock_orch):
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                quick_analyze_text,
            )

            result = await quick_analyze_text("Hello", api_config={"k": "v"})

        assert result == {"result": "ok"}
        mock_orch.analyze_with_fact_checking.assert_awaited_once()

    async def test_quick_fact_check_only(self):
        mock_orch = MagicMock()
        mock_orch.quick_fact_check = AsyncMock(return_value={"status": "no_claims"})

        with patch(f"{MOD}.get_fact_checking_orchestrator", return_value=mock_orch):
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                quick_fact_check_only,
            )

            result = await quick_fact_check_only("text", api_config={"k": "v"})

        assert result == {"status": "no_claims"}

    async def test_quick_fallacy_analysis_only(self):
        mock_orch = MagicMock()
        mock_orch.analyze_fallacy_families_only = AsyncMock(
            return_value={"status": "completed"}
        )

        with patch(f"{MOD}.get_fact_checking_orchestrator", return_value=mock_orch):
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                quick_fallacy_analysis_only,
            )

            result = await quick_fallacy_analysis_only("text")

        assert result == {"status": "completed"}

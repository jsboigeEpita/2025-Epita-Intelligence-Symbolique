#!/usr/bin/env python3
"""
Tests for pipeline utilities.

Issue #215: Feature parity with archived RealLLMOrchestrator
"""

import asyncio
import pytest
import time

from argumentation_analysis.orchestration.pipeline_utils import (
    AnalysisCache,
    PipelineMetrics,
    BatchRequest,
    BatchResult,
    run_batch_analysis,
)


class TestAnalysisCache:
    """Tests for TTL-based analysis cache."""

    def test_cache_entry_expiration(self):
        """Test that cache entries expire correctly."""
        cache = AnalysisCache(ttl_seconds=0.1, max_size=10)

        # Set an entry
        cache.set("text1", "type1", {"result": "old"})

        # Should be present immediately
        assert cache.get("text1", "type1") == {"result": "old"}

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired now
        assert cache.get("text1", "type1") is None

    def test_cache_hit_and_miss(self):
        """Test cache hits and misses."""
        cache = AnalysisCache(ttl_seconds=3600)

        # Test miss
        assert cache.get("text", "type") is None

        # Test set and hit
        cache.set("text", "type", {"result": "value"})
        assert cache.get("text", "type") == {"result": "value"}
        assert cache.get("text", "type") == {"result": "value"}  # Second hit

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_cache_lfu_eviction(self):
        """Test LFU (Least Frequently Used) eviction when cache is full."""
        cache = AnalysisCache(ttl_seconds=3600, max_size=3)

        # Fill cache
        cache.set("text1", "type", {"id": 1})
        cache.set("text2", "type", {"id": 2})
        cache.set("text3", "type", {"id": 3})

        # Access text1 to increase its hit count
        cache.get("text1", "type")
        cache.get("text1", "type")

        # Add new entry - should evict text2 (fewest hits)
        cache.set("text4", "type", {"id": 4})

        # text2 should be evicted
        assert cache.get("text2", "type") is None
        # text1 should still be there
        assert cache.get("text1", "type") == {"id": 1}

        stats = cache.get_stats()
        assert stats["evictions"] == 1


class TestPipelineMetrics:
    """Tests for metrics collection."""

    def test_record_and_summary(self):
        """Test recording metrics and getting summary."""
        metrics = PipelineMetrics()

        # Record some analyses
        metrics.record("informal", 0.1, True, confidence=0.8)
        metrics.record("logical", 0.2, True, confidence=0.9)
        metrics.record("quality", 0.15, False, error="Failed")

        summary = metrics.get_summary()
        assert summary["total_analyses"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == 2/3

    def test_confidence_aggregation(self):
        """Test confidence score aggregation."""
        metrics = PipelineMetrics()

        metrics.record("phase1", 0.1, True, confidence=0.8)
        metrics.record("phase2", 0.1, True, confidence=0.9)
        metrics.record("phase3", 0.1, True, confidence=0.7)

        summary = metrics.get_summary()
        assert "avg_confidence" in summary
        assert abs(summary["avg_confidence"] - 0.8) < 0.01

    def test_reset_metrics(self):
        """Test metrics reset."""
        metrics = PipelineMetrics()

        metrics.record("phase1", 0.1, True)
        assert metrics.get_summary()["total_analyses"] == 1

        metrics.reset()
        assert metrics.get_summary()["total_analyses"] == 0

    def test_get_recent(self):
        """Test getting recent metrics."""
        metrics = PipelineMetrics()

        for i in range(5):
            metrics.record(f"type{i}", 0.1, True)

        recent = metrics.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[-1]["analysis_type"] == "type4"


class TestBatchAnalysis:
    """Tests for batch analysis functionality."""

    @pytest.mark.asyncio
    async def test_batch_success(self):
        """Test successful batch analysis."""
        cache = AnalysisCache(ttl_seconds=60)
        metrics = PipelineMetrics()

        requests = [
            BatchRequest(id="1", text="text1", analysis_type="test"),
            BatchRequest(id="2", text="text2", analysis_type="test"),
            BatchRequest(id="3", text="text3", analysis_type="test"),
        ]

        async def mock_analyze(text: str, analysis_type: str, params=None):
            await asyncio.sleep(0.01)
            return {"text": text, "type": analysis_type, "result": "ok"}

        results = await run_batch_analysis(
            requests,
            analyze_fn=mock_analyze,
            cache=cache,
            metrics=metrics,
            max_concurrent=2,
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].result["text"] == "text1"

    @pytest.mark.asyncio
    async def test_batch_with_cache(self):
        """Test that batch analysis uses cache."""
        cache = AnalysisCache(ttl_seconds=60)
        call_count = 0

        async def counting_analyze(text: str, analysis_type: str, params=None):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {"text": text}

        requests = [
            BatchRequest(id="1", text="same", analysis_type="test"),
            BatchRequest(id="2", text="same", analysis_type="test"),  # Duplicate
        ]

        # Run with max_concurrent=1 to ensure sequential execution
        results = await run_batch_analysis(
            requests,
            analyze_fn=counting_analyze,
            cache=cache,
            max_concurrent=1,
        )

        # Second request should hit cache
        stats = cache.get_stats()
        # With sequential execution, first call populates cache, second hits
        assert stats["hits"] >= 1 or call_count == 1  # Either cache hit or only 1 call

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self):
        """Test batch analysis with partial failures."""
        metrics = PipelineMetrics()

        async def failing_analyze(text: str, analysis_type: str, params=None):
            if "fail" in text:
                raise ValueError("Intentional failure")
            return {"text": text}

        requests = [
            BatchRequest(id="1", text="good1", analysis_type="test"),
            BatchRequest(id="2", text="fail1", analysis_type="test"),
            BatchRequest(id="3", text="good2", analysis_type="test"),
        ]

        results = await run_batch_analysis(
            requests,
            analyze_fn=failing_analyze,
            metrics=metrics,
            max_concurrent=2,
        )

        assert len(results) == 3
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        assert len(successful) == 2
        assert len(failed) == 1
        assert failed[0].error is not None  # error is a string attribute, not in result

    @pytest.mark.asyncio
    async def test_batch_metrics_tracking(self):
        """Test that metrics are properly recorded during batch."""
        metrics = PipelineMetrics()

        async def mock_analyze(text: str, analysis_type: str, params=None):
            return {"text": text, "confidence": 0.9}

        requests = [
            BatchRequest(id="1", text="text1", analysis_type="informal"),
            BatchRequest(id="2", text="text2", analysis_type="logical"),
        ]

        await run_batch_analysis(
            requests,
            analyze_fn=mock_analyze,
            metrics=metrics,
            max_concurrent=2,
        )

        summary = metrics.get_summary()
        assert summary["total_analyses"] == 2
        assert summary["successful"] == 2
        assert summary["avg_confidence"] == 0.9

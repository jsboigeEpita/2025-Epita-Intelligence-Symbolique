#!/usr/bin/env python3
"""
Pipeline Utilities - Caching, Metrics, and Batch Processing
============================================================

Utility classes and functions to enhance UnifiedPipeline with:
- TTL-based caching for analysis results
- Structured metrics collection
- Batch analysis with concurrency control

Issue #215: Feature parity with archived RealLLMOrchestrator
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, ParamSpec

logger = logging.getLogger("PipelineUtils")

P = ParamSpec("P")
T = TypeVar("T")


# =============================================================================
# 1. TTL-BASED CACHING
# =============================================================================

@dataclass
class CacheEntry:
    """A cached result with metadata."""
    value: Any
    created_at: float
    ttl_seconds: float
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds <= 0:
            return False  # Never expires
        return (time.time() - self.created_at) > self.ttl_seconds


class AnalysisCache:
    """
    TTL-based cache for analysis results.

    Provides caching similar to the archived RealLLMOrchestrator's cache
    with configurable TTL and automatic cleanup.

    Usage:
        cache = AnalysisCache(ttl_seconds=3600, max_size=1000)
        cached = cache.get(text, analysis_type, parameters)
        if cached is None:
            result = await analyze(text)
            cache.set(text, analysis_type, result, parameters)
    """

    def __init__(self, ttl_seconds: float = 3600, max_size: int = 1000):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
            max_size: Maximum number of entries before LRU eviction
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    def _generate_key(
        self,
        text: str,
        analysis_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a unique cache key from inputs."""
        content = f"{text}:{analysis_type}:{json.dumps(parameters or {}, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(
        self,
        text: str,
        analysis_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get a cached result if available and not expired.

        Returns:
            The cached value or None if not found/expired.
        """
        key = self._generate_key(text, analysis_type, parameters)
        entry = self._cache.get(key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired():
            del self._cache[key]
            self._stats["expirations"] += 1
            self._stats["misses"] += 1
            return None

        entry.hits += 1
        self._stats["hits"] += 1
        return entry.value

    def set(
        self,
        text: str,
        analysis_type: str,
        result: Any,
        parameters: Optional[Dict[str, Any]] = None,
        ttl_override: Optional[float] = None
    ) -> None:
        """
        Cache a result.

        Args:
            text: The analyzed text
            analysis_type: Type of analysis
            result: The result to cache
            parameters: Optional parameters used
            ttl_override: Override default TTL for this entry
        """
        # Evict if at capacity (LRU: remove entry with fewest hits)
        if len(self._cache) >= self._max_size:
            lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].hits)
            del self._cache[lru_key]
            self._stats["evictions"] += 1

        key = self._generate_key(text, analysis_type, parameters)
        self._cache[key] = CacheEntry(
            value=result,
            created_at=time.time(),
            ttl_seconds=ttl_override if ttl_override is not None else self._ttl_seconds,
        )

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self._max_size,
            "hit_rate": round(hit_rate, 3),
            "ttl_seconds": self._ttl_seconds,
        }


def cached_analysis(
    cache: AnalysisCache,
    analysis_type: str,
    parameters: Optional[Dict[str, Any]] = None
):
    """
    Decorator to cache analysis function results.

    Usage:
        cache = AnalysisCache()

        @cached_analysis(cache, "informal")
        async def analyze_informal(text: str) -> Dict:
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Assume first arg is text
            text = args[0] if args else kwargs.get("text", "")

            # Check cache
            cached_result = cache.get(text, analysis_type, parameters)
            if cached_result is not None:
                logger.debug(f"Cache hit for {analysis_type}")
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            cache.set(text, analysis_type, result, parameters)
            return result

        return wrapper
    return decorator


# =============================================================================
# 2. STRUCTURED METRICS COLLECTION
# =============================================================================

@dataclass
class AnalysisMetric:
    """A single analysis metric entry."""
    timestamp: float
    analysis_type: str
    duration_seconds: float
    success: bool
    confidence: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PipelineMetrics:
    """
    Structured metrics collector for pipeline analysis.

    Replaces the basic metrics dict from archived RealLLMOrchestrator with
    a more comprehensive tracking system.

    Usage:
        metrics = PipelineMetrics()

        with metrics.track("informal"):
            result = await analyze_informal(text)

        print(metrics.get_summary())
    """

    def __init__(self, max_entries: int = 10000):
        """
        Initialize metrics collector.

        Args:
            max_entries: Maximum metrics entries to retain (FIFO)
        """
        self._metrics: List[AnalysisMetric] = []
        self._max_entries = max_entries
        self._start_time = time.time()

    def record(
        self,
        analysis_type: str,
        duration_seconds: float,
        success: bool,
        confidence: Optional[float] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a single analysis metric."""
        # Enforce max entries
        if len(self._metrics) >= self._max_entries:
            self._metrics.pop(0)

        self._metrics.append(AnalysisMetric(
            timestamp=time.time(),
            analysis_type=analysis_type,
            duration_seconds=duration_seconds,
            success=success,
            confidence=confidence,
            error=error,
            metadata=metadata or {},
        ))

    def track(self, analysis_type: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to track analysis duration automatically.

        Usage:
            with metrics.track("informal", {"text_length": len(text)}):
                result = await analyze(text)
        """
        return _MetricsContext(self, analysis_type, metadata)

    def get_summary(self) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        if not self._metrics:
            return {
                "total_analyses": 0,
                "successful": 0,
                "failed": 0,
                "uptime_seconds": time.time() - self._start_time,
            }

        successful = [m for m in self._metrics if m.success]
        failed = [m for m in self._metrics if not m.success]

        # Per-type breakdown
        by_type: Dict[str, Dict[str, Any]] = {}
        for m in self._metrics:
            if m.analysis_type not in by_type:
                by_type[m.analysis_type] = {
                    "count": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration": 0.0,
                    "avg_confidence": [],
                }
            by_type[m.analysis_type]["count"] += 1
            by_type[m.analysis_type]["total_duration"] += m.duration_seconds
            if m.success:
                by_type[m.analysis_type]["successful"] += 1
                if m.confidence is not None:
                    by_type[m.analysis_type]["avg_confidence"].append(m.confidence)
            else:
                by_type[m.analysis_type]["failed"] += 1

        # Compute averages
        for type_data in by_type.values():
            count = type_data["count"]
            type_data["avg_duration"] = type_data["total_duration"] / count if count > 0 else 0
            confs = type_data["avg_confidence"]
            type_data["avg_confidence"] = sum(confs) / len(confs) if confs else None

        # Overall averages
        durations = [m.duration_seconds for m in self._metrics]
        confidences = [m.confidence for m in successful if m.confidence is not None]

        return {
            "total_analyses": len(self._metrics),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self._metrics),
            "avg_duration_seconds": sum(durations) / len(durations),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
            "uptime_seconds": time.time() - self._start_time,
            "by_analysis_type": by_type,
        }

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics entries."""
        recent = self._metrics[-limit:]
        return [
            {
                "timestamp": m.timestamp,
                "datetime": datetime.fromtimestamp(m.timestamp).isoformat(),
                "analysis_type": m.analysis_type,
                "duration_seconds": m.duration_seconds,
                "success": m.success,
                "confidence": m.confidence,
                "error": m.error,
            }
            for m in recent
        ]

    def reset(self) -> None:
        """Clear all metrics."""
        self._metrics.clear()
        self._start_time = time.time()


class _MetricsContext:
    """Context manager for tracking analysis duration."""

    def __init__(
        self,
        metrics: PipelineMetrics,
        analysis_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self._metrics = metrics
        self._analysis_type = analysis_type
        self._metadata = metadata
        self._start_time: Optional[float] = None
        self._result: Any = None
        self._error: Optional[str] = None

    def __enter__(self):
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self._start_time if self._start_time else 0
        success = exc_type is None
        error = str(exc_val) if exc_val else None

        # Try to extract confidence from result
        confidence = None
        if isinstance(self._result, dict):
            confidence = self._result.get("confidence")

        self._metrics.record(
            analysis_type=self._analysis_type,
            duration_seconds=duration,
            success=success,
            confidence=confidence,
            error=error,
            metadata=self._metadata,
        )
        return False  # Don't suppress exceptions

    def set_result(self, result: Any) -> None:
        """Set the result for confidence extraction."""
        self._result = result


# =============================================================================
# 3. BATCH ANALYSIS WITH CONCURRENCY CONTROL
# =============================================================================

@dataclass
class BatchRequest:
    """A single request in a batch."""
    id: str
    text: str
    analysis_type: str
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class BatchResult:
    """Result of a single batch request."""
    id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


async def run_batch_analysis(
    requests: List[BatchRequest],
    analyze_fn: Callable[[str, str, Optional[Dict]], Any],
    max_concurrent: int = 10,
    fail_fast: bool = False,
    cache: Optional[AnalysisCache] = None,
    metrics: Optional[PipelineMetrics] = None,
) -> List[BatchResult]:
    """
    Run multiple analyses concurrently with semaphore control.

    Replicates the batch_analyze functionality from archived RealLLMOrchestrator.

    Args:
        requests: List of analysis requests
        analyze_fn: Async function(text, analysis_type, parameters) -> result
        max_concurrent: Maximum concurrent analyses
        fail_fast: If True, stop on first error
        cache: Optional cache for deduplication
        metrics: Optional metrics collector

    Returns:
        List of BatchResult in same order as requests

    Usage:
        requests = [
            BatchRequest(id="1", text="Hello", analysis_type="informal"),
            BatchRequest(id="2", text="World", analysis_type="logical"),
        ]
        results = await run_batch_analysis(
            requests,
            analyze_fn=unified_pipeline.analyze,
            max_concurrent=5,
            cache=AnalysisCache(),
            metrics=PipelineMetrics(),
        )
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results: List[BatchResult] = []
    stop_flag = asyncio.Event()

    async def process_request(req: BatchRequest) -> BatchResult:
        if fail_fast and stop_flag.is_set():
            return BatchResult(
                id=req.id,
                success=False,
                error="Batch stopped due to previous error",
            )

        start = time.time()
        try:
            async with semaphore:
                if fail_fast and stop_flag.is_set():
                    return BatchResult(
                        id=req.id,
                        success=False,
                        error="Batch stopped due to previous error",
                    )

                # Check cache first
                if cache is not None:
                    cached = cache.get(req.text, req.analysis_type, req.parameters)
                    if cached is not None:
                        logger.debug(f"Cache hit for {req.id}")
                        return BatchResult(
                            id=req.id,
                            success=True,
                            result=cached,
                            duration_seconds=time.time() - start,
                        )

                result = await analyze_fn(req.text, req.analysis_type, req.parameters)

                # Cache the result
                if cache is not None:
                    cache.set(req.text, req.analysis_type, result, req.parameters)

                duration = time.time() - start

                # Record metrics
                if metrics is not None:
                    confidence = None
                    if isinstance(result, dict):
                        confidence = result.get("confidence")
                    metrics.record(
                        analysis_type=req.analysis_type,
                        duration_seconds=duration,
                        success=True,
                        confidence=confidence,
                        metadata={"request_id": req.id},
                    )

                return BatchResult(
                    id=req.id,
                    success=True,
                    result=result,
                    duration_seconds=duration,
                )
        except Exception as e:
            if fail_fast:
                stop_flag.set()
            logger.error(f"Batch request {req.id} failed: {e}")

            duration = time.time() - start
            error_str = str(e)

            # Record failure metrics
            if metrics is not None:
                metrics.record(
                    analysis_type=req.analysis_type,
                    duration_seconds=duration,
                    success=False,
                    error=error_str,
                    metadata={"request_id": req.id},
                )

            return BatchResult(
                id=req.id,
                success=False,
                error=error_str,
                duration_seconds=duration,
            )

    # Run all requests concurrently (semaphore controls parallelism)
    tasks = [process_request(req) for req in requests]
    results = await asyncio.gather(*tasks)

    return list(results)


# =============================================================================
# 4. INTEGRATED PIPELINE ENHANCEMENT
# =============================================================================

class EnhancedPipeline:
    """
    UnifiedPipeline wrapper with caching, metrics, and batch support.

    This class wraps the UnifiedPipeline to provide feature parity with
    the archived RealLLMOrchestrator while using the modern Lego architecture.

    Usage:
        from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis
        from argumentation_analysis.orchestration.pipeline_utils import EnhancedPipeline

        # Create enhanced pipeline
        pipeline = EnhancedPipeline(
            cache_ttl=3600,
            max_concurrent=10,
        )

        # Single analysis with caching
        result = await pipeline.analyze("Some text", workflow="standard")

        # Batch analysis
        requests = [BatchRequest(...), ...]
        results = await pipeline.batch_analyze(requests)

        # Get metrics
        print(pipeline.get_metrics_summary())
    """

    def __init__(
        self,
        cache_ttl: float = 3600,
        cache_max_size: int = 1000,
        max_concurrent: int = 10,
        metrics_max_entries: int = 10000,
    ):
        self._cache = AnalysisCache(ttl_seconds=cache_ttl, max_size=cache_max_size)
        self._metrics = PipelineMetrics(max_entries=metrics_max_entries)
        self._max_concurrent = max_concurrent

    async def analyze(
        self,
        text: str,
        workflow: str = "standard",
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run analysis with optional caching and metrics tracking.
        """
        from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

        # Check cache
        if use_cache:
            cached = self._cache.get(text, workflow, kwargs)
            if cached is not None:
                logger.debug(f"Cache hit for workflow {workflow}")
                return cached

        # Run analysis with metrics tracking
        with self._metrics.track(workflow, {"text_length": len(text)}) as ctx:
            result = await run_unified_analysis(
                text=text,
                workflow_name=workflow,
                **kwargs
            )
            ctx.set_result(result)

        # Cache result
        if use_cache:
            self._cache.set(text, workflow, result, kwargs)

        return result

    async def batch_analyze(
        self,
        requests: List[BatchRequest],
        workflow: str = "standard",
        fail_fast: bool = False,
    ) -> List[BatchResult]:
        """
        Run batch analyses with concurrency control.
        """
        async def analyze_fn(text: str, analysis_type: str, params: Optional[Dict]) -> Any:
            return await self.analyze(text, workflow=analysis_type, **(params or {}))

        return await run_batch_analysis(
            requests=requests,
            analyze_fn=analyze_fn,
            max_concurrent=self._max_concurrent,
            fail_fast=fail_fast,
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return self._metrics.get_summary()

    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics entries."""
        return self._metrics.get_recent(limit)

    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        self._cache.clear()

    def reset_metrics(self) -> None:
        """Reset metrics collection."""
        self._metrics.reset()


# =============================================================================
# MODULE-LEVEL CONVENIENCE INSTANCES
# =============================================================================

# Default shared instances for easy import
_default_cache: Optional[AnalysisCache] = None
_default_metrics: Optional[PipelineMetrics] = None


def get_default_cache() -> AnalysisCache:
    """Get or create the default shared cache instance."""
    global _default_cache
    if _default_cache is None:
        _default_cache = AnalysisCache()
    return _default_cache


def get_default_metrics() -> PipelineMetrics:
    """Get or create the default shared metrics instance."""
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = PipelineMetrics()
    return _default_metrics


__all__ = [
    # Caching
    "AnalysisCache",
    "CacheEntry",
    "cached_analysis",
    # Metrics
    "PipelineMetrics",
    "AnalysisMetric",
    # Batch
    "BatchRequest",
    "BatchResult",
    "run_batch_analysis",
    # Integrated
    "EnhancedPipeline",
    # Convenience
    "get_default_cache",
    "get_default_metrics",
]

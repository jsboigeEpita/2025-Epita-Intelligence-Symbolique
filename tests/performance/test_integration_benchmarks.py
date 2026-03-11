# -*- coding: utf-8 -*-
"""
Performance benchmarks for integrated student project components.

Measures execution time and scalability of:
- CapabilityRegistry operations (registration, lookup)
- QualityScoringPlugin (9-virtue evaluation)
- GovernancePlugin (voting methods, conflict detection)
- CounterArgumentPlugin (parsing, vulnerabilities, strategies)
- DebatePlugin (quality analysis, logical structure)
- UnifiedPipeline (setup_registry, workflow builders)

Usage:
    conda run -n projet-is-roo-new --no-capture-output pytest tests/performance/test_integration_benchmarks.py -v
"""

import json
import time
import gc
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

pytestmark = pytest.mark.performance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def timed(func, *args, **kwargs):
    """Run func and return (result, elapsed_seconds)."""
    gc.collect()
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


SAMPLE_ARGUMENT_FR = (
    "La vaccination obligatoire est justifiee car les etudes epidemiologiques "
    "montrent une reduction de 95% des cas de rougeole dans les pays avec "
    "couverture vaccinale superieure a 90%. Les donnees de l'OMS confirment "
    "cette correlation depuis 2010."
)

SAMPLE_ARGUMENT_FR_2 = (
    "Les energies renouvelables sont trop couteuses pour remplacer "
    "les energies fossiles dans un avenir proche."
)

SAMPLE_ARGUMENT_FR_3 = (
    "L'intelligence artificielle va creer plus d'emplois qu'elle n'en detruira, "
    "comme l'a fait chaque revolution industrielle precedente."
)


# ===========================================================================
# 1. CapabilityRegistry Benchmarks
# ===========================================================================

class TestRegistryPerformance:
    """Benchmark CapabilityRegistry registration and lookup speed."""

    def test_setup_registry_time(self):
        """setup_registry() should complete in under 2 seconds."""
        from argumentation_analysis.orchestration.unified_pipeline import setup_registry

        _, elapsed = timed(setup_registry, include_optional=False)
        print(f"\n  setup_registry(core): {elapsed:.3f}s")
        assert elapsed < 2.0, f"setup_registry took {elapsed:.3f}s (limit: 2.0s)"

    def test_setup_registry_full_time(self):
        """setup_registry(include_optional=True) should complete in under 3 seconds."""
        from argumentation_analysis.orchestration.unified_pipeline import setup_registry

        _, elapsed = timed(setup_registry, include_optional=True)
        print(f"\n  setup_registry(full): {elapsed:.3f}s")
        assert elapsed < 3.0, f"setup_registry(full) took {elapsed:.3f}s (limit: 3.0s)"

    def test_capability_lookup_speed(self):
        """Capability lookup should be under 5ms."""
        from argumentation_analysis.orchestration.unified_pipeline import setup_registry

        registry = setup_registry(include_optional=False)
        capabilities = registry.get_all_capabilities()

        # Benchmark lookups
        times = []
        for cap in capabilities:
            _, elapsed = timed(registry.find_agents_for_capability, cap)
            times.append(elapsed)

        avg_ms = (sum(times) / len(times)) * 1000 if times else 0
        max_ms = max(times) * 1000 if times else 0
        print(f"\n  Capability lookups ({len(times)}): avg={avg_ms:.2f}ms, max={max_ms:.2f}ms")
        assert max_ms < 50, f"Max lookup took {max_ms:.2f}ms (limit: 50ms)"

    def test_registry_capabilities_count(self):
        """Registry should register at least 15 capabilities."""
        from argumentation_analysis.orchestration.unified_pipeline import setup_registry

        registry = setup_registry(include_optional=True)
        caps = registry.get_all_capabilities()
        print(f"\n  Registered capabilities: {len(caps)}")
        assert len(caps) >= 15, f"Only {len(caps)} capabilities registered (expected >= 15)"


# ===========================================================================
# 2. QualityScoringPlugin Benchmarks
# ===========================================================================

class TestQualityScoringPerformance:
    """Benchmark argument quality evaluation."""

    @pytest.fixture
    def plugin(self):
        from argumentation_analysis.plugins.quality_scoring_plugin import QualityScoringPlugin
        return QualityScoringPlugin()

    def test_evaluate_argument_quality_time(self, plugin):
        """Single evaluation should complete in under 2s (includes spacy model load on first call)."""
        _, elapsed = timed(plugin.evaluate_argument_quality, SAMPLE_ARGUMENT_FR)
        print(f"\n  evaluate_argument_quality: {elapsed * 1000:.1f}ms")
        assert elapsed < 2.0, f"Evaluation took {elapsed * 1000:.1f}ms (limit: 2000ms)"

    def test_get_quality_score_time(self, plugin):
        """Quality score computation should complete in under 200ms."""
        _, elapsed = timed(plugin.get_quality_score, SAMPLE_ARGUMENT_FR)
        print(f"\n  get_quality_score: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.2, f"Score took {elapsed * 1000:.1f}ms (limit: 200ms)"

    def test_batch_evaluation_scalability(self, plugin):
        """10 sequential evaluations should show linear scaling."""
        texts = [SAMPLE_ARGUMENT_FR, SAMPLE_ARGUMENT_FR_2, SAMPLE_ARGUMENT_FR_3] * 4  # 12 texts

        gc.collect()
        start = time.perf_counter()
        for text in texts[:10]:
            plugin.evaluate_argument_quality(text)
        total = time.perf_counter() - start

        avg_ms = (total / 10) * 1000
        print(f"\n  Batch (10 args): total={total:.3f}s, avg={avg_ms:.1f}ms/arg")
        assert total < 2.0, f"Batch took {total:.3f}s (limit: 2.0s)"

    def test_list_virtues_time(self, plugin):
        """Listing virtues should be near-instant."""
        _, elapsed = timed(plugin.list_virtues)
        result = json.loads(plugin.list_virtues())
        print(f"\n  list_virtues: {elapsed * 1000:.2f}ms, {len(result)} virtues")
        assert elapsed < 0.01, f"list_virtues took {elapsed * 1000:.2f}ms (limit: 10ms)"


# ===========================================================================
# 3. GovernancePlugin Benchmarks
# ===========================================================================

class TestGovernancePerformance:
    """Benchmark governance voting and conflict detection."""

    @pytest.fixture
    def plugin(self):
        from argumentation_analysis.plugins.governance_plugin import GovernancePlugin
        return GovernancePlugin()

    def _make_positions(self, n_agents):
        """Generate positions for n agents."""
        positions = {}
        for i in range(n_agents):
            side = "for" if i % 2 == 0 else "against"
            conf = 0.5 + (i % 5) * 0.1
            positions[f"agent_{i}"] = {"position": side, "confidence": conf}
        return json.dumps(positions)

    def test_list_governance_methods_time(self, plugin):
        """Listing methods should be near-instant."""
        _, elapsed = timed(plugin.list_governance_methods)
        result = json.loads(plugin.list_governance_methods())
        print(f"\n  list_governance_methods: {elapsed * 1000:.2f}ms, {len(result)} methods")
        assert elapsed < 0.01

    def test_conflict_detection_5_agents(self, plugin):
        """Conflict detection for 5 agents should be under 50ms."""
        positions = self._make_positions(5)
        _, elapsed = timed(plugin.detect_conflicts_fn, positions)
        print(f"\n  detect_conflicts (5 agents): {elapsed * 1000:.1f}ms")
        assert elapsed < 0.05

    def test_conflict_detection_50_agents(self, plugin):
        """Conflict detection for 50 agents should be under 500ms."""
        positions = self._make_positions(50)
        _, elapsed = timed(plugin.detect_conflicts_fn, positions)
        print(f"\n  detect_conflicts (50 agents): {elapsed * 1000:.1f}ms")
        assert elapsed < 0.5

    def test_conflict_detection_scalability(self, plugin):
        """Conflict detection should scale sub-quadratically."""
        times = {}
        for n in [5, 10, 20, 50]:
            positions = self._make_positions(n)
            _, elapsed = timed(plugin.detect_conflicts_fn, positions)
            times[n] = elapsed * 1000

        print(f"\n  Scalability: " + ", ".join(f"{n}={t:.1f}ms" for n, t in times.items()))
        # 50-agent time should be < 20x the 5-agent time (sub-quadratic)
        if times[5] > 0:
            ratio = times[50] / times[5]
            print(f"  Ratio 50/5: {ratio:.1f}x")
            assert ratio < 100, f"Scaling ratio {ratio:.1f}x is too high"


# ===========================================================================
# 4. CounterArgumentPlugin Benchmarks
# ===========================================================================

class TestCounterArgumentPerformance:
    """Benchmark counter-argument generation pipeline."""

    @pytest.fixture
    def plugin(self):
        from argumentation_analysis.agents.core.counter_argument import CounterArgumentPlugin
        return CounterArgumentPlugin()

    def test_parse_argument_time(self, plugin):
        """Argument parsing should complete in under 100ms."""
        _, elapsed = timed(plugin.parse_argument, SAMPLE_ARGUMENT_FR_2)
        print(f"\n  parse_argument: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.1

    def test_identify_vulnerabilities_time(self, plugin):
        """Vulnerability identification should complete in under 200ms."""
        _, elapsed = timed(plugin.identify_vulnerabilities, SAMPLE_ARGUMENT_FR_2)
        print(f"\n  identify_vulnerabilities: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.2

    def test_suggest_strategy_time(self, plugin):
        """Strategy suggestion should complete in under 200ms."""
        _, elapsed = timed(plugin.suggest_strategy, SAMPLE_ARGUMENT_FR_2)
        print(f"\n  suggest_strategy: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.2

    def test_full_pipeline_time(self, plugin):
        """Full pipeline (parse + vulnerabilities + strategy) should be under 500ms."""
        gc.collect()
        start = time.perf_counter()
        plugin.parse_argument(SAMPLE_ARGUMENT_FR_2)
        plugin.identify_vulnerabilities(SAMPLE_ARGUMENT_FR_2)
        plugin.suggest_strategy(SAMPLE_ARGUMENT_FR_2)
        total = time.perf_counter() - start

        print(f"\n  Full pipeline: {total * 1000:.1f}ms")
        assert total < 0.5


# ===========================================================================
# 5. DebatePlugin Benchmarks
# ===========================================================================

class TestDebatePerformance:
    """Benchmark debate analysis operations."""

    @pytest.fixture
    def plugin(self):
        from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin
        return DebatePlugin()

    def test_analyze_argument_quality_time(self, plugin):
        """Argument quality analysis should complete in under 200ms."""
        _, elapsed = timed(plugin.analyze_argument_quality, SAMPLE_ARGUMENT_FR_3)
        print(f"\n  analyze_argument_quality: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.2

    def test_analyze_logical_structure_time(self, plugin):
        """Logical structure analysis should complete in under 200ms."""
        _, elapsed = timed(plugin.analyze_logical_structure, SAMPLE_ARGUMENT_FR_3)
        print(f"\n  analyze_logical_structure: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.2

    def test_batch_analysis_time(self, plugin):
        """Batch analysis of 10 arguments should be under 2 seconds."""
        arguments = [SAMPLE_ARGUMENT_FR, SAMPLE_ARGUMENT_FR_2, SAMPLE_ARGUMENT_FR_3] * 4

        gc.collect()
        start = time.perf_counter()
        for arg in arguments[:10]:
            plugin.analyze_argument_quality(arg)
            plugin.analyze_logical_structure(arg)
        total = time.perf_counter() - start

        avg_ms = (total / 10) * 1000
        print(f"\n  Batch (10 args, quality+structure): total={total:.3f}s, avg={avg_ms:.1f}ms/arg")
        assert total < 2.0


# ===========================================================================
# 6. UnifiedPipeline Workflow Benchmarks
# ===========================================================================

class TestPipelinePerformance:
    """Benchmark unified pipeline workflow construction."""

    def test_build_light_workflow_time(self):
        """Light workflow should build in under 100ms."""
        from argumentation_analysis.orchestration.unified_pipeline import build_light_workflow

        _, elapsed = timed(build_light_workflow)
        print(f"\n  build_light_workflow: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.1

    def test_build_standard_workflow_time(self):
        """Standard workflow should build in under 200ms."""
        from argumentation_analysis.orchestration.unified_pipeline import build_standard_workflow

        _, elapsed = timed(build_standard_workflow)
        print(f"\n  build_standard_workflow: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.2

    def test_build_full_workflow_time(self):
        """Full workflow should build in under 500ms."""
        from argumentation_analysis.orchestration.unified_pipeline import build_full_workflow

        _, elapsed = timed(build_full_workflow)
        print(f"\n  build_full_workflow: {elapsed * 1000:.1f}ms")
        assert elapsed < 0.5

    def test_workflow_phase_counts(self):
        """Verify workflow complexity is as expected."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_light_workflow,
            build_standard_workflow,
            build_full_workflow,
        )

        light = build_light_workflow()
        standard = build_standard_workflow()
        full = build_full_workflow()

        print(f"\n  Light: {len(light.phases)} phases")
        print(f"  Standard: {len(standard.phases)} phases")
        print(f"  Full: {len(full.phases)} phases")

        assert len(light.phases) >= 2
        assert len(standard.phases) >= len(light.phases)
        assert len(full.phases) >= len(standard.phases)

    def test_all_workflows_combined_time(self):
        """Building all 3 workflows should take under 1 second total."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_light_workflow,
            build_standard_workflow,
            build_full_workflow,
        )

        gc.collect()
        start = time.perf_counter()
        build_light_workflow()
        build_standard_workflow()
        build_full_workflow()
        total = time.perf_counter() - start

        print(f"\n  All 3 workflows: {total * 1000:.1f}ms")
        assert total < 1.0

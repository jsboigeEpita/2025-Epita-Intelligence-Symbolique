"""
Performance benchmarks: standard vs spectacular workflows.

Runs both workflows on documents from the encrypted dataset and measures
wall-clock time, state size, and field coverage.

Markers:
    @pytest.mark.requires_api — skip without OPENAI_API_KEY
    @pytest.mark.slow — each cell takes 2-10 minutes

Privacy: opaque IDs only (doc_A, doc_B, doc_C).
"""

import json
import os
import time

import pytest

# Skip entire module without API key
pytestmark = [
    pytest.mark.requires_api,
    pytest.mark.slow,
]

from argumentation_analysis.evaluation import BenchmarkRunner, ModelRegistry


DATASET_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "argumentation_analysis",
    "data",
    "extract_sources.json.gz.enc",
)

OPAQUE_IDS = {0: "doc_A", 1: "doc_B", 2: "doc_C"}

WALL_CLOCK_TIMEOUT = 600.0  # 10 min per cell


@pytest.fixture(scope="module")
def benchmark_runner():
    """Set up benchmark runner with encrypted dataset."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        pytest.skip("TEXT_CONFIG_PASSPHRASE not set")

    if not os.path.exists(DATASET_PATH):
        pytest.skip(f"Dataset not found: {DATASET_PATH}")

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_encrypted(DATASET_PATH, passphrase)
    return runner


def _count_populated_fields(state):
    """Count non-empty fields in a state snapshot."""
    if not state:
        return 0
    field_keys = [
        "identified_arguments", "identified_fallacies", "belief_sets",
        "extracts", "counter_arguments", "argument_quality_scores",
        "jtms_beliefs", "jtms_retraction_chain", "dung_frameworks",
        "governance_decisions", "debate_transcripts", "neural_fallacy_scores",
        "ranking_results", "aspic_results", "fol_analysis_results",
        "propositional_analysis_results", "modal_analysis_results",
        "formal_synthesis_reports", "nl_to_logic_translations",
        "atms_contexts", "narrative_synthesis", "final_conclusion",
        "answers", "query_log", "belief_revision_results",
        "dialogue_results", "probabilistic_results", "bipolar_results",
        "fol_signature", "workflow_results", "semantic_index_refs",
        "transcription_segments",
    ]
    count = 0
    for key in field_keys:
        val = state.get(key)
        if val is None:
            continue
        if isinstance(val, (list, dict, str)) and len(val) > 0:
            count += 1
        elif isinstance(val, bool) and val:
            count += 1
        elif isinstance(val, (int, float)) and val != 0:
            count += 1
    return count


@pytest.fixture(scope="module")
def benchmark_results(benchmark_runner):
    """Run both workflows on 3 docs and collect results."""
    import asyncio

    results = {}
    for wf in ["standard", "spectacular"]:
        for doc_idx in [0, 1, 2]:
            result = asyncio.run(benchmark_runner.run_cell(
                workflow_name=wf,
                model_name="default",
                document_index=doc_idx,
                max_text_chars=3000,
                timeout=WALL_CLOCK_TIMEOUT,
            ))
            key = f"{wf}_{OPAQUE_IDS.get(doc_idx, f'doc_{doc_idx}')}"
            results[key] = {
                "success": result.success,
                "duration": result.duration_seconds,
                "phases_completed": result.phases_completed,
                "phases_total": result.phases_total,
                "state_snapshot": result.state_snapshot,
                "error": result.error,
            }
    return results


# --- Performance Tests ---

class TestSpectacularPerformance:
    """Wall-clock and state size benchmarks."""

    def test_standard_completes_within_timeout(self, benchmark_results):
        """Standard workflow completes within 600s for each doc."""
        for doc in ["doc_A", "doc_B", "doc_C"]:
            key = f"standard_{doc}"
            r = benchmark_results[key]
            assert r["success"], f"Standard × {doc} failed: {r['error']}"
            assert r["duration"] < WALL_CLOCK_TIMEOUT

    def test_spectacular_completes_within_timeout(self, benchmark_results):
        """Spectacular workflow completes within 600s for each doc."""
        for doc in ["doc_A", "doc_B", "doc_C"]:
            key = f"spectacular_{doc}"
            r = benchmark_results[key]
            assert r["success"], f"Spectacular × {doc} failed: {r['error']}"
            assert r["duration"] < WALL_CLOCK_TIMEOUT

    def test_spectacular_more_phases_than_standard(self, benchmark_results):
        """Spectacular runs more phases than standard."""
        for doc in ["doc_A", "doc_B", "doc_C"]:
            std = benchmark_results[f"standard_{doc}"]
            spec = benchmark_results[f"spectacular_{doc}"]
            if std["success"] and spec["success"]:
                assert spec["phases_total"] >= std["phases_total"], (
                    f"{doc}: spectacular ({spec['phases_total']}) should have "
                    f">= standard ({std['phases_total']}) phases"
                )

    def test_state_size_measured(self, benchmark_results):
        """State JSON size is measurable and reasonable."""
        for wf in ["standard", "spectacular"]:
            for doc in ["doc_A", "doc_B", "doc_C"]:
                r = benchmark_results[f"{wf}_{doc}"]
                if r["success"] and r["state_snapshot"]:
                    size_kb = len(json.dumps(r["state_snapshot"], default=str)) / 1024
                    assert size_kb > 0
                    assert size_kb < 10240  # Less than 10MB


class TestSpectacularCoverage:
    """Field coverage and quality metrics."""

    def test_spectacular_more_fields_than_standard(self, benchmark_results):
        """Spectacular fills more UnifiedAnalysisState fields than standard."""
        for doc in ["doc_A", "doc_B", "doc_C"]:
            std = benchmark_results[f"standard_{doc}"]
            spec = benchmark_results[f"spectacular_{doc}"]
            if std["success"] and spec["success"] and std["state_snapshot"] and spec["state_snapshot"]:
                std_fields = _count_populated_fields(std["state_snapshot"])
                spec_fields = _count_populated_fields(spec["state_snapshot"])
                assert spec_fields >= std_fields, (
                    f"{doc}: spectacular ({spec_fields} fields) should have "
                    f">= standard ({std_fields} fields)"
                )

    def test_spectacular_field_coverage_at_least_50pct(self, benchmark_results):
        """Spectacular fills at least 50% of state fields on doc_A."""
        r = benchmark_results["spectacular_doc_A"]
        if r["success"] and r["state_snapshot"]:
            fields = _count_populated_fields(r["state_snapshot"])
            coverage = fields / 32 * 100
            assert coverage >= 50, f"doc_A spectacular coverage: {coverage}% < 50%"

    def test_spectacular_has_fallacies(self, benchmark_results):
        """Spectacular detects fallacies on all docs."""
        for doc in ["doc_A", "doc_B", "doc_C"]:
            r = benchmark_results[f"spectacular_{doc}"]
            if r["success"] and r["state_snapshot"]:
                fallacies = r["state_snapshot"].get("identified_fallacies", {})
                neural = r["state_snapshot"].get("neural_fallacy_scores", [])
                assert len(fallacies) > 0 or len(neural) > 0, (
                    f"{doc}: no fallacies detected"
                )

    def test_spectacular_has_formal_logic(self, benchmark_results):
        """Spectacular produces FOL analysis on doc_A."""
        r = benchmark_results["spectacular_doc_A"]
        if r["success"] and r["state_snapshot"]:
            fol = r["state_snapshot"].get("fol_analysis_results", [])
            assert len(fol) > 0, "doc_A: no FOL formulas produced"

    def test_spectacular_has_narrative(self, benchmark_results):
        """Spectacular produces narrative synthesis on doc_A."""
        r = benchmark_results["spectacular_doc_A"]
        if r["success"] and r["state_snapshot"]:
            narrative = r["state_snapshot"].get("narrative_synthesis", "")
            assert narrative and len(narrative.strip()) > 0, (
                "doc_A: no narrative synthesis produced"
            )


class TestComparisonMetrics:
    """Cross-workflow comparison assertions."""

    def test_perf_summary(self, benchmark_results):
        """Print performance summary table (informational, always passes)."""
        print("\n")
        print(f"{'Workflow':<15} {'Doc':<6} {'Time(s)':>8} {'Phases':>8} {'Fields':>8} {'Size(KB)':>10}")
        print("-" * 60)
        for wf in ["standard", "spectacular"]:
            for doc in ["doc_A", "doc_B", "doc_C"]:
                key = f"{wf}_{doc}"
                r = benchmark_results[key]
                if r["success"] and r["state_snapshot"]:
                    fields = _count_populated_fields(r["state_snapshot"])
                    size = len(json.dumps(r["state_snapshot"], default=str)) / 1024
                    print(
                        f"{wf:<15} {doc:<6} {r['duration']:>8.1f} "
                        f"{r['phases_completed']:>3}/{r['phases_total']:<3} "
                        f"{fields:>5}/32 {size:>9.1f}"
                    )
                else:
                    print(f"{wf:<15} {doc:<6} {'FAIL':>8}")

    def test_no_plaintext_in_results(self, benchmark_results):
        """Verify no source names or plaintext content leaked into results."""
        sensitive_fields = [
            "raw_text", "source_name", "full_text",
            "extract_text", "content",
        ]
        for key, r in benchmark_results.items():
            if not r["state_snapshot"]:
                continue
            for field in sensitive_fields:
                val = r["state_snapshot"].get(field, "")
                if isinstance(val, str) and len(val) > 200:
                    pytest.fail(
                        f"{key}: {field} contains {len(val)} chars of potential plaintext"
                    )

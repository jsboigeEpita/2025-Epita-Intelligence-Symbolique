"""
Selective Capability Evaluator: measure the impact of each capability.

Tests workflows with capabilities selectively enabled/disabled to identify:
1. Which capabilities add the most value (quality delta)
2. Which combinations produce synergies (superadditive quality)
3. Optimal capability subsets for different document types

Usage:
    python -m argumentation_analysis.evaluation.capability_evaluator \
        --corpus argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json \
        --output argumentation_analysis/evaluation/results/capability_eval \
        --max-docs 5
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("evaluation.capability_evaluator")


@dataclass
class CapabilityEvalResult:
    """Result of evaluating a capability subset on a document."""

    document_name: str
    capabilities_enabled: List[str]
    capabilities_disabled: List[str]
    phases_completed: int
    phases_total: int
    phases_failed: int
    duration_seconds: float
    state_snapshot: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class CapabilityImpact:
    """Measured impact of a single capability across documents."""

    capability: str
    avg_completion_delta: float  # How much completion improves when added
    avg_state_richness_delta: float  # How much state data increases
    avg_duration_delta: float  # How much slower (negative = faster)
    documents_tested: int
    always_succeeds: bool  # Does this capability always complete?


# Core capabilities that form the evaluation basis
CORE_CAPABILITIES = [
    "argument_quality",
    "counter_argument_generation",
    "adversarial_debate",
    "governance_simulation",
    "belief_maintenance",
]

# Track A capabilities to evaluate for marginal value
TRACK_A_CAPABILITIES = [
    "ranking_semantics",
    "aspic_plus_reasoning",
    "belief_revision",
    "dialogue_protocols",
    "probabilistic_argumentation",
    "bipolar_argumentation",
]

# Capability subsets to test (ablation study)
CAPABILITY_SUBSETS = {
    "minimal": ["argument_quality"],
    "quality_counter": ["argument_quality", "counter_argument_generation"],
    "core_trio": [
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
    ],
    "core_full": CORE_CAPABILITIES,
    "core_plus_ranking": CORE_CAPABILITIES + ["ranking_semantics"],
    "core_plus_formal": CORE_CAPABILITIES
    + ["ranking_semantics", "aspic_plus_reasoning", "dialogue_protocols"],
    "core_plus_belief": CORE_CAPABILITIES + ["belief_revision", "belief_maintenance"],
    "all_available": CORE_CAPABILITIES + TRACK_A_CAPABILITIES,
}


def _count_state_entries(snapshot: Dict[str, Any]) -> int:
    """Count total data entries in a state snapshot (measure of richness)."""
    count = 0
    for key, value in snapshot.items():
        if key.endswith("_count") and isinstance(value, (int, float)):
            count += int(value)
    return count


async def evaluate_capability_subset(
    text: str,
    document_name: str,
    subset_name: str,
    enabled_capabilities: List[str],
) -> CapabilityEvalResult:
    """Run a workflow with only the specified capabilities enabled.

    Uses a custom-built workflow that only includes phases for the
    enabled capabilities.
    """
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder
    from argumentation_analysis.orchestration.unified_pipeline import (
        CAPABILITY_STATE_WRITERS,
        WorkflowExecutor,
        setup_registry,
    )
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    registry = setup_registry()
    state = UnifiedAnalysisState(text)

    # Build a custom workflow with only the enabled capabilities
    builder = WorkflowBuilder(f"eval_{subset_name}")
    phase_count = 0
    prev_phase = None

    # Map capabilities to phase names
    capability_phases = {
        "argument_quality": "quality",
        "counter_argument_generation": "counter",
        "adversarial_debate": "debate",
        "governance_simulation": "governance",
        "belief_maintenance": "jtms",
        "ranking_semantics": "ranking",
        "aspic_plus_reasoning": "aspic",
        "belief_revision": "belief_rev",
        "dialogue_protocols": "dialogue",
        "probabilistic_argumentation": "probabilistic",
        "bipolar_argumentation": "bipolar",
        "fact_extraction": "extract",
        "neural_fallacy_detection": "fallacy",
    }

    for cap in enabled_capabilities:
        phase_name = capability_phases.get(cap, cap.replace("_", ""))
        deps = [prev_phase] if prev_phase and phase_count > 0 else []
        builder.add_phase(phase_name, capability=cap, depends_on=deps, optional=True)
        prev_phase = phase_name
        phase_count += 1

    if phase_count == 0:
        return CapabilityEvalResult(
            document_name=document_name,
            capabilities_enabled=enabled_capabilities,
            capabilities_disabled=[],
            phases_completed=0,
            phases_total=0,
            phases_failed=0,
            duration_seconds=0.0,
            state_snapshot={},
            error="No capabilities enabled",
        )

    workflow = builder.build()
    executor = WorkflowExecutor(registry)

    start = time.time()
    try:
        phase_results = await executor.execute(
            workflow,
            input_data=text,
            context={},
            state=state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )
        duration = time.time() - start

        from argumentation_analysis.orchestration.workflow_dsl import PhaseStatus

        completed = sum(
            1 for r in phase_results.values() if r.status == PhaseStatus.COMPLETED
        )
        failed = sum(
            1 for r in phase_results.values() if r.status == PhaseStatus.FAILED
        )
        total = len(phase_results)

        snapshot = state.get_state_snapshot(summarize=True)

        return CapabilityEvalResult(
            document_name=document_name,
            capabilities_enabled=enabled_capabilities,
            capabilities_disabled=[],
            phases_completed=completed,
            phases_total=total,
            phases_failed=failed,
            duration_seconds=duration,
            state_snapshot=snapshot,
        )

    except Exception as e:
        duration = time.time() - start
        return CapabilityEvalResult(
            document_name=document_name,
            capabilities_enabled=enabled_capabilities,
            capabilities_disabled=[],
            phases_completed=0,
            phases_total=phase_count,
            phases_failed=phase_count,
            duration_seconds=duration,
            state_snapshot={},
            error=str(e),
        )


async def run_capability_evaluation(
    corpus_path: str,
    output_dir: str,
    max_docs: int = 5,
    subsets: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Run capability evaluation across document corpus.

    For each document, runs all capability subsets and compares results.
    """
    from dotenv import load_dotenv

    load_dotenv()

    subsets = subsets or CAPABILITY_SUBSETS
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load corpus
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus_data = json.load(f)

    documents = corpus_data.get("documents", corpus_data.get("corpus", []))
    if max_docs > 0:
        documents = documents[:max_docs]

    logger.info(
        f"Capability evaluation: {len(subsets)} subsets × {len(documents)} docs "
        f"= {len(subsets) * len(documents)} cells"
    )

    results = []
    jsonl_path = output_path / "capability_eval_results.jsonl"

    for doc_idx, doc in enumerate(documents):
        doc_name = doc.get(
            "source_name", doc.get("name", doc.get("id", f"doc_{doc_idx}"))
        )
        text = doc.get("full_text") or doc.get("text") or doc.get("content", "")
        if not text:
            for ext in doc.get("extracts", []):
                text += (ext.get("extract_text") or ext.get("text", "")) + "\n\n"

        for subset_name, capabilities in subsets.items():
            logger.info(f"  [{doc_idx+1}/{len(documents)}] {doc_name} × {subset_name}")

            result = await evaluate_capability_subset(
                text=text,
                document_name=doc_name,
                subset_name=subset_name,
                enabled_capabilities=capabilities,
            )

            result_dict = {
                "document_name": result.document_name,
                "subset_name": subset_name,
                "capabilities_enabled": result.capabilities_enabled,
                "phases_completed": result.phases_completed,
                "phases_total": result.phases_total,
                "phases_failed": result.phases_failed,
                "duration_seconds": round(result.duration_seconds, 2),
                "state_richness": _count_state_entries(result.state_snapshot),
                "state_snapshot": result.state_snapshot,
                "error": result.error,
            }
            results.append(result_dict)

            # Stream results to JSONL
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result_dict, ensure_ascii=False, default=str) + "\n")

    # Generate comparison report
    report = _generate_comparison_report(results, subsets)
    report_path = output_path / "capability_impact_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    report_json_path = output_path / "capability_impact_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"results": results, "subsets": {k: v for k, v in subsets.items()}},
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    logger.info(f"Reports saved to {output_path}/")
    return {"results": results, "report_path": str(report_path)}


def _generate_comparison_report(
    results: List[Dict], subsets: Dict[str, List[str]]
) -> str:
    """Generate markdown comparison report from evaluation results."""
    from collections import defaultdict
    from datetime import datetime

    # Group by subset
    by_subset = defaultdict(list)
    for r in results:
        by_subset[r["subset_name"]].append(r)

    lines = [
        "# Capability Impact Evaluation Report",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Subsets tested**: {len(subsets)}",
        f"**Documents**: {len(set(r['document_name'] for r in results))}",
        f"**Total cells**: {len(results)}",
        "",
        "## Results by Capability Subset",
        "",
        "| Subset | Capabilities | Avg Completion | Avg Duration | Avg State Richness |",
        "|--------|:---:|:---:|:---:|:---:|",
    ]

    subset_stats = {}
    for subset_name, runs in sorted(by_subset.items()):
        n_caps = len(subsets.get(subset_name, []))
        completion_rates = [
            (
                r["phases_completed"] / r["phases_total"] * 100
                if r["phases_total"] > 0
                else 0
            )
            for r in runs
        ]
        durations = [r["duration_seconds"] for r in runs]
        richness = [r["state_richness"] for r in runs]

        avg_comp = (
            sum(completion_rates) / len(completion_rates) if completion_rates else 0
        )
        avg_dur = sum(durations) / len(durations) if durations else 0
        avg_rich = sum(richness) / len(richness) if richness else 0

        subset_stats[subset_name] = {
            "avg_completion": avg_comp,
            "avg_duration": avg_dur,
            "avg_richness": avg_rich,
            "n_caps": n_caps,
        }

        lines.append(
            f"| {subset_name} | {n_caps} | {avg_comp:.0f}% | {avg_dur:.1f}s | {avg_rich:.0f} |"
        )

    # Marginal value analysis
    lines.extend(
        [
            "",
            "## Marginal Value Analysis",
            "",
            "Compares each subset against its predecessor to measure marginal impact:",
            "",
            "| From → To | +Capabilities | Completion Δ | Duration Δ | Richness Δ |",
            "|-----------|:---:|:---:|:---:|:---:|",
        ]
    )

    ordered_subsets = [
        "minimal",
        "quality_counter",
        "core_trio",
        "core_full",
        "core_plus_ranking",
        "core_plus_formal",
        "all_available",
    ]

    for i in range(1, len(ordered_subsets)):
        prev = ordered_subsets[i - 1]
        curr = ordered_subsets[i]
        if prev in subset_stats and curr in subset_stats:
            p = subset_stats[prev]
            c = subset_stats[curr]
            added = set(subsets.get(curr, [])) - set(subsets.get(prev, []))
            comp_delta = c["avg_completion"] - p["avg_completion"]
            dur_delta = c["avg_duration"] - p["avg_duration"]
            rich_delta = c["avg_richness"] - p["avg_richness"]
            added_str = ", ".join(sorted(added))[:40]
            lines.append(
                f"| {prev} → {curr} | {added_str} | "
                f"{comp_delta:+.0f}pp | {dur_delta:+.1f}s | {rich_delta:+.0f} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **State richness** measures how much data the pipeline produces "
            "(argument counts, fallacy counts, quality scores, etc.)",
            "- **Completion rate** should be ~100% for all subsets (fallbacks ensure this)",
            "- **Duration delta** shows the cost of each additional capability",
            "- **Richness delta** shows the data gain — high delta = high-value capability",
        ]
    )

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Capability impact evaluator")
    parser.add_argument(
        "--corpus",
        required=True,
        help="Path to corpus JSON",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for results",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=5,
        help="Max documents to evaluate (0=all)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(
        run_capability_evaluation(
            corpus_path=args.corpus,
            output_dir=args.output,
            max_docs=args.max_docs,
        )
    )
    print(f"\nEvaluation complete: {len(result['results'])} cells")
    print(f"Report: {result['report_path']}")


if __name__ == "__main__":
    main()

"""
Conversational vs Sequential baseline benchmarks (Issue #308, Epic #300 T2).

Compares three orchestration modes on fixed benchmark texts:
  - pipeline/standard
  - pipeline/full
  - conversational

Metrics collected per run:
  - state field fill rate (non-empty / total)
  - fallacy count and precision
  - quality score mean and variance
  - cross-reference density (argument_profile enrichment coverage)
  - wall-clock time
  - PM designation rate (conversational only)
  - phase completion rate (pipeline only)
  - total messages / turns (conversational only)

Usage:
    conda run -n projet-is-roo-new --no-capture-output python -m \
        argumentation_analysis.evaluation.conversational_benchmark

    # Or via pytest for regression integration:
    pytest tests/test_regression_golden.py -v -k "golden"
"""

import json
import time
import logging
import os
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("conversational_benchmark")

# ============================================================
# Benchmark texts
# ============================================================

BENCHMARK_TEXTS = {
    "vaccins": (
        "Les vaccins sont indispensables pour la sante publique. "
        "Les etudes scientifiques montrent que la vaccination a eradique la variole "
        "et reduit considerablement la polio. Ceux qui affirment que les vaccins "
        "sont dangereux ignorent les decades de recherche clinique. "
        "L'argument selon lequel les produits pharmaceutiques cachent les effets "
        "secondaires est une theorie du complot sans fondement. "
        "Les taux de vaccination eleves protegent aussi ceux qui ne peuvent pas "
        "etre vaccines grace a l'immunite collective."
    ),
    "peine_de_mort": (
        "La peine de mort est une sanction necessaire dans certains cas extremes. "
        "Elle sert de dissuasion contre les crimes les plus graves comme le meurtre "
        "de masse. Les opposants argumentent que le systeme judiciaire peut se tromper, "
        "mais les avancees en ADN reduisent considerablement ce risque. "
        "De plus, certains criminels sont irrecuperables et representent un danger "
        "permanent pour la societe. Cependant, il faut reconnaitre que la peine de mort "
        "est irreversible, ce qui rend toute erreur fatale. "
        "Le cout des appels et procedures est souvent superieur a l'emprisonnement a vie."
    ),
    "climat": (
        "Le changement climatique est une realite scientifique incontestable. "
        "Les mesures de temperature globale montrent une augmentation de 1.1 degres "
        "depuis l'ere preindustrielle. Les sceptiques affirment que le climat a toujours "
        "change, mais ils omettent la vitesse sans precedent du changement actuel. "
        "Les modeles predictifs sont unanimes sur l'impact des activites humaines. "
        "Ceux qui minimisent la crise climatique utilisent souvent des donnees "
        "selectives pour soutenir leur position. "
        "La transition energetique est non seulement necessaire mais aussi "
        "economiquement avantageuse a long terme."
    ),
}

MODES = ["standard", "full", "conversational"]


# ============================================================
# Data classes
# ============================================================


@dataclass
class BenchmarkRun:
    """Results from a single benchmark run."""
    text_name: str
    mode: str
    duration_seconds: float
    # State field fill rate
    non_empty_fields: int
    total_fields: int
    fill_rate: float = 0.0
    # Counts
    arguments_count: int = 0
    fallacies_count: int = 0
    quality_scores_count: int = 0
    counter_arguments_count: int = 0
    jtms_beliefs_count: int = 0
    dung_frameworks_count: int = 0
    governance_decisions_count: int = 0
    debate_transcripts_count: int = 0
    fol_results_count: int = 0
    # Quality metrics
    quality_score_mean: float = 0.0
    quality_score_variance: float = 0.0
    # Cross-reference density
    enrichment_coverage: float = 0.0
    enrichment_gaps: int = 0
    # Pipeline-specific
    phases_completed: int = 0
    phases_total: int = 0
    phase_completion_rate: float = 0.0
    # Conversational-specific
    total_messages: int = 0
    pm_designations: int = 0
    # Error tracking
    error: Optional[str] = None
    timestamp: str = ""


@dataclass
class BenchmarkComparison:
    """Aggregated comparison across modes for a single text."""
    text_name: str
    runs: Dict[str, BenchmarkRun] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text_name": self.text_name,
            "runs": {mode: asdict(run) for mode, run in self.runs.items()},
        }


# ============================================================
# Metric computation
# ============================================================


def _count_non_empty(state_dict: Dict[str, Any]) -> tuple:
    """Count non-empty fields in a state snapshot dict."""
    non_empty = 0
    total = 0
    for v in state_dict.values():
        total += 1
        if v and v not in ([], {}, "", None, 0):
            non_empty += 1
    return non_empty, total


def _compute_quality_stats(quality_scores: Dict[str, Dict[str, Any]]) -> tuple:
    """Compute mean and variance of quality overall scores."""
    if not quality_scores:
        return 0.0, 0.0
    scores = [v.get("overall", 0.0) for v in quality_scores.values() if isinstance(v, dict)]
    if not scores:
        return 0.0, 0.0
    mean = sum(scores) / len(scores)
    if len(scores) < 2:
        return mean, 0.0
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    return round(mean, 3), round(variance, 3)


def _compute_enrichment_metrics(state) -> tuple:
    """Compute enrichment coverage and gap count from state."""
    try:
        summary = state.get_enrichment_summary()
        total = summary.get("total_arguments", 0)
        if total == 0:
            return 0.0, 0
        enriched = (
            summary.get("with_fallacy_analysis", 0)
            + summary.get("with_quality_score", 0)
            + summary.get("with_counter_argument", 0)
            + summary.get("with_formal_verification", 0)
            + summary.get("with_jtms_belief", 0)
        )
        max_possible = total * 5  # 5 enrichment dimensions
        coverage = enriched / max_possible if max_possible > 0 else 0.0
        gaps = len(summary.get("gaps", []))
        return round(coverage, 3), gaps
    except Exception:
        return 0.0, 0


# ============================================================
# Runners
# ============================================================


async def run_pipeline_benchmark(
    text: str, text_name: str, workflow: str,
) -> BenchmarkRun:
    """Run pipeline mode benchmark."""
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    run = BenchmarkRun(
        text_name=text_name,
        mode=workflow,
        duration_seconds=0.0,
        non_empty_fields=0,
        total_fields=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    try:
        start = time.time()
        result = await run_unified_analysis(text=text, workflow_name=workflow)
        run.duration_seconds = round(time.time() - start, 1)

        state = result.get("unified_state")
        snapshot = result.get("state_snapshot", {})

        # Fill rate
        non_empty, total = _count_non_empty(snapshot)
        run.non_empty_fields = non_empty
        run.total_fields = total
        run.fill_rate = round(non_empty / total, 3) if total > 0 else 0.0

        # Counts
        if state:
            run.arguments_count = len(state.identified_arguments)
            run.fallacies_count = len(state.identified_fallacies)
            run.quality_scores_count = len(state.argument_quality_scores)
            run.counter_arguments_count = len(state.counter_arguments)
            run.jtms_beliefs_count = len(state.jtms_beliefs)
            run.dung_frameworks_count = len(state.dung_frameworks)
            run.governance_decisions_count = len(state.governance_decisions)
            run.debate_transcripts_count = len(state.debate_transcripts)
            run.fol_results_count = len(state.fol_analysis_results)

            # Quality stats
            run.quality_score_mean, run.quality_score_variance = _compute_quality_stats(
                state.argument_quality_scores
            )

            # Enrichment metrics
            run.enrichment_coverage, run.enrichment_gaps = _compute_enrichment_metrics(state)

        # Phase metrics
        summary = result.get("summary", {})
        run.phases_completed = summary.get("completed", 0)
        run.phases_total = summary.get("total", 0)
        run.phase_completion_rate = (
            round(run.phases_completed / run.phases_total, 3)
            if run.phases_total > 0 else 0.0
        )

    except Exception as e:
        run.error = str(e)
        logger.error(f"  FAILED {text_name}/{workflow}: {e}")

    return run


async def run_conversational_benchmark(
    text: str, text_name: str,
) -> BenchmarkRun:
    """Run conversational mode benchmark."""
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    run = BenchmarkRun(
        text_name=text_name,
        mode="conversational",
        duration_seconds=0.0,
        non_empty_fields=0,
        total_fields=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    try:
        start = time.time()
        result = await run_conversational_analysis(text=text, max_turns_per_phase=5)
        run.duration_seconds = round(time.time() - start, 1)

        # Conversational-specific metrics
        run.total_messages = result.get("total_messages", 0)

        # State extraction
        state = result.get("unified_state")
        snapshot = {}
        if state:
            snapshot = state.get_state_snapshot(summarize=True)
        elif "state_snapshot" in result:
            snapshot = result["state_snapshot"]

        non_empty, total = _count_non_empty(snapshot)
        run.non_empty_fields = result.get("state_non_empty_fields", non_empty)
        run.total_fields = total
        run.fill_rate = round(run.non_empty_fields / total, 3) if total > 0 else 0.0

        if state:
            run.arguments_count = len(state.identified_arguments)
            run.fallacies_count = len(state.identified_fallacies)
            run.quality_scores_count = len(state.argument_quality_scores)
            run.counter_arguments_count = len(state.counter_arguments)
            run.jtms_beliefs_count = len(state.jtms_beliefs)
            run.fol_results_count = len(state.fol_analysis_results)

            run.quality_score_mean, run.quality_score_variance = _compute_quality_stats(
                state.argument_quality_scores
            )
            run.enrichment_coverage, run.enrichment_gaps = _compute_enrichment_metrics(state)

            # PM designation rate
            conv_log = result.get("conversation_log", [])
            pm_count = sum(
                1 for msg in conv_log
                if isinstance(msg, dict) and "ProjectManager" in str(msg.get("agent_name", ""))
            )
            run.pm_designations = pm_count

    except Exception as e:
        run.error = str(e)
        logger.error(f"  FAILED {text_name}/conversational: {e}")

    return run


# ============================================================
# Main runner
# ============================================================


async def run_full_benchmark(
    text_names: Optional[List[str]] = None,
    modes: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run the full benchmark suite.

    Args:
        text_names: Subset of text names to benchmark (default: all).
        modes: Subset of modes to run (default: all).
        output_dir: Directory to save JSON results.

    Returns:
        Dict with comparisons and summary table.
    """
    texts = text_names or list(BENCHMARK_TEXTS.keys())
    modes = modes or MODES

    comparisons: List[BenchmarkComparison] = []
    all_runs: List[BenchmarkRun] = []

    for text_name in texts:
        text = BENCHMARK_TEXTS[text_name]
        comparison = BenchmarkComparison(text_name=text_name)

        for mode in modes:
            logger.info(f"Benchmark: {text_name} / {mode}")
            if mode == "conversational":
                br = await run_conversational_benchmark(text, text_name)
            else:
                br = await run_pipeline_benchmark(text, text_name, mode)
            comparison.runs[mode] = br
            all_runs.append(br)

        comparisons.append(comparison)

    # Build summary
    summary = _build_summary_table(comparisons)

    # Save if output_dir provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        results_file = output_dir / f"conversational_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "comparisons": [c.to_dict() for c in comparisons],
                    "summary_table": summary,
                },
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        logger.info(f"Results saved: {results_file}")

    return {
        "comparisons": comparisons,
        "summary": summary,
        "total_runs": len(all_runs),
        "successful_runs": sum(1 for r in all_runs if r.error is None),
        "failed_runs": sum(1 for r in all_runs if r.error is not None),
    }


def _build_summary_table(comparisons: List[BenchmarkComparison]) -> List[Dict[str, Any]]:
    """Build a flat summary table from comparisons."""
    rows = []
    for comp in comparisons:
        for mode, run in comp.runs.items():
            rows.append({
                "text": run.text_name,
                "mode": run.mode,
                "duration_s": run.duration_seconds,
                "fill_rate": run.fill_rate,
                "args": run.arguments_count,
                "fallacies": run.fallacies_count,
                "quality_mean": run.quality_score_mean,
                "quality_var": run.quality_score_variance,
                "cross_ref_coverage": run.enrichment_coverage,
                "phases": f"{run.phases_completed}/{run.phases_total}" if run.phases_total > 0 else "n/a",
                "messages": run.total_messages,
                "error": run.error,
            })
    return rows


def print_summary(result: Dict[str, Any]):
    """Print a formatted summary table."""
    print(f"\n{'='*100}")
    print(f" CONVERSATIONAL BENCHMARK RESULTS")
    print(f"{'='*100}")
    print(f"  Runs: {result['successful_runs']}/{result['total_runs']} successful")
    print()

    header = f"  {'Text':<15} {'Mode':<16} {'Time':>6} {'Fill%':>6} {'Args':>4} {'Fall':>4} {'QMean':>6} {'QCov':>6} {'Phases':>8} {'Msgs':>5}"
    print(header)
    print(f"  {'-'*90}")

    for row in result["summary"]:
        if row.get("error"):
            print(f"  {row['text']:<15} {row['mode']:<16} FAIL: {row['error'][:50]}")
        else:
            print(
                f"  {row['text']:<15} {row['mode']:<16} "
                f"{row['duration_s']:>5.1f}s "
                f"{row['fill_rate']:>5.1%} "
                f"{row['args']:>4} "
                f"{row['fallacies']:>4} "
                f"{row['quality_mean']:>6.2f} "
                f"{row['cross_ref_coverage']:>5.1%} "
                f"{row['phases']:>8} "
                f"{row['messages']:>5}"
            )
    print(f"{'='*100}\n")


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Conversational baseline benchmark (Issue #308)")
    parser.add_argument(
        "--mode", action="append", dest="modes",
        choices=["standard", "full", "conversational"],
        help="Which mode(s) to benchmark (repeatable, default: all)",
    )
    parser.add_argument(
        "--text", action="append", dest="texts",
        choices=list(BENCHMARK_TEXTS.keys()),
        help="Which text(s) to benchmark (repeatable, default: all)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=".analysis_kb/results",
        help="Output directory for JSON results",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for name in ["httpx", "openai", "semantic_kernel"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    result = await run_full_benchmark(
        text_names=args.texts,
        modes=args.modes,
        output_dir=Path(args.output_dir),
    )
    print_summary(result)


if __name__ == "__main__":
    asyncio.run(main())

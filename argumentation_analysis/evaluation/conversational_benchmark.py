"""Conversational vs Sequential benchmark (#308).

Compares 3 orchestration modes on benchmark texts:
- standard: sequential pipeline (WorkflowExecutor)
- full: extended sequential pipeline
- conversational: multi-agent dialogue (AgentGroupChat)

Measures per run:
- state_field_fill_rate: fraction of 32 possible state fields with data
- fallacy_count: number of fallacies detected
- quality_scores_count: number of arguments with quality evaluation
- argument_count: number of extracted arguments
- counter_argument_count: number of counter-arguments generated
- jtms_belief_count: JTMS belief network size
- cross_ref_density: enrichment coverage from get_enrichment_summary()
- wall_clock_seconds: total execution time
- total_messages: (conversational only) number of agent messages
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("conversational_benchmark")


# ── Benchmark texts ──────────────────────────────────────────────────────

BENCHMARK_TEXTS = {
    "kremlin_reform": (
        "Le Premier ministre a déclaré que la réforme des retraites est nécessaire "
        "car tous les pays européens l'ont déjà faite. C'est un argument d'autorité "
        "qui ne tient pas compte des différences structurelles entre les systèmes. "
        "De plus, affirmer que « si nous n'agissons pas maintenant, le système "
        "s'effondrera dans cinq ans » est un appel à la peur classique. "
        "Les syndicats rétorquent que le gouvernement utilise un sophisme naturaliste "
        "en prétendant que travailler plus longtemps est « dans l'ordre des choses ». "
        "Par ailleurs, le ministre des finances a présenté des chiffres montrant "
        "que le déficit atteindra 2.3% du PIB d'ici 2030, mais cette projection "
        "repose sur des hypothèses de croissance optimistes de 1.8% par an."
    ),
    "climate_debate": (
        "Les climatosceptiques affirment que le réchauffement climatique est un cycle "
        "naturel, invoquant le Moyen Âge chaud comme preuve. C'est un sophisme "
        "d'échantillon biaisé : une période locale ne représente pas le climat global. "
        "Ils ajoutent que « les scientifiques ne sont pas d'accord entre eux », "
        "ce qui est un appel à la controverse fabriqué — 97% des climatologues "
        "confirment l'origine anthropique. L'argument « la technologie résoudra tout » "
        "est une pétition de principe qui suppose ce qu'elle devrait démontrer. "
        "Enfin, accuser les écologistes d'être « anti-progrès » constitue un "
        "homme de paille : personne ne propose de revenir à l'âge de pierre."
    ),
    "education_policy": (
        "Le ministre de l'éducation prétend que les résultats PISA prouvent "
        "l'efficacité de sa réforme, alors que les scores n'ont augmenté que "
        "de 2 points sur 3 ans — une fausse précision statistique. Son opposant "
        "rétorque avec un tu quoque : « vous avez fait pire quand vous étiez "
        "au pouvoir ». Le syndicat enseignant dénonce un faux dilemme : "
        "« soit on augmente les heures de cours, soit le niveau baisse » ignore "
        "d'autres leviers comme la formation des enseignants. La presse commet "
        "un amalgame en comparant le système français au système finlandais "
        "sans tenir compte des différences culturelles et socio-économiques."
    ),
}

# All 32 possible state fields for fill rate computation
ALL_STATE_FIELDS = [
    "identified_arguments",
    "identified_fallacies",
    "belief_sets",
    "query_log",
    "answers",
    "extracts",
    "counter_arguments",
    "argument_quality_scores",
    "jtms_beliefs",
    "dung_frameworks",
    "governance_decisions",
    "debate_transcripts",
    "transcription_segments",
    "semantic_index_refs",
    "neural_fallacy_scores",
    "ranking_results",
    "aspic_results",
    "belief_revision_results",
    "dialogue_results",
    "probabilistic_results",
    "bipolar_results",
    "fol_analysis_results",
    "propositional_analysis_results",
    "modal_analysis_results",
    "formal_synthesis_reports",
    "nl_to_logic_translations",
    "workflow_results",
    "analysis_tasks",
    "final_conclusion",
    "raw_text",
]

COUNTABLE_FIELDS = [
    "identified_arguments",
    "identified_fallacies",
    "counter_arguments",
    "argument_quality_scores",
    "jtms_beliefs",
    "governance_decisions",
    "debate_transcripts",
    "fol_analysis_results",
    "propositional_analysis_results",
    "nl_to_logic_translations",
    "neural_fallacy_scores",
]


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class RunMetrics:
    """Metrics from a single benchmark run."""

    text_id: str
    mode: str
    wall_clock_seconds: float = 0.0
    argument_count: int = 0
    fallacy_count: int = 0
    quality_scores_count: int = 0
    counter_argument_count: int = 0
    jtms_belief_count: int = 0
    debate_transcript_count: int = 0
    governance_decision_count: int = 0
    fol_count: int = 0
    pl_count: int = 0
    nl_to_logic_count: int = 0
    neural_fallacy_count: int = 0
    state_field_fill_rate: float = 0.0
    cross_ref_density: float = 0.0
    total_messages: int = 0  # conversational only
    completed_phases: int = 0
    failed_phases: int = 0
    skipped_phases: int = 0
    error: str = ""


@dataclass
class BenchmarkReport:
    """Aggregated benchmark results."""

    runs: List[RunMetrics] = field(default_factory=list)
    mode_averages: Dict[str, Dict[str, float]] = field(default_factory=dict)
    summary: str = ""

    def compute_averages(self):
        """Compute per-mode average metrics."""
        for mode in ("standard", "full", "conversational"):
            mode_runs = [r for r in self.runs if r.mode == mode and not r.error]
            if not mode_runs:
                continue
            n = len(mode_runs)
            self.mode_averages[mode] = {
                "avg_wall_clock": sum(r.wall_clock_seconds for r in mode_runs) / n,
                "avg_arguments": sum(r.argument_count for r in mode_runs) / n,
                "avg_fallacies": sum(r.fallacy_count for r in mode_runs) / n,
                "avg_quality_scores": sum(r.quality_scores_count for r in mode_runs)
                / n,
                "avg_counter_args": sum(r.counter_argument_count for r in mode_runs)
                / n,
                "avg_jtms_beliefs": sum(r.jtms_belief_count for r in mode_runs) / n,
                "avg_field_fill_rate": sum(r.state_field_fill_rate for r in mode_runs)
                / n,
                "avg_cross_ref": sum(r.cross_ref_density for r in mode_runs) / n,
                "avg_messages": sum(r.total_messages for r in mode_runs) / n,
                "run_count": n,
                "error_rate": sum(1 for r in self.runs if r.mode == mode and r.error)
                / len([r for r in self.runs if r.mode == mode]),
            }


def extract_metrics(
    text_id: str,
    mode: str,
    result: Dict[str, Any],
    duration: float,
) -> RunMetrics:
    """Extract RunMetrics from a pipeline result dict."""
    metrics = RunMetrics(text_id=text_id, mode=mode, wall_clock_seconds=duration)

    # Get state from result
    state = result.get("unified_state")
    if state is None:
        metrics.error = "No unified_state in result"
        return metrics

    # Count fields
    metrics.argument_count = len(getattr(state, "identified_arguments", {}))
    metrics.fallacy_count = len(getattr(state, "identified_fallacies", {}))
    metrics.quality_scores_count = len(getattr(state, "argument_quality_scores", {}))
    metrics.counter_argument_count = len(getattr(state, "counter_arguments", []))
    metrics.jtms_belief_count = len(getattr(state, "jtms_beliefs", {}))
    metrics.debate_transcript_count = len(getattr(state, "debate_transcripts", []))
    metrics.governance_decision_count = len(getattr(state, "governance_decisions", []))
    metrics.fol_count = len(getattr(state, "fol_analysis_results", []))
    metrics.pl_count = len(getattr(state, "propositional_analysis_results", []))
    metrics.nl_to_logic_count = len(getattr(state, "nl_to_logic_translations", []))
    metrics.neural_fallacy_count = len(getattr(state, "neural_fallacy_scores", []))

    # State field fill rate
    filled = 0
    for field_name in ALL_STATE_FIELDS:
        val = getattr(state, field_name, None)
        if val is not None:
            if isinstance(val, (dict, list)):
                if len(val) > 0:
                    filled += 1
            elif isinstance(val, str):
                if val.strip():
                    filled += 1
            else:
                filled += 1
    metrics.state_field_fill_rate = (
        filled / len(ALL_STATE_FIELDS) if ALL_STATE_FIELDS else 0
    )

    # Cross-reference density
    try:
        enrichment = state.get_enrichment_summary()
        total = enrichment.get("total_arguments", 0)
        if total > 0:
            with_quality = enrichment.get("with_quality_score", 0)
            with_fallacy = enrichment.get("with_fallacy_analysis", 0)
            with_counter = enrichment.get("with_counter_argument", 0)
            with_formal = enrichment.get("with_formal_verification", 0)
            # Density = average enrichment coverage across 4 dimensions
            metrics.cross_ref_density = (
                with_quality + with_fallacy + with_counter + with_formal
            ) / (4 * total)
    except Exception:
        pass

    # Conversational-specific
    metrics.total_messages = result.get("total_messages", 0)

    # Phase summary
    summary = result.get("summary", {})
    metrics.completed_phases = summary.get("completed", 0)
    metrics.failed_phases = summary.get("failed", 0)
    metrics.skipped_phases = summary.get("skipped", 0)

    return metrics


class ConversationalBenchmarkRunner:
    """Run comparative benchmarks across orchestration modes."""

    def __init__(
        self,
        texts: Optional[Dict[str, str]] = None,
        modes: Optional[List[str]] = None,
    ):
        self.texts = texts or BENCHMARK_TEXTS
        self.modes = modes or ["standard", "full", "conversational"]

    async def run_single(self, text_id: str, text: str, mode: str) -> RunMetrics:
        """Run a single benchmark cell (text × mode)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        logger.info(f"Running benchmark: {text_id} × {mode}")
        start = time.time()
        try:
            result = await run_unified_analysis(text, workflow_name=mode)
            duration = time.time() - start
            metrics = extract_metrics(text_id, mode, result, duration)
        except Exception as e:
            duration = time.time() - start
            logger.error(f"Benchmark {text_id}×{mode} failed: {e}")
            metrics = RunMetrics(
                text_id=text_id,
                mode=mode,
                wall_clock_seconds=duration,
                error=str(e),
            )
        return metrics

    async def run_benchmark(self) -> BenchmarkReport:
        """Run full benchmark matrix: all texts × all modes."""
        report = BenchmarkReport()

        for text_id, text in self.texts.items():
            for mode in self.modes:
                metrics = await self.run_single(text_id, text, mode)
                report.runs.append(metrics)
                logger.info(
                    f"  {text_id}×{mode}: "
                    f"args={metrics.argument_count} "
                    f"fallacies={metrics.fallacy_count} "
                    f"fill={metrics.state_field_fill_rate:.0%} "
                    f"time={metrics.wall_clock_seconds:.1f}s"
                )

        report.compute_averages()
        report.summary = self._format_summary(report)
        return report

    def _format_summary(self, report: BenchmarkReport) -> str:
        """Format benchmark report as markdown."""
        lines = ["# Conversational vs Sequential Benchmark\n"]

        # Per-run table
        lines.append("## Per-Run Results\n")
        lines.append(
            f"{'Text':<20} {'Mode':<15} {'Args':>5} {'Fall':>5} {'Qual':>5} "
            f"{'CAs':>5} {'JTMS':>5} {'Fill':>6} {'XRef':>6} {'Time':>7} {'Msgs':>5}"
        )
        lines.append("-" * 100)
        for r in report.runs:
            if r.error:
                lines.append(f"{r.text_id:<20} {r.mode:<15} ERROR: {r.error[:50]}")
            else:
                lines.append(
                    f"{r.text_id:<20} {r.mode:<15} "
                    f"{r.argument_count:>5} {r.fallacy_count:>5} "
                    f"{r.quality_scores_count:>5} {r.counter_argument_count:>5} "
                    f"{r.jtms_belief_count:>5} {r.state_field_fill_rate:>5.0%} "
                    f"{r.cross_ref_density:>5.1%} {r.wall_clock_seconds:>6.1f}s "
                    f"{r.total_messages:>5}"
                )
        lines.append("")

        # Per-mode averages
        lines.append("## Mode Averages\n")
        for mode, avgs in report.mode_averages.items():
            lines.append(f"### {mode}")
            for key, val in avgs.items():
                if isinstance(val, float):
                    lines.append(f"  {key}: {val:.2f}")
                else:
                    lines.append(f"  {key}: {val}")
            lines.append("")

        return "\n".join(lines)

    def save_report(self, report: BenchmarkReport, path: str):
        """Save report to JSON."""
        data = {
            "runs": [asdict(r) for r in report.runs],
            "mode_averages": report.mode_averages,
            "summary": report.summary,
            "text_count": len(self.texts),
            "modes": self.modes,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Report saved to {path}")

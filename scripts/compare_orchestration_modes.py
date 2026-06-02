"""Compare orchestration modes on the same corpus.

Runs multiple orchestration modes (pipeline, conversational, hierarchical,
cluedo_baseline, cluedo_extended, conversation_deterministic) on benchmark
texts and produces a markdown comparison report with aggregate metrics.

Usage:
    # Compare all available modes on benchmark texts
    python scripts/compare_orchestration_modes.py

    # Specific modes only
    python scripts/compare_orchestration_modes.py --modes pipeline conversational

    # Save report to file
    python scripts/compare_orchestration_modes.py --output report.md

    # Dry run (show which modes would run, no execution)
    python scripts/compare_orchestration_modes.py --dry-run

Modes are skipped gracefully if their orchestrator is unavailable (e.g. missing
LLM, JVM not initialized, or mode not yet wired).
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("orchestration_mode_harness")

# Reduce noisy loggers
for _name in ("httpx", "openai", "semantic_kernel", "urllib3"):
    logging.getLogger(_name).setLevel(logging.WARNING)


# ── Benchmark texts (opaque IDs, no raw content in reports) ──────────────

BENCHMARK_TEXTS = {
    "corpus_A": (
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
    "corpus_B": (
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
    "corpus_C": (
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


@dataclass
class ModeResult:
    """Result of running one orchestration mode on one corpus."""

    mode: str
    corpus_id: str
    success: bool
    error: Optional[str] = None
    duration_seconds: float = 0.0
    state_fill_rate: float = 0.0
    fallacy_count: int = 0
    argument_count: int = 0
    phases_completed: int = 0
    phases_total: int = 0
    capabilities_used: List[str] = field(default_factory=list)
    capabilities_missing: List[str] = field(default_factory=list)
    extra_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Mode runners ─────────────────────────────────────────────────────────


async def run_pipeline_mode(
    text: str, corpus_id: str, workflow_name: str = "standard"
) -> ModeResult:
    """Run UnifiedPipeline (modern workflow engine)."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    start = time.time()
    result = await run_unified_analysis(text=text, workflow_name=workflow_name)
    duration = time.time() - start

    summary = result.get("summary", {})
    state = result.get("state_snapshot", {})

    total_fields = len(state) if state else 1
    non_empty = sum(
        1 for v in (state or {}).values()
        if v and v not in ([], {}, "", None, 0)
    )

    return ModeResult(
        mode=f"pipeline_{workflow_name}",
        corpus_id=corpus_id,
        success=True,
        duration_seconds=round(duration, 2),
        state_fill_rate=round(non_empty / max(total_fields, 1), 3),
        fallacy_count=result.get("extra_metrics", {}).get("fallacy_count", 0),
        argument_count=result.get("extra_metrics", {}).get("argument_count", 0),
        phases_completed=summary.get("completed", 0),
        phases_total=summary.get("total", 0),
        capabilities_used=result.get("capabilities_used", []),
        capabilities_missing=result.get("capabilities_missing", []),
    )


async def run_conversational_mode(
    text: str, corpus_id: str
) -> ModeResult:
    """Run conversational orchestrator (AgentGroupChat multi-agent)."""
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    start = time.time()
    result = await run_conversational_analysis(text=text)
    duration = time.time() - start

    state = result.get("state_snapshot", {})
    total_fields = len(state) if state else 1
    non_empty = sum(
        1 for v in (state or {}).values()
        if v and v not in ([], {}, "", None, 0)
    )

    return ModeResult(
        mode="conversational",
        corpus_id=corpus_id,
        success=True,
        duration_seconds=round(duration, 2),
        state_fill_rate=round(non_empty / max(total_fields, 1), 3),
        fallacy_count=result.get("extra_metrics", {}).get("fallacy_count", 0),
        phases_completed=len(result.get("phases", [])),
        phases_total=len(result.get("phases", [])),
        capabilities_used=result.get("capabilities_used", []),
        extra_metrics={
            "total_messages": result.get("total_messages", 0),
            "duration_seconds_raw": result.get("duration_seconds", 0),
        },
    )


async def run_conversation_deterministic_mode(
    text: str, corpus_id: str
) -> ModeResult:
    """Run ConversationOrchestrator in demo mode (SimulatedAgent, no LLM)."""
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )

    start = time.time()
    orch = ConversationOrchestrator(mode="demo")
    report = orch.run_orchestration(text)
    duration = time.time() - start

    conv_state = orch.get_conversation_state()

    return ModeResult(
        mode="conversation_deterministic",
        corpus_id=corpus_id,
        success=True,
        duration_seconds=round(duration, 3),
        state_fill_rate=round(conv_state.get("state", {}).get("score", 0), 3),
        fallacy_count=conv_state.get("state", {}).get("fallacies_detected", 0),
        phases_completed=3,  # informal + fol + synthesis
        phases_total=3,
        extra_metrics={
            "messages_count": conv_state.get("messages_count", 0),
            "tools_count": conv_state.get("tools_count", 0),
            "processing_time": conv_state.get("processing_time", 0),
        },
    )


async def run_hierarchical_mode(
    text: str, corpus_id: str
) -> ModeResult:
    """Run hierarchical orchestrator (if available)."""
    try:
        from argumentation_analysis.orchestration.hierarchical.orchestrator import (
            HierarchicalOrchestrator,
        )
    except ImportError:
        return ModeResult(
            mode="hierarchical",
            corpus_id=corpus_id,
            success=False,
            error="HierarchicalOrchestrator not available (not yet merged)",
        )

    start = time.time()
    try:
        orch = HierarchicalOrchestrator()
        result = await orch.analyze(text)
        duration = time.time() - start

        return ModeResult(
            mode="hierarchical",
            corpus_id=corpus_id,
            success=True,
            duration_seconds=round(duration, 2),
            extra_metrics=result if isinstance(result, dict) else {},
        )
    except Exception as e:
        duration = time.time() - start
        return ModeResult(
            mode="hierarchical",
            corpus_id=corpus_id,
            success=False,
            error=str(e)[:200],
            duration_seconds=round(duration, 2),
        )


async def run_cluedo_baseline_mode(
    text: str, corpus_id: str
) -> ModeResult:
    """Run Cluedo 2-agent baseline (if available)."""
    return ModeResult(
        mode="cluedo_baseline",
        corpus_id=corpus_id,
        success=False,
        error="Cluedo baseline requires LLM + kernel setup — not yet wired for text analysis",
    )


async def run_cluedo_extended_mode(
    text: str, corpus_id: str
) -> ModeResult:
    """Run Cluedo 3-agent extended (if available)."""
    return ModeResult(
        mode="cluedo_extended",
        corpus_id=corpus_id,
        success=False,
        error="Cluedo extended requires LLM + kernel setup — not yet wired for text analysis",
    )


# ── Mode registry ────────────────────────────────────────────────────────

MODE_RUNNERS = {
    "pipeline": lambda text, cid: run_pipeline_mode(text, cid, "standard"),
    "pipeline_light": lambda text, cid: run_pipeline_mode(text, cid, "light"),
    "pipeline_full": lambda text, cid: run_pipeline_mode(text, cid, "full"),
    "conversational": run_conversational_mode,
    "conversation_deterministic": run_conversation_deterministic_mode,
    "hierarchical": run_hierarchical_mode,
    "cluedo_baseline": run_cluedo_baseline_mode,
    "cluedo_extended": run_cluedo_extended_mode,
}


# ── Reporting ────────────────────────────────────────────────────────────


def generate_report(results: List[ModeResult], title: str = "Orchestration Mode Comparison") -> str:
    """Generate markdown comparison report."""
    lines = [
        f"# {title}",
        "",
        f"Generated: {datetime.now().isoformat()}",
        f"Modes tested: {len(set(r.mode for r in results))}",
        f"Corpora tested: {len(set(r.corpus_id for r in results))}",
        f"Total runs: {len(results)}",
        "",
    ]

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| Mode | Corpus | Success | Duration | State Fill | Fallacies | Args | Phases |"
    )
    lines.append(
        "|------|--------|---------|----------|------------|-----------|------|--------|"
    )

    for r in sorted(results, key=lambda x: (x.mode, x.corpus_id)):
        status = "✅" if r.success else "❌"
        err = f" ({r.error})" if r.error and len(r.error) < 50 else ""
        lines.append(
            f"| {r.mode} | {r.corpus_id} | {status}{err} | "
            f"{r.duration_seconds:.2f}s | {r.state_fill_rate:.1%} | "
            f"{r.fallacy_count} | {r.argument_count} | "
            f"{r.phases_completed}/{r.phases_total} |"
        )

    lines.append("")

    # Cross-mode comparison per corpus
    corpora = sorted(set(r.corpus_id for r in results))
    for corpus_id in corpora:
        corpus_results = [r for r in results if r.corpus_id == corpus_id and r.success]
        if not corpus_results:
            continue

        lines.append(f"## {corpus_id} — Cross-Mode Comparison")
        lines.append("")

        # Duration comparison
        durations = {r.mode: r.duration_seconds for r in corpus_results}
        if durations:
            fastest = min(durations, key=durations.get)
            lines.append(f"**Fastest mode**: `{fastest}` ({durations[fastest]:.2f}s)")
            lines.append("")

        # Fill rate comparison
        fills = {r.mode: r.state_fill_rate for r in corpus_results if r.state_fill_rate > 0}
        if fills:
            best_fill = max(fills, key=fills.get)
            lines.append(f"**Highest state fill**: `{best_fill}` ({fills[best_fill]:.1%})")
            lines.append("")

        # Capabilities used
        for r in corpus_results:
            if r.capabilities_used:
                lines.append(f"**{r.mode}** capabilities: {', '.join(r.capabilities_used)}")
                lines.append("")

        lines.append("")

    # Skipped/failed modes
    failed = [r for r in results if not r.success]
    if failed:
        lines.append("## Skipped/Failed Modes")
        lines.append("")
        for r in failed:
            lines.append(f"- **{r.mode}** ({r.corpus_id}): {r.error}")
        lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────


async def run_all(
    modes: Optional[List[str]] = None,
    corpora: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    dry_run: bool = False,
) -> List[ModeResult]:
    """Run selected modes on selected corpora."""
    if modes is None:
        modes = list(MODE_RUNNERS.keys())
    if corpora is None:
        corpora = list(BENCHMARK_TEXTS.keys())

    if dry_run:
        print("Dry run — modes that would be tested:")
        for mode in modes:
            runner = MODE_RUNNERS.get(mode)
            available = "available" if runner else "UNKNOWN"
            print(f"  {mode}: {available}")
        print(f"\nCorpora: {', '.join(corpora)}")
        return []

    # Load environment
    try:
        from argumentation_analysis.core.jvm_setup import initialize_jvm
        initialize_jvm()
    except Exception as e:
        logger.warning(f"JVM init failed: {e}")

    results: List[ModeResult] = []

    for corpus_id in corpora:
        text = BENCHMARK_TEXTS.get(corpus_id)
        if text is None:
            logger.warning(f"Unknown corpus: {corpus_id}, skipping")
            continue

        for mode in modes:
            runner = MODE_RUNNERS.get(mode)
            if runner is None:
                logger.warning(f"Unknown mode: {mode}, skipping")
                continue

            logger.info(f"Running {mode} on {corpus_id} ({len(text)} chars)...")
            try:
                result = await runner(text, corpus_id)
                results.append(result)
                status = "OK" if result.success else f"FAILED: {result.error}"
                logger.info(f"  → {mode} on {corpus_id}: {status} ({result.duration_seconds:.2f}s)")
            except Exception as e:
                results.append(ModeResult(
                    mode=mode,
                    corpus_id=corpus_id,
                    success=False,
                    error=f"Exception: {str(e)[:200]}",
                ))
                logger.error(f"  → {mode} on {corpus_id}: EXCEPTION {e}")

    # Generate report
    report = generate_report(results)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        logger.info(f"Report written to {output_path}")

        # Also write raw JSON
        json_path = output_path.with_suffix(".json")
        json_path.write_text(
            json.dumps([r.to_dict() for r in results], indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"Raw results written to {json_path}")
    else:
        print(report)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compare orchestration modes on benchmark corpora",
    )
    parser.add_argument(
        "--modes", "-m", nargs="+", default=None,
        help=f"Modes to test: {', '.join(MODE_RUNNERS.keys())}",
    )
    parser.add_argument(
        "--corpora", "-c", nargs="+", default=None,
        help=f"Corpora to test: {', '.join(BENCHMARK_TEXTS.keys())}",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output file for report (markdown + json)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show which modes would run without executing",
    )
    args = parser.parse_args()

    asyncio.run(run_all(
        modes=args.modes,
        corpora=args.corpora,
        output_file=args.output,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()

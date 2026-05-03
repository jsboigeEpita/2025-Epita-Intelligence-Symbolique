#!/usr/bin/env python3
"""Profile the spectacular workflow for performance bottleneck analysis (Issue #400).

Produces three profiling artifacts in .profiling/:
  - spectacular_cprofile.prof     (cProfile binary, viewable with snakeviz)
  - spectacular_pyinstrument.html (pyinstrument HTML flame graph)
  - spectacular_phase_timings.json (per-phase wall-clock breakdown)

Uses cached LLM responses when LLM_CACHE_MODE=replay for reproducibility.
Falls back to live LLM if no cache is available.

Usage:
    # With cached LLM responses (reproducible, fast)
    set LLM_CACHE_MODE=replay
    python scripts/profile_spectacular.py

    # With live LLM (records cache for future replays)
    set LLM_CACHE_MODE=record
    python scripts/profile_spectacular.py

    # No caching (passthrough)
    python scripts/profile_spectacular.py
"""

import argparse
import asyncio
import cProfile
import json
import logging
import os
import pstats
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyinstrument

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv

    load_dotenv(project_root / ".env")
except ImportError:
    pass

PROFILING_DIR = project_root / ".profiling"
PROFILING_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("profile_spectacular")

# Suppress noisy loggers during profiling
for _name in ("httpx", "openai", "httpcore", "urllib3", "semantic_kernel.connectors.ai"):
    logging.getLogger(_name).setLevel(logging.WARNING)


# --- Sample text for profiling (no sensitive data) ---
SAMPLE_TEXT = (
    "Le réchauffement climatique est un mythe inventé par les médias. "
    "97% des scientifiques seraient d'accord, mais la science n'est pas une démocratie ! "
    "Si nous arrêtons le charbon demain, l'économie s'effondrera et des millions de gens "
    "perdront leur emploi. D'ailleurs, cet hiver a été le plus froid depuis 10 ans, "
    "ce qui prouve que la planète ne se réchauffe pas. Les énergies renouvelables "
    "sont une arnaque financée par des intérêts privés pour contrôler le marché de l'énergie."
)


def _load_encrypted_doc(doc_index: int = 0, max_chars: int = 3000) -> Optional[str]:
    """Try to load a document from the encrypted dataset (opaque ID only)."""
    try:
        from argumentation_analysis.core.io_manager import load_extract_definitions

        passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
        if not passphrase:
            return None

        dataset_path = project_root / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
        if not dataset_path.exists():
            return None

        definitions = load_extract_definitions(str(dataset_path), passphrase)
        if doc_index < len(definitions):
            text = definitions[doc_index].get("text", "")
            if text:
                return text[:max_chars]
    except Exception as e:
        logger.warning(f"Could not load encrypted doc: {e}")
    return None


class PhaseTimingCollector:
    """Collect per-phase wall-clock timings by monkey-patching WorkflowExecutor."""

    def __init__(self):
        self.phase_timings: List[Dict[str, Any]] = []
        self._original_execute = None

    def install(self):
        """Hook into WorkflowExecutor.execute to capture per-phase timing."""
        from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor

        original_execute = WorkflowExecutor.execute
        self._original_execute = original_execute
        collector = self

        async def instrumented_execute(self_exec, workflow, input_data, context=None, state=None, state_writers=None):
            results = await original_execute(self_exec, workflow, input_data, context, state, state_writers)
            for name, result in results.items():
                entry = {
                    "phase": name,
                    "capability": result.capability,
                    "status": result.status.value,
                    "duration_seconds": round(result.duration_seconds, 4) if result.duration_seconds else 0,
                    "error": result.error,
                }
                collector.phase_timings.append(entry)
            return results

        WorkflowExecutor.execute = instrumented_execute

    def uninstall(self):
        """Restore original execute method."""
        from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor

        if self._original_execute:
            WorkflowExecutor.execute = self._original_execute


async def run_spectacular_with_profiling(
    text: str,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Run spectacular workflow with full profiling instrumentation."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    # Set up cache mode for reproducibility
    if use_cache:
        cache_mode = os.environ.get("LLM_CACHE_MODE", "off").lower()
        if cache_mode == "off":
            logger.info("LLM_CACHE_MODE not set — profiling with live LLM (no caching)")
        else:
            logger.info(f"LLM_CACHE_MODE={cache_mode} — profiling with cached responses")

    # Install phase timing collector
    timing_collector = PhaseTimingCollector()
    timing_collector.install()

    # Start tracemalloc for memory tracking
    tracemalloc.start()

    # cProfile setup
    profiler = cProfile.Profile()
    profiler.enable()

    # pyinstrument setup
    pyi_profiler = pyinstrument.Profiler(async_mode="enabled")
    pyi_profiler.start()

    # --- Run the workflow ---
    start_wall = time.monotonic()
    try:
        result = await run_unified_analysis(
            text=text,
            workflow_name="spectacular",
            create_state=True,
        )
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        result = {"error": str(e)}
    wall_clock = time.monotonic() - start_wall

    # --- Collect profiling data ---
    pyi_profiler.stop()
    profiler.disable()

    # Memory snapshot
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Uninstall timing collector
    timing_collector.uninstall()

    # --- Save artifacts ---

    # 1. cProfile binary
    cprofile_path = PROFILING_DIR / "spectacular_cprofile.prof"
    profiler.dump_stats(str(cprofile_path))
    logger.info(f"cProfile saved: {cprofile_path}")

    # 2. pyinstrument HTML
    pyi_path = PROFILING_DIR / "spectacular_pyinstrument.html"
    html = pyi_profiler.output_html()
    pyi_path.write_text(html, encoding="utf-8")
    logger.info(f"pyinstrument HTML saved: {pyi_path}")

    # 3. Phase timings JSON
    phase_timings = timing_collector.phase_timings
    total_phase_time = sum(p["duration_seconds"] for p in phase_timings)

    # cProfile top functions (filter profiler internals)
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")
    skip_prefixes = ("pyinstrument", "cProfile", "pstats", "tracemalloc")
    top_functions = []
    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        func_str = f"{func[0]}:{func[2]}" if len(func) == 3 else str(func)
        if any(s in func_str for s in skip_prefixes):
            continue
        if tt < 0.01:
            continue
        top_functions.append({
            "function": func_str,
            "calls": nc,
            "total_time_s": round(tt, 4),
            "cumulative_time_s": round(ct, 4),
        })
    top_functions.sort(key=lambda x: x["cumulative_time_s"], reverse=True)
    top_functions = top_functions[:30]

    # tracemalloc top allocators
    tracemalloc.start()
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics("lineno")[:20]
    top_allocators = []
    for stat in top_stats:
        top_allocators.append({
            "file": str(stat.traceback),
            "size_kb": round(stat.size / 1024, 1),
            "count": stat.count,
        })
    tracemalloc.stop()

    profiling_output = {
        "wall_clock_seconds": round(wall_clock, 2),
        "total_phase_time_seconds": round(total_phase_time, 2),
        "overhead_seconds": round(wall_clock - total_phase_time, 2),
        "memory_current_mb": round(current_mem / 1024 / 1024, 2),
        "memory_peak_mb": round(peak_mem / 1024 / 1024, 2),
        "phase_timings": sorted(phase_timings, key=lambda p: p["duration_seconds"], reverse=True),
        "top_functions_cumulative": top_functions[:20],
        "top_allocators_kb": top_allocators[:10],
        "workflow_summary": {
            "completed": result.get("summary", {}).get("completed", 0) if isinstance(result, dict) else 0,
            "failed": result.get("summary", {}).get("failed", 0) if isinstance(result, dict) else 0,
            "skipped": result.get("summary", {}).get("skipped", 0) if isinstance(result, dict) else 0,
            "total": result.get("summary", {}).get("total", 0) if isinstance(result, dict) else 0,
        },
    }

    timings_path = PROFILING_DIR / "spectacular_phase_timings.json"
    timings_path.write_text(
        json.dumps(profiling_output, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    logger.info(f"Phase timings saved: {timings_path}")

    return profiling_output


def generate_report(profiling: Dict[str, Any]) -> str:
    """Generate the markdown profiling report."""
    wall = profiling["wall_clock_seconds"]
    phase_total = profiling["total_phase_time_seconds"]
    overhead = profiling["overhead_seconds"]
    peak_mem = profiling["memory_peak_mb"]
    phases = profiling["phase_timings"]
    top_funcs = profiling.get("top_functions_cumulative", [])
    top_alloc = profiling.get("top_allocators_kb", [])
    summary = profiling.get("workflow_summary", {})

    lines = [
        "# Spectacular Workflow Profiling Report",
        "",
        "Performance bottleneck analysis for the spectacular analysis workflow.",
        "Generated with `cProfile` + `pyinstrument` + `tracemalloc`.",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Wall-clock time | {wall:.1f}s |",
        f"| Phase execution time | {phase_total:.1f}s |",
        f"| Orchestration overhead | {overhead:.1f}s |",
        f"| Peak memory | {peak_mem:.1f} MB |",
        f"| Phases completed | {summary.get('completed', 0)}/{summary.get('total', 0)} |",
        f"| Phases failed | {summary.get('failed', 0)} |",
        f"| Phases skipped | {summary.get('skipped', 0)} |",
        "",
    ]

    # Per-phase timing breakdown
    lines.extend([
        "## Per-Phase Wall-Clock Breakdown",
        "",
        "Phases sorted by duration (descending).",
        "",
        "| Phase | Capability | Duration (s) | % of Total | Status |",
        "|-------|-----------|-------------:|-----------:|--------|",
    ])

    for p in phases:
        pct = (p["duration_seconds"] / phase_total * 100) if phase_total > 0 else 0
        status_icon = "OK" if p["status"] == "completed" else p["status"]
        lines.append(
            f"| {p['phase']} | {p['capability']} | "
            f"{p['duration_seconds']:.2f} | {pct:.1f}% | {status_icon} |"
        )

    # Phase grouping analysis
    if phases:
        llm_phases = [p for p in phases if p["capability"] in (
            "fact_extraction", "nl_to_logic_translation", "neural_fallacy_detection",
            "hierarchical_fallacy_detection", "counter_argument_generation",
            "adversarial_debate", "narrative_synthesis", "formal_synthesis",
        )]
        formal_phases = [p for p in phases if p["capability"] in (
            "propositional_logic", "fol_reasoning", "modal_logic",
            "dung_extensions", "aspic_plus_reasoning",
        )]
        tms_phases = [p for p in phases if p["capability"] in (
            "belief_maintenance", "assumption_based_reasoning",
        )]
        other_phases = [p for p in phases if p not in llm_phases and p not in formal_phases and p not in tms_phases]

        def _phase_group_time(group):
            return sum(p["duration_seconds"] for p in group)

        llm_time = _phase_group_time(llm_phases)
        formal_time = _phase_group_time(formal_phases)
        tms_time = _phase_group_time(tms_phases)
        other_time = _phase_group_time(other_phases)

        lines.extend([
            "",
            "### Time by Category",
            "",
            "| Category | Phases | Total Time (s) | % of Phase Time |",
            "|----------|-------:|---------------:|----------------:|",
        ])

        for cat_name, cat_time, cat_count in [
            ("LLM-dependent", llm_time, len(llm_phases)),
            ("Formal logic (Tweety/JVM)", formal_time, len(formal_phases)),
            ("Truth maintenance (JTMS/ATMS)", tms_time, len(tms_phases)),
            ("Other (quality, governance, etc.)", other_time, len(other_phases)),
        ]:
            pct = (cat_time / phase_total * 100) if phase_total > 0 else 0
            lines.append(f"| {cat_name} | {cat_count} | {cat_time:.2f} | {pct:.1f}% |")

    # Top hot functions
    if top_funcs:
        lines.extend([
            "",
            "## Top 10 Hot Functions (by cumulative time)",
            "",
            "From cProfile output.",
            "",
            "| # | Function | Calls | Cumulative (s) | Total (s) |",
            "|--:|----------|------:|---------------:|----------:|",
        ])
        for i, f in enumerate(top_funcs[:10], 1):
            func_name = f["function"]
            if len(func_name) > 80:
                func_name = "..." + func_name[-77:]
            lines.append(
                f"| {i} | `{func_name}` | {f['calls']} | "
                f"{f['cumulative_time_s']:.3f} | {f['total_time_s']:.3f} |"
            )

    # Top memory allocators
    if top_alloc:
        lines.extend([
            "",
            "## Top 5 Memory Allocators",
            "",
            "From tracemalloc snapshot.",
            "",
            "| # | Location | Size (KB) | Allocations |",
            "|--:|----------|----------:|------------:|",
        ])
        for i, a in enumerate(top_alloc[:5], 1):
            loc = a["file"]
            if len(loc) > 80:
                loc = "..." + loc[-77:]
            lines.append(f"| {i} | `{loc}` | {a['size_kb']} | {a['count']} |")

    # Optimization recommendations
    lines.extend([
        "",
        "## Optimization Recommendations",
        "",
    ])

    # Auto-generate recommendations based on profiling data
    slowest = phases[0] if phases else None
    recommendations = []

    if slowest and slowest["duration_seconds"] > wall * 0.3:
        recommendations.append(
            f"1. **Parallelize or cache `{slowest['phase']}` ({slowest['duration_seconds']:.1f}s, "
            f"{slowest['duration_seconds']/wall*100:.0f}% of total).** "
            f"This single phase dominates the workflow. Consider caching its output "
            f"(the LLM cache layer from A.2 already helps) or running it concurrently "
            f"with other L1 phases."
        )

    if llm_time > phase_total * 0.6:
        recommendations.append(
            f"2. **LLM calls account for ~{llm_time/phase_total*100:.0f}% of phase time.** "
            f"Strategies: (a) batch multiple extraction prompts into one call, "
            f"(b) use smaller/faster models for extraction and quality evaluation, "
            f"(c) pre-warm the LLM cache with common patterns."
        )

    if formal_time > 5:
        recommendations.append(
            f"3. **Formal logic phases take {formal_time:.1f}s.** "
            f"The JVM/Tweety startup cost is amortized if JVM is already warm, "
            f"but cold starts are ~2-3s. Ensure JVM is initialized before the pipeline "
            f"(`jvm_setup.py` should be called during registry setup)."
        )

    if overhead > wall * 0.1:
        recommendations.append(
            f"4. **Orchestration overhead is {overhead:.1f}s ({overhead/wall*100:.0f}% of wall-clock).** "
            f"Consider reducing Python-level dispatch overhead by batching phase execution "
            f"within each DAG level (already parallel in theory, but async gathering may help)."
        )

    if peak_mem > 200:
        recommendations.append(
            f"5. **Peak memory usage is {peak_mem:.0f} MB.** "
            f"For large corpora, consider streaming analysis results to disk "
            f"rather than accumulating everything in the UnifiedAnalysisState."
        )

    if not recommendations:
        recommendations.append(
            "No critical bottlenecks detected. The workflow appears well-balanced."
        )

    for rec in recommendations:
        lines.append(rec)

    lines.extend([
        "",
        "## Methodology",
        "",
        "- **cProfile**: deterministic profiling of all function calls",
        "- **pyinstrument**: statistical sampling profiler (lower overhead, flame graph view)",
        "- **tracemalloc**: memory allocation tracking",
        "- **Phase timing**: instrumented WorkflowExecutor per-phase wall-clock",
        "- **Reproducibility**: run with `LLM_CACHE_MODE=replay` for deterministic cached responses",
        "",
        "View the pyinstrument flame graph: `open .profiling/spectacular_pyinstrument.html`",
        "View cProfile interactively: `snakeviz .profiling/spectacular_cprofile.prof`",
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Profile the spectacular workflow for bottleneck analysis (#400)"
    )
    parser.add_argument(
        "--text", type=str, default=None,
        help="Custom text to analyze (default: sample climate text)",
    )
    parser.add_argument(
        "--doc-index", type=int, default=None,
        help="Load doc from encrypted dataset by index (0=doc_A, 1=doc_B, etc.)",
    )
    parser.add_argument(
        "--max-chars", type=int, default=3000,
        help="Max chars of input text (default: 3000)",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable LLM caching for profiling",
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="Generate report from existing .profiling/spectacular_phase_timings.json",
    )
    args = parser.parse_args()

    if args.report_only:
        timings_path = PROFILING_DIR / "spectacular_phase_timings.json"
        if not timings_path.exists():
            logger.error(f"No existing timings file: {timings_path}")
            sys.exit(1)
        profiling = json.loads(timings_path.read_text(encoding="utf-8"))
    else:
        # Determine input text
        text = args.text
        if text is None and args.doc_index is not None:
            loaded = _load_encrypted_doc(args.doc_index, args.max_chars)
            if loaded:
                text = loaded
                logger.info(f"Loaded encrypted doc (opaque ID: doc_{chr(65 + args.doc_index)})")
            else:
                logger.warning("Could not load encrypted doc, using sample text")
                text = SAMPLE_TEXT[:args.max_chars]
        if text is None:
            text = SAMPLE_TEXT[:args.max_chars]

        logger.info(f"Input text: {len(text)} chars")
        logger.info(f"Output directory: {PROFILING_DIR}")

        # Run profiling
        profiling = asyncio.run(
            run_spectacular_with_profiling(text=text, use_cache=not args.no_cache)
        )

    # Generate and save report
    report = generate_report(profiling)
    report_path = project_root / "docs" / "reports" / "spectacular_profiling.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info(f"Report saved: {report_path}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("PROFILING SUMMARY")
    print("=" * 60)
    print(f"Wall-clock: {profiling['wall_clock_seconds']:.1f}s")
    print(f"Peak memory: {profiling['memory_peak_mb']:.1f} MB")
    print(f"Phases: {profiling.get('workflow_summary', {}).get('completed', '?')}/"
          f"{profiling.get('workflow_summary', {}).get('total', '?')} completed")
    print()
    print("Top 5 phases by duration:")
    for p in profiling["phase_timings"][:5]:
        print(f"  {p['phase']:<25s} {p['duration_seconds']:>6.2f}s  ({p['capability']})")
    print()
    print(f"Full report: {report_path}")
    print(f"cProfile:    {PROFILING_DIR / 'spectacular_cprofile.prof'}")
    print(f"Flame graph: {PROFILING_DIR / 'spectacular_pyinstrument.html'}")


if __name__ == "__main__":
    main()

"""
Capability evaluation framework: systematic marginal contribution analysis.

Evaluates which capability combinations produce the best argumentation analysis
results by running selective activation experiments against a corpus.

Usage:
    python -m argumentation_analysis.evaluation.capability_eval \
        --corpus argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json \
        --output argumentation_analysis/evaluation/results/capability_eval \
        --configs baseline quality fallacy counter debate full \
        --max-docs 5 \
        --judge-model default

Architecture:
    - FilteredRegistry: wraps CapabilityRegistry, limits active capabilities
    - CapabilityConfig: named set of active capabilities
    - PRESET_CONFIGS: predefined experimental configurations (issue #95 matrix)
    - run_capability_eval(): runs one config × one document → JudgeScore
    - compute_marginal_scores(): score(with X) - score(without X)
    - main(): CLI entry point
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("evaluation.capability_eval")

# ---------------------------------------------------------------------------
# Capability configuration matrix (from issue #95)
# ---------------------------------------------------------------------------


@dataclass
class CapabilityConfig:
    """Named set of capabilities to activate for one experimental condition."""

    name: str
    capabilities: List[str]
    description: str = ""

    def __post_init__(self):
        # Normalize to set for deduplication, then back to sorted list
        self.capabilities = sorted(set(self.capabilities))


# Preset configurations matching the issue #95 experimental matrix
PRESET_CONFIGS: Dict[str, CapabilityConfig] = {
    "baseline": CapabilityConfig(
        name="baseline",
        capabilities=["fact_extraction"],
        description="Baseline: ExtractAgent only",
    ),
    "quality": CapabilityConfig(
        name="quality",
        capabilities=["fact_extraction", "argument_quality"],
        description="Extract + quality scoring",
    ),
    "fallacy": CapabilityConfig(
        name="fallacy",
        capabilities=["fact_extraction", "fallacy_detection"],
        description="Extract + fallacy detection",
    ),
    "counter": CapabilityConfig(
        name="counter",
        capabilities=["fact_extraction", "counter_argument"],
        description="Extract + counter-argument generation",
    ),
    "debate": CapabilityConfig(
        name="debate",
        capabilities=["fact_extraction", "adversarial_debate", "governance_simulation"],
        description="Extract + debate + governance",
    ),
    "logic": CapabilityConfig(
        name="logic",
        capabilities=["fact_extraction", "aspic_plus_reasoning", "ranking_semantics"],
        description="Extract + ASPIC+ formal logic + ranking",
    ),
    "quality_fallacy": CapabilityConfig(
        name="quality_fallacy",
        capabilities=["fact_extraction", "argument_quality", "fallacy_detection"],
        description="Extract + quality + fallacy (synergy test)",
    ),
    "debate_governance": CapabilityConfig(
        name="debate_governance",
        capabilities=[
            "fact_extraction",
            "adversarial_debate",
            "governance_simulation",
            "argument_quality",
        ],
        description="Full debate stack with quality baseline",
    ),
    "full": CapabilityConfig(
        name="full",
        capabilities=[
            "fact_extraction",
            "argument_quality",
            "fallacy_detection",
            "counter_argument",
            "adversarial_debate",
            "governance_simulation",
            "aspic_plus_reasoning",
            "ranking_semantics",
            "dialogue_protocols",
            "epistemic_argumentation",
            "aba_reasoning",
            "social_argumentation",
        ],
        description="All available capabilities",
    ),
}

# The eval workflow: all phases optional — selective registry controls which run
EVAL_WORKFLOW_PHASES = [
    # (phase_name, capability, depends_on)
    ("extract", "fact_extraction", []),
    ("quality", "argument_quality", []),
    ("fallacy", "fallacy_detection", []),
    ("counter", "counter_argument", []),
    ("debate", "adversarial_debate", []),
    ("governance", "governance_simulation", []),
    ("formalization", "aspic_plus_reasoning", []),
    ("ranking", "ranking_semantics", []),
    ("dialogue", "dialogue_protocols", []),
    ("epistemic", "epistemic_argumentation", []),
    ("aba", "aba_reasoning", []),
    ("social", "social_argumentation", []),
]


# ---------------------------------------------------------------------------
# FilteredRegistry
# ---------------------------------------------------------------------------


class FilteredRegistry:
    """
    Wraps a CapabilityRegistry and limits which capabilities are visible.

    The WorkflowExecutor calls find_for_capability(cap) to resolve providers.
    This wrapper returns an empty list for capabilities not in the allowlist,
    making those workflow phases skip/fail gracefully.
    """

    def __init__(self, registry: Any, allowed_capabilities: Set[str]):
        self._registry = registry
        self._allowed = allowed_capabilities

    def find_for_capability(self, capability: str) -> List[Any]:
        if capability not in self._allowed:
            return []
        return self._registry.find_for_capability(capability)

    # Delegate everything else to the underlying registry
    def __getattr__(self, name: str) -> Any:
        return getattr(self._registry, name)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class EvalCell:
    """Result of one (config, document) evaluation cell."""

    config_name: str
    capabilities_active: List[str]
    document_name: str
    document_index: int
    phases_run: int
    phases_skipped: int
    phases_failed: int
    # Judge scores (0 if judge not run or failed)
    completeness: float = 0.0
    accuracy: float = 0.0
    depth: float = 0.0
    coherence: float = 0.0
    actionability: float = 0.0
    overall: float = 0.0
    reasoning: str = ""
    judge_error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def composite_score(self) -> float:
        return (
            self.overall * 0.40
            + self.depth * 0.20
            + self.completeness * 0.20
            + self.accuracy * 0.10
            + self.coherence * 0.05
            + self.actionability * 0.05
        )


@dataclass
class MarginalScore:
    """Marginal contribution of one capability across all documents."""

    capability: str
    avg_score_with: float  # avg composite when this cap is in the config
    avg_score_without: float  # avg composite when this cap is NOT in the config
    marginal_contribution: float  # score_with - score_without
    n_with: int
    n_without: int


@dataclass
class SynergyScore:
    """Synergy between two capabilities: score(A+B) - score(A) - score(B) + baseline."""

    cap_a: str
    cap_b: str
    synergy: float  # positive = super-additive, negative = anti-pattern


@dataclass
class CapabilityEvalReport:
    """Aggregated report for the full capability evaluation run."""

    timestamp: str = ""
    configs_evaluated: List[str] = field(default_factory=list)
    num_documents: int = 0
    total_cells: int = 0
    # Per-config aggregates
    config_scores: List[Dict[str, Any]] = field(default_factory=list)
    # Marginal contribution per capability
    marginal_scores: List[Dict[str, Any]] = field(default_factory=list)
    # Top configs by composite score
    best_config: Optional[str] = None
    best_composite: float = 0.0
    # Synergy analysis
    synergies: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            if key not in os.environ:
                os.environ[key] = val


def _build_eval_workflow():
    """Build the maximum-coverage optional workflow for capability evaluation."""
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    builder = WorkflowBuilder("capability_eval")
    for phase_name, capability, depends_on in EVAL_WORKFLOW_PHASES:
        builder.add_phase(
            name=phase_name,
            capability=capability,
            optional=True,  # Skipped gracefully when provider absent
            depends_on=depends_on,
        )
    return builder.build()


async def run_single_cell(
    config: CapabilityConfig,
    document_text: str,
    document_name: str,
    document_index: int,
    full_registry: Any,
    judge: Optional[Any],
    workflow: Any,
    executor: Any,
) -> EvalCell:
    """
    Run one (config, document) cell.

    Args:
        config: The capability configuration to activate.
        document_text: Raw text to analyze.
        document_name: Document identifier.
        document_index: 0-based index.
        full_registry: The fully-populated CapabilityRegistry.
        judge: LLMJudge instance (None → skip quality scoring).
        workflow: WorkflowDefinition (the eval workflow).
        executor: WorkflowExecutor instance.

    Returns:
        EvalCell with phase counts and judge scores.
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    start = time.time()

    # Wrap the registry to limit active capabilities
    filtered_reg = FilteredRegistry(full_registry, set(config.capabilities))
    executor._registry = filtered_reg

    state = UnifiedAnalysisState(initial_text=document_text)

    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        results = await executor.execute(
            workflow, document_text, state=state, state_writers=CAPABILITY_STATE_WRITERS
        )
    except Exception as e:
        logger.error(
            f"Workflow execution failed for {config.name}/{document_name}: {e}"
        )
        results = {}

    phases_run = sum(
        1
        for r in results.values()
        if hasattr(r, "status") and r.status.value == "completed"
    )
    phases_skipped = sum(
        1
        for r in results.values()
        if hasattr(r, "status") and r.status.value == "skipped"
    )
    phases_failed = sum(
        1
        for r in results.values()
        if hasattr(r, "status") and r.status.value == "failed"
    )

    duration = time.time() - start

    cell = EvalCell(
        config_name=config.name,
        capabilities_active=list(config.capabilities),
        document_name=document_name,
        document_index=document_index,
        phases_run=phases_run,
        phases_skipped=phases_skipped,
        phases_failed=phases_failed,
        duration_seconds=duration,
    )

    # Judge evaluation (requires API key)
    if judge is not None:
        try:
            snapshot = (
                state.get_state_snapshot()
                if hasattr(state, "get_state_snapshot")
                else {}
            )
            score = await judge.evaluate(
                input_text=document_text,
                workflow_name=config.name,
                analysis_results=snapshot,
            )
            cell.completeness = score.completeness
            cell.accuracy = score.accuracy
            cell.depth = score.depth
            cell.coherence = score.coherence
            cell.actionability = score.actionability
            cell.overall = score.overall
            cell.reasoning = score.reasoning
        except Exception as je:
            logger.warning(f"Judge failed for {config.name}/{document_name}: {je}")
            cell.judge_error = str(je)

    logger.info(
        f"  [{config.name}] {document_name}: "
        f"ran={phases_run}, skip={phases_skipped}, fail={phases_failed}, "
        f"composite={cell.composite_score:.2f} ({duration:.1f}s)"
    )
    return cell


def compute_marginal_scores(cells: List[EvalCell]) -> List[MarginalScore]:
    """
    For each capability, compute the marginal score: avg(with) - avg(without).

    A cell "has" a capability if it appears in `capabilities_active`.
    """
    all_caps: Set[str] = set()
    for cell in cells:
        all_caps.update(cell.capabilities_active)

    marginals = []
    for cap in sorted(all_caps):
        with_scores = [c.composite_score for c in cells if cap in c.capabilities_active]
        without_scores = [
            c.composite_score for c in cells if cap not in c.capabilities_active
        ]

        avg_with = sum(with_scores) / len(with_scores) if with_scores else 0.0
        avg_without = (
            sum(without_scores) / len(without_scores) if without_scores else 0.0
        )

        marginals.append(
            MarginalScore(
                capability=cap,
                avg_score_with=avg_with,
                avg_score_without=avg_without,
                marginal_contribution=avg_with - avg_without,
                n_with=len(with_scores),
                n_without=len(without_scores),
            )
        )

    # Sort by marginal contribution descending
    marginals.sort(key=lambda m: m.marginal_contribution, reverse=True)
    return marginals


def compute_synergies(cells: List[EvalCell]) -> List[SynergyScore]:
    """
    Compute pairwise synergy: score(A+B) - score(A) - score(B) + baseline.

    Uses the baseline score (no extra capabilities) as the reference.
    Positive synergy = super-additive, negative = anti-pattern.
    """
    # Group cells by config
    config_scores: Dict[str, List[float]] = {}
    for cell in cells:
        key = tuple(sorted(cell.capabilities_active))
        config_scores.setdefault(str(key), []).append(cell.composite_score)

    def avg_for_caps(caps: Set[str]) -> Optional[float]:
        key = str(tuple(sorted(caps)))
        if key in config_scores:
            scores = config_scores[key]
            return sum(scores) / len(scores)
        return None

    # Find baseline (smallest config)
    baseline_cells = [
        c
        for c in cells
        if len(c.capabilities_active) == min(len(x.capabilities_active) for x in cells)
    ]
    baseline = sum(c.composite_score for c in baseline_cells) / max(
        len(baseline_cells), 1
    )

    # Collect all unique capabilities across configs
    all_caps: Set[str] = set()
    for cell in cells:
        all_caps.update(cell.capabilities_active)

    synergies = []
    caps_list = sorted(all_caps)
    for i, cap_a in enumerate(caps_list):
        for cap_b in caps_list[i + 1 :]:
            score_ab = avg_for_caps({cap_a, cap_b})
            score_a = avg_for_caps({cap_a})
            score_b = avg_for_caps({cap_b})
            if score_ab is not None and score_a is not None and score_b is not None:
                synergy_val = score_ab - score_a - score_b + baseline
                synergies.append(
                    SynergyScore(
                        cap_a=cap_a,
                        cap_b=cap_b,
                        synergy=synergy_val,
                    )
                )

    synergies.sort(key=lambda s: abs(s.synergy), reverse=True)
    return synergies


def build_report(
    cells: List[EvalCell],
    marginals: List[MarginalScore],
    synergies: List[SynergyScore],
) -> CapabilityEvalReport:
    """Build the aggregated evaluation report."""
    from collections import defaultdict

    configs_seen = list(
        dict.fromkeys(c.config_name for c in cells)
    )  # order-preserving unique
    docs_seen = set(c.document_name for c in cells)

    # Per-config aggregates
    config_cells: Dict[str, List[EvalCell]] = defaultdict(list)
    for cell in cells:
        config_cells[cell.config_name].append(cell)

    config_scores = []
    for cfg_name in configs_seen:
        cfg_cells = config_cells[cfg_name]
        n = len(cfg_cells)
        avg_composite = sum(c.composite_score for c in cfg_cells) / n
        avg_phases_run = sum(c.phases_run for c in cfg_cells) / n
        config_scores.append(
            {
                "config_name": cfg_name,
                "capabilities": cfg_cells[0].capabilities_active if cfg_cells else [],
                "n_docs": n,
                "avg_composite": round(avg_composite, 3),
                "avg_overall": round(sum(c.overall for c in cfg_cells) / n, 3),
                "avg_depth": round(sum(c.depth for c in cfg_cells) / n, 3),
                "avg_completeness": round(
                    sum(c.completeness for c in cfg_cells) / n, 3
                ),
                "avg_phases_run": round(avg_phases_run, 1),
            }
        )

    # Sort by composite
    config_scores.sort(key=lambda x: x["avg_composite"], reverse=True)
    best = config_scores[0] if config_scores else None

    report = CapabilityEvalReport(
        configs_evaluated=configs_seen,
        num_documents=len(docs_seen),
        total_cells=len(cells),
        config_scores=config_scores,
        marginal_scores=[asdict(m) for m in marginals],
        best_config=best["config_name"] if best else None,
        best_composite=best["avg_composite"] if best else 0.0,
        synergies=[asdict(s) for s in synergies[:20]],  # top 20 pairs
    )
    return report


def write_cells_jsonl(cells: List[EvalCell], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for cell in cells:
            f.write(json.dumps(asdict(cell), ensure_ascii=False) + "\n")
    logger.info(f"Wrote {len(cells)} cells to {output_path}")


def write_report(report: CapabilityEvalReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = output_dir / "capability_eval_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    logger.info(f"Report JSON: {json_path}")

    # Markdown
    md_path = output_dir / "capability_eval_report.md"
    lines = [
        "# Capability Evaluation Report",
        f"\n**Generated:** {report.timestamp}",
        f"**Documents evaluated:** {report.num_documents}",
        f"**Total cells:** {report.total_cells}",
        "",
        "## Configuration Rankings",
        "",
        "| Config | Capabilities | N | Composite | Overall | Depth | Completeness | Avg phases run |",
        "|--------|--------------|---|-----------|---------|-------|--------------|----------------|",
    ]
    for cs in report.config_scores:
        caps_short = ", ".join(cs["capabilities"][:3])
        if len(cs["capabilities"]) > 3:
            caps_short += f" (+{len(cs['capabilities'])-3})"
        lines.append(
            f"| **{cs['config_name']}** | {caps_short} | {cs['n_docs']} "
            f"| {cs['avg_composite']:.3f} | {cs['avg_overall']:.2f} "
            f"| {cs['avg_depth']:.2f} | {cs['avg_completeness']:.2f} "
            f"| {cs['avg_phases_run']:.1f} |"
        )

    if report.best_config:
        lines += [
            "",
            f"**Best configuration:** `{report.best_config}` (composite={report.best_composite:.3f})",
        ]

    lines += [
        "",
        "## Marginal Capability Contributions",
        "",
        "Marginal contribution = avg_score(configs with this cap) - avg_score(configs without).",
        "",
        "| Capability | Avg (with) | Avg (without) | Marginal | N with | N without |",
        "|------------|-----------|---------------|----------|--------|-----------|",
    ]
    for m in report.marginal_scores:
        sign = "+" if m["marginal_contribution"] >= 0 else ""
        lines.append(
            f"| {m['capability']} | {m['avg_score_with']:.3f} | {m['avg_score_without']:.3f} "
            f"| {sign}{m['marginal_contribution']:.3f} | {m['n_with']} | {m['n_without']} |"
        )

    if report.synergies:
        lines += [
            "",
            "## Top Pairwise Synergies",
            "",
            "Synergy = score(A+B) - score(A) - score(B) + baseline. Positive = super-additive.",
            "",
            "| Cap A | Cap B | Synergy |",
            "|-------|-------|---------|",
        ]
        for s in report.synergies[:10]:
            sign = "+" if s["synergy"] >= 0 else ""
            lines.append(f"| {s['cap_a']} | {s['cap_b']} | {sign}{s['synergy']:.3f} |")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Report Markdown: {md_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main_async(args: argparse.Namespace) -> int:
    _load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Load corpus
    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        logger.error(f"Corpus not found: {corpus_path}")
        return 1

    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)
    documents = corpus.get("documents", [])
    if args.max_docs:
        documents = documents[: args.max_docs]
    logger.info(f"Loaded {len(documents)} documents from {corpus_path}")

    # Resolve configs
    config_names = [c.strip() for c in args.configs.split(",")]
    configs = []
    for name in config_names:
        if name in PRESET_CONFIGS:
            configs.append(PRESET_CONFIGS[name])
        else:
            logger.warning(f"Unknown config '{name}', skipping")
    if not configs:
        logger.error(f"No valid configs. Available: {list(PRESET_CONFIGS.keys())}")
        return 1
    logger.info(f"Evaluating {len(configs)} configs: {[c.name for c in configs]}")

    # Set up registry and executor
    from argumentation_analysis.orchestration.unified_pipeline import setup_registry
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor

    logger.info("Setting up capability registry...")
    full_registry = setup_registry()
    executor = WorkflowExecutor(full_registry)
    workflow = _build_eval_workflow()

    # Optionally create judge
    judge = None
    if not args.skip_judge:
        from argumentation_analysis.evaluation.judge import LLMJudge

        judge = LLMJudge(model_name=args.judge_model)
        logger.info(f"LLM judge: {args.judge_model}")
    else:
        logger.info("Judge scoring disabled (--skip-judge)")

    # Run evaluation matrix
    cells: List[EvalCell] = []
    total = len(configs) * len(documents)
    logger.info(
        f"Running {total} cells ({len(configs)} configs × {len(documents)} docs)..."
    )

    for doc_idx, doc in enumerate(documents):
        doc_text = doc.get("text", "")
        doc_name = doc.get("id", f"doc_{doc_idx}")

        if not doc_text:
            logger.warning(f"Empty text for {doc_name}, skipping")
            continue

        for config in configs:
            cell = await run_single_cell(
                config=config,
                document_text=doc_text,
                document_name=doc_name,
                document_index=doc_idx,
                full_registry=full_registry,
                judge=judge,
                workflow=workflow,
                executor=executor,
            )
            cells.append(cell)

    # Write results
    output_dir = Path(args.output)
    cells_path = output_dir / "capability_eval_cells.jsonl"
    write_cells_jsonl(cells, cells_path)

    # Compute analysis
    marginals = compute_marginal_scores(cells)
    synergies = compute_synergies(cells)
    report = build_report(cells, marginals, synergies)
    write_report(report, output_dir)

    # Print summary
    print(f"\n=== Capability Evaluation Summary ===\n")
    print(
        f"{'Config':<22} {'N':>3}  {'Composite':>9}  {'Overall':>7}  {'Depth':>5}  {'Phases':>6}"
    )
    print("-" * 60)
    for cs in report.config_scores:
        print(
            f"{cs['config_name']:<22} {cs['n_docs']:>3}  "
            f"{cs['avg_composite']:>9.3f}  {cs['avg_overall']:>7.2f}  "
            f"{cs['avg_depth']:>5.2f}  {cs['avg_phases_run']:>6.1f}"
        )
    if report.best_config:
        print(f"\nBest: {report.best_config} (composite={report.best_composite:.3f})")

    if marginals:
        print(f"\n=== Top 5 Marginal Contributions ===\n")
        for m in marginals[:5]:
            sign = "+" if m.marginal_contribution >= 0 else ""
            print(f"  {m.capability:<35} {sign}{m.marginal_contribution:.3f}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate capability combinations for argumentation analysis quality."
    )
    parser.add_argument(
        "--corpus",
        default="argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json",
        help="Path to corpus JSON file",
    )
    parser.add_argument(
        "--output",
        default="argumentation_analysis/evaluation/results/capability_eval",
        help="Output directory for results",
    )
    parser.add_argument(
        "--configs",
        default="baseline,quality,fallacy,counter,debate,logic,full",
        help=f"Comma-separated config names. Available: {', '.join(PRESET_CONFIGS.keys())}",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="Max documents to evaluate (0 = all)",
    )
    parser.add_argument(
        "--judge-model",
        default="default",
        help="Judge model name (default = OPENAI_CHAT_MODEL_ID env var)",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip LLM judge scoring (structural evaluation only)",
    )
    args = parser.parse_args()

    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()

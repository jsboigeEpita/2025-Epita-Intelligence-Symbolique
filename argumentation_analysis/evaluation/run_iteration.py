"""
Incremental validation runner for Epic #138.

Runs a custom workflow with a subset of capabilities on the encrypted dataset,
captures state snapshots, and computes delta vs previous iteration.

Usage:
    python -m argumentation_analysis.evaluation.run_iteration \
        --iter 1 \
        --capabilities fact_extraction \
        --max-docs 3 --max-text 5000 \
        --output argumentation_analysis/evaluation/results/incremental_validation
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("evaluation.run_iteration")

# Iteration definitions: iter_num -> list of capabilities
ITERATION_CAPABILITIES = {
    1: ["fact_extraction"],
    2: ["fact_extraction", "hierarchical_fallacy_detection"],
    3: ["fact_extraction", "hierarchical_fallacy_detection", "argument_quality"],
    4: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
    ],
    5: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
    ],
    6: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
        "governance_simulation",
    ],
    7: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
        "governance_simulation",
        "propositional_logic",
        "fol_reasoning",
    ],
    8: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
        "governance_simulation",
        "propositional_logic",
        "fol_reasoning",
        "aspic_plus_reasoning",
    ],
    9: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
        "governance_simulation",
        "propositional_logic",
        "fol_reasoning",
        "aspic_plus_reasoning",
        "ranking_semantics",
    ],
    10: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
        "governance_simulation",
        "propositional_logic",
        "fol_reasoning",
        "aspic_plus_reasoning",
        "ranking_semantics",
        "dialogue_protocols",
    ],
    11: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
        "governance_simulation",
        "propositional_logic",
        "fol_reasoning",
        "aspic_plus_reasoning",
        "ranking_semantics",
        "dialogue_protocols",
        "belief_revision",
        "belief_maintenance",
    ],
    12: [
        "fact_extraction",
        "hierarchical_fallacy_detection",
        "argument_quality",
        "counter_argument_generation",
        "adversarial_debate",
        "governance_simulation",
        "propositional_logic",
        "fol_reasoning",
        "aspic_plus_reasoning",
        "ranking_semantics",
        "dialogue_protocols",
        "belief_revision",
        "belief_maintenance",
        "epistemic_argumentation",
        "social_argumentation",
    ],
    13: None,  # All available — no filtering
}


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
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            if key not in os.environ:
                os.environ[key] = val


def _build_iteration_workflow(iter_num: int, capabilities: List[str]):
    """Build a workflow with phases for the given capabilities."""
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    builder = WorkflowBuilder(f"iter{iter_num}_validation")

    # Phase ordering: extract first, then informal, then formal
    phase_order = [
        ("extract", "fact_extraction", []),
        ("hierarchical_fallacy", "hierarchical_fallacy_detection", ["extract"]),
        ("quality", "argument_quality", ["extract"]),
        ("counter", "counter_argument_generation", ["quality"]),
        ("debate", "adversarial_debate", ["counter"]),
        ("governance", "governance_simulation", ["quality"]),
        ("propositional", "propositional_logic", ["extract"]),
        ("fol", "fol_reasoning", ["extract"]),
        ("aspic", "aspic_plus_reasoning", ["extract"]),
        ("ranking", "ranking_semantics", ["extract"]),
        ("dialogue", "dialogue_protocols", ["extract"]),
        ("belief_rev", "belief_revision", ["extract"]),
        ("belief_jtms", "belief_maintenance", ["extract"]),
        ("epistemic", "epistemic_argumentation", ["extract"]),
        ("social", "social_argumentation", ["extract"]),
    ]

    for phase_name, capability, deps in phase_order:
        if capability in capabilities:
            valid_deps = [
                d
                for d in deps
                if any(
                    c == p[1] for p in phase_order if p[0] == d and p[1] in capabilities
                )
            ]
            builder.add_phase(
                name=phase_name,
                capability=capability,
                depends_on=valid_deps if valid_deps else [],
                optional=(phase_name != "extract"),
            )

    return builder.build()


def _count_state_richness(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze state snapshot richness."""
    richness = {}
    for key, val in snapshot.items():
        if key == "raw_text":
            richness[key] = f"{len(val)} chars" if isinstance(val, str) else "empty"
        elif isinstance(val, dict):
            richness[key] = len(val)
        elif isinstance(val, list):
            richness[key] = len(val)
        elif val and val not in [None, "", 0, False]:
            richness[key] = 1
        else:
            richness[key] = 0
    return richness


def _compute_delta(
    current: Dict[str, Any], previous: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compute delta between current and previous iteration richness."""
    if previous is None:
        return {"note": "baseline — no previous iteration"}
    delta = {}
    all_keys = set(list(current.keys()) + list(previous.keys()))
    for key in sorted(all_keys):
        curr = current.get(key, 0)
        prev = previous.get(key, 0)
        if isinstance(curr, str) or isinstance(prev, str):
            continue
        if curr != prev:
            delta[key] = {"prev": prev, "curr": curr, "delta": curr - prev}
    return delta


async def run_iteration(
    iter_num: int,
    max_docs: int = 3,
    max_text: int = 5000,
    output_dir: str = "argumentation_analysis/evaluation/results/incremental_validation",
) -> Dict[str, Any]:
    """Run one iteration of the incremental validation."""
    _load_dotenv()

    from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner
    from argumentation_analysis.evaluation.model_registry import ModelRegistry
    from argumentation_analysis.orchestration.unified_pipeline import (
        setup_registry,
        CAPABILITY_STATE_WRITERS,
    )
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    # Determine capabilities
    if iter_num in ITERATION_CAPABILITIES:
        capabilities = ITERATION_CAPABILITIES[iter_num]
    else:
        capabilities = None  # all

    if capabilities is not None:
        logger.info(
            f"Iter {iter_num}: {len(capabilities)} capabilities: {capabilities}"
        )
    else:
        logger.info(f"Iter {iter_num}: ALL capabilities (no filtering)")

    # Load encrypted dataset
    registry_model = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry_model)
    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE", "")
    docs = runner.load_dataset_encrypted(
        "argumentation_analysis/data/extract_sources.json.gz.enc", passphrase
    )
    if max_docs > 0:
        docs = docs[:max_docs]
    logger.info(f"Loaded {len(docs)} documents")

    # Setup pipeline
    full_registry = setup_registry()
    executor = WorkflowExecutor(full_registry)

    if capabilities is not None:
        workflow = _build_iteration_workflow(iter_num, capabilities)
        # Filter registry
        from argumentation_analysis.evaluation.capability_eval import FilteredRegistry

        filtered = FilteredRegistry(full_registry, set(capabilities))
        executor._registry = filtered
    else:
        # Use all — build a maximal workflow
        workflow = _build_iteration_workflow(
            iter_num, list(CAPABILITY_STATE_WRITERS.keys())
        )

    # Run on each document
    results = []
    for doc_idx, doc in enumerate(docs):
        text = doc.get("text", "")[:max_text]
        doc_id = doc.get("id", f"doc_{doc_idx}")
        if not text:
            continue

        logger.info(f"  [{doc_idx}] {doc_id} ({len(text)} chars)...")
        state = UnifiedAnalysisState(initial_text=text)
        start = time.time()

        try:
            phase_results = await executor.execute(
                workflow, text, state=state, state_writers=CAPABILITY_STATE_WRITERS
            )
            duration = time.time() - start
            snapshot = state.get_state_snapshot()
            richness = _count_state_richness(snapshot)

            phases_completed = sum(
                1
                for r in phase_results.values()
                if hasattr(r, "status") and r.status.value == "completed"
            )
            phases_total = len(phase_results)

            result = {
                "iter": iter_num,
                "doc_id": doc_id,
                "doc_index": doc_idx,
                "duration_seconds": round(duration, 1),
                "phases_completed": phases_completed,
                "phases_total": phases_total,
                "richness": richness,
                "snapshot": snapshot,
                "timestamp": datetime.now().isoformat(),
            }
            results.append(result)

            # Summary line
            non_empty = sum(
                1 for v in richness.values() if v and v != 0 and v != "empty"
            )
            logger.info(
                f"    → {phases_completed}/{phases_total} phases, {non_empty} non-empty fields, {duration:.1f}s"
            )

        except Exception as e:
            duration = time.time() - start
            logger.error(f"    → FAILED: {e} ({duration:.1f}s)")
            results.append(
                {
                    "iter": iter_num,
                    "doc_id": doc_id,
                    "doc_index": doc_idx,
                    "duration_seconds": round(duration, 1),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

    # Load previous iteration results for delta
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    prev_path = out_path / f"iter{iter_num - 1}_results.jsonl"
    prev_richness = None
    if prev_path.exists():
        with open(prev_path) as f:
            prev_lines = [json.loads(l) for l in f if l.strip()]
            if prev_lines:
                prev_richness = prev_lines[0].get("richness")

    # Compute delta
    if results and "richness" in results[0]:
        delta = _compute_delta(results[0]["richness"], prev_richness)
    else:
        delta = {"error": "no results"}

    # Write results
    results_path = out_path / f"iter{iter_num}_results.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for r in results:
            # Remove full snapshot from JSONL (too large), keep richness
            r_out = {k: v for k, v in r.items() if k != "snapshot"}
            f.write(json.dumps(r_out, ensure_ascii=False, default=str) + "\n")
    logger.info(f"Results: {results_path}")

    # Write summary
    summary = {
        "iter": iter_num,
        "capabilities": capabilities or "ALL",
        "n_docs": len(results),
        "n_success": sum(1 for r in results if "error" not in r),
        "avg_duration": round(
            sum(r.get("duration_seconds", 0) for r in results) / max(len(results), 1), 1
        ),
        "avg_non_empty_fields": round(
            sum(
                sum(
                    1
                    for v in r.get("richness", {}).values()
                    if v and v != 0 and v != "empty"
                )
                for r in results
                if "richness" in r
            )
            / max(sum(1 for r in results if "richness" in r), 1),
            1,
        ),
        "delta_vs_previous": delta,
        "timestamp": datetime.now().isoformat(),
    }
    summary_path = out_path / f"iter{iter_num}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Summary: {summary_path}")

    # Print
    print(f"\n=== Iteration {iter_num} Summary ===")
    print(f"Capabilities: {len(capabilities) if capabilities else 'ALL'}")
    print(f"Documents: {summary['n_docs']} ({summary['n_success']} success)")
    print(f"Avg duration: {summary['avg_duration']}s")
    print(f"Avg non-empty fields: {summary['avg_non_empty_fields']}")
    if delta and "note" not in delta and "error" not in delta:
        print(f"\nDelta vs iter-{iter_num - 1}:")
        for k, v in delta.items():
            print(
                f"  {k}: {v['prev']} → {v['curr']} ({'+' if v['delta'] > 0 else ''}{v['delta']})"
            )

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run incremental validation iteration")
    parser.add_argument(
        "--iter", type=int, required=True, help="Iteration number (1-13)"
    )
    parser.add_argument(
        "--max-docs", type=int, default=3, help="Max documents (default: 3)"
    )
    parser.add_argument(
        "--max-text", type=int, default=5000, help="Max text chars per doc"
    )
    parser.add_argument(
        "--output",
        default="argumentation_analysis/evaluation/results/incremental_validation",
        help="Output directory",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    asyncio.run(run_iteration(args.iter, args.max_docs, args.max_text, args.output))


if __name__ == "__main__":
    main()

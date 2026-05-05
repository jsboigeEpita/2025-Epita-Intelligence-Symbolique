"""
Agentic conversation evaluation for Issue #97.

Compares two execution modes on the same documents:
1. Single-pass pipeline (standard workflow, 15 capabilities, 1 round)
2. Multi-round conversational pipeline (same workflow, 3 rounds of refinement)

The hypothesis: iterative multi-round execution should improve analysis quality
because each round can build on and refine the previous round's outputs.

Usage:
    python -m argumentation_analysis.evaluation.run_agentic_eval \
        --max-docs 3 --max-text 5000 --rounds 3
"""

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("evaluation.agentic_eval")


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


def _build_full_workflow():
    """Build a workflow with all 15 capabilities."""
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    builder = WorkflowBuilder("agentic_eval")

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
        builder.add_phase(
            name=phase_name,
            capability=capability,
            depends_on=deps,
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


async def run_single_pass(
    doc_text: str,
    doc_id: str,
    workflow,
    executor,
    state_writers: Dict,
) -> Dict[str, Any]:
    """Run standard single-pass pipeline (baseline)."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState(initial_text=doc_text)
    start = time.time()

    phase_results = await executor.execute(
        workflow, doc_text, state=state, state_writers=state_writers
    )

    duration = time.time() - start
    snapshot = state.get_state_snapshot()
    richness = _count_state_richness(snapshot)

    phases_completed = sum(
        1
        for r in phase_results.values()
        if hasattr(r, "status") and r.status.value == "completed"
    )

    non_empty = sum(1 for v in richness.values() if v and v != 0 and v != "empty")

    logger.info(
        f"  [single-pass] {doc_id}: {phases_completed}/{len(phase_results)} phases, "
        f"{non_empty} fields, {duration:.1f}s"
    )

    return {
        "mode": "single_pass",
        "doc_id": doc_id,
        "duration_seconds": round(duration, 1),
        "phases_completed": phases_completed,
        "phases_total": len(phase_results),
        "richness": richness,
        "snapshot": snapshot,
        "non_empty_fields": non_empty,
    }


async def run_multi_round(
    doc_text: str,
    doc_id: str,
    workflow,
    registry,
    state_writers: Dict,
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """Run multi-round conversational pipeline."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.conversational_executor import (
        ConversationalPipeline,
        WorkflowTurnStrategy,
    )
    from argumentation_analysis.orchestration.turn_protocol import ConversationConfig

    state = UnifiedAnalysisState(initial_text=doc_text)

    # Convergence: compare non-empty field counts between rounds
    def convergence_fn(prev, curr):
        # If both rounds produce same number of completed phases, consider converged
        prev_completed = sum(
            1
            for r in prev.phase_results.values()
            if hasattr(r, "status") and r.status.value == "completed"
        )
        curr_completed = sum(
            1
            for r in curr.phase_results.values()
            if hasattr(r, "status") and r.status.value == "completed"
        )
        return prev_completed == curr_completed and curr.confidence >= 0.7

    config = ConversationConfig(
        max_rounds=max_rounds,
        convergence_fn=convergence_fn,
        confidence_threshold=0.95,  # High threshold to encourage multiple rounds
    )

    strategy = WorkflowTurnStrategy(workflow, registry, state_writers=state_writers)
    pipeline = ConversationalPipeline(strategy, config=config)

    start = time.time()
    result = await pipeline.execute(doc_text, state=state)
    duration = time.time() - start

    snapshot = state.get_state_snapshot()
    richness = _count_state_richness(snapshot)
    non_empty = sum(1 for v in richness.values() if v and v != 0 and v != "empty")

    n_rounds = len(result.get("rounds", []))
    status = result.get("status", "unknown")

    logger.info(
        f"  [multi-round] {doc_id}: {n_rounds} rounds, status={status}, "
        f"{non_empty} fields, {duration:.1f}s"
    )

    # Collect per-round stats
    round_stats = []
    for r in result.get("rounds", []):
        tr = r.get("turn_result")
        if tr:
            completed = sum(
                1
                for pr in tr.phase_results.values()
                if hasattr(pr, "status") and pr.status.value == "completed"
            )
            round_stats.append(
                {
                    "round": tr.turn_number,
                    "phases_completed": completed,
                    "confidence": round(tr.confidence, 3),
                    "duration": round(tr.duration_seconds, 1),
                }
            )

    return {
        "mode": "multi_round",
        "doc_id": doc_id,
        "duration_seconds": round(duration, 1),
        "n_rounds": n_rounds,
        "status": status,
        "round_stats": round_stats,
        "richness": richness,
        "snapshot": snapshot,
        "non_empty_fields": non_empty,
    }


async def score_with_judge(
    input_text: str,
    workflow_name: str,
    snapshot: Dict[str, Any],
) -> Dict[str, float]:
    """Score a snapshot using LLM Judge."""
    from argumentation_analysis.evaluation.judge import LLMJudge

    judge = LLMJudge()
    score = await judge.evaluate(
        input_text=input_text,
        workflow_name=workflow_name,
        analysis_results=snapshot,
    )

    return {
        "completeness": score.completeness,
        "accuracy": score.accuracy,
        "depth": score.depth,
        "coherence": score.coherence,
        "actionability": score.actionability,
        "overall": score.overall,
        "composite": round(
            (
                score.completeness
                + score.accuracy
                + score.depth
                + score.coherence
                + score.actionability
            )
            / 5,
            2,
        ),
        "reasoning": score.reasoning,
    }


async def run_agentic_eval(
    max_docs: int = 3,
    max_text: int = 5000,
    max_rounds: int = 3,
    output_dir: str = "argumentation_analysis/evaluation/results/agentic_eval",
) -> Dict[str, Any]:
    """Run the full agentic conversation evaluation."""
    _load_dotenv()

    from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner
    from argumentation_analysis.evaluation.model_registry import ModelRegistry
    from argumentation_analysis.orchestration.unified_pipeline import (
        setup_registry,
        CAPABILITY_STATE_WRITERS,
    )
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor

    # Load dataset
    registry_model = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry_model)
    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE", "")
    docs = runner.load_dataset_encrypted(
        "argumentation_analysis/data/extract_sources.json.gz.enc", passphrase
    )
    if max_docs > 0:
        docs = docs[:max_docs]
    logger.info(f"Loaded {len(docs)} documents")

    # Setup
    full_registry = setup_registry()
    executor = WorkflowExecutor(full_registry)
    workflow = _build_full_workflow()

    all_results = []
    judge_comparisons = []

    for doc_idx, doc in enumerate(docs):
        text = doc.get("text", "")[:max_text]
        doc_id = doc.get("id", f"doc_{doc_idx}")
        if not text:
            continue

        logger.info(f"[{doc_idx}] Processing {doc_id} ({len(text)} chars)")

        # 1) Single-pass baseline
        try:
            single = await run_single_pass(
                text, doc_id, workflow, executor, CAPABILITY_STATE_WRITERS
            )
            all_results.append(single)
        except Exception as e:
            logger.error(f"  Single-pass failed: {e}")
            single = {"mode": "single_pass", "doc_id": doc_id, "error": str(e)}
            all_results.append(single)

        # 2) Multi-round conversational
        try:
            multi = await run_multi_round(
                text,
                doc_id,
                workflow,
                full_registry,
                CAPABILITY_STATE_WRITERS,
                max_rounds=max_rounds,
            )
            all_results.append(multi)
        except Exception as e:
            logger.error(f"  Multi-round failed: {e}")
            multi = {"mode": "multi_round", "doc_id": doc_id, "error": str(e)}
            all_results.append(multi)

        # 3) Score both with LLM Judge (if snapshots available)
        comparison = {"doc_id": doc_id}
        if "snapshot" in single:
            try:
                single_score = await score_with_judge(
                    text, "single_pass_pipeline", single["snapshot"]
                )
                comparison["single_pass"] = single_score
                logger.info(
                    f"  [judge] single-pass: composite={single_score['composite']}"
                )
            except Exception as e:
                logger.error(f"  Judge (single) failed: {e}")
                comparison["single_pass"] = {"error": str(e)}

        if "snapshot" in multi:
            try:
                multi_score = await score_with_judge(
                    text, f"multi_round_{max_rounds}r", multi["snapshot"]
                )
                comparison["multi_round"] = multi_score
                logger.info(
                    f"  [judge] multi-round: composite={multi_score['composite']}"
                )
            except Exception as e:
                logger.error(f"  Judge (multi) failed: {e}")
                comparison["multi_round"] = {"error": str(e)}

        judge_comparisons.append(comparison)

    # Write results
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Detailed results (with snapshots, for LLM Judge)
    snapshots_path = out_path / "agentic_snapshots.jsonl"
    with open(snapshots_path, "w", encoding="utf-8") as f:
        for r in all_results:
            if "snapshot" not in r:
                continue
            entry = {
                "workflow_name": f"{r['mode']}_agentic_eval",
                "model_name": "default",
                "document_name": r.get("doc_id", ""),
                "mode": r["mode"],
                "success": "error" not in r,
                "state_snapshot": r["snapshot"],
                "duration_seconds": r.get("duration_seconds", 0),
            }
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # Lightweight results (without snapshots)
    results_path = out_path / "agentic_results.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for r in all_results:
            r_out = {k: v for k, v in r.items() if k != "snapshot"}
            f.write(json.dumps(r_out, ensure_ascii=False, default=str) + "\n")

    # Judge comparison summary
    comparison_path = out_path / "agentic_judge_comparison.json"
    with open(comparison_path, "w", encoding="utf-8") as f:
        json.dump(judge_comparisons, f, indent=2, ensure_ascii=False, default=str)

    # Compute aggregate summary
    summary = _compute_summary(all_results, judge_comparisons, max_rounds)

    summary_path = out_path / "agentic_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Summary: {summary_path}")

    # Print summary
    _print_summary(summary)

    return summary


def _compute_summary(
    results: List[Dict],
    judge_comparisons: List[Dict],
    max_rounds: int,
) -> Dict[str, Any]:
    """Compute aggregate summary."""
    single_results = [
        r for r in results if r.get("mode") == "single_pass" and "error" not in r
    ]
    multi_results = [
        r for r in results if r.get("mode") == "multi_round" and "error" not in r
    ]

    def avg(values):
        return round(sum(values) / max(len(values), 1), 2)

    # Aggregate scores
    single_scores = [
        c.get("single_pass", {}) for c in judge_comparisons if "single_pass" in c
    ]
    multi_scores = [
        c.get("multi_round", {}) for c in judge_comparisons if "multi_round" in c
    ]

    single_composites = [s["composite"] for s in single_scores if "composite" in s]
    multi_composites = [s["composite"] for s in multi_scores if "composite" in s]

    return {
        "eval_type": "agentic_conversation",
        "max_rounds": max_rounds,
        "n_docs": len(single_results),
        "single_pass": {
            "avg_duration": avg([r["duration_seconds"] for r in single_results]),
            "avg_non_empty_fields": avg(
                [r["non_empty_fields"] for r in single_results]
            ),
            "avg_composite_score": (
                avg(single_composites) if single_composites else None
            ),
            "scores_by_dimension": _avg_dimension_scores(single_scores),
        },
        "multi_round": {
            "avg_duration": avg([r["duration_seconds"] for r in multi_results]),
            "avg_non_empty_fields": avg([r["non_empty_fields"] for r in multi_results]),
            "avg_rounds": avg([r["n_rounds"] for r in multi_results]),
            "statuses": [r.get("status", "?") for r in multi_results],
            "avg_composite_score": avg(multi_composites) if multi_composites else None,
            "scores_by_dimension": _avg_dimension_scores(multi_scores),
        },
        "delta": {
            "composite": (
                round(avg(multi_composites) - avg(single_composites), 2)
                if single_composites and multi_composites
                else None
            ),
            "duration_ratio": (
                round(
                    avg([r["duration_seconds"] for r in multi_results])
                    / max(avg([r["duration_seconds"] for r in single_results]), 1),
                    2,
                )
                if single_results and multi_results
                else None
            ),
        },
        "timestamp": datetime.now().isoformat(),
    }


def _avg_dimension_scores(scores: List[Dict]) -> Dict[str, float]:
    """Average scores by dimension."""
    dims = ["completeness", "accuracy", "depth", "coherence", "actionability"]
    result = {}
    for dim in dims:
        vals = [s[dim] for s in scores if dim in s and isinstance(s[dim], (int, float))]
        if vals:
            result[dim] = round(sum(vals) / len(vals), 2)
    return result


def _print_summary(summary: Dict[str, Any]):
    """Print summary to console."""
    print("\n" + "=" * 60)
    print("AGENTIC CONVERSATION EVALUATION")
    print("=" * 60)

    sp = summary.get("single_pass", {})
    mr = summary.get("multi_round", {})
    delta = summary.get("delta", {})

    print(f"\nDocuments: {summary.get('n_docs', 0)}")
    print(f"Max rounds: {summary.get('max_rounds', 0)}")

    print(f"\n{'Metric':<25} {'Single-pass':>12} {'Multi-round':>12} {'Delta':>8}")
    print("-" * 60)
    dr = delta.get("duration_ratio", "?")
    print(
        f"{'Duration (avg)':<25} {sp.get('avg_duration', '?'):>10}s {mr.get('avg_duration', '?'):>10}s {f'x{dr}':>8}"
    )
    print(
        f"{'Non-empty fields':<25} {sp.get('avg_non_empty_fields', '?'):>12} {mr.get('avg_non_empty_fields', '?'):>12}"
    )
    print(
        f"{'Composite score':<25} {sp.get('avg_composite_score', '?'):>12} {mr.get('avg_composite_score', '?'):>12} {delta.get('composite', '?'):>8}"
    )

    for dim in ["completeness", "accuracy", "depth", "coherence", "actionability"]:
        sp_val = sp.get("scores_by_dimension", {}).get(dim, "?")
        mr_val = mr.get("scores_by_dimension", {}).get(dim, "?")
        print(f"  {dim:<23} {sp_val:>12} {mr_val:>12}")

    print(f"\nMulti-round avg rounds: {mr.get('avg_rounds', '?')}")
    print(f"Statuses: {mr.get('statuses', [])}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Agentic conversation evaluation (#97)"
    )
    parser.add_argument("--max-docs", type=int, default=3, help="Max documents")
    parser.add_argument(
        "--max-text", type=int, default=5000, help="Max text chars per doc"
    )
    parser.add_argument("--rounds", type=int, default=3, help="Max conversation rounds")
    parser.add_argument(
        "--output",
        default="argumentation_analysis/evaluation/results/agentic_eval",
        help="Output directory",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )

    result = asyncio.run(
        run_agentic_eval(
            max_docs=args.max_docs,
            max_text=args.max_text,
            max_rounds=args.rounds,
            output_dir=args.output,
        )
    )

    print(f"\nResult: {json.dumps(result, indent=2, default=str)}")


if __name__ == "__main__":
    main()

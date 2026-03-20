"""
Baseline Capability Benchmark Runner

Exécute le corpus d'évaluation baseline sur les workflows light/standard/full
et génère un rapport de comparaison des capacités.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from argumentation_analysis.evaluation.model_registry import ModelRegistry
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner
from argumentation_analysis.evaluation.result_collector import ResultCollector
from argumentation_analysis.evaluation.judge import LLMJudge

logger = logging.getLogger("evaluation.baseline_benchmark")


async def run_baseline_benchmark(
    corpus_path: str,
    output_dir: str,
    workflows: List[str] = ("light", "standard"),
    max_docs: int = 0,
    skip_judge: bool = False,
):
    """
    Exécute le benchmark baseline sur le corpus spécifié.

    Args:
        corpus_path: Chemin vers le fichier JSON du corpus
        output_dir: Répertoire de sortie pour les résultats
        workflows: Liste des workflows à tester (défaut: light, standard)
        max_docs: Nombre max de documents à traiter (0 = tous)
        skip_judge: Si True, saute l'évaluation LLM judge
    """
    # Setup
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize components
    model_registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(model_registry)

    # Load corpus
    logger.info(f"Chargement du corpus depuis {corpus_path}")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus_data = json.load(f)

    documents = corpus_data.get("documents", [])
    if max_docs > 0:
        documents = documents[:max_docs]

    logger.info(f"Corpus chargé: {len(documents)} documents")

    # Prepare dataset for runner
    runner._dataset = documents

    # Result collector
    collector = ResultCollector(output_path)

    # Execute benchmark cells
    total_cells = len(workflows) * len(documents)
    completed = 0

    for workflow in workflows:
        logger.info(f"\n{'='*60}")
        logger.info(f"Workflow: {workflow}")
        logger.info(f"{'='*60}")

        for idx, doc in enumerate(documents):
            doc_id = doc.get("id", f"doc_{idx}")
            logger.info(f"  [{idx+1}/{len(documents)}] {doc_id}...")

            try:
                result = await runner.run_cell(
                    workflow_name=workflow,
                    model_name="default",
                    document_index=idx,
                    timeout=120.0,
                )
                collector.save(result)

                if result.success:
                    completed += 1
                    logger.info(f"    ✓ Success ({result.duration_seconds:.1f}s)")
                else:
                    logger.warning(f"    ✗ Failed: {result.error}")

            except Exception as e:
                logger.error(f"    ✗ Exception: {e}")

    # Generate summary
    logger.info(f"\n{'='*60}")
    logger.info("RÉSUMÉ DU BENCHMARK")
    logger.info(f"{'='*60}")

    summary = collector.generate_summary()
    logger.info(f"Total cellules: {total_cells}")
    logger.info(f"Succès: {completed} ({100*completed/total_cells:.1f}%)")
    logger.info(f"Échecs: {total_cells - completed}")

    for workflow in workflows:
        wf_results = collector.query(workflow_name=workflow)
        success_count = sum(1 for r in wf_results if r.get("success", False))
        logger.info(f"  {workflow}: {success_count}/{len(wf_results)} réussies")

    # Save summary
    summary_path = output_path / "benchmark_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"\nRapport sauvegardé: {summary_path}")

    # Optional: LLM Judge evaluation
    if not skip_judge:
        logger.info(f"\n{'='*60}")
        logger.info("ÉVALUATION LLM JUDGE (sur un échantillon)")
        logger.info(f"{'='*60}")

        judge = LLMJudge(model_name="default")
        judge_results = []

        # Judge first successful result from each workflow
        for workflow in workflows:
            wf_results = [
                r
                for r in collector.query(workflow_name=workflow)
                if r.get("success", False)
            ]
            if wf_results:
                sample = wf_results[0]
                doc_idx = sample["document_index"]
                doc_text = runner.get_document_text(doc_idx)

                logger.info(f"  Évaluation workflow={workflow}, doc={doc_idx}...")
                try:
                    score = await judge.evaluate(
                        input_text=doc_text,
                        workflow_name=workflow,
                        analysis_results=sample.get("state_snapshot", {}),
                        model_registry=model_registry,
                    )
                    judge_results.append(
                        {
                            "workflow": workflow,
                            "document_index": doc_idx,
                            "document_id": documents[doc_idx].get(
                                "id", f"doc_{doc_idx}"
                            ),
                            "score": {
                                "completeness": score.completeness,
                                "accuracy": score.accuracy,
                                "depth": score.depth,
                                "coherence": score.coherence,
                                "actionability": score.actionability,
                                "overall": score.overall,
                            },
                            "reasoning": score.reasoning,
                        }
                    )
                    logger.info(f"    Score global: {score.overall}/5")
                except Exception as e:
                    logger.error(f"    Erreur de jugement: {e}")

        if judge_results:
            judge_path = output_path / "judge_evaluation.json"
            with open(judge_path, "w", encoding="utf-8") as f:
                json.dump(judge_results, f, indent=2, ensure_ascii=False)
            logger.info(f"Évaluation judge sauvegardée: {judge_path}")

    return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Baseline Capability Benchmark")
    parser.add_argument(
        "--corpus",
        default="argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json",
        help="Chemin vers le corpus JSON",
    )
    parser.add_argument(
        "--output",
        default="argumentation_analysis/evaluation/results/baseline",
        help="Répertoire de sortie",
    )
    parser.add_argument(
        "--workflows",
        nargs="+",
        default=["light", "standard"],
        choices=["light", "standard", "full"],
        help="Workflows à tester",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="Nombre max de documents (0 = tous)",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Sauter l'évaluation LLM judge",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mode verbeux",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run benchmark
    asyncio.run(
        run_baseline_benchmark(
            corpus_path=args.corpus,
            output_dir=args.output,
            workflows=args.workflows,
            max_docs=args.max_docs,
            skip_judge=args.skip_judge,
        )
    )


if __name__ == "__main__":
    main()

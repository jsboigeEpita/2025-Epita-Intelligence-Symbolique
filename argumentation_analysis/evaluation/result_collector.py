"""
Result collector: persist and query benchmark results.

Stores results as JSON lines (append-only) with optional summary generation.
"""

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

logger = logging.getLogger("evaluation.result_collector")

DEFAULT_RESULTS_DIR = Path("argumentation_analysis/evaluation/results")


class ResultCollector:
    """Append-only benchmark result store with query capabilities."""

    def __init__(self, results_dir: Optional[Path] = None):
        self.results_dir = results_dir or DEFAULT_RESULTS_DIR
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._results_file = self.results_dir / "benchmark_results.jsonl"

    def save(self, result: BenchmarkResult) -> None:
        """Append a single result to the JSONL file."""
        with open(self._results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
        logger.debug(f"Saved result: {result.workflow_name}/{result.model_name}/{result.document_name}")

    def save_batch(self, results: List[BenchmarkResult]) -> None:
        """Append multiple results."""
        for r in results:
            self.save(r)

    def load_all(self) -> List[Dict[str, Any]]:
        """Load all results from JSONL file."""
        if not self._results_file.exists():
            return []
        results = []
        with open(self._results_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
        return results

    def query(
        self,
        workflow_name: Optional[str] = None,
        model_name: Optional[str] = None,
        document_index: Optional[int] = None,
        success_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Filter results by criteria."""
        results = self.load_all()
        if workflow_name:
            results = [r for r in results if r["workflow_name"] == workflow_name]
        if model_name:
            results = [r for r in results if r["model_name"] == model_name]
        if document_index is not None:
            results = [r for r in results if r["document_index"] == document_index]
        if success_only:
            results = [r for r in results if r["success"]]
        return results

    def generate_summary(self) -> Dict[str, Any]:
        """Generate a summary report from all collected results."""
        all_results = self.load_all()
        if not all_results:
            return {"total": 0, "message": "No results collected yet"}

        total = len(all_results)
        successes = sum(1 for r in all_results if r["success"])
        failures = total - successes

        # Group by model
        by_model: Dict[str, List] = {}
        for r in all_results:
            by_model.setdefault(r["model_name"], []).append(r)

        # Group by workflow
        by_workflow: Dict[str, List] = {}
        for r in all_results:
            by_workflow.setdefault(r["workflow_name"], []).append(r)

        model_stats = {}
        for model, results in by_model.items():
            ok = [r for r in results if r["success"]]
            model_stats[model] = {
                "total": len(results),
                "success": len(ok),
                "avg_duration": sum(r["duration_seconds"] for r in ok) / len(ok) if ok else 0,
                "avg_phases_completed": sum(r["phases_completed"] for r in ok) / len(ok) if ok else 0,
            }

        workflow_stats = {}
        for wf, results in by_workflow.items():
            ok = [r for r in results if r["success"]]
            workflow_stats[wf] = {
                "total": len(results),
                "success": len(ok),
                "avg_duration": sum(r["duration_seconds"] for r in ok) / len(ok) if ok else 0,
            }

        return {
            "total": total,
            "successes": successes,
            "failures": failures,
            "by_model": model_stats,
            "by_workflow": workflow_stats,
            "generated_at": datetime.now().isoformat(),
        }

    def export_csv(self, output_path: Optional[Path] = None) -> Path:
        """Export results to CSV for external analysis."""
        import csv

        output = output_path or (self.results_dir / "benchmark_results.csv")
        all_results = self.load_all()

        if not all_results:
            logger.warning("No results to export")
            return output

        fields = [
            "timestamp", "workflow_name", "model_name", "document_index",
            "document_name", "success", "duration_seconds", "phases_completed",
            "phases_total", "phases_failed", "phases_skipped", "error",
        ]

        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_results)

        logger.info(f"Exported {len(all_results)} results to {output}")
        return output

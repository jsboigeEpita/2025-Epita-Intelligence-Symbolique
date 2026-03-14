"""
Synergy Analyzer: Analyze workflow and agent combination performance.

Provides tools to:
- Compare workflows across different document types
- Identify optimal agent combinations
- Generate synergy reports and recommendations
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

logger = logging.getLogger("evaluation.synergy_analyzer")

# Workflow phase definitions
WORKFLOW_PHASES = {
    "light": ["extract", "quality", "counter"],
    "standard": ["extract", "quality", "counter", "jtms", "governance", "debate"],
    "full": ["transcribe", "extract", "quality", "neural_fallacy", "counter", "jtms", "governance", "debate", "index"],
}

# Document difficulty levels
DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

# Fallacy categories
FALLACY_CATEGORIES = [
    "ad_hominem",
    "appeal_to_authority",
    "appeal_to_emotion",
    "appeal_to_popularity",
    "appeal_to_tradition",
    "false_analogy",
    "false_dilemma",
    "guilt_by_association",
    "hasty_generalization",
    "loaded_language",
    "poisoning_the_well",
    "red_herring",
    "slippery_slope",
    "straw_man",
]


@dataclass
class WorkflowMetrics:
    """Performance metrics for a workflow."""
    workflow_name: str
    total_runs: int = 0
    success_rate: float = 0.0
    avg_duration: float = 0.0
    avg_phases_completed: float = 0.0
    avg_phases_total: float = 0.0
    completion_ratio: float = 0.0  # phases_completed / phases_total
    by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_fallacy_category: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class SynergyRecommendation:
    """Recommendation for optimal workflow configuration."""
    use_case: str
    recommended_workflow: str
    confidence: float  # 0.0 - 1.0
    reasoning: str
    alternative_workflows: List[str] = field(default_factory=list)
    expected_metrics: Dict[str, float] = field(default_factory=dict)


class SynergyAnalyzer:
    """Analyze workflow and agent combination performance from benchmark results."""

    def __init__(self, results_dir: Optional[Path] = None):
        from argumentation_analysis.evaluation.result_collector import ResultCollector, DEFAULT_RESULTS_DIR

        self.results_dir = results_dir or DEFAULT_RESULTS_DIR
        self.collector = ResultCollector(self.results_dir)
        self._corpus_data: Optional[Dict] = None

    def load_corpus(self, corpus_path: Optional[Path] = None) -> Dict:
        """Load baseline corpus metadata for document categorization."""
        if self._corpus_data is not None:
            return self._corpus_data

        default_path = Path(__file__).parent / "corpus" / "baseline_corpus_v1.json"
        path = corpus_path or default_path

        if not path.exists():
            logger.warning(f"Corpus file not found at {path}")
            return {}

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # Strip BOM if present
            if content.startswith("\ufeff"):
                content = content[1:]
            self._corpus_data = json.loads(content)

        return self._corpus_data

    def get_document_metadata(self, document_index: int) -> Dict[str, Any]:
        """Get metadata for a document from the corpus."""
        corpus = self.load_corpus()
        if not corpus or document_index >= len(corpus.get("documents", [])):
            return {"difficulty": "unknown", "expected_fallacies": []}

        return {
            "id": corpus["documents"][document_index].get("id", f"doc_{document_index}"),
            "difficulty": corpus["documents"][document_index].get("difficulty", "unknown"),
            "expected_fallacies": corpus["documents"][document_index].get("expected_fallacies", []),
            "expected_quality_score_range": corpus["documents"][document_index].get("expected_quality_score_range", [0, 10]),
        }

    def analyze_workflow_performance(self) -> Dict[str, WorkflowMetrics]:
        """Analyze performance metrics for each workflow."""
        all_results = self.collector.load_all()
        if not all_results:
            logger.warning("No results to analyze")
            return {}

        metrics: Dict[str, WorkflowMetrics] = {}

        for workflow in WORKFLOW_PHASES.keys():
            wf_results = [r for r in all_results if r["workflow_name"] == workflow]
            if not wf_results:
                continue

            successful = [r for r in wf_results if r["success"]]

            # Base metrics
            workflow_metric = WorkflowMetrics(
                workflow_name=workflow,
                total_runs=len(wf_results),
                success_rate=len(successful) / len(wf_results) if wf_results else 0.0,
                avg_duration=np.mean([r["duration_seconds"] for r in successful]) if successful else 0.0,
                avg_phases_completed=np.mean([r["phases_completed"] for r in successful]) if successful else 0.0,
                avg_phases_total=np.mean([r["phases_total"] for r in successful]) if successful else 0.0,
            )
            workflow_metric.completion_ratio = (
                workflow_metric.avg_phases_completed / workflow_metric.avg_phases_total
                if workflow_metric.avg_phases_total > 0
                else 0.0
            )

            # By difficulty
            for difficulty in DIFFICULTY_LEVELS:
                diff_results = [
                    r for r in wf_results
                    if self.get_document_metadata(r["document_index"])["difficulty"] == difficulty
                ]
                diff_successful = [r for r in diff_results if r["success"]]
                if diff_results:
                    workflow_metric.by_difficulty[difficulty] = {
                        "count": len(diff_results),
                        "success_rate": len(diff_successful) / len(diff_results),
                        "avg_duration": np.mean([r["duration_seconds"] for r in diff_successful]) if diff_successful else 0.0,
                    }

            metrics[workflow] = workflow_metric

        return metrics

    def compare_workflows(self) -> Dict[str, Any]:
        """Generate comparative analysis between workflows."""
        metrics = self.analyze_workflow_performance()
        if not metrics:
            return {"error": "No metrics available"}

        comparison = {
            "workflows": {},
            "best_by_success_rate": None,
            "best_by_speed": None,
            "best_by_completion": None,
            "summary": {},
        }

        # Find best performers
        best_success = max(metrics.items(), key=lambda x: x[1].success_rate)
        comparison["best_by_success_rate"] = {
            "workflow": best_success[0],
            "rate": best_success[1].success_rate,
        }

        best_speed = min(
            [(k, v) for k, v in metrics.items() if v.avg_duration > 0],
            key=lambda x: x[1].avg_duration,
            default=(None, None),
        )
        if best_speed[0]:
            comparison["best_by_speed"] = {
                "workflow": best_speed[0],
                "avg_duration": best_speed[1].avg_duration,
            }

        best_completion = max(metrics.items(), key=lambda x: x[1].completion_ratio)
        comparison["best_by_completion"] = {
            "workflow": best_completion[0],
            "ratio": best_completion[1].completion_ratio,
        }

        # Workflow details
        for workflow, metric in metrics.items():
            comparison["workflows"][workflow] = {
                "total_runs": metric.total_runs,
                "success_rate": metric.success_rate,
                "avg_duration": metric.avg_duration,
                "completion_ratio": metric.completion_ratio,
                "by_difficulty": metric.by_difficulty,
            }

        # Summary statistics
        all_success_rates = [m.success_rate for m in metrics.values()]
        all_durations = [m.avg_duration for m in metrics.values() if m.avg_duration > 0]
        all_completion_ratios = [m.completion_ratio for m in metrics.values()]

        comparison["summary"] = {
            "avg_success_rate": float(np.mean(all_success_rates)) if all_success_rates else 0.0,
            "std_success_rate": float(np.std(all_success_rates)) if all_success_rates else 0.0,
            "avg_duration": float(np.mean(all_durations)) if all_durations else 0.0,
            "avg_completion_ratio": float(np.mean(all_completion_ratios)) if all_completion_ratios else 0.0,
            "total_workflows_analyzed": len(metrics),
        }

        return comparison

    def generate_recommendations(self) -> List[SynergyRecommendation]:
        """Generate recommendations for optimal workflow configurations."""
        metrics = self.analyze_workflow_performance()
        if not metrics:
            return []

        recommendations = []

        # 1. Fast analysis recommendation (for quick assessments)
        fastest = min(
            [(k, v) for k, v in metrics.items() if v.avg_duration > 0],
            key=lambda x: x[1].avg_duration,
            default=None,
        )
        if fastest:
            recommendations.append(SynergyRecommendation(
                use_case="quick_assessment",
                recommended_workflow=fastest[0],
                confidence=0.9 if fastest[1].success_rate > 0.8 else 0.7,
                reasoning=f"Fastest workflow with {fastest[1].avg_duration:.1f}s average duration and {fastest[1].success_rate*100:.1f}% success rate",
                alternative_workflows=[k for k in metrics.keys() if k != fastest[0]],
                expected_metrics={"avg_duration": fastest[1].avg_duration, "success_rate": fastest[1].success_rate},
            ))

        # 2. High accuracy recommendation (for thorough analysis)
        most_accurate = max(metrics.items(), key=lambda x: x[1].completion_ratio * x[1].success_rate)
        recommendations.append(SynergyRecommendation(
            use_case="thorough_analysis",
            recommended_workflow=most_accurate[0],
            confidence=0.85,
            reasoning=f"Highest completion ratio ({most_accurate[1].completion_ratio:.2f}) with good success rate ({most_accurate[1].success_rate*100:.1f}%)",
            alternative_workflows=[k for k in metrics.keys() if k != most_accurate[0]],
            expected_metrics={
                "completion_ratio": most_accurate[1].completion_ratio,
                "success_rate": most_accurate[1].success_rate,
            },
        ))

        # 3. Easy documents recommendation
        easy_performance = {}
        for workflow, metric in metrics.items():
            easy_stats = metric.by_difficulty.get("easy", {})
            if easy_stats:
                easy_performance[workflow] = easy_stats.get("success_rate", 0.0)

        if easy_performance:
            best_for_easy = max(easy_performance.items(), key=lambda x: x[1])
            recommendations.append(SynergyRecommendation(
                use_case="easy_documents",
                recommended_workflow=best_for_easy[0],
                confidence=0.8,
                reasoning=f"Best performance on easy documents ({best_for_easy[1]*100:.1f}% success rate)",
                alternative_workflows=[k for k in easy_performance.keys() if k != best_for_easy[0]],
                expected_metrics={"easy_success_rate": best_for_easy[1]},
            ))

        # 4. Hard documents recommendation
        hard_performance = {}
        for workflow, metric in metrics.items():
            hard_stats = metric.by_difficulty.get("hard", {})
            if hard_stats:
                hard_performance[workflow] = hard_stats.get("success_rate", 0.0)

        if hard_performance:
            best_for_hard = max(hard_performance.items(), key=lambda x: x[1])
            recommendations.append(SynergyRecommendation(
                use_case="complex_documents",
                recommended_workflow=best_for_hard[0],
                confidence=0.75,
                reasoning=f"Best performance on hard/complex documents ({best_for_hard[1]*100:.1f}% success rate)",
                alternative_workflows=[k for k in hard_performance.keys() if k != best_for_hard[0]],
                expected_metrics={"hard_success_rate": best_for_hard[1]},
            ))

        return recommendations

    def generate_report(self, output_path: Optional[Path] = None) -> Path:
        """Generate a comprehensive synergy analysis report."""
        output = output_path or (self.results_dir / "synergy_analysis_report.json")

        comparison = self.compare_workflows()
        recommendations = self.generate_recommendations()

        report = {
            "generated_at": datetime.now().isoformat(),
            "analyzer_version": "1.0",
            "comparison": comparison,
            "recommendations": [
                {
                    "use_case": r.use_case,
                    "recommended_workflow": r.recommended_workflow,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                    "alternative_workflows": r.alternative_workflows,
                    "expected_metrics": r.expected_metrics,
                }
                for r in recommendations
            ],
            "workflow_phases": WORKFLOW_PHASES,
        }

        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Synergy analysis report saved to {output}")
        return output

    def export_markdown_report(self, output_path: Optional[Path] = None) -> Path:
        """Generate a human-readable Markdown report."""
        output = output_path or (self.results_dir / "synergy_analysis_report.md")

        comparison = self.compare_workflows()
        recommendations = self.generate_recommendations()

        lines = [
            "# Synergy Analysis Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Analyzer Version**: 1.0",
            "",
            "## Executive Summary",
            "",
        ]

        if "summary" in comparison:
            summary = comparison["summary"]
            lines.extend([
                f"- **Total Workflows Analyzed**: {summary.get('total_workflows_analyzed', 0)}",
                f"- **Average Success Rate**: {summary.get('avg_success_rate', 0)*100:.1f}%",
                f"- **Average Duration**: {summary.get('avg_duration', 0):.1f}s",
                f"- **Average Completion Ratio**: {summary.get('avg_completion_ratio', 0)*100:.1f}%",
                "",
            ])

        if "best_by_success_rate" in comparison and comparison["best_by_success_rate"]:
            best = comparison["best_by_success_rate"]
            lines.extend([
                f"**Best Success Rate**: {best['workflow']} ({best['rate']*100:.1f}%)",
            ])
        if "best_by_speed" in comparison and comparison["best_by_speed"]:
            best = comparison["best_by_speed"]
            lines.extend([
                f"**Fastest Workflow**: {best['workflow']} ({best['avg_duration']:.1f}s)",
            ])
        if "best_by_completion" in comparison and comparison["best_by_completion"]:
            best = comparison["best_by_completion"]
            lines.extend([
                f"**Best Completion**: {best['workflow']} ({best['ratio']*100:.1f}%)",
            ])
        lines.append("")

        # Workflow comparison table
        lines.extend([
            "## Workflow Comparison",
            "",
            "| Workflow | Success Rate | Avg Duration | Completion Ratio | Total Runs |",
            "|----------|--------------|--------------|------------------|------------|",
        ])

        if "workflows" in comparison:
            for workflow, data in comparison["workflows"].items():
                lines.append(
                    f"| {workflow} | {data['success_rate']*100:.1f}% | "
                    f"{data['avg_duration']:.1f}s | {data['completion_ratio']*100:.1f}% | "
                    f"{data['total_runs']} |"
                )

        lines.append("")

        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
        ])

        for rec in recommendations:
            lines.extend([
                f"### {rec.use_case.replace('_', ' ').title()}",
                "",
                f"**Recommended**: `{rec.recommended_workflow}`",
                f"**Confidence**: {rec.confidence*100:.0f}%",
                "",
                f"{rec.reasoning}",
                "",
            ])
            if rec.alternative_workflows:
                lines.append(f"**Alternatives**: {', '.join(f'`{w}`' for w in rec.alternative_workflows)}")
                lines.append("")

        # Workflow phases
        lines.extend([
            "## Workflow Phases",
            "",
            "### Light",
            "1. extract (fact extraction)",
            "2. quality (argument quality)",
            "3. counter (counter-argument generation)",
            "",
            "### Standard",
            "1. extract (fact extraction)",
            "2. quality (argument quality)",
            "3. counter (counter-argument generation)",
            "4. jtms (belief maintenance, optional)",
            "5. governance (governance simulation, optional)",
            "6. debate (adversarial debate, optional)",
            "",
            "### Full",
            "1. transcribe (speech transcription, optional)",
            "2. extract (fact extraction)",
            "3. quality (argument quality)",
            "4. neural_fallacy (neural fallacy detection, optional)",
            "5. counter (counter-argument generation)",
            "6. jtms (belief maintenance, optional)",
            "7. governance (governance simulation, optional)",
            "8. debate (adversarial debate, optional)",
            "9. index (semantic indexing, optional)",
            "",
        ])

        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Markdown report saved to {output}")
        return output

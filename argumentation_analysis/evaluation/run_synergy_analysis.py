"""
Synergy Analysis Runner

Analyzes benchmark results to determine optimal workflow configurations
and agent combinations for different use cases.
"""

import argparse
import logging
from pathlib import Path

from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

logger = logging.getLogger("evaluation.synergy_runner")


def main():
    parser = argparse.ArgumentParser(description="Synergy Analysis - Optimal Workflow Configuration")
    parser.add_argument(
        "--results-dir",
        default="argumentation_analysis/evaluation/results",
        help="Directory containing benchmark results",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for reports (default: results_dir)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Report format",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    results_dir = Path(args.results_dir)
    analyzer = SynergyAnalyzer(results_dir)

    logger.info("Loading corpus metadata...")
    analyzer.load_corpus()

    logger.info("Analyzing workflow performance...")
    metrics = analyzer.analyze_workflow_performance()

    if not metrics:
        logger.error("No benchmark results found. Run a benchmark first.")
        return 1

    logger.info(f"Found metrics for {len(metrics)} workflows:")
    for workflow, metric in metrics.items():
        logger.info(
            f"  {workflow}: {metric.total_runs} runs, "
            f"{metric.success_rate*100:.1f}% success, "
            f"{metric.avg_duration:.1f}s avg"
        )

    output_path = Path(args.output) if args.output else None

    if args.format in ("json", "both"):
        json_path = analyzer.generate_report(output_path)
        logger.info(f"JSON report: {json_path}")

    if args.format in ("markdown", "both"):
        md_path = analyzer.export_markdown_report(output_path)
        logger.info(f"Markdown report: {md_path}")

    # Print recommendations to console
    recommendations = analyzer.generate_recommendations()
    logger.info("\n=== RECOMMENDATIONS ===")
    for rec in recommendations:
        logger.info(f"\n[{rec.use_case}]")
        logger.info(f"  Workflow: {rec.recommended_workflow}")
        logger.info(f"  Confidence: {rec.confidence*100:.0f}%")
        logger.info(f"  Reasoning: {rec.reasoning}")

    return 0


if __name__ == "__main__":
    exit(main())

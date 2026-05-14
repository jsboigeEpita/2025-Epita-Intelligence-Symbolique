"""Compare pre/post Epic G baseline results (#481).

Reads JSON result files from analysis_kb/results/ and produces
a markdown comparison report with aggregate metrics.

Usage:
    python analysis_kb/compare_results.py --pre doc_2 --post doc_2_epic_g
    python analysis_kb/compare_results.py --all
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RESULTS_DIR = Path("analysis_kb/results")
REPORTS_DIR = Path("analysis_kb/reports")


def load_result(name: str) -> Optional[Dict[str, Any]]:
    path = RESULTS_DIR / f"{name}.json"
    if not path.exists():
        print(f"Warning: {path} not found", file=sys.stderr)
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def count_non_empty(data: Dict[str, Any]) -> int:
    """Count non-empty top-level fields."""
    return sum(
        1
        for v in data.values()
        if v is not None and v != "" and v != [] and v != {} and v != 0
    )


def extract_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract comparable metrics from a result file."""
    return {
        "non_empty_fields": data.get("non_empty_fields", 0),
        "total_fields": data.get("total_fields", 0),
        "duration_seconds": data.get("duration_seconds", 0),
        "phases_completed": data.get("phases_completed", "0/0"),
        "phases_failed": data.get("phases_failed", 0),
        "arguments_count": data.get("arguments_count", 0),
        "fallacies_count": data.get("fallacies_count", 0),
        "jtms_beliefs_count": data.get("jtms_beliefs_count", 0),
        "formal_results_keys": data.get("formal_results_keys", []),
        "counter_arguments_count": data.get("counter_arguments_count", 0),
        "quality_scores": data.get("quality_scores", {}),
        "debate_results_keys": data.get("debate_results_keys", []),
        "governance_results_keys": data.get("governance_results_keys", []),
        "state_json_size_bytes": data.get("state_json_size_bytes", 0),
        "capabilities_used": data.get("capabilities_used", []),
        "capabilities_missing": data.get("capabilities_missing", []),
    }


def compare_pair(
    pre_name: str, post_name: str
) -> Optional[Dict[str, Any]]:
    """Compare pre/post results for a single document."""
    pre = load_result(pre_name)
    post = load_result(post_name)
    if pre is None or post is None:
        return None

    pre_m = extract_metrics(pre)
    post_m = extract_metrics(post)

    # Calculate field coverage improvement
    pre_coverage = pre_m["non_empty_fields"] / max(pre_m["total_fields"], 1) * 100
    post_coverage = post_m["non_empty_fields"] / max(post_m["total_fields"], 1) * 100

    # New capabilities gained
    pre_caps = set(pre_m["capabilities_used"])
    post_caps = set(post_m["capabilities_used"])
    new_caps = post_caps - pre_caps

    return {
        "pre_name": pre_name,
        "post_name": post_name,
        "pre": pre_m,
        "post": post_m,
        "coverage_delta": round(post_coverage - pre_coverage, 1),
        "new_capabilities": sorted(new_caps),
        "formal_results_delta": len(post_m["formal_results_keys"])
        - len(pre_m["formal_results_keys"]),
    }


def generate_report(
    comparisons: List[Dict[str, Any]], title: str = "Epic G Pre/Post Comparison"
) -> str:
    """Generate markdown report from comparisons."""
    lines = [
        f"# {title}",
        f"",
        f"Generated: {datetime.now().isoformat()}",
        f"Documents compared: {len(comparisons)}",
        "",
    ]

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| Document | Pre Coverage | Post Coverage | Delta | New Caps | Formal Keys Delta |"
    )
    lines.append(
        "|----------|-------------|--------------|-------|----------|-------------------|"
    )

    for c in comparisons:
        pre_cov = f'{c["pre"]["non_empty_fields"]}/{c["pre"]["total_fields"]}'
        post_cov = f'{c["post"]["non_empty_fields"]}/{c["post"]["total_fields"]}'
        lines.append(
            f'| {c["pre_name"]} | {pre_cov} | {post_cov} | '
            f'{c["coverage_delta"]:+.1f}% | {len(c["new_capabilities"])} | '
            f'{c["formal_results_delta"]:+d} |'
        )

    lines.append("")

    # Per-document detail
    for c in comparisons:
        lines.append(f"## {c['pre_name']}")
        lines.append("")
        lines.append("### Field Coverage")
        lines.append(f"- Arguments: {c['pre']['arguments_count']} → {c['post']['arguments_count']}")
        lines.append(f"- Fallacies: {c['pre']['fallacies_count']} → {c['post']['fallacies_count']}")
        lines.append(f"- JTMS beliefs: {c['pre']['jtms_beliefs_count']} → {c['post']['jtms_beliefs_count']}")
        lines.append(
            f"- Counter-arguments: {c['pre']['counter_arguments_count']} → {c['post']['counter_arguments_count']}"
        )
        lines.append(
            f"- Formal results: {c['pre']['formal_results_keys']} → {c['post']['formal_results_keys']}"
        )
        lines.append(
            f"- State size: {c['pre']['state_json_size_bytes']}B → {c['post']['state_json_size_bytes']}B"
        )
        lines.append(
            f"- Duration: {c['pre']['duration_seconds']:.1f}s → {c['post']['duration_seconds']:.1f}s"
        )
        lines.append("")

        if c["new_capabilities"]:
            lines.append("### New Capabilities")
            for cap in c["new_capabilities"]:
                lines.append(f"- `{cap}`")
            lines.append("")

        # Regression check
        if c["coverage_delta"] < -10:
            lines.append(
                f"**WARNING: Regression detected ({c['coverage_delta']:.1f}%)**"
            )
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare pre/post Epic G baselines")
    parser.add_argument("--pre", nargs="+", help="Pre-result filenames (without .json)")
    parser.add_argument("--post", nargs="+", help="Post-result filenames (without .json)")
    parser.add_argument("--all", action="store_true", help="Compare all doc_*_pipeline_full vs doc_*_epic_g_full")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    args = parser.parse_args()

    comparisons = []

    if args.all:
        # Find pre/post pairs
        pre_files = sorted(RESULTS_DIR.glob("doc_*_pipeline_full.json"))
        for pre_path in pre_files:
            pre_name = pre_path.stem
            # Derive post name
            post_name = pre_name.replace("_pipeline_full", "_epic_g_full")
            c = compare_pair(pre_name, post_name)
            if c:
                comparisons.append(c)
    elif args.pre and args.post:
        for pre_name, post_name in zip(args.pre, args.post):
            c = compare_pair(pre_name, post_name)
            if c:
                comparisons.append(c)
    else:
        # Default: compare all existing results
        for f in sorted(RESULTS_DIR.glob("doc_*_pipeline_full.json")):
            name = f.stem
            pre_m = extract_metrics(load_result(name))
            empty_m = {"non_empty_fields": 0, "total_fields": 0, "duration_seconds": 0,
                        "phases_completed": "0/0", "phases_failed": 0, "arguments_count": 0,
                        "fallacies_count": 0, "jtms_beliefs_count": 0, "formal_results_keys": [],
                        "counter_arguments_count": 0, "quality_scores": {},
                        "debate_results_keys": [], "governance_results_keys": [],
                        "state_json_size_bytes": 0, "capabilities_used": [],
                        "capabilities_missing": []}
            c = {"pre_name": name, "post_name": "(pending)", "pre": pre_m,
                 "post": empty_m, "coverage_delta": 0, "new_capabilities": [],
                 "formal_results_delta": 0}
            comparisons.append(c)

    report = generate_report(comparisons)

    if args.output:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORTS_DIR / args.output
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {out_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()

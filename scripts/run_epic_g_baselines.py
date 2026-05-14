"""Run Epic G baselines on 3 opaque documents (#481).

Runs the spectacular and formal_extended workflows on selected documents
and saves results to analysis_kb/results/.

Usage:
    python analysis_kb/run_epic_g_baselines.py --workflow spectacular
    python analysis_kb/run_epic_g_baselines.py --workflow formal_extended
    python analysis_kb/run_epic_g_baselines.py --all

Note: Requires OPENAI_API_KEY in .env and the encrypted dataset passphrase.
      This script is gitignored — results contain aggregate metrics only.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path("analysis_kb/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 3 opaque documents from the encrypted dataset
DOC_IDS = ["src0_ext0", "src3_ext0", "src6_ext0"]


def load_document_text(doc_id: str) -> Optional[str]:
    """Load document text from the encrypted dataset."""
    try:
        from argumentation_analysis.core.io_manager import load_extract_definitions
        from argumentation_analysis.core.environment import get_text_config_passphrase

        passphrase = get_text_config_passphrase()
        if not passphrase:
            print(f"Warning: No passphrase available for dataset", file=sys.stderr)
            return None

        definitions = load_extract_definitions(passphrase)
        for source in definitions:
            for extract in source.get("extracts", []):
                if extract.get("id") == doc_id or f"src{definitions.index(source)}_ext{source.get('extracts', []).index(extract)}" == doc_id:
                    return extract.get("full_text", "")
        print(f"Warning: Document '{doc_id}' not found in dataset", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error loading dataset: {e}", file=sys.stderr)
        return None


def run_workflow_on_text(
    text: str, doc_id: str, workflow_name: str
) -> Dict[str, Any]:
    """Run a workflow on text and return metrics."""
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            UnifiedPipeline,
        )

        pipeline = UnifiedPipeline()
        registry = pipeline.registry

        from argumentation_analysis.orchestration.workflows import get_workflow_catalog
        catalog = get_workflow_catalog()

        if workflow_name not in catalog:
            print(f"Workflow '{workflow_name}' not in catalog. Available: {list(catalog.keys())}", file=sys.stderr)
            return {"error": f"Workflow '{workflow_name}' not found"}

        start = time.time()
        result = pipeline.run_workflow(workflow_name, text)
        duration = time.time() - start

        # Extract metrics from result
        state = result.get("state")
        if state is not None:
            metrics = extract_state_metrics(state)
        else:
            metrics = {"error": "No state returned"}

        metrics.update({
            "document": doc_id,
            "mode": "pipeline",
            "workflow": workflow_name,
            "duration_seconds": round(duration, 1),
            "timestamp": datetime.now().isoformat(),
        })
        return metrics

    except Exception as e:
        return {
            "document": doc_id,
            "mode": "pipeline",
            "workflow": workflow_name,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def extract_state_metrics(state: Any) -> Dict[str, Any]:
    """Extract aggregate metrics from a UnifiedAnalysisState."""
    metrics = {
        "non_empty_fields": 0,
        "total_fields": 0,
        "arguments_count": 0,
        "fallacies_count": 0,
        "jtms_beliefs_count": 0,
        "formal_results_keys": [],
        "counter_arguments_count": 0,
        "quality_scores": {},
        "debate_results_keys": [],
        "governance_results_keys": [],
        "state_json_size_bytes": 0,
        "capabilities_used": [],
        "capabilities_missing": [],
    }

    try:
        # Count non-empty fields
        if hasattr(state, "to_dict"):
            d = state.to_dict()
        elif hasattr(state, "__dict__"):
            d = {k: v for k, v in state.__dict__.items() if not k.startswith("_")}
        else:
            d = {}

        metrics["total_fields"] = len(d)
        metrics["non_empty_fields"] = sum(
            1 for v in d.values()
            if v is not None and v != "" and v != [] and v != {}
        )
        metrics["state_json_size_bytes"] = len(json.dumps(d, default=str))

        # Specific counts
        if hasattr(state, "arguments"):
            metrics["arguments_count"] = len(state.arguments) if state.arguments else 0
        if hasattr(state, "fallacies"):
            metrics["fallacies_count"] = len(state.fallacies) if state.fallacies else 0
        if hasattr(state, "jtms_beliefs"):
            metrics["jtms_beliefs_count"] = len(state.jtms_beliefs) if state.jtms_beliefs else 0
        if hasattr(state, "formal_results"):
            metrics["formal_results_keys"] = list(state.formal_results.keys()) if state.formal_results else []
        if hasattr(state, "counter_arguments"):
            metrics["counter_arguments_count"] = len(state.counter_arguments) if state.counter_arguments else 0
        if hasattr(state, "quality_scores"):
            metrics["quality_scores"] = state.quality_scores if state.quality_scores else {}
        if hasattr(state, "debate_results"):
            metrics["debate_results_keys"] = list(state.debate_results.keys()) if state.debate_results else []
        if hasattr(state, "governance_results"):
            metrics["governance_results_keys"] = list(state.governance_results.keys()) if state.governance_results else []

    except Exception as e:
        metrics["extraction_error"] = str(e)

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Run Epic G baselines")
    parser.add_argument(
        "--workflow",
        default="spectacular",
        help="Workflow to run (default: spectacular)",
    )
    parser.add_argument(
        "--docs",
        nargs="+",
        default=DOC_IDS,
        help=f"Document IDs to analyze (default: {DOC_IDS})",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run both spectacular and formal_extended workflows",
    )
    args = parser.parse_args()

    workflows = [args.workflow]
    if args.all:
        workflows = ["spectacular", "formal_extended"]

    for workflow_name in workflows:
        print(f"\n{'='*60}")
        print(f"Running workflow: {workflow_name}")
        print(f"Documents: {args.docs}")
        print(f"{'='*60}\n")

        for doc_id in args.docs:
            print(f"Loading {doc_id}...", end=" ")
            text = load_document_text(doc_id)
            if not text:
                print("SKIP (not found)")
                continue
            print(f"({len(text)} chars)")

            print(f"Running {workflow_name} on {doc_id}...", end=" ", flush=True)
            result = run_workflow_on_text(text, doc_id, workflow_name)

            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(
                    f"OK ({result.get('duration_seconds', 0):.1f}s, "
                    f"{result.get('non_empty_fields', 0)}/{result.get('total_fields', 0)} fields)"
                )

            # Save result
            suffix = "epic_g" if workflow_name == "spectacular" else workflow_name
            out_name = f"{doc_id}_{suffix}.json"
            out_path = RESULTS_DIR / out_name
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str, ensure_ascii=False)
            print(f"  Saved to {out_path}")


if __name__ == "__main__":
    main()

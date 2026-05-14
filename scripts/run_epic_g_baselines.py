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
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
    except ImportError:
        pass

    try:
        from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
        from argumentation_analysis.core.io_manager import load_extract_definitions

        passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE", "")
        if not passphrase:
            print("Warning: TEXT_CONFIG_PASSPHRASE not set", file=sys.stderr)
            return None

        key = derive_encryption_key(passphrase)
        config_file = Path(__file__).parent.parent / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
        if not config_file.exists():
            print(f"Error: Encrypted config not found at {config_file}", file=sys.stderr)
            return None

        definitions = load_extract_definitions(config_file, key)
        for src_idx, source in enumerate(definitions):
            # Try source-level full_text first
            source_ft = source.get("full_text", "")
            for ext_idx, extract in enumerate(source.get("extracts", [])):
                synthetic_id = f"src{src_idx}_ext{ext_idx}"
                if synthetic_id == doc_id:
                    # Prefer extract-level text, fall back to source-level
                    text = extract.get("full_text", "") or source_ft
                    return text if text else None
        print(f"Warning: Document '{doc_id}' not found in dataset", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error loading dataset: {e}", file=sys.stderr)
        return None


async def run_workflow_on_text(
    text: str, doc_id: str, workflow_name: str
) -> Dict[str, Any]:
    """Run a workflow on text and return metrics."""
    import asyncio
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        start = time.time()
        results = await run_unified_analysis(text=text, workflow_name=workflow_name)
        duration = time.time() - start

        state = results.get("state_snapshot", {})
        summary = results.get("summary", {})

        metrics = {
            "document": doc_id,
            "mode": "pipeline",
            "workflow": workflow_name,
            "duration_seconds": round(duration, 1),
            "phases_completed": f"{summary.get('completed', 0)}/{summary.get('total', 0)}",
            "phases_failed": summary.get("failed", 0),
            "phases_skipped": summary.get("skipped", 0),
            "non_empty_fields": 0,
            "total_fields": 0,
            "state_json_size_bytes": len(json.dumps(state, default=str).encode()) if state else 0,
            "arguments_count": len(state.get("arguments", [])) if state else 0,
            "fallacies_count": len(state.get("fallacies", [])) if state else 0,
            "formal_results_keys": list(state.get("formal_analysis", {}).keys()) if isinstance(state.get("formal_analysis"), dict) else [],
            "jtms_beliefs_count": len(state.get("jtms_beliefs", [])) if state else 0,
            "quality_scores": state.get("quality_scores", {}) if state else {},
            "counter_arguments_count": len(state.get("counter_arguments", [])) if state else 0,
            "debate_results_keys": list(state.get("debate_results", {}).keys()) if isinstance(state.get("debate_results"), dict) else [],
            "governance_results_keys": list(state.get("governance_results", {}).keys()) if isinstance(state.get("governance_results"), dict) else [],
            "capabilities_used": results.get("capabilities_used", []),
            "capabilities_missing": results.get("capabilities_missing", []),
            "timestamp": datetime.now().isoformat(),
        }

        if state:
            non_empty = sum(
                1 for v in state.values()
                if v is not None and v != "" and v != [] and v != {}
            )
            metrics["non_empty_fields"] = non_empty
            metrics["total_fields"] = len(state)

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


async def main():
    import asyncio
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
            result = await run_workflow_on_text(text, doc_id, workflow_name)

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
    import asyncio
    asyncio.run(main())

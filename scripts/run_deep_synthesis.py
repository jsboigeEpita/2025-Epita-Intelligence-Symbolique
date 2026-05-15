"""Deep Synthesis runner — produces 9-section grounded markdown reports (#534).

Runs the spectacular (or conversational) workflow on a source from the
encrypted dataset, then invokes DeepSynthesisAgent to produce a multi-page
markdown analysis under outputs/deep_analysis/ (gitignored).

Usage:
    # Run on a specific source from the encrypted dataset
    python scripts/run_deep_synthesis.py --source src0_ext0

    # Run on raw text (for testing)
    python scripts/run_deep_synthesis.py --text "Some argumentative text to analyze..."

    # Choose workflow
    python scripts/run_deep_synthesis.py --source src0_ext0 --workflow conversational

    # Specify output path
    python scripts/run_deep_synthesis.py --source src0_ext0 --output outputs/deep_analysis/custom.md
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

OUTPUT_DIR = Path("outputs/deep_analysis")


async def run_from_source(source_id: str, workflow: str = "spectacular") -> dict:
    """Run full workflow + deep synthesis on a dataset source."""
    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.environment import ensure_environment

    ensure_environment()

    # Load text from encrypted dataset
    definitions = load_extract_definitions()
    text = None
    source_meta = {}
    for source in definitions:
        for extract in source.get("extracts", []):
            eid = f"src{source.get('source_num', '?')}_ext{extract.get('extract_num', '?')}"
            if eid == source_id:
                text = extract.get("full_text", "") or extract.get("text", "")
                source_meta = {
                    "opaque_id": source_id,
                    "era": extract.get("era", ""),
                    "language": extract.get("language", ""),
                    "discourse_type": extract.get("discourse_type", ""),
                }
                break
        if text:
            break

    if not text:
        available = set()
        for s in definitions:
            for e in s.get("extracts", []):
                available.add(f"src{s.get('source_num', '?')}_ext{e.get('extract_num', '?')}")
        print(f"ERROR: Source '{source_id}' not found. Available: {sorted(available)}")
        sys.exit(1)

    print(f"Source: {source_id} ({len(text)} chars)")
    return await run_on_text(text, source_meta, workflow)


async def run_on_text(
    text: str,
    source_meta: Optional[dict] = None,
    workflow: str = "spectacular",
) -> dict:
    """Run workflow + deep synthesis on raw text."""
    from argumentation_analysis.orchestration.invoke_callables import _invoke_deep_synthesis
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    source_meta = source_meta or {"opaque_id": "inline_text", "era": "", "language": "", "discourse_type": ""}

    # Build a populated state from the spectacular pipeline
    print(f"Running {workflow} workflow...")
    start = time.time()

    state = UnifiedAnalysisState(text)

    if workflow == "spectacular":
        try:
            from argumentation_analysis.orchestration.unified_pipeline import UnifiedPipeline
            pipeline = UnifiedPipeline()
            pipeline.setup_registry()
            results = await pipeline.run_unified_analysis(
                text=text,
                workflow_name="spectacular",
                source_id=source_meta.get("opaque_id", "unknown"),
            )
            # Extract the state from pipeline results
            if isinstance(results, dict):
                state = results.get("unified_state", results.get("state", state))
                if not isinstance(state, UnifiedAnalysisState):
                    state = UnifiedAnalysisState(text)
        except Exception as e:
            print(f"WARNING: Pipeline run failed ({e}), using empty state")
    elif workflow == "conversational":
        try:
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )
            results = await run_conversational_analysis(
                text=text,
                source_id=source_meta.get("opaque_id", "unknown"),
                spectacular=True,
            )
            state = results.get("unified_state", state)
        except Exception as e:
            print(f"WARNING: Conversational run failed ({e}), using empty state")

    pipeline_duration = time.time() - start
    print(f"Workflow completed in {pipeline_duration:.1f}s")

    # Run deep synthesis
    print("Running deep synthesis...")
    ctx = {
        "_state_object": state,
        "source_metadata": source_meta,
    }
    ds_result = await _invoke_deep_synthesis("", ctx)

    if "error" in ds_result:
        print(f"ERROR: Deep synthesis failed: {ds_result['error']}")
        sys.exit(1)

    ds_result["pipeline_duration_s"] = pipeline_duration
    return ds_result


def main():
    parser = argparse.ArgumentParser(
        description="Run DeepSynthesisAgent on a corpus source or raw text"
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", help="Source ID from encrypted dataset (e.g. src0_ext0)")
    source_group.add_argument("--text", help="Raw text to analyze")
    parser.add_argument(
        "--workflow",
        choices=["spectacular", "conversational"],
        default="spectacular",
        help="Workflow to run before deep synthesis (default: spectacular)",
    )
    parser.add_argument("--output", help="Output markdown file path")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.source:
        result = asyncio.run(run_from_source(args.source, args.workflow))
    else:
        meta = {"opaque_id": "inline", "era": "", "language": "", "discourse_type": ""}
        result = asyncio.run(run_on_text(args.text, meta, args.workflow))

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        opaque = "inline"
        if args.source:
            opaque = args.source
        out_path = OUTPUT_DIR / f"{opaque}_{ts}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write markdown
    markdown = result.get("markdown", "")
    out_path.write_text(markdown, encoding="utf-8")

    # Summary
    print(f"\n{'='*60}")
    print(f"Deep Synthesis Report")
    print(f"{'='*60}")
    print(f"Output: {out_path}")
    print(f"Sections: {result.get('sections_populated', '?')}/9")
    print(f"State fields consumed: {result.get('total_state_fields', '?')}")
    print(f"Markdown length: {len(markdown)} chars")
    print(f"Pipeline duration: {result.get('pipeline_duration_s', '?')}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

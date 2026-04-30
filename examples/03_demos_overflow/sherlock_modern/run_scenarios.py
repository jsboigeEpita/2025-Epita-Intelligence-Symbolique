#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sherlock Modern scenarios on encrypted dataset (#360).

Runs 3 investigation scenarios using opaque IDs only.
No plaintext content is logged or committed.

Usage:
    python examples/03_demos_overflow/sherlock_modern/run_scenarios.py
"""

import asyncio
import json
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

SCENARIOS = [
    {
        "id": "scenario_1",
        "document_id": "doc_A",
        "query": "Identify rhetorical strategies and fallacy patterns",
        "expected": ">=2 fallacies detected, >=1 hypothesis retracted",
    },
    {
        "id": "scenario_2",
        "document_id": "doc_B",
        "query": "Cross-examine argument quality and counter-arguments",
        "expected": "Quality score <=5/10, >=1 counter-argument generated",
    },
    {
        "id": "scenario_3",
        "document_id": "doc_C",
        "query": "Full investigation with hypothesis branching",
        "expected": ">=3 hypotheses, >=1 coherent, >=1 incoherent",
    },
]


def _load_dataset_text(doc_id: str) -> str:
    """Load text from encrypted dataset by opaque ID.

    Returns sample text if dataset is unavailable (tests/demo mode).
    """
    try:
        from argumentation_analysis.core.io_manager import load_extract_definitions
        from argumentation_analysis.core.environment import (
            get_encrypted_config_path,
            get_encryption_key,
        )

        config_path = get_encrypted_config_path()
        key = get_encryption_key()
        if config_path and key:
            definitions = load_extract_definitions(config_path, key)
            idx = hash(doc_id) % max(len(definitions), 1)
            if definitions:
                entry = definitions[idx]
                text = entry.get("text", entry.get("full_text", ""))
                if text:
                    return text
    except Exception:
        pass

    return (
        "Speaker attributes responsibility for economic failure to the opposition. "
        "Uses ad hominem attacks and hasty generalizations without citing evidence. "
        "Multiple appeals to emotion despite factual counter-evidence available."
    )


async def run_scenario(scenario: dict) -> dict:
    """Run a single investigation scenario."""
    from argumentation_analysis.orchestration.open_domain_investigation import (
        OpenDomainInvestigator,
    )

    text = _load_dataset_text(scenario["document_id"])
    investigator = OpenDomainInvestigator()
    result = await investigator.investigate_document(
        discourse=text,
        document_id=scenario["document_id"],
    )

    return {
        "scenario_id": scenario["id"],
        "document_id": scenario["document_id"],
        "query": scenario["query"],
        "expected": scenario["expected"],
        "actual": {
            "claims_analyzed": result.claims_analyzed,
            "active_hypotheses": len(result.hypothesis_summary),
            "reasoning_steps": len(result.reasoning_trace),
            "attributions": len(result.attributions),
            "conclusion_length": len(result.conclusion),
        },
        "hypothesis_summary": result.hypothesis_summary,
        "reasoning_trace": result.reasoning_trace,
    }


async def run_all():
    """Run all scenarios and display results."""
    print("=" * 60)
    print(" Sherlock Modern — Investigation Scenarios (#360)")
    print(" Opaque IDs only — no plaintext content")
    print("=" * 60)

    results = []
    for scenario in SCENARIOS:
        print(f"\n--- {scenario['id']}: {scenario['document_id']} ---")
        print(f"  Query: {scenario['query']}")
        print(f"  Expected: {scenario['expected']}")

        try:
            result = await run_scenario(scenario)
            results.append(result)

            print(f"  Claims: {result['actual']['claims_analyzed']}")
            print(f"  Hypotheses: {result['actual']['active_hypotheses']}")
            print(f"  Reasoning steps: {result['actual']['reasoning_steps']}")
            print(f"  Attributions: {result['actual']['attributions']}")
            print(f"  Status: COMPLETED")
        except Exception as e:
            print(f"  Error: {e}")
            print(f"  Status: FAILED")

    print("\n" + "=" * 60)
    print(f" Completed {len(results)}/{len(SCENARIOS)} scenarios")
    print("=" * 60)

    return results


if __name__ == "__main__":
    results = asyncio.run(run_all())
    sys.exit(0 if results else 1)

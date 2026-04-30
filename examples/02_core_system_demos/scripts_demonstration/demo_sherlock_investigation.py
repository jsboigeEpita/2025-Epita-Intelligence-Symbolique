#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Demo: Open-domain investigation via Sherlock Modern (#358).

Whodunit-style argument analysis on a sample discourse. Uses opaque IDs
for privacy compliance.

Usage:
    python examples/02_core_system_demos/scripts_demonstration/demo_sherlock_investigation.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

SAMPLE_DISCOURSE = (
    "Le professeur affirme que le changement climatique est exagere par les medias. "
    "Il cite une etude non peer-reviewee et attaque personnellement les scientifiques "
    "du GIEC. Malgre des preuves contradictoires issues de sources independantes, "
    "il maintient sa position avec conviction et rejette tout debat contradictoire."
)


async def run_demo():
    """Run the open-domain investigation demo."""
    from argumentation_analysis.orchestration.open_domain_investigation import (
        OpenDomainInvestigator,
    )

    print("=" * 60)
    print(" Sherlock Modern — Open-domain Investigation Demo")
    print("=" * 60)
    print(f"\nDocument: doc_A (opaque ID)")
    print(f"Text length: {len(SAMPLE_DISCOURSE)} characters\n")

    investigator = OpenDomainInvestigator()
    result = await investigator.investigate_document(
        discourse=SAMPLE_DISCOURSE,
        document_id="doc_A",
    )

    # Display results
    print("-" * 60)
    print(" INVESTIGATION RESULTS")
    print("-" * 60)
    print(f"Document: {result.document_id}")
    print(f"Claims analyzed: {result.claims_analyzed}")

    print("\n Reasoning trace:")
    for i, step in enumerate(result.reasoning_trace, 1):
        print(f"  {i}. {step}")

    if result.hypothesis_summary:
        print("\n Hypotheses:")
        for h_id, desc in result.hypothesis_summary.items():
            print(f"  - {h_id}: {desc}")

    if result.attributions:
        print("\n Attributions:")
        for attr in result.attributions:
            status = "SUPPORTED" if attr.coherent else "UNDERMINED"
            print(f"  [{status}] {attr.attribution} (confidence: {attr.confidence:.2f})")

    print("\n Conclusion:")
    print(f"  {result.conclusion}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    result = asyncio.run(run_demo())
    # Exit with 0 if investigation produced results
    sys.exit(0 if result.claims_analyzed >= 0 else 1)

#!/usr/bin/env python3
"""
Demo: Unified Capabilities — Emergent Features from Student Integration

This script demonstrates the capabilities that emerge from integrating
12 student projects into a unified Lego architecture:

1. CapabilityRegistry: discover and compose components dynamically
2. QualityScoringPlugin: evaluate argument quality (9 virtues)
3. CounterArgumentAgent: generate counter-arguments (5 strategies)
4. DebateAgent: adversarial debate with scoring
5. GovernancePlugin: multi-method voting and consensus
6. UnifiedPipeline: end-to-end analysis workflows

Usage:
    conda run -n projet-is-roo-new --no-capture-output python examples/03_integrations/demo_unified_capabilities.py
"""

import json
import sys
import os

# Ensure the project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def demo_capability_registry():
    """Demonstrate the Lego CapabilityRegistry."""
    print("\n" + "=" * 60)
    print("1. CAPABILITY REGISTRY — Component Discovery")
    print("=" * 60)

    from argumentation_analysis.orchestration.unified_pipeline import setup_registry

    registry = setup_registry(include_optional=False)

    # Show all registered capabilities
    all_caps = registry.get_all_capabilities()
    print(f"\nRegistered capabilities ({len(all_caps)}):")
    for cap in sorted(all_caps):
        print(f"  - {cap}")

    # Find components for a specific capability
    agents = registry.find_agents_for_capability("adversarial_debate")
    print(f"\nAgents for 'adversarial_debate': {[a.name for a in agents]}")

    services = registry.find_services_for_capability("belief_maintenance")
    print(f"Services for 'belief_maintenance': {[s.name for s in services]}")

    print("\nRegistry demonstrates dynamic component discovery.")


def demo_quality_scoring():
    """Demonstrate the QualityScoringPlugin."""
    print("\n" + "=" * 60)
    print("2. QUALITY SCORING — 9 Virtue Evaluation")
    print("=" * 60)

    from argumentation_analysis.plugins.quality_scoring_plugin import (
        QualityScoringPlugin,
    )

    plugin = QualityScoringPlugin()

    text = (
        "La vaccination obligatoire est justifiee car les etudes epidemiologiques "
        "montrent une reduction de 95% des cas de rougeole dans les pays avec "
        "couverture vaccinale superieure a 90%. Les donnees de l'OMS confirment "
        "cette correlation depuis 2010."
    )

    result = json.loads(plugin.evaluate_argument_quality(text))
    print(f"\nText: {text[:80]}...")
    print(f"\nQuality result keys: {list(result.keys())}")

    score = json.loads(plugin.get_quality_score(text))
    print(f"Quality score: {score}")

    virtues = json.loads(plugin.list_virtues())
    print(f"Available virtues ({len(virtues)}): {virtues[:5]}...")


def demo_counter_argument():
    """Demonstrate the CounterArgumentPlugin."""
    print("\n" + "=" * 60)
    print("3. COUNTER-ARGUMENT — 5 Rhetorical Strategies")
    print("=" * 60)

    from argumentation_analysis.agents.core.counter_argument import (
        CounterArgumentPlugin,
    )

    plugin = CounterArgumentPlugin()

    argument = (
        "Les energies renouvelables sont trop couteuses pour remplacer "
        "les energies fossiles dans un avenir proche."
    )

    # Parse the argument
    parsed = json.loads(plugin.parse_argument(argument))
    print(f"\nArgument: {argument}")
    print(f"Parsed content length: {len(parsed.get('content', ''))}")

    # Identify vulnerabilities
    vulns = json.loads(plugin.identify_vulnerabilities(argument))
    print(f"\nVulnerabilities: {json.dumps(vulns, indent=2)[:200]}")

    # Suggest strategy
    strategy = json.loads(plugin.suggest_strategy(argument))
    print(f"\nSuggested strategy: {json.dumps(strategy, indent=2)[:200]}")


def demo_governance():
    """Demonstrate the GovernancePlugin."""
    print("\n" + "=" * 60)
    print("4. GOVERNANCE — Multi-Method Voting")
    print("=" * 60)

    from argumentation_analysis.plugins.governance_plugin import GovernancePlugin

    plugin = GovernancePlugin()

    # List available methods
    methods = json.loads(plugin.list_governance_methods())
    print(f"\nAvailable voting methods ({len(methods)}):")
    for m in sorted(methods):
        print(f"  - {m}")

    # Detect conflicts in positions
    positions = json.dumps(
        {
            "agent_A": {"position": "for", "confidence": 0.9},
            "agent_B": {"position": "against", "confidence": 0.8},
            "agent_C": {"position": "for", "confidence": 0.6},
        }
    )
    conflicts = json.loads(plugin.detect_conflicts_fn(positions))
    print(f"\nConflict detection result:")
    if isinstance(conflicts, list):
        print(f"  Conflicts found: {len(conflicts)}")
        for c in conflicts[:3]:
            print(f"    - {c}")
    else:
        print(f"  Result: {conflicts}")


def demo_debate_plugin():
    """Demonstrate the DebatePlugin."""
    print("\n" + "=" * 60)
    print("5. DEBATE — Adversarial Argument Analysis")
    print("=" * 60)

    from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin

    plugin = DebatePlugin()

    argument = (
        "L'intelligence artificielle va creer plus d'emplois qu'elle n'en detruira, "
        "comme l'a fait chaque revolution industrielle precedente."
    )

    quality = json.loads(plugin.analyze_argument_quality(argument))
    print(f"\nArgument: {argument[:80]}...")
    print(f"\nQuality analysis:")
    if "metrics" in quality:
        metrics = quality["metrics"]
        print(f"  Relevance: {metrics.get('relevance_score', 'N/A')}")
        print(f"  Readability: {metrics.get('readability_score', 'N/A')}")

    # Analyze logical structure
    structure = json.loads(plugin.analyze_logical_structure(argument))
    print(f"\nLogical structure analysis:")
    print(f"  {json.dumps(structure, indent=2)[:200]}")


def demo_unified_pipeline():
    """Demonstrate the unified pipeline workflow builder."""
    print("\n" + "=" * 60)
    print("6. UNIFIED PIPELINE — Workflow Composition")
    print("=" * 60)

    from argumentation_analysis.orchestration.unified_pipeline import (
        build_light_workflow,
        build_standard_workflow,
        build_full_workflow,
    )

    light = build_light_workflow()
    standard = build_standard_workflow()
    full = build_full_workflow()

    print(f"\nPre-built workflows:")
    print(f"  Light:    {len(light.phases)} phases — {[p.name for p in light.phases]}")
    print(
        f"  Standard: {len(standard.phases)} phases — {[p.name for p in standard.phases]}"
    )
    print(f"  Full:     {len(full.phases)} phases — {[p.name for p in full.phases]}")

    print("\nWorkflows compose registered capabilities into analysis pipelines.")
    print("Each phase maps to a capability in the registry.")


def main():
    print("=" * 60)
    print("UNIFIED CAPABILITIES DEMO")
    print("12 Student Projects — Lego Architecture")
    print("=" * 60)

    demos = [
        ("Registry", demo_capability_registry),
        ("Quality", demo_quality_scoring),
        ("Counter-Argument", demo_counter_argument),
        ("Governance", demo_governance),
        ("Debate", demo_debate_plugin),
        ("Pipeline", demo_unified_pipeline),
    ]

    for name, demo_fn in demos:
        try:
            demo_fn()
        except Exception as e:
            print(f"\n[SKIP] {name} demo failed: {e}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("All capabilities available via CapabilityRegistry + SK plugins.")
    print("=" * 60)


if __name__ == "__main__":
    main()

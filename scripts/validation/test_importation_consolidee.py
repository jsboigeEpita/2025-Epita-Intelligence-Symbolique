#!/usr/bin/env python3
import argumentation_analysis.core.environment

"""
Test d'importation consolidée : les symboles dont dépend le système s'importent.

Chaque vérification importe un module et lit un symbole. Le script rend 1 dès
qu'une vérification échoue.

#2532 : la version précédente affichait « ✅ Modules critiques opérationnels »
et « Prêt pour tests complets Phase 3 » quels que soient ses résultats, et
rendait toujours 0. Trois de ses symboles n'avaient jamais existé dans le module
interrogé (`generate_unified_report`, `ReportingPipeline`, `load_config` :
`git log -S` ne trouve aucune définition), et un quatrième nommait un module
supprimé. Les vérifications nomment désormais les symboles réels.

Ce script vérifie des symboles. Le garde
`tests/unit/test_web_lane_imports_resolve_2529.py` vérifie les modules.
"""

import importlib
import sys

# (section, module, symbole)
CHECKS = [
    (
        "Modules critiques",
        "argumentation_analysis.agents.core.logic.fol_logic_agent",
        "FOLLogicAgent",
    ),
    (
        "Modules critiques",
        "argumentation_analysis.utils.report_generator",
        "generate_markdown_performance_report",
    ),
    (
        "Modules critiques",
        "argumentation_analysis.orchestration.unified_pipeline",
        "run_unified_analysis",
    ),
    ("Modules critiques", "config.unified_config", "UnifiedConfig"),
    ("Rapports", "argumentation_analysis.reporting.models", None),
    (
        "Rapports",
        "argumentation_analysis.pipelines.reporting_pipeline",
        "run_comprehensive_report_pipeline",
    ),
    (
        "Orchestration et agents",
        "argumentation_analysis.orchestration.cluedo_orchestrator",
        "CluedoOrchestrator",
    ),
    (
        "Orchestration et agents",
        "argumentation_analysis.agents.core.informal.informal_agent",
        "InformalAnalysisAgent",
    ),
    (
        "Services et utilitaires",
        "argumentation_analysis.services.logic_service",
        "LogicService",
    ),
    (
        "Services et utilitaires",
        "argumentation_analysis.utils.config_utils",
        "find_sources_in_config_by_ids",
    ),
    (
        "Hiérarchie",
        "argumentation_analysis.orchestration.hierarchical.tactical.coordinator",
        "TacticalCoordinator",
    ),
    (
        "Hiérarchie",
        "argumentation_analysis.orchestration.hierarchical.operational.manager",
        "OperationalManager",
    ),
    (
        "Analyse",
        "argumentation_analysis.plugins.analysis_tools.logic.rhetorical_result_analyzer",
        "EnhancedRhetoricalResultAnalyzer",
    ),
]


def check(module_name, symbol):
    module = importlib.import_module(module_name)
    if symbol is not None:
        getattr(module, symbol)


def test_critical_imports():
    """Rend la liste des vérifications en échec (vide si tout passe)."""
    print("=== TEST IMPORTATION CONSOLIDÉE ===")
    print(f"Python version: {sys.version}")

    failures = []
    section = None
    for current, module_name, symbol in CHECKS:
        if current != section:
            section = current
            print(f"\n{section}:")
        label = f"{module_name}.{symbol}" if symbol else module_name
        try:
            check(module_name, symbol)
            print(f"✅ {label}")
        except Exception as e:
            print(f"❌ {label}: {e}")
            failures.append(label)

    print("\nCohérence:")
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        summary = setup_registry().summary()
        print(
            f"✅ setup_registry : {summary['agents']} agents, "
            f"{summary['plugins']} plugins, {summary['services']} services"
        )
    except Exception as e:
        print(f"❌ setup_registry: {e}")
        failures.append("setup_registry")

    total = len(CHECKS) + 1
    print(f"\n=== {total - len(failures)}/{total} vérifications réussies ===")
    for label in failures:
        print(f"❌ {label}")
    return failures


if __name__ == "__main__":
    sys.exit(1 if test_critical_imports() else 0)

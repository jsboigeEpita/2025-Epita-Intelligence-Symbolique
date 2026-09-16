"""Né-rouge guards for #2270 — the production (no-registry) injection path.

Measured on the pristine tree (base ``295ff1f1``): both production
constructors of ``FactCheckingOrchestrator`` (its own singleton factory and
``service_manager``) pass no ``plugin_registry``. On that path
``self.taxonomy_plugin = get_taxonomy_manager()`` injects the
``FallacyTaxonomyManager`` **service** — which lacks the surface
``FallacyFamilyAnalyzer`` consumes (``await detect_and_classify(...)`` and
``families.get(...)`` — the service's ``families`` is a ``set``). Every
analysis routed to fact-checking (7 analysis types via
``service_manager._select_orchestrator``) dies with ``AttributeError`` at
step 3 of ``analyze_comprehensive``. The ``Optional[TaxonomyExplorerPlugin]``
annotation described a runtime that only exists when tests inject the real
plugin — the taxonomy half of the #2101 lying-annotation fix.
"""

import pytest


@pytest.fixture
def production_orchestrator():
    """Built exactly the way production builds it: no plugin_registry."""
    from argumentation_analysis.orchestration.fact_checking_orchestrator import (
        FactCheckingOrchestrator,
    )

    return FactCheckingOrchestrator(api_config={})


def test_production_injection_carries_the_consumed_surface(production_orchestrator):
    tp = production_orchestrator.family_analyzer.taxonomy_plugin
    assert hasattr(tp, "detect_and_classify"), (
        "the no-registry production path injects the FallacyTaxonomyManager "
        "service, which has no detect_and_classify (#2270)"
    )
    assert hasattr(
        tp.families, "get"
    ), "families must be a mapping (plugin surface) — the service carries a set"


async def test_production_analysis_completes_to_classification(
    production_orchestrator,
):
    from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
        AnalysisDepth,
    )

    result = await production_orchestrator.family_analyzer.analyze_comprehensive(
        text="Tout le monde dit que c'est vrai, donc c'est forcément vrai.",
        depth=AnalysisDepth.BASIC,
    )
    assert "error" not in result.overall_assessment, (
        "analyze_comprehensive swallowed an exception into its degraded result "
        "(broad except → overall_assessment={'error': ...}) — the no-registry "
        "production path never reaches classification (#2270)"
    )


def test_analyzer_default_construction_is_the_real_plugin():
    from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
        FallacyFamilyAnalyzer,
    )
    from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import (
        TaxonomyExplorerPlugin,
    )

    analyzer = FallacyFamilyAnalyzer(api_config={})
    assert isinstance(
        analyzer.taxonomy_plugin, TaxonomyExplorerPlugin
    ), "the default injection must be the plugin the annotation promises (#2270)"

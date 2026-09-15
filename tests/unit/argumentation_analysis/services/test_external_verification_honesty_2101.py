"""Né-rouge guards for #2101 — honesty of the external-verification chain.

Measured on the pristine tree (base ``9dc3fd86``):

* The production chain is ``service_manager`` → ``FactCheckingOrchestrator``
  (no plugin registry) → the **service shims**
  (``services/fact_verification_service.py`` returning UNVERIFIABLE stubs,
  ``services/fallacy_taxonomy_service.py`` delegating to the detector).
  ``ExternalVerificationPlugin`` is **never constructed anywhere** — it is
  imported for a type annotation (``fallacy_family_analyzer.py:129``) whose
  runtime object is actually the shim, plus one dead import in the
  orchestrator (:31-33).
* The plugin's searches are fabricated fixtures (``example-tavily.com``,
  ``example-searxng.com``) returned **even when API keys are configured** —
  the dishonest theater #2101 item 1.
* ``import aiohttp`` (:8) is dead (declared in ``plugin.yaml:13`` for
  nothing); ``taxonomy_plugin`` (:125/:142) is injected then never consumed.
* The enums ``VerificationStatus``/``SourceReliability`` are duplicated with
  **inverted reliability maps** between the plugin and the service shim —
  and no third file imports either, so the shim (the measured production
  surface) becomes the single source.
* Both shim docstrings claim to delegate to plugins they never import.

The repair assumes the simulation loudly (no real network wiring — that is a
separate arbitration, audit C-06 E1), removes the dead weight, and points
every consumer at the truth.
"""

import logging
from pathlib import Path

import pytest

from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
    ClaimType,
    ClaimVerifiability,
    FactualClaim,
)
import argumentation_analysis.plugin_framework.core.plugins.standard.external_verification.plugin as ev_plugin
import argumentation_analysis.services.fact_verification_service as fv_service

REPO_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_PY = (
    REPO_ROOT
    / "argumentation_analysis"
    / "plugin_framework"
    / "core"
    / "plugins"
    / "standard"
    / "external_verification"
    / "plugin.py"
)
PLUGIN_YAML = PLUGIN_PY.parent / "plugin.yaml"
ORCHESTRATOR_PY = (
    REPO_ROOT
    / "argumentation_analysis"
    / "orchestration"
    / "fact_checking_orchestrator.py"
)
ANALYZER_PY = (
    REPO_ROOT
    / "argumentation_analysis"
    / "agents"
    / "tools"
    / "analysis"
    / "fallacy_family_analyzer.py"
)
SHIM_VERIF = (
    REPO_ROOT / "argumentation_analysis" / "services" / "fact_verification_service.py"
)
SHIM_TAXO = (
    REPO_ROOT / "argumentation_analysis" / "services" / "fallacy_taxonomy_service.py"
)


def _claim() -> FactualClaim:
    return FactualClaim(
        claim_text="En 2023, 50% des français utilisent internet",
        claim_type=ClaimType.STATISTICAL,
        verifiability=ClaimVerifiability.HIGHLY_VERIFIABLE,
        confidence=0.9,
        context="",
        start_pos=0,
        end_pos=10,
        entities=[],
        keywords=[],
        temporal_references=[],
        numerical_values=[],
        sources_mentioned=[],
        extraction_method="guard",
    )


def _make_plugin(api_config=None):
    """Post-fix the ctor takes no taxonomy plugin; pristine needed one
    (never consumed) — the fallback keeps the né-rouge measurable."""
    try:
        return ev_plugin.ExternalVerificationPlugin(api_config=api_config)
    except TypeError:
        return ev_plugin.ExternalVerificationPlugin(
            taxonomy_plugin=object(), api_config=api_config
        )


def test_plugin_constructs_without_unused_taxonomy_injection_2101():
    plugin = ev_plugin.ExternalVerificationPlugin(api_config={})
    assert not hasattr(plugin, "taxonomy_plugin"), (
        "taxonomy_plugin was injected then never consumed (#2101 item 3) — "
        "the dead dependency must not force callers to provide it"
    )


@pytest.mark.asyncio
async def test_simulated_search_is_loud_and_not_per_provider_2101(caplog):
    """With API keys configured, the plugin must not hand back per-provider
    fixtures implying the provider was queried."""
    plugin = _make_plugin(
        api_config={"tavily_api_key": "test-key", "searxng_url": "http://example.org"}
    )
    with caplog.at_level(logging.WARNING, logger="ExternalVerificationPlugin"):
        results = await plugin.verify_claims([_claim()])
    assert len(results) == 1
    domains = [s.domain for s in results[0].sources]
    fabricated = [
        d
        for d in domains
        if d.startswith("example-tavily") or d.startswith("example-searxng")
    ]
    assert not fabricated, (
        f"provider-shaped fixtures returned while keys are configured: {fabricated} "
        "(#2101 item 1 — simulated results must not masquerade as provider output)"
    )
    assert any(
        "SIMULÉ" in r.message or "simulated" in r.message.lower()
        for r in caplog.records
    ), (
        "the simulation must be announced loudly (WARNING) when API keys are "
        "configured — silence is the #1019 theater pattern"
    )


def test_dead_aiohttp_dependency_is_gone_2101():
    assert "import aiohttp" not in PLUGIN_PY.read_text(encoding="utf-8")
    assert "aiohttp" not in PLUGIN_YAML.read_text(encoding="utf-8")


def test_enums_have_a_single_source_the_service_2101():
    """The shim is the measured production surface — the plugin must consume
    its enums, not redefine divergent twins (#2101 item 4)."""
    source = PLUGIN_PY.read_text(encoding="utf-8")
    assert "class VerificationStatus" not in source
    assert "class SourceReliability" not in source
    assert ev_plugin.VerificationStatus is fv_service.VerificationStatus
    assert ev_plugin.SourceReliability is fv_service.SourceReliability


def test_shims_do_not_claim_plugin_delegation_2101():
    verif = SHIM_VERIF.read_text(encoding="utf-8")
    taxo = SHIM_TAXO.read_text(encoding="utf-8")
    assert "déléguant au plugin ExternalVerificationPlugin" not in verif, (
        "fact_verification_service imports no plugin — its docstring must not "
        "claim delegation (#2101 item 5)"
    )
    assert "plugin TaxonomyExplorerPlugin" not in taxo, (
        "fallacy_taxonomy_service delegates to the detector, not to the "
        "TaxonomyExplorerPlugin it never imports (#2101 item 5)"
    )


def test_consumers_stop_importing_the_never_constructed_plugin_2101():
    """The orchestrator's import is dead; the analyzer's annotation lies
    about the runtime object (the shim). Both must use the structural truth."""
    orch = ORCHESTRATOR_PY.read_text(encoding="utf-8")
    ana = ANALYZER_PY.read_text(encoding="utf-8")
    assert "external_verification.plugin" not in orch, (
        "fact_checking_orchestrator imports ExternalVerificationPlugin and "
        "never uses the name — a dead import of a never-constructed class"
    )
    assert "external_verification.plugin" not in ana, (
        "fallacy_family_analyzer types its verification_plugin parameter as "
        "ExternalVerificationPlugin while the runtime object is the service "
        "shim — the annotation must be structural"
    )

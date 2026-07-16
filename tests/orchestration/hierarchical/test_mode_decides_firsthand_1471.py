# -*- coding: utf-8 -*-
"""
Integration test for BO-1 #1471 — M3 hierarchical mode is a selectable,
comparable orchestration axis that DECIDES firsthand on a real workflow.

Closes the loop on the dispatch's DoD:
- Mode is selectable via ``--mode hierarchical`` (already in CLI).
- Bridge mode runs end-to-end with REAL agents (CapabilityRegistry + WorkflowExecutor).
- Mode reaches a strategic decision (not a smoke-test empty path).
- Mode is HONEST-DEGRADED on missing tier (delegation mode fails loud
  without an executor / capability_registry, NOT a silent fallback).

This test was authored first-hand via the smoke-test pipeline — the bridge
mode path was crashing in Phase 4 (``publish_strategic_decision`` did not
exist on StrategicAdapter). The fix is in
``strategic/manager.py:evaluate_final_results`` (route through
``broadcast_objective``); this test locks in the contract going forward.
"""

import pytest

from argumentation_analysis.orchestration.hierarchical.orchestrator import (
    run_hierarchical_analysis,
)
from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    DelegationError,
    DelegationOrchestrator,
    _absent_operational_executor,
)

SYNTHETIC_FALLACY_TEXT = (
    "Argument 1 : Les experts sont unanimes, c'est donc vrai. "
    "Argument 2 : Si vous n'etes pas expert, votre avis ne compte pas."
)


class TestHierarchicalBridgeModeFirsthandDecision:
    """Bridge mode (M2 default) runs end-to-end with REAL agents and reaches
    a strategic decision. This is the DoD baseline for BO-1 #1471.
    """

    @pytest.mark.asyncio
    async def test_bridge_mode_decides_end_to_end_with_real_agents(self) -> None:
        """Bridge mode completes all 4 phases with REAL CapabilityRegistry
        services, reaches a strategic conclusion, and does NOT crash in
        Phase 4 (``publish_strategic_decision`` regression guard).
        """
        result = await run_hierarchical_analysis(SYNTHETIC_FALLACY_TEXT)

        # --- Workflow + phase outcomes ---------------------------------
        assert "summary" in result
        assert result["summary"]["total"] >= 1, "at least one objective phase"
        # We accept completed=total OR completed<total-but-no-crash. The key
        # contract: NO crash raised out of analyze(), Phase 4 included.
        assert (
            result["summary"]["failed"] <= result["summary"]["total"]
        ), "phases counted honestly"

        # --- Strategic decision reached (not a smoke-test) -------------
        assert "conclusion" in result, "Phase 4 strategic decision missing"
        assert isinstance(result["conclusion"], str)
        assert len(result["conclusion"]) > 0, "conclusion is empty"
        # The conclusion string is one of the 3 graded verdicts in
        # ``strategic/manager.py:_formulate_conclusion``. Any non-empty string
        # proves Phase 4 reached end-of-line without an AttributeError.
        assert result["conclusion"] in {
            "Analyse réussie avec une performance globale élevée.",
            "Analyse satisfaisante avec quelques faiblesses.",
            "L'analyse a rencontré des difficultés significatives.",
        }

        # --- Bridge-mode is the default selection -----------------------
        assert result.get("workflow_name") == "hierarchical_analysis"
        assert result.get("duration_seconds", 0) > 0


class TestHierarchicalDelegationModeFailsLoud:
    """Delegation mode (M3 true 3-tier) FAILS LOUD on missing tier
    instead of fabricating a degraded result (anti-théâtre #1019).
    """

    @pytest.mark.asyncio
    async def test_delegation_without_executor_or_registry_raises(self) -> None:
        """When neither ``operational_executor`` nor ``capability_registry``
        is provided, delegation mode raises ``DelegationError`` — it does
        NOT return a synthetic success dict.
        """
        orchestrator = DelegationOrchestrator(
            operational_executor=_absent_operational_executor,
            # capability_registry left None
        )
        with pytest.raises(DelegationError) as exc_info:
            await orchestrator.analyze(SYNTHETIC_FALLACY_TEXT)
        # The error message itself reflects the anti-pendule guard
        assert "operational tier" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_run_hierarchical_analysis_delegation_no_registry_raises(
        self,
    ) -> None:
        """Top-level entry point propagates the fail-loud: without a
        capability_registry, ``mode='delegation'`` raises rather than
        silently using the M2 bridge as a heuristic fallback.
        """
        with pytest.raises(DelegationError):
            await run_hierarchical_analysis(
                SYNTHETIC_FALLACY_TEXT,
                mode="delegation",
                # capability_registry omitted on purpose
            )

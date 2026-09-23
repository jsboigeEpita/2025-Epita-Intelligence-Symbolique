# -*- coding: utf-8 -*-
"""#2344 — hierarchical bridge: the silent 4-objective injection is gone.

The M2 bridge used to mask a StrategicManager returning zero objectives by
injecting an untagged hardcoded 4-objective set — the silent-fallback shape
delegation mode has refused since its creation (anti-pendule, #1019). The
manager's contract guarantees a non-empty set: every degradation path inside
``_define_initial_objectives`` / ``_generate_llm_objectives`` lands on
``_fallback_objectives()``, tagged ``source="degraded"`` and logged. So an
empty list at the bridge means the strategic tier is broken — it must fail
loud, not fabricate untagged objectives (doctrine #1019, tri-état #2344).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.orchestration.hierarchical.orchestrator import (
    HierarchicalOrchestrator,
)


class _ContractViolatingManager:
    """Strategic tier stub that returns ZERO objectives (contract violation)."""

    def initialize_analysis(self, text):
        return {"objectives": [], "strategic_plan": {}}


class _DegradedManager:
    """Strategic tier stub mirroring the manager's tagged degraded fallback.

    The description intentionally matches no keyword of the bridge's
    ``_OBJECTIVE_CAPABILITY_MAP`` so the workflow builds through the
    deterministic optional-generic-phase branch.
    """

    def initialize_analysis(self, text):
        return {
            "objectives": [
                {
                    "id": "obj-1",
                    "description": "Objectif générique sans mot-clé",
                    "priority": "high",
                    "source": "degraded",
                }
            ],
            "strategic_plan": {},
        }

    def evaluate_final_results(self, eval_input):
        return {"conclusion": "Analyse : conclusion de test.", "evaluation": {}}


def _orchestrator_with(manager) -> HierarchicalOrchestrator:
    return HierarchicalOrchestrator(
        capability_registry=MagicMock(name="capability_registry"),
        strategic_manager=manager,
    )


class TestEmptyObjectivesFailLoud:
    """Zero objectives from the strategic tier raise instead of being masked."""

    @pytest.mark.asyncio
    async def test_zero_objectives_raise_instead_of_silent_injection(self):
        orchestrator = _orchestrator_with(_ContractViolatingManager())
        with pytest.raises(RuntimeError, match="no objectives"):
            await orchestrator.analyze("Texte argumentatif de test.")


class TestDegradedTagTravelsThroughTheBridge:
    """Objectives tagged by the manager keep their tag in the bridge result.

    Locks the item-18 side: the degradation is named at the source
    (``source='degraded'``) and the bridge result must not launder it back
    into indistinguishable-from-normal objectives.
    """

    @pytest.mark.asyncio
    async def test_degraded_objectives_keep_their_tag_in_the_result(self):
        orchestrator = _orchestrator_with(_DegradedManager())
        with patch(
            "argumentation_analysis.orchestration.workflow_dsl.WorkflowExecutor.execute",
            new=AsyncMock(return_value={}),
        ) as mock_execute:
            result = await orchestrator.analyze("Texte argumentatif de test.")

        mock_execute.assert_awaited_once()
        assert result["objectives"], "objectives must reach the result"
        sources = [obj.get("source") for obj in result["objectives"]]
        assert "degraded" in sources, f"laundered by the bridge: {sources}"

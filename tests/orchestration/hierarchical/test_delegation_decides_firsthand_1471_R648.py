# -*- coding: utf-8 -*-
"""
Integration test for BO-1 #1471 continuation (R648) — delegation mode
(M3 true 3-tier) DECIDES firsthand on `hierarchical_fallacy` once the
legacy→registry capability mapping + dict/str signature normalisation
are applied in ``make_registry_operational_executor``.

The dispatch's stated diagnostic ("contrat dict/str dans
_invoke_hierarchical_fallacy_per_argument") was imprecise: the actual
root cause was that ``make_registry_operational_executor`` (a) never
bridged legacy capability names hardcoded in
``TaskCoordinator.agent_capabilities`` (coordinator.py:79-92) to the
canonical registry capability names, and (b) passed a dict as
``input_text`` to providers whose signatures declare
``(input_text: str, context: Dict)``. Both seams are now bridged; this
test is the regression guard.
"""

import pytest

from typing import Any, Dict

from argumentation_analysis.orchestration.hierarchical.orchestrator import (
    run_hierarchical_analysis,
)
from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    LEGACY_TO_REGISTRY_CAPABILITY,
    make_registry_operational_executor,
)
from argumentation_analysis.orchestration.registry_setup import setup_registry

SYNTHETIC_FALLACY_TEXT = (
    "Argument 1 : Les experts sont unanimes, c'est donc vrai. "
    "Argument 2 : Si vous n'etes pas expert, votre avis ne compte pas."
)


class TestDelegationModeDecidesFirsthand:
    """Delegation mode (M3) DECIDES firsthand on hierarchical_fallacy
    when wired against the CapabilityRegistry.

    Five tactical tasks get decomposed from the synthetic scenario.
    Before the R648 fix only the ``fallacy_detection`` task had a
    registry provider (1/5 completed, conclusion "difficultés
    significatives"). After the fix, every task's required_capabilities
    is mapped to a real provider via LEGACY_TO_REGISTRY_CAPABILITY (or
    via _OBJECTIVE_CAPABILITY_MAP fallback for generic tasks), so 5/5
    complete and the verdict reads "performance globale élevée".
    """

    @pytest.mark.asyncio
    async def test_delegation_mode_decides_end_to_end_with_real_agents(self) -> None:
        """5/5 operational tasks complete; conclusion is a graded verdict.

        Honnête-partiel: this assumes the test environment has a populated
        ``setup_registry()`` (i.e. ``include_optional=True``). The
        synthesis conclusion is one of the three graded verdicts in
        ``strategic/manager.py:_formulate_conclusion``; we assert that
        set membership AND the underlying success_rate moves from 0.25
        pre-fix to >=0.80 post-fix.
        """
        registry = setup_registry(include_optional=True)
        result = await run_hierarchical_analysis(
            SYNTHETIC_FALLACY_TEXT,
            capability_registry=registry,
            mode="delegation",
        )

        # --- All 5 tasks completed via real registry providers ---------
        ops = result.get("operational_results", [])
        assert len(ops) == 5, f"expected 5 tasks, got {len(ops)}"
        completed = [op for op in ops if op.get("status") == "completed"]
        assert len(completed) >= 4, (
            f"delegation should drive at least 4/5 tasks to completion, "
            f"got {len(completed)}/5 (pre-R648: 1/5)"
        )

        # --- Every completed task used a registry-backed capability ----
        for op in completed:
            cap = op.get("capability")
            assert cap, f"completed task missing capability: {op}"
            providers = registry.find_for_capability(cap)
            assert providers, (
                f"completed task claimed capability {cap!r} but registry "
                f"has no provider for it (anti-théâtre #1019)"
            )

        # --- Strategic decision reached + graded verdict --------------
        assert "conclusion" in result
        assert result["conclusion"] in {
            "Analyse réussie avec une performance globale élevée.",
            "Analyse satisfaisante avec quelques faiblesses.",
        }, (
            f"conclusion {result['conclusion']!r} is degraded — R648 fix "
            f"did not lift delegation mode out of 'difficultés'"
        )
        eval_block = result.get("evaluation", {}).get("objectives_evaluation", {})
        assert eval_block.get("obj-2", {}).get("success_rate", 0) >= 0.5, (
            "obj-2 (Détecter les sophismes) must succeed — this is the "
            "hierarchical_fallacy north-star"
        )

    def test_legacy_to_registry_capability_mapping_is_well_formed(self) -> None:
        """The mapping is a pure data structure — every key resolves to a
        non-empty string. Anything fancier (auto-discovery, dynamic
        introspection) is out of scope; the table is hand-curated and
        intentional (anti-pendule #1019: no fabricated entries).
        """
        for legacy, registry_cap in LEGACY_TO_REGISTRY_CAPABILITY.items():
            assert isinstance(legacy, str) and legacy
            assert isinstance(registry_cap, str) and registry_cap

    def test_registry_operational_executor_bridges_legacy_text_extraction(
        self,
    ) -> None:
        """The legacy ``text_extraction`` capability used by the
        ``extract_processor`` agent (coordinator.py:79-92) has no
        provider in the registry. ``make_registry_operational_executor``
        must route it through LEGACY_TO_REGISTRY_CAPABILITY to a real
        provider (``fact_extraction``), instead of returning
        ``no_provider_for_required_capabilities``.
        """
        registry = setup_registry(include_optional=True)
        # text_extraction MUST be absent from the registry (sanity check).
        assert not registry.find_for_capability("text_extraction")
        # fact_extraction MUST be present (target of the mapping).
        assert registry.find_for_capability("fact_extraction")

        executor = make_registry_operational_executor(registry)
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            executor(
                {
                    "tactical_task_id": "t-test-legacy",
                    "objective_id": "obj-legacy-test",
                    "description": "Extraire segments pertinents",
                    "required_capabilities": ["text_extraction"],
                    "context": {},
                }
            )
        )
        assert result["status"] == "completed", (
            f"legacy text_extraction should route via fact_extraction, " f"got {result}"
        )
        assert result["capability"] == "fact_extraction"


class TestDelegationModeDictStrSignatureBridge:
    """The dict/str mismatch root cause (R648): ``_invoke_*`` providers
    declared ``(input_text: str, context: Dict)``, but the delegation
    mode executor passed the full ``input_data`` dict as the position
    bound to ``input_text``. The fix is to thread the textual payload
    (``command['description']``) as ``input_text`` and tuck the
    structured fields into ``context['input_data']``.
    """

    @pytest.mark.asyncio
    async def test_executor_passes_text_as_str_not_dict(self) -> None:
        """When the executor invokes a provider, the positional
        ``input_text`` argument must be a ``str`` — never a ``dict``.
        This is the regression guard for #1471.
        """
        registry = setup_registry(include_optional=True)

        captured: Dict[str, Any] = {}

        async def _spy_provider(
            input_text: str, context: Dict[str, Any]
        ) -> Dict[str, Any]:
            captured["input_text_type"] = type(input_text).__name__
            captured["input_text_value"] = (
                input_text[:80] if isinstance(input_text, str) else input_text
            )
            captured["context_has_input_data"] = (
                isinstance(context, dict) and "input_data" in context
            )
            return {"status": "completed", "echo": input_text[:40]}

        # Register a transient provider under a fresh capability.
        from argumentation_analysis.core.capability_registry import (
            ComponentType,
        )

        registry.register(
            name="spy_signature_bridge_provider",
            component_type=ComponentType.SERVICE,
            capabilities=["spy_signature_bridge"],
            invoke=_spy_provider,
        )

        executor = make_registry_operational_executor(registry)
        result = await executor(
            {
                "tactical_task_id": "t-spy",
                "objective_id": "obj-spy",
                "description": "Le texte d'entrée est ici.",
                "required_capabilities": ["spy_signature_bridge"],
                "context": {"phase": "spy"},
            }
        )

        assert result["status"] == "completed"
        assert captured["input_text_type"] == "str", (
            f"provider received {captured['input_text_type']} — the "
            f"dict/str mismatch has regressed"
        )
        assert captured[
            "context_has_input_data"
        ], "structured input_data must be carried in context['input_data']"

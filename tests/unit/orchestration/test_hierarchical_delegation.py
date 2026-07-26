#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the M3 true 3-tier delegation orchestrator (RA-10 #1069 / ORC-2).
===========================================================================

Covers the DoD of #1069:
- 3-tier path runnable + selectable (DelegationOrchestrator + mode routing).
- Strategic NL objective flows S→T→O — a write→read chain test asserting a
  unique strategic-intent marker reaches the operational command/provider.
- No heuristic fallback — a degraded delegation fails loud (#1019):
    * empty strategic objectives → DelegationError
    * absent operational tier → DelegationError
    * missing capability provider → honest status="failed" (not fabrication)

Async note: this directory's local ``pytest.ini`` uses STRICT asyncio mode
(not the repo root's ``asyncio_mode = auto``), so the module-level
``pytestmark = pytest.mark.asyncio`` below is required for the ``async def``
tests to run.
"""

from unittest.mock import MagicMock
from typing import Any, Dict

import pytest

from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    DelegationError,
    DelegationOrchestrator,
    make_registry_operational_executor,
    run_delegation_analysis,
)
from argumentation_analysis.orchestration.hierarchical.orchestrator import (
    run_hierarchical_analysis,
)

# This dir's local pytest.ini uses strict asyncio mode — mark every (async) test.
pytestmark = pytest.mark.asyncio


# A deliberately unique, keyword-free marker. Keyword-free so the tactical
# decomposition falls through to its generic branch (it must NOT match the
# "identifier"+"arguments" or "détecter"+"sophisme" heuristics), which proves
# the NL intent is threaded explicitly rather than via the keyword router.
STRATEGIC_MARKER = "UNIQUE_STRATEGIC_INTENT_zeta42_opaque"


class _FakeStrategicManager:
    """Strategic-tier seam: returns canned objectives, records eval input.

    Replacing the real ``StrategicManager`` keeps the test free of LLM/middleware
    while still exercising the REAL tactical decomposition + T→O translation.
    """

    def __init__(self, objectives):
        self._objectives = objectives
        self.eval_calls = []

    def initialize_analysis(self, text):
        return {"objectives": self._objectives, "strategic_plan": {}}

    def evaluate_final_results(self, results):
        self.eval_calls.append(results)
        return {
            "conclusion": "stub-conclusion",
            "evaluation": {"overall_success_rate": 1.0},
        }


class _FakeProvider:
    def __init__(self, name, invoke):
        self.name = name
        self.invoke = invoke


class _FakeRegistry:
    """Minimal CapabilityRegistry surface used by RegistryBackedOperationalRegistry."""

    def __init__(self, providers_by_cap=None):
        self._providers_by_cap = providers_by_cap or {}

    def find_for_capability(self, capability):
        return self._providers_by_cap.get(capability, [])


# ---------------------------------------------------------------------------
# S→T→O write→read chain
# ---------------------------------------------------------------------------


async def test_strategic_objective_flows_s_to_t_to_o():
    """The strategic NL objective (write) reaches the operational command (read).

    This is the core #1069 chain test: a unique strategic-intent marker, set at
    the strategic tier, must surface verbatim on the operational command after
    crossing the real tactical decomposition + translation tiers.
    """
    objectives = [{"id": "obj-1", "description": STRATEGIC_MARKER, "priority": "high"}]
    captured = []

    async def stub_executor(command):
        captured.append(command)
        return {
            "task_id": command.get("tactical_task_id"),
            "objective_id": command.get("objective_id"),
            "status": "completed",
            "outputs": {"ok": True},
        }

    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        operational_executor=stub_executor,
        middleware=MagicMock(),
    )

    result = await orchestrator.analyze("some source text")

    assert result["mode"] == "delegation"
    assert result["tasks_created"] >= 1
    assert len(captured) >= 1
    # write→read: the NL intent crossed S→T→O intact.
    assert captured[0]["strategic_objective_description"] == STRATEGIC_MARKER
    assert captured[0]["objective_id"] == "obj-1"
    # The strategic tier received an aggregated per-objective success_rate.
    assert orchestrator.strategic_manager.eval_calls
    assert "obj-1" in orchestrator.strategic_manager.eval_calls[0]


async def test_multiple_objectives_each_thread_their_intent():
    """Each objective's NL intent reaches its own task's command (no cross-talk)."""
    objectives = [
        {"id": "obj-1", "description": "ALPHA_intent_opaque", "priority": "high"},
        {"id": "obj-2", "description": "BETA_intent_opaque", "priority": "medium"},
    ]
    captured = {}

    async def stub_executor(command):
        captured[command["objective_id"]] = command["strategic_objective_description"]
        return {
            "task_id": command.get("tactical_task_id"),
            "objective_id": command.get("objective_id"),
            "status": "completed",
        }

    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        operational_executor=stub_executor,
        middleware=MagicMock(),
    )
    await orchestrator.analyze("text")

    assert captured["obj-1"] == "ALPHA_intent_opaque"
    assert captured["obj-2"] == "BETA_intent_opaque"


# ---------------------------------------------------------------------------
# Fail-loud — no heuristic fallback (#1019)
# ---------------------------------------------------------------------------


async def test_empty_objectives_fails_loud():
    """Zero strategic objectives must raise, not silently inject defaults."""
    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager([]),
        operational_executor=lambda cmd: None,  # never reached
        middleware=MagicMock(),
    )
    with pytest.raises(DelegationError):
        await orchestrator.analyze("text")


async def test_absent_operational_tier_fails_loud():
    """No executor and no registry → the chain has no operational tier → raise."""
    objectives = [
        {"id": "obj-1", "description": "generic_opaque_task", "priority": "high"}
    ]
    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        middleware=MagicMock(),
    )  # no operational_executor, no capability_registry
    with pytest.raises(DelegationError):
        await orchestrator.analyze("text")


async def test_run_delegation_analysis_routes_to_chain():
    """The convenience fn builds + runs the chain (and fails loud on empty tier)."""
    objectives = [
        {"id": "obj-1", "description": "generic_opaque_task", "priority": "high"}
    ]
    with pytest.raises(DelegationError):
        await run_delegation_analysis(
            "text",
            strategic_manager=_FakeStrategicManager(objectives),
            middleware=MagicMock(),
        )


# ---------------------------------------------------------------------------
# Default registry-backed executor — honest failure vs real routing
# ---------------------------------------------------------------------------


async def test_registry_executor_missing_provider_is_honest_failure():
    """A required capability with no provider yields status=failed, not a raise
    and not a fabricated success."""
    executor = make_registry_operational_executor(_FakeRegistry())
    result = await executor(
        {
            "tactical_task_id": "t1",
            "objective_id": "obj-1",
            "required_capabilities": ["fallacy_detection"],
        }
    )
    assert result["status"] == "failed"
    assert result["reason"] == "no_provider_for_required_capabilities"


async def test_registry_executor_invokes_real_provider_with_intent():
    """The default executor routes the strategic NL intent to the provider.

    BO-1 #1471 cont. R648: the executor normalises the signature so that
    ``input_text`` (position 1) is the textual payload (``command["description"]``,
    a ``str``) and the structured fields land in ``context["input_data"]`` —
    mirroring the contract ``RegistryBackedOperationalRegistry.invoke_capability``
    expects. The NL intent ``strategic_objective_description`` flows S→T→O via
    the command dict, so the provider must read it from ``context["input_data"]``.
    """
    captured: Dict[str, Any] = {}

    async def fake_invoke(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        captured["input_text_type"] = type(input_text).__name__
        captured["input_text"] = input_text
        captured["intent_in_input_data"] = (
            isinstance(context, dict)
            and "input_data" in context
            and context["input_data"].get("strategic_objective_description")
            == "INTENT_MARK_opaque"
        )
        return {"echo": context["input_data"]["strategic_objective_description"]}

    registry = _FakeRegistry(
        {"fallacy_detection": [_FakeProvider("informal_v1", fake_invoke)]}
    )
    executor = make_registry_operational_executor(registry)
    result = await executor(
        {
            "tactical_task_id": "t1",
            "objective_id": "obj-2",
            "description": "Some tactical description for the provider.",
            "required_capabilities": ["fallacy_detection"],
            "strategic_objective_description": "INTENT_MARK_opaque",
            # CC #1531: le corpus voyage par ``text_extracts``. Le fixture est
            # antérieur à ce contrat (il ne portait qu'une ``description``), ce
            # qui est exactement le défaut corrigé — les assertions R648
            # ci-dessous sont conservées telles quelles.
            "text_extracts": [{"id": "x1", "content": "CORPUS_MARK_opaque"}],
        }
    )
    assert result["status"] == "completed"
    assert result["capability"] == "fallacy_detection"
    assert captured["input_text_type"] == "str", (
        f"provider received {captured['input_text_type']} at position 1 — "
        f"the dict/str normalisation regressed"
    )
    assert captured[
        "intent_in_input_data"
    ], "strategic NL intent must reach the provider via context['input_data']"
    assert result["outputs"]["echo"] == "INTENT_MARK_opaque"
    assert captured["input_text"] == "CORPUS_MARK_opaque", (
        "the provider must receive the CORPUS at position 1, not the task label "
        f"— got {captured['input_text']!r} (CC #1531)"
    )


# ---------------------------------------------------------------------------
# Mode routing on the shared hierarchical entry point
# ---------------------------------------------------------------------------


async def test_run_hierarchical_analysis_unknown_mode_raises():
    with pytest.raises(ValueError):
        await run_hierarchical_analysis("text", mode="nonsense")


async def test_run_hierarchical_analysis_delegation_mode_dispatches():
    """mode='delegation' routes to the M3 chain (proven by its fail-loud on an
    absent operational tier, which the M2 bridge would not raise).

    The fake strategic_manager + MagicMock middleware are threaded through
    ``**kwargs`` so no real LLM/MessageMiddleware is constructed in the test.
    """
    objectives = [
        {"id": "obj-1", "description": "generic_opaque_task", "priority": "high"}
    ]
    with pytest.raises(DelegationError):
        await run_hierarchical_analysis(
            "text",
            mode="delegation",
            strategic_manager=_FakeStrategicManager(objectives),
            middleware=MagicMock(),
        )


# ---------------------------------------------------------------------------
# CC #1531 — le CORPUS doit atteindre le tier opérationnel
# ---------------------------------------------------------------------------

# Marqueur distinct de STRATEGIC_MARKER : celui-ci suit le *texte à analyser*,
# pas l'intention stratégique. Les deux chaînes sont indépendantes et le test
# ci-dessous échouerait si l'une était confondue avec l'autre.
CORPUS_MARKER = "UNIQUE_CORPUS_omega77_opaque"


async def test_corpus_reaches_the_operational_command():
    """Chaîne écriture→lecture pour le TEXTE lui-même, pas seulement l'intention.

    CC #1531 : le tier tactique n'avait aucun canal pour le corpus.
    ``_determine_relevant_extracts`` retournait un extrait codé en dur et chaque
    agent opérationnel analysait un libellé de tâche d'une trentaine de
    caractères (``source_length: 28`` observé en run réel), pendant que la
    chaîne concluait « performance globale élevée ».
    """
    objectives = [{"id": "obj-1", "description": STRATEGIC_MARKER, "priority": "high"}]
    captured = []

    async def stub_executor(command):
        captured.append(command)
        return {
            "task_id": command.get("tactical_task_id"),
            "objective_id": command.get("objective_id"),
            "status": "completed",
            "outputs": {"ok": True},
        }

    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        operational_executor=stub_executor,
        middleware=MagicMock(),
    )
    await orchestrator.analyze(CORPUS_MARKER)

    assert captured, "aucune commande opérationnelle produite"
    for command in captured:
        contents = [
            extract.get("content") for extract in command.get("text_extracts", [])
        ]
        assert CORPUS_MARKER in contents, (
            f"le corpus n'a pas atteint la commande {command.get('id')} — "
            f"extraits reçus : {contents!r}"
        )
        assert (
            "Extrait à analyser..." not in contents
        ), "le placeholder codé en dur est revenu (régression CC #1531)"


async def test_executor_fails_loud_without_corpus():
    """Sans corpus, l'exécuteur échoue honnêtement au lieu de valider du vide."""

    async def fake_invoke(input_text, context):
        raise AssertionError(
            "le provider ne doit pas être invoqué sans corpus (CC #1531)"
        )

    registry = _FakeRegistry(
        {"fallacy_detection": [_FakeProvider("informal_v1", fake_invoke)]}
    )
    executor = make_registry_operational_executor(registry)
    result = await executor(
        {
            "tactical_task_id": "t1",
            "objective_id": "obj-1",
            "description": "Détecter les sophismes",  # libellé seul : insuffisant
            "required_capabilities": ["fallacy_detection"],
            "text_extracts": [],
        }
    )

    assert result["status"] == "failed"
    assert result["reason"] == "insufficient_input"


async def test_starved_run_does_not_report_success_to_the_strategic_tier():
    """L'ENTRÉE du verdict ne ment plus.

    Anti-pendule : on ne touche ni ``_compute_decides`` ni
    ``_formulate_conclusion``. On prouve que ce qui les alimente est honnête —
    une chaîne privée de corpus remonte ``success_rate == 0.0``, et non 1.0.
    Auparavant chaque tâche était comptée ``completed`` (le provider répondait
    « aucun texte fourni ») ⇒ 1.0 ⇒ « performance globale élevée ».
    """
    objectives = [{"id": "obj-1", "description": STRATEGIC_MARKER, "priority": "high"}]

    async def fake_invoke(input_text, context):
        return {"unreachable": True}

    registry = _FakeRegistry(
        {
            cap: [_FakeProvider(f"prov_{cap}", fake_invoke)]
            for cap in ("fallacy_detection", "fact_extraction", "argument_parsing")
        }
    )
    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        operational_executor=make_registry_operational_executor(registry),
        middleware=MagicMock(),
    )
    # Corpus vide : le tier tactique n'a rien à transmettre.
    result = await orchestrator.analyze("")

    assert all(
        r["status"] == "failed" for r in result["operational_results"]
    ), f"une tâche sans corpus a été comptée réussie : {result['operational_results']!r}"
    eval_input = orchestrator.strategic_manager.eval_calls[0]
    assert all(
        v["success_rate"] == 0.0 for v in eval_input.values()
    ), f"le tier stratégique a reçu un taux de succès fabriqué : {eval_input!r}"

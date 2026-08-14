# -*- coding: utf-8 -*-
"""
#1735 T3 — désignation motivée au palier tactique hiérarchique.

Le palier tactique (``TaskCoordinator``) enregistre désormais POURQUOI il
alloue chaque tâche — miroir du ``record_designation`` conversationnel
(CONV-C #1334) — et la trace du run (``DelegationOrchestrator.analyze``)
l'expose, scrubée par le mécanisme de ``strategic_bridge``.

DoD couvert :
- chaque allocation porte une motivation non vide, vérifiable en trace ;
- un test échoue si une allocation est enregistrée SANS motivation
  (``record_allocation_motivation`` refuse le blanc ; l'invariant de run
  vérifie l'alignement assignation↔motivation) ;
- le scrub privacy de ``strategic_bridge`` s'applique au nouveau contenu ;
- la trace CLI (run_orchestration.py) lit ``result["task_assignments"]``.

Contrôles de substitution (kill-sets disjoints, exécutés en session) :
- Sub A (retirer l'enregistrement dans ``assign_task_to_operational``) →
  invariant de run rouge seul.
- Sub B (vider ``record_allocation_motivation`` de son ValueError) → le
  test de refus de blanc rouge seul.
"""

import json

import pytest

from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    DelegationOrchestrator,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)


class _FakeStrategicManager:
    """Strategic tier fake — deterministic objectives, no LLM."""

    def __init__(self, objectives):
        self._objectives = objectives

    def initialize_analysis(self, text):
        return {"objectives": list(self._objectives), "strategic_plan": {}}

    def evaluate_final_results(self, eval_input):
        return {
            "conclusion": "Conclusion de test.",
            "evaluation": {"objectives_evaluation": eval_input},
        }


async def _completed_executor(command):
    """Operational executor fake — every task completes."""
    caps = command.get("required_capabilities") or ["generic"]
    return {
        "task_id": command.get("tactical_task_id"),
        "objective_id": command.get("objective_id"),
        "status": "completed",
        "capability": caps[0],
        "outputs": {"echo": "ok"},
    }


def _objectives():
    """Two objectives hitting the two keyword decomposition branches:
    "identifier"+arguments → 2 tasks, "détecter"+sophisme → 1 task."""
    return [
        {
            "id": "obj-identify",
            "description": "Identifier les arguments dans le texte",
            "priority": "high",
        },
        {
            "id": "obj-fallacy",
            "description": "Détecter les sophismes dans le texte",
            "priority": "medium",
        },
    ]


async def _run(objectives=None, executor=None):
    orch = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives or _objectives()),
        operational_executor=executor or _completed_executor,
    )
    result = await orch.analyze("Texte de test court, sans source nominative.")
    return orch, result


async def test_every_allocation_carries_non_empty_motivation():
    """DoD 1 : chaque allocation porte une motivation non vide, en trace."""
    orch, result = await _run()
    assignments = result.get("task_assignments", [])
    assert len(assignments) == 3, (
        f"expected 3 decomposed tasks (2 identifier-branch + 1 fallacy-branch), "
        f"got {len(assignments)}"
    )
    for a in assignments:
        assert a["task_id"], f"assignment missing task_id: {a}"
        assert a["agent_id"], f"assignment {a['task_id']} missing agent_id"
        motivation = a.get("motivation", "")
        assert motivation.strip(), (
            f"allocation {a['task_id']} recorded WITHOUT a motivation (#1735 T3): "
            f"an allocation without a why is the defect the motivated designation "
            f"exists to forbid"
        )


async def test_state_assignments_and_motivations_are_aligned():
    """Invariant : tout task_id assigné a une motivation, et réciproquement."""
    orch, _ = await _run()
    state = orch.tactical_coordinator.state
    assert set(state.task_assignments) == set(state.task_assignments_motivation), (
        f"assignations {sorted(state.task_assignments)} != motivations "
        f"{sorted(state.task_assignments_motivation)} — désalignement "
        f"qui/ pourquoi"
    )
    assert len(state.task_assignments) == 3
    for task_id, motivation in state.task_assignments_motivation.items():
        assert (
            motivation.strip()
        ), f"task {task_id} assigned with a blank motivation in the state"


def test_blank_motivation_is_refused():
    """DoD 2 : une allocation enregistrée SANS motivation est refusée.

    Version directe du canari : ``record_allocation_motivation`` lève
    ValueError sur blanc — le point d'écriture rend le défaut impossible,
    pas seulement détectable.
    """
    state = TacticalState()
    with pytest.raises(ValueError, match="non vide"):
        state.record_allocation_motivation("task-1", "   ")
    # Une motivation réelle passe.
    assert state.record_allocation_motivation("task-1", "  raison réelle  ") is True
    assert state.task_assignments_motivation["task-1"] == "raison réelle"


async def test_motivation_documents_the_score_not_the_forbidden_template():
    """Anti-pendule #1732 : la motivation n'est PAS « tâche X → agent Y ».

    Elle documente la règle de décision réellement appliquée : la couverture
    de capacités qui a fait gagner l'agent au scoring.
    """
    _, result = await _run()
    assignments = result["task_assignments"]
    premise_task = next(
        a
        for a in assignments
        if a["description"] == "Identifier prémisses et conclusions"
    )
    assert premise_task["agent_id"] == "informal_analyzer"
    motivation = premise_task["motivation"]
    forbidden_template = (
        f"allocation de la tâche {premise_task['task_id']} à l'agent "
        f"{premise_task['agent_id']}"
    )
    assert motivation != forbidden_template
    assert "informal_analyzer" in motivation
    assert "1/1" in motivation, f"motivation lacks the score: {motivation!r}"
    assert (
        "argument_identification" in motivation
    ), f"motivation lacks the covered capability: {motivation!r}"


async def test_motivation_for_generic_task_documents_fallback():
    """Une tâche sans capacité requise est quand même motivée — par le fallback."""
    generic = [
        {
            "id": "obj-g",
            "description": "Analyser la structure logique",
            "priority": "low",
        }
    ]
    _, result = await _run(objectives=generic)
    assignments = result["task_assignments"]
    assert len(assignments) == 1
    a = assignments[0]
    assert a["agent_id"] == "default_operational_agent"
    assert a["motivation"].strip()
    assert (
        "fallback" in a["motivation"]
    ), f"fallback not documented: {a['motivation']!r}"


async def test_privacy_scrub_applies_to_motivated_assignments():
    """DoD 3 : le scrub de strategic_bridge s'applique au nouveau contenu.

    Un objectif portant des champs nominatifs (``author``/``source_name``)
    ne laisse aucune clé nominative ni aucune valeur canary dans les
    assignations motivées — la motivation est construite des libellés
    génériques + scoring, jamais des champs nominatifs de l'objectif, et le
    dict passe par ``strategic_bridge._scrub_dict`` avant de sortir.
    """
    objectives = [
        {
            "id": "obj-p",
            "description": "Identifier les arguments dans le texte",
            "priority": "high",
            "author": "Nom_Reel_Source_1735",
            "source_name": "Titre_Reel_Source_1735",
        }
    ]
    _, result = await _run(objectives=objectives)
    serialized = json.dumps(result["task_assignments"], ensure_ascii=False)
    assert "Nom_Reel_Source_1735" not in serialized
    assert "Titre_Reel_Source_1735" not in serialized
    assert '"author"' not in serialized
    assert '"source_name"' not in serialized


async def test_trace_exposes_motivated_assignments():
    """DoD 4 (tracé) : la trace du run porte les assignations motivées.

    C'est la clé lue par la trace CLI delegation
    (``run_orchestration.py`` — "Assignations (N):").
    """
    _, result = await _run()
    assert "task_assignments" in result
    assignments = result["task_assignments"]
    assert isinstance(assignments, list) and assignments
    for a in assignments:
        assert {"task_id", "description", "agent_id", "motivation"} <= set(a)

# -*- coding: utf-8 -*-
"""#2794 — la délégation ne renvoie plus ses résultats par l'interface tactique.

``DelegationOrchestrator.analyze`` appelait, après chaque tâche,
``interface.process_operational_result(command, result)``, sous un commentaire
qui promettait de mettre à jour l'état tactique. Cet appel ne touchait pas
l'état tactique. Il construisait un rapport, l'envoyait sur le middleware à
``tactical_coordinator`` et l'écrivait sous ``RESULTS_DIR``.

Recensement sur ``main`` ``3098f4a5f`` (``git grep`` hors ``tests/`` et
``docs/``) :

- le rapport envoyé n'a aucun lecteur de production
  (``TacticalAdapter.get_pending_task_results`` et ``receive_task_result`` : 0
  appelant) ;
- le fichier ``<tâche>_results.json`` n'est relu par aucun code ;
- l'état tactique n'est lu par personne après la boucle :
  ``run_delegation_analysis`` jette l'orchestrateur au retour d'``analyze``, et
  le dict rendu ne porte pas l'état tactique. Pendant la boucle, la traduction
  lit le texte, les tâches voisines et les dépendances, jamais le statut.

Décision : retrait (option b de l'issue). Le résultat va directement des
tâches opérationnelles à ``_aggregate_results_by_objective``.

Contrôle : remettre l'appel dans la boucle rougit les deux premiers tests.
"""

from unittest.mock import MagicMock

import pytest

from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    DelegationOrchestrator,
)
from argumentation_analysis.orchestration.hierarchical.interfaces import (
    tactical_operational,
)


@pytest.fixture(autouse=True)
def results_dir(tmp_path, monkeypatch):
    """Redirige ``RESULTS_DIR`` : même un mutant qui rétablit l'appel
    n'écrit rien dans le checkout."""
    path = tmp_path / "results"
    monkeypatch.setattr(tactical_operational, "RESULTS_DIR", path)
    return path


class _FakeStrategicManager:
    """Palier stratégique factice : objectifs fixes, entrée d'évaluation gardée."""

    def __init__(self, objectives):
        self._objectives = objectives
        self.eval_inputs = []

    def initialize_analysis(self, text):
        return {"objectives": list(self._objectives), "strategic_plan": {}}

    def evaluate_final_results(self, eval_input):
        self.eval_inputs.append(eval_input)
        return {"conclusion": "Conclusion de test.", "evaluation": {}}


async def _executor_failing_fallacy_tasks(command):
    """Les tâches de l'objectif sophismes échouent, les autres produisent."""
    failed = command.get("objective_id") == "obj-fallacy"
    caps = command.get("required_capabilities") or ["generic"]
    result = {
        "task_id": command.get("tactical_task_id"),
        "objective_id": command.get("objective_id"),
        "status": "failed" if failed else "completed",
        "capability": caps[0],
        "outputs": {} if failed else {"echo": "ok"},
    }
    if failed:
        result["reason"] = "fournisseur indisponible (test)"
    return result


def _objectives():
    # Deux branches de décomposition par mots-clés : 2 tâches + 1 tâche.
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


def _orchestrator():
    strategic = _FakeStrategicManager(_objectives())
    orch = DelegationOrchestrator(
        strategic_manager=strategic,
        operational_executor=_executor_failing_fallacy_tasks,
    )
    return orch, strategic


async def test_delegation_writes_no_result_file(results_dir):
    orch, _ = _orchestrator()

    result = await orch.analyze("Texte de test court, sans source nominative.")

    assert len(result["operational_results"]) == 3
    written = (
        sorted(p.name for p in results_dir.rglob("*")) if results_dir.exists() else []
    )
    assert (
        written == []
    ), f"la délégation a écrit des rapports que personne ne relit : {written}"


async def test_delegation_sends_no_report_on_the_middleware():
    orch, _ = _orchestrator()
    send_result = MagicMock(name="send_result")
    orch.interface.operational_adapter.send_result = send_result

    await orch.analyze("Texte de test court, sans source nominative.")

    send_result.assert_not_called()


async def test_task_outcomes_reach_the_strategic_evaluation_directly():
    orch, strategic = _orchestrator()

    result = await orch.analyze("Texte de test court, sans source nominative.")

    statuses = sorted(r["status"] for r in result["operational_results"])
    assert statuses == ["completed", "completed", "failed"]
    assert strategic.eval_inputs == [
        {
            "obj-identify": {"success_rate": 1.0},
            "obj-fallacy": {"success_rate": 0.0},
        }
    ]
    assert "fournisseur indisponible (test)" in " ".join(result["degradation_reasons"])

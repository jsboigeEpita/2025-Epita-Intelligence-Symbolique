# -*- coding: utf-8 -*-
"""#2786 — le worker rend chaque tâche prise ; un objectif en échec ne part
plus dans un rapport que personne ne lit.

1. ``OperationalManager._worker`` sautait ``task_done()`` sur son chemin
   d'erreur : un ``task_queue.join()`` attendait sans fin après la première
   erreur. Et son ``if "task" in locals()`` restait vrai d'un tour à l'autre,
   si bien qu'une erreur levée avant la prise d'une nouvelle tâche accusait
   la tâche du tour précédent.
2. ``TaskCoordinator.handle_task_result`` envoyait un rapport
   ``objective_completion`` au stratégique, toujours à ``completed`` même si
   toutes les tâches avaient échoué, et aucun code ne le lisait. Il est
   retiré : l'issue de l'objectif reste dans l'état tactique que le
   coordinateur met à jour, et le stratégique la reçoit, sur le chemin réel,
   par l'agrégation de ``DelegationOrchestrator``.

Le manager, l'interface, le coordinateur et les états sont réels. Seuls le
registre d'agents du manager et le middleware du coordinateur sont doublés.
Entrées synthétiques.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import (
    TacticalOperationalInterface,
)
from argumentation_analysis.orchestration.hierarchical.operational.manager import (
    OperationalManager,
)
from argumentation_analysis.orchestration.hierarchical.operational.state import (
    OperationalState,
)
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import (
    TaskCoordinator,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)

OBJECTIVE_ID = "obj-2786"
JOIN_TIMEOUT = 5.0


def _tactical_task():
    return {
        "id": "task-2786",
        "description": "Synthetic fallacy detection",
        "objective_id": OBJECTIVE_ID,
        "required_capabilities": ["fallacy_detection"],
    }


def _manager(process_task, interface=None):
    manager = OperationalManager(
        operational_state=OperationalState(), tactical_operational_interface=interface
    )
    manager.agent_registry.initialize_all_agents = AsyncMock()
    manager.agent_registry.process_task = process_task
    return manager


def _drain(queue):
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


async def test_join_returns_after_a_raising_task():
    """Le témoin du DoD : ``join()`` revient après une tâche qui lève."""
    manager = _manager(AsyncMock(side_effect=RuntimeError("Synthetic worker failure")))

    await manager.start()
    try:
        await manager.task_queue.put({"id": "op-1"})
        await asyncio.wait_for(manager.task_queue.join(), timeout=JOIN_TIMEOUT)
    finally:
        await manager.stop()

    (error,) = _drain(manager.result_queue)
    assert error["task_id"] == "op-1"
    assert error["status"] == "failed"
    assert error["issues"] == [
        {"type": "worker_error", "description": "Synthetic worker failure"}
    ]


async def test_error_outside_a_task_is_not_charged_to_the_previous_one():
    """Une erreur levée avant la prise d'une tâche n'accuse aucune tâche.

    La première tâche réussit ; la prise suivante lève. L'ancien worker
    rapportait cette erreur contre ``op-1``, déjà terminée, puis continuait.
    Elle remonte maintenant telle quelle, sans rapport d'échec inventé.
    """
    done = {"id": "result-1", "task_id": "op-1", "status": "completed"}
    manager = _manager(AsyncMock(return_value=done))
    queue = MagicMock()
    queue.get = AsyncMock(
        side_effect=[
            {"id": "op-1"},
            RuntimeError("Synthetic queue failure"),
            # Borne l'ancien worker, qui continuait après l'erreur.
            asyncio.CancelledError(),
        ]
    )
    manager.task_queue = queue
    manager.running = True

    with pytest.raises(RuntimeError, match="Synthetic queue failure"):
        await manager._worker()

    assert _drain(manager.result_queue) == [done]
    queue.task_done.assert_called_once_with()


async def test_failed_objective_stays_in_the_tactical_state_without_a_report(
    monkeypatch,
):
    """La chaîne réelle : erreur du worker → rapport de l'interface → état.

    Aucun rapport ``objective_completion`` ne part vers le stratégique.
    """
    interface = TacticalOperationalInterface(tactical_state=TacticalState())
    # Seule écriture disque de la chaîne : le rapport JSON sous RESULTS_DIR.
    monkeypatch.setattr(interface, "_save_result_to_file", lambda report: None)
    manager = _manager(
        AsyncMock(side_effect=RuntimeError("Synthetic worker failure")), interface
    )
    state = TacticalState()
    state.add_task(_tactical_task(), "in_progress")
    middleware = MagicMock()
    coordinator = TaskCoordinator(tactical_state=state, middleware=middleware)

    await manager.start()
    try:
        report = await manager.process_tactical_task(_tactical_task())
    finally:
        await manager.stop()
    assert coordinator.handle_task_result(report) == {"status": "success"}

    assert [t["id"] for t in state.tasks["failed"]] == ["task-2786"]
    assert state.are_all_tasks_for_objective_done(OBJECTIVE_ID)
    sent = [c.args[0] for c in middleware.send_message.call_args_list if c.args]
    assert [
        m for m in sent if m.content.get("report_type") == "objective_completion"
    ] == []

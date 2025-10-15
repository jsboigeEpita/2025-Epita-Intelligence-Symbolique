# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import (
    TaskCoordinator,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)
from argumentation_analysis.core.communication import (
    MessageMiddleware,
    Message,
    MessageType,
    AgentLevel,
    ChannelType,
    MessagePriority,
)


@pytest.fixture
def mock_tactical_state():
    """Fixture pour un TacticalState mocké."""
    state = MagicMock(spec=TacticalState)
    state.tasks = {"pending": [], "in_progress": [], "completed": [], "failed": []}
    state.assigned_objectives = []
    state.identified_conflicts = []
    state.log_tactical_action = MagicMock()
    state.add_assigned_objective = MagicMock()
    state.add_task = MagicMock()
    state.add_task_dependency = MagicMock()
    state.update_task_status = MagicMock()
    state.add_intermediate_result = MagicMock()
    state.get_objective_results = MagicMock(return_value={})
    return state


@pytest.fixture
def mock_middleware():
    """Fixture pour un MessageMiddleware mocké."""
    middleware = MagicMock(spec=MessageMiddleware)
    mock_channel = MagicMock()
    middleware.get_channel.return_value = mock_channel
    return middleware


@pytest.fixture
def task_coordinator(mock_tactical_state, mock_middleware):
    """Fixture pour un TaskCoordinator avec des dépendances mockées."""
    with patch.object(
        TaskCoordinator, "_subscribe_to_strategic_directives", return_value=None
    ), patch(
        "argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter"
    ) as MockAdapterClass:
        mock_adapter_instance = MockAdapterClass.return_value
        coordinator = TaskCoordinator(
            tactical_state=mock_tactical_state, middleware=mock_middleware
        )
        coordinator.adapter = mock_adapter_instance
    return coordinator


def test_task_coordinator_initialization(
    task_coordinator, mock_tactical_state, mock_middleware
):
    """Teste l'initialisation correcte du TaskCoordinator."""
    assert task_coordinator.state == mock_tactical_state
    assert task_coordinator.middleware == mock_middleware
    assert task_coordinator.adapter is not None
    assert isinstance(task_coordinator.adapter, MagicMock)


def test_determine_appropriate_agent(task_coordinator):
    """Teste la détermination de l'agent approprié."""
    task_coordinator.agent_capabilities = {
        "agent1": ["capA", "capB"],
        "agent2": ["capB", "capC"],
        "agent3": ["capA", "capD"],
    }
    assert task_coordinator._determine_appropriate_agent(["capA", "capB"]) == "agent1"
    assert task_coordinator._determine_appropriate_agent(["capC"]) == "agent2"
    assert task_coordinator._determine_appropriate_agent(["capD", "capA"]) == "agent3"
    assert task_coordinator._determine_appropriate_agent(["capX"]) is None
    assert task_coordinator._determine_appropriate_agent([]) is None


def test_decompose_objective_to_tasks_identify_arguments(task_coordinator):
    """Teste la décomposition d'un objectif d'identification d'arguments."""
    objective = {
        "id": "obj-identify",
        "description": "Identifier les arguments dans le texte.",
        "priority": "high",
    }
    tasks = task_coordinator._decompose_objective_to_tasks(objective)
    assert len(tasks) == 4
    assert (
        tasks[0]["description"]
        == "Extraire les segments de texte contenant des arguments potentiels"
    )
    assert tasks[0]["required_capabilities"] == ["text_extraction"]
    assert (
        tasks[1]["description"] == "Identifier les prémisses et conclusions explicites"
    )
    assert tasks[1]["required_capabilities"] == ["argument_identification"]
    for task in tasks:
        assert task["objective_id"] == "obj-identify"
        assert task["priority"] == "high"


def test_handle_task_result_objective_completion(task_coordinator, mock_tactical_state):
    """Teste la gestion du résultat d'une tâche menant à la complétion d'un objectif."""
    task_id = "task1_op"
    tactical_task_id = "obj1-task-final"
    objective_id = "obj1"

    # Configure state so that this is the last task for the objective
    mock_tactical_state.tasks = {
        "pending": [],
        "in_progress": [{"id": tactical_task_id, "objective_id": objective_id}],
        "completed": [{"id": "obj1-task-prev", "objective_id": objective_id}],
        "failed": [],
    }

    def side_effect_update_status(tid, status, *args, **kwargs):
        if tid == tactical_task_id and status == "completed":
            # Simulate moving the task from in_progress to completed
            mock_tactical_state.tasks["in_progress"] = []
            mock_tactical_state.tasks["completed"].append(
                {"id": tactical_task_id, "objective_id": objective_id}
            )

    mock_tactical_state.update_task_status.side_effect = side_effect_update_status

    with patch(
        "argumentation_analysis.orchestration.hierarchical.tactical.coordinator.RESULTS_DIR",
        "mocked_results_dir_path_value",
    ):
        result_data = {
            "task_id": task_id,
            "tactical_task_id": tactical_task_id,
            "status": "completed",
            "data": "some_result",
        }
        response = task_coordinator.handle_task_result(result_data)

    mock_tactical_state.update_task_status.assert_called_with(
        tactical_task_id, "completed"
    )
    mock_tactical_state.add_intermediate_result.assert_called_once_with(
        tactical_task_id, result_data
    )

    task_coordinator.adapter.send_report.assert_called_once_with(
        report_type="objective_completion",
        content={
            "objective_id": objective_id,
            "status": "completed",
            "results_path": "mocked_results_dir_path_value",
        },
        recipient_id="strategic_manager",
        priority=MessagePriority.HIGH,
    )
    assert response["status"] == "success"

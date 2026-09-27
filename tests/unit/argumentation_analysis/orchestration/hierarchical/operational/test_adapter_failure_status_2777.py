# -*- coding: utf-8 -*-
"""#2777 — un échec d'adaptateur remonte comme un échec, jusqu'à l'état tactique.

La chaîne vivante est adaptateur → ``OperationalManager._worker`` → Future →
``process_operational_result`` → ``TaskCoordinator.handle_task_result`` →
``TacticalState``. Elle cassait à trois endroits :

1. les chemins fatals des adaptateurs (``execution_error``,
   ``initialization_error``, ``agent_not_found``) rendaient
   ``completed_with_issues``, alors que l'état opérationnel notait ``failed``
   (ou restait ``in_progress``) ;
2. ``handle_task_result`` passait ``completed_with_issues`` à un état tactique
   qui n'a pas de liste à ce nom : la mise à jour échouait sans bruit et la
   tâche restait ``in_progress`` ;
3. ``_handle_worker_error`` résolvait la Future avec un dict nu, que
   ``process_tactical_task`` déballe en ``(task, result)`` : la cause du worker
   se perdait dans un ``ValueError`` de déballage.

Les adaptateurs, l'interface, le coordinateur et les états sont réels. Seuls
la frontière LLM (``Kernel.invoke_prompt``) et, pour le worker, le registre
d'agents du manager sont doublés. Entrées synthétiques.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)
from semantic_kernel.kernel import Kernel

from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
    InformalFallacyAgent,
)
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import (
    TacticalOperationalInterface,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import (
    ExtractAgentAdapter,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import (
    InformalAgentAdapter,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import (
    PLAgentAdapter,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.rhetorical_tools_adapter import (
    RhetoricalToolsAdapter,
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

OBJECTIVE_ID = "obj-2777"


def _tactical_task():
    return {
        "id": "task-2777",
        "description": "Synthetic fallacy detection",
        "objective_id": OBJECTIVE_ID,
        "required_capabilities": ["fallacy_detection"],
    }


@pytest.fixture
def kernel():
    """Kernel réel avec un service chat moqué, comme #2132 et #2740."""
    kernel = Kernel()
    service = MagicMock(spec=ChatCompletionClientBase)
    service.get_prompt_execution_settings_class.return_value = PromptExecutionSettings
    service.service_id = "test_service"
    kernel.add_service(service)
    return kernel


@pytest.fixture
def interface(monkeypatch):
    iface = TacticalOperationalInterface(tactical_state=TacticalState())
    # Seule écriture disque de la chaîne : le rapport JSON sous RESULTS_DIR.
    monkeypatch.setattr(iface, "_save_result_to_file", lambda report: None)
    return iface


@pytest.fixture
def tactical():
    """L'état tactique réel, la tâche en cours, et son coordinateur."""
    state = TacticalState()
    state.add_task(_tactical_task(), "in_progress")
    return state, TaskCoordinator(tactical_state=state)


@pytest.fixture
def operational_task(interface):
    task = interface.translate_task_to_command(_tactical_task())
    task["text_extracts"] = [{"content": "A synthetic claim"}]
    return task


@pytest.fixture
def informal(kernel):
    adapter = InformalAgentAdapter(
        config_name="simple", operational_state=OperationalState()
    )
    adapter.agent = InformalFallacyAgent(
        kernel=kernel, config_name="simple", llm_service_id="test_service"
    )
    adapter.initialized = True
    return adapter


def _operational_status(adapter, task_id):
    (task,) = [
        t for t in adapter.operational_state.assigned_tasks if t["id"] == task_id
    ]
    return task["status"]


def _buckets(state, task_id):
    return [
        status
        for status, tasks in state.tasks.items()
        if any(t["id"] == task_id for t in tasks)
    ]


class TestAdapterExceptionEndsFailed:
    async def test_raising_agent_fails_through_to_the_tactical_state(
        self, informal, interface, tactical, operational_task
    ):
        state, coordinator = tactical
        with patch.object(Kernel, "invoke_prompt", new_callable=AsyncMock) as invoke:
            invoke.side_effect = RuntimeError("Synthetic service failure")
            result = await informal.process_task(operational_task)
            invoke.assert_awaited_once()

        assert result["status"] == "failed"
        assert _operational_status(informal, operational_task["id"]) == "failed"

        report = interface.process_operational_result(operational_task, result)
        assert report["completion_status"] == "failed"
        assert report["issues"] == [
            {"type": "task_failure", "description": "Synthetic service failure"}
        ]

        assert coordinator.handle_task_result(report) == {"status": "success"}
        assert _buckets(state, "task-2777") == ["failed"]
        assert state.are_all_tasks_for_objective_done(OBJECTIVE_ID)

    async def test_non_fatal_issue_ends_completed_with_its_issues(
        self, informal, interface, tactical, operational_task
    ):
        state, coordinator = tactical
        with patch.object(Kernel, "invoke_prompt", new_callable=AsyncMock) as invoke:
            invoke.return_value = None
            result = await informal.process_task(operational_task)

        assert result["status"] == "completed_with_issues"
        assert (
            _operational_status(informal, operational_task["id"])
            == "completed_with_issues"
        )

        report = interface.process_operational_result(operational_task, result)
        coordinator.handle_task_result(report)

        assert _buckets(state, "task-2777") == ["completed"]
        assert state.are_all_tasks_for_objective_done(OBJECTIVE_ID)
        assert state.intermediate_results["task-2777"]["issues"] == [
            {"type": "empty_agent_response"}
        ]


def _uninitialized(adapter_cls):
    return adapter_cls(operational_state=OperationalState())


def _pl_without_agent():
    adapter = PLAgentAdapter(operational_state=OperationalState())
    adapter.initialized = True
    return adapter


@pytest.mark.parametrize(
    "make_adapter, issue_type",
    [
        (lambda: _uninitialized(ExtractAgentAdapter), "initialization_error"),
        (lambda: _uninitialized(InformalAgentAdapter), "initialization_error"),
        (lambda: _uninitialized(PLAgentAdapter), "initialization_error"),
        (lambda: _uninitialized(RhetoricalToolsAdapter), "initialization_error"),
        (_pl_without_agent, "agent_not_found"),
    ],
    ids=["extract", "informal", "pl", "rhetorical", "pl-agent-not-found"],
)
async def test_fatal_path_reports_failed_in_result_and_state(
    make_adapter, issue_type, operational_task
):
    adapter = make_adapter()

    result = await adapter.process_task(operational_task)

    assert [issue["type"] for issue in result["issues"]] == [issue_type]
    assert result["status"] == "failed"
    # Avant #2777, l'état restait ``in_progress`` sur ces chemins.
    assert _operational_status(adapter, operational_task["id"]) == "failed"


def test_unknown_completion_status_is_refused(tactical):
    state, coordinator = tactical
    report = {"tactical_task_id": "task-2777", "completion_status": "done-ish"}

    with pytest.raises(ValueError, match="done-ish"):
        coordinator.handle_task_result(report)

    assert _buckets(state, "task-2777") == ["in_progress"]


async def test_worker_error_reaches_the_tactical_report(interface):
    manager = OperationalManager(
        operational_state=OperationalState(), tactical_operational_interface=interface
    )
    manager.agent_registry.initialize_all_agents = AsyncMock()
    manager.agent_registry.process_task = AsyncMock(
        side_effect=RuntimeError("Synthetic worker failure")
    )

    await manager.start()
    try:
        report = await manager.process_tactical_task(_tactical_task())
    finally:
        await manager.stop()

    assert report["tactical_task_id"] == "task-2777"
    assert report["completion_status"] == "failed"
    assert report["issues"] == [
        {"type": "worker_error", "description": "Synthetic worker failure"}
    ]

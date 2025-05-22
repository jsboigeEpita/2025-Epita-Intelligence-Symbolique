import pytest
from unittest.mock import MagicMock, patch
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.core.communication import MessageMiddleware, Message, MessageType, AgentLevel, ChannelType, MessagePriority

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
    # Pour le test de la branche issues
    # del state.issues # S'assurer qu'il n'existe pas par défaut pour tester le fallback
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
    with patch.object(TaskCoordinator, '_subscribe_to_strategic_directives', return_value=None), \
         patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter') as MockAdapterClass:
        mock_adapter_instance = MockAdapterClass.return_value
        coordinator = TaskCoordinator(tactical_state=mock_tactical_state, middleware=mock_middleware)
        coordinator.adapter = mock_adapter_instance
    return coordinator

def test_task_coordinator_initialization(task_coordinator, mock_tactical_state, mock_middleware):
    """Teste l'initialisation correcte du TaskCoordinator."""
    assert task_coordinator.state == mock_tactical_state
    assert task_coordinator.middleware == mock_middleware
    assert task_coordinator.adapter is not None
    assert isinstance(task_coordinator.adapter, MagicMock)


def test_log_action(task_coordinator, mock_tactical_state):
    """Teste l'enregistrement d'une action tactique."""
    action_type = "test_action"
    description = "This is a test action."
    task_coordinator._log_action(action_type, description)
    mock_tactical_state.log_tactical_action.assert_called_once()
    call_args = mock_tactical_state.log_tactical_action.call_args[0][0]
    assert call_args["type"] == action_type
    assert call_args["description"] == description
    assert call_args["agent_id"] == "task_coordinator"

def test_subscribe_to_strategic_directives(mock_middleware):
    """Teste l'abonnement aux directives stratégiques."""
    state = MagicMock(spec=TacticalState)
    with patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter'):
        coordinator = TaskCoordinator(tactical_state=state, middleware=mock_middleware)
    
    mock_channel = mock_middleware.get_channel.return_value
    mock_channel.subscribe.assert_called_once()
    call_args = mock_channel.subscribe.call_args
    assert call_args[1]["subscriber_id"] == "tactical_coordinator"
    assert "callback" in call_args[1]
    assert call_args[1]["filter_criteria"] == {
        "recipient": "tactical_coordinator",
        "type": MessageType.COMMAND,
        "sender_level": AgentLevel.STRATEGIC
    }

def test_handle_directive_objective(mock_tactical_state, mock_middleware):
    """Teste la gestion d'une directive d'objectif."""
    objective_content = {"id": "obj1", "description": "Identifier les arguments", "priority": "high"}
    message_content = {
        "directive_type": "objective",
        "content": {"objective": objective_content}
    }
    message = Message(
        message_id="msg1",
        sender="strategic_manager",
        recipient="tactical_coordinator",
        message_type=MessageType.COMMAND,
        content=message_content,
        timestamp="2023-01-01T00:00:00Z",
        priority=MessagePriority.HIGH,
        sender_level=AgentLevel.STRATEGIC
    )
    
    callback_handler = None
    def mock_subscribe(subscriber_id, callback, filter_criteria):
        nonlocal callback_handler
        callback_handler = callback

    local_mock_middleware = MagicMock(spec=MessageMiddleware)
    mock_channel_for_fresh = MagicMock()
    mock_channel_for_fresh.subscribe.side_effect = mock_subscribe
    local_mock_middleware.get_channel.return_value = mock_channel_for_fresh
    
    with patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter') as MockFreshAdapterClass, \
         patch.object(TaskCoordinator, '_decompose_objective_to_tasks', return_value=[{"id": "task1"}, {"id": "task2"}]) as mock_decompose, \
         patch.object(TaskCoordinator, '_establish_task_dependencies') as mock_establish_deps, \
         patch.object(TaskCoordinator, '_log_action') as mock_log:
        
        fresh_coordinator = TaskCoordinator(tactical_state=mock_tactical_state, middleware=local_mock_middleware)
        fresh_coordinator.adapter = MockFreshAdapterClass.return_value 
        
        assert callback_handler is not None, "Callback was not captured"
        callback_handler(message)

    mock_tactical_state.add_assigned_objective.assert_called_with(objective_content)
    mock_decompose.assert_called_with(objective_content)
    mock_establish_deps.assert_called_once() 
    mock_log.assert_called() 

    assert mock_tactical_state.add_task.call_count == 2 
    mock_tactical_state.add_task.assert_any_call({"id": "task1"})
    mock_tactical_state.add_task.assert_any_call({"id": "task2"})
    
    fresh_coordinator.adapter.send_report.assert_called_once_with(
        report_type="directive_acknowledgement",
        content={
            "objective_id": "obj1",
            "tasks_created": 2
        },
        recipient_id="strategic_manager",
        priority=MessagePriority.NORMAL
    )

def test_process_strategic_objectives(task_coordinator, mock_tactical_state):
    """Teste le traitement des objectifs stratégiques."""
    objectives = [
        {"id": "obj1", "description": "Identifier les arguments", "priority": "high"},
        {"id": "obj2", "description": "Détecter les sophismes", "priority": "medium"}
    ]
    
    with patch.object(task_coordinator, '_decompose_objective_to_tasks', side_effect=[[{"id": "t1", "objective_id": "obj1"}], [{"id": "t2", "objective_id": "obj2"}]]) as mock_decompose, \
         patch.object(task_coordinator, '_establish_task_dependencies') as mock_establish_deps, \
         patch.object(task_coordinator, '_assign_task_to_operational_agent') as mock_assign_task, \
         patch.object(task_coordinator, '_log_action'): 

        result = task_coordinator.process_strategic_objectives(objectives)

    assert mock_tactical_state.add_assigned_objective.call_count == 2
    mock_tactical_state.add_assigned_objective.assert_any_call(objectives[0])
    mock_tactical_state.add_assigned_objective.assert_any_call(objectives[1])

    assert mock_decompose.call_count == 2
    mock_decompose.assert_any_call(objectives[0])
    mock_decompose.assert_any_call(objectives[1])

    mock_establish_deps.assert_called_once_with([{"id": "t1", "objective_id": "obj1"}, {"id": "t2", "objective_id": "obj2"}])
    
    assert mock_tactical_state.add_task.call_count == 2
    mock_tactical_state.add_task.assert_any_call({"id": "t1", "objective_id": "obj1"})
    mock_tactical_state.add_task.assert_any_call({"id": "t2", "objective_id": "obj2"})

    assert mock_assign_task.call_count == 2
    mock_assign_task.assert_any_call({"id": "t1", "objective_id": "obj1"})
    mock_assign_task.assert_any_call({"id": "t2", "objective_id": "obj2"})
    
    assert result["tasks_created"] == 2
    assert result["tasks_by_objective"] == {"obj1": ["t1"], "obj2": ["t2"]}

def test_determine_appropriate_agent(task_coordinator):
    """Teste la détermination de l'agent approprié."""
    task_coordinator.agent_capabilities = {
        "agent1": ["capA", "capB"],
        "agent2": ["capB", "capC"],
        "agent3": ["capA", "capD"]
    }
    assert task_coordinator._determine_appropriate_agent(["capA", "capB"]) == "agent1"
    assert task_coordinator._determine_appropriate_agent(["capC"]) == "agent2"
    assert task_coordinator._determine_appropriate_agent(["capD", "capA"]) == "agent3" 
    assert task_coordinator._determine_appropriate_agent(["capX"]) is None 
    assert task_coordinator._determine_appropriate_agent([]) is None 

def test_decompose_objective_to_tasks_identify_arguments(task_coordinator):
    """Teste la décomposition d'un objectif d'identification d'arguments."""
    objective = {"id": "obj-identify", "description": "Identifier les arguments dans le texte.", "priority": "high"}
    tasks = task_coordinator._decompose_objective_to_tasks(objective)
    assert len(tasks) == 4
    assert tasks[0]["description"] == "Extraire les segments de texte contenant des arguments potentiels"
    assert tasks[0]["required_capabilities"] == ["text_extraction"]
    assert tasks[1]["description"] == "Identifier les prémisses et conclusions explicites"
    assert tasks[1]["required_capabilities"] == ["argument_identification"]
    for task in tasks:
        assert task["objective_id"] == "obj-identify"
        assert task["priority"] == "high"

def test_decompose_objective_to_tasks_detect_fallacies(task_coordinator):
    """Teste la décomposition d'un objectif de détection de sophismes."""
    objective = {"id": "obj-fallacy", "description": "Détecter les sophismes dans les arguments.", "priority": "medium"}
    tasks = task_coordinator._decompose_objective_to_tasks(objective)
    assert len(tasks) == 3
    assert tasks[0]["description"] == "Analyser les arguments pour détecter les sophismes formels"
    assert tasks[0]["required_capabilities"] == ["fallacy_detection", "formal_logic"]
    for task in tasks:
        assert task["objective_id"] == "obj-fallacy"
        assert task["priority"] == "medium"

def test_decompose_objective_to_tasks_analyze_logical_structure(task_coordinator):
    """Teste la décomposition d'un objectif d'analyse de structure logique."""
    objective = {"id": "obj-logic", "description": "Analyser la structure logique des arguments.", "priority": "high"}
    tasks = task_coordinator._decompose_objective_to_tasks(objective)
    assert len(tasks) == 3
    assert tasks[0]["description"] == "Formaliser les arguments en logique propositionnelle"
    assert tasks[0]["required_capabilities"] == ["formal_logic"]
    for task in tasks:
        assert task["objective_id"] == "obj-logic"
        assert task["priority"] == "high"

def test_decompose_objective_to_tasks_evaluate_consistency(task_coordinator):
    """Teste la décomposition d'un objectif d'évaluation de cohérence."""
    objective = {"id": "obj-consistency", "description": "Évaluer la cohérence des arguments.", "priority": "medium"}
    tasks = task_coordinator._decompose_objective_to_tasks(objective)
    assert len(tasks) == 3
    assert tasks[0]["description"] == "Analyser la cohérence interne des arguments"
    assert tasks[0]["required_capabilities"] == ["consistency_analysis"]
    for task in tasks:
        assert task["objective_id"] == "obj-consistency"
        assert task["priority"] == "medium"

def test_decompose_objective_to_tasks_generic(task_coordinator):
    """Teste la décomposition d'un objectif générique."""
    objective = {"id": "obj-generic", "description": "Analyser la rhétorique du discours.", "priority": "low"}
    tasks = task_coordinator._decompose_objective_to_tasks(objective)
    assert len(tasks) == 2
    assert tasks[0]["description"] == "Analyser le texte pour Analyser la rhétorique du discours."
    assert tasks[0]["required_capabilities"] == ["text_extraction"]
    assert tasks[1]["description"] == "Produire des résultats pour Analyser la rhétorique du discours."
    assert tasks[1]["required_capabilities"] == ["summary_generation"]
    for task in tasks:
        assert task["objective_id"] == "obj-generic"
        assert task["priority"] == "low"

def test_establish_task_dependencies(task_coordinator, mock_tactical_state):
    """Teste l'établissement des dépendances entre tâches."""
    tasks = [
        {"id": "obj1-task-1", "objective_id": "obj1", "description": "Identifier arguments"},
        {"id": "obj1-task-2", "objective_id": "obj1", "description": "Analyser arguments"},
        {"id": "obj2-task-1", "objective_id": "obj2", "description": "Extraire texte"},
    ]
    task_coordinator._establish_task_dependencies(tasks)
    
    mock_tactical_state.add_task_dependency.assert_any_call("obj1-task-1", "obj1-task-2")
    
    mock_tactical_state.reset_mock() 
    tasks_complex = [
        {"id": "id-args-1", "objective_id": "objA", "description": "Identifier les arguments"},
        {"id": "analyse-args-1", "objective_id": "objB", "description": "Analyser les arguments identifiés"},
        {"id": "eval-args-1", "objective_id": "objC", "description": "Évaluer la force des arguments"},
        {"id": "extract-text-1", "objective_id": "objD", "description": "Extraire le texte source"},
    ]
    task_coordinator._establish_task_dependencies(tasks_complex)
    mock_tactical_state.add_task_dependency.assert_any_call("id-args-1", "analyse-args-1")
    mock_tactical_state.add_task_dependency.assert_any_call("id-args-1", "eval-args-1")

def test_handle_task_result_objective_completion(task_coordinator, mock_tactical_state):
    """Teste la gestion du résultat d'une tâche menant à la complétion d'un objectif."""
    task_id = "task1_op"
    tactical_task_id = "obj1-task-final"
    objective_id = "obj1"

    mock_tactical_state.tasks = {
        "pending": [],
        "in_progress": [], 
        "completed": [
            {"id": "obj1-task-prev", "objective_id": objective_id},
        ], 
        "failed": []
    }
    current_task_details = {"id": tactical_task_id, "objective_id": objective_id}
    
    mock_tactical_state.tasks["in_progress"].append(current_task_details)

    def side_effect_update_status(tid, status):
        if tid == tactical_task_id and status == "completed":
            mock_tactical_state.tasks["in_progress"].remove(current_task_details)
            mock_tactical_state.tasks["completed"].append(current_task_details)
    
    mock_tactical_state.update_task_status.side_effect = side_effect_update_status
    
    with patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.RESULTS_DIR', "mocked_results_dir_path_value"):
        result_data = {
            "task_id": task_id, 
            "tactical_task_id": tactical_task_id, 
            "status": "completed", 
            "data": "some_result"
        }
        response = task_coordinator.handle_task_result(result_data)

    mock_tactical_state.update_task_status.assert_called_with(tactical_task_id, "completed")
    mock_tactical_state.add_intermediate_result.assert_called_with(tactical_task_id, result_data)
    
    task_coordinator.adapter.send_report.assert_called_once_with(
        report_type="objective_completion",
        content={
            "objective_id": objective_id,
            "status": "completed",
            "mocked_results_dir_path_value": {} 
        },
        recipient_id="strategic_manager",
        priority=MessagePriority.HIGH
    )
    assert response["status"] == "success"

def test_handle_task_result_objective_not_all_completed(task_coordinator, mock_tactical_state):
    """
    Teste la gestion du résultat d'une tâche lorsque d'autres tâches de l'objectif ne sont pas encore complétées.
    Ceci est pour couvrir les lignes 567-569 et 571.
    """
    task_id = "task_op_partial"
    tactical_task_id = "obj_partial-task1"
    objective_id = "obj_partial"

    # Une tâche de l'objectif est encore en pending
    mock_tactical_state.tasks = {
        "pending": [{"id": "obj_partial-task2", "objective_id": objective_id}],
        "in_progress": [{"id": tactical_task_id, "objective_id": objective_id}],
        "completed": [],
        "failed": []
    }
    current_task_details = {"id": tactical_task_id, "objective_id": objective_id} # La tâche qui vient de se terminer

    def side_effect_update_status(tid, status):
        if tid == tactical_task_id and status == "completed":
            # Simuler le déplacement de la tâche vers 'completed'
            mock_tactical_state.tasks["in_progress"].remove(current_task_details)
            mock_tactical_state.tasks["completed"].append(current_task_details)
    
    mock_tactical_state.update_task_status.side_effect = side_effect_update_status
    
    result_data = {
        "task_id": task_id, 
        "tactical_task_id": tactical_task_id, 
        "status": "completed", 
        "data": "some_result_partial"
    }
    
    response = task_coordinator.handle_task_result(result_data)

    mock_tactical_state.update_task_status.assert_called_with(tactical_task_id, "completed")
    mock_tactical_state.add_intermediate_result.assert_called_with(tactical_task_id, result_data)
    
    # Le rapport d'achèvement de l'objectif ne doit PAS être appelé
    task_coordinator.adapter.send_report.assert_not_called()
    assert response["status"] == "success"


def test_generate_status_report(task_coordinator, mock_tactical_state):
    """Teste la génération d'un rapport de statut, y compris la branche 'issues'."""
    mock_tactical_state.tasks = {
        "pending": [{"id": "t1", "objective_id": "obj1"}],
        "in_progress": [{"id": "t2", "objective_id": "obj1"}],
        "completed": [{"id": "t3", "objective_id": "obj2"}],
        "failed": []
    }
    mock_tactical_state.assigned_objectives = [
        {"id": "obj1", "description": "Objective 1"},
        {"id": "obj2", "description": "Objective 2"}
    ]
    # Cas 1: self.state.issues existe
    mock_tactical_state.issues = [{"issue_id": "i1", "description": "An actual issue"}]
    # S'assurer que identified_conflicts n'est pas utilisé si issues existe
    mock_tactical_state.identified_conflicts = [] 

    report_with_issues = task_coordinator.generate_status_report()

    assert report_with_issues["overall_progress"] == 1/3 
    assert len(report_with_issues["issues"]) == 1
    assert report_with_issues["issues"][0]["issue_id"] == "i1"
    task_coordinator.adapter.send_report.assert_called_with( # Ne pas utiliser assert_called_once_with car on va le rappeler
        report_type="status_update",
        content=report_with_issues, 
        recipient_id="strategic_manager",
        priority=MessagePriority.NORMAL
    )
    task_coordinator.adapter.send_report.reset_mock() # Réinitialiser pour le prochain appel

    # Cas 2: self.state.issues n'existe PAS, identified_conflicts est utilisé
    # Pour simuler que 'issues' n'existe pas, on le supprime du mock.
    # Une manière plus propre serait de créer un nouveau mock_tactical_state sans 'issues'.
    # Ou, si mock_tactical_state est une instance de MagicMock, on peut utiliser delattr.
    # Cependant, comme c'est un MagicMock(spec=TacticalState), il ne l'aura pas par défaut.
    # On va plutôt s'assurer qu'il n'est pas setté.
    
    # Créons un nouveau mock_state pour ce cas spécifique pour éviter les effets de bord.
    state_without_issues = MagicMock(spec=TacticalState)
    state_without_issues.tasks = mock_tactical_state.tasks # réutiliser la config des tâches
    state_without_issues.assigned_objectives = mock_tactical_state.assigned_objectives
    state_without_issues.get_objective_results = MagicMock(return_value={})
    state_without_issues.identified_conflicts = [{"conflict_id": "c1", "description": "A conflict from identified_conflicts"}]
    # Assurons-nous que 'issues' n'est pas un attribut pour ce mock
    # En spécifiant spec=TacticalState, si TacticalState n'a pas 'issues', hasattr retournera False.
    # Si TacticalState a 'issues', il faut le supprimer explicitement du mock ou ne pas le setter.
    # Pour ce test, on va supposer que la classe TacticalState n'a pas 'issues' par défaut,
    # ou que notre mock ne l'a pas. Si la classe l'a, il faudrait faire:
    if hasattr(state_without_issues, 'issues'):
        del state_without_issues.issues

    task_coordinator.state = state_without_issues # Remplacer temporairement l'état du coordinateur

    report_without_issues = task_coordinator.generate_status_report()
    assert len(report_without_issues["issues"]) == 1
    assert report_without_issues["issues"][0]["conflict_id"] == "c1"
    task_coordinator.adapter.send_report.assert_called_with(
        report_type="status_update",
        content=report_without_issues,
        recipient_id="strategic_manager",
        priority=MessagePriority.NORMAL
    )
    # Restaurer l'état original si nécessaire pour d'autres tests, bien que la fixture le fasse.
    task_coordinator.state = mock_tactical_state


def test_assign_task_to_operational_agent_specific_agent(task_coordinator):
    """Teste l'assignation d'une tâche à un agent spécifique."""
    task = {"id": "task1", "required_capabilities": ["capA"], "priority": "high"}
    
    with patch.object(task_coordinator, '_determine_appropriate_agent', return_value="agentX") as mock_determine:
        task_coordinator._assign_task_to_operational_agent(task)

    mock_determine.assert_called_once_with(["capA"])
    task_coordinator.adapter.assign_task.assert_called_once_with(
        task_type="operational_task",
        parameters=task,
        recipient_id="agentX",
        priority=MessagePriority.HIGH,
        requires_ack=True,
        metadata={
            "objective_id": None, 
            "task_origin": "tactical_coordinator"
        }
    )
    task_coordinator.middleware.publish.assert_not_called()

def test_assign_task_to_operational_agent_publish_task(task_coordinator):
    """Teste la publication d'une tâche lorsqu'aucun agent spécifique n'est trouvé."""
    task = {"id": "task2", "required_capabilities": ["capB"], "priority": "low", "objective_id": "objTest"}
    
    with patch.object(task_coordinator, '_determine_appropriate_agent', return_value=None) as mock_determine:
        task_coordinator._assign_task_to_operational_agent(task)

    mock_determine.assert_called_once_with(["capB"])
    
    task_coordinator.middleware.publish.assert_called_once_with(
        topic_id="operational_tasks.capB",
        sender="tactical_coordinator",
        sender_level=AgentLevel.TACTICAL,
        content={
            "task_type": "operational_task",
            "task_data": task
        },
        priority=MessagePriority.LOW,
        metadata={
            "objective_id": "objTest",
            "requires_capabilities": ["capB"]
        }
    )
    task_coordinator.adapter.assign_task.assert_not_called()

def test_apply_strategic_adjustments_objective_modification(task_coordinator):
    """Teste l'application d'ajustements stratégiques pour la modification d'objectifs."""
    adjustments = {
        "objective_modifications": [
            {"id": "obj1", "action": "modify", "updates": {"priority": "critical"}}
        ]
    }
    task_in_state = {"id": "task_for_obj1", "objective_id": "obj1", "required_capabilities": ["capTest"]}
    task_coordinator.state.tasks["pending"] = [task_in_state]

    with patch.object(task_coordinator, '_determine_appropriate_agent', return_value="agent_assigned_to_task") as mock_determine_agent:
        task_coordinator._apply_strategic_adjustments(adjustments)
    
    assert task_in_state["priority"] == "critical" 
    
    mock_determine_agent.assert_called_with(["capTest"])
    task_coordinator.adapter.send_status_update.assert_called_with(
        update_type="task_priority_change",
        status={
            "task_id": "task_for_obj1",
            "new_priority": "critical"
        },
        recipient_id="agent_assigned_to_task" 
    )

def test_apply_strategic_adjustments_resource_reallocation(task_coordinator):
    """Teste l'application d'ajustements stratégiques pour la réallocation de ressources."""
    adjustments = {
        "resource_reallocation": {
            "informal_analyzer": {"new_config": "config_value"}
        }
    }
    task_coordinator.agent_capabilities["informal_analyzer"] = ["some_capability"]

    task_coordinator._apply_strategic_adjustments(adjustments)
    
    task_coordinator.adapter.send_status_update.assert_called_once_with(
        update_type="resource_allocation_change",
        status={
            "resource": "informal_analyzer",
            "updates": {"new_config": "config_value"}
        },
        recipient_id="informal_analyzer"
    )

def test_handle_directive_strategic_adjustment(mock_tactical_state, mock_middleware):
    """Teste la gestion d'une directive d'ajustement stratégique."""
    adjustment_content = {"objective_modifications": [{"id": "obj1", "action": "modify", "updates": {"priority": "urgent"}}]}
    message_content = {
        "directive_type": "strategic_adjustment",
        "content": adjustment_content
    }
    message = Message(
        message_id="msg_adjust",
        sender="strategic_manager",
        recipient="tactical_coordinator",
        message_type=MessageType.COMMAND,
        content=message_content,
        timestamp="2023-01-02T00:00:00Z",
        priority=MessagePriority.HIGH,
        sender_level=AgentLevel.STRATEGIC
    )

    callback_handler = None
    def mock_subscribe_capture(subscriber_id, callback, filter_criteria):
        nonlocal callback_handler
        callback_handler = callback

    local_mock_middleware_adjust = MagicMock(spec=MessageMiddleware)
    mock_channel_for_adjust = MagicMock()
    mock_channel_for_adjust.subscribe.side_effect = mock_subscribe_capture
    local_mock_middleware_adjust.get_channel.return_value = mock_channel_for_adjust

    with patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter') as MockFreshAdapterClassAdjust, \
         patch.object(TaskCoordinator, '_apply_strategic_adjustments') as mock_apply_adjustments, \
         patch.object(TaskCoordinator, '_log_action') as mock_log_adjust:
        
        fresh_coordinator_adjust = TaskCoordinator(tactical_state=mock_tactical_state, middleware=local_mock_middleware_adjust)
        fresh_coordinator_adjust.adapter = MockFreshAdapterClassAdjust.return_value
        
        assert callback_handler is not None, "Callback for adjustment was not captured"
        callback_handler(message)

    mock_apply_adjustments.assert_called_once_with(adjustment_content)
    mock_log_adjust.assert_called()
    
    fresh_coordinator_adjust.adapter.send_report.assert_called_once_with(
        report_type="adjustment_acknowledgement",
        content={"status": "applied"},
        recipient_id="strategic_manager",
        priority=MessagePriority.NORMAL
    )

def test_handle_task_result_missing_tactical_task_id(task_coordinator):
    """Teste la gestion d'un résultat de tâche sans ID de tâche tactique."""
    result_data = {
        "task_id": "op_task_id_only",
        "status": "completed",
        "data": "some_data"
    }
    response = task_coordinator.handle_task_result(result_data)
    assert response["status"] == "error"
    assert "Identifiant de tâche tactique manquant" in response["message"]
    task_coordinator.state.update_task_status.assert_not_called()
    task_coordinator.state.add_intermediate_result.assert_not_called()
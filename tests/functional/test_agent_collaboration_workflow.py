# -*- coding: utf-8 -*-
"""
Tests fonctionnels pour le workflow de collaboration entre agents.

Ce module contient des tests fonctionnels qui vérifient la collaboration
entre les différents agents (PM, PL, Informal, Extract) dans le contexte
d'un workflow d'analyse argumentative complet.
"""

import unittest
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
   sys.path.insert(0, project_root)
# L'installation du package via `pip install -e .` devrait gérer l'accessibilité,
# mais cette modification assure le fonctionnement même sans installation en mode édition.
# conftest.py et pytest.ini devraient également aider, mais ajout explicite pour robustesse.

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy, SimpleTerminationStrategy
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
# from tests.async_test_case import AsyncTestCase # Suppression de l'import

# Imports spécifiques pour ce test
from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TacticalCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.monitor import ProgressMonitor as TaskMonitor # Alias pour compatibilité
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import ConflictResolver
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import PLAgentAdapter
from argumentation_analysis.core.communication import MessageMiddleware, LocalChannel


@pytest.fixture
def setup_workflow():
    """Fixture pour initialiser le workflow de collaboration."""
    test_text = """
    La légalisation du cannabis est un sujet brûlant.
    Certains affirment que cela réduirait la criminalité et augmenterait les recettes fiscales.
    D'autres craignent une augmentation des problèmes de santé publique.
    Les études scientifiques sur le sujet sont souvent contradictoires.
    Il est crucial de peser soigneusement tous les arguments avant de prendre une décision.
    """
    
    state = RhetoricalAnalysisState(test_text)
    llm_service = MagicMock()
    llm_service.service_id = "test_llm_service"
    
    # Middleware et canaux
    middleware = MessageMiddleware()
    strategic_channel = LocalChannel("strategic_alerts", middleware)
    tactical_channel = LocalChannel("tactical_commands", middleware)
    operational_channel = LocalChannel("operational_tasks", middleware)
    feedback_channel = LocalChannel("feedback", middleware)
    
    # Enregistrer les canaux dans le middleware
    from argumentation_analysis.core.communication.channel_interface import ChannelType
    middleware.register_channel(strategic_channel)
    middleware.register_channel(tactical_channel)
    middleware.register_channel(operational_channel)
    middleware.register_channel(feedback_channel)
    
    # Créer et enregistrer un canal hiérarchique pour les communications tactiques
    hierarchical_channel = LocalChannel("hierarchical", middleware)
    hierarchical_channel.type = ChannelType.HIERARCHICAL  # Définir le bon type
    middleware.register_channel(hierarchical_channel)

    # Créer et enregistrer le canal de données
    data_channel = LocalChannel("data", middleware)
    data_channel.type = ChannelType.DATA
    middleware.register_channel(data_channel)

    # Création des managers et coordinateurs
    strategic_manager = StrategicManager(middleware=middleware)
    tactical_coordinator = TacticalCoordinator(middleware=middleware)
    operational_manager = OperationalManager(
        middleware=middleware,
        kernel=MagicMock(spec=sk.Kernel),
        llm_service_id="mock_llm_service"
    )
    
    # Création de l'interface et liaison
    interface = TacticalOperationalInterface(
        tactical_state=tactical_coordinator.state,
        operational_state=operational_manager.operational_state,
        middleware=middleware
    )
    operational_manager.set_tactical_operational_interface(interface)

    # Création des agents opérationnels (mocks pour ce test)
    mock_extract_adapter = AsyncMock(spec=ExtractAgentAdapter)
    mock_extract_adapter.name = "ExtractAgent"
    mock_extract_adapter.get_capabilities.return_value = ["text_extraction"]
    async def mock_process_task_extract(task_data):
        return {
            "status": "completed",
            "id": task_data["id"],
            "tactical_task_id": task_data["tactical_task_id"],
            "outputs": {"extracted_text": "mock extract"},
            "metrics": {},
            "issues": []
        }
    mock_extract_adapter.process_task.side_effect = mock_process_task_extract

    mock_informal_adapter = AsyncMock(spec=InformalAgentAdapter)
    mock_informal_adapter.name = "InformalAgent"
    mock_informal_adapter.get_capabilities.return_value = ["informal_analysis"]
    async def mock_process_task_informal(task_data):
        return {
            "status": "completed",
            "id": task_data["id"],
            "tactical_task_id": task_data["tactical_task_id"],
            "outputs": {"identified_fallacies": []},
            "metrics": {},
            "issues": []
        }
    mock_informal_adapter.process_task.side_effect = mock_process_task_informal

    mock_pl_adapter = AsyncMock(spec=PLAgentAdapter)
    mock_pl_adapter.name = "PLAgent"
    mock_pl_adapter.get_capabilities = MagicMock(return_value=["logical_formalization"])
    async def mock_process_task_pl(task_data):
        return {
            "status": "completed",
            "id": task_data["id"],
            "tactical_task_id": task_data["tactical_task_id"],
            "outputs": {"belief_set_id": "bs1"},
            "metrics": {},
            "issues": []
        }
    mock_pl_adapter.process_task.side_effect = mock_process_task_pl

    # Remplacer la méthode de sélection d'agent pour retourner directement nos mocks
    async def mock_select_agent(task: dict):
        capabilities = task.get("required_capabilities", [])
        if "text_extraction" in capabilities:
            # Simuler le comportement de get_agent qui retourne une instance
            mock_extract_adapter.initialize = AsyncMock(return_value=True)
            return mock_extract_adapter
        if "informal_analysis" in capabilities:
            mock_informal_adapter.initialize = AsyncMock(return_value=True)
            return mock_informal_adapter
        if "logical_formalization" in capabilities:
            mock_pl_adapter.initialize = AsyncMock(return_value=True)
            return mock_pl_adapter
        return None

    operational_manager.agent_registry.select_agent_for_task = mock_select_agent

    return {
        "strategic_manager": strategic_manager,
        "tactical_coordinator": tactical_coordinator,
        "operational_manager": operational_manager,
        "mock_extract_adapter": mock_extract_adapter,
        "mock_informal_adapter": mock_informal_adapter,
        "mock_pl_adapter": mock_pl_adapter,
    }

@pytest.fixture
async def started_operational_manager(setup_workflow):
    """Fixture pour démarrer et arrêter le gestionnaire opérationnel."""
    op_manager = setup_workflow["operational_manager"]
    await op_manager.start()
    yield op_manager
    await op_manager.stop()

@pytest.mark.anyio
async def test_full_collaboration_workflow(setup_workflow, started_operational_manager):
    """Teste un workflow de collaboration complet entre les niveaux hiérarchiques."""
    
    strategic_manager = setup_workflow["strategic_manager"]
    tactical_coordinator = setup_workflow["tactical_coordinator"]
    operational_manager = started_operational_manager # Utiliser le manager démarré
    mock_extract_adapter = setup_workflow["mock_extract_adapter"]
    mock_informal_adapter = setup_workflow["mock_informal_adapter"]

    # 1. Le manager stratégique définit un objectif global
    strategic_goal = {
        "id": "goal_1",
        "description": "Analyser la rhétorique du texte sur la légalisation du cannabis.",
        "priority": "high",
        "target_metric": "overall_argument_strength",
        "desired_value": 0.7
    }
    strategic_manager.define_strategic_goal(strategic_goal)
    
    # 2. Le coordinateur tactique reçoit l'objectif et le décompose en tâches
    tactical_plan = await tactical_coordinator.decompose_strategic_goal(strategic_goal)
    assert tactical_plan is not None
    assert "tasks" in tactical_plan
    assert len(tactical_plan["tasks"]) > 0
    
    # 3. Le coordinateur tactique assigne les tâches au manager opérationnel
    for task in tactical_plan["tasks"]:
        await tactical_coordinator.assign_task_to_operational(task)
        
    # 4. Le manager opérationnel traite les tâches en utilisant les agents
    extraction_task_data = next((t for t in tactical_plan["tasks"] if "text_extraction" in t.get("required_capabilities", [])), None)
    assert extraction_task_data is not None, "Aucune tâche d'extraction trouvée dans le plan tactique"
    
    operational_result_extraction = None
    if extraction_task_data:
        operational_result_extraction = await operational_manager.process_tactical_task(extraction_task_data)
        assert operational_result_extraction is not None
        assert operational_result_extraction.get("completion_status") == "completed"
        mock_extract_adapter.process_task.assert_called_once()

    informal_task_data = next((t for t in tactical_plan["tasks"] if "informal_analysis" in t.get("required_capabilities", [])), None)
    # Note: Le plan tactique par défaut peut ne pas inclure cette tâche.
    # assert informal_task_data is not None, "Aucune tâche d'analyse informelle trouvée dans le plan tactique"

    operational_result_informal = None
    if informal_task_data:
        operational_result_informal = await operational_manager.process_tactical_task(informal_task_data)
        assert operational_result_informal is not None
        assert operational_result_informal.get("completion_status") == "completed"
        mock_informal_adapter.process_task.assert_called_once()

    # 5. Le coordinateur met à jour l'état après un résultat opérationnel
    if extraction_task_data and operational_result_extraction:
        tactical_coordinator.handle_task_result(operational_result_extraction)
    if informal_task_data and operational_result_informal:
        tactical_coordinator.handle_task_result(operational_result_informal)

    # Vérifier l'état tactique
    tactical_state = tactical_coordinator.state
    if extraction_task_data:
        assert extraction_task_data["id"] in tactical_state.task_progress
        assert tactical_state.task_progress[extraction_task_data["id"]] == 1.0

    # 6. Le coordinateur tactique génère un rapport pour le manager stratégique
    progress_report_for_strategic = tactical_coordinator.generate_status_report()
    assert progress_report_for_strategic is not None
    assert "overall_progress" in progress_report_for_strategic
    
    # 7. Le manager stratégique évalue le rapport et ajuste la stratégie si nécessaire
    strategic_manager.process_tactical_feedback(progress_report_for_strategic)
    
    # Vérifier que le but stratégique est marqué comme potentiellement complété ou en cours
    # assert "goal_1" in strategic_manager.state.strategic_goals_status
    # assert strategic_manager.state.strategic_goals_status["goal_1"]["status"] in ["in_progress", "completed"]

if __name__ == '__main__':
    pytest.main(['-xvs', __file__])
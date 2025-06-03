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
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import PLAgentAdapter
from argumentation_analysis.core.communication import MessageMiddleware, LocalChannel


class TestAgentCollaborationWorkflow: # Suppression de l'héritage AsyncTestCase
    """Tests fonctionnels pour le workflow de collaboration entre agents."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.test_text = """
        La légalisation du cannabis est un sujet brûlant. 
        Certains affirment que cela réduirait la criminalité et augmenterait les recettes fiscales.
        D'autres craignent une augmentation des problèmes de santé publique.
        Les études scientifiques sur le sujet sont souvent contradictoires.
        Il est crucial de peser soigneusement tous les arguments avant de prendre une décision.
        """
        
        self.state = RhetoricalAnalysisState(self.test_text)
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_llm_service"
        
        # Middleware et canaux
        self.middleware = MessageMiddleware()
        self.strategic_channel = LocalChannel("strategic_alerts", self.middleware)
        self.tactical_channel = LocalChannel("tactical_commands", self.middleware)
        self.operational_channel = LocalChannel("operational_tasks", self.middleware)
        self.feedback_channel = LocalChannel("feedback", self.middleware)
        
        # Enregistrer les canaux dans le middleware
        from argumentation_analysis.core.communication.channel_interface import ChannelType
        self.middleware.register_channel(self.strategic_channel)
        self.middleware.register_channel(self.tactical_channel)
        self.middleware.register_channel(self.operational_channel)
        self.middleware.register_channel(self.feedback_channel)
        
        # Créer et enregistrer un canal hiérarchique pour les communications tactiques
        self.hierarchical_channel = LocalChannel("hierarchical", self.middleware)
        self.hierarchical_channel.type = ChannelType.HIERARCHICAL  # Définir le bon type
        self.middleware.register_channel(self.hierarchical_channel)

        # Création des managers et coordinateurs
        self.strategic_manager = StrategicManager(middleware=self.middleware)
        self.tactical_coordinator = TacticalCoordinator(middleware=self.middleware)
        self.operational_manager = OperationalManager(middleware=self.middleware)
        
        # Création des agents opérationnels (mocks pour ce test)
        self.mock_extract_adapter = MagicMock(spec=ExtractAgentAdapter)
        self.mock_extract_adapter.name = "ExtractAgent"
        self.mock_extract_adapter.get_capabilities = MagicMock(return_value=["text_extraction"])
        self.mock_extract_adapter.process_task = AsyncMock(return_value={"status": "completed", "outputs": {"extracted_text": "mock extract"}, "metrics": {}, "issues": []})

        self.mock_informal_adapter = MagicMock(spec=InformalAgentAdapter)
        self.mock_informal_adapter.name = "InformalAgent"
        self.mock_informal_adapter.get_capabilities = MagicMock(return_value=["informal_analysis"])
        self.mock_informal_adapter.process_task = AsyncMock(return_value={"status": "completed", "outputs": {"identified_fallacies": []}, "metrics": {}, "issues": []})

        self.mock_pl_adapter = MagicMock(spec=PLAgentAdapter)
        self.mock_pl_adapter.name = "PLAgent"
        self.mock_pl_adapter.get_capabilities = MagicMock(return_value=["logical_formalization"])
        self.mock_pl_adapter.process_task = AsyncMock(return_value={"status": "completed", "outputs": {"belief_set_id": "bs1"}, "metrics": {}, "issues": []})

        # Enregistrement des agents mocks dans le manager opérationnel
        self.operational_manager.agent_registry.register_agent_class("extract", self.mock_extract_adapter)
        self.operational_manager.agent_registry.register_agent_class("informal", self.mock_informal_adapter)
        self.operational_manager.agent_registry.register_agent_class("pl", self.mock_pl_adapter)


    @pytest.mark.anyio
    async def test_full_collaboration_workflow(self):
        """Teste un workflow de collaboration complet entre les niveaux hiérarchiques."""
        
        # 1. Le manager stratégique définit un objectif global
        strategic_goal = {
            "id": "goal_1",
            "description": "Analyser la rhétorique du texte sur la légalisation du cannabis.",
            "priority": 1,
            "target_metric": "overall_argument_strength",
            "desired_value": 0.7
        }
        await self.strategic_manager.define_strategic_goal(strategic_goal)
        
        # Vérifier que l'objectif a été transmis au coordinateur tactique (via middleware)
        # Pour ce test, on va directement appeler le coordinateur tactique comme si le message était reçu
        
        # 2. Le coordinateur tactique reçoit l'objectif et le décompose en tâches
        tactical_plan = await self.tactical_coordinator.decompose_strategic_goal(strategic_goal)
        self.assertIsNotNone(tactical_plan)
        self.assertIn("tasks", tactical_plan)
        self.assertGreater(len(tactical_plan["tasks"]), 0)
        
        # 3. Le coordinateur tactique assigne les tâches au manager opérationnel
        for task in tactical_plan["tasks"]:
            await self.tactical_coordinator.assign_task_to_operational(task)
            
        # Vérifier que le manager opérationnel a reçu les tâches (via middleware)
        # Pour ce test, on va directement appeler le manager opérationnel
        
        # 4. Le manager opérationnel traite les tâches en utilisant les agents
        # On simule la réception et le traitement d'une tâche d'extraction
        extraction_task_data = next((t for t in tactical_plan["tasks"] if "extraction" in t.get("required_capabilities", [])), None)
        self.assertIsNotNone(extraction_task_data, "Aucune tâche d'extraction trouvée dans le plan tactique")
        
        if extraction_task_data:
            operational_result_extraction = await self.operational_manager.process_task_request(extraction_task_data)
            self.assertEqual(operational_result_extraction["status"], "completed")
            self.mock_extract_adapter.process_task.assert_called_once() # Vérifie que l'agent a été appelé
        
        # On simule la réception et le traitement d'une tâche d'analyse informelle
        informal_task_data = next((t for t in tactical_plan["tasks"] if "informal_analysis" in t.get("required_capabilities", [])), None)
        self.assertIsNotNone(informal_task_data, "Aucune tâche d'analyse informelle trouvée dans le plan tactique")

        if informal_task_data:
            operational_result_informal = await self.operational_manager.process_task_request(informal_task_data)
            self.assertEqual(operational_result_informal["status"], "completed")
            self.mock_informal_adapter.process_task.assert_called_once()

        # 5. Le moniteur de progression (TaskMonitor) suit l'avancement
        # (Normalement, le moniteur écouterait les messages de statut)
        # Ici, on peut vérifier l'état tactique après traitement des tâches
        # Supposons que les tâches opérationnelles mettent à jour l'état tactique via le coordinateur
        
        # Exemple: le coordinateur met à jour l'état après un résultat opérationnel
        if extraction_task_data and operational_result_extraction:
             await self.tactical_coordinator.update_task_status_from_operational(operational_result_extraction)
        if informal_task_data and operational_result_informal:
            await self.tactical_coordinator.update_task_status_from_operational(operational_result_informal)

        # Vérifier l'état tactique
        tactical_state = self.tactical_coordinator.state
        if extraction_task_data:
            self.assertIn(extraction_task_data["id"], tactical_state.task_progress)
            self.assertEqual(tactical_state.task_progress[extraction_task_data["id"]], 1.0) # Supposant une complétion totale
        
        # 6. Le coordinateur tactique génère un rapport pour le manager stratégique
        progress_report_for_strategic = await self.tactical_coordinator.generate_progress_report_for_strategic("goal_1")
        self.assertIsNotNone(progress_report_for_strategic)
        self.assertIn("overall_progress", progress_report_for_strategic)
        
        # 7. Le manager stratégique évalue le rapport et ajuste la stratégie si nécessaire
        await self.strategic_manager.evaluate_progress_and_adapt("goal_1", progress_report_for_strategic)
        # Pour ce test, on ne vérifie pas d'adaptation complexe de stratégie
        
        # Vérifier que le but stratégique est marqué comme potentiellement complété ou en cours
        self.assertIn("goal_1", self.strategic_manager.state.strategic_goals_status)
        self.assertIn(self.strategic_manager.state.strategic_goals_status["goal_1"]["status"], ["in_progress", "completed"])

if __name__ == '__main__':
    pytest.main(['-xvs', __file__])
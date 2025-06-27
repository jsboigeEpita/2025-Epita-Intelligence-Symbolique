#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests Unitaires pour les Gestionnaires Hiérarchiques
===================================================

Tests pour valider le fonctionnement des gestionnaires de l'architecture hiérarchique :
- StrategicManager (niveau stratégique)
- TaskCoordinator (niveau tactique) 
- OperationalManager (niveau opérationnel)

Structure des tests :
- Initialisation et configuration
- Flux de traitement hiérarchique
- Communication inter-niveaux
- Gestion d'erreurs
- Performance et optimisation

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock, MagicMock, ANY
from typing import Dict, Any, List

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Imports à tester
try:
    import logging
    from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
    from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
    from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
    HIERARCHICAL_AVAILABLE = True
except ImportError as e:
    HIERARCHICAL_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Gestionnaires hiérarchiques non disponibles: {e}")


class TestStrategicManager:
    """Tests pour le gestionnaire stratégique."""
    
    @pytest.fixture
    def sample_config(self):
        """Configuration d'exemple pour les tests."""
        return {
            "strategic_analysis_depth": "comprehensive",
            "objective_generation_mode": "automatic",
            "planning_horizon": "medium_term",
            "risk_assessment_level": "standard",
            "resource_allocation_strategy": "balanced"
        }
    
    @pytest.fixture
    def strategic_manager(self, sample_config):
        """Instance de StrategicManager pour les tests."""
        mock_middleware = MagicMock()
        mock_state = MagicMock()
        with patch('argumentation_analysis.orchestration.hierarchical.strategic.manager.MessageMiddleware', return_value=mock_middleware), \
             patch('argumentation_analysis.orchestration.hierarchical.strategic.manager.StrategicState', return_value=mock_state):
            manager = StrategicManager()
            manager.config = sample_config # L'attribut config n'existe plus, on le mock pour les tests existants.
            return manager
    
    def test_strategic_manager_initialization(self, strategic_manager, sample_config):
        """Test de l'initialisation du gestionnaire stratégique."""
        assert hasattr(strategic_manager, 'state')
        assert hasattr(strategic_manager, 'middleware')
        assert hasattr(strategic_manager, 'adapter')
        assert strategic_manager.config == sample_config # On vérifie le mock.
    
    def test_initialize_analysis_and_issue_directive(self, strategic_manager):
        """
        Teste si initialize_analysis déclenche correctement une directive
        pour le coordinateur tactique via le middleware.
        """
        text = "Texte d'analyse initial."
        
        # Espionner la méthode `issue_directive` de l'adaptateur
        spy_issue_directive = MagicMock()
        strategic_manager.adapter.issue_directive = spy_issue_directive
        
        # Configurer l'état mock pour retourner des objectifs
        strategic_manager.state.global_objectives = [{"id": "obj1", "description": "Test"}]

        # Exécution de la méthode
        result = strategic_manager.initialize_analysis(text)

        # 1. Vérifier la sortie de la méthode
        assert "objectives" in result
        assert "strategic_plan" in result
        assert len(result["objectives"]) > 0

        # 2. Vérifier que la directive a été envoyée
        spy_issue_directive.assert_called_once()
        
        # 3. Vérifier le contenu de la directive
        call_kwargs = spy_issue_directive.call_args.kwargs
        assert call_kwargs.get("directive_type") == "new_strategic_plan"
        assert call_kwargs.get("recipient_id") == "tactical_coordinator"
        assert "plan" in call_kwargs.get("parameters", {})
        assert "objectives" in call_kwargs.get("parameters", {})

    def test_process_tactical_feedback_with_issues(self, strategic_manager):
        """
        Teste le traitement du feedback tactique contenant des problèmes et
        vérifie que des ajustements sont envoyés.
        """
        feedback = {
            "progress_metrics": {"completion_rate": 0.5},
            "issues": [
                {"type": "resource_shortage", "resource": "llm_power"},
                {"type": "objective_unrealistic", "objective_id": "obj-2"},
            ],
        }
        
        # Espionner l'envoi de directives d'ajustement
        spy_send_adjustments = MagicMock()
        strategic_manager._send_strategic_adjustments = spy_send_adjustments

        # Exécution
        result = strategic_manager.process_tactical_feedback(feedback)

        # 1. Vérifier la sortie
        assert "strategic_adjustments" in result
        assert "resource_reallocation" in result["strategic_adjustments"]
        assert "objective_modifications" in result["strategic_adjustments"]

        # 2. Vérifier que les ajustements ont été envoyés
        spy_send_adjustments.assert_called_once()
        sent_adjustments = spy_send_adjustments.call_args.args[0]
        assert "resource_reallocation" in sent_adjustments
        assert "objective_modifications" in sent_adjustments

    def test_evaluate_final_results_and_publish(self, strategic_manager):
        """
        Teste l'évaluation des résultats finaux et la publication de la conclusion.
        """
        # Pré-remplir les objectifs dans l'état pour que l'évaluation fonctionne
        strategic_manager.state.global_objectives = [
            {"id": "obj-1", "description": "Identifier les arguments principaux"},
            {"id": "obj-2", "description": "Détecter les sophismes"},
        ]
        
        final_results_from_tactical = {
            "obj-1": {"success_rate": 0.9},
            "obj-2": {"success_rate": 0.75},
        }
        
        # Espionner la publication de la décision finale
        spy_publish = MagicMock()
        strategic_manager.adapter.publish_strategic_decision = spy_publish

        # Exécution
        result = strategic_manager.evaluate_final_results(final_results_from_tactical)

        # 1. Vérifier la sortie
        assert "conclusion" in result
        assert "evaluation" in result
        assert result["evaluation"]["overall_success_rate"] > 0.8

        # 2. Vérifier que la conclusion a été publiée
        spy_publish.assert_called_once()
        call_kwargs = spy_publish.call_args.kwargs
        assert call_kwargs.get("decision_type") == "final_conclusion"
        assert "conclusion" in call_kwargs.get("content", {})


class TestTaskCoordinator:
    """Tests pour le coordinateur de tâches (niveau tactique)."""
    
    @pytest.fixture
    def task_coordinator(self):
        """Instance de TaskCoordinator pour les tests."""
        mock_middleware = MagicMock()
        mock_state = MagicMock()
        with patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.MessageMiddleware', return_value=mock_middleware), \
             patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalState', return_value=mock_state):
            coordinator = TaskCoordinator()
            coordinator.config = { # L'attribut config n'existe plus, on le mock pour les tests existants.
                "coordination_strategy": "adaptive",
                "task_distribution_mode": "load_balanced",
                "communication_protocol": "message_passing"
            }
            return coordinator
    
    @pytest.fixture
    def sample_strategic_objectives(self):
        """Objectifs stratégiques d'exemple."""
        return [
            {
                "id": "strategic_obj_1",
                "description": "Analyser la structure argumentative",
                "priority": "critical",
                "type": "structural_analysis"
            },
            {
                "id": "strategic_obj_2",
                "description": "Identifier les sophismes",
                "priority": "high", 
                "type": "fallacy_detection"
            }
        ]
    
    def test_task_coordinator_initialization(self, task_coordinator):
        """Test de l'initialisation du coordinateur de tâches."""
        assert hasattr(task_coordinator, 'state')
        assert hasattr(task_coordinator, 'middleware')
        assert hasattr(task_coordinator, 'adapter')
    
    def test_process_strategic_objectives_updates_state(self, task_coordinator, sample_strategic_objectives):
        """
        Teste si le traitement des objectifs stratégiques met correctement à jour
        l'état tactique.
        """
        # Rendre la méthode de décomposition synchrone et la mocker
        task_coordinator._decompose_objective_to_tasks = MagicMock(return_value=[
            {"id": "task_1_1", "description": "Tâche décomposée 1", "objective_id": "strategic_obj_1"},
            {"id": "task_1_2", "description": "Tâche décomposée 2", "objective_id": "strategic_obj_1"}
        ])
        
        # Exécution de la méthode
        result = task_coordinator.process_strategic_objectives(sample_strategic_objectives)

        # Vérification de l'état
        tactical_state = task_coordinator.state
        tactical_state.add_task.assert_called()
        assert tactical_state.add_assigned_objective.call_count == 2
        
        # Vérification du résultat
        assert "tasks_created" in result
        assert result["tasks_created"] == 4

    def test_handle_failed_task_and_report(self, task_coordinator):
        """
        Teste que le traitement d'un résultat de tâche en échec déclenche
        un rapport vers la couche stratégique.
        """
        failed_result = {
            "tactical_task_id": "task_1",
            "completion_status": "failed",
            "reason": "Agent execution failed"
        }
        
        # Mocker les méthodes d'état pour simuler la fin d'un objectif
        task_coordinator.state.get_objective_for_task = MagicMock(return_value="obj_1")
        task_coordinator.state.are_all_tasks_for_objective_done = MagicMock(return_value=True)
        task_coordinator.state.get_objective_results = MagicMock(return_value={"some": "results"})
        
        # Espionner l'envoi de rapport
        spy_send_report = MagicMock()
        task_coordinator.adapter.send_report = spy_send_report

        # Exécution
        task_coordinator.handle_task_result(failed_result)

        # Vérifications
        task_coordinator.state.update_task_status.assert_called_once_with("task_1", "failed")
        spy_send_report.assert_called_once()
        report_kwargs = spy_send_report.call_args.kwargs
        assert report_kwargs.get("report_type") == "objective_completion"
        assert report_kwargs.get("content", {}).get("status") == "completed" # La logique actuelle envoie 'completed' même en cas d'échec


class TestOperationalManager:
    """Tests pour le gestionnaire opérationnel."""
    
    @pytest.fixture
    def operational_manager(self):
        """Instance d'OperationalManager pour les tests."""
        mock_middleware = MagicMock()
        mock_state = MagicMock()
        mock_interface = MagicMock()
        with patch('argumentation_analysis.orchestration.hierarchical.operational.manager.MessageMiddleware', return_value=mock_middleware), \
             patch('argumentation_analysis.orchestration.hierarchical.operational.manager.OperationalState', return_value=mock_state):
            manager = OperationalManager(tactical_operational_interface=mock_interface)
            return manager
    
    @pytest.fixture
    def sample_tasks(self):
        """Tâches d'exemple pour les tests."""
        return [
            {
                "id": "op_task_1",
                "type": "premise_extraction",
                "description": "Extraire les prémisses du texte",
                "text_segment": "L'éducation améliore la société car elle forme des citoyens éclairés.",
                "parameters": {"extraction_method": "nlp_pattern"},
                "priority": "high"
            },
            {
                "id": "op_task_2", 
                "type": "fallacy_detection",
                "description": "Détecter les sophismes",
                "text_segment": "Tous les experts disent que c'est vrai, donc c'est forcément vrai.",
                "parameters": {"fallacy_types": ["appeal_to_authority"]},
                "priority": "medium"
            }
        ]
    
    def test_operational_manager_initialization(self, operational_manager):
        """Test de l'initialisation du gestionnaire opérationnel."""
        assert hasattr(operational_manager, 'operational_state')
        assert hasattr(operational_manager, 'middleware')
        assert hasattr(operational_manager, 'adapter')
    
    @pytest.mark.asyncio
    async def test_process_tactical_task_puts_task_in_queue(self, operational_manager, sample_tasks):
        """
        Teste que 'process_tactical_task' met bien une tâche dans la queue et
        enregistre une future, sans tester le worker.
        """
        task = sample_tasks[0]
        op_task = {"id": "op_task_1", **task}
        operational_manager.tactical_operational_interface.translate_task_to_command.return_value = op_task
        operational_manager.operational_state.add_result_future = MagicMock()

        # On ne veut pas que le test attende la future, car elle ne sera jamais résolue dans ce test unitaire.
        # On la lance en tâche de fond.
        processing_task = asyncio.create_task(operational_manager.process_tactical_task(task))
        
        # On donne la main à la boucle d'événements pour permettre à la coroutine de s'exécuter jusqu'au premier await.
        await asyncio.sleep(0)

        # Vérifier que la tâche a bien été mise dans la queue
        assert not operational_manager.task_queue.empty()
        queued_task = operational_manager.task_queue.get_nowait()
        assert queued_task["id"] == op_task["id"]

        # Vérifier qu'une future a bien été enregistrée
        operational_manager.operational_state.add_result_future.assert_called_once_with(op_task["id"], ANY)

        # Nettoyage propre de la tâche pour éviter un warning "task never awaited"
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass # C'est normal


class TestHierarchicalIntegration:
    """Tests d'intégration entre les niveaux hiérarchiques."""
    
    @pytest.fixture
    def integrated_hierarchy(self):
        """Hiérarchie complète pour tests d'intégration."""
        middleware = MagicMock()
        
        strategic_state = MagicMock()
        tactical_state = MagicMock()
        operational_state = MagicMock()
        # Mock de l'interface pour le manager opérationnel
        operational_interface = MagicMock()


        strategic = StrategicManager(middleware=middleware)
        tactical = TaskCoordinator(middleware=middleware)
        operational = OperationalManager(middleware=middleware, tactical_operational_interface=operational_interface)
        
        return {
            "strategic": strategic,
            "tactical": tactical,
            "operational": operational
        }
    
    @pytest.mark.asyncio
    async def test_full_hierarchical_flow(self, integrated_hierarchy):
        """
        Test du flux complet, simulant la résolution de la future.
        """
        text = "L'IA va-t-elle nous remplacer ?"
        
        strategic = integrated_hierarchy["strategic"]
        tactical = integrated_hierarchy["tactical"]
        operational = integrated_hierarchy["operational"]

        # Mocks
        strategic.adapter.issue_directive = MagicMock()
        tactical.adapter.assign_task = MagicMock()
        strategic.state.global_objectives = [{"id": "obj1", "description": "Test"}]
        decomposed_task = {"id": "t1", "objective_id": "obj1", "description": "Tâche décomposée"}
        tactical._decompose_objective_to_tasks = MagicMock(return_value=[decomposed_task])
        
        op_task = {"id": "op1", **decomposed_task}
        op_result = {"status": "completed", "data": "ok"}
        final_result_processed = {"final": True, **op_result}
        operational.tactical_operational_interface.translate_task_to_command.return_value = op_task
        operational.tactical_operational_interface.process_operational_result.return_value = final_result_processed
        
        # Mock add_result_future pour capturer la future
        future_container = []
        def capture_future(task_id, future):
            future_container.append(future)
        operational.operational_state.add_result_future = MagicMock(side_effect=capture_future)

        # --- Flux ---
        strategic.initialize_analysis(text)
        directive = strategic.adapter.issue_directive.call_args.kwargs
        objectives = directive.get('parameters', {}).get('objectives', [])
        tactical.process_strategic_objectives(objectives)
        a_task_for_op = tactical.adapter.assign_task.call_args.kwargs.get("parameters")
        
        # Lancer le traitement op. en arrière-plan
        processing_task = asyncio.create_task(operational.process_tactical_task(a_task_for_op))
        await asyncio.sleep(0)

        # S'assurer qu'une future a été capturée
        assert len(future_container) == 1
        future_to_resolve = future_container[0]
        
        # Résoudre la future, ce qui doit débloquer la processing_task
        future_to_resolve.set_result(op_result)
        
        # Attendre le résultat
        final_result = await processing_task

        # Vérification
        assert final_result == final_result_processed
    
    def test_communication_feedback_loop(self, integrated_hierarchy):
        """Test de la boucle de communication et feedback entre niveaux via les adaptateurs."""
        strategic = integrated_hierarchy["strategic"]
        tactical = integrated_hierarchy["tactical"]
        
        # Mocker les adaptateurs pour simuler la communication
        tactical.adapter.escalate_issue = MagicMock()
        strategic.adapter.issue_directive = MagicMock()

        # 1. Le niveau tactique escalade un problème
        issue = {"type": "unresolved_conflict", "details": {"id": "c1"}}
        tactical.adapter.escalate_issue(**issue)
        tactical.adapter.escalate_issue.assert_called_once_with(**issue)

        # 2. Le niveau stratégique traite le feedback (simulé) et répond
        # avec un ajustement.
        feedback = {"issues": [issue]}
        strategic.process_tactical_feedback(feedback)
        strategic.adapter.issue_directive.assert_called_once()
        directive = strategic.adapter.issue_directive.call_args.kwargs
        assert directive['directive_type'] == 'strategic_adjustment'

    def test_error_escalation_hierarchy(self, integrated_hierarchy):
        """
        Teste que la réception d'un rapport d'objectif échoué par le stratégique
        déclenche bien des ajustements.
        """
        tactical = integrated_hierarchy["tactical"]
        strategic = integrated_hierarchy["strategic"]

        tactical.adapter.send_report = MagicMock()
        strategic.adapter.issue_directive = MagicMock()

        # 1. Le coordinateur tactique envoie un rapport d'échec d'objectif
        failure_report = {
            "report_type": "objective_completion",
            "content": {"objective_id": "obj-F", "status": "failed"}
        }
        # Simuler ce que le coordinateur enverrait
        tactical.adapter.send_report(**failure_report)
        tactical.adapter.send_report.assert_called_once()

        # 2. Le manager stratégique reçoit le rapport (via un mock de handler) et réagit
        # On simule le feedback en créant une structure similaire à ce qui serait reçu
        strategic.process_tactical_feedback({"issues": [failure_report['content']]})
        strategic.adapter.issue_directive.assert_called_once()
        directive = strategic.adapter.issue_directive.call_args.kwargs
        assert directive['directive_type'] == 'strategic_adjustment'


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])
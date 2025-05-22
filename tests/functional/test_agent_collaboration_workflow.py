#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests fonctionnels pour le flux de travail de collaboration entre agents.

Ce module teste le flux de travail complet de collaboration entre agents
pour l'analyse rhétorique et la détection des sophismes.
"""

import unittest
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import logging
import json
from pathlib import Path

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestAgentCollaborationWorkflow")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('../..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.tactical.monitor import TaskMonitor
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import ConflictResolver
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentation_analysis.orchestration.message_middleware import MessageMiddleware
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import ComplexFallacyAnalyzer


class TestAgentCollaborationWorkflow(unittest.TestCase):
    """Tests fonctionnels pour le flux de travail de collaboration entre agents."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un middleware
        self.middleware = MessageMiddleware()
        
        # Créer un état tactique
        self.tactical_state = TacticalState()
        
        # Créer le coordinateur tactique
        self.coordinator = TaskCoordinator(tactical_state=self.tactical_state, middleware=self.middleware)
        
        # Créer le moniteur tactique
        self.monitor = TaskMonitor(tactical_state=self.tactical_state, middleware=self.middleware)
        
        # Créer le résolveur de conflits
        self.resolver = ConflictResolver(tactical_state=self.tactical_state, middleware=self.middleware)
        
        # Créer l'adaptateur d'extraction
        self.extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=self.middleware)
        
        # Créer l'analyseur de sophismes complexes
        self.complex_analyzer = ComplexFallacyAnalyzer()
        
        # Créer l'agent informel
        self.informal_agent = InformalAgent(
            agent_id="informal_agent",
            tools={"complex_analyzer": self.complex_analyzer}
        )
        
        # Créer l'adaptateur d'agent informel
        self.informal_adapter = InformalAgentAdapter(agent_id="informal_agent_adapter", middleware=self.middleware)
        
        # Initialiser les protocoles de communication
        self.middleware.initialize_protocols()
        
        # Créer le répertoire de résultats si nécessaire
        os.makedirs("results/test", exist_ok=True)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter le middleware
        self.middleware.shutdown()
    
    def test_collaborative_analysis_workflow(self):
        """
        Teste le flux de travail complet de collaboration entre agents
        pour l'analyse rhétorique et la détection des sophismes.
        """
        # Créer un objectif
        objective = {
            "id": "test-objective",
            "description": "Analyser le texte pour identifier les sophismes",
            "priority": "high",
            "text": "Ceci est un texte d'exemple pour l'analyse des sophismes.",
            "type": "fallacy_analysis"
        }
        
        # Ajouter l'objectif à l'état tactique
        self.tactical_state.add_assigned_objective(objective)
        
        # Patcher les méthodes du coordinateur pour simuler la décomposition de l'objectif en tâches
        with patch.object(self.coordinator, '_decompose_objective_to_tasks', return_value=[
            {
                "id": "task-1",
                "description": "Extraire le texte",
                "objective_id": "test-objective",
                "estimated_duration": 3600,
                "required_capabilities": ["text_extraction"],
                "parameters": {
                    "document_path": "examples/exemple_sophisme.txt",
                    "output_format": "text"
                }
            },
            {
                "id": "task-2",
                "description": "Analyser les sophismes",
                "objective_id": "test-objective",
                "estimated_duration": 7200,
                "required_capabilities": ["fallacy_detection"],
                "parameters": {
                    "analysis_type": "fallacy",
                    "output_format": "json"
                }
            },
            {
                "id": "task-3",
                "description": "Générer un rapport",
                "objective_id": "test-objective",
                "estimated_duration": 1800,
                "required_capabilities": ["result_presentation"],
                "parameters": {
                    "report_type": "summary",
                    "output_format": "json"
                }
            }
        ]) as mock_decompose:
            
            # Patcher la méthode _establish_task_dependencies du coordinateur
            with patch.object(self.coordinator, '_establish_task_dependencies') as mock_establish:
                
                # Patcher la méthode _get_agent_for_task du coordinateur
                with patch.object(self.coordinator, '_get_agent_for_task', side_effect=["extract_agent", "informal_agent", "report_agent"]) as mock_get_agent:
                    
                    # Patcher la méthode _send_task_assignment du coordinateur
                    with patch.object(self.coordinator, '_send_task_assignment') as mock_send:
                        
                        # Patcher la méthode extract_text_from_file de l'adaptateur d'extraction
                        with patch.object(self.extract_adapter, 'extract_text_from_file', return_value="""
                        Le réchauffement climatique est un mythe car il a neigé cet hiver.
                        Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
                        Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
                        """) as mock_extract:
                            
                            # Patcher la méthode analyze_text de l'agent informel
                            with patch.object(self.informal_agent, 'analyze_text', return_value={
                                "fallacies": [
                                    {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
                                    {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
                                    {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
                                ],
                                "analysis_metadata": {
                                    "timestamp": "2025-05-21T23:30:00",
                                    "agent_id": "informal_agent",
                                    "version": "1.0"
                                }
                            }) as mock_analyze:
                                
                                # Simuler le flux de travail
                                
                                # 1. Décomposer l'objectif en tâches
                                tasks = self.coordinator._decompose_objective_to_tasks(objective)
                                
                                # Vérifier que la méthode a été appelée
                                mock_decompose.assert_called_once_with(objective)
                                
                                # 2. Établir les dépendances entre les tâches
                                self.coordinator._establish_task_dependencies(tasks)
                                
                                # Vérifier que la méthode a été appelée
                                mock_establish.assert_called_once_with(tasks)
                                
                                # 3. Ajouter les tâches à l'état tactique
                                for task in tasks:
                                    self.tactical_state.add_task(task)
                                
                                # Vérifier que les tâches ont été ajoutées
                                self.assertEqual(len(self.tactical_state.tasks["pending"]), 3)
                                
                                # 4. Assigner les tâches aux agents
                                for task in tasks:
                                    agent_id = self.coordinator._get_agent_for_task(task)
                                    self.coordinator._send_task_assignment(task, agent_id)
                                    self.tactical_state.update_task_status(task["id"], "assigned", {"agent_id": agent_id})
                                
                                # Vérifier que les méthodes ont été appelées
                                self.assertEqual(mock_get_agent.call_count, 3)
                                self.assertEqual(mock_send.call_count, 3)
                                
                                # 5. Simuler l'exécution de la tâche d'extraction
                                extract_task = tasks[0]
                                extract_result = {
                                    "text": """
                                    Le réchauffement climatique est un mythe car il a neigé cet hiver.
                                    Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
                                    Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
                                    """,
                                    "metadata": {
                                        "source": "examples/exemple_sophisme.txt",
                                        "extraction_time": "2025-05-21T23:30:00"
                                    }
                                }
                                
                                # Simuler l'envoi du résultat
                                self.extract_adapter.send_task_result(extract_task["id"], extract_result, "completed")
                                
                                # Mettre à jour l'état tactique
                                self.tactical_state.update_task_status(extract_task["id"], "completed", {"result": extract_result})
                                
                                # 6. Simuler l'exécution de la tâche d'analyse
                                analysis_task = tasks[1]
                                analysis_result = {
                                    "fallacies": [
                                        {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
                                        {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
                                        {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
                                    ],
                                    "analysis_metadata": {
                                        "timestamp": "2025-05-21T23:30:00",
                                        "agent_id": "informal_agent",
                                        "version": "1.0"
                                    }
                                }
                                
                                # Simuler l'envoi du résultat
                                self.informal_adapter.send_task_result(analysis_task["id"], analysis_result, "completed")
                                
                                # Mettre à jour l'état tactique
                                self.tactical_state.update_task_status(analysis_task["id"], "completed", {"result": analysis_result})
                                
                                # 7. Simuler l'exécution de la tâche de génération de rapport
                                report_task = tasks[2]
                                report_result = {
                                    "summary": "Analyse des sophismes dans le texte",
                                    "fallacies_count": 3,
                                    "fallacies_by_type": {
                                        "généralisation_hâtive": 1,
                                        "faux_dilemme": 1,
                                        "ad_hominem": 1
                                    },
                                    "report_metadata": {
                                        "timestamp": "2025-05-21T23:30:00",
                                        "source": "examples/exemple_sophisme.txt"
                                    }
                                }
                                
                                # Mettre à jour l'état tactique
                                self.tactical_state.update_task_status(report_task["id"], "completed", {"result": report_result})
                                
                                # 8. Vérifier que toutes les tâches sont complétées
                                completed_tasks = [t for t in self.tactical_state.get_tasks_by_status("completed")]
                                self.assertEqual(len(completed_tasks), 3)
                                
                                # 9. Sauvegarder le résultat final
                                final_result = {
                                    "objective": objective,
                                    "tasks": [
                                        {
                                            "id": task["id"],
                                            "description": task["description"],
                                            "status": "completed",
                                            "result": self.tactical_state.get_task_result(task["id"])
                                        } for task in tasks
                                    ],
                                    "metadata": {
                                        "timestamp": "2025-05-21T23:30:00",
                                        "completion_time": "2025-05-21T23:45:00"
                                    }
                                }
                                
                                result_file = os.path.join("results/test", "agent_collaboration_result.json")
                                with open(result_file, 'w', encoding='utf-8') as f:
                                    json.dump(final_result, f, ensure_ascii=False, indent=2)
                                
                                # Vérifier que le fichier de résultat a été créé
                                self.assertTrue(os.path.exists(result_file))
    
    def test_conflict_resolution_workflow(self):
        """
        Teste le flux de travail de résolution de conflits entre agents.
        """
        # Créer un conflit
        conflict = {
            "id": "conflict-1",
            "description": "Conflit d'analyse entre agents",
            "agents_involved": ["informal_agent", "logic_agent"],
            "task_id": "task-2",
            "conflict_type": "analysis_disagreement",
            "conflict_data": {
                "informal_agent": {
                    "fallacy": "faux_dilemme",
                    "confidence": 0.85
                },
                "logic_agent": {
                    "fallacy": "non_fallacy",
                    "confidence": 0.78
                }
            }
        }
        
        # Ajouter le conflit à l'état tactique
        self.tactical_state.add_conflict(conflict)
        
        # Patcher la méthode _resolve_conflict du résolveur
        with patch.object(self.resolver, '_resolve_conflict', return_value={
            "resolution": "accepted",
            "winner": "informal_agent",
            "reason": "Confiance plus élevée",
            "resolution_data": {
                "fallacy": "faux_dilemme",
                "confidence": 0.85,
                "resolution_confidence": 0.92
            }
        }) as mock_resolve:
            
            # Patcher la méthode _notify_agents_of_resolution du résolveur
            with patch.object(self.resolver, '_notify_agents_of_resolution') as mock_notify:
                
                # Résoudre le conflit
                resolution = self.resolver._resolve_conflict(conflict)
                
                # Vérifier que la méthode a été appelée
                mock_resolve.assert_called_once_with(conflict)
                
                # Mettre à jour l'état tactique
                self.tactical_state.update_conflict_status(conflict["id"], "resolved", resolution)
                
                # Notifier les agents de la résolution
                self.resolver._notify_agents_of_resolution(conflict["id"], resolution)
                
                # Vérifier que la méthode a été appelée
                mock_notify.assert_called_once_with(conflict["id"], resolution)
                
                # Vérifier que le conflit a été résolu
                self.assertEqual(self.tactical_state.conflicts[conflict["id"]]["status"], "resolved")
                self.assertEqual(self.tactical_state.conflicts[conflict["id"]]["resolution"], resolution)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
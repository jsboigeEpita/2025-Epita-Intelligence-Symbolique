# -*- coding: utf-8 -*-
"""
Tests pour l'interface entre les niveaux stratégique et tactique.
"""

import pytest # Ajout de pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime

from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentation_analysis.core.communication import (
    MessageMiddleware, StrategicAdapter, TacticalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TestStrategicTacticalInterface:
    """Tests pour la classe StrategicTacticalInterface."""

    @pytest.fixture
    def interface_components(self):
        """Initialise les objets nécessaires pour les tests."""
        mock_strategic_state = MagicMock(spec=StrategicState)
        mock_tactical_state = MagicMock(spec=TacticalState)
        mock_middleware = MagicMock(spec=MessageMiddleware)
        mock_strategic_adapter = MagicMock(spec=StrategicAdapter)
        mock_tactical_adapter = MagicMock(spec=TacticalAdapter)

        mock_middleware.get_adapter.side_effect = lambda agent_id, level: (
            mock_strategic_adapter if level == AgentLevel.STRATEGIC else mock_tactical_adapter
        )

        mock_strategic_state.strategic_plan = {
            "phases": [
                {"id": "phase-1", "objectives": ["obj-1", "obj-2"]},
                {"id": "phase-2", "objectives": ["obj-3"]}
            ],
            "success_criteria": {
                "phase-1": "Critères de succès pour la phase 1",
                "phase-2": "Critères de succès pour la phase 2"
            },
            "priorities": {
                "primary": "argument_identification",
                "secondary": "fallacy_detection"
            }
        }
        mock_strategic_state.global_objectives = [
            {"id": "obj-1", "description": "Identifier les arguments principaux", "priority": "high"},
            {"id": "obj-2", "description": "Détecter les sophismes dans le texte", "priority": "medium"},
            {"id": "obj-3", "description": "Analyser la structure logique des arguments", "priority": "low"}
        ]
        mock_strategic_state.global_metrics = {"progress": 0.4, "quality": 0.7, "resource_utilization": 0.6}
        mock_strategic_state.resource_allocation = {
            "agent_assignments": {"agent-1": ["obj-1"], "agent-2": ["obj-2", "obj-3"]}
        }

        interface = StrategicTacticalInterface(
            strategic_state=mock_strategic_state,
            tactical_state=mock_tactical_state,
            middleware=mock_middleware
        )
        interface.strategic_adapter = mock_strategic_adapter
        interface.tactical_adapter = mock_tactical_adapter
        
        return interface, mock_strategic_state, mock_tactical_state, mock_middleware, mock_strategic_adapter, mock_tactical_adapter

    def test_translate_objectives(self, interface_components):
        """Teste la traduction des objectifs stratégiques en directives tactiques."""
        interface, _, _, _, mock_strategic_adapter, _ = interface_components
        # Définir les objectifs à traduire
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments principaux",
                "priority": "high"
            },
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans le texte",
                "priority": "medium"
            }
        ]
        
        # Appeler la méthode à tester
        result = interface.translate_objectives(objectives)
        
        # Vérifier que la méthode issue_directive a été appelée (corrigé selon l'erreur)
        mock_strategic_adapter.issue_directive.assert_called()
        
        # Vérifier le résultat
        assert isinstance(result, dict)
        assert "objectives" in result
        assert "global_context" in result
        assert "control_parameters" in result
        
        # Vérifier que les objectifs ont été enrichis
        assert len(result["objectives"]) == 2
        for obj in result["objectives"]:
            assert "context" in obj
            assert "global_plan_phase" in obj["context"]
            assert "related_objectives" in obj["context"]
            assert "priority_level" in obj["context"]
            assert "success_criteria" in obj["context"]
    
    def test_process_tactical_report(self, interface_components):
        """Teste le traitement d'un rapport tactique."""
        interface, mock_strategic_state, _, _, mock_strategic_adapter, _ = interface_components
        # Définir un rapport tactique
        tactical_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_progress": 0.6,
            "tasks_summary": {
                "total": 10,
                "completed": 6,
                "in_progress": 2,
                "pending": 1,
                "failed": 1
            },
            "progress_by_objective": {
                "obj-1": {
                    "total_tasks": 5,
                    "completed_tasks": 4,
                    "progress": 0.8
                },
                "obj-2": {
                    "total_tasks": 3,
                    "completed_tasks": 2,
                    "progress": 0.7
                },
                "obj-3": {
                    "total_tasks": 2,
                    "completed_tasks": 0,
                    "progress": 0.1
                }
            },
            "issues": [
                {
                    "type": "blocked_task",
                    "description": "Tâche bloquée par une dépendance échouée",
                    "severity": "high",
                    "task_id": "task-1",
                    "objective_id": "obj-3",
                    "blocked_by": ["task-2"]
                },
                {
                    "type": "conflict",
                    "description": "Conflit entre résultats",
                    "severity": "medium",
                    "involved_tasks": ["task-3", "task-4"]
                }
            ],
            "conflicts": {
                "total": 2,
                "resolved": 1
            },
            "metrics": {
                "agent_utilization": {
                    "agent-1": 0.9,
                    "agent-2": 0.5
                }
            }
        }
        
        # Configurer le mock pour get_pending_reports
        mock_strategic_adapter.get_pending_reports.return_value = []
        
        # Appeler la méthode à tester
        result = interface.process_tactical_report(tactical_report)
        
        # Vérifier que la méthode get_pending_reports a été appelée
        mock_strategic_adapter.get_pending_reports.assert_called_once()
        
        # Vérifier le résultat
        assert isinstance(result, dict)
        assert "metrics" in result
        assert "issues" in result
        assert "adjustments" in result
        assert "progress_by_objective" in result
        
        # Vérifier les métriques
        assert "progress" in result["metrics"]
        assert "quality_indicators" in result["metrics"]
        assert "resource_utilization" in result["metrics"]
        
        # Vérifier les problèmes stratégiques
        assert isinstance(result["issues"], list)
        assert len(result["issues"]) > 0
        
        # Vérifier les ajustements
        assert "plan_updates" in result["adjustments"]
        assert "resource_reallocation" in result["adjustments"]
        assert "objective_modifications" in result["adjustments"]
        
        # Vérifier que la méthode update_global_metrics a été appelée
        mock_strategic_state.update_global_metrics.assert_called_once()
    
    def test_determine_phase_for_objective(self, interface_components):
        """Teste la détermination de la phase pour un objectif."""
        interface, _, _, _, _, _ = interface_components
        # Définir un objectif
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments principaux",
            "priority": "high"
        }
        
        # Appeler la méthode à tester
        result = interface._determine_phase_for_objective(objective)
        
        # Vérifier le résultat
        assert result == "phase-1"
        
        # Tester avec un objectif inconnu
        unknown_objective = {
            "id": "obj-unknown",
            "description": "Objectif inconnu",
            "priority": "medium"
        }
        
        result = interface._determine_phase_for_objective(unknown_objective)
        assert result == "unknown"
    
    def test_find_related_objectives(self, interface_components):
        """Teste la recherche d'objectifs liés."""
        interface, _, _, _, _, _ = interface_components
        # Définir un objectif
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments principaux",
            "priority": "high"
        }
        
        # Définir tous les objectifs
        all_objectives = [
            objective,
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans les arguments",
                "priority": "medium"
            },
            {
                "id": "obj-3",
                "description": "Analyser la structure logique",
                "priority": "low"
            }
        ]
        
        # Appeler la méthode à tester
        result = interface._find_related_objectives(objective, all_objectives)
        
        # Vérifier le résultat
        assert isinstance(result, list)
        assert "obj-2" in result  # Car "arguments" est présent dans les deux descriptions
        assert "obj-3" not in result  # Car pas de mots-clés communs
    
    def test_translate_priority(self, interface_components):
        """Teste la traduction de la priorité stratégique."""
        interface, _, _, _, _, _ = interface_components
        # Tester avec différentes priorités
        high_result = interface._translate_priority("high")
        medium_result = interface._translate_priority("medium")
        low_result = interface._translate_priority("low")
        unknown_result = interface._translate_priority("unknown")
        
        # Vérifier les résultats
        assert isinstance(high_result, dict)
        assert "urgency" in high_result
        assert "resource_allocation" in high_result
        assert "quality_threshold" in high_result
        
        assert high_result["urgency"] == "high"
        assert medium_result["urgency"] == "medium"
        assert low_result["urgency"] == "low"
        
        # La priorité inconnue devrait être traitée comme "medium"
        assert unknown_result["urgency"] == "medium"
    
    def test_extract_success_criteria(self, interface_components):
        """Teste l'extraction des critères de succès."""
        interface, _, _, _, _, _ = interface_components
        # Définir un objectif
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments principaux",
            "priority": "high"
        }
        
        # Appeler la méthode à tester
        result = interface._extract_success_criteria(objective)
        
        # Vérifier le résultat
        assert isinstance(result, dict)
        assert "criteria" in result
        assert "threshold" in result
        assert result["criteria"] == "Critères de succès pour la phase 1"
        
        # Tester avec un objectif sans critères de succès définis
        unknown_objective = {
            "id": "obj-unknown",
            "description": "Objectif inconnu",
            "priority": "medium"
        }
        
        result = interface._extract_success_criteria(unknown_objective)
        assert isinstance(result, dict)
        assert "criteria" in result
        assert "threshold" in result
        # Devrait utiliser les critères par défaut
        assert result["criteria"] == "Complétion satisfaisante de l'objectif"
    
    def test_determine_current_phase(self, interface_components):
        """Teste la détermination de la phase actuelle."""
        interface, mock_strategic_state, _, _, _, _ = interface_components
        # Configurer le mock pour différentes valeurs de progression
        
        # Phase initiale (progress < 0.3)
        mock_strategic_state.global_metrics = {"progress": 0.2}
        result = interface._determine_current_phase()
        assert result == "initial"
        
        # Phase intermédiaire (0.3 <= progress < 0.7)
        mock_strategic_state.global_metrics = {"progress": 0.5}
        result = interface._determine_current_phase()
        assert result == "intermediate"
        
        # Phase finale (progress >= 0.7)
        mock_strategic_state.global_metrics = {"progress": 0.8}
        result = interface._determine_current_phase()
        assert result == "final"
    
    def test_determine_primary_focus(self, interface_components):
        """Teste la détermination du focus principal."""
        interface, mock_strategic_state, _, _, _, _ = interface_components
        # Le focus devrait être déterminé en fonction des objectifs
        result = interface._determine_primary_focus()
        
        # Avec les objectifs définis dans la fixture, le focus devrait être "argument_identification"
        assert result == "argument_identification"
        
        # Modifier les objectifs pour changer le focus
        mock_strategic_state.global_objectives = [
            {"id": "obj-1", "description": "Détecter les sophismes dans le texte", "priority": "high"},
            {"id": "obj-2", "description": "Détecter d'autres sophismes", "priority": "high"},
            {"id": "obj-3", "description": "Identifier quelques arguments", "priority": "low"}
        ]
        
        result = interface._determine_primary_focus()
        assert result == "fallacy_detection"

    def test_request_tactical_status(self, interface_components):
        """Teste la demande de statut tactique."""
        interface, _, _, _, mock_strategic_adapter, _ = interface_components
        # Configurer le mock pour request_tactical_info (corrigé)
        expected_response = {
            "status": "ok",
            "progress": 0.5
        }
        mock_strategic_adapter.request_tactical_info.return_value = expected_response # Corrigé ici
        
        # Appeler la méthode à tester
        result = interface.request_tactical_status(timeout=5.0)
        
        # Vérifier le résultat
        assert result == expected_response
        
        # Vérifier que la méthode request_tactical_info a été appelée (corrigé)
        mock_strategic_adapter.request_tactical_info.assert_called_once_with( # Corrigé ici
            request_type="tactical_status",
            parameters={},
            recipient_id="tactical_coordinator",
            timeout=5.0
        )
    
    def test_send_strategic_adjustment(self, interface_components):
        """Teste l'envoi d'un ajustement stratégique."""
        interface, _, _, _, mock_strategic_adapter, _ = interface_components
        # Définir un ajustement
        adjustment = {
            "plan_updates": {
                "phase-1": {
                    "priority": "high"
                }
            },
            "urgent": True
        }
        
        # Configurer le mock pour send_directive
        mock_strategic_adapter.issue_directive.return_value = "message-id-123" # Corrigé ici
        
        # Appeler la méthode à tester
        result = interface.send_strategic_adjustment(adjustment)
        
        # Vérifier le résultat
        assert result is True
        
        # Vérifier que la méthode issue_directive a été appelée (corrigé)
        mock_strategic_adapter.issue_directive.assert_called_once_with( # Corrigé ici
            directive_type="strategic_adjustment",
            content=adjustment,
            recipient_id="tactical_coordinator",
            priority=MessagePriority.HIGH
        )
    
    def test_map_priority_to_enum(self, interface_components):
        """Teste la conversion de priorité textuelle en énumération."""
        interface, _, _, _, _, _ = interface_components
        # Tester avec différentes priorités
        assert interface._map_priority_to_enum("high") == MessagePriority.HIGH
        assert interface._map_priority_to_enum("medium") == MessagePriority.NORMAL
        assert interface._map_priority_to_enum("low") == MessagePriority.LOW
        assert interface._map_priority_to_enum("unknown") == MessagePriority.NORMAL
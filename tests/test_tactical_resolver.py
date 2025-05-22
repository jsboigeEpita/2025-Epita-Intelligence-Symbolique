#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module orchestration.hierarchical.tactical.resolver.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTacticalResolver")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import ConflictResolver
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class TestTacticalResolver(unittest.TestCase):
    """Tests unitaires pour le résolveur de conflits tactique."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique mock
        self.tactical_state = TacticalState()
        
        # Créer le résolveur de conflits
        self.resolver = ConflictResolver(tactical_state=self.tactical_state)
        
        # Ajouter des résultats intermédiaires à l'état tactique pour les tests
        self.tactical_state.intermediate_results = {
            "task-1": {
                "identified_arguments": [
                    {
                        "id": "arg-1",
                        "text": "Tous les hommes sont mortels",
                        "confidence": 0.9
                    },
                    {
                        "id": "arg-2",
                        "text": "Socrate est un homme",
                        "confidence": 0.95
                    }
                ],
                "identified_fallacies": [
                    {
                        "id": "fallacy-1",
                        "type": "Appel à l'autorité",
                        "argument_id": "arg-1",
                        "confidence": 0.7
                    }
                ]
            },
            "task-2": {
                "identified_arguments": [
                    {
                        "id": "arg-3",
                        "text": "Socrate est mortel",
                        "confidence": 0.85
                    },
                    {
                        "id": "arg-4",
                        "text": "Tous les philosophes sont mortels",
                        "confidence": 0.8
                    }
                ],
                "identified_fallacies": [
                    {
                        "id": "fallacy-2",
                        "type": "Généralisation hâtive",
                        "argument_id": "arg-4",
                        "confidence": 0.6
                    }
                ]
            }
        }
        
        # Ajouter des tâches à l'état tactique
        self.task1 = {
            "id": "task-1",
            "description": "Analyser les arguments du texte 1",
            "objective_id": "objective-1"
        }
        self.task2 = {
            "id": "task-2",
            "description": "Analyser les arguments du texte 2",
            "objective_id": "objective-1"
        }
        
        self.tactical_state.add_task(self.task1, "completed")
        self.tactical_state.add_task(self.task2, "completed")
    
    def test_initialization(self):
        """Teste l'initialisation du résolveur de conflits."""
        # Vérifier que le résolveur a été correctement initialisé
        self.assertIsNotNone(self.resolver)
        self.assertEqual(self.resolver.state, self.tactical_state)
        
        # Vérifier que les stratégies de résolution ont été définies
        self.assertIn("contradiction", self.resolver.resolution_strategies)
        self.assertIn("overlap", self.resolver.resolution_strategies)
        self.assertIn("inconsistency", self.resolver.resolution_strategies)
        self.assertIn("ambiguity", self.resolver.resolution_strategies)
    
    def test_log_action(self):
        """Teste la méthode _log_action."""
        # Appeler la méthode _log_action
        action_type = "test_action"
        description = "Test description"
        self.resolver._log_action(action_type, description)
        
        # Vérifier que l'action a été enregistrée dans l'état tactique
        self.assertEqual(len(self.tactical_state.tactical_actions_log), 1)
        action = self.tactical_state.tactical_actions_log[0]
        self.assertEqual(action["type"], action_type)
        self.assertEqual(action["description"], description)
        self.assertEqual(action["agent_id"], "conflict_resolver")
        self.assertIn("timestamp", action)
    
    def test_detect_conflicts(self):
        """Teste la méthode detect_conflicts."""
        # Créer des résultats à analyser
        results = {
            "identified_arguments": [
                {
                    "id": "arg-5",
                    "text": "Tous les hommes sont mortels",
                    "confidence": 0.9
                },
                {
                    "id": "arg-6",
                    "text": "Socrate est immortel",
                    "confidence": 0.7
                }
            ],
            "identified_fallacies": [
                {
                    "id": "fallacy-3",
                    "type": "Contradiction",
                    "argument_id": "arg-6",
                    "confidence": 0.8
                }
            ]
        }
        
        # Patcher les méthodes appelées par detect_conflicts
        with patch.object(self.resolver, '_check_argument_conflicts', return_value=[]) as mock_check_args, \
             patch.object(self.resolver, '_check_fallacy_conflicts', return_value=[]) as mock_check_fallacies:
            
            # Appeler la méthode detect_conflicts
            conflicts = self.resolver.detect_conflicts(results)
            
            # Vérifier que les méthodes ont été appelées
            mock_check_args.assert_called_once()
            mock_check_fallacies.assert_called_once()
            
            # Vérifier que la méthode retourne une liste (même vide)
            self.assertIsInstance(conflicts, list)
    
    def test_check_argument_conflicts(self):
        """Teste la méthode _check_argument_conflicts."""
        # Créer des arguments à analyser
        arguments = [
            {
                "id": "arg-5",
                "text": "Tous les hommes sont mortels",
                "confidence": 0.9
            },
            {
                "id": "arg-6",
                "text": "Socrate est immortel",
                "confidence": 0.7
            }
        ]
        
        # Créer des résultats existants
        existing_results = {
            "objective-1": {
                "task-1": {
                    "identified_arguments": [
                        {
                            "id": "arg-1",
                            "text": "Tous les hommes sont mortels",
                            "confidence": 0.9
                        },
                        {
                            "id": "arg-2",
                            "text": "Socrate est un homme",
                            "confidence": 0.95
                        }
                    ]
                },
                "task-2": {
                    "identified_arguments": [
                        {
                            "id": "arg-3",
                            "text": "Socrate est mortel",
                            "confidence": 0.85
                        }
                    ]
                }
            }
        }
        
        # Appeler la méthode _check_argument_conflicts
        conflicts = self.resolver._check_argument_conflicts(arguments, existing_results)
        
        # Vérifier que la méthode retourne une liste
        self.assertIsInstance(conflicts, list)
        
        # Vérifier que des conflits ont été détectés
        # Note: Le comportement exact dépend de l'implémentation de _check_argument_conflicts
        # Si l'implémentation détecte des conflits entre "Tous les hommes sont mortels" et
        # "Socrate est immortel", alors la liste ne devrait pas être vide
        if conflicts:
            conflict = conflicts[0]
            self.assertIn("type", conflict)
            self.assertIn("description", conflict)
            self.assertIn("arguments", conflict)
            self.assertIn("severity", conflict)
    
    def test_check_fallacy_conflicts(self):
        """Teste la méthode _check_fallacy_conflicts."""
        # Créer des sophismes à analyser
        fallacies = [
            {
                "id": "fallacy-3",
                "type": "Appel à l'autorité",
                "argument_id": "arg-5",
                "confidence": 0.8
            },
            {
                "id": "fallacy-4",
                "type": "Généralisation hâtive",
                "argument_id": "arg-6",
                "confidence": 0.7
            }
        ]
        
        # Créer des résultats existants
        existing_results = {
            "objective-1": {
                "task-1": {
                    "identified_fallacies": [
                        {
                            "id": "fallacy-1",
                            "type": "Appel à l'autorité",
                            "argument_id": "arg-1",
                            "confidence": 0.7
                        }
                    ]
                },
                "task-2": {
                    "identified_fallacies": [
                        {
                            "id": "fallacy-2",
                            "type": "Ad hominem",
                            "argument_id": "arg-3",
                            "confidence": 0.6
                        }
                    ]
                }
            }
        }
        
        # Appeler la méthode _check_fallacy_conflicts
        conflicts = self.resolver._check_fallacy_conflicts(fallacies, existing_results)
        
        # Vérifier que la méthode retourne une liste
        self.assertIsInstance(conflicts, list)
    
    def test_resolve_conflict(self):
        """Teste la méthode resolve_conflict."""
        # Créer un conflit à résoudre
        conflict = {
            "id": "conflict-1",
            "type": "contradiction",
            "description": "Contradiction entre les arguments arg-1 et arg-6",
            "arguments": ["arg-1", "arg-6"],
            "severity": "high"
        }
        
        # Patcher la méthode _resolve_contradiction
        with patch.object(self.resolver, '_resolve_contradiction', return_value={
            "status": "resolved",
            "resolution": "Argument arg-6 rejeté en faveur de arg-1",
            "confidence": 0.8
        }) as mock_resolve:
            
            # Appeler la méthode resolve_conflict
            resolution = self.resolver.resolve_conflict(conflict)
            
            # Vérifier que la méthode _resolve_contradiction a été appelée
            mock_resolve.assert_called_once_with(conflict)
            
            # Vérifier que la résolution est correcte
            self.assertEqual(resolution["status"], "resolved")
            self.assertIn("resolution", resolution)
            self.assertIn("confidence", resolution)
    
    def test_resolve_contradiction(self):
        """Teste la méthode _resolve_contradiction."""
        # Créer un conflit de type contradiction
        conflict = {
            "id": "conflict-1",
            "type": "contradiction",
            "description": "Contradiction entre les arguments arg-1 et arg-6",
            "arguments": ["arg-1", "arg-6"],
            "severity": "high"
        }
        
        # Appeler la méthode _resolve_contradiction
        resolution = self.resolver._resolve_contradiction(conflict)
        
        # Vérifier que la résolution est correcte
        self.assertIn("status", resolution)
        self.assertIn("resolution", resolution)
        self.assertIn("confidence", resolution)
    
    def test_resolve_overlap(self):
        """Teste la méthode _resolve_overlap."""
        # Créer un conflit de type overlap
        conflict = {
            "id": "conflict-2",
            "type": "overlap",
            "description": "Chevauchement entre les arguments arg-1 et arg-5",
            "arguments": ["arg-1", "arg-5"],
            "severity": "medium"
        }
        
        # Appeler la méthode _resolve_overlap
        resolution = self.resolver._resolve_overlap(conflict)
        
        # Vérifier que la résolution est correcte
        self.assertIn("status", resolution)
        self.assertIn("resolution", resolution)
        self.assertIn("confidence", resolution)
    
    def test_resolve_inconsistency(self):
        """Teste la méthode _resolve_inconsistency."""
        # Créer un conflit de type inconsistency
        conflict = {
            "id": "conflict-3",
            "type": "inconsistency",
            "description": "Incohérence entre les sophismes fallacy-1 et fallacy-3",
            "fallacies": ["fallacy-1", "fallacy-3"],
            "severity": "medium"
        }
        
        # Appeler la méthode _resolve_inconsistency
        resolution = self.resolver._resolve_inconsistency(conflict)
        
        # Vérifier que la résolution est correcte
        self.assertIn("status", resolution)
        self.assertIn("resolution", resolution)
        self.assertIn("confidence", resolution)
    
    def test_resolve_ambiguity(self):
        """Teste la méthode _resolve_ambiguity."""
        # Créer un conflit de type ambiguity
        conflict = {
            "id": "conflict-4",
            "type": "ambiguity",
            "description": "Ambiguïté dans l'argument arg-4",
            "arguments": ["arg-4"],
            "severity": "low"
        }
        
        # Appeler la méthode _resolve_ambiguity
        resolution = self.resolver._resolve_ambiguity(conflict)
        
        # Vérifier que la résolution est correcte
        self.assertIn("status", resolution)
        self.assertIn("resolution", resolution)
        self.assertIn("confidence", resolution)
    
    def test_apply_resolution(self):
        """Teste la méthode apply_resolution."""
        # Créer un conflit et sa résolution
        conflict = {
            "id": "conflict-1",
            "type": "contradiction",
            "description": "Contradiction entre les arguments arg-1 et arg-6",
            "arguments": ["arg-1", "arg-6"],
            "severity": "high"
        }
        
        resolution = {
            "status": "resolved",
            "resolution": "Argument arg-6 rejeté en faveur de arg-1",
            "confidence": 0.8,
            "action": "reject",
            "reject_argument": "arg-6"
        }
        
        # Appeler la méthode apply_resolution
        result = self.resolver.apply_resolution(conflict, resolution)
        
        # Vérifier que le résultat est correct
        self.assertIn("status", result)
        self.assertIn("applied_changes", result)
        
        # Vérifier qu'une action a été enregistrée
        self.assertGreaterEqual(len(self.tactical_state.tactical_actions_log), 1)
        action = self.tactical_state.tactical_actions_log[-1]
        self.assertEqual(action["type"], "Application de résolution")
        self.assertIn(conflict["id"], action["description"])


if __name__ == "__main__":
    unittest.main()
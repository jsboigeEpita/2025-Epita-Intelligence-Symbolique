#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests avancés pour le module orchestration.hierarchical.tactical.resolver.
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
logger = logging.getLogger("TestTacticalResolverAdvanced")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import ConflictResolver
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class TestTacticalResolverAdvanced(unittest.TestCase):
    """Tests avancés pour le résolveur de conflits tactique."""
    
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
        
        # Ajouter des conflits à l'état tactique
        self.tactical_state.identified_conflicts = [
            {
                "id": "conflict-1",
                "type": "contradiction",
                "description": "Contradiction entre les arguments arg-1 et arg-4",
                "involved_tasks": ["task-1", "task-2"],
                "severity": "high",
                "resolved": False
            },
            {
                "id": "conflict-2",
                "type": "overlap",
                "description": "Chevauchement entre les arguments arg-2 et arg-3",
                "involved_tasks": ["task-1", "task-2"],
                "severity": "medium",
                "resolved": True,
                "resolution": {
                    "method": "merge",
                    "merged_result": {
                        "id": "merged-arg-1",
                        "text": "Socrate est un homme mortel",
                        "confidence": 0.9
                    }
                }
            }
        ]
    
    def test_escalate_unresolved_conflicts(self):
        """Teste la méthode escalate_unresolved_conflicts."""
        # Appeler la méthode escalate_unresolved_conflicts
        conflicts_to_escalate = self.resolver.escalate_unresolved_conflicts()
        
        # Vérifier que des conflits ont été identifiés pour l'escalade
        self.assertIsInstance(conflicts_to_escalate, list)
        self.assertEqual(len(conflicts_to_escalate), 1)  # Seul le conflit non résolu devrait être escaladé
        
        # Vérifier les détails du conflit à escalader
        conflict = conflicts_to_escalate[0]
        self.assertEqual(conflict["conflict_id"], "conflict-1")
        self.assertEqual(conflict["conflict_type"], "contradiction")
        self.assertEqual(conflict["severity"], "high")
        self.assertEqual(conflict["involved_tasks"], ["task-1", "task-2"])
        self.assertIsNone(conflict["resolution_attempt"])
    
    def test_escalate_unresolved_conflicts_with_default_resolution(self):
        """Teste la méthode escalate_unresolved_conflicts avec une résolution par défaut."""
        # Ajouter un conflit avec une résolution par défaut
        self.tactical_state.identified_conflicts.append({
            "id": "conflict-3",
            "type": "ambiguity",
            "description": "Ambiguïté dans l'argument arg-2",
            "involved_tasks": ["task-1"],
            "severity": "low",
            "resolved": True,
            "resolution": {
                "method": "default",
                "rationale": "Résolution par défaut: conflit non résolu, escalade nécessaire"
            }
        })
        
        # Appeler la méthode escalate_unresolved_conflicts
        conflicts_to_escalate = self.resolver.escalate_unresolved_conflicts()
        
        # Vérifier que des conflits ont été identifiés pour l'escalade
        self.assertIsInstance(conflicts_to_escalate, list)
        self.assertEqual(len(conflicts_to_escalate), 2)  # Le conflit non résolu et celui avec résolution par défaut
        
        # Vérifier les détails du conflit avec résolution par défaut
        default_resolution_conflict = next((c for c in conflicts_to_escalate if c["conflict_id"] == "conflict-3"), None)
        self.assertIsNotNone(default_resolution_conflict)
        self.assertEqual(default_resolution_conflict["conflict_type"], "ambiguity")
        self.assertEqual(default_resolution_conflict["severity"], "low")
        self.assertEqual(default_resolution_conflict["involved_tasks"], ["task-1"])
        self.assertIsNotNone(default_resolution_conflict["resolution_attempt"])
        self.assertEqual(default_resolution_conflict["resolution_attempt"]["method"], "default")
    
    def test_are_arguments_contradictory(self):
        """Teste la méthode _are_arguments_contradictory."""
        # Créer des arguments contradictoires
        arg1 = {
            "id": "arg-5",
            "conclusion": "Le réchauffement climatique est réel"
        }
        arg2 = {
            "id": "arg-6",
            "conclusion": "Le réchauffement climatique n'est pas réel"
        }
        
        # Vérifier que les arguments sont détectés comme contradictoires
        result = self.resolver._are_arguments_contradictory(arg1, arg2)
        self.assertTrue(result)
        
        # Créer des arguments non contradictoires
        arg3 = {
            "id": "arg-7",
            "conclusion": "Le réchauffement climatique est réel"
        }
        arg4 = {
            "id": "arg-8",
            "conclusion": "Le réchauffement climatique est causé par l'homme"
        }
        
        # Vérifier que les arguments ne sont pas détectés comme contradictoires
        result = self.resolver._are_arguments_contradictory(arg3, arg4)
        self.assertFalse(result)
    
    def test_are_arguments_overlapping(self):
        """Teste la méthode _are_arguments_overlapping."""
        # Créer des arguments qui se chevauchent
        arg1 = {
            "id": "arg-5",
            "subject": "réchauffement climatique"
        }
        arg2 = {
            "id": "arg-6",
            "subject": "réchauffement climatique et ses effets"
        }
        
        # Vérifier que les arguments sont détectés comme se chevauchant
        result = self.resolver._are_arguments_overlapping(arg1, arg2)
        self.assertTrue(result)
        
        # Créer des arguments qui ne se chevauchent pas
        arg3 = {
            "id": "arg-7",
            "subject": "réchauffement climatique"
        }
        arg4 = {
            "id": "arg-8",
            "subject": "pollution plastique"
        }
        
        # Vérifier que les arguments ne sont pas détectés comme se chevauchant
        result = self.resolver._are_arguments_overlapping(arg3, arg4)
        self.assertFalse(result)
    
    def test_are_fallacies_contradictory(self):
        """Teste la méthode _are_fallacies_contradictory."""
        # Créer des sophismes contradictoires
        fallacy1 = {
            "id": "fallacy-3",
            "type": "Appel à l'autorité",
            "segment": "Einstein a dit que la théorie quantique est incomplète"
        }
        fallacy2 = {
            "id": "fallacy-4",
            "type": "Ad hominem",
            "segment": "Einstein a dit que la théorie quantique est incomplète"
        }
        
        # Vérifier que les sophismes sont détectés comme contradictoires
        result = self.resolver._are_fallacies_contradictory(fallacy1, fallacy2)
        self.assertTrue(result)
        
        # Créer des sophismes non contradictoires
        fallacy3 = {
            "id": "fallacy-5",
            "type": "Appel à l'autorité",
            "segment": "Einstein a dit que la théorie quantique est incomplète"
        }
        fallacy4 = {
            "id": "fallacy-6",
            "type": "Appel à l'autorité",
            "segment": "Bohr a dit que la théorie quantique est complète"
        }
        
        # Vérifier que les sophismes ne sont pas détectés comme contradictoires
        result = self.resolver._are_fallacies_contradictory(fallacy3, fallacy4)
        self.assertFalse(result)
    
    def test_are_formal_analyses_contradictory(self):
        """Teste la méthode _are_formal_analyses_contradictory."""
        # Créer des analyses formelles contradictoires
        analysis1 = {
            "id": "analysis-1",
            "argument_id": "arg-1",
            "is_valid": True
        }
        analysis2 = {
            "id": "analysis-2",
            "argument_id": "arg-1",
            "is_valid": False
        }
        
        # Vérifier que les analyses sont détectées comme contradictoires
        result = self.resolver._are_formal_analyses_contradictory(analysis1, analysis2)
        self.assertTrue(result)
        
        # Créer des analyses formelles non contradictoires
        analysis3 = {
            "id": "analysis-3",
            "argument_id": "arg-1",
            "is_valid": True
        }
        analysis4 = {
            "id": "analysis-4",
            "argument_id": "arg-2",
            "is_valid": False
        }
        
        # Vérifier que les analyses ne sont pas détectées comme contradictoires
        result = self.resolver._are_formal_analyses_contradictory(analysis3, analysis4)
        self.assertFalse(result)
    
    def test_check_formal_analysis_conflicts(self):
        """Teste la méthode _check_formal_analysis_conflicts."""
        # Créer des analyses formelles
        analyses = [
            {
                "id": "analysis-1",
                "argument_id": "arg-1",
                "is_valid": True,
                "confidence": 0.8
            },
            {
                "id": "analysis-2",
                "argument_id": "arg-2",
                "is_valid": False,
                "confidence": 0.7
            }
        ]
        
        # Créer des résultats existants avec des analyses contradictoires
        existing_results = {
            "objective-1": {
                "task-1": {
                    "formal_analyses": [
                        {
                            "id": "analysis-3",
                            "argument_id": "arg-1",
                            "is_valid": False,
                            "confidence": 0.6
                        }
                    ]
                }
            }
        }
        
        # Appeler la méthode _check_formal_analysis_conflicts
        conflicts = self.resolver._check_formal_analysis_conflicts(analyses, existing_results)
        
        # Vérifier que des conflits ont été détectés
        self.assertIsInstance(conflicts, list)
        self.assertEqual(len(conflicts), 1)
        
        # Vérifier les détails du conflit
        conflict = conflicts[0]
        self.assertEqual(conflict["type"], "contradiction")
        self.assertEqual(conflict["description"], "Contradiction dans les analyses formelles")
        self.assertEqual(conflict["severity"], "high")
        self.assertEqual(conflict["involved_tasks"], ["task-1"])
        self.assertEqual(conflict["details"]["analysis1"]["argument_id"], "arg-1")
        self.assertEqual(conflict["details"]["analysis2"]["argument_id"], "arg-1")
        self.assertTrue(conflict["details"]["analysis1"]["is_valid"])
        self.assertFalse(conflict["details"]["analysis2"]["is_valid"])


if __name__ == "__main__":
    unittest.main()
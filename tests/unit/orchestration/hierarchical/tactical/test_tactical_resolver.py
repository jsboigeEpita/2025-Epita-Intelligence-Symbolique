#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le Résolveur de Conflits de l'architecture hiérarchique.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging
from datetime import datetime

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestConflictResolver")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# L'installation du package via `pip install -e .` devrait gérer l'accessibilité,
# mais cette modification assure le fonctionnement même sans installation en mode édition.

# Import du module à tester
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import ConflictResolver
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class TestConflictResolver(unittest.TestCase):
    """Tests unitaires pour le Résolveur de Conflits."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique mock
        self.tactical_state = MagicMock(spec=TacticalState)
        self.tactical_state.log_tactical_action = MagicMock()
        self.tactical_state.add_conflict = MagicMock()
        self.tactical_state.resolve_conflict = MagicMock(return_value=True)
        self.tactical_state.intermediate_results = {}
        self.tactical_state.tasks = {
            "pending": [],
            "in_progress": [],
            "completed": [],
            "failed": []
        }
        self.tactical_state.identified_conflicts = []
        
        # Créer le résolveur de conflits
        self.resolver = ConflictResolver(tactical_state=self.tactical_state)
    
    def test_initialization(self):
        """Teste l'initialisation du résolveur de conflits."""
        # Vérifier que l'état tactique a été correctement assigné
        self.assertEqual(self.resolver.state, self.tactical_state)
        
        # Vérifier que les stratégies de résolution ont été définies
        self.assertIn("contradiction", self.resolver.resolution_strategies)
        self.assertIn("overlap", self.resolver.resolution_strategies)
        self.assertIn("inconsistency", self.resolver.resolution_strategies)
        self.assertIn("ambiguity", self.resolver.resolution_strategies)
    
    def test_detect_conflicts_with_arguments(self):
        """Teste la détection de conflits entre arguments."""
        # Configurer l'état tactique pour le test
        self.tactical_state.intermediate_results = {
            "task-1": {
                "identified_arguments": [
                    {
                        "id": "arg-1",
                        "conclusion": "Le produit est sûr",
                        "confidence": 0.7
                    }
                ]
            }
        }
        self.tactical_state.tasks = {
            "completed": [
                {
                    "id": "task-1",
                    "objective_id": "obj-1"
                }
            ],
            "pending": [],
            "in_progress": [],
            "failed": []
        }
        
        # Créer des résultats avec un argument contradictoire
        results = {
            "identified_arguments": [
                {
                    "id": "arg-2",
                    "conclusion": "Le produit n'est pas sûr",
                    "confidence": 0.8
                }
            ]
        }
        
        # Appeler la méthode detect_conflicts
        conflicts = self.resolver.detect_conflicts(results)
        
        # Vérifier que la méthode add_conflict a été appelée
        self.tactical_state.add_conflict.assert_called_once()
        
        # Vérifier les conflits détectés
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["type"], "contradiction")
        self.assertEqual(conflicts[0]["severity"], "medium")
        self.assertEqual(conflicts[0]["details"]["argument1"]["id"], "arg-2")
        self.assertEqual(conflicts[0]["details"]["argument2"]["id"], "arg-1")
    
    def test_detect_conflicts_with_fallacies(self):
        """Teste la détection de conflits entre sophismes."""
        # Configurer l'état tactique pour le test
        self.tactical_state.intermediate_results = {
            "task-1": {
                "identified_fallacies": [
                    {
                        "id": "fallacy-1",
                        "segment": "Les experts affirment que ce produit est sûr",
                        "type": "Appel à l'autorité",
                        "confidence": 0.7
                    }
                ]
            }
        }
        self.tactical_state.tasks = {
            "completed": [
                {
                    "id": "task-1",
                    "objective_id": "obj-1"
                }
            ],
            "pending": [],
            "in_progress": [],
            "failed": []
        }
        
        # Créer des résultats avec un sophisme contradictoire
        results = {
            "identified_fallacies": [
                {
                    "id": "fallacy-2",
                    "segment": "Les experts affirment que ce produit est sûr",
                    "type": "Faux dilemme",
                    "confidence": 0.8
                }
            ]
        }
        
        # Appeler la méthode detect_conflicts
        conflicts = self.resolver.detect_conflicts(results)
        
        # Vérifier que la méthode add_conflict a été appelée
        self.tactical_state.add_conflict.assert_called_once()
        
        # Vérifier les conflits détectés
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["type"], "contradiction")
        self.assertEqual(conflicts[0]["severity"], "medium")
        self.assertEqual(conflicts[0]["details"]["fallacy1"]["id"], "fallacy-2")
        self.assertEqual(conflicts[0]["details"]["fallacy2"]["id"], "fallacy-1")
    
    def test_detect_conflicts_with_formal_analyses(self):
        """Teste la détection de conflits entre analyses formelles."""
        # Configurer l'état tactique pour le test
        self.tactical_state.intermediate_results = {
            "task-1": {
                "formal_analyses": [
                    {
                        "id": "analysis-1",
                        "argument_id": "arg-1",
                        "is_valid": True,
                        "confidence": 0.7
                    }
                ]
            }
        }
        self.tactical_state.tasks = {
            "completed": [
                {
                    "id": "task-1",
                    "objective_id": "obj-1"
                }
            ],
            "pending": [],
            "in_progress": [],
            "failed": []
        }
        
        # Créer des résultats avec une analyse formelle contradictoire
        results = {
            "formal_analyses": [
                {
                    "id": "analysis-2",
                    "argument_id": "arg-1",
                    "is_valid": False,
                    "confidence": 0.8
                }
            ]
        }
        
        # Appeler la méthode detect_conflicts
        conflicts = self.resolver.detect_conflicts(results)
        
        # Vérifier que la méthode add_conflict a été appelée
        self.tactical_state.add_conflict.assert_called_once()
        
        # Vérifier les conflits détectés
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["type"], "contradiction")
        self.assertEqual(conflicts[0]["severity"], "high")
        self.assertEqual(conflicts[0]["details"]["analysis1"]["id"], "analysis-2")
        self.assertEqual(conflicts[0]["details"]["analysis2"]["id"], "analysis-1")
    
    def test_are_arguments_contradictory(self):
        """Teste la méthode _are_arguments_contradictory."""
        # Cas 1: Arguments contradictoires
        arg1 = {"conclusion": "Le produit est sûr"}
        arg2 = {"conclusion": "Le produit n'est pas sûr"}
        self.assertTrue(self.resolver._are_arguments_contradictory(arg1, arg2))
        
        # Cas 2: Arguments non contradictoires
        arg1 = {"conclusion": "Le produit est sûr"}
        arg2 = {"conclusion": "Le produit est efficace"}
        self.assertFalse(self.resolver._are_arguments_contradictory(arg1, arg2))
        
        # Cas 3: Arguments sans conclusion
        arg1 = {"premise": "Le produit a été testé"}
        arg2 = {"premise": "Le produit n'a pas été testé"}
        self.assertFalse(self.resolver._are_arguments_contradictory(arg1, arg2))
    
    def test_are_arguments_overlapping(self):
        """Teste la méthode _are_arguments_overlapping."""
        # Cas 1: Arguments se chevauchant
        arg1 = {"subject": "sécurité du produit"}
        arg2 = {"subject": "sécurité du produit X"}
        self.assertTrue(self.resolver._are_arguments_overlapping(arg1, arg2))
        
        # Cas 2: Arguments ne se chevauchant pas
        arg1 = {"subject": "sécurité du produit"}
        arg2 = {"subject": "efficacité du produit"}
        self.assertFalse(self.resolver._are_arguments_overlapping(arg1, arg2))
        
        # Cas 3: Arguments sans sujet
        arg1 = {"conclusion": "Le produit est sûr"}
        arg2 = {"conclusion": "Le produit est efficace"}
        self.assertFalse(self.resolver._are_arguments_overlapping(arg1, arg2))
    
    def test_are_fallacies_contradictory(self):
        """Teste la méthode _are_fallacies_contradictory."""
        # Cas 1: Sophismes contradictoires
        fallacy1 = {"segment": "Les experts affirment", "type": "Appel à l'autorité"}
        fallacy2 = {"segment": "Les experts affirment", "type": "Faux dilemme"}
        self.assertTrue(self.resolver._are_fallacies_contradictory(fallacy1, fallacy2))
        
        # Cas 2: Sophismes non contradictoires
        fallacy1 = {"segment": "Les experts affirment", "type": "Appel à l'autorité"}
        fallacy2 = {"segment": "Les experts affirment", "type": "Appel à l'autorité"}
        self.assertFalse(self.resolver._are_fallacies_contradictory(fallacy1, fallacy2))
        
        # Cas 3: Sophismes sans segment ou type
        fallacy1 = {"confidence": 0.7}
        fallacy2 = {"confidence": 0.8}
        self.assertFalse(self.resolver._are_fallacies_contradictory(fallacy1, fallacy2))
    
    def test_are_formal_analyses_contradictory(self):
        """Teste la méthode _are_formal_analyses_contradictory."""
        # Cas 1: Analyses contradictoires
        analysis1 = {"argument_id": "arg-1", "is_valid": True}
        analysis2 = {"argument_id": "arg-1", "is_valid": False}
        self.assertTrue(self.resolver._are_formal_analyses_contradictory(analysis1, analysis2))
        
        # Cas 2: Analyses non contradictoires
        analysis1 = {"argument_id": "arg-1", "is_valid": True}
        analysis2 = {"argument_id": "arg-1", "is_valid": True}
        self.assertFalse(self.resolver._are_formal_analyses_contradictory(analysis1, analysis2))
        
        # Cas 3: Analyses pour différents arguments
        analysis1 = {"argument_id": "arg-1", "is_valid": True}
        analysis2 = {"argument_id": "arg-2", "is_valid": False}
        self.assertFalse(self.resolver._are_formal_analyses_contradictory(analysis1, analysis2))
        
        # Cas 4: Analyses sans argument_id ou is_valid
        analysis1 = {"confidence": 0.7}
        analysis2 = {"confidence": 0.8}
        self.assertFalse(self.resolver._are_formal_analyses_contradictory(analysis1, analysis2))
    
    def test_resolve_conflict_contradiction_arguments(self):
        """Teste la résolution de conflits de type contradiction entre arguments."""
        # Configurer l'état tactique pour le test
        conflict = {
            "id": "conflict-1",
            "type": "contradiction",
            "details": {
                "argument1": {
                    "id": "arg-1",
                    "conclusion": "Le produit est sûr",
                    "confidence": 0.7
                },
                "argument2": {
                    "id": "arg-2",
                    "conclusion": "Le produit n'est pas sûr",
                    "confidence": 0.8
                }
            }
        }
        self.tactical_state.identified_conflicts = [conflict]
        
        # Appeler la méthode resolve_conflict
        result = self.resolver.resolve_conflict("conflict-1")
        
        # Vérifier que la méthode resolve_conflict de l'état tactique a été appelée
        self.tactical_state.resolve_conflict.assert_called_once()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["conflict_id"], "conflict-1")
        self.assertEqual(result["conflict_type"], "contradiction")
        self.assertEqual(result["resolution"]["method"], "confidence_based")
        self.assertEqual(result["resolution"]["chosen_option"]["id"], "arg-2")
        self.assertEqual(result["resolution"]["rejected_option"]["id"], "arg-1")
    
    def test_resolve_conflict_contradiction_fallacies(self):
        """Teste la résolution de conflits de type contradiction entre sophismes."""
        # Configurer l'état tactique pour le test
        conflict = {
            "id": "conflict-1",
            "type": "contradiction",
            "details": {
                "fallacy1": {
                    "id": "fallacy-1",
                    "type": "Appel à l'autorité",
                    "confidence": 0.7
                },
                "fallacy2": {
                    "id": "fallacy-2",
                    "type": "Faux dilemme",
                    "confidence": 0.8
                }
            }
        }
        self.tactical_state.identified_conflicts = [conflict]
        
        # Appeler la méthode resolve_conflict
        result = self.resolver.resolve_conflict("conflict-1")
        
        # Vérifier que la méthode resolve_conflict de l'état tactique a été appelée
        self.tactical_state.resolve_conflict.assert_called_once()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["conflict_id"], "conflict-1")
        self.assertEqual(result["conflict_type"], "contradiction")
        self.assertEqual(result["resolution"]["method"], "confidence_based")
        self.assertEqual(result["resolution"]["chosen_option"]["id"], "fallacy-2")
        self.assertEqual(result["resolution"]["rejected_option"]["id"], "fallacy-1")
    
    def test_resolve_conflict_overlap(self):
        """Teste la résolution de conflits de type chevauchement."""
        # Configurer l'état tactique pour le test
        conflict = {
            "id": "conflict-1",
            "type": "overlap",
            "details": {
                "argument1": {
                    "id": "arg-1",
                    "premises": ["premise-1", "premise-2"],
                    "conclusion": "Le produit est sûr",
                    "confidence": 0.7
                },
                "argument2": {
                    "id": "arg-2",
                    "premises": ["premise-2", "premise-3"],
                    "conclusion": "Le produit est très sûr",
                    "confidence": 0.8
                }
            }
        }
        self.tactical_state.identified_conflicts = [conflict]
        
        # Appeler la méthode resolve_conflict
        result = self.resolver.resolve_conflict("conflict-1")
        
        # Vérifier que la méthode resolve_conflict de l'état tactique a été appelée
        self.tactical_state.resolve_conflict.assert_called_once()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["conflict_id"], "conflict-1")
        self.assertEqual(result["conflict_type"], "overlap")
        self.assertEqual(result["resolution"]["method"], "merge")
        self.assertEqual(result["resolution"]["merged_result"]["conclusion"], "Le produit est très sûr")
        self.assertEqual(len(result["resolution"]["merged_result"]["premises"]), 3)
        self.assertEqual(result["resolution"]["merged_result"]["confidence"], 0.8)
    
    def test_resolve_conflict_inconsistency(self):
        """Teste la résolution de conflits de type incohérence."""
        # Configurer l'état tactique pour le test
        conflict = {
            "id": "conflict-1",
            "type": "inconsistency"
        }
        self.tactical_state.identified_conflicts = [conflict]
        
        # Appeler la méthode resolve_conflict
        result = self.resolver.resolve_conflict("conflict-1")
        
        # Vérifier que la méthode resolve_conflict de l'état tactique a été appelée
        self.tactical_state.resolve_conflict.assert_called_once()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["conflict_id"], "conflict-1")
        self.assertEqual(result["conflict_type"], "inconsistency")
        self.assertEqual(result["resolution"]["method"], "recency")
    
    def test_resolve_conflict_ambiguity(self):
        """Teste la résolution de conflits de type ambiguïté."""
        # Configurer l'état tactique pour le test
        conflict = {
            "id": "conflict-1",
            "type": "ambiguity"
        }
        self.tactical_state.identified_conflicts = [conflict]
        
        # Appeler la méthode resolve_conflict
        result = self.resolver.resolve_conflict("conflict-1")
        
        # Vérifier que la méthode resolve_conflict de l'état tactique a été appelée
        self.tactical_state.resolve_conflict.assert_called_once()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["conflict_id"], "conflict-1")
        self.assertEqual(result["conflict_type"], "ambiguity")
        self.assertEqual(result["resolution"]["method"], "preserve_both")
    
    def test_resolve_conflict_not_found(self):
        """Teste la résolution d'un conflit non trouvé."""
        # Configurer l'état tactique pour le test
        self.tactical_state.identified_conflicts = []
        
        # Appeler la méthode resolve_conflict
        result = self.resolver.resolve_conflict("conflict-1")
        
        # Vérifier que la méthode resolve_conflict de l'état tactique n'a pas été appelée
        self.tactical_state.resolve_conflict.assert_not_called()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Conflit conflict-1 non trouvé")
    
    def test_resolve_conflict_already_resolved(self):
        """Teste la résolution d'un conflit déjà résolu."""
        # Configurer l'état tactique pour le test
        conflict = {
            "id": "conflict-1",
            "type": "contradiction",
            "resolved": True,
            "resolution": {
                "method": "confidence_based",
                "chosen_option": {"id": "arg-2"},
                "rejected_option": {"id": "arg-1"}
            }
        }
        self.tactical_state.identified_conflicts = [conflict]
        
        # Appeler la méthode resolve_conflict
        result = self.resolver.resolve_conflict("conflict-1")
        
        # Vérifier que la méthode resolve_conflict de l'état tactique n'a pas été appelée
        self.tactical_state.resolve_conflict.assert_not_called()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "already_resolved")
        self.assertEqual(result["resolution"]["method"], "confidence_based")
    
    def test_escalate_unresolved_conflicts(self):
        """Teste la méthode escalate_unresolved_conflicts."""
        # Configurer l'état tactique pour le test
        self.tactical_state.identified_conflicts = [
            {
                "id": "conflict-1",
                "type": "contradiction",
                "description": "Conflit 1",
                "severity": "high",
                "involved_tasks": ["task-1", "task-2"],
                "resolved": True,
                "resolution": {
                    "method": "confidence_based"
                }
            },
            {
                "id": "conflict-2",
                "type": "overlap",
                "description": "Conflit 2",
                "severity": "medium",
                "involved_tasks": ["task-3", "task-4"],
                "resolved": True,
                "resolution": {
                    "method": "default"
                }
            },
            {
                "id": "conflict-3",
                "type": "inconsistency",
                "description": "Conflit 3",
                "severity": "low",
                "involved_tasks": ["task-5", "task-6"],
                "resolved": False
            }
        ]
        
        # Appeler la méthode escalate_unresolved_conflicts
        conflicts = self.resolver.escalate_unresolved_conflicts()
        
        # Vérifier que la méthode log_tactical_action a été appelée
        self.tactical_state.log_tactical_action.assert_called_once()
        
        # Vérifier les conflits à escalader
        self.assertEqual(len(conflicts), 2)
        
        # Vérifier que le conflit avec méthode "default" est à escalader
        default_conflict = next((c for c in conflicts if c["conflict_id"] == "conflict-2"), None)
        self.assertIsNotNone(default_conflict)
        self.assertEqual(default_conflict["conflict_type"], "overlap")
        self.assertEqual(default_conflict["severity"], "medium")
        self.assertEqual(default_conflict["resolution_attempt"]["method"], "default")
        
        # Vérifier que le conflit non résolu est à escalader
        unresolved_conflict = next((c for c in conflicts if c["conflict_id"] == "conflict-3"), None)
        self.assertIsNotNone(unresolved_conflict)
        self.assertEqual(unresolved_conflict["conflict_type"], "inconsistency")
        self.assertEqual(unresolved_conflict["severity"], "low")
        self.assertIsNone(unresolved_conflict["resolution_attempt"])


if __name__ == "__main__":
    unittest.main()
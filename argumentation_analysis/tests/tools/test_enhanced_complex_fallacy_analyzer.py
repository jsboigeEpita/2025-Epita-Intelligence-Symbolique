#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour l'analyseur de sophismes complexes amélioré.

Ce module contient les tests unitaires pour la classe EnhancedComplexFallacyAnalyzer.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer


class TestEnhancedComplexFallacyAnalyzer(unittest.TestCase):
    """Tests pour la classe EnhancedComplexFallacyAnalyzer."""

    def setUp(self):
        """Initialise l'environnement de test."""
        self.analyzer = EnhancedComplexFallacyAnalyzer()
        
        # Exemples d'arguments pour les tests
        self.test_arguments = [
            "Les experts affirment que ce produit est sûr.",
            "Ce produit est utilisé par des millions de personnes.",
            "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
            "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
        ]
        
        self.test_context = "commercial"

    def test_initialization(self):
        """Teste l'initialisation de l'analyseur."""
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.contextual_analyzer)
        self.assertIsNotNone(self.analyzer.severity_evaluator)
        self.assertIsNotNone(self.analyzer.argument_structure_patterns)
        self.assertIsNotNone(self.analyzer.advanced_fallacy_combinations)
        self.assertEqual(len(self.analyzer.analysis_history), 0)

    def test_analyze_argument_structure(self):
        """Teste la méthode analyze_argument_structure."""
        result = self.analyzer.analyze_argument_structure(self.test_arguments, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("argument_count", result)
        self.assertEqual(result["argument_count"], len(self.test_arguments))
        self.assertIn("identified_structures", result)
        self.assertIn("argument_relations", result)
        self.assertIn("coherence_evaluation", result)
        self.assertIn("vulnerability_analysis", result)
        self.assertIn("context", result)
        self.assertEqual(result["context"], self.test_context)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que l'historique d'analyse a été mis à jour
        self.assertEqual(len(self.analyzer.analysis_history), 1)
        self.assertEqual(self.analyzer.analysis_history[0]["type"], "structure_analysis")

    def test_detect_composite_fallacies(self):
        """Teste la méthode detect_composite_fallacies."""
        result = self.analyzer.detect_composite_fallacies(self.test_arguments, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("individual_fallacies_count", result)
        self.assertIn("basic_combinations", result)
        self.assertIn("advanced_combinations", result)
        self.assertIn("fallacy_patterns", result)
        self.assertIn("composite_severity", result)
        self.assertIn("context", result)
        self.assertEqual(result["context"], self.test_context)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que l'historique d'analyse a été mis à jour
        self.assertEqual(len(self.analyzer.analysis_history), 1)
        self.assertEqual(self.analyzer.analysis_history[0]["type"], "composite_fallacy_detection")

    def test_analyze_inter_argument_coherence(self):
        """Teste la méthode analyze_inter_argument_coherence."""
        result = self.analyzer.analyze_inter_argument_coherence(self.test_arguments, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("argument_count", result)
        self.assertEqual(result["argument_count"], len(self.test_arguments))
        self.assertIn("thematic_coherence", result)
        self.assertIn("logical_coherence", result)
        self.assertIn("contradictions", result)
        self.assertIn("overall_coherence", result)
        self.assertIn("context", result)
        self.assertEqual(result["context"], self.test_context)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que l'historique d'analyse a été mis à jour
        self.assertEqual(len(self.analyzer.analysis_history), 1)
        self.assertEqual(self.analyzer.analysis_history[0]["type"], "inter_argument_coherence")

    def test_identify_argument_structures(self):
        """Teste la méthode _identify_argument_structures."""
        # Tester avec un argument contenant une structure d'autorité
        argument = "Les experts scientifiques affirment que ce produit est sûr et efficace."
        structures = self.analyzer._identify_argument_structures(argument)
        
        # Vérifier qu'au moins une structure a été identifiée
        self.assertGreater(len(structures), 0)
        
        # Vérifier qu'une structure d'autorité a été identifiée
        authority_structures = [s for s in structures if s["structure_type"] == "structure_autorité"]
        self.assertGreater(len(authority_structures), 0)

    def test_identify_argument_relations(self):
        """Teste la méthode _identify_argument_relations."""
        # Créer des arguments avec des relations évidentes
        related_arguments = [
            "Les experts affirment que ce produit est sûr.",
            "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit."
        ]
        
        relations = self.analyzer._identify_argument_relations(related_arguments)
        
        # Vérifier qu'au moins une relation a été identifiée
        self.assertGreater(len(relations), 0)

    def test_calculate_simple_similarity(self):
        """Teste la méthode _calculate_simple_similarity."""
        text1 = "Les experts affirment que ce produit est sûr."
        text2 = "Les experts disent que ce produit est sécuritaire."
        text3 = "Ce produit est complètement différent des autres."
        
        # Vérifier que des textes similaires ont un score élevé
        similarity1 = self.analyzer._calculate_simple_similarity(text1, text2)
        self.assertGreater(similarity1, 0.3)
        
        # Vérifier que des textes différents ont un score faible
        similarity2 = self.analyzer._calculate_simple_similarity(text1, text3)
        self.assertLess(similarity2, 0.3)

    def test_evaluate_argument_coherence(self):
        """Teste la méthode _evaluate_argument_coherence."""
        # Créer des arguments cohérents
        coherent_arguments = [
            "Les experts affirment que ce produit est sûr.",
            "Des études scientifiques ont confirmé cette sécurité.",
            "Par conséquent, vous pouvez utiliser ce produit en toute confiance."
        ]
        
        # Créer des relations entre ces arguments
        relations = [
            {
                "relation_type": "support",
                "source_argument_index": 0,
                "target_argument_index": 2,
                "confidence": 0.8
            },
            {
                "relation_type": "support",
                "source_argument_index": 1,
                "target_argument_index": 2,
                "confidence": 0.9
            }
        ]
        
        coherence = self.analyzer._evaluate_argument_coherence(coherent_arguments, relations)
        
        # Vérifier la structure du résultat
        self.assertIn("coherence_score", coherence)
        self.assertGreater(coherence["coherence_score"], 0.5)  # Score élevé pour des arguments cohérents

    def test_detect_circular_reasoning(self):
        """Teste la méthode _detect_circular_reasoning."""
        # Créer un graphe avec un raisonnement circulaire
        circular_graph = {
            0: [1],
            1: [2],
            2: [0]
        }
        
        # Créer un graphe sans raisonnement circulaire
        non_circular_graph = {
            0: [1],
            1: [2]
        }
        
        # Vérifier que le raisonnement circulaire est détecté
        self.assertTrue(self.analyzer._detect_circular_reasoning(circular_graph))
        
        # Vérifier que l'absence de raisonnement circulaire est correctement identifiée
        self.assertFalse(self.analyzer._detect_circular_reasoning(non_circular_graph))

    def test_analyze_structure_vulnerabilities(self):
        """Teste la méthode _analyze_structure_vulnerabilities."""
        # Créer des structures argumentatives
        argument_structures = [
            {
                "argument_index": 0,
                "argument_text": "Les experts affirment que ce produit est sûr.",
                "structures": [
                    {
                        "structure_type": "structure_autorité",
                        "description": "Arguments basés sur des autorités ou des experts",
                        "confidence": 0.8,
                        "fallacy_risk": "Appel à l'autorité, Appel à la nouveauté",
                        "complexity_score": 0.4
                    }
                ]
            }
        ]
        
        # Créer des relations entre arguments
        argument_relations = [
            {
                "relation_type": "support",
                "source_argument_index": 0,
                "target_argument_index": 1,
                "confidence": 0.8
            }
        ]
        
        vulnerabilities = self.analyzer._analyze_structure_vulnerabilities(argument_structures, argument_relations)
        
        # Vérifier la structure du résultat
        self.assertIn("vulnerability_score", vulnerabilities)
        self.assertIn("vulnerability_level", vulnerabilities)
        self.assertIn("specific_vulnerabilities", vulnerabilities)
        
        # Vérifier qu'au moins une vulnérabilité a été identifiée
        self.assertGreater(len(vulnerabilities["specific_vulnerabilities"]), 0)

    @patch('numpy.array')
    @patch('numpy.mean')
    def test_analyze_complex_fallacies_with_numpy_dependency(self, mock_mean, mock_array):
        """Teste l'analyse des sophismes complexes avec mock de numpy."""
        # Configurer les mocks numpy
        mock_array.return_value = [0.7, 0.8, 0.9]
        mock_mean.return_value = 0.8
        
        # Appeler la méthode qui utilise numpy
        result = self.analyzer.detect_composite_fallacies(self.test_arguments, self.test_context)
        
        # Vérifier que le résultat est correct
        self.assertIsNotNone(result)
        self.assertIn("composite_severity", result)
        
        # Vérifier que les mocks ont été appelés
        mock_array.assert_called()
        mock_mean.assert_called()


if __name__ == "__main__":
    unittest.main()
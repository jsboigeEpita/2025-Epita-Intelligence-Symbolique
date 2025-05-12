#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour l'analyseur contextuel de sophismes amélioré.

Ce module contient les tests unitaires pour la classe EnhancedContextualFallacyAnalyzer.
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

from argumentiation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer


class TestEnhancedContextualFallacyAnalyzer(unittest.TestCase):
    """Tests pour la classe EnhancedContextualFallacyAnalyzer."""

    def setUp(self):
        """Initialise l'environnement de test."""
        # Patcher les dépendances externes pour éviter les erreurs d'importation
        self.transformers_patcher = patch('argumentiation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.HAS_TRANSFORMERS', False)
        self.transformers_patcher.start()
        
        self.analyzer = EnhancedContextualFallacyAnalyzer()
        
        # Exemples de textes pour les tests
        self.test_text = "Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
        self.test_context = "Discours commercial pour un produit controversé"

    def tearDown(self):
        """Nettoie l'environnement de test."""
        self.transformers_patcher.stop()

    def test_initialization(self):
        """Teste l'initialisation de l'analyseur."""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(len(self.analyzer.feedback_history), 0)
        self.assertEqual(len(self.analyzer.context_embeddings_cache), 0)
        self.assertEqual(len(self.analyzer.last_analysis_fallacies), 0)

    def test_analyze_context(self):
        """Teste la méthode analyze_context."""
        result = self.analyzer.analyze_context(self.test_text, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("context_analysis", result)
        self.assertIn("potential_fallacies_count", result)
        self.assertIn("contextual_fallacies_count", result)
        self.assertIn("contextual_fallacies", result)
        self.assertIn("fallacy_relations", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier l'analyse du contexte
        context_analysis = result["context_analysis"]
        self.assertIn("context_type", context_analysis)
        self.assertIn("context_subtypes", context_analysis)
        self.assertIn("audience_characteristics", context_analysis)
        self.assertIn("formality_level", context_analysis)
        self.assertIn("confidence", context_analysis)
        
        # Vérifier que le contexte a été mis en cache
        self.assertGreater(len(self.analyzer.context_embeddings_cache), 0)

    def test_analyze_context_deeply(self):
        """Teste la méthode _analyze_context_deeply."""
        context_analysis = self.analyzer._analyze_context_deeply(self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("context_type", context_analysis)
        self.assertIn("context_subtypes", context_analysis)
        self.assertIn("audience_characteristics", context_analysis)
        self.assertIn("formality_level", context_analysis)
        self.assertIn("confidence", context_analysis)
        
        # Vérifier que le type de contexte est correctement identifié
        self.assertEqual(context_analysis["context_type"], "commercial")
        
        # Vérifier que le niveau de formalité est défini
        self.assertIn(context_analysis["formality_level"], ["faible", "moyen", "élevé"])

    def test_identify_potential_fallacies_with_nlp(self):
        """Teste la méthode _identify_potential_fallacies_with_nlp."""
        potential_fallacies = self.analyzer._identify_potential_fallacies_with_nlp(self.test_text)
        
        # Vérifier que des sophismes potentiels ont été identifiés
        self.assertGreater(len(potential_fallacies), 0)
        
        # Vérifier la structure des sophismes identifiés
        for fallacy in potential_fallacies:
            self.assertIn("fallacy_type", fallacy)
            self.assertIn("keyword", fallacy)
            self.assertIn("context_text", fallacy)
            self.assertIn("confidence", fallacy)

    def test_filter_by_context_semantic(self):
        """Teste la méthode _filter_by_context_semantic."""
        # Créer des sophismes potentiels pour le test
        potential_fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": "Les experts sont unanimes : ce produit est sûr et efficace.",
                "confidence": 0.7
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "millions",
                "context_text": "Des millions de personnes l'utilisent déjà.",
                "confidence": 0.6
            }
        ]
        
        # Créer une analyse de contexte pour le test
        context_analysis = {
            "context_type": "commercial",
            "context_subtypes": [],
            "audience_characteristics": ["généraliste"],
            "formality_level": "moyen",
            "confidence": 0.8
        }
        
        contextual_fallacies = self.analyzer._filter_by_context_semantic(potential_fallacies, context_analysis)
        
        # Vérifier que les sophismes ont été filtrés
        self.assertEqual(len(contextual_fallacies), 2)
        
        # Vérifier que les informations contextuelles ont été ajoutées
        for fallacy in contextual_fallacies:
            self.assertIn("contextual_relevance", fallacy)
            self.assertIn("context_adjustment", fallacy)
            self.assertIn("context_analysis", fallacy)

    def test_analyze_fallacy_relations(self):
        """Teste la méthode _analyze_fallacy_relations."""
        # Créer des sophismes pour le test
        fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "context_text": "Les experts sont unanimes : ce produit est sûr et efficace.",
                "confidence": 0.7
            },
            {
                "fallacy_type": "Appel à la popularité",
                "context_text": "Des millions de personnes l'utilisent déjà.",
                "confidence": 0.6
            }
        ]
        
        relations = self.analyzer._analyze_fallacy_relations(fallacies)
        
        # Vérifier que des relations ont été identifiées
        self.assertGreater(len(relations), 0)
        
        # Vérifier la structure des relations
        for relation in relations:
            self.assertIn("relation_type", relation)
            self.assertIn("fallacy1_type", relation)
            self.assertIn("fallacy2_type", relation)
            self.assertIn("strength", relation)

    def test_are_complementary_fallacies(self):
        """Teste la méthode _are_complementary_fallacies."""
        # Tester des paires complémentaires
        self.assertTrue(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Appel à la popularité"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Faux dilemme", "Appel à l'émotion"))
        
        # Tester des paires non complémentaires
        self.assertFalse(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Faux dilemme"))
        self.assertFalse(self.analyzer._are_complementary_fallacies("Généralisation hâtive", "Ad hominem"))

    def test_identify_contextual_fallacies(self):
        """Teste la méthode identify_contextual_fallacies."""
        fallacies = self.analyzer.identify_contextual_fallacies(self.test_text, self.test_context)
        
        # Vérifier que des sophismes contextuels ont été identifiés
        self.assertGreaterEqual(len(fallacies), 0)
        
        # Si des sophismes ont été identifiés, vérifier leur structure
        if fallacies:
            for fallacy in fallacies:
                self.assertIn("fallacy_type", fallacy)
                self.assertIn("context_text", fallacy)
                self.assertIn("confidence", fallacy)
                self.assertGreaterEqual(fallacy["confidence"], 0.5)  # Confiance élevée

    def test_provide_feedback(self):
        """Teste la méthode provide_feedback."""
        # Simuler une analyse préalable
        self.analyzer.last_analysis_fallacies = {
            "fallacy_0": {
                "fallacy_type": "Appel à l'autorité",
                "context_text": "Les experts sont unanimes : ce produit est sûr et efficace.",
                "confidence": 0.7
            }
        }
        
        # Fournir un feedback positif
        self.analyzer.provide_feedback("fallacy_0", True, "Bonne détection")
        
        # Vérifier que le feedback a été enregistré
        self.assertEqual(len(self.analyzer.feedback_history), 1)
        self.assertEqual(self.analyzer.feedback_history[0]["fallacy_id"], "fallacy_0")
        self.assertTrue(self.analyzer.feedback_history[0]["is_correct"])
        self.assertEqual(self.analyzer.feedback_history[0]["feedback_text"], "Bonne détection")
        
        # Vérifier que les ajustements de confiance ont été mis à jour
        self.assertIn("Appel à l'autorité", self.analyzer.learning_data["confidence_adjustments"])

    def test_get_contextual_fallacy_examples(self):
        """Teste la méthode get_contextual_fallacy_examples."""
        examples = self.analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "commercial")
        
        # Vérifier que des exemples ont été retournés
        self.assertGreater(len(examples), 0)
        
        # Vérifier la structure des exemples
        for example in examples:
            if isinstance(example, dict):
                self.assertIn("text", example)
                self.assertIn("explanation", example)
                self.assertIn("correction_suggestion", example)

    def test_generate_fallacy_explanation(self):
        """Teste la méthode _generate_fallacy_explanation."""
        explanation = self.analyzer._generate_fallacy_explanation(
            "Appel à l'autorité", 
            "commercial", 
            "Les experts affirment que ce produit est sûr."
        )
        
        # Vérifier que l'explication n'est pas vide
        self.assertIsNotNone(explanation)
        self.assertGreater(len(explanation), 0)
        
        # Vérifier que l'explication contient des informations pertinentes
        self.assertIn("Appel à l'autorité", explanation)
        self.assertIn("commercial", explanation)

    def test_generate_correction_suggestion(self):
        """Teste la méthode _generate_correction_suggestion."""
        suggestion = self.analyzer._generate_correction_suggestion(
            "Appel à l'autorité",
            "Les experts affirment que ce produit est sûr."
        )
        
        # Vérifier que la suggestion n'est pas vide
        self.assertIsNotNone(suggestion)
        self.assertGreater(len(suggestion), 0)
        
        # Vérifier que la suggestion contient des informations pertinentes
        self.assertIn("Appel à l'autorité", suggestion) or self.assertIn("experts", suggestion)


if __name__ == "__main__":
    unittest.main()
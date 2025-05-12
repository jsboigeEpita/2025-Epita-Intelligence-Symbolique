#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour l'analyseur de résultats rhétoriques amélioré.

Ce module contient les tests unitaires pour la classe EnhancedRhetoricalResultAnalyzer.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from argumentiation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer


class TestEnhancedRhetoricalResultAnalyzer(unittest.TestCase):
    """Tests pour la classe EnhancedRhetoricalResultAnalyzer."""

    def setUp(self):
        """Initialise l'environnement de test."""
        self.analyzer = EnhancedRhetoricalResultAnalyzer()
        
        # Exemple de résultats d'analyse rhétorique pour les tests
        self.test_results = {
            "complex_fallacy_analysis": {
                "individual_fallacies_count": 5,
                "basic_combinations": [
                    {
                        "combination_name": "Appel à l'autorité + Appel à la popularité",
                        "description": "Combinaison d'appel à l'autorité et d'appel à la popularité",
                        "severity": 0.7,
                        "severity_level": "Élevé"
                    }
                ],
                "advanced_combinations": [
                    {
                        "combination_name": "cascade_émotionnelle",
                        "description": "Combinaison d'appels à l'émotion qui s'intensifient progressivement",
                        "components": ["Appel à l'émotion", "Appel à la peur", "Appel à la pitié"],
                        "pattern": "escalation",
                        "pattern_match_score": 0.8,
                        "severity": 0.8,
                        "severity_level": "Élevé"
                    }
                ],
                "fallacy_patterns": [
                    {
                        "pattern_name": "escalade_émotionnelle",
                        "description": "Escalade progressive d'appels à l'émotion",
                        "confidence": 0.7,
                        "severity": 0.7
                    }
                ],
                "composite_severity": {
                    "basic_severity": 0.6,
                    "advanced_severity": 0.8,
                    "pattern_severity": 0.7,
                    "composite_severity": 0.7,
                    "context_modifier": 0.1,
                    "adjusted_severity": 0.8,
                    "severity_level": "Élevé"
                },
                "context": "politique",
                "analysis_timestamp": datetime.now().isoformat()
            },
            "contextual_fallacy_analysis": {
                "context_analysis": {
                    "context_type": "politique",
                    "context_subtypes": ["électoral"],
                    "audience_characteristics": ["généraliste"],
                    "formality_level": "moyen",
                    "confidence": 0.8
                },
                "potential_fallacies_count": 8,
                "contextual_fallacies_count": 5,
                "contextual_fallacies": [
                    {
                        "fallacy_type": "Appel à l'émotion",
                        "keyword": "peur",
                        "context_text": "Si nous ne faisons pas ce choix, nous risquons de graves conséquences.",
                        "confidence": 0.8,
                        "contextual_relevance": "Élevée",
                        "context_adjustment": 0.2
                    },
                    {
                        "fallacy_type": "Ad hominem",
                        "keyword": "attaque personnelle",
                        "context_text": "Mon adversaire n'a pas l'expérience nécessaire pour diriger.",
                        "confidence": 0.7,
                        "contextual_relevance": "Élevée",
                        "context_adjustment": 0.3
                    }
                ],
                "fallacy_relations": [
                    {
                        "relation_type": "complementary",
                        "fallacy1_type": "Appel à l'émotion",
                        "fallacy2_type": "Appel à la peur",
                        "explanation": "Les sophismes 'Appel à l'émotion' et 'Appel à la peur' se renforcent mutuellement",
                        "strength": 0.7
                    }
                ],
                "analysis_timestamp": datetime.now().isoformat()
            },
            "argument_coherence_evaluation": {
                "coherence_score": 0.6,
                "coherence_level": "Modéré",
                "thematic_clusters": [
                    {
                        "cluster_id": 0,
                        "arguments": [0, 1, 2]
                    },
                    {
                        "cluster_id": 1,
                        "arguments": [3, 4]
                    }
                ],
                "logical_flows": [
                    {
                        "flow_id": 0,
                        "source_argument": 0,
                        "target_argument": 1,
                        "relation_type": "support",
                        "confidence": 0.8
                    }
                ],
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
        
        self.test_context = "Discours politique électoral"

    def test_initialization(self):
        """Teste l'initialisation de l'analyseur."""
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.analysis_history)
        self.assertEqual(len(self.analyzer.analysis_history), 0)

    def test_analyze_rhetorical_results(self):
        """Teste la méthode analyze_rhetorical_results."""
        result = self.analyzer.analyze_rhetorical_results(self.test_results, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("overall_analysis", result)
        self.assertIn("fallacy_analysis", result)
        self.assertIn("coherence_analysis", result)
        self.assertIn("persuasion_analysis", result)
        self.assertIn("recommendations", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier l'analyse globale
        overall_analysis = result["overall_analysis"]
        self.assertIn("rhetorical_quality", overall_analysis)
        self.assertIn("rhetorical_quality_level", overall_analysis)
        self.assertIn("main_strengths", overall_analysis)
        self.assertIn("main_weaknesses", overall_analysis)
        self.assertIn("context_relevance", overall_analysis)
        
        # Vérifier que l'historique d'analyse a été mis à jour
        self.assertEqual(len(self.analyzer.analysis_history), 1)
        self.assertEqual(self.analyzer.analysis_history[0]["type"], "rhetorical_results_analysis")

    def test_analyze_fallacy_distribution(self):
        """Teste la méthode _analyze_fallacy_distribution."""
        fallacy_analysis = self.analyzer._analyze_fallacy_distribution(self.test_results)
        
        # Vérifier la structure du résultat
        self.assertIn("total_fallacies", fallacy_analysis)
        self.assertIn("fallacy_types_distribution", fallacy_analysis)
        self.assertIn("most_common_fallacies", fallacy_analysis)
        self.assertIn("most_severe_fallacies", fallacy_analysis)
        self.assertIn("composite_fallacies", fallacy_analysis)
        self.assertIn("overall_severity", fallacy_analysis)
        self.assertIn("severity_level", fallacy_analysis)
        
        # Vérifier que le nombre total de sophismes est cohérent
        self.assertGreaterEqual(fallacy_analysis["total_fallacies"], 0)
        
        # Vérifier que les sophismes les plus courants sont identifiés
        self.assertGreaterEqual(len(fallacy_analysis["most_common_fallacies"]), 0)
        
        # Vérifier que les sophismes les plus graves sont identifiés
        self.assertGreaterEqual(len(fallacy_analysis["most_severe_fallacies"]), 0)

    def test_analyze_coherence_quality(self):
        """Teste la méthode _analyze_coherence_quality."""
        coherence_analysis = self.analyzer._analyze_coherence_quality(self.test_results)
        
        # Vérifier la structure du résultat
        self.assertIn("overall_coherence", coherence_analysis)
        self.assertIn("coherence_level", coherence_analysis)
        self.assertIn("thematic_coherence", coherence_analysis)
        self.assertIn("logical_coherence", coherence_analysis)
        self.assertIn("structure_quality", coherence_analysis)
        self.assertIn("main_coherence_issues", coherence_analysis)
        
        # Vérifier que la cohérence globale est dans les limites attendues
        self.assertGreaterEqual(coherence_analysis["overall_coherence"], 0.0)
        self.assertLessEqual(coherence_analysis["overall_coherence"], 1.0)
        
        # Vérifier que le niveau de cohérence est valide
        self.assertIn(coherence_analysis["coherence_level"], ["Très faible", "Faible", "Modéré", "Élevé", "Excellent"])

    def test_analyze_persuasion_effectiveness(self):
        """Teste la méthode _analyze_persuasion_effectiveness."""
        persuasion_analysis = self.analyzer._analyze_persuasion_effectiveness(self.test_results, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("persuasion_score", persuasion_analysis)
        self.assertIn("persuasion_level", persuasion_analysis)
        self.assertIn("emotional_appeal", persuasion_analysis)
        self.assertIn("logical_appeal", persuasion_analysis)
        self.assertIn("credibility_appeal", persuasion_analysis)
        self.assertIn("context_appropriateness", persuasion_analysis)
        self.assertIn("audience_alignment", persuasion_analysis)
        
        # Vérifier que le score de persuasion est dans les limites attendues
        self.assertGreaterEqual(persuasion_analysis["persuasion_score"], 0.0)
        self.assertLessEqual(persuasion_analysis["persuasion_score"], 1.0)
        
        # Vérifier que le niveau de persuasion est valide
        self.assertIn(persuasion_analysis["persuasion_level"], ["Très faible", "Faible", "Modéré", "Élevé", "Excellent"])

    def test_generate_recommendations(self):
        """Teste la méthode _generate_recommendations."""
        # Créer des analyses pour le test
        fallacy_analysis = {
            "total_fallacies": 5,
            "most_common_fallacies": ["Appel à l'émotion", "Ad hominem"],
            "most_severe_fallacies": ["Appel à la peur"],
            "overall_severity": 0.7,
            "severity_level": "Élevé"
        }
        
        coherence_analysis = {
            "overall_coherence": 0.6,
            "coherence_level": "Modéré",
            "main_coherence_issues": ["Thematic shifts", "Logical gaps"]
        }
        
        persuasion_analysis = {
            "persuasion_score": 0.5,
            "persuasion_level": "Modéré",
            "emotional_appeal": 0.8,
            "logical_appeal": 0.4,
            "credibility_appeal": 0.6
        }
        
        recommendations = self.analyzer._generate_recommendations(
            fallacy_analysis, coherence_analysis, persuasion_analysis, self.test_context
        )
        
        # Vérifier la structure du résultat
        self.assertIn("general_recommendations", recommendations)
        self.assertIn("fallacy_recommendations", recommendations)
        self.assertIn("coherence_recommendations", recommendations)
        self.assertIn("persuasion_recommendations", recommendations)
        self.assertIn("context_specific_recommendations", recommendations)
        
        # Vérifier que des recommandations ont été générées
        self.assertGreater(len(recommendations["general_recommendations"]), 0)
        self.assertGreater(len(recommendations["fallacy_recommendations"]), 0)
        self.assertGreater(len(recommendations["coherence_recommendations"]), 0)
        self.assertGreater(len(recommendations["persuasion_recommendations"]), 0)

    def test_calculate_overall_rhetorical_quality(self):
        """Teste la méthode _calculate_overall_rhetorical_quality."""
        # Créer des analyses pour le test
        fallacy_analysis = {
            "overall_severity": 0.7,
            "severity_level": "Élevé"
        }
        
        coherence_analysis = {
            "overall_coherence": 0.6,
            "coherence_level": "Modéré"
        }
        
        persuasion_analysis = {
            "persuasion_score": 0.5,
            "persuasion_level": "Modéré"
        }
        
        quality, level = self.analyzer._calculate_overall_rhetorical_quality(
            fallacy_analysis, coherence_analysis, persuasion_analysis
        )
        
        # Vérifier que la qualité rhétorique est dans les limites attendues
        self.assertGreaterEqual(quality, 0.0)
        self.assertLessEqual(quality, 1.0)
        
        # Vérifier que le niveau de qualité rhétorique est valide
        self.assertIn(level, ["Très faible", "Faible", "Modéré", "Bon", "Excellent"])

    def test_identify_strengths_and_weaknesses(self):
        """Teste la méthode _identify_strengths_and_weaknesses."""
        # Créer des analyses pour le test
        fallacy_analysis = {
            "total_fallacies": 5,
            "most_common_fallacies": ["Appel à l'émotion", "Ad hominem"],
            "most_severe_fallacies": ["Appel à la peur"],
            "overall_severity": 0.7,
            "severity_level": "Élevé"
        }
        
        coherence_analysis = {
            "overall_coherence": 0.6,
            "coherence_level": "Modéré",
            "thematic_coherence": 0.7,
            "logical_coherence": 0.5,
            "main_coherence_issues": ["Thematic shifts", "Logical gaps"]
        }
        
        persuasion_analysis = {
            "persuasion_score": 0.5,
            "persuasion_level": "Modéré",
            "emotional_appeal": 0.8,
            "logical_appeal": 0.4,
            "credibility_appeal": 0.6
        }
        
        strengths, weaknesses = self.analyzer._identify_strengths_and_weaknesses(
            fallacy_analysis, coherence_analysis, persuasion_analysis
        )
        
        # Vérifier que des forces et des faiblesses ont été identifiées
        self.assertGreater(len(strengths), 0)
        self.assertGreater(len(weaknesses), 0)


if __name__ == "__main__":
    unittest.main()
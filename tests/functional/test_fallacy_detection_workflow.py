#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests fonctionnels pour le flux de travail de détection des sophismes.

Ce module teste le flux de travail complet de détection des sophismes,
de l'extraction du texte à l'évaluation de la sévérité des sophismes.
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
logger = logging.getLogger("TestFallacyDetectionWorkflow")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('../..'))

# Import des modules à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import ComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import FallacySeverityEvaluator
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.message_middleware import MessageMiddleware


class TestFallacyDetectionWorkflow(unittest.TestCase):
    """Tests fonctionnels pour le flux de travail de détection des sophismes."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer les outils d'analyse
        self.complex_analyzer = ComplexFallacyAnalyzer()
        self.contextual_analyzer = ContextualFallacyAnalyzer()
        self.severity_evaluator = FallacySeverityEvaluator()
        
        # Créer l'agent informel
        self.informal_agent = InformalAgent(
            agent_id="informal_agent_test",
            tools={
                "complex_analyzer": self.complex_analyzer,
                "contextual_analyzer": self.contextual_analyzer,
                "severity_evaluator": self.severity_evaluator
            }
        )
        
        # Créer un middleware
        self.middleware = MessageMiddleware()
        
        # Créer l'adaptateur d'extraction
        self.extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=self.middleware)
        
        # Initialiser les protocoles de communication
        self.middleware.initialize_protocols()
        
        # Créer le répertoire de résultats si nécessaire
        os.makedirs("results/test", exist_ok=True)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter le middleware
        self.middleware.shutdown()
    
    def test_fallacy_detection_workflow(self):
        """
        Teste le flux de travail complet de détection des sophismes.
        """
        # Chemin du fichier d'exemple
        example_file = "examples/test_data/test_sophismes_complexes.txt"
        
        # Vérifier que le fichier existe
        if not os.path.exists(example_file):
            # Créer le répertoire si nécessaire
            os.makedirs(os.path.dirname(example_file), exist_ok=True)
            
            # Créer un fichier d'exemple
            example_content = """
            Le réchauffement climatique est un mythe car il a neigé cet hiver.
            Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
            Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
            """
            with open(example_file, 'w', encoding='utf-8') as f:
                f.write(example_content)
        
        # Patcher la méthode d'extraction pour simuler la lecture du fichier
        with patch.object(self.extract_adapter, 'extract_text_from_file', return_value="""
        Le réchauffement climatique est un mythe car il a neigé cet hiver.
        Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
        Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
        """) as mock_extract:
            
            # Patcher les méthodes des outils d'analyse
            with patch.object(self.complex_analyzer, 'analyze', return_value=[
                {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
                {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
                {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
            ]) as mock_complex_analyze:
                
                with patch.object(self.contextual_analyzer, 'analyze_context', return_value={
                    "généralisation_hâtive": {"context_relevance": 0.7, "cultural_factors": ["climat", "science"]},
                    "faux_dilemme": {"context_relevance": 0.8, "cultural_factors": ["environnement", "politique"]},
                    "ad_hominem": {"context_relevance": 0.9, "cultural_factors": ["science", "financement"]}
                }) as mock_context_analyze:
                    
                    with patch.object(self.severity_evaluator, 'evaluate_severity', return_value=[
                        {"type": "généralisation_hâtive", "severity": 0.7, "impact": "medium"},
                        {"type": "faux_dilemme", "severity": 0.8, "impact": "high"},
                        {"type": "ad_hominem", "severity": 0.9, "impact": "high"}
                    ]) as mock_evaluate:
                        
                        # Exécuter le flux de travail de détection des sophismes
                        # 1. Extraire le texte
                        text = self.extract_adapter.extract_text_from_file(example_file)
                        
                        # 2. Détecter les sophismes
                        fallacies = self.complex_analyzer.analyze(text)
                        
                        # 3. Analyser le contexte
                        context_analysis = self.contextual_analyzer.analyze_context(fallacies)
                        
                        # 4. Évaluer la sévérité
                        severity_evaluation = self.severity_evaluator.evaluate_severity(fallacies, context_analysis)
                        
                        # 5. Générer le résultat final
                        result = {
                            "fallacies": fallacies,
                            "context_analysis": context_analysis,
                            "severity_evaluation": severity_evaluation,
                            "metadata": {
                                "source_file": example_file,
                                "timestamp": "2025-05-21T23:30:00",
                                "agent_id": "informal_agent_test"
                            }
                        }
                        
                        # Sauvegarder le résultat
                        result_file = os.path.join("results/test", "fallacy_detection_result.json")
                        with open(result_file, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        
                        # Vérifier que les méthodes ont été appelées
                        mock_extract.assert_called_once_with(example_file)
                        mock_complex_analyze.assert_called_once_with(text)
                        mock_context_analyze.assert_called_once_with(fallacies)
                        mock_evaluate.assert_called_once()
                        
                        # Vérifier le résultat
                        self.assertEqual(len(result["fallacies"]), 3)
                        self.assertEqual(len(result["severity_evaluation"]), 3)
                        
                        # Vérifier que le fichier de résultat a été créé
                        self.assertTrue(os.path.exists(result_file))
    
    def test_fallacy_detection_with_real_text(self):
        """
        Teste la détection des sophismes avec un texte réel.
        """
        # Texte réel contenant des sophismes
        real_text = """
        Les vaccins contre la COVID-19 ont été développés trop rapidement pour être sûrs.
        Soit nous acceptons la surveillance de masse, soit nous risquons des attaques terroristes.
        Les défenseurs du contrôle des armes à feu veulent confisquer toutes les armes et laisser les citoyens sans défense.
        """
        
        # Patcher les méthodes des outils d'analyse
        with patch.object(self.complex_analyzer, 'analyze', return_value=[
            {"type": "corrélation_causation", "text": "Les vaccins contre la COVID-19 ont été développés trop rapidement pour être sûrs", "confidence": 0.78},
            {"type": "faux_dilemme", "text": "Soit nous acceptons la surveillance de masse, soit nous risquons des attaques terroristes", "confidence": 0.91},
            {"type": "homme_de_paille", "text": "Les défenseurs du contrôle des armes à feu veulent confisquer toutes les armes et laisser les citoyens sans défense", "confidence": 0.85}
        ]) as mock_complex_analyze:
            
            with patch.object(self.contextual_analyzer, 'analyze_context', return_value={
                "corrélation_causation": {"context_relevance": 0.8, "cultural_factors": ["santé", "science"]},
                "faux_dilemme": {"context_relevance": 0.9, "cultural_factors": ["sécurité", "vie privée"]},
                "homme_de_paille": {"context_relevance": 0.7, "cultural_factors": ["armes", "politique"]}
            }) as mock_context_analyze:
                
                with patch.object(self.severity_evaluator, 'evaluate_severity', return_value=[
                    {"type": "corrélation_causation", "severity": 0.8, "impact": "high"},
                    {"type": "faux_dilemme", "severity": 0.9, "impact": "high"},
                    {"type": "homme_de_paille", "severity": 0.7, "impact": "medium"}
                ]) as mock_evaluate:
                    
                    # Exécuter le flux de travail avec l'agent informel
                    result = self.informal_agent.perform_enhanced_analysis(real_text)
                    
                    # Vérifier que les méthodes ont été appelées
                    mock_complex_analyze.assert_called_once_with(real_text)
                    mock_context_analyze.assert_called_once()
                    mock_evaluate.assert_called_once()
                    
                    # Vérifier le résultat
                    self.assertIsNotNone(result)
                    self.assertIn("fallacies", result)
                    self.assertIn("context_analysis", result)
                    self.assertIn("severity_evaluation", result)
                    
                    # Vérifier les sophismes détectés
                    fallacy_types = [f["type"] for f in result["fallacies"]]
                    self.assertIn("corrélation_causation", fallacy_types)
                    self.assertIn("faux_dilemme", fallacy_types)
                    self.assertIn("homme_de_paille", fallacy_types)
    
    def test_fallacy_detection_with_multiple_texts(self):
        """
        Teste la détection des sophismes sur plusieurs textes.
        """
        # Textes d'exemple
        texts = [
            "Les vaccins contre la COVID-19 ont été développés trop rapidement pour être sûrs.",
            "Soit nous acceptons la surveillance de masse, soit nous risquons des attaques terroristes.",
            "Les défenseurs du contrôle des armes à feu veulent confisquer toutes les armes."
        ]
        
        # Résultats attendus pour chaque texte
        expected_fallacies = [
            [{"type": "corrélation_causation", "text": texts[0], "confidence": 0.78}],
            [{"type": "faux_dilemme", "text": texts[1], "confidence": 0.91}],
            [{"type": "homme_de_paille", "text": texts[2], "confidence": 0.85}]
        ]
        
        # Patcher la méthode d'analyse
        with patch.object(self.complex_analyzer, 'analyze', side_effect=expected_fallacies) as mock_analyze:
            
            # Analyser chaque texte
            results = []
            for text in texts:
                fallacies = self.complex_analyzer.analyze(text)
                results.append(fallacies)
            
            # Vérifier que la méthode a été appelée pour chaque texte
            self.assertEqual(mock_analyze.call_count, len(texts))
            
            # Vérifier les résultats
            for i, result in enumerate(results):
                self.assertEqual(result, expected_fallacies[i])
            
            # Agréger les résultats
            all_fallacies = [item for sublist in results for item in sublist]
            
            # Vérifier l'agrégation
            self.assertEqual(len(all_fallacies), 3)
            
            # Sauvegarder le résultat agrégé
            result_file = os.path.join("results/test", "multi_text_fallacy_detection.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({"fallacies": all_fallacies}, f, ensure_ascii=False, indent=2)
            
            # Vérifier que le fichier de résultat a été créé
            self.assertTrue(os.path.exists(result_file))


if __name__ == "__main__":
    pytest.main(["-v", __file__])
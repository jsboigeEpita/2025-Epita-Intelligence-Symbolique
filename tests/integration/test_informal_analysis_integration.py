#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration entre les agents informels et les outils d'analyse.

Ce module teste l'interaction entre les agents informels et les outils d'analyse
pour la détection et l'évaluation des sophismes dans un contexte d'argumentation informelle.
"""

import unittest
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestInformalAnalysisIntegration")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('../..'))

# Import des modules à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.core.informal.informal_definitions import FallacyDefinition, FallacyCategory
from argumentation_analysis.agents.tools.analysis.fallacy_detector import FallacyDetector
from argumentation_analysis.agents.tools.analysis.rhetorical_analyzer import RhetoricalAnalyzer


class TestInformalAnalysisIntegration(unittest.TestCase):
    """Tests d'intégration entre les agents informels et les outils d'analyse."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer les définitions de sophismes
        self.fallacy_definitions = [
            FallacyDefinition(
                name="ad_hominem",
                category=FallacyCategory.RELEVANCE,
                description="Attaque la personne plutôt que l'argument",
                examples=["Il est stupide, donc son argument est invalide"],
                detection_patterns=["stupide", "idiot", "incompétent"]
            ),
            FallacyDefinition(
                name="faux_dilemme",
                category=FallacyCategory.STRUCTURE,
                description="Présente seulement deux options alors qu'il en existe d'autres",
                examples=["Soit vous êtes avec nous, soit vous êtes contre nous"],
                detection_patterns=["soit...soit", "ou bien...ou bien", "deux options"]
            ),
            FallacyDefinition(
                name="pente_glissante",
                category=FallacyCategory.CAUSALITE,
                description="Suggère qu'une action mènera inévitablement à une chaîne d'événements indésirables",
                examples=["Si nous autorisons cela, bientôt tout sera permis"],
                detection_patterns=["bientôt", "mènera à", "conduira à", "inévitablement"]
            )
        ]
        
        # Créer les outils d'analyse
        self.fallacy_detector = FallacyDetector(fallacy_definitions=self.fallacy_definitions)
        self.rhetorical_analyzer = RhetoricalAnalyzer()
        
        # Créer l'agent informel
        self.informal_agent = InformalAgent(
            agent_id="informal_agent_test",
            tools={
                "fallacy_detector": self.fallacy_detector,
                "rhetorical_analyzer": self.rhetorical_analyzer
            }
        )
    
    def test_fallacy_detection_with_definitions(self):
        """
        Teste la détection des sophismes par l'agent informel en utilisant
        les définitions de sophismes et le détecteur de sophismes.
        """
        # Texte d'exemple contenant des sophismes
        text = """
        Jean est incompétent, donc son argument sur l'économie est invalide.
        Soit nous augmentons les impôts, soit l'économie s'effondrera.
        Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux.
        """
        
        # Patcher la méthode detect du détecteur de sophismes
        with patch.object(self.fallacy_detector, 'detect', return_value=[
            {"type": "ad_hominem", "text": "Jean est incompétent, donc son argument sur l'économie est invalide", "confidence": 0.85},
            {"type": "faux_dilemme", "text": "Soit nous augmentons les impôts, soit l'économie s'effondrera", "confidence": 0.78},
            {"type": "pente_glissante", "text": "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux", "confidence": 0.92}
        ]) as mock_detect:
            
            # Appeler la méthode d'analyse de l'agent informel
            result = self.informal_agent.analyze_text(text)
            
            # Vérifier que la méthode detect a été appelée
            mock_detect.assert_called_once_with(text)
            
            # Vérifier le résultat
            self.assertIsNotNone(result)
            self.assertIn("fallacies", result)
            self.assertEqual(len(result["fallacies"]), 3)
            
            # Vérifier que les sophismes détectés sont présents dans le résultat
            fallacy_types = [f["type"] for f in result["fallacies"]]
            self.assertIn("ad_hominem", fallacy_types)
            self.assertIn("faux_dilemme", fallacy_types)
            self.assertIn("pente_glissante", fallacy_types)
    
    def test_rhetorical_analysis_integration(self):
        """
        Teste l'intégration de l'analyse rhétorique avec la détection des sophismes.
        """
        # Texte d'exemple
        text = """
        Mesdames et messieurs, je vous demande de réfléchir attentivement.
        Notre adversaire prétend défendre vos intérêts, mais il est financé par des lobbies.
        Comment pourrait-il être objectif ? C'est impossible !
        Vous avez deux choix : voter pour nous et prospérer, ou voter pour eux et souffrir.
        """
        
        # Patcher les méthodes des outils d'analyse
        with patch.object(self.fallacy_detector, 'detect', return_value=[
            {"type": "ad_hominem", "text": "Notre adversaire prétend défendre vos intérêts, mais il est financé par des lobbies", "confidence": 0.75},
            {"type": "faux_dilemme", "text": "Vous avez deux choix : voter pour nous et prospérer, ou voter pour eux et souffrir", "confidence": 0.88}
        ]) as mock_detect:
            
            with patch.object(self.rhetorical_analyzer, 'analyze', return_value={
                "tone": "persuasif",
                "style": "émotionnel",
                "techniques": ["appel à l'émotion", "question rhétorique", "polarisation"],
                "effectiveness": 0.82
            }) as mock_rhetorical:
                
                # Appeler la méthode d'analyse complète de l'agent informel
                result = self.informal_agent.perform_complete_analysis(text)
                
                # Vérifier que les méthodes des outils d'analyse ont été appelées
                mock_detect.assert_called_once_with(text)
                mock_rhetorical.assert_called_once_with(text)
                
                # Vérifier le résultat
                self.assertIsNotNone(result)
                self.assertIn("fallacies", result)
                self.assertIn("rhetorical_analysis", result)
                
                # Vérifier les sophismes détectés
                fallacy_types = [f["type"] for f in result["fallacies"]]
                self.assertIn("ad_hominem", fallacy_types)
                self.assertIn("faux_dilemme", fallacy_types)
                
                # Vérifier l'analyse rhétorique
                self.assertEqual(result["rhetorical_analysis"]["tone"], "persuasif")
                self.assertEqual(result["rhetorical_analysis"]["style"], "émotionnel")
                self.assertIn("appel à l'émotion", result["rhetorical_analysis"]["techniques"])
                self.assertIn("question rhétorique", result["rhetorical_analysis"]["techniques"])
    
    def test_fallacy_categorization(self):
        """
        Teste la catégorisation des sophismes détectés selon les définitions.
        """
        # Texte d'exemple
        text = """
        Si nous légalisons la marijuana, bientôt toutes les drogues seront légales.
        Pierre est riche, donc son opinion sur la pauvreté n'est pas valable.
        """
        
        # Patcher la méthode detect du détecteur de sophismes
        with patch.object(self.fallacy_detector, 'detect', return_value=[
            {"type": "pente_glissante", "text": "Si nous légalisons la marijuana, bientôt toutes les drogues seront légales", "confidence": 0.89},
            {"type": "ad_hominem", "text": "Pierre est riche, donc son opinion sur la pauvreté n'est pas valable", "confidence": 0.82}
        ]) as mock_detect:
            
            # Patcher la méthode categorize_fallacies de l'agent informel
            with patch.object(self.informal_agent, 'categorize_fallacies', wraps=self.informal_agent.categorize_fallacies) as mock_categorize:
                
                # Appeler la méthode d'analyse catégorisée de l'agent informel
                result = self.informal_agent.analyze_and_categorize(text)
                
                # Vérifier que les méthodes ont été appelées
                mock_detect.assert_called_once_with(text)
                mock_categorize.assert_called_once()
                
                # Vérifier le résultat
                self.assertIsNotNone(result)
                self.assertIn("fallacies", result)
                self.assertIn("categories", result)
                
                # Vérifier les catégories
                self.assertIn(FallacyCategory.CAUSALITE.name, result["categories"])
                self.assertIn(FallacyCategory.RELEVANCE.name, result["categories"])
                
                # Vérifier que les sophismes sont correctement catégorisés
                self.assertIn("pente_glissante", result["categories"][FallacyCategory.CAUSALITE.name])
                self.assertIn("ad_hominem", result["categories"][FallacyCategory.RELEVANCE.name])


if __name__ == "__main__":
    pytest.main(["-v", __file__])
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.tools.analysis.fallacy_analyzer.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestFallacyAnalyzer")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Utiliser les vraies bibliothèques numpy et pandas si disponibles
try:
    import numpy
    import pandas
    HAS_REAL_LIBS = True
except ImportError:
    # Importer les mocks pour numpy et pandas si les vraies bibliothèques ne sont pas disponibles
    from tests.mocks.numpy_mock import *
    from tests.mocks.pandas_mock import *
    
    # Patcher numpy et pandas avant d'importer le module à tester
    sys.modules['numpy'] = sys.modules.get('numpy')
    sys.modules['pandas'] = sys.modules.get('pandas')
    HAS_REAL_LIBS = False

# Import du module à tester
from argumentation_analysis.agents.tools.analysis.fallacy_detector import FallacyDetector
from argumentation_analysis.agents.core.informal.informal_definitions import FallacyDefinition, FallacyCategory


class TestFallacyAnalyzer(unittest.TestCase):
    """Tests unitaires pour l'analyseur de sophismes."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer des définitions de sophismes pour les tests
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
            ),
            FallacyDefinition(
                name="appel_autorite",
                category=FallacyCategory.RELEVANCE,
                description="Invoque une autorité non pertinente",
                examples=["Les experts affirment que ce produit est sûr"],
                detection_patterns=["expert", "autorité", "scientifique"]
            ),
            FallacyDefinition(
                name="appel_popularite",
                category=FallacyCategory.RELEVANCE,
                description="Invoque la popularité comme preuve de validité",
                examples=["Tout le monde le fait, donc c'est bien"],
                detection_patterns=["tout le monde", "millions", "populaire"]
            )
        ]
        
        # Créer l'analyseur de sophismes
        self.analyzer = FallacyDetector(fallacy_definitions=self.fallacy_definitions)
        
        # Texte d'exemple pour les tests
        self.text = """
        Jean est incompétent, donc son argument sur l'économie est invalide.
        Soit nous augmentons les impôts, soit l'économie s'effondrera.
        Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux.
        Les experts affirment que ce produit est sûr et efficace.
        Ce produit est utilisé par des millions de personnes dans le monde entier.
        """
    
    def test_initialization(self):
        """Teste l'initialisation de l'analyseur de sophismes."""
        # Vérifier que l'analyseur a été correctement initialisé
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.fallacy_definitions)
        self.assertEqual(len(self.analyzer.fallacy_definitions), 5)
        
        # Vérifier que les définitions de sophismes ont été correctement assignées
        self.assertEqual(self.analyzer.fallacy_definitions[0].name, "ad_hominem")
        self.assertEqual(self.analyzer.fallacy_definitions[1].name, "faux_dilemme")
        self.assertEqual(self.analyzer.fallacy_definitions[2].name, "pente_glissante")
        self.assertEqual(self.analyzer.fallacy_definitions[3].name, "appel_autorite")
        self.assertEqual(self.analyzer.fallacy_definitions[4].name, "appel_popularite")
    
    def test_initialization_with_empty_definitions(self):
        """Teste l'initialisation de l'analyseur de sophismes avec des définitions vides."""
        # Créer un analyseur avec des définitions vides
        analyzer = FallacyDetector(fallacy_definitions=[])
        
        # Vérifier que l'analyseur a été correctement initialisé
        self.assertIsNotNone(analyzer)
        self.assertEqual(len(analyzer.fallacy_definitions), 0)
    
    def test_initialization_with_default_definitions(self):
        """Teste l'initialisation de l'analyseur de sophismes avec les définitions par défaut."""
        # Patcher la méthode _load_default_definitions
        with patch.object(FallacyDetector, '_load_default_definitions', return_value=[
            FallacyDefinition(
                name="default_fallacy",
                category=FallacyCategory.RELEVANCE,
                description="Définition par défaut",
                examples=["Exemple par défaut"],
                detection_patterns=["pattern"]
            )
        ]):
            # Créer un analyseur sans définitions
            analyzer = FallacyDetector()
            
            # Vérifier que l'analyseur a été correctement initialisé
            self.assertIsNotNone(analyzer)
            self.assertEqual(len(analyzer.fallacy_definitions), 1)
            self.assertEqual(analyzer.fallacy_definitions[0].name, "default_fallacy")
    
    def test_detect(self):
        """Teste la méthode detect."""
        # Patcher la méthode _match_patterns
        with patch.object(self.analyzer, '_match_patterns', side_effect=[
            [("incompétent", 0.8)],  # Pour ad_hominem
            [("soit...soit", 0.7)],  # Pour faux_dilemme
            [("bientôt", 0.9)],      # Pour pente_glissante
            [("expert", 0.8)],       # Pour appel_autorite
            [("millions", 0.7)]      # Pour appel_popularite
        ]) as mock_match:
            
            # Appeler la méthode detect
            fallacies = self.analyzer.detect(self.text)
            
            # Vérifier que la méthode _match_patterns a été appelée
            self.assertEqual(mock_match.call_count, 5)
            
            # Vérifier le résultat
            self.assertIsInstance(fallacies, list)
            self.assertEqual(len(fallacies), 5)
            
            # Vérifier les sophismes détectés
            fallacy_types = [f["fallacy_type"] for f in fallacies]
            self.assertIn("ad_hominem", fallacy_types)
            self.assertIn("faux_dilemme", fallacy_types)
            self.assertIn("pente_glissante", fallacy_types)
            self.assertIn("appel_autorite", fallacy_types)
            self.assertIn("appel_popularite", fallacy_types)
            
            # Vérifier les détails des sophismes
            for fallacy in fallacies:
                self.assertIn("fallacy_type", fallacy)
                self.assertIn("text", fallacy)
                self.assertIn("confidence", fallacy)
                self.assertGreaterEqual(fallacy["confidence"], 0.0)
                self.assertLessEqual(fallacy["confidence"], 1.0)
    
    def test_detect_with_confidence_threshold(self):
        """Teste la méthode detect avec un seuil de confiance."""
        # Patcher la méthode _match_patterns
        with patch.object(self.analyzer, '_match_patterns', side_effect=[
            [("incompétent", 0.8)],  # Pour ad_hominem
            [("soit...soit", 0.7)],  # Pour faux_dilemme
            [("bientôt", 0.9)],      # Pour pente_glissante
            [("expert", 0.8)],       # Pour appel_autorite
            [("millions", 0.7)]      # Pour appel_popularite
        ]) as mock_match:
            
            # Appeler la méthode detect avec un seuil de confiance
            fallacies = self.analyzer.detect(self.text, confidence_threshold=0.8)
            
            # Vérifier que la méthode _match_patterns a été appelée
            self.assertEqual(mock_match.call_count, 5)
            
            # Vérifier le résultat
            self.assertIsInstance(fallacies, list)
            self.assertEqual(len(fallacies), 3)  # Seulement 3 sophismes ont une confiance >= 0.8
            
            # Vérifier les sophismes détectés
            fallacy_types = [f["fallacy_type"] for f in fallacies]
            self.assertIn("ad_hominem", fallacy_types)
            self.assertIn("pente_glissante", fallacy_types)
            self.assertIn("appel_autorite", fallacy_types)
            self.assertNotIn("faux_dilemme", fallacy_types)
            self.assertNotIn("appel_popularite", fallacy_types)
    
    def test_detect_with_max_fallacies(self):
        """Teste la méthode detect avec un nombre maximum de sophismes."""
        # Patcher la méthode _match_patterns
        with patch.object(self.analyzer, '_match_patterns', side_effect=[
            [("incompétent", 0.8)],  # Pour ad_hominem
            [("soit...soit", 0.7)],  # Pour faux_dilemme
            [("bientôt", 0.9)],      # Pour pente_glissante
            [("expert", 0.8)],       # Pour appel_autorite
            [("millions", 0.7)]      # Pour appel_popularite
        ]) as mock_match:
            
            # Appeler la méthode detect avec un nombre maximum de sophismes
            fallacies = self.analyzer.detect(self.text, max_fallacies=3)
            
            # Vérifier que la méthode _match_patterns a été appelée
            self.assertEqual(mock_match.call_count, 5)
            
            # Vérifier le résultat
            self.assertIsInstance(fallacies, list)
            self.assertEqual(len(fallacies), 3)  # Seulement 3 sophismes sont retournés
    
    def test_match_patterns(self):
        """Teste la méthode _match_patterns."""
        # Créer une définition de sophisme
        fallacy_def = FallacyDefinition(
            name="test_fallacy",
            category=FallacyCategory.RELEVANCE,
            description="Définition de test",
            examples=["Exemple de test"],
            detection_patterns=["test", "exemple", "définition"]
        )
        
        # Appeler la méthode _match_patterns
        matches = self.analyzer._match_patterns(
            "Ceci est un test pour la définition de l'exemple.",
            fallacy_def
        )
        
        # Vérifier le résultat
        self.assertIsInstance(matches, list)
        self.assertEqual(len(matches), 3)  # 3 patterns correspondent
        
        # Vérifier les correspondances
        patterns = [m[0] for m in matches]
        self.assertIn("test", patterns)
        self.assertIn("exemple", patterns)
        self.assertIn("définition", patterns)
        
        # Vérifier les scores de confiance
        for match in matches:
            self.assertIsInstance(match[1], float)
            self.assertGreaterEqual(match[1], 0.0)
            self.assertLessEqual(match[1], 1.0)
    
    def test_match_patterns_with_no_matches(self):
        """Teste la méthode _match_patterns sans correspondances."""
        # Créer une définition de sophisme
        fallacy_def = FallacyDefinition(
            name="test_fallacy",
            category=FallacyCategory.RELEVANCE,
            description="Définition de test",
            examples=["Exemple de test"],
            detection_patterns=["pattern1", "pattern2", "pattern3"]
        )
        
        # Appeler la méthode _match_patterns
        matches = self.analyzer._match_patterns(
            "Ceci est un texte qui ne contient aucun des patterns.",
            fallacy_def
        )
        
        # Vérifier le résultat
        self.assertIsInstance(matches, list)
        self.assertEqual(len(matches), 0)  # Aucun pattern ne correspond
    
    def test_calculate_confidence(self):
        """Teste la méthode _calculate_confidence."""
        # Appeler la méthode _calculate_confidence
        confidence = self.analyzer._calculate_confidence(
            [("pattern1", 0.8), ("pattern2", 0.6), ("pattern3", 0.9)],
            "Ceci est un texte avec pattern1, pattern2 et pattern3."
        )
        
        # Vérifier le résultat
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # Vérifier que la confiance est calculée correctement
        # La confiance devrait être une combinaison des scores individuels
        self.assertGreaterEqual(confidence, 0.6)  # Au moins égale au score minimum
        self.assertLessEqual(confidence, 0.9)  # Au plus égale au score maximum
    
    def test_calculate_confidence_with_empty_matches(self):
        """Teste la méthode _calculate_confidence avec des correspondances vides."""
        # Appeler la méthode _calculate_confidence
        confidence = self.analyzer._calculate_confidence(
            [],
            "Ceci est un texte sans correspondances."
        )
        
        # Vérifier le résultat
        self.assertIsInstance(confidence, float)
        self.assertEqual(confidence, 0.0)  # La confiance devrait être nulle
    
    def test_extract_context(self):
        """Teste la méthode _extract_context."""
        # Appeler la méthode _extract_context
        context = self.analyzer._extract_context(
            "Ceci est un texte avec un pattern au milieu.",
            "pattern",
            10
        )
        
        # Vérifier le résultat
        self.assertIsInstance(context, str)
        self.assertIn("pattern", context)
        
        # Vérifier que le contexte est correctement extrait
        expected_context = "texte avec un pattern au milieu"
        self.assertEqual(context, expected_context)
    
    def test_extract_context_at_beginning(self):
        """Teste la méthode _extract_context avec un pattern au début."""
        # Appeler la méthode _extract_context
        context = self.analyzer._extract_context(
            "Pattern au début du texte.",
            "Pattern",
            10
        )
        
        # Vérifier le résultat
        self.assertIsInstance(context, str)
        self.assertIn("Pattern", context)
        
        # Vérifier que le contexte est correctement extrait
        expected_context = "Pattern au début"
        self.assertEqual(context, expected_context)
    
    def test_extract_context_at_end(self):
        """Teste la méthode _extract_context avec un pattern à la fin."""
        # Appeler la méthode _extract_context
        context = self.analyzer._extract_context(
            "Ceci est un texte avec un pattern.",
            "pattern",
            10
        )
        
        # Vérifier le résultat
        self.assertIsInstance(context, str)
        self.assertIn("pattern", context)
        
        # Vérifier que le contexte est correctement extrait
        expected_context = "texte avec un pattern"
        self.assertEqual(context, expected_context)
    
    def test_detect_with_empty_text(self):
        """Teste la méthode detect avec un texte vide."""
        # Appeler la méthode detect avec un texte vide
        fallacies = self.analyzer.detect("")
        
        # Vérifier le résultat
        self.assertIsInstance(fallacies, list)
        self.assertEqual(len(fallacies), 0)  # Aucun sophisme ne devrait être détecté
    
    def test_detect_with_none_text(self):
        """Teste la méthode detect avec un texte None."""
        # Appeler la méthode detect avec un texte None
        with self.assertRaises(ValueError):
            fallacies = self.analyzer.detect(None)


if __name__ == "__main__":
    unittest.main()
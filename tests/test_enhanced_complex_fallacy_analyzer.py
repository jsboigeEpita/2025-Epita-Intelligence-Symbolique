#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.tools.analysis.enhanced.complex_fallacy_analyzer.
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
logger = logging.getLogger("TestEnhancedComplexFallacyAnalyzer")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Importer les mocks pour numpy et pandas
from tests.mocks.numpy_mock import *
from tests.mocks.pandas_mock import *

# Patcher numpy et pandas avant d'importer le module à tester
sys.modules['numpy'] = sys.modules.get('numpy')
sys.modules['pandas'] = sys.modules.get('pandas')

# Import du module à tester
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer


class TestEnhancedComplexFallacyAnalyzer(unittest.TestCase):
    """Tests unitaires pour l'analyseur de sophismes complexes amélioré."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer l'analyseur de sophismes complexes amélioré
        self.analyzer = EnhancedComplexFallacyAnalyzer()
        
        # Créer des arguments et des sophismes pour les tests
        self.arguments = [
            {
                "id": "arg-1",
                "text": "Tous les experts sont d'accord que le réchauffement climatique est réel, donc c'est vrai.",
                "confidence": 0.9,
                "source": "texte-1",
                "position": {"start": 0, "end": 80}
            },
            {
                "id": "arg-2",
                "text": "Si nous acceptons le mariage homosexuel, bientôt les gens voudront épouser des animaux.",
                "confidence": 0.85,
                "source": "texte-1",
                "position": {"start": 81, "end": 160}
            },
            {
                "id": "arg-3",
                "text": "Mon opposant n'a pas de diplôme en économie, donc son plan économique est forcément mauvais.",
                "confidence": 0.8,
                "source": "texte-1",
                "position": {"start": 161, "end": 240}
            }
        ]
        
        self.fallacies = [
            {
                "id": "fallacy-1",
                "type": "Appel à l'autorité",
                "argument_id": "arg-1",
                "confidence": 0.7,
                "description": "L'argument repose uniquement sur l'opinion d'experts sans présenter de preuves."
            },
            {
                "id": "fallacy-2",
                "type": "Pente glissante",
                "argument_id": "arg-2",
                "confidence": 0.8,
                "description": "L'argument suggère qu'une action mènera inévitablement à une chaîne d'événements indésirables sans justification."
            },
            {
                "id": "fallacy-3",
                "type": "Ad hominem",
                "argument_id": "arg-3",
                "confidence": 0.9,
                "description": "L'argument attaque la personne plutôt que ses idées."
            }
        ]
    
    def test_initialization(self):
        """Teste l'initialisation de l'analyseur de sophismes complexes amélioré."""
        # Vérifier que l'analyseur a été correctement initialisé
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.contextual_analyzer)
        self.assertIsNotNone(self.analyzer.severity_evaluator)
        self.assertIsNotNone(self.analyzer.argument_structure_patterns)
        self.assertIsNotNone(self.analyzer.advanced_fallacy_combinations)
    
    def test_analyze_complex_fallacies(self):
        """Teste la méthode analyze_complex_fallacies."""
        # Appeler la méthode analyze_complex_fallacies
        result = self.analyzer.analyze_complex_fallacies(self.arguments, self.fallacies)
        
        # Vérifier que le résultat est correct
        self.assertIsInstance(result, dict)
        self.assertIn("complex_fallacies", result)
        self.assertIn("fallacy_combinations", result)
        self.assertIn("structural_patterns", result)
        
        # Vérifier que les sophismes complexes ont été identifiés
        self.assertIsInstance(result["complex_fallacies"], list)
        
        # Vérifier que les combinaisons de sophismes ont été identifiées
        self.assertIsInstance(result["fallacy_combinations"], list)
        
        # Vérifier que les motifs structurels ont été identifiés
        self.assertIsInstance(result["structural_patterns"], list)
    
    def test_detect_fallacy_combinations(self):
        """Teste la méthode _detect_fallacy_combinations."""
        # Appeler la méthode _detect_fallacy_combinations
        combinations = self.analyzer._detect_fallacy_combinations(self.fallacies)
        
        # Vérifier que le résultat est correct
        self.assertIsInstance(combinations, list)
    
    def test_analyze_argument_structure(self):
        """Teste la méthode _analyze_argument_structure."""
        # Appeler la méthode _analyze_argument_structure
        patterns = self.analyzer._analyze_argument_structure(self.arguments)
        
        # Vérifier que le résultat est correct
        self.assertIsInstance(patterns, list)
    
    def test_detect_circular_reasoning(self):
        """Teste la méthode _detect_circular_reasoning."""
        # Créer des arguments avec un raisonnement circulaire
        circular_arguments = [
            {
                "id": "arg-4",
                "text": "La Bible est la parole de Dieu car elle le dit elle-même.",
                "confidence": 0.9,
                "source": "texte-2",
                "position": {"start": 0, "end": 60}
            },
            {
                "id": "arg-5",
                "text": "La Bible dit qu'elle est la parole de Dieu, donc c'est vrai.",
                "confidence": 0.85,
                "source": "texte-2",
                "position": {"start": 61, "end": 120}
            }
        ]
        
        # Appeler la méthode _detect_circular_reasoning
        circular = self.analyzer._detect_circular_reasoning(circular_arguments)
        
        # Vérifier que le résultat est correct
        self.assertIsInstance(circular, list)
        
        # Vérifier que le raisonnement circulaire a été détecté
        if circular:
            self.assertEqual(len(circular), 1)
            self.assertIn("arguments", circular[0])
            self.assertIn("arg-4", circular[0]["arguments"])
            self.assertIn("arg-5", circular[0]["arguments"])
    
    def test_analyze_structure_vulnerabilities(self):
        """Teste la méthode _analyze_structure_vulnerabilities."""
        # Appeler la méthode _analyze_structure_vulnerabilities
        vulnerabilities = self.analyzer._analyze_structure_vulnerabilities(self.arguments)
        
        # Vérifier que le résultat est correct
        self.assertIsInstance(vulnerabilities, list)
    
    def test_evaluate_complex_fallacy_severity(self):
        """Teste la méthode _evaluate_complex_fallacy_severity."""
        # Créer un sophisme complexe
        complex_fallacy = {
            "id": "complex-fallacy-1",
            "type": "Double appel",
            "arguments": ["arg-1", "arg-3"],
            "components": ["Appel à l'autorité", "Ad hominem"],
            "confidence": 0.8,
            "description": "Combinaison d'un appel à l'autorité et d'un ad hominem."
        }
        
        # Appeler la méthode _evaluate_complex_fallacy_severity
        severity = self.analyzer._evaluate_complex_fallacy_severity(complex_fallacy, self.fallacies)
        
        # Vérifier que le résultat est correct
        self.assertIsInstance(severity, float)
        self.assertGreaterEqual(severity, 0.0)
        self.assertLessEqual(severity, 1.0)
    
    def test_analyze_fallacy_interactions(self):
        """Teste la méthode _analyze_fallacy_interactions."""
        # Appeler la méthode _analyze_fallacy_interactions
        interactions = self.analyzer._analyze_fallacy_interactions(self.fallacies)
        
        # Vérifier que le résultat est correct
        self.assertIsInstance(interactions, list)
    
    def test_generate_complex_fallacy_report(self):
        """Teste la méthode generate_complex_fallacy_report."""
        # Créer des sophismes complexes
        complex_fallacies = [
            {
                "id": "complex-fallacy-1",
                "type": "Double appel",
                "arguments": ["arg-1", "arg-3"],
                "components": ["Appel à l'autorité", "Ad hominem"],
                "confidence": 0.8,
                "severity": 0.85,
                "description": "Combinaison d'un appel à l'autorité et d'un ad hominem."
            }
        ]
        
        # Créer des combinaisons de sophismes
        fallacy_combinations = [
            {
                "id": "combo-1",
                "type": "Combinaison",
                "fallacies": ["fallacy-1", "fallacy-3"],
                "confidence": 0.75,
                "severity": 0.8,
                "description": "Combinaison d'un appel à l'autorité et d'un ad hominem."
            }
        ]
        
        # Créer des motifs structurels
        structural_patterns = [
            {
                "id": "pattern-1",
                "type": "chaîne_causale",
                "arguments": ["arg-1", "arg-2"],
                "confidence": 0.7,
                "severity": 0.6,
                "description": "Chaîne causale entre les arguments arg-1 et arg-2."
            }
        ]
        
        # Appeler la méthode generate_complex_fallacy_report
        report = self.analyzer.generate_complex_fallacy_report(
            complex_fallacies, fallacy_combinations, structural_patterns, self.arguments, self.fallacies
        )
        
        # Vérifier que le rapport est correct
        self.assertIsInstance(report, dict)
        self.assertIn("summary", report)
        self.assertIn("complex_fallacies", report)
        self.assertIn("fallacy_combinations", report)
        self.assertIn("structural_patterns", report)
        self.assertIn("overall_severity", report)
        self.assertIn("recommendations", report)
    
    def test_save_analysis_results(self):
        """Teste la méthode save_analysis_results."""
        # Créer des résultats d'analyse
        results = {
            "complex_fallacies": [
                {
                    "id": "complex-fallacy-1",
                    "type": "Double appel",
                    "arguments": ["arg-1", "arg-3"],
                    "components": ["Appel à l'autorité", "Ad hominem"],
                    "confidence": 0.8,
                    "severity": 0.85,
                    "description": "Combinaison d'un appel à l'autorité et d'un ad hominem."
                }
            ],
            "fallacy_combinations": [
                {
                    "id": "combo-1",
                    "type": "Combinaison",
                    "fallacies": ["fallacy-1", "fallacy-3"],
                    "confidence": 0.75,
                    "severity": 0.8,
                    "description": "Combinaison d'un appel à l'autorité et d'un ad hominem."
                }
            ],
            "structural_patterns": [
                {
                    "id": "pattern-1",
                    "type": "chaîne_causale",
                    "arguments": ["arg-1", "arg-2"],
                    "confidence": 0.7,
                    "severity": 0.6,
                    "description": "Chaîne causale entre les arguments arg-1 et arg-2."
                }
            ]
        }
        
        # Créer un fichier temporaire pour les résultats
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Patcher la méthode open pour éviter d'écrire réellement dans un fichier
            with patch('builtins.open', MagicMock()):
                # Appeler la méthode save_analysis_results
                saved = self.analyzer.save_analysis_results(results, output_path=temp_path)
                
                # Vérifier que la méthode a retourné True
                self.assertTrue(saved)
        finally:
            # Supprimer le fichier temporaire
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
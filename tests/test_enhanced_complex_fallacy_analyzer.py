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
import pytest # Ajout de l'import pytest

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestEnhancedComplexFallacyAnalyzer")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
# sys.path.append(os.path.abspath('..')) # Déjà géré par conftest.py et PYTHONPATH
# sys.path.append(os.path.abspath('.'))  # Déjà géré par conftest.py et PYTHONPATH

# Importer les mocks pour numpy et pandas
# Le répertoire tests/mocks est ajouté à sys.path par conftest.py
from numpy_mock import *
from pandas_mock import *

# Patcher numpy et pandas avant d'importer le module à tester
# Cette section est redondante si conftest.py gère correctement les mocks dans sys.modules
# sys.modules['numpy'] = sys.modules.get('numpy') 
# sys.modules['pandas'] = sys.modules.get('pandas')

# Import du module à tester
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer


@pytest.mark.xfail(reason="Binary incompatibility with SciPy C extensions and NumPy mock. ValueError: numpy.dtype size changed.", raises=ValueError, strict=True)
class TestEnhancedComplexFallacyAnalyzer(unittest.TestCase):
    """Tests unitaires pour l'analyseur de sophismes complexes amélioré."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.analyzer = EnhancedComplexFallacyAnalyzer()
        
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
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.contextual_analyzer)
        self.assertIsNotNone(self.analyzer.severity_evaluator)
        self.assertIsNotNone(self.analyzer.argument_structure_patterns)
        self.assertIsNotNone(self.analyzer.advanced_fallacy_combinations)
    
    def test_analyze_complex_fallacies(self):
        arguments_text = [arg["text"] for arg in self.arguments]
        result = self.analyzer.detect_composite_fallacies(arguments_text, "général")
        self.assertIsInstance(result, dict)
        self.assertIn("basic_combinations", result)
        self.assertIn("advanced_combinations", result)
        self.assertIn("fallacy_patterns", result)
        self.assertIn("composite_severity", result)
        self.assertIsInstance(result["basic_combinations"], list)
        self.assertIsInstance(result["advanced_combinations"], list)
        self.assertIsInstance(result["fallacy_patterns"], list)
    
    def test_detect_fallacy_combinations(self):
        fallacies_text = " ".join([fallacy["description"] for fallacy in self.fallacies])
        combinations = self.analyzer.identify_combined_fallacies(fallacies_text)
        self.assertIsInstance(combinations, list)
    
    def test_analyze_argument_structure(self):
        arguments_text = [arg["text"] for arg in self.arguments]
        result = self.analyzer.analyze_argument_structure(arguments_text, "général")
        self.assertIsInstance(result, dict)
        self.assertIn("identified_structures", result)
        self.assertIn("argument_relations", result)
        self.assertIn("coherence_evaluation", result)
        self.assertIn("vulnerability_analysis", result)
    
    def test_detect_circular_reasoning(self):
        circular_arguments = [
            "La Bible est la parole de Dieu car elle le dit elle-même.",
            "La Bible dit qu'elle est la parole de Dieu, donc c'est vrai."
        ]
        result = self.analyzer.analyze_inter_argument_coherence(circular_arguments, "religieux")
        self.assertIsInstance(result, dict)
        self.assertIn("overall_coherence", result)
        self.assertLessEqual(result["overall_coherence"]["overall_score"], 0.6)
    
    def test_analyze_structure_vulnerabilities(self):
        arguments_text = [arg["text"] for arg in self.arguments]
        result = self.analyzer.analyze_argument_structure(arguments_text, "général")
        self.assertIsInstance(result, dict)
        self.assertIn("vulnerability_analysis", result)
    
    def test_evaluate_composite_severity(self):
        arguments_text = [arg["text"] for arg in self.arguments]
        result = self.analyzer.detect_composite_fallacies(arguments_text, "général")
        self.assertIsInstance(result, dict)
        self.assertIn("composite_severity", result)
        self.assertIn("adjusted_severity", result["composite_severity"])
        self.assertGreaterEqual(result["composite_severity"]["adjusted_severity"], 0.0)
        self.assertLessEqual(result["composite_severity"]["adjusted_severity"], 1.0)
    
    def test_analyze_fallacy_interactions(self):
        arguments_text = [arg["text"] for arg in self.arguments]
        result = self.analyzer.detect_composite_fallacies(arguments_text, "général")
        self.assertIsInstance(result, dict)
        self.assertIn("basic_combinations", result)
        self.assertIn("advanced_combinations", result)
    
    def test_analyze_inter_argument_coherence(self):
        arguments_text = [arg["text"] for arg in self.arguments]
        result = self.analyzer.analyze_inter_argument_coherence(arguments_text, "général")
        self.assertIsInstance(result, dict)
        self.assertIn("thematic_coherence", result)
        self.assertIn("logical_coherence", result)
        self.assertIn("overall_coherence", result)
    
    def test_identify_fallacy_patterns(self):
        arguments_text = " ".join([arg["text"] for arg in self.arguments])
        patterns = self.analyzer.identify_fallacy_patterns(arguments_text)
        self.assertIsInstance(patterns, list)

if __name__ == "__main__":
    unittest.main()
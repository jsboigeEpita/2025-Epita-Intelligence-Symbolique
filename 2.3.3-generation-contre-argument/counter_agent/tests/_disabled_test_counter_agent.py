"""
Tests pour l'agent de génération de contre-arguments.

Ce module contient des tests unitaires pour valider le fonctionnement
de l'agent de génération de contre-arguments.
"""

import sys
import os
import unittest
from typing import List
from unittest.mock import MagicMock

# Ajouter le répertoire parent au path pour permettre l'importation du package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from counter_agent import (
    CounterArgumentAgent,
    Argument,
    CounterArgumentType,
    RhetoricalStrategy,
    ArgumentStrength,
    Vulnerability
)


class TestArgumentParser(unittest.TestCase):
    """Tests pour le parseur d'arguments."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        self.agent = CounterArgumentAgent(kernel=MagicMock())
        self.mock_taxonomy = MagicMock()
    
    def test_parse_simple_argument(self):
        """Teste la capacité à parser un argument simple."""
        # Argument simple
        argument_text = "Il pleut. Donc le sol est mouillé."
        
        # Analyse de l'argument
        argument = self.agent.analyze_argument(argument_text, self.mock_taxonomy)
        
        # Vérifications
        self.assertIsInstance(argument, Argument)
        self.assertEqual(argument.content, argument_text)
        self.assertGreater(len(argument.premises), 0)
        self.assertEqual(argument.premises[0], "Il pleut")
        self.assertTrue("sol est mouillé" in argument.conclusion)
    
    def test_parse_complex_argument(self):
        """Teste la capacité à parser un argument plus complexe."""
        # Argument plus complexe
        argument_text = """
        Tous les hommes sont mortels.
        Socrate est un homme.
        Donc Socrate est mortel.
        """
        
        # Analyse de l'argument
        argument = self.agent.analyze_argument(argument_text, self.mock_taxonomy)
        
        # Vérifications
        self.assertIsInstance(argument, Argument)
        self.assertGreaterEqual(len(argument.premises), 1)
        self.assertTrue("mortel" in argument.conclusion.lower())
        self.assertGreater(argument.confidence, 0.5)


class TestVulnerabilityAnalysis(unittest.TestCase):
    """Tests pour l'analyse des vulnérabilités."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        self.agent = CounterArgumentAgent(kernel=MagicMock())
        self.mock_taxonomy = MagicMock()
    
    def test_identify_generalisation_vulnerability(self):
        """Teste la capacité à identifier une généralisation abusive."""
        # Argument avec généralisation abusive
        argument_text = "Tous les politiciens sont corrompus. Donc on ne peut faire confiance à aucun politicien."
        
        # Analyse de l'argument
        argument = self.agent.analyze_argument(argument_text, self.mock_taxonomy)
        vulnerabilities = self.agent.identify_vulnerabilities(argument)
        
        # Vérifications
        self.assertIsInstance(vulnerabilities, list)
        self.assertGreater(len(vulnerabilities), 0)
        
        # Au moins une vulnérabilité doit être du type généralisation
        generalisation_found = False
        for vuln in vulnerabilities:
            if "general" in vuln.type.lower():
                generalisation_found = True
                break
        
        self.assertTrue(generalisation_found, "Une généralisation abusive aurait dû être détectée")
    
    def test_identify_premise_vulnerability(self):
        """Teste la capacité à identifier une prémisse faible."""
        # Argument avec prémisse faible
        argument_text = "Évidemment, les vaccins sont dangereux. Donc il ne faut pas se faire vacciner."
        
        # Analyse de l'argument
        argument = self.agent.analyze_argument(argument_text, self.mock_taxonomy)
        vulnerabilities = self.agent.identify_vulnerabilities(argument)
        
        # Vérifications
        self.assertIsInstance(vulnerabilities, list)
        self.assertGreater(len(vulnerabilities), 0)
        
        # Au moins une vulnérabilité doit cibler une prémisse
        premise_vuln_found = False
        for vuln in vulnerabilities:
            if "premise" in vuln.target:
                premise_vuln_found = True
                break
        
        self.assertTrue(premise_vuln_found, "Une vulnérabilité de prémisse aurait dû être détectée")


class TestCounterArgumentGeneration(unittest.TestCase):
    """Tests pour la génération de contre-arguments."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        self.agent = CounterArgumentAgent(kernel=MagicMock())
        self.mock_taxonomy = MagicMock()
        
        # Argument utilisé pour les tests
        self.argument_text = """
        Tous les étudiants qui travaillent dur réussissent leurs examens.
        Marie travaille dur. Donc Marie réussira ses examens.
        """
        
        # Analyse préalable
        self.argument = self.agent.analyze_argument(self.argument_text, self.mock_taxonomy)
        self.vulnerabilities = self.agent.identify_vulnerabilities(self.argument)
    
    def test_direct_refutation_generation(self):
        """Teste la génération d'une réfutation directe."""
        counter_arg = self.agent.generate_counter_argument(
            self.argument,
            CounterArgumentType.DIRECT_REFUTATION,
            self.vulnerabilities
        )
        
        # Vérifications
        self.assertEqual(counter_arg.counter_type, CounterArgumentType.DIRECT_REFUTATION)
        self.assertIsNotNone(counter_arg.counter_content)
        self.assertGreater(len(counter_arg.counter_content), 10)
        self.assertEqual(counter_arg.original_argument, self.argument)
    
    def test_counter_example_generation(self):
        """Teste la génération d'un contre-exemple."""
        counter_arg = self.agent.generate_counter_argument(
            self.argument,
            CounterArgumentType.COUNTER_EXAMPLE,
            self.vulnerabilities
        )
        
        # Vérifications
        self.assertEqual(counter_arg.counter_type, CounterArgumentType.COUNTER_EXAMPLE)
        self.assertIsNotNone(counter_arg.counter_content)
        self.assertGreater(len(counter_arg.counter_content), 10)
    
    def test_premise_challenge_generation(self):
        """Teste la génération d'une remise en question des prémisses."""
        counter_arg = self.agent.generate_counter_argument(
            self.argument,
            CounterArgumentType.PREMISE_CHALLENGE,
            self.vulnerabilities
        )
        
        # Vérifications
        self.assertEqual(counter_arg.counter_type, CounterArgumentType.PREMISE_CHALLENGE)
        self.assertIsNotNone(counter_arg.counter_content)
        self.assertGreater(len(counter_arg.counter_content), 10)
    
    def test_strategy_customization(self):
        """Teste la génération avec une stratégie rhétorique spécifique."""
        # Tester différentes stratégies
        strategies = [
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            RhetoricalStrategy.ANALOGICAL_COUNTER
        ]
        
        for strategy in strategies:
            counter_arg = self.agent.generate_counter_argument(
                self.argument,
                CounterArgumentType.DIRECT_REFUTATION,
                self.vulnerabilities,
                custom_strategy=strategy
            )
            
            # Vérifications
            self.assertEqual(counter_arg.rhetorical_strategy, strategy.value)
            self.assertIsNotNone(counter_arg.counter_content)
            self.assertGreater(len(counter_arg.counter_content), 10)


class TestCounterArgumentEvaluation(unittest.TestCase):
    """Tests pour l'évaluation des contre-arguments."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        self.agent = CounterArgumentAgent(kernel=MagicMock())
        self.mock_taxonomy = MagicMock()
        
        # Argument utilisé pour les tests
        self.argument_text = "Tous les cygnes sont blancs. Donc il n'existe pas de cygnes noirs."
        
        # Analyse préalable
        self.argument = self.agent.analyze_argument(self.argument_text, self.mock_taxonomy)
        self.vulnerabilities = self.agent.identify_vulnerabilities(self.argument)
        
        # Génération d'un contre-argument
        self.counter_arg = self.agent.generate_counter_argument(
            self.argument,
            CounterArgumentType.COUNTER_EXAMPLE,
            self.vulnerabilities
        )
    
    def test_evaluation_metrics(self):
        """Teste les métriques d'évaluation d'un contre-argument."""
        # Évaluer le contre-argument
        evaluation = self.agent.evaluate_counter_argument(self.argument, self.counter_arg)
        
        # Vérifications
        self.assertGreaterEqual(evaluation.relevance, 0)
        self.assertLessEqual(evaluation.relevance, 1)
        
        self.assertGreaterEqual(evaluation.logical_strength, 0)
        self.assertLessEqual(evaluation.logical_strength, 1)
        
        self.assertGreaterEqual(evaluation.persuasiveness, 0)
        self.assertLessEqual(evaluation.persuasiveness, 1)
        
        self.assertGreaterEqual(evaluation.originality, 0)
        self.assertLessEqual(evaluation.originality, 1)
        
        self.assertGreaterEqual(evaluation.clarity, 0)
        self.assertLessEqual(evaluation.clarity, 1)
        
        self.assertGreaterEqual(evaluation.overall_score, 0)
        self.assertLessEqual(evaluation.overall_score, 1)
        
        self.assertIsInstance(evaluation.recommendations, list)


if __name__ == '__main__':
    unittest.main() 
# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_tweety_bridge.py
"""
Tests unitaires pour la classe TweetyBridge.
"""
import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Ajout pour forcer la reconnaissance du package principal
current_script_path = Path(__file__).resolve()
project_root_for_test = current_script_path.parents[4]
sys.path.insert(0, str(project_root_for_test))

from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.logic.pl_handler import PLHandler
from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler

class TestTweetyBridge(unittest.TestCase):
    """Tests pour la classe TweetyBridge."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.use_real_jpype = os.environ.get('USE_REAL_JPYPE') == 'true'

        if self.use_real_jpype:
            self.bridge = TweetyBridge.get_instance()
            try:
                self.bridge.initialize_jvm()
            except Exception as e:
                self.fail(f"L'initialisation de la JVM en condition réelle a échoué: {e}")
        else:
            # Patcher entièrement TweetyInitializer pour éviter tout contact avec jpype
            self.initializer_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.TweetyInitializer', autospec=True)
            self.mock_initializer_class = self.initializer_patcher.start()
            self.mock_initializer_instance = self.mock_initializer_class.return_value
            # Simuler une JVM prête
            self.mock_initializer_instance.is_jvm_ready.return_value = True

            # Patcher les classes Handler pour injecter des mocks
            self.pl_handler_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.PropositionalLogicHandler', autospec=True)
            self.fol_handler_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.FirstOrderLogicHandler', autospec=True)
            self.mock_pl_handler_class = self.pl_handler_patcher.start()
            self.mock_fol_handler_class = self.fol_handler_patcher.start()

            self.mock_pl_handler_instance = self.mock_pl_handler_class.return_value
            self.mock_fol_handler_instance = self.mock_fol_handler_class.return_value

            self.bridge = TweetyBridge.get_instance()

    def tearDown(self):
        """Nettoyage après chaque test."""
        if self.use_real_jpype:
            if self.bridge.initializer.is_jvm_ready():
                self.bridge.shutdown_jvm()
        else:
            patch.stopall()
        # Réinitialiser le singleton pour l'isolation des tests
        TweetyBridge._instance = None

    def test_singleton_instance(self):
        """Vérifie que get_instance retourne toujours la même instance."""
        instance1 = TweetyBridge.get_instance()
        instance2 = TweetyBridge.get_instance()
        self.assertIs(instance1, instance2)

    @unittest.skipIf(os.environ.get('USE_REAL_JPYPE') == 'true', "Test pour environnement mocké uniquement")
    def test_lazy_loading_of_handlers(self):
        """Vérifie que les handlers sont créés uniquement au premier accès."""
        # Au début, les handlers ne doivent pas être initialisés
        self.assertIsNone(self.bridge._pl_handler)
        self.assertIsNone(self.bridge._fol_handler)
        self.mock_pl_handler_class.assert_not_called()
        self.mock_fol_handler_class.assert_not_called()

        # Premier accès au pl_handler
        _ = self.bridge.pl_handler
        self.mock_pl_handler_class.assert_called_once_with(self.bridge._initializer)
        self.assertIsNotNone(self.bridge._pl_handler)

        # Premier accès au fol_handler
        _ = self.bridge.fol_handler
        self.mock_fol_handler_class.assert_called_once_with(self.bridge._initializer)
        self.assertIsNotNone(self.bridge._fol_handler)

    def test_pl_query_delegation(self):
        """Vérifie que pl_query délègue correctement l'appel au handler."""
        kb = "a"
        query = "b"
        if not self.use_real_jpype:
            self.bridge.pl_query(kb, query)
            self.mock_pl_handler_instance.pl_query.assert_called_once_with(kb, query)
        else:
            # En mode réel, on vérifie juste que ça ne crashe pas
            try:
                self.bridge.pl_query(kb, query)
            except Exception as e:
                self.fail(f"pl_query a levé une exception inattendue: {e}")

    def test_fol_query_delegation(self):
        """Vérifie que fol_query délègue correctement l'appel au handler."""
        kb_str = "forall X: p(X)."
        query_str = "p(a)."
        if not self.use_real_jpype:
            belief_set_mock = MagicMock()
            self.mock_fol_handler_instance.create_belief_set_from_string.return_value = belief_set_mock
            
            self.bridge.fol_query(kb_str, query_str)
            
            self.mock_fol_handler_instance.create_belief_set_from_string.assert_called_once_with(kb_str)
            self.mock_fol_handler_instance.fol_query.assert_called_once_with(belief_set_mock, query_str)
        else:
            try:
                self.bridge.fol_query(kb_str, query_str)
            except Exception as e:
                self.fail(f"fol_query a levé une exception inattendue: {e}")

    def test_validate_pl_formula_delegation(self):
        """Vérifie que validate_pl_formula délègue correctement."""
        formula = "a => b"
        if not self.use_real_jpype:
            self.bridge.validate_pl_formula(formula)
            self.mock_pl_handler_instance.parse_pl_formula.assert_called_once_with(formula)
        else:
            self.assertTrue(self.bridge.validate_pl_formula(formula))
            self.assertFalse(self.bridge.validate_pl_formula("a ==> b"))

    def test_validate_fol_formula_delegation(self):
        """Vérifie que validate_fol_formula délègue correctement."""
        formula = "forall X : p(X)"
        if not self.use_real_jpype:
            self.bridge.validate_fol_formula(formula)
            self.mock_fol_handler_instance.parse_fol_formula.assert_called_once_with(formula)
        else:
            self.assertTrue(self.bridge.validate_fol_formula(formula)[0])
            self.assertFalse(self.bridge.validate_fol_formula("forall X p(X)")[0])


if __name__ == "__main__":
    unittest.main()

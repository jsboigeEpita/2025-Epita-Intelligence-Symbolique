# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_tweety_bridge.py
"""
Tests unitaires pour la classe TweetyBridge.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock

import jpype

from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestTweetyBridge(unittest.TestCase):
    """Tests pour la classe TweetyBridge."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Patcher jpype
        self.jpype_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.jpype')
        self.mock_jpype = self.jpype_patcher.start()
        
        # Configurer le mock de jpype
        self.mock_jpype.isJVMStarted.return_value = True
        
        # Mocks pour les classes Java
        self.mock_pl_parser = MagicMock()
        self.mock_sat_reasoner = MagicMock()
        self.mock_pl_formula = MagicMock()
        
        self.mock_fol_parser = MagicMock()
        self.mock_fol_reasoner = MagicMock()
        self.mock_fol_formula = MagicMock()
        
        self.mock_modal_parser = MagicMock()
        self.mock_modal_reasoner = MagicMock()
        self.mock_modal_formula = MagicMock()
        
        # Configurer JClass pour retourner les mocks
        self.mock_jpype.JClass.side_effect = lambda class_name: {
            "org.tweetyproject.logics.pl.parser.PlParser": self.mock_pl_parser,
            "org.tweetyproject.logics.pl.reasoner.SatReasoner": self.mock_sat_reasoner,
            "org.tweetyproject.logics.pl.syntax.PlFormula": self.mock_pl_formula,
            "org.tweetyproject.logics.fol.parser.FolParser": self.mock_fol_parser,
            "org.tweetyproject.logics.fol.reasoner.FolReasoner": self.mock_fol_reasoner,
            "org.tweetyproject.logics.fol.syntax.FolFormula": self.mock_fol_formula,
            "org.tweetyproject.logics.ml.parser.ModalParser": self.mock_modal_parser,
            "org.tweetyproject.logics.ml.reasoner.ModalReasoner": self.mock_modal_reasoner,
            "org.tweetyproject.logics.ml.syntax.ModalFormula": self.mock_modal_formula
        }[class_name]
        
        # Mocks pour les instances
        self.mock_pl_parser_instance = MagicMock()
        self.mock_sat_reasoner_instance = MagicMock()
        
        self.mock_fol_parser_instance = MagicMock()
        self.mock_fol_reasoner_instance = MagicMock()
        
        self.mock_modal_parser_instance = MagicMock()
        self.mock_modal_reasoner_instance = MagicMock()
        
        # Configurer les constructeurs pour retourner les mocks
        self.mock_pl_parser.return_value = self.mock_pl_parser_instance
        self.mock_sat_reasoner.return_value = self.mock_sat_reasoner_instance
        
        self.mock_fol_parser.return_value = self.mock_fol_parser_instance
        self.mock_fol_reasoner.return_value = self.mock_fol_reasoner_instance
        
        self.mock_modal_parser.return_value = self.mock_modal_parser_instance
        self.mock_modal_reasoner.return_value = self.mock_modal_reasoner_instance
        
        # Créer l'instance de TweetyBridge
        self.tweety_bridge = TweetyBridge()
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.jpype_patcher.stop()
    
    def test_initialization_jvm_ready(self):
        """Test de l'initialisation lorsque la JVM est prête."""
        # Vérifier que la JVM est prête
        self.assertTrue(self.tweety_bridge.is_jvm_ready())
        
        # Vérifier que les classes Java ont été chargées
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.pl.parser.PlParser")
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.pl.reasoner.SatReasoner")
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.pl.syntax.PlFormula")
        
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.parser.FolParser")
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.reasoner.FolReasoner")
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.syntax.FolFormula")
        
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.parser.ModalParser")
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.reasoner.ModalReasoner")
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.syntax.ModalFormula")
        
        # Vérifier que les instances ont été créées
        self.mock_pl_parser.assert_called_once()
        self.mock_sat_reasoner.assert_called_once()
        
        self.mock_fol_parser.assert_called_once()
        self.mock_fol_reasoner.assert_called_once()
        
        self.mock_modal_parser.assert_called_once()
        self.mock_modal_reasoner.assert_called_once()
    
    def test_initialization_jvm_not_ready(self):
        """Test de l'initialisation lorsque la JVM n'est pas prête."""
        # Configurer le mock de jpype
        self.mock_jpype.isJVMStarted.return_value = False
        
        # Créer l'instance de TweetyBridge
        tweety_bridge = TweetyBridge()
        
        # Vérifier que la JVM n'est pas prête
        self.assertFalse(tweety_bridge.is_jvm_ready())
        
        # Vérifier que les classes Java n'ont pas été chargées
        self.mock_jpype.JClass.assert_not_called()
    
    def test_validate_formula_valid(self):
        """Test de la validation d'une formule propositionnelle valide."""
        # Configurer le mock du parser
        self.mock_pl_parser_instance.parseFormula.return_value = MagicMock()
        
        # Valider une formule
        is_valid, message = self.tweety_bridge.validate_formula("a => b")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a => b")
        
        # Vérifier le résultat
        self.assertTrue(is_valid)
        self.assertEqual(message, "Formule valide")
    
    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule propositionnelle invalide."""
        # Configurer le mock du parser pour lever une exception
        java_exception = MagicMock(spec=jpype.JException)
        java_exception.getMessage.return_value = "Erreur de syntaxe"
        self.mock_pl_parser_instance.parseFormula.side_effect = java_exception
        
        # Valider une formule
        is_valid, message = self.tweety_bridge.validate_formula("a ==> b")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a ==> b")
        
        # Vérifier le résultat
        self.assertFalse(is_valid)
        self.assertEqual(message, "Erreur de syntaxe: Erreur de syntaxe")
    
    def test_validate_belief_set_valid(self):
        """Test de la validation d'un ensemble de croyances propositionnelles valide."""
        # Configurer le mock du parser
        mock_belief_set = MagicMock()
        mock_belief_set.__str__.return_value = "a => b"
        self.mock_pl_parser_instance.parseBeliefBase.return_value = mock_belief_set
        
        # Valider un ensemble de croyances
        is_valid, message = self.tweety_bridge.validate_belief_set("a => b")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseBeliefBase.assert_called_once()
        
        # Vérifier le résultat
        self.assertTrue(is_valid)
        self.assertEqual(message, "Ensemble de croyances valide")
    
    def test_validate_belief_set_empty(self):
        """Test de la validation d'un ensemble de croyances propositionnelles vide."""
        # Configurer le mock du parser
        mock_belief_set = MagicMock()
        mock_belief_set.__str__.return_value = ""
        self.mock_pl_parser_instance.parseBeliefBase.return_value = mock_belief_set
        
        # Valider un ensemble de croyances
        is_valid, message = self.tweety_bridge.validate_belief_set("")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseBeliefBase.assert_called_once()
        
        # Vérifier le résultat
        self.assertFalse(is_valid)
        self.assertEqual(message, "Ensemble de croyances vide ou ne contenant que des commentaires")
    
    def test_validate_belief_set_invalid(self):
        """Test de la validation d'un ensemble de croyances propositionnelles invalide."""
        # Configurer le mock du parser pour lever une exception
        java_exception = MagicMock(spec=jpype.JException)
        java_exception.getMessage.return_value = "Erreur de syntaxe à la ligne 2"
        java_exception.message.return_value = "Erreur de syntaxe à la ligne 2"
        self.mock_pl_parser_instance.parseBeliefBase.side_effect = java_exception
        
        # Valider un ensemble de croyances
        is_valid, message = self.tweety_bridge.validate_belief_set("a ==> b")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseBeliefBase.assert_called_once()
        
        # Vérifier le résultat
        self.assertFalse(is_valid)
        self.assertIn("Erreur de syntaxe", message)
    
    def test_execute_pl_query_accepted(self):
        """Test de l'exécution d'une requête propositionnelle acceptée."""
        # Configurer les mocks
        mock_belief_set = MagicMock()
        mock_formula = MagicMock()
        
        # Configurer le mock du parser
        self.mock_pl_parser_instance.parseBeliefBase.return_value = mock_belief_set
        self.mock_pl_parser_instance.parseFormula.return_value = mock_formula
        
        # Configurer le mock du raisonneur
        self.mock_sat_reasoner_instance.query.return_value = True
        
        # Configurer le mock de JObject
        self.mock_jpype.JObject.return_value = True
        
        # Exécuter une requête
        result = self.tweety_bridge.execute_pl_query("a => b", "a")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseBeliefBase.assert_called_once()
        self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a")
        
        # Vérifier que le raisonneur a été appelé
        self.mock_sat_reasoner_instance.query.assert_called_once_with(mock_belief_set, mock_formula)
        
        # Vérifier le résultat
        self.assertIn("ACCEPTED", result)
    
    def test_execute_pl_query_rejected(self):
        """Test de l'exécution d'une requête propositionnelle rejetée."""
        # Configurer les mocks
        mock_belief_set = MagicMock()
        mock_formula = MagicMock()
        
        # Configurer le mock du parser
        self.mock_pl_parser_instance.parseBeliefBase.return_value = mock_belief_set
        self.mock_pl_parser_instance.parseFormula.return_value = mock_formula
        
        # Configurer le mock du raisonneur
        self.mock_sat_reasoner_instance.query.return_value = False
        
        # Configurer le mock de JObject
        self.mock_jpype.JObject.return_value = True
        
        # Exécuter une requête
        result = self.tweety_bridge.execute_pl_query("a => b", "a")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseBeliefBase.assert_called_once()
        self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a")
        
        # Vérifier que le raisonneur a été appelé
        self.mock_sat_reasoner_instance.query.assert_called_once_with(mock_belief_set, mock_formula)
        
        # Vérifier le résultat
        self.assertIn("REJECTED", result)
    
    def test_execute_pl_query_error(self):
        """Test de l'exécution d'une requête propositionnelle avec erreur."""
        # Configurer le mock du parser pour lever une exception
        java_exception = MagicMock(spec=jpype.JException)
        java_exception.getMessage.return_value = "Erreur de syntaxe"
        java_exception.getClass().getName.return_value = "org.tweetyproject.SyntaxException"
        self.mock_pl_parser_instance.parseBeliefBase.side_effect = java_exception
        
        # Exécuter une requête
        result = self.tweety_bridge.execute_pl_query("a ==> b", "a")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseBeliefBase.assert_called_once()
        
        # Vérifier le résultat
        self.assertIn("FUNC_ERROR", result)
    
    # Tests similaires pour les méthodes FOL et modales
    def test_validate_fol_formula(self):
        """Test de la validation d'une formule du premier ordre."""
        # Configurer le mock du parser
        self.mock_fol_parser_instance.parseFormula.return_value = MagicMock()
        
        # Valider une formule
        is_valid, message = self.tweety_bridge.validate_fol_formula("forall X: (P(X) => Q(X))")
        
        # Vérifier que le parser a été appelé
        self.mock_fol_parser_instance.parseFormula.assert_called_once_with("forall X: (P(X) => Q(X))")
        
        # Vérifier le résultat
        self.assertTrue(is_valid)
        self.assertEqual(message, "Formule FOL valide")
    
    def test_validate_modal_formula(self):
        """Test de la validation d'une formule modale."""
        # Configurer le mock du parser
        self.mock_modal_parser_instance.parseFormula.return_value = MagicMock()
        
        # Valider une formule
        is_valid, message = self.tweety_bridge.validate_modal_formula("[]p => <>q")
        
        # Vérifier que le parser a été appelé
        self.mock_modal_parser_instance.parseFormula.assert_called_once_with("[]p => <>q")
        
        # Vérifier le résultat
        self.assertTrue(is_valid)
        self.assertEqual(message, "Formule modale valide")


if __name__ == "__main__":
    unittest.main()
# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_tweety_bridge.py
"""
Tests unitaires pour la classe TweetyBridge.
"""

import os # Ajout de l'import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from tests.mocks.jpype_mock import JException as MockedJException

# import jpype # Gardé pour référence si des types réels sont nécessaires, mais les tests devraient utiliser le mock.

from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestTweetyBridge(unittest.TestCase):
    """Tests pour la classe TweetyBridge."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # self.use_real_jpype = os.environ.get('USE_REAL_JPYPE') == 'true' # Remplacé par vérification directe
        
        self.jpype_patcher = None
        self.jvm_setup_jpype_patcher = None
        self.mock_jpype = None
        self.mock_jvm_setup_jpype = None

        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Patcher jpype
            self.jpype_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.jpype')
            self.mock_jpype = self.jpype_patcher.start()
            self.mock_jpype.JException = MockedJException # Assigner la classe mockée

            # Patcher jpype dans jvm_setup également pour contrôler son comportement depuis les tests de TweetyBridge
            self.jvm_setup_jpype_patcher = patch('argumentation_analysis.core.jvm_setup.jpype')
            self.mock_jvm_setup_jpype = self.jvm_setup_jpype_patcher.start()

            # Assurer la cohérence des mocks jpype entre les deux modules patchés
            self.mock_jvm_setup_jpype.isJVMStarted = self.mock_jpype.isJVMStarted
            self.mock_jvm_setup_jpype.JException = self.mock_jpype.JException
            self.mock_jvm_setup_jpype.JClass = self.mock_jpype.JClass
            self.mock_jvm_setup_jpype.startJVM = self.mock_jpype.startJVM
            self.mock_jvm_setup_jpype.shutdownJVM = self.mock_jpype.shutdownJVM # Au cas où
            
            # Configurer le mock de jpype (sera propagé à mock_jvm_setup_jpype)
            self.mock_jpype.isJVMStarted.return_value = True
            
            # Mocks pour les classes Java
            self.mock_pl_parser = MagicMock(name="PlParser_class_mock")
            self.mock_sat_reasoner = MagicMock(name="SatReasoner_class_mock")
            self.mock_pl_formula = MagicMock(name="PlFormula_class_mock")
            
            self.mock_fol_parser = MagicMock(name="FolParser_class_mock")
            self.mock_fol_reasoner = MagicMock(name="FolReasoner_class_mock") 
            self.mock_fol_formula = MagicMock(name="FolFormula_class_mock")
            
            self.mock_ml_parser = MagicMock(name="MlParser_class_mock")
            self.mock_abstract_ml_reasoner = MagicMock(name="AbstractMlReasoner_class_mock")
            self.mock_simple_ml_reasoner = MagicMock(name="SimpleMlReasoner_class_mock")
            self.mock_modal_formula = MagicMock(name="ModalFormula_class_mock")
            self.mock_simple_fol_reasoner = MagicMock(name="SimpleFolReasoner_class_mock")
            self.mock_sat_solver = MagicMock(name="SatSolver_class_mock")
            self.mock_sat4j_solver = MagicMock(name="Sat4jSolver_class_mock")
            self.mock_pl_belief_set = MagicMock(name="PlBeliefSet_class_mock") # Ajout
            
            self.jclass_map = {
                "org.tweetyproject.logics.pl.parser.PlParser": self.mock_pl_parser,
                "org.tweetyproject.logics.pl.reasoner.SatReasoner": self.mock_sat_reasoner,
                "org.tweetyproject.logics.pl.syntax.PlFormula": self.mock_pl_formula,
                "org.tweetyproject.logics.fol.parser.FolParser": self.mock_fol_parser,
                "org.tweetyproject.logics.fol.reasoner.FolReasoner": self.mock_fol_reasoner,
                "org.tweetyproject.logics.fol.syntax.FolFormula": self.mock_fol_formula,
                "org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner": self.mock_simple_fol_reasoner,
                "org.tweetyproject.logics.ml.parser.MlParser": self.mock_ml_parser,
                "org.tweetyproject.logics.ml.reasoner.AbstractMlReasoner": self.mock_abstract_ml_reasoner,
                "org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner": self.mock_simple_ml_reasoner,
                "org.tweetyproject.logics.ml.syntax.MlFormula": self.mock_modal_formula,
                "org.tweetyproject.logics.pl.sat.SatSolver": self.mock_sat_solver,
                "org.tweetyproject.logics.pl.sat.Sat4jSolver": self.mock_sat4j_solver,
                "org.tweetyproject.logics.pl.syntax.PlBeliefSet": self.mock_pl_belief_set # Ajout
            }
            
            def jclass_side_effect_strict(class_name):
                if class_name not in self.jclass_map:
                    raise KeyError(f"Mock JClass: La classe '{class_name}' n'est pas définie dans jclass_map. Classes disponibles: {list(self.jclass_map.keys())}")
                return self.jclass_map[class_name]

            self.mock_jpype.JClass.side_effect = jclass_side_effect_strict
            
            self.mock_pl_parser_instance = MagicMock(name="PlParser_instance_mock")
            self.mock_sat_reasoner_instance = MagicMock(name="SatReasoner_instance_mock")
            self.mock_fol_parser_instance = MagicMock(name="FolParser_instance_mock")
            self.mock_ml_parser_instance = MagicMock(name="MlParser_instance_mock")
            self.mock_simple_ml_reasoner_instance = MagicMock(name="SimpleMlReasoner_instance_mock")
            self.mock_simple_fol_reasoner_instance = MagicMock(name="SimpleFolReasoner_instance_mock")
            
            self.mock_pl_parser.return_value = self.mock_pl_parser_instance
            self.mock_sat_reasoner.return_value = self.mock_sat_reasoner_instance
            self.mock_fol_parser.return_value = self.mock_fol_parser_instance
            self.mock_simple_fol_reasoner.return_value = self.mock_simple_fol_reasoner_instance
            self.mock_ml_parser.return_value = self.mock_ml_parser_instance
            self.mock_simple_ml_reasoner.return_value = self.mock_simple_ml_reasoner_instance

            self.tweety_bridge = TweetyBridge()

            self.tweety_bridge._pl_parser_instance = self.mock_pl_parser_instance
            self.tweety_bridge._pl_reasoner_instance = self.mock_sat_reasoner_instance
            self.tweety_bridge._fol_parser_instance = self.mock_fol_parser_instance
            self.tweety_bridge._fol_reasoner_instance = self.mock_simple_fol_reasoner_instance
            self.tweety_bridge._modal_parser_instance = self.mock_ml_parser_instance
            self.tweety_bridge._modal_reasoner_instance = self.mock_simple_ml_reasoner_instance
            
            self.tweety_bridge._PlFormula = self.mock_pl_formula
            self.tweety_bridge._FolFormula = self.mock_fol_formula
            self.tweety_bridge._ModalFormula = self.mock_modal_formula
            
        else: # os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1')
            self.tweety_bridge = TweetyBridge()

    def tearDown(self):
        """Nettoyage après chaque test."""
        if self.jpype_patcher:
            self.jpype_patcher.stop()
            self.jpype_patcher = None
        if self.jvm_setup_jpype_patcher:
            self.jvm_setup_jpype_patcher.stop()
            self.jvm_setup_jpype_patcher = None
    
    def test_initialization_jvm_ready(self):
        """Test de l'initialisation lorsque la JVM est prête."""
        self.assertTrue(self.tweety_bridge.is_jvm_ready())

        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.pl.parser.PlParser")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.pl.reasoner.SatReasoner")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.pl.syntax.PlFormula")
            
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.parser.FolParser")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.reasoner.FolReasoner")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.syntax.FolFormula")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner")
            
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.parser.MlParser")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.reasoner.AbstractMlReasoner")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner")
            self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.syntax.MlFormula")
            
            self.mock_pl_parser.assert_called_once()
            self.mock_sat_reasoner.assert_called_once()
            self.mock_fol_parser.assert_called_once()
            self.mock_simple_fol_reasoner.assert_called_once()
            self.mock_ml_parser.assert_called_once()
            self.mock_simple_ml_reasoner.assert_called_once()
        else:
            # Vérifier que les handlers sont initialisés
            self.assertIsNotNone(self.tweety_bridge._pl_handler, "PLHandler non initialisé")
            self.assertIsNotNone(self.tweety_bridge._fol_handler, "FOLHandler non initialisé")
            self.assertIsNotNone(self.tweety_bridge._modal_handler, "ModalHandler non initialisé")

            # Vérifier que les parsers et reasoners dans les handlers sont initialisés
            self.assertIsNotNone(self.tweety_bridge._pl_handler._pl_parser, "PL Parser dans PLHandler non initialisé")
            self.assertIsNotNone(self.tweety_bridge._pl_handler._pl_reasoner, "PL Reasoner dans PLHandler non initialisé")
            self.assertIsNotNone(self.tweety_bridge._fol_handler._fol_parser, "FOL Parser dans FOLHandler non initialisé")
            # FOL et Modal reasoners ne sont pas initialisés par défaut dans les handlers actuels
            self.assertIsNotNone(self.tweety_bridge._modal_handler._modal_parser, "Modal Parser dans ModalHandler non initialisé")

            # Vérifier que les classes de formule sont présentes (en supposant les nouveaux noms d'attributs)
            self.assertIsNotNone(self.tweety_bridge._PlFormulaClass, "Classe PlFormula non initialisée")
            self.assertIsNotNone(self.tweety_bridge._FolFormulaClass, "Classe FolFormula non initialisée")
            self.assertIsNotNone(self.tweety_bridge._ModalFormulaClass, "Classe ModalFormula non initialisée")

    def test_initialization_jvm_not_ready(self):
        """Test de l'initialisation lorsque la JVM n'est pas prête."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            self.mock_jpype.isJVMStarted.return_value = False
            self.mock_jpype.JClass.reset_mock()
            self.mock_jpype.startJVM.reset_mock()
            self.mock_jpype.startJVM.side_effect = Exception("Mocked JVM start failure")
            
            tweety_bridge_test_instance = TweetyBridge()
            
            self.mock_jpype.startJVM.side_effect = None 
            
            self.assertFalse(tweety_bridge_test_instance.is_jvm_ready())
            self.mock_jpype.JClass.assert_not_called()
        else:
            self.skipTest("Ce test est spécifique au cas mocké où le démarrage de la JVM peut être simulé comme échoué.")

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule propositionnelle valide."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            self.mock_pl_parser_instance.parseFormula.return_value = MagicMock()
            is_valid, message = self.tweety_bridge.validate_formula("a => b")
            self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a => b")
            self.assertTrue(is_valid)
            self.assertEqual(message, "Formule valide")
        else:
            is_valid, message = self.tweety_bridge.validate_formula("a => b")
            self.assertTrue(is_valid, f"La formule 'a => b' devrait être valide avec la vraie JVM. Message: {message}")
            self.assertEqual(message, "Formule valide", f"Message inattendu pour 'a => b' avec la vraie JVM. Reçu: {message}")
    
    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule propositionnelle invalide."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer le mock du parser pour lever une exception
            java_exception_instance = self.mock_jpype.JException("Erreur de syntaxe")
            # Configurer getMessage sur l'instance si nécessaire, bien que le constructeur du mock le fasse déjà.
            # java_exception_instance.getMessage = MagicMock(return_value="Erreur de syntaxe")
            self.mock_pl_parser_instance.parseFormula.side_effect = java_exception_instance
            
            # Valider une formule
            is_valid, message = self.tweety_bridge.validate_formula("a ==> b")
            
            # Vérifier que le parser a été appelé
            self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a ==> b")
            
            # Vérifier le résultat
            self.assertFalse(is_valid)
            self.assertEqual(message, "Erreur de syntaxe: Erreur de syntaxe") # Le mock JException préfixe
        else:
            # Valider une formule invalide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_formula("a ==> b")
            
            # Vérifier le résultat
            self.assertFalse(is_valid, "La formule 'a ==> b' devrait être invalide avec la vraie JVM.")
            self.assertTrue(message, "Le message d'erreur ne devrait pas être vide pour une formule invalide.")
            self.assertIn("syntax", message.lower(), f"Le message d'erreur '{message}' devrait contenir 'syntax' pour 'a ==> b'.")
            
            # Test avec une autre formule invalide
            is_valid_complex, message_complex = self.tweety_bridge.validate_formula("p1 & (p2 | )") # Erreur de syntaxe
            self.assertFalse(is_valid_complex, "La formule 'p1 & (p2 | )' devrait être invalide.")
            self.assertIn("syntax", message_complex.lower(), f"Le message d'erreur '{message_complex}' devrait contenir 'syntax' pour 'p1 & (p2 | )'.")

    def test_validate_belief_set_valid(self):
        """Test de la validation d'un ensemble de croyances propositionnelles valide."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer le mock du parser
            mock_belief_set = MagicMock() # Cet objet mock_belief_set n'est plus directement utilisé si on ne mocke que parseFormula
            # self.mock_pl_parser_instance.parseBeliefBase.return_value = mock_belief_set # Inutile si parseBeliefBase n'est pas appelé
            
            # Mock pour parseFormula, car c'est ce qui est appelé par validate_belief_set
            # pour chaque formule dans le set.
            mock_parsed_formula = MagicMock(name="parsed_formula_mock_valid_bs")
            self.mock_pl_parser_instance.parseFormula.return_value = mock_parsed_formula

            # Valider un ensemble de croyances
            is_valid, message = self.tweety_bridge.validate_belief_set("a => b")
            
            # Vérifier que le parser a été appelé pour la formule donnée
            self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a => b")
            
            # Vérifier le résultat
            self.assertTrue(is_valid)
            self.assertEqual(message, "Ensemble de croyances valide")
        else:
            # Valider un ensemble de croyances valide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_belief_set("a => b; c.")
            self.assertTrue(is_valid, f"L'ensemble 'a => b; c.' devrait être valide. Message: {message}")
            self.assertEqual(message, "Ensemble de croyances valide", f"Message inattendu. Reçu: {message}")

    def test_validate_belief_set_empty(self):
        """Test de la validation d'un ensemble de croyances propositionnelles vide."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer le mock du parser
            # mock_belief_set = MagicMock() # Inutile
            # mock_belief_set.__str__.return_value = "" # Inutile
            # self.mock_pl_parser_instance.parseBeliefBase.return_value = mock_belief_set # Inutile

            # Valider un ensemble de croyances
            is_valid, message = self.tweety_bridge.validate_belief_set("") # Test avec chaîne vide
            
            # Vérifier que le parser (parseFormula) n'a pas été appelé car l'input est vide
            self.mock_pl_parser_instance.parseFormula.assert_not_called()
            self.mock_pl_parser_instance.parseBeliefBase.assert_not_called() # Pour être sûr
            
            # Vérifier le résultat
            self.assertFalse(is_valid)
            self.assertEqual(message, "Ensemble de croyances vide ou ne contenant que des commentaires")
        else:
            # Valider un ensemble de croyances vide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_belief_set("")
            self.assertFalse(is_valid, "Un ensemble vide devrait être invalide (ou traité comme tel).")
            self.assertEqual(message, "Ensemble de croyances vide ou ne contenant que des commentaires")
            
            is_valid_comment, message_comment = self.tweety_bridge.validate_belief_set("% commentaire seul")
            self.assertFalse(is_valid_comment, "Un ensemble avec seulement des commentaires devrait être invalide.")
            self.assertEqual(message_comment, "Ensemble de croyances vide ou ne contenant que des commentaires")

    def test_validate_belief_set_invalid(self):
        """Test de la validation d'un ensemble de croyances propositionnelles invalide."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer le mock du parser pour lever une exception sur parseFormula
            java_exception_instance = self.mock_jpype.JException("Erreur de syntaxe à la ligne 2")
            self.mock_pl_parser_instance.parseFormula.side_effect = java_exception_instance
            
            # Valider un ensemble de croyances
            is_valid, message = self.tweety_bridge.validate_belief_set("a ==> b")
            
            # Vérifier que le parser (parseFormula) a été appelé
            self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a ==> b")
            
            # Vérifier le résultat
            self.assertFalse(is_valid)
            self.assertIn("Erreur de syntaxe", message)
        else:
            # Valider un ensemble de croyances invalide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_belief_set("a ==>; c.")
            self.assertFalse(is_valid, "L'ensemble 'a ==>; c.' devrait être invalide.")
            self.assertTrue(message, "Le message d'erreur pour un ensemble invalide ne devrait pas être vide.")
            self.assertIn("syntax", message.lower(), f"Le message d'erreur '{message}' devrait contenir 'syntax'.")

    def test_execute_pl_query_accepted(self):
        """Test de l'exécution d'une requête propositionnelle acceptée."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer les mocks
            # mock_belief_set = MagicMock() # parseBeliefBase n'est pas appelé
            mock_kb_formula = MagicMock(name="mock_kb_formula")
            mock_query_formula = MagicMock(name="mock_query_formula")
            
            # Configure parseFormula pour retourner des mocks distincts pour le KB et la query
            # afin de pouvoir vérifier les appels spécifiques.
            def parse_formula_side_effect(formula_str):
                if formula_str == "a => b":
                    return mock_kb_formula
                elif formula_str == "a":
                    return mock_query_formula
                return MagicMock() # Fallback pour d'autres appels inattendus
            self.mock_pl_parser_instance.parseFormula.side_effect = parse_formula_side_effect
            
            self.mock_sat_reasoner_instance.query.return_value = True
            self.mock_jpype.JObject.return_value = True # Pour la conversion du résultat booléen Java
            
            # Exécuter une requête
            result = self.tweety_bridge.execute_pl_query("a => b", "a")
            
            # Vérifier les appels à parseFormula
            self.mock_pl_parser_instance.parseFormula.assert_any_call("a => b")
            self.mock_pl_parser_instance.parseFormula.assert_any_call("a")
            self.assertEqual(self.mock_pl_parser_instance.parseFormula.call_count, 2)
            
            # Vérifier que le reasoner a été appelé avec les formules parsées
            # Note: l'instance de PlBeliefSet est créée à l'intérieur de pl_handler,
            # donc nous vérifions que query est appelée avec *une* instance de PlBeliefSet (via mock_belief_set qui est maintenant le retour de parseFormula)
            # et la formule de requête mockée.
            # Pour une vérification plus précise du contenu du PlBeliefSet, il faudrait mocker PlBeliefSet lui-même.
            # Pour l'instant, on se concentre sur les appels aux parsers et au reasoner.
            # Le premier argument de query est un PlBeliefSet. Le mock_kb_formula est ajouté à ce PlBeliefSet.
            self.mock_sat_reasoner_instance.query.assert_called_once_with(unittest.mock.ANY, mock_query_formula)

            self.assertIn("ACCEPTED", result)
        else:
            # Exécuter une requête acceptée avec la vraie JVM
            result = self.tweety_bridge.execute_pl_query("a; a=>b", "b") # KB: a, a implies b. Query: b.
            self.assertIn("ACCEPTED", result, f"Query 'b' from 'a; a=>b' should be ACCEPTED. Result: {result}")
            
            result_complex = self.tweety_bridge.execute_pl_query("p1; p2; (p1 && p2) => q", "q")
            self.assertIn("ACCEPTED", result_complex, f"Query 'q' from 'p1; p2; (p1 && p2) => q' should be ACCEPTED. Result: {result_complex}")

    def test_execute_pl_query_rejected(self):
        """Test de l'exécution d'une requête propositionnelle rejetée."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer les mocks
            # mock_belief_set = MagicMock() # parseBeliefBase n'est pas appelé
            mock_kb_formula_rejected = MagicMock(name="mock_kb_formula_rejected")
            mock_query_formula_rejected = MagicMock(name="mock_query_formula_rejected")

            def parse_formula_side_effect_rejected(formula_str):
                if formula_str == "a => b":
                    return mock_kb_formula_rejected
                elif formula_str == "c":
                    return mock_query_formula_rejected
                return MagicMock()
            self.mock_pl_parser_instance.parseFormula.side_effect = parse_formula_side_effect_rejected
            
            self.mock_sat_reasoner_instance.query.return_value = False
            self.mock_jpype.JObject.return_value = True
            
            # Exécuter une requête
            result = self.tweety_bridge.execute_pl_query("a => b", "c")
            
            # Vérifier les appels à parseFormula
            self.mock_pl_parser_instance.parseFormula.assert_any_call("a => b")
            self.mock_pl_parser_instance.parseFormula.assert_any_call("c")
            self.assertEqual(self.mock_pl_parser_instance.parseFormula.call_count, 2)
            
            self.mock_sat_reasoner_instance.query.assert_called_once_with(unittest.mock.ANY, mock_query_formula_rejected)
            self.assertIn("REJECTED", result)
        else:
            # Exécuter une requête rejetée avec la vraie JVM
            result = self.tweety_bridge.execute_pl_query("a; a=>b", "c") # KB: a, a implies b. Query: c.
            self.assertIn("REJECTED", result, f"Query 'c' from 'a; a=>b' should be REJECTED. Result: {result}")

    def test_execute_pl_query_error(self):
        """Test de l'exécution d'une requête propositionnelle avec erreur."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer le mock du parser pour lever une exception
            java_exception = self.mock_jpype.JException("Erreur de syntaxe")
            # L'erreur doit se produire lors du parsing de la première formule du KB
            self.mock_pl_parser_instance.parseFormula.side_effect = java_exception
            
            # Exécuter une requête
            result = self.tweety_bridge.execute_pl_query("a ==> b", "a")
            
            # Vérifier que parseFormula a été appelé (et a levé l'exception)
            self.mock_pl_parser_instance.parseFormula.assert_called_once_with("a ==> b")
            self.assertIn("FUNC_ERROR", result)
            self.assertIn("Erreur de syntaxe", result)
        else:
            # Exécuter une requête avec erreur de syntaxe dans la base avec la vraie JVM
            result = self.tweety_bridge.execute_pl_query("a ==>; b", "c") 
            self.assertIn("FUNC_ERROR", result, f"Query with syntax error in KB should be FUNC_ERROR. Result: {result}")
            self.assertTrue(result) # S'assurer que le message d'erreur n'est pas vide
            self.assertTrue("error" in result.lower() or "exception" in result.lower() or "parsing" in result.lower(), f"Error message '{result}' should contain 'error', 'exception', or 'parsing'.")

    def test_validate_fol_formula(self):
        """Test de la validation d'une formule du premier ordre."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer le mock du parser
            self.mock_fol_parser_instance.parseFormula.return_value = MagicMock()
            
            # Valider une formule
            is_valid, message = self.tweety_bridge.validate_fol_formula("forall X: (P(X) => Q(X))")
            
            # Vérifier que le parser a été appelé
            self.mock_fol_parser_instance.parseFormula.assert_called_once_with("forall X: (P(X) => Q(X))")
            
            # Vérifier le résultat
            self.assertTrue(is_valid)
            self.assertEqual(message, "Formule FOL valide")
        else:
            # Valider une formule FOL valide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_fol_formula("forall X: (p(X) => p(X))") # Prédicat en minuscule
            self.assertTrue(is_valid, f"FOL Formula 'forall X: (p(X) => p(X))' should be valid. Message: {message}")
            self.assertEqual(message, "Formule FOL valide", f"Message inattendu. Reçu: {message}")
            
            # Valider une formule FOL invalide avec la vraie JVM
            is_valid_invalid, message_invalid = self.tweety_bridge.validate_fol_formula("forall X: p(X) &") # Prédicat en minuscule, erreur de syntaxe claire
            self.assertFalse(is_valid_invalid, f"FOL Formula 'forall X: p(X) &' should be invalid. Message: {message_invalid}")
            self.assertTrue(message_invalid)
            self.assertTrue("syntax" in message_invalid.lower() or "error" in message_invalid.lower(), f"Message d'erreur '{message_invalid}' devrait contenir 'syntax' or 'error'.")
    def test_validate_modal_formula(self):
        """Test de la validation d'une formule modale."""
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            # Configurer le mock du parser
            self.mock_ml_parser_instance.parseFormula.return_value = MagicMock(name="parsed_modal_formula_mock")
            
            # Valider une formule
            is_valid, message = self.tweety_bridge.validate_modal_formula("[]p => <>q")
            
            # Vérifier que le parser a été appelé
            # Ces prints sont utiles pour déboguer les mocks
            print(f"DEBUG (mock): ID of self.tweety_bridge._modal_parser_instance: {id(self.tweety_bridge._modal_parser_instance)}")
            print(f"DEBUG (mock): ID of self.mock_ml_parser_instance: {id(self.mock_ml_parser_instance)}")
            self.assertIs(self.tweety_bridge._modal_parser_instance, self.mock_ml_parser_instance, "Instance de _modal_parser_instance n'est pas self.mock_ml_parser_instance")
            
            self.tweety_bridge._modal_parser_instance.parseFormula.assert_called_once_with("[]p => <>q")
            
            # Vérifier le résultat
            self.assertTrue(is_valid)
            self.assertEqual(message, "Formule modale valide")
        else:
            # Valider une formule modale valide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_modal_formula("[] (prop1) => <> (prop1)") # Proposition en minuscule
            self.assertTrue(is_valid, f"Modal formula '[] (prop1) => <> (prop1)' should be valid. Message: {message}")
            self.assertEqual(message, "Formule modale valide", f"Message inattendu. Reçu: {message}")

            # Valider une formule modale invalide avec la vraie JVM
            is_valid_invalid, message_invalid = self.tweety_bridge.validate_modal_formula("[] (prop1) => <>") # Invalide
            self.assertFalse(is_valid_invalid, f"Modal formula '[] (prop1) => <>' should be invalid. Message: {message_invalid}")
            self.assertTrue(message_invalid)
            self.assertTrue("syntax" in message_invalid.lower() or "error" in message_invalid.lower(), f"Message d'erreur '{message_invalid}' devrait contenir 'syntax' or 'error'.")

if __name__ == "__main__":
    unittest.main()
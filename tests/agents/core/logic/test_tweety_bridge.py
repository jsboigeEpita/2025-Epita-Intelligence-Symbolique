# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_tweety_bridge.py
"""
Tests unitaires pour la classe TweetyBridge.
"""

import sys # Ajout de sys
import os
from pathlib import Path # Ajout de Path

# Ajout pour forcer la reconnaissance du package principal
current_script_path = Path(__file__).resolve()
project_root_for_test = current_script_path.parents[4] # Remonter de tests/agents/core/logic à la racine du projet
sys.path.insert(0, str(project_root_for_test))
print(f"DEBUG: sys.path[0] in test_tweety_bridge.py set to: {str(project_root_for_test)}")

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from tests.mocks.jpype_mock import jpype_mock

from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

class TestTweetyBridge(unittest.TestCase):
    """Tests pour la classe TweetyBridge."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # FORCER PROVISOIREMENT L'UTILISATION DES MOCKS pour débogage
        # self.use_real_jpype = False # Commenté pour utiliser la variable d'environnement
        self.use_real_jpype = os.environ.get('USE_REAL_JPYPE') == 'true' # Ligne originale décommentée
        
        self.jpype_patcher = None
        self.mock_jpype = None # Mock pour jpype dans tweety_bridge lui-même

        # Patchers pour TweetyInitializer et Handlers
        self.tweety_initializer_patcher = None
        self.mock_tweety_initializer_class = None # Mock de la classe TweetyInitializer
        self.mock_tweety_initializer_instance = None # Mock de l'instance retournée par get_instance()

        self.pl_handler_patcher = None
        self.mock_pl_handler_class = None
        self.mock_pl_handler_instance = None # Mock de l'instance de PLHandler

        self.fol_handler_patcher = None
        self.mock_fol_handler_class = None
        self.mock_fol_handler_instance = None # Mock de l'instance de FOLHandler

        self.modal_handler_patcher = None
        self.mock_modal_handler_class = None
        self.mock_modal_handler_instance = None # Mock de l'instance de ModalHandler
        
        # Mocks pour les composants Java (parsers, reasoners) retournés par TweetyInitializer statique
        self.mock_java_pl_parser = MagicMock(name="MockJavaPlParser")
        self.mock_java_pl_reasoner = MagicMock(name="MockJavaPlReasoner")
        self.mock_java_fol_parser = MagicMock(name="MockJavaFolParser")
        # self.mock_java_fol_reasoner = MagicMock(name="MockJavaFolReasoner") # Si FOLHandler l'utilise
        self.mock_java_modal_parser = MagicMock(name="MockJavaModalParser")
        # self.mock_java_modal_reasoner = MagicMock(name="MockJavaModalReasoner") # Si ModalHandler l'utilise

        if not self.use_real_jpype:
            # 1. Patcher jpype dans tweety_bridge (principalement pour JException)
            self.jpype_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.jpype')
            self.mock_jpype = self.jpype_patcher.start()
            self.mock_jpype.JException = jpype_mock.JException

            # 2. Patcher TweetyInitializer
            #    Patch la classe TweetyInitializer là où elle est importée par TweetyBridge et les Handlers.
            #    Nous devons patcher `get_instance` et les méthodes statiques `get_..._parser/reasoner`.
            self.tweety_initializer_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.TweetyInitializer')
            self.mock_tweety_initializer_class = self.tweety_initializer_patcher.start()

            # Configurer le mock de la classe TweetyInitializer
            self.mock_tweety_initializer_instance = MagicMock(name="MockTweetyInitializerInstance")
            # self.mock_tweety_initializer_class.get_instance.return_value = self.mock_tweety_initializer_instance # Supprimé car get_instance n'est plus utilisé
            self.mock_tweety_initializer_class.return_value = self.mock_tweety_initializer_instance # Assure que l'appel de la classe mockée retourne notre instance mockée
            
            # Configurer les méthodes de l'instance mockée de TweetyInitializer
            # Remplacé par une propriété mockée pour suivre la nouvelle implémentation
            type(self.mock_tweety_initializer_instance).is_jvm_ready = PropertyMock(return_value=True)
            self.mock_tweety_initializer_instance.initialize_pl_components = MagicMock()
            self.mock_tweety_initializer_instance.initialize_fol_components = MagicMock()
            self.mock_tweety_initializer_instance.initialize_modal_components = MagicMock()


            # Configurer les méthodes statiques mockées de TweetyInitializer (utilisées par les Handlers)
            # Ces mocks seront utilisés lorsque les vrais Handlers (ou leurs mocks) appellent TweetyInitializer.get_...
            # Pour que cela fonctionne, il faut aussi patcher TweetyInitializer dans pl_handler.py, fol_handler.py, modal_handler.py
            # ou s'assurer que le patch ici est global. Pour l'instant, on se concentre sur le patch dans tweety_bridge.
            # Si les Handlers sont aussi mockés (voir ci-dessous), leurs __init__ ne seront pas appelés par défaut,
            # sauf si on configure le mock de la classe Handler pour appeler l'original ou si on teste les vrais Handlers.
            
            # Pour simplifier, nous allons patcher les méthodes statiques directement sur self.mock_tweety_initializer_class
            # car c'est ce que les handlers vont référencer s'ils importent TweetyInitializer du même module.
            # Si les handlers importent `from .tweety_initializer import TweetyInitializer`, il faudra patcher là-bas aussi.
            # Pour l'instant, on suppose que le patch dans tweety_bridge est suffisant ou que les handlers sont mockés.
            
            self.mock_tweety_initializer_class.get_pl_parser.return_value = self.mock_java_pl_parser
            self.mock_tweety_initializer_class.get_pl_reasoner.return_value = self.mock_java_pl_reasoner
            self.mock_tweety_initializer_class.get_fol_parser.return_value = self.mock_java_fol_parser
            self.mock_tweety_initializer_class.get_modal_parser.return_value = self.mock_java_modal_parser
            # Ajouter get_fol_reasoner, get_modal_reasoner si nécessaire

            # 3. Patcher les Handlers
            self.pl_handler_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.PLHandler')
            self.mock_pl_handler_class = self.pl_handler_patcher.start()
            self.mock_pl_handler_instance = MagicMock(name="MockPLHandlerInstance")
            self.mock_pl_handler_class.return_value = self.mock_pl_handler_instance # TweetyBridge obtiendra ce mock lors de l'instanciation

            self.fol_handler_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.FOLHandler')
            self.mock_fol_handler_class = self.fol_handler_patcher.start()
            self.mock_fol_handler_instance = MagicMock(name="MockFOLHandlerInstance")
            self.mock_fol_handler_class.return_value = self.mock_fol_handler_instance

            self.modal_handler_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.ModalHandler')
            self.mock_modal_handler_class = self.modal_handler_patcher.start()
            self.mock_modal_handler_instance = MagicMock(name="MockModalHandlerInstance")
            self.mock_modal_handler_class.return_value = self.mock_modal_handler_instance
            
            # Initialiser TweetyBridge APRÈS que tous les patchs sont en place
            self.tweety_bridge = TweetyBridge()
            
        else: # self.use_real_jpype is True
            self.tweety_bridge = TweetyBridge()

    def tearDown(self):
        """Nettoyage après chaque test."""
        if self.jpype_patcher:
            self.jpype_patcher.stop()
        if self.tweety_initializer_patcher:
            self.tweety_initializer_patcher.stop()
        if self.pl_handler_patcher:
            self.pl_handler_patcher.stop()
        if self.fol_handler_patcher:
            self.fol_handler_patcher.stop()
        if self.modal_handler_patcher:
            self.modal_handler_patcher.stop()
    
    def test_initialization_jvm_ready(self):
        """Test de l'initialisation lorsque la JVM est prête."""
        if not self.use_real_jpype:
            # TweetyBridge instancie TweetyInitializer directement dans son __init__
            # donc on vérifie que la classe mockée TweetyInitializer a été appelée pour créer une instance.
            # TweetyBridge passe `self` (l'instance de TweetyBridge) à TweetyInitializer.
            # L'instance de TweetyBridge est self.tweety_bridge, créée dans setUp.
            self.mock_tweety_initializer_class.assert_called_once_with(self.tweety_bridge)
            
            # Vérifier que is_jvm_ready a été vérifiée
            self.assertTrue(self.mock_tweety_initializer_instance.is_jvm_ready)
            
            # Les handlers sont maintenant initialisés directement dans le constructeur de TweetyBridge
            # donc nous n'avons plus à mocker les méthodes d'initialisation des composants sur l'initializer.
            # On vérifie que les classes des handlers ont été instanciées.
            
            # Vérifier que les constructeurs des Handlers ont été appelés
            self.mock_pl_handler_class.assert_called_once()
            self.mock_fol_handler_class.assert_called_once()
            self.mock_modal_handler_class.assert_called_once()
            
            # Vérifier que TweetyBridge considère la JVM comme prête
            self.assertTrue(self.tweety_bridge.is_jvm_ready())
        else:
            # Pour le cas réel, on vérifie juste que l'initialisation ne lève pas d'erreur
            # et que is_jvm_ready retourne True.
            self.assertTrue(self.tweety_bridge.is_jvm_ready(), "TweetyBridge devrait être prêt avec la vraie JVM.")
            # Des assertions plus spécifiques sur les instances réelles pourraient être ajoutées si nécessaire,
            # mais cela relèverait plus de tests d'intégration pour les handlers/initializer.
            self.assertIsNotNone(self.tweety_bridge._initializer)
            self.assertIsNotNone(self.tweety_bridge._pl_handler)
            self.assertIsNotNone(self.tweety_bridge._fol_handler)
            self.assertIsNotNone(self.tweety_bridge._modal_handler)

    def test_initialization_jvm_not_ready(self):
        """Test de l'initialisation lorsque la JVM n'est pas prête."""
        if not self.use_real_jpype:
            # Configurer le mock de TweetyInitializer pour simuler un échec d'initialisation de la JVM
            # 1. is_jvm_ready() retourne False initialement
            # 2. start_jvm_and_initialize() est appelée
            # 3. is_jvm_ready() retourne toujours False après l'appel à start_jvm_and_initialize
            
            # Réinitialiser les mocks pour ce test spécifique
            self.mock_tweety_initializer_class.reset_mock()
            self.mock_pl_handler_class.reset_mock()
            self.mock_fol_handler_class.reset_mock()
            self.mock_modal_handler_class.reset_mock()
            # Ne pas réinitialiser self.mock_tweety_initializer_instance ici, car nous allons en créer un local.
 
            # Créer et configurer une instance de mock locale pour TweetyInitializer
            local_mock_initializer_instance = MagicMock(name="LocalMockTweetyInitializerInstance")
            # is_jvm_started est appelée une première fois. Si False, TweetyBridge loggue.
            # Puis is_jvm_started est appelée une seconde fois. Si toujours False, TweetyBridge lève une exception.
            # On configure le mock de la classe pour qu'il lève une exception LORS de l'instanciation
            self.mock_tweety_initializer_class.side_effect = RuntimeError("TweetyBridge ne peut pas fonctionner sans une JVM initialisée.")
    
            # S'attendre à une RuntimeError lors de l'instanciation de TweetyBridge
            with self.assertRaisesRegex(RuntimeError, "TweetyBridge ne peut pas fonctionner sans une JVM initialisée."):
                TweetyBridge()
    
            # Vérifications des appels
            self.mock_tweety_initializer_class.assert_called_once_with(unittest.mock.ANY) # L'instance est passée en argument
    
            # Les handlers ne devraient pas être initialisés si la JVM échoue
            self.mock_pl_handler_class.assert_not_called()
            self.mock_fol_handler_class.assert_not_called()
            self.mock_modal_handler_class.assert_not_called()
        else:
            self.skipTest("Ce test est spécifique au cas mocké où le démarrage de la JVM peut être simulé comme échoué.")

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule propositionnelle valide."""
        formula_str = "a => b"
        if not self.use_real_jpype:
            # Configurer le mock de PLHandler pour ne pas lever d'exception lors du parsing
            self.mock_pl_handler_instance.parse_pl_formula.return_value = MagicMock(name="ParsedPlFormulaMock") # Simule un objet formule parsé

            is_valid, message = self.tweety_bridge.validate_formula(formula_str)
            
            # Vérifier que la méthode du handler a été appelée
            self.mock_pl_handler_instance.parse_pl_formula.assert_called_once_with(formula_str)
            self.assertTrue(is_valid)
            self.assertEqual(message, "Formule valide")
        else:
            is_valid, message = self.tweety_bridge.validate_formula(formula_str)
            self.assertTrue(is_valid, f"La formule '{formula_str}' devrait être valide avec la vraie JVM. Message: {message}")
            self.assertEqual(message, "Formule valide", f"Message inattendu pour '{formula_str}' avec la vraie JVM. Reçu: {message}")
    
    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule propositionnelle invalide."""
        formula_str = "a ==> b"
        error_detail = "Détail de l'erreur de syntaxe du handler"
        if not self.use_real_jpype:
            # Configurer le mock de PLHandler pour lever une ValueError lors du parsing
            self.mock_pl_handler_instance.parse_pl_formula.side_effect = ValueError(error_detail)
            
            is_valid, message = self.tweety_bridge.validate_formula(formula_str)
            
            # Vérifier que la méthode du handler a été appelée
            self.mock_pl_handler_instance.parse_pl_formula.assert_called_once_with(formula_str)
            
            self.assertFalse(is_valid)
            self.assertEqual(message, f"Erreur de syntaxe: {error_detail}")
        else:
            # Valider une formule invalide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_formula(formula_str)
            
            self.assertFalse(is_valid, f"La formule '{formula_str}' devrait être invalide avec la vraie JVM.")
            self.assertTrue(message, "Le message d'erreur ne devrait pas être vide pour une formule invalide.")
            # Le message exact peut varier, mais il devrait indiquer une erreur de syntaxe.
            self.assertIn("syntax", message.lower(), f"Le message d'erreur '{message}' devrait contenir 'syntax' pour '{formula_str}'.")
            
            # Test avec une autre formule invalide
            formula_complex = "p1 & (p2 | )"
            is_valid_complex, message_complex = self.tweety_bridge.validate_formula(formula_complex) # Erreur de syntaxe
            self.assertFalse(is_valid_complex, f"La formule '{formula_complex}' devrait être invalide.")
            self.assertIn("syntax", message_complex.lower(), f"Le message d'erreur '{message_complex}' devrait contenir 'syntax' pour '{formula_complex}'.")

    def test_validate_belief_set_valid(self):
        """Test de la validation d'un ensemble de croyances propositionnelles valide."""
        belief_set_str = "a => b; c" # TweetyBridge._remove_comments_and_empty_lines enlèvera le point final s'il y en a un.
        cleaned_formulas = ["a => b", "c"] # Ce que _remove_comments_and_empty_lines devrait retourner

        if not self.use_real_jpype:
            # Configurer le mock de PLHandler pour ne pas lever d'exception lors du parsing
            self.mock_pl_handler_instance.parse_pl_formula.return_value = MagicMock(name="ParsedPlFormulaMock")
            
            # On peut aussi mocker _remove_comments_and_empty_lines pour contrôler son output
            with patch.object(self.tweety_bridge, '_remove_comments_and_empty_lines', return_value=cleaned_formulas) as mock_remove_lines:
                is_valid, message = self.tweety_bridge.validate_belief_set(belief_set_str)
            
            mock_remove_lines.assert_called_once_with(belief_set_str)
            
            # Vérifier que la méthode du handler a été appelée pour chaque formule nettoyée
            self.assertEqual(self.mock_pl_handler_instance.parse_pl_formula.call_count, len(cleaned_formulas))
            for formula in cleaned_formulas:
                self.mock_pl_handler_instance.parse_pl_formula.assert_any_call(formula)
            
            self.assertTrue(is_valid)
            self.assertEqual(message, "Ensemble de croyances valide")
        else:
            # Valider un ensemble de croyances valide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_belief_set("a => b; c.") # Avec un point final
            self.assertTrue(is_valid, f"L'ensemble 'a => b; c.' devrait être valide. Message: {message}")
            self.assertEqual(message, "Ensemble de croyances valide", f"Message inattendu. Reçu: {message}")

            is_valid_nocomment, message_nocomment = self.tweety_bridge.validate_belief_set("p1; p2 || p3")
            self.assertTrue(is_valid_nocomment, f"L'ensemble 'p1; p2 || p3' devrait être valide. Message: {message_nocomment}")
            self.assertEqual(message_nocomment, "Ensemble de croyances valide")

    def test_validate_belief_set_empty(self):
        """Test de la validation d'un ensemble de croyances propositionnelles vide."""
        belief_set_empty_str = ""
        belief_set_comment_str = "% commentaire seul"
        expected_message = "Ensemble de croyances vide ou ne contenant que des commentaires"

        if not self.use_real_jpype:
            # Test avec chaîne vide
            with patch.object(self.tweety_bridge, '_remove_comments_and_empty_lines', return_value=[]) as mock_remove_lines_empty:
                is_valid_empty, message_empty = self.tweety_bridge.validate_belief_set(belief_set_empty_str)
            
            mock_remove_lines_empty.assert_called_once_with(belief_set_empty_str)
            self.mock_pl_handler_instance.parse_pl_formula.assert_not_called() # Ne devrait pas être appelé si la liste est vide
            self.assertFalse(is_valid_empty)
            self.assertEqual(message_empty, expected_message)
            
            self.mock_pl_handler_instance.parse_pl_formula.reset_mock() # Réinitialiser pour le prochain test

            # Test avec seulement des commentaires
            with patch.object(self.tweety_bridge, '_remove_comments_and_empty_lines', return_value=[]) as mock_remove_lines_comment:
                is_valid_comment, message_comment = self.tweety_bridge.validate_belief_set(belief_set_comment_str)

            mock_remove_lines_comment.assert_called_once_with(belief_set_comment_str)
            self.mock_pl_handler_instance.parse_pl_formula.assert_not_called()
            self.assertFalse(is_valid_comment)
            self.assertEqual(message_comment, expected_message)
        else:
            # Valider un ensemble de croyances vide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_belief_set(belief_set_empty_str)
            self.assertFalse(is_valid, "Un ensemble vide devrait retourner False.")
            self.assertEqual(message, expected_message)
            
            is_valid_comment, message_comment = self.tweety_bridge.validate_belief_set(belief_set_comment_str)
            self.assertFalse(is_valid_comment, "Un ensemble avec seulement des commentaires devrait retourner False.")
            self.assertEqual(message_comment, expected_message)

    def test_validate_belief_set_invalid(self):
        """Test de la validation d'un ensemble de croyances propositionnelles invalide."""
        belief_set_str = "a => b; a ==> c" # La deuxième formule est invalide
        cleaned_formulas = ["a => b", "a ==> c"]
        error_detail = "Erreur sur a ==> c"

        if not self.use_real_jpype:
            # Configurer le mock de PLHandler pour lever une ValueError sur la deuxième formule
            self.mock_pl_handler_instance.parse_pl_formula.side_effect = [
                MagicMock(name="ParsedOkFormula"), # Pour "a => b"
                ValueError(error_detail)          # Pour "a ==> c"
            ]
            
            with patch.object(self.tweety_bridge, '_remove_comments_and_empty_lines', return_value=cleaned_formulas) as mock_remove_lines:
                is_valid, message = self.tweety_bridge.validate_belief_set(belief_set_str)
            
            mock_remove_lines.assert_called_once_with(belief_set_str)
            
            # parse_pl_formula devrait être appelée pour "a => b" et "a ==> c"
            self.assertEqual(self.mock_pl_handler_instance.parse_pl_formula.call_count, 2)
            self.mock_pl_handler_instance.parse_pl_formula.assert_any_call("a => b")
            self.mock_pl_handler_instance.parse_pl_formula.assert_any_call("a ==> c")
            
            self.assertFalse(is_valid)
            self.assertEqual(message, f"Erreur de syntaxe: {error_detail}")
        else:
            # Valider un ensemble de croyances invalide avec la vraie JVM
            is_valid, message = self.tweety_bridge.validate_belief_set("a ==>; c.")
            self.assertFalse(is_valid, "L'ensemble 'a ==>; c.' devrait être invalide.")
            self.assertTrue(message, "Le message d'erreur pour un ensemble invalide ne devrait pas être vide.")
            self.assertIn("syntax", message.lower(), f"Le message d'erreur '{message}' devrait contenir 'syntax'.")

    def test_execute_pl_query_accepted(self):
        """Test de l'exécution d'une requête propositionnelle acceptée."""
        belief_set_content = "a; a=>b"
        query_string = "b"
        
        if not self.use_real_jpype:
            # Configurer le mock de PLHandler pour retourner True
            self.mock_pl_handler_instance.pl_query.return_value = True
            
            result, message = self.tweety_bridge.execute_pl_query(belief_set_content, query_string)
            self.mock_pl_handler_instance.pl_query.assert_called_once_with(belief_set_content, query_string)
            self.assertTrue(result)
            self.assertIn(f"Query '{query_string}' is ACCEPTED (True)", message)
        else:
            is_accepted, message = self.tweety_bridge.execute_pl_query(belief_set_content, query_string)
            self.assertTrue(is_accepted, f"Query '{query_string}' from '{belief_set_content}' should be ACCEPTED. Message: {message}")
            self.assertIn("ACCEPTED (True)", message)

            belief_set_complex = "p1; p2; (p1 && p2) => q"
            query_complex = "q"
            is_accepted_complex, message_complex = self.tweety_bridge.execute_pl_query(belief_set_complex, query_complex)
            self.assertTrue(is_accepted_complex, f"Query '{query_complex}' from '{belief_set_complex}' should be ACCEPTED. Message: {message_complex}")
            self.assertIn("ACCEPTED (True)", message_complex)

    def test_execute_pl_query_rejected(self):
        """Test de l'exécution d'une requête propositionnelle rejetée."""
        belief_set_content = "a; a=>b"
        query_string = "c"

        if not self.use_real_jpype:
            # Configurer le mock de PLHandler pour retourner False
            self.mock_pl_handler_instance.pl_query.return_value = False
            
            result, message = self.tweety_bridge.execute_pl_query(belief_set_content, query_string)
            self.mock_pl_handler_instance.pl_query.assert_called_once_with(belief_set_content, query_string)
            self.assertFalse(result)
            self.assertIn(f"Query '{query_string}' is REJECTED (False)", message)
        else:
            is_accepted, message = self.tweety_bridge.execute_pl_query(belief_set_content, query_string)
            self.assertFalse(is_accepted, f"Query '{query_string}' from '{belief_set_content}' should be REJECTED. Message: {message}")
            self.assertIn("REJECTED (False)", message)

    def test_execute_pl_query_error(self):
        """Test de l'exécution d'une requête propositionnelle avec erreur."""
        belief_set_content_invalid = "a ==> b" # Erreur de syntaxe dans le BS
        query_string = "a"
        error_detail_handler = "Erreur de parsing du handler pour le BS"

        if not self.use_real_jpype:
            # Configurer le mock de PLHandler pour lever une ValueError
            self.mock_pl_handler_instance.pl_query.side_effect = ValueError(error_detail_handler)
            
            result, message = self.tweety_bridge.execute_pl_query(belief_set_content_invalid, query_string)
            self.mock_pl_handler_instance.pl_query.assert_called_once_with(belief_set_content_invalid, query_string)
            self.assertFalse(result, "Result should be False on error")
            self.assertIn("FUNC_ERROR", message)
            expected_error_message_part = f"Error during PL query execution via PLHandler: {error_detail_handler}"
            self.assertIn(expected_error_message_part, message)
        else:
            result, message = self.tweety_bridge.execute_pl_query(belief_set_content_invalid, query_string)
            self.assertFalse(result, f"Result should be False for a query with syntax error in KB. Got: {result}")
            self.assertIn("FUNC_ERROR", message, f"Message for query with syntax error in KB '{belief_set_content_invalid}' should be FUNC_ERROR. Message: {message}")

    def test_validate_fol_formula(self):
        """Test de la validation d'une formule du premier ordre."""
        formula_valid_str = "forall X: (p(X) => q(X))"
        formula_invalid_str = "forall X: p(X) &"
        signature_str = "sort person; predicate p(person); predicate q(person);" # Exemple de signature
        error_detail_handler = "Détail erreur syntaxe FOL handler"

        if not self.use_real_jpype:
            # Test cas valide
            self.mock_fol_handler_instance.parse_fol_formula.return_value = MagicMock(name="ParsedFolFormulaMock")
            is_valid, message = self.tweety_bridge.validate_fol_formula(formula_valid_str, signature_str)
            self.mock_fol_handler_instance.parse_fol_formula.assert_called_once_with(formula_valid_str, signature_str)
            self.assertTrue(is_valid)
            self.assertEqual(message, "Formule FOL valide")
            self.mock_fol_handler_instance.parse_fol_formula.reset_mock()

            # Test cas invalide
            self.mock_fol_handler_instance.parse_fol_formula.side_effect = ValueError(error_detail_handler)
            is_valid_invalid, message_invalid = self.tweety_bridge.validate_fol_formula(formula_invalid_str, signature_str)
            self.mock_fol_handler_instance.parse_fol_formula.assert_called_once_with(formula_invalid_str, signature_str)
            self.assertFalse(is_valid_invalid)
            self.assertEqual(message_invalid, f"Erreur de syntaxe FOL: {error_detail_handler}")
        else:
            # Valider une formule FOL valide avec la vraie JVM
            # Note: Pour FOL, la validité peut dépendre de la déclaration des prédicats/sorts.
            # TweetyBridge.validate_fol_formula ne prend pas de signature pour l'instant,
            # mais le handler oui. Les tests ici doivent refléter cela.
            # Pour un test simple, on utilise une formule qui ne dépend pas de prédicats complexes.
            is_valid_real, message_real = self.tweety_bridge.validate_fol_formula("forall X: (p(X) => p(X))") # Pas de signature passée ici
            self.assertTrue(is_valid_real, f"FOL Formula 'forall X: (p(X) => p(X))' should be valid. Message: {message_real}")
            self.assertEqual(message_real, "Formule FOL valide", f"Message inattendu. Reçu: {message_real}")
            
            # Valider une formule FOL invalide avec la vraie JVM
            is_valid_invalid_real, message_invalid_real = self.tweety_bridge.validate_fol_formula(formula_invalid_str)
            self.assertFalse(is_valid_invalid_real, f"FOL Formula '{formula_invalid_str}' should be invalid. Message: {message_invalid_real}")
            self.assertTrue(message_invalid_real)
            self.assertTrue("syntax" in message_invalid_real.lower() or "error" in message_invalid_real.lower(), f"Message d'erreur '{message_invalid_real}' devrait contenir 'syntax' or 'error'.")

    def test_validate_modal_formula(self):
        """Test de la validation d'une formule modale."""
        formula_valid_str = "[]p => <>q"
        formula_invalid_str = "[]p => <>" # Erreur de syntaxe
        modal_logic = "S4"
        error_detail_handler = "Détail erreur syntaxe Modale handler"

        if not self.use_real_jpype:
            # Test cas valide
            self.mock_modal_handler_instance.parse_modal_formula.return_value = MagicMock(name="ParsedModalFormulaMock")
            is_valid, message = self.tweety_bridge.validate_modal_formula(formula_valid_str, modal_logic)
            self.mock_modal_handler_instance.parse_modal_formula.assert_called_once_with(formula_valid_str, modal_logic)
            self.assertTrue(is_valid)
            self.assertEqual(message, "Formule Modale valide")
            self.mock_modal_handler_instance.parse_modal_formula.reset_mock()

            # Test cas invalide
            self.mock_modal_handler_instance.parse_modal_formula.side_effect = ValueError(error_detail_handler)
            is_valid_invalid, message_invalid = self.tweety_bridge.validate_modal_formula(formula_invalid_str, modal_logic)
            self.mock_modal_handler_instance.parse_modal_formula.assert_called_once_with(formula_invalid_str, modal_logic)
            self.assertFalse(is_valid_invalid)
            self.assertEqual(message_invalid, f"Erreur de syntaxe Modale: {error_detail_handler}")
        else:
            # Valider une formule modale valide avec la vraie JVM
            is_valid_real, message_real = self.tweety_bridge.validate_modal_formula("[] (prop1) => <> (prop1)", modal_logic)
            self.assertTrue(is_valid_real, f"Modal formula '[] (prop1) => <> (prop1)' (Logic: {modal_logic}) should be valid. Message: {message_real}")
            self.assertEqual(message_real, "Formule Modale valide", f"Message inattendu. Reçu: {message_real}")

            # Valider une formule modale invalide avec la vraie JVM
            is_valid_invalid_real, message_invalid_real = self.tweety_bridge.validate_modal_formula(formula_invalid_str, modal_logic)
            self.assertFalse(is_valid_invalid_real, f"Modal formula '{formula_invalid_str}' (Logic: {modal_logic}) should be invalid. Message: {message_invalid_real}")
            self.assertTrue(message_invalid_real)
            self.assertTrue("syntax" in message_invalid_real.lower() or "error" in message_invalid_real.lower(), f"Message d'erreur '{message_invalid_real}' devrait contenir 'syntax' or 'error'.")

    # --- Tests pour FOL Belief Set ---
    def test_validate_fol_belief_set_valid(self):
        """Test de la validation d'un ensemble de croyances FOL valide."""
        belief_set_str = "forall X: p(X); exists Y: q(Y)"
        cleaned_formulas = ["forall X: p(X)", "exists Y: q(Y)"]
        signature_str = "sort T; predicate p(T); predicate q(T);"

        if not self.use_real_jpype:
            self.mock_fol_handler_instance.parse_fol_formula.return_value = MagicMock(name="ParsedFolFormulaMock")
            with patch.object(self.tweety_bridge, '_remove_comments_and_empty_lines', return_value=cleaned_formulas) as mock_remove_lines:
                is_valid, message = self.tweety_bridge.validate_fol_belief_set(belief_set_str, signature_str)
            
            mock_remove_lines.assert_called_once_with(belief_set_str)
            self.assertEqual(self.mock_fol_handler_instance.parse_fol_formula.call_count, len(cleaned_formulas))
            for formula in cleaned_formulas:
                self.mock_fol_handler_instance.parse_fol_formula.assert_any_call(formula, signature_str)
            self.assertTrue(is_valid)
            self.assertEqual(message, "Ensemble de croyances FOL valide")
        else:
            is_valid, message = self.tweety_bridge.validate_fol_belief_set("forall X: p(X).", "sort T; predicate p(T).")
            self.assertTrue(is_valid, f"L'ensemble FOL devrait être valide. Message: {message}")
            self.assertEqual(message, "Ensemble de croyances FOL valide")

    def test_validate_fol_belief_set_empty(self):
        """Test de la validation d'un ensemble de croyances FOL vide."""
        expected_message = "Ensemble de croyances FOL vide ou ne contenant que des commentaires"
        if not self.use_real_jpype:
            with patch.object(self.tweety_bridge, '_remove_comments_and_empty_lines', return_value=[]) as mock_remove_lines:
                is_valid, message = self.tweety_bridge.validate_fol_belief_set("", None)
            mock_remove_lines.assert_called_once_with("")
            self.mock_fol_handler_instance.parse_fol_formula.assert_not_called()
            self.assertFalse(is_valid)
            self.assertEqual(message, expected_message)
        else:
            is_valid, message = self.tweety_bridge.validate_fol_belief_set("% only comment", None)
            self.assertFalse(is_valid)
            self.assertEqual(message, expected_message)

    def test_validate_fol_belief_set_invalid(self):
        """Test de la validation d'un ensemble de croyances FOL invalide."""
        belief_set_str = "forall X: p(X); forall Y: q(Y) &" # Dernière formule invalide
        cleaned_formulas = ["forall X: p(X)", "forall Y: q(Y) &"]
        signature_str = "sort T; predicate p(T); predicate q(T);"
        error_detail = "Erreur sur q(Y) &"
        if not self.use_real_jpype:
            self.mock_fol_handler_instance.parse_fol_formula.side_effect = [MagicMock(), ValueError(error_detail)]
            with patch.object(self.tweety_bridge, '_remove_comments_and_empty_lines', return_value=cleaned_formulas) as mock_remove_lines:
                is_valid, message = self.tweety_bridge.validate_fol_belief_set(belief_set_str, signature_str)
            mock_remove_lines.assert_called_once_with(belief_set_str)
            self.assertEqual(self.mock_fol_handler_instance.parse_fol_formula.call_count, 2)
            self.assertFalse(is_valid)
            self.assertEqual(message, f"Erreur de syntaxe FOL: {error_detail}")
        else:
            is_valid, message = self.tweety_bridge.validate_fol_belief_set("forall X: p(X); forall Y: q(Y) &", "sort T; predicate p(T); predicate q(T).")
            self.assertFalse(is_valid)
            self.assertIn("syntaxe FOL", message)


    # --- Tests pour Modal Belief Set ---
    def test_validate_modal_belief_set_valid(self):
        """Test de la validation d'un ensemble de croyances modales valide."""
        belief_set_str = "[]p; <>q"
        cleaned_formulas = ["[]p", "<>q"]
        modal_logic = "S4"
        if not self.use_real_jpype:
            # La validation est maintenant entièrement déléguée au handler.
            # On configure le mock pour qu'il ne lève pas d'exception.
            self.mock_modal_handler_instance.parse_modal_belief_set.return_value = None
            
            is_valid, message = self.tweety_bridge.validate_modal_belief_set(belief_set_str, modal_logic)
            
            self.mock_modal_handler_instance.parse_modal_belief_set.assert_called_once_with(belief_set_str, modal_logic)
            self.assertTrue(is_valid)
            self.assertEqual(message, "Ensemble de croyances Modal valide")
        else:
            is_valid, message = self.tweety_bridge.validate_modal_belief_set("[]p.", modal_logic)
            self.assertTrue(is_valid, f"L'ensemble Modal devrait être valide. Message: {message}")
            self.assertEqual(message, "Ensemble de croyances Modal valide")

    def test_validate_modal_belief_set_empty(self):
        """Test de la validation d'un ensemble de croyances modales vide."""
        expected_message = "Ensemble de croyances Modal vide ou ne contenant que des commentaires"
        if not self.use_real_jpype:
            # On simule le handler qui lève une exception pour un BS invalide (vide)
            self.mock_modal_handler_instance.parse_modal_belief_set.side_effect = ValueError(expected_message)
            
            is_valid, message = self.tweety_bridge.validate_modal_belief_set("", "S4")

            self.mock_modal_handler_instance.parse_modal_belief_set.assert_called_once_with("", "S4")
            self.assertFalse(is_valid)
            self.assertIn("Erreur de syntaxe Modale", message)
            self.assertIn(expected_message, message)
        else:
            is_valid, message = self.tweety_bridge.validate_modal_belief_set("% only comment", "S4")
            self.assertFalse(is_valid)
            self.assertEqual(message, expected_message)

    def test_validate_modal_belief_set_invalid(self):
        """Test de la validation d'un ensemble de croyances modales invalide."""
        belief_set_str = "[]p; <>q &" # Dernière formule invalide
        cleaned_formulas = ["[]p", "<>q &"]
        modal_logic = "S4"
        error_detail = "Erreur sur <>q &"
        if not self.use_real_jpype:
            # Le handler lève une exception sur le BS invalide
            self.mock_modal_handler_instance.parse_modal_belief_set.side_effect = ValueError(error_detail)

            is_valid, message = self.tweety_bridge.validate_modal_belief_set(belief_set_str, modal_logic)

            self.mock_modal_handler_instance.parse_modal_belief_set.assert_called_once_with(belief_set_str, modal_logic)
            self.assertFalse(is_valid)
            self.assertEqual(message, f"Erreur de syntaxe Modale: {error_detail}")
        else:
            is_valid, message = self.tweety_bridge.validate_modal_belief_set("[]p; <>q &", modal_logic)
            self.assertFalse(is_valid)
            self.assertIn("syntaxe Modale", message)

    # --- Tests pour execute_fol_query ---
    def test_execute_fol_query_accepted(self):
        """Test de l'exécution d'une requête FOL acceptée."""
        bs = "forall X: p(X)."
        query = "p(a)."
        sig = "sort T; constant a:T; predicate p(T)."
        if not self.use_real_jpype:
            self.mock_fol_handler_instance.fol_query.return_value = True
            result, message = self.tweety_bridge.execute_fol_query(bs, query, sig)
            self.mock_fol_handler_instance.fol_query.assert_called_once_with(bs, query, sig)
            self.assertTrue(result)
            self.assertIn(f"FOL Query '{query}' is ACCEPTED (True)", message)
        else:
            result, message = self.tweety_bridge.execute_fol_query(bs, query, sig)
            self.assertTrue(result, f"FOL query should be accepted. Message: {message}")
            self.assertIn("ACCEPTED (True)", message)

    def test_execute_fol_query_rejected(self):
        """Test de l'exécution d'une requête FOL rejetée."""
        bs = "forall X: p(X)."
        query = "q(a)." # q n'est pas dans le BS
        sig = "sort T; constant a:T; predicate p(T); predicate q(T)."
        if not self.use_real_jpype:
            self.mock_fol_handler_instance.fol_query.return_value = False
            result, message = self.tweety_bridge.execute_fol_query(bs, query, sig)
            self.mock_fol_handler_instance.fol_query.assert_called_once_with(bs, query, sig)
            self.assertFalse(result)
            self.assertIn(f"FOL Query '{query}' is REJECTED (False)", message)
        else:
            result, message = self.tweety_bridge.execute_fol_query(bs, query, sig)
            self.assertFalse(result, f"FOL query should be rejected. Message: {message}")
            self.assertIn("REJECTED (False)", message)

    def test_execute_fol_query_unknown(self):
        """Test de l'exécution d'une requête FOL avec résultat inconnu."""
        bs = "exists X: p(X)."
        query = "p(a)."
        sig = "sort T; constant a:T; predicate p(T)."
        if not self.use_real_jpype:
            self.mock_fol_handler_instance.fol_query.return_value = None # Simule un résultat inconnu
            result, message = self.tweety_bridge.execute_fol_query(bs, query, sig)
            self.mock_fol_handler_instance.fol_query.assert_called_once_with(bs, query, sig)
            self.assertIsNone(result)
            self.assertIn(f"Unknown for FOL query '{query}'", message)
        else:
            # Le comportement "Unknown" dépend du vrai reasoner FOL.
            # Pour l'instant, le handler placeholder ne retourne pas None.
            self.skipTest("Le vrai FOLHandler ne retourne pas 'None' pour l'instant.")

    def test_execute_fol_query_error(self):
        """Test de l'exécution d'une requête FOL avec erreur."""
        bs_invalid = "forall X: p(X) &." # Erreur de syntaxe
        query = "p(a)."
        sig = "sort T; constant a:T; predicate p(T)."
        error_detail = "Erreur de parsing FOL dans le handler"
        if not self.use_real_jpype:
            self.mock_fol_handler_instance.fol_query.side_effect = ValueError(error_detail)
            result, message = self.tweety_bridge.execute_fol_query(bs_invalid, query, sig)
            self.mock_fol_handler_instance.fol_query.assert_called_once_with(bs_invalid, query, sig)
            self.assertIsNone(result)
            self.assertIn("FUNC_ERROR", message)
            self.assertIn(f"Error during FOL query execution via FOLHandler: {error_detail}", message)
        else:
            result, message = self.tweety_bridge.execute_fol_query(bs_invalid, query, sig)
            self.assertIsNone(result)
            self.assertIn("FUNC_ERROR", message)
            self.assertIn("syntaxe", message.lower())


    # --- Tests pour execute_modal_query ---
    def test_execute_modal_query_accepted(self):
        """Test de l'exécution d'une requête modale acceptée."""
        bs = "[]p"
        query = "p"
        logic = "S4"
        if not self.use_real_jpype:
            self.mock_modal_handler_instance.modal_query.return_value = True # Le handler mocké retourne maintenant un bool
            message = self.tweety_bridge.execute_modal_query(bs, query, logic)
            self.mock_modal_handler_instance.modal_query.assert_called_once_with(bs, query, logic, None) # None pour signature
            self.assertIn("ACCEPTED (True)", message)
        else:
            message = self.tweety_bridge.execute_modal_query(bs, query, logic)
            self.assertIn("ACCEPTED (True)", message)

    def test_execute_modal_query_rejected(self):
        """Test de l'exécution d'une requête modale rejetée."""
        bs = "[]p"
        query = "<>q" # q n'est pas dans le BS
        logic = "S4"
        if not self.use_real_jpype:
            self.mock_modal_handler_instance.modal_query.return_value = False
            message = self.tweety_bridge.execute_modal_query(bs, query, logic)
            self.mock_modal_handler_instance.modal_query.assert_called_once_with(bs, query, logic, None)
            self.assertIn("REJECTED (False)", message)
        else:
            message = self.tweety_bridge.execute_modal_query(bs, query, logic)
            self.assertIn("REJECTED (False)", message)

    def test_execute_modal_query_unknown(self):
        """Test de l'exécution d'une requête modale avec résultat inconnu."""
        bs = "<>p"
        query = "p" # Peut être vrai ou faux selon le modèle
        logic = "K"
        if not self.use_real_jpype:
            self.mock_modal_handler_instance.modal_query.return_value = None
            message = self.tweety_bridge.execute_modal_query(bs, query, logic)
            self.mock_modal_handler_instance.modal_query.assert_called_once_with(bs, query, logic, None)
            self.assertIn("Unknown for Modal query", message)
        else:
            # Le comportement "Unknown" dépend du vrai reasoner Modal.
            # Le handler placeholder actuel retourne False.
            self.skipTest("Le vrai ModalHandler ne retourne pas 'None' pour l'instant.")


    def test_execute_modal_query_error(self):
        """Test de l'exécution d'une requête modale avec erreur."""
        bs_invalid = "[]p &." # Erreur de syntaxe
        query = "p"
        logic = "S4"
        error_detail = "Erreur de parsing Modale dans le handler"
        if not self.use_real_jpype:
            self.mock_modal_handler_instance.modal_query.side_effect = ValueError(error_detail)
            message = self.tweety_bridge.execute_modal_query(bs_invalid, query, logic) # This should now work
            self.mock_modal_handler_instance.modal_query.assert_called_once_with(bs_invalid, query, logic, None)
            self.assertIn("FUNC_ERROR", message)
            self.assertIn(f"Error during Modal query execution via ModalHandler: {error_detail}", message)
        else:
            message = self.tweety_bridge.execute_modal_query(bs_invalid, query, logic)
            self.assertIn("FUNC_ERROR", message)
            self.assertIn("syntaxe", message.lower())


if __name__ == "__main__":
    unittest.main()

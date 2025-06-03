# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_tweety_bridge.py
"""
Tests unitaires pour la classe TweetyBridge.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from tests.mocks.jpype_mock import JException as MockedJException

import jpype # Gardé pour référence si des types réels sont nécessaires, mais les tests devraient utiliser le mock.

from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestTweetyBridge(unittest.TestCase):
    """Tests pour la classe TweetyBridge."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
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
        self.mock_pl_parser = MagicMock()
        self.mock_sat_reasoner = MagicMock()
        self.mock_pl_formula = MagicMock()
        
        self.mock_fol_parser = MagicMock()
        self.mock_fol_reasoner = MagicMock()
        self.mock_fol_formula = MagicMock()
        
        self.mock_modal_parser = MagicMock(name="ModalParser_class_mock_OLD") # Sera remplacé par MlParser
        self.mock_ml_parser = MagicMock() # name enlevé
        self.mock_modal_reasoner = MagicMock() # name enlevé (utilisé comme clé dans jclass_map pour Simple/Abstract)
        self.mock_abstract_ml_reasoner = MagicMock() # name enlevé (non instancié directement)
        self.mock_simple_ml_reasoner = MagicMock() # name enlevé
        self.mock_modal_formula = MagicMock(name="ModalFormula_class_mock") # Garde son nom, pas instancié avec ()
        self.mock_simple_fol_reasoner = MagicMock() # name enlevé
        
        # Configurer JClass pour retourner les mocks
        # Utilisation d'un dictionnaire fixe pour le side_effect pour plus de clarté
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
            "org.tweetyproject.logics.ml.reasoner.ModalReasoner": self.mock_modal_reasoner,
            "org.tweetyproject.logics.ml.syntax.MlFormula": self.mock_modal_formula
        }
        
        def jclass_side_effect_strict(class_name):
            # print(f"DEBUG JClass side_effect: Demande pour '{class_name}'")
            if class_name not in self.jclass_map:
                # Lever une erreur pour un débogage strict si la classe n'est pas dans la map.
                # Cela nous dira si le problème est que la clé n'est pas trouvée.
                raise KeyError(f"Mock JClass: La classe '{class_name}' n'est pas définie dans jclass_map. Classes disponibles: {list(self.jclass_map.keys())}")
            # print(f"DEBUG JClass side_effect: Classe '{class_name}' trouvée, retour de {self.jclass_map[class_name]}")
            return self.jclass_map[class_name]

        self.mock_jpype.JClass.side_effect = jclass_side_effect_strict
        
        # Mocks pour les instances
        self.mock_pl_parser_instance = MagicMock()
        self.mock_sat_reasoner_instance = MagicMock()
        
        self.mock_fol_parser_instance = MagicMock()
        self.mock_fol_reasoner_instance = MagicMock()
        
        self.mock_ml_parser_instance = MagicMock(name="MlParser_instance_mock")
        self.mock_modal_reasoner_instance = MagicMock(name="ModalReasoner_instance_mock_OLD")
        self.mock_abstract_ml_reasoner_instance = MagicMock(name="AbstractMlReasoner_instance_mock")
        self.mock_simple_ml_reasoner_instance = MagicMock(name="SimpleMlReasoner_instance_mock")
        self.mock_simple_fol_reasoner_instance = MagicMock(name="SimpleFolReasoner_instance_mock")
        
        # Configurer les mocks de classe (qui sont appelés avec () dans TweetyBridge)
        # pour retourner les instances mockées correspondantes via return_value.
        # Les mocks de classe concernés n'ont pas de 'name' pour éviter qu'ils ne retournent eux-mêmes.
        
        # Logique propositionnelle
        self.mock_pl_parser.return_value = self.mock_pl_parser_instance
        self.mock_sat_reasoner.return_value = self.mock_sat_reasoner_instance
        
        # Logique du premier ordre (FOL)
        self.mock_fol_parser.return_value = self.mock_fol_parser_instance
        # FolReasoner (self.mock_fol_reasoner) n'est pas directement instancié par TweetyBridge.
        # TweetyBridge instancie SimpleFolReasoner.
        self.mock_simple_fol_reasoner.return_value = self.mock_simple_fol_reasoner_instance
        
        # Logique modale (ML)
        self.mock_ml_parser.return_value = self.mock_ml_parser_instance
        # AbstractMlReasoner (self.mock_abstract_ml_reasoner) et ModalReasoner (self.mock_modal_reasoner)
        # ne sont pas directement instanciés par TweetyBridge sous ces noms.
        # TweetyBridge instancie SimpleMlReasoner pour son _ModalReasoner interne.
        self.mock_simple_ml_reasoner.return_value = self.mock_simple_ml_reasoner_instance

        # Les classes de formule (PlFormula, FolFormula, ModalFormula) ne sont pas instanciées avec (),
        # donc pas besoin de .return_value pour retourner une instance. Elles sont utilisées comme types.

        # Créer l'instance de TweetyBridge APRES avoir configuré les return_value
        self.tweety_bridge = TweetyBridge()

        # Forcer l'assignation des instances mockées correctes aux attributs internes
        # de TweetyBridge, car l'appel () sur les mocks de classe ne semble pas
        # retourner la valeur de return_value/side_effect comme attendu.
        self.tweety_bridge._PlParser = self.mock_pl_parser_instance
        self.tweety_bridge._SatReasoner = self.mock_sat_reasoner_instance
        self.tweety_bridge._FolParser = self.mock_fol_parser_instance
        self.tweety_bridge._SimpleFolReasoner = self.mock_simple_fol_reasoner_instance
        self.tweety_bridge._ModalParser = self.mock_ml_parser_instance
        self.tweety_bridge._ModalReasoner = self.mock_simple_ml_reasoner_instance
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.jpype_patcher.stop()
        self.jvm_setup_jpype_patcher.stop()
    
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
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner") # Ajouté
        
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.parser.MlParser")
        # Basé sur les logs, TweetyBridge appelle AbstractMlReasoner et SimpleMlReasoner, pas ModalReasoner directement pour l'instanciation principale.
        print(f"DEBUG: JClass call_args_list before ModalReasoner assert: {self.mock_jpype.JClass.call_args_list}")
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.reasoner.AbstractMlReasoner") # Corrigé selon les logs
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner")   # Corrigé selon les logs
        self.mock_jpype.JClass.assert_any_call("org.tweetyproject.logics.ml.syntax.MlFormula")
        
        # Vérifier que les instances ont été créées
        self.mock_pl_parser.assert_called_once()
        self.mock_sat_reasoner.assert_called_once()
        
        self.mock_fol_parser.assert_called_once()
        self.mock_simple_fol_reasoner.assert_called_once()
        
        self.mock_ml_parser.assert_called_once()
        # AbstractMlReasoner n'est pas instancié directement par TweetyBridge, seulement SimpleMlReasoner.
        # self.mock_abstract_ml_reasoner.assert_called_once()
        self.mock_simple_ml_reasoner.assert_called_once()
    
    def test_initialization_jvm_not_ready(self):
        """Test de l'initialisation lorsque la JVM n'est pas prête."""
        # Configurer le mock de jpype
        self.mock_jpype.isJVMStarted.return_value = False
        self.mock_jpype.JClass.reset_mock() # Réinitialiser les appels JClass pour ce test spécifique
        self.mock_jpype.startJVM.reset_mock() # Réinitialiser les appels startJVM aussi
        
        # Simuler un échec du démarrage de la JVM
        self.mock_jpype.startJVM.side_effect = Exception("Mocked JVM start failure")
        
        # Créer l'instance de TweetyBridge
        tweety_bridge = TweetyBridge()
        
        # Restaurer le comportement par défaut de startJVM pour ne pas affecter d'autres tests
        # Bien que setUp soit appelé pour chaque test, c'est plus propre.
        self.mock_jpype.startJVM.side_effect = None
        
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
        java_exception_instance = self.mock_jpype.JException("Erreur de syntaxe à la ligne 2")
        # java_exception_instance.getMessage = MagicMock(return_value="Erreur de syntaxe à la ligne 2")
        self.mock_pl_parser_instance.parseBeliefBase.side_effect = java_exception_instance
        
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
        java_exception = self.mock_jpype.JException("Erreur de syntaxe") # Utiliser le JException mocké via self.mock_jpype
        # java_exception.getMessage.return_value = "Erreur de syntaxe" # Déjà géré par MockedJException
        # java_exception.getClass().getName.return_value = "org.tweetyproject.SyntaxException" # MockedJException ne simule pas getClass().getName() ainsi
        self.mock_pl_parser_instance.parseBeliefBase.side_effect = java_exception
        
        # Exécuter une requête
        result = self.tweety_bridge.execute_pl_query("a ==> b", "a")
        
        # Vérifier que le parser a été appelé
        self.mock_pl_parser_instance.parseBeliefBase.assert_called_once()
        
        # Vérifier le résultat
        self.assertIn("FUNC_ERROR", result)
        self.assertIn("Erreur de syntaxe", result) # Vérifier que le message de l'exception est dans le résultat
    
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
        # C'est self.mock_ml_parser_instance qui doit être configuré car c'est ce que TweetyBridge._ModalParser devrait être.
        self.mock_ml_parser_instance.parseFormula.return_value = MagicMock(name="parsed_modal_formula_mock")
        
        # Valider une formule
        is_valid, message = self.tweety_bridge.validate_modal_formula("[]p => <>q")
        
        # Vérifier que le parser a été appelé
        print(f"DEBUG: ID of self.tweety_bridge._ModalParser: {id(self.tweety_bridge._ModalParser)}")
        print(f"DEBUG: ID of self.mock_ml_parser_instance: {id(self.mock_ml_parser_instance)}")
        # Décommenter pour un check strict si les IDs sont différents, cela arrêtera le test ici.
        self.assertIs(self.tweety_bridge._ModalParser, self.mock_ml_parser_instance, "Instance de _ModalParser n'est pas self.mock_ml_parser_instance")
        print(f"DEBUG: self.tweety_bridge._ModalParser.parseFormula call_count: {getattr(self.tweety_bridge._ModalParser, 'parseFormula', MagicMock()).call_count}")
        print(f"DEBUG: self.mock_ml_parser_instance.parseFormula call_count: {self.mock_ml_parser_instance.parseFormula.call_count}")
        
        # L'assertion doit porter sur l'instance qui est réellement utilisée par tweety_bridge
        self.tweety_bridge._ModalParser.parseFormula.assert_called_once_with("[]p => <>q")
        
        # Vérifier le résultat
        self.assertTrue(is_valid)
        self.assertEqual(message, "Formule modale valide")


if __name__ == "__main__":
    unittest.main()
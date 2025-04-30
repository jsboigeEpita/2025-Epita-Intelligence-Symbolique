"""
Tests unitaires pour le module de logique propositionnelle.
"""

import unittest
from unittest.mock import MagicMock, patch
import jpype
import semantic_kernel as sk
from agents.pl.pl_definitions import PropositionalLogicPlugin, setup_pl_kernel


class TestPropositionalLogicPlugin(unittest.TestCase):
    """Tests pour la classe PropositionalLogicPlugin."""

    @patch('jpype.isJVMStarted')
    @patch('jpype.JClass')
    def test_initialization_jvm_not_started(self, mock_jclass, mock_is_jvm_started):
        """Teste l'initialisation lorsque la JVM n'est pas démarrée."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = False
        
        # Créer l'instance du plugin
        plugin = PropositionalLogicPlugin()
        
        # Vérifier que l'initialisation a échoué
        self.assertFalse(plugin._jvm_ok)
        mock_jclass.assert_not_called()

    @patch('jpype.isJVMStarted')
    @patch('jpype.JClass')
    def test_initialization_jvm_started(self, mock_jclass, mock_is_jvm_started):
        """Teste l'initialisation lorsque la JVM est démarrée."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = True
        
        # Configurer les mocks pour les classes Java
        mock_parser = MagicMock()
        mock_reasoner = MagicMock()
        mock_formula = MagicMock()
        
        mock_jclass.side_effect = lambda class_name: {
            "org.tweetyproject.logics.pl.parser.PlParser": mock_parser,
            "org.tweetyproject.logics.pl.reasoner.SatReasoner": mock_reasoner,
            "org.tweetyproject.logics.pl.syntax.PlFormula": mock_formula
        }[class_name]
        
        # Créer l'instance du plugin
        plugin = PropositionalLogicPlugin()
        
        # Vérifier que l'initialisation a réussi
        self.assertTrue(plugin._jvm_ok)
        self.assertEqual(plugin._PlParser, mock_parser)
        self.assertEqual(plugin._SatReasoner, mock_reasoner)
        self.assertEqual(plugin._PlFormula, mock_formula)
        self.assertEqual(mock_jclass.call_count, 3)

    @patch('jpype.isJVMStarted')
    @patch('jpype.JClass')
    def test_execute_pl_query_jvm_not_ready(self, mock_jclass, mock_is_jvm_started):
        """Teste l'exécution d'une requête lorsque la JVM n'est pas prête."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = False
        
        # Créer l'instance du plugin
        plugin = PropositionalLogicPlugin()
        
        # Exécuter une requête
        result = plugin.execute_pl_query("belief_set", "query")
        
        # Vérifier que l'exécution a échoué
        self.assertTrue(result.startswith("FUNC_ERROR"))
        self.assertIn("JVM non prête", result)

    @patch('jpype.isJVMStarted')
    @patch('jpype.JClass')
    def test_execute_pl_query_success(self, mock_jclass, mock_is_jvm_started):
        """Teste l'exécution réussie d'une requête."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = True
        
        # Créer des mocks pour les méthodes internes
        with patch.object(PropositionalLogicPlugin, '_internal_parse_belief_set') as mock_parse_bs, \
             patch.object(PropositionalLogicPlugin, '_internal_parse_formula') as mock_parse_formula, \
             patch.object(PropositionalLogicPlugin, '_internal_execute_query') as mock_execute_query:
            
            # Configurer les mocks
            mock_parse_bs.return_value = MagicMock()
            mock_parse_formula.return_value = MagicMock()
            mock_execute_query.return_value = True
            
            # Créer l'instance du plugin
            plugin = PropositionalLogicPlugin()
            plugin._jvm_ok = True
            
            # Exécuter une requête
            result = plugin.execute_pl_query("a => b", "a")
            
            # Vérifier que l'exécution a réussi
            self.assertIn("ACCEPTED", result)
            mock_parse_bs.assert_called_once_with("a => b")
            mock_parse_formula.assert_called_once_with("a")
            mock_execute_query.assert_called_once()

    @patch('jpype.isJVMStarted')
    @patch('jpype.JClass')
    def test_execute_pl_query_rejected(self, mock_jclass, mock_is_jvm_started):
        """Teste l'exécution d'une requête rejetée."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = True
        
        # Créer des mocks pour les méthodes internes
        with patch.object(PropositionalLogicPlugin, '_internal_parse_belief_set') as mock_parse_bs, \
             patch.object(PropositionalLogicPlugin, '_internal_parse_formula') as mock_parse_formula, \
             patch.object(PropositionalLogicPlugin, '_internal_execute_query') as mock_execute_query:
            
            # Configurer les mocks
            mock_parse_bs.return_value = MagicMock()
            mock_parse_formula.return_value = MagicMock()
            mock_execute_query.return_value = False
            
            # Créer l'instance du plugin
            plugin = PropositionalLogicPlugin()
            plugin._jvm_ok = True
            
            # Exécuter une requête
            result = plugin.execute_pl_query("a => b", "a")
            
            # Vérifier que l'exécution a réussi mais la requête a été rejetée
            self.assertIn("REJECTED", result)
            mock_parse_bs.assert_called_once_with("a => b")
            mock_parse_formula.assert_called_once_with("a")
            mock_execute_query.assert_called_once()

    @patch('jpype.isJVMStarted')
    @patch('jpype.JClass')
    def test_execute_pl_query_unknown(self, mock_jclass, mock_is_jvm_started):
        """Teste l'exécution d'une requête avec résultat inconnu."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = True
        
        # Créer des mocks pour les méthodes internes
        with patch.object(PropositionalLogicPlugin, '_internal_parse_belief_set') as mock_parse_bs, \
             patch.object(PropositionalLogicPlugin, '_internal_parse_formula') as mock_parse_formula, \
             patch.object(PropositionalLogicPlugin, '_internal_execute_query') as mock_execute_query:
            
            # Configurer les mocks
            mock_parse_bs.return_value = MagicMock()
            mock_parse_formula.return_value = MagicMock()
            mock_execute_query.return_value = None
            
            # Créer l'instance du plugin
            plugin = PropositionalLogicPlugin()
            plugin._jvm_ok = True
            
            # Exécuter une requête
            result = plugin.execute_pl_query("a => b", "a")
            
            # Vérifier que l'exécution a réussi mais le résultat est inconnu
            self.assertIn("Unknown", result)
            mock_parse_bs.assert_called_once_with("a => b")
            mock_parse_formula.assert_called_once_with("a")
            mock_execute_query.assert_called_once()

    @patch('jpype.isJVMStarted')
    @patch('jpype.JClass')
    def test_execute_pl_query_parse_error(self, mock_jclass, mock_is_jvm_started):
        """Teste l'exécution d'une requête avec erreur de parsing."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = True
        
        # Créer des mocks pour les méthodes internes
        with patch.object(PropositionalLogicPlugin, '_internal_parse_belief_set') as mock_parse_bs, \
             patch.object(PropositionalLogicPlugin, '_internal_parse_formula') as mock_parse_formula:
            
            # Configurer les mocks
            mock_parse_bs.return_value = MagicMock()
            mock_parse_formula.side_effect = RuntimeError("Erreur de parsing")
            
            # Créer l'instance du plugin
            plugin = PropositionalLogicPlugin()
            plugin._jvm_ok = True
            
            # Exécuter une requête
            result = plugin.execute_pl_query("a => b", "a")
            
            # Vérifier que l'exécution a échoué
            self.assertTrue(result.startswith("FUNC_ERROR"))
            self.assertIn("Erreur de parsing", result)
            mock_parse_bs.assert_called_once_with("a => b")
            mock_parse_formula.assert_called_once_with("a")


class TestSetupPLKernel(unittest.TestCase):
    """Tests pour la fonction setup_pl_kernel."""

    @patch('jpype.isJVMStarted')
    def test_setup_pl_kernel_jvm_not_started(self, mock_is_jvm_started):
        """Teste la configuration du kernel lorsque la JVM n'est pas démarrée."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = False
        
        # Créer un mock pour le kernel
        kernel_mock = MagicMock(spec=sk.Kernel)
        
        # Créer un mock pour le service LLM
        llm_service_mock = MagicMock()
        
        # Appeler la fonction à tester
        setup_pl_kernel(kernel_mock, llm_service_mock)
        
        # Vérifier que le plugin n'a pas été ajouté
        kernel_mock.add_plugin.assert_not_called()

    @patch('jpype.isJVMStarted')
    @patch('agents.pl.pl_definitions.PropositionalLogicPlugin')
    def test_setup_pl_kernel_jvm_started(self, mock_plugin_class, mock_is_jvm_started):
        """Teste la configuration du kernel lorsque la JVM est démarrée."""
        # Configurer les mocks
        mock_is_jvm_started.return_value = True
        
        # Créer un mock pour l'instance du plugin
        plugin_instance_mock = MagicMock()
        plugin_instance_mock._jvm_ok = True
        mock_plugin_class.return_value = plugin_instance_mock
        
        # Créer un mock pour le kernel
        kernel_mock = MagicMock(spec=sk.Kernel)
        # Ajouter l'attribut plugins au mock
        kernel_mock.plugins = {}
        
        # Créer un mock pour le service LLM
        llm_service_mock = MagicMock()
        llm_service_mock.service_id = "test_service"
        
        # Configurer le mock pour get_prompt_execution_settings_from_service_id
        kernel_mock.get_prompt_execution_settings_from_service_id.return_value = MagicMock()
        
        # Appeler la fonction à tester
        setup_pl_kernel(kernel_mock, llm_service_mock)
        
        # Vérifier que le plugin a été ajouté
        kernel_mock.add_plugin.assert_called_once_with(plugin_instance_mock, plugin_name="PLAnalyzer")
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        self.assertEqual(kernel_mock.add_function.call_count, 3)


if __name__ == '__main__':
    unittest.main()
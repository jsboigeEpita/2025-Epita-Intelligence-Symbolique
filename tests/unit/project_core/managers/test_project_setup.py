import unittest
from unittest.mock import patch, MagicMock

from project_core.core_from_scripts.project_setup import ProjectSetup
from project_core.core_from_scripts.common_utils import Logger

class TestProjectSetup(unittest.TestCase):

    def setUp(self):
        """Met en place un logger mocké avant chaque test."""
        self.mock_logger = MagicMock(spec=Logger)

    @patch('project_core.core_from_scripts.project_setup.ValidationEngine')
    @patch('project_core.core_from_scripts.project_setup.EnvironmentManager')
    def test_install_project_success(self, MockEnvironmentManager, MockValidationEngine):
        """
        Teste le cas nominal de install_project où toutes les étapes réussissent.
        """
        # Configuration des mocks
        # Le validateur retourne un succès pour les outils de build
        mock_validator_instance = MockValidationEngine.return_value
        mock_validator_instance.validate_build_tools.return_value = {'status': 'success', 'message': 'OK'}
        
        # Le gestionnaire d'environnement retourne un succès pour l'installation des dépendances
        mock_env_manager_instance = MockEnvironmentManager.return_value
        mock_env_manager_instance.fix_dependencies.return_value = True

        # Création de l'instance de ProjectSetup
        setup = ProjectSetup(logger=self.mock_logger)

        # Mock de la méthode set_project_path_file directement sur l'instance
        with patch.object(setup, 'set_project_path_file', return_value=True) as mock_set_path:
            # Appel de la méthode à tester
            result = setup.install_project()

            # Assertions
            self.assertTrue(result, "La méthode install_project aurait dû retourner True.")
            
            # Vérifier que les méthodes ont été appelées
            mock_validator_instance.validate_build_tools.assert_called_once()
            mock_env_manager_instance.fix_dependencies.assert_called_once_with(
                requirements_file="requirements.txt", 
                strategy='aggressive'
            )
            mock_set_path.assert_called_once()

            # Vérifier les logs de succès
            self.mock_logger.success.assert_any_call("Outils de compilation validés.")
            self.mock_logger.success.assert_any_call("Dépendances installées avec succès.")
            self.mock_logger.success.assert_any_call("PYTHONPATH configuré avec succès.")
            self.mock_logger.success.assert_any_call("Installation complète du projet terminée avec succès!")

    @patch('project_core.core_from_scripts.project_setup.ValidationEngine')
    @patch('project_core.core_from_scripts.project_setup.EnvironmentManager')
    def test_install_project_failure_on_build_tools(self, MockEnvironmentManager, MockValidationEngine):
        """
        Teste le cas où l'installation échoue à cause de la validation des outils de compilation.
        """
        # Configuration des mocks
        # Le validateur retourne un échec
        mock_validator_instance = MockValidationEngine.return_value
        mock_validator_instance.validate_build_tools.return_value = {'status': 'failure', 'message': 'Build tools not found'}

        mock_env_manager_instance = MockEnvironmentManager.return_value

        # Création de l'instance
        setup = ProjectSetup(logger=self.mock_logger)
        
        with patch.object(setup, 'set_project_path_file') as mock_set_path:
            # Appel de la méthode
            result = setup.install_project()

            # Assertions
            self.assertFalse(result, "La méthode install_project aurait dû retourner False.")

            # Vérifier que seule la validation a été tentée
            mock_validator_instance.validate_build_tools.assert_called_once()
            
            # Vérifier que les étapes suivantes n'ont PAS été appelées
            mock_env_manager_instance.fix_dependencies.assert_not_called()
            mock_set_path.assert_not_called()

            # Vérifier le log d'erreur
            self.mock_logger.error.assert_called_with("Installation annulée. Veuillez installer les outils de compilation requis et réessayer.")

if __name__ == '__main__':
    unittest.main()
    @patch('project_core.core_from_scripts.project_setup.EnvironmentManager')
    def test_setup_test_environment_without_mocks(self, MockEnvironmentManager):
        """
        Teste que setup_test_environment réussit sans activer les mocks.
        """
        # Configuration
        mock_env_manager_instance = MockEnvironmentManager.return_value
        setup = ProjectSetup(logger=self.mock_logger)

        # Appel
        result = setup.setup_test_environment(with_mocks=False)

        # Assertions
        self.assertTrue(result)
        self.mock_logger.info.assert_any_call("Configuration de l'environnement de test...")
        # Vérifie que la logique de mock n'est PAS appelée
        self.assertNotIn("Activation des mocks", [call[0][0] for call in self.mock_logger.info.call_args_list])
        self.mock_logger.success.assert_called_with("Environnement de test prêt.")

    @patch('project_core.core_from_scripts.project_setup.EnvironmentManager')
    def test_setup_test_environment_with_mocks(self, MockEnvironmentManager):
        """
        Teste que setup_test_environment réussit et active les mocks.
        """
        # Configuration
        mock_env_manager_instance = MockEnvironmentManager.return_value
        setup = ProjectSetup(logger=self.mock_logger)

        # Appel
        result = setup.setup_test_environment(with_mocks=True)

        # Assertions
        self.assertTrue(result)
        self.mock_logger.info.assert_any_call("Configuration de l'environnement de test...")
        self.mock_logger.info.assert_any_call("Activation des mocks pour l'environnement de test...")
        self.mock_logger.info.assert_any_call("Mocks activés.")
        self.mock_logger.success.assert_called_with("Environnement de test prêt.")
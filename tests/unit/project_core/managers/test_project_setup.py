import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from project_core.core_from_scripts.project_setup import ProjectSetup
from project_core.core_from_scripts.common_utils import Logger


class TestProjectSetup(unittest.TestCase):
    def setUp(self):
        """Met en place un logger mocké avant chaque test."""
        self.mock_logger = MagicMock(spec=Logger)

    @patch(
        "project_core.core_from_scripts.project_setup.ProjectSetup._setup_test_environment"
    )
    @patch(
        "project_core.core_from_scripts.project_setup.ProjectSetup._setup_development_environment"
    )
    @patch("project_core.core_from_scripts.project_setup.ValidationEngine")
    @patch("project_core.core_from_scripts.project_setup.EnvironmentManager")
    def test_setup_environment_routes_to_dev(
        self,
        MockEnvironmentManager,
        MockValidationEngine,
        mock_dev_setup,
        mock_test_setup,
    ):
        """Vérifie que setup_environment('dev') appelle la bonne méthode."""
        MockEnvironmentManager.return_value.project_root = Path("/fake/dir")
        # We also need to mock the ValidationEngine to prevent it from creating a real EnvironmentManager
        mock_validator_instance = MockValidationEngine.return_value
        setup = ProjectSetup(logger=self.mock_logger)
        setup.setup_environment(env_name="dev")
        mock_dev_setup.assert_called_once()
        mock_test_setup.assert_not_called()

    @patch(
        "project_core.core_from_scripts.project_setup.ProjectSetup._setup_test_environment"
    )
    @patch(
        "project_core.core_from_scripts.project_setup.ProjectSetup._setup_development_environment"
    )
    @patch("project_core.core_from_scripts.project_setup.ValidationEngine")
    @patch("project_core.core_from_scripts.project_setup.EnvironmentManager")
    def test_setup_environment_routes_to_test(
        self,
        MockEnvironmentManager,
        MockValidationEngine,
        mock_dev_setup,
        mock_test_setup,
    ):
        """Vérifie que setup_environment('test') appelle la bonne méthode."""
        MockEnvironmentManager.return_value.project_root = Path("/fake/dir")
        mock_validator_instance = MockValidationEngine.return_value
        setup = ProjectSetup(logger=self.mock_logger)
        setup.setup_environment(env_name="test", with_mocks=True)
        mock_dev_setup.assert_not_called()
        mock_test_setup.assert_called_once_with(with_mocks=True)

    @patch("project_core.core_from_scripts.project_setup.ValidationEngine")
    @patch("project_core.core_from_scripts.project_setup.EnvironmentManager")
    def test_setup_environment_handles_invalid_name(
        self, MockEnvironmentManager, MockValidationEngine
    ):
        """Vérifie qu'un nom d'environnement invalide est correctement géré."""
        MockEnvironmentManager.return_value.project_root = Path("/fake/dir")
        mock_validator_instance = MockValidationEngine.return_value
        setup = ProjectSetup(logger=self.mock_logger)
        result = setup.setup_environment(env_name="invalid_env")
        self.assertFalse(result)
        self.mock_logger.error.assert_called_with(
            "Nom d'environnement non reconnu : 'invalid_env'. Les choix valides sont 'test', 'dev'."
        )

    @patch("project_core.core_from_scripts.project_setup.ValidationEngine")
    @patch("project_core.core_from_scripts.project_setup.EnvironmentManager")
    @patch(
        "project_core.core_from_scripts.project_setup.ProjectSetup.download_test_jars"
    )
    def test_setup_test_environment_orchestration(
        self, mock_download_jars, MockEnvironmentManager, MockValidationEngine
    ):
        """Teste l'orchestration de _setup_test_environment."""
        MockEnvironmentManager.return_value.project_root = Path("/fake/dir")
        mock_validator_instance = MockValidationEngine.return_value
        mock_download_jars.return_value = True
        setup = ProjectSetup(logger=self.mock_logger)

        result = setup._setup_test_environment(with_mocks=True)

        self.assertTrue(result)
        mock_download_jars.assert_called_once()
        self.mock_logger.info.assert_any_call(
            "Activation des mocks pour l'environnement de test..."
        )
        self.mock_logger.success.assert_called_with(
            "Environnement de test configuré avec succès."
        )

    @patch("pathlib.Path.home", return_value=Path("/fake/home"))
    @patch("project_core.core_from_scripts.project_setup.ValidationEngine")
    @patch("project_core.core_from_scripts.project_setup.EnvironmentManager")
    def test_install_project_success(
        self, MockEnvironmentManager, MockValidationEngine, mock_home
    ):
        """Teste le cas nominal de install_project où toutes les étapes réussissent."""
        # Note: 'from pathlib import Path' is already at the top of the file

        mock_validator_instance = MockValidationEngine.return_value
        mock_validator_instance.validate_build_tools.return_value = {
            "status": "success",
            "message": "OK",
        }

        # Configure the mock instance *that will be returned* when EnvironmentManager() is called
        mock_env_manager_instance = MockEnvironmentManager.return_value
        mock_env_manager_instance.project_root = Path("/fake/project/root")
        mock_env_manager_instance.fix_dependencies.return_value = True

        # Now, instantiate ProjectSetup. Its __init__ will use the pre-configured mock.
        setup = ProjectSetup(logger=self.mock_logger)

        with patch.object(
            setup, "set_project_path_file", return_value=True
        ) as mock_set_path:
            result = setup.install_project()

            self.assertTrue(result)
            mock_validator_instance.validate_build_tools.assert_called_once()
            mock_env_manager_instance.fix_dependencies.assert_called_once_with(
                requirements_file="requirements.txt", strategy_name="aggressive"
            )
            mock_set_path.assert_called_once()
            self.mock_logger.success.assert_any_call(
                "Installation complète du projet terminée avec succès!"
            )

    @patch("project_core.core_from_scripts.project_setup.EnvironmentManager")
    @patch("project_core.core_from_scripts.project_setup.ValidationEngine")
    def test_install_project_failure_on_build_tools(
        self, MockValidationEngine, MockEnvironmentManager
    ):
        """Teste le cas où l'installation échoue à cause des outils de compilation."""
        mock_validator_instance = MockValidationEngine.return_value
        mock_validator_instance.validate_build_tools.return_value = {
            "status": "failure",
            "message": "Build tools not found",
        }

        # Configure the mock to prevent TypeError, even if it's not directly used for assertions
        mock_env_manager_instance = MockEnvironmentManager.return_value
        mock_env_manager_instance.project_root = Path("/fake/project/root")

        setup = ProjectSetup(logger=self.mock_logger)
        result = setup.install_project()

        self.assertFalse(result)
        mock_validator_instance.validate_build_tools.assert_called_once()
        self.mock_logger.error.assert_called_with(
            "Installation annulée. Veuillez installer les outils de compilation requis et réessayer."
        )


if __name__ == "__main__":
    unittest.main()

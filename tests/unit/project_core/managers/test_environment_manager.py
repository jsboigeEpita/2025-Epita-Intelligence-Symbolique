import unittest
from unittest.mock import patch

from project_core.managers.environment_manager import EnvironmentManager


class TestEnvironmentManager(unittest.TestCase):
    """Unit tests for the EnvironmentManager."""

    @patch('project_core.managers.environment_manager.load_dotenv')
    def test_init_loads_dotenv(self, mock_load_dotenv):
        """Test that __init__ calls load_dotenv."""
        EnvironmentManager()
        mock_load_dotenv.assert_called_once()

    @patch('os.getenv')
    @patch('project_core.managers.environment_manager.load_dotenv')
    def test_get_variable_success(self, mock_load_dotenv, mock_getenv):
        """Test retrieving an existing environment variable."""
        # Arrange
        mock_getenv.return_value = 'my_test_value'
        env_manager = EnvironmentManager()

        # Act
        value = env_manager.get_variable('MY_VAR')

        # Assert
        mock_getenv.assert_called_once_with('MY_VAR', None)
        self.assertEqual(value, 'my_test_value')

    @patch('os.getenv')
    @patch('project_core.managers.environment_manager.load_dotenv')
    def test_get_variable_with_default(self, mock_load_dotenv, mock_getenv):
        """Test get_variable returns default value when variable is not set."""
        # Arrange
        # This simulates os.getenv returning the default value when the key is not found.
        mock_getenv.return_value = 'default_value'
        env_manager = EnvironmentManager()

        # Act
        value = env_manager.get_variable('NON_EXISTENT_VAR', 'default_value')

        # Assert
        mock_getenv.assert_called_once_with('NON_EXISTENT_VAR', 'default_value')
        self.assertEqual(value, 'default_value')
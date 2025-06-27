import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os

from project_core.core_from_scripts.environment_manager import EnvironmentManager

class TestEnvironmentManager(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.mock_logger = MagicMock()
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.manager = EnvironmentManager(project_root=self.project_root, logger_instance=self.mock_logger)

    @patch('pathlib.Path.is_file', return_value=True)
    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env', return_value=0)
    def test_fix_dependencies_from_requirements_file(self, mock_run_command, mock_is_file):
        """Test dependency fixing from a requirements file."""
        requirements_path = "requirements-test.txt"
        
        result = self.manager.fix_dependencies(requirements_file=requirements_path)

        self.assertTrue(result)
        mock_is_file.assert_called_with()
        mock_run_command.assert_called_once_with(f"pip install -r {requirements_path}")


    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env', return_value=0)
    def test_fix_dependencies_with_packages(self, mock_run_command):
        """Test dependency fixing with a list of packages."""
        packages_to_fix = ["numpy", "pandas"]

        result = self.manager.fix_dependencies(packages=packages_to_fix)
        
        self.assertTrue(result)
        expected_command = "pip install --force-reinstall --no-cache-dir numpy pandas"
        mock_run_command.assert_called_once_with(expected_command)

    def test_fix_dependencies_mutually_exclusive_args(self):
        """Test that providing both packages and requirements_file raises an error."""
        with self.assertRaises(ValueError):
            self.manager.fix_dependencies(packages=["numpy"], requirements_file="req.txt")


if __name__ == '__main__':
    unittest.main()
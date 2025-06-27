import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import sys

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

    @patch('pathlib.Path.is_file', return_value=True)
    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env', return_value=0)
    def test_fix_dependencies_for_subproject(self, mock_run_command, mock_is_file):
        """Test dependency fixing for a subproject like abs_arg_dung."""
        requirements_path = "abs_arg_dung/requirements.txt"
        
        result = self.manager.fix_dependencies(requirements_file=requirements_path)

        self.assertTrue(result)
        mock_is_file.assert_called_with()
        expected_command = f"pip install -r {requirements_path}"
        mock_run_command.assert_called_once_with(expected_command)

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env')
    def test_fix_dependencies_aggressive_strategy_success_on_first_try(self, mock_run_command):
        """Test the aggressive strategy succeeds on the first attempt."""
        mock_run_command.return_value = 0  # Success on the first call
        
        result = self.manager.fix_dependencies(packages=["JPype1"], strategy='aggressive')
        
        self.assertTrue(result)
        mock_run_command.assert_called_once_with('pip install "JPype1"')

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env')
    def test_fix_dependencies_aggressive_strategy_success_on_second_try(self, mock_run_command):
        """Test the aggressive strategy succeeds on the second attempt (no binary)."""
        mock_run_command.side_effect = [1, 0]  # Fail first, succeed second
        
        result = self.manager.fix_dependencies(packages=["JPype1"], strategy='aggressive')
        
        self.assertTrue(result)
        self.assertEqual(mock_run_command.call_count, 2)
        mock_run_command.assert_any_call('pip install "JPype1"')
        mock_run_command.assert_any_call('pip install --no-binary :all: "JPype1"')

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager._find_vcvarsall', return_value=None)
    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env')
    def test_fix_dependencies_aggressive_strategy_all_fail(self, mock_run_command, mock_find_vcvars):
        """Test the aggressive strategy when all attempts fail."""
        mock_run_command.return_value = 1  # All pip commands fail
        
        result = self.manager.fix_dependencies(packages=["acme"], strategy='aggressive')
        
        self.assertFalse(result)
        self.assertEqual(mock_run_command.call_count, 2) # It will try the two pip strategies
        if sys.platform == 'win32':
             mock_find_vcvars.assert_called_once()


if __name__ == '__main__':
    unittest.main()
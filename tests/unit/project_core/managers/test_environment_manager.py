import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
from project_core.core_from_scripts.strategies.base_strategy import BaseStrategy
import sys
from collections import namedtuple

from project_core.core_from_scripts.environment_manager import EnvironmentManager

class TestEnvironmentManager(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.mock_logger = MagicMock()
        # Mock the project_root to isolate from the filesystem and control path operations
        self.mock_project_root = MagicMock(spec=Path)
        
        # We patch __init__ to avoid the automatic (and real) loading of strategies
        with patch.object(EnvironmentManager, '_load_strategies'):
            # self.manager will now have a mocked project_root
            self.manager = EnvironmentManager(project_root=self.mock_project_root, logger_instance=self.mock_logger)
            
            # We manually set the strategies to control them in tests
            self.manager._strategies = {
                'default': MagicMock(spec=BaseStrategy, name='default'),
                'simple': MagicMock(spec=BaseStrategy, name='simple'),
                'no-binary': MagicMock(spec=BaseStrategy, name='no-binary'),
                'wheel-install': MagicMock(spec=BaseStrategy, name='wheel-install'),
                'msvc-build': MagicMock(spec=BaseStrategy, name='msvc-build')
            }

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env', return_value=0)
    def test_fix_dependencies_from_requirements_file(self, mock_run_command):
        """Test dependency fixing from a requirements file."""
        # Configure the mocked project_root to handle the '/' operator and subsequent `is_file` call.
        self.mock_project_root.__truediv__.return_value.is_file.return_value = True

        requirements_path = "requirements-test.txt"
        result = self.manager.fix_dependencies(requirements_file=requirements_path)

        self.assertTrue(result, "fix_dependencies should return True on success")
        self.mock_project_root.__truediv__.return_value.is_file.assert_called_once()
        mock_run_command.assert_called_once_with(f"pip install -r {requirements_path}")

    def test_fix_dependencies_with_packages(self):
        """Test dependency fixing with a list of packages using the default strategy."""
        packages_to_fix = ["numpy", "pandas"]
        
        # Configure the mock for the default strategy
        self.manager._strategies['default'].execute.return_value = True

        result = self.manager.fix_dependencies(packages=packages_to_fix, strategy_name='default')
        
        self.assertTrue(result)
        # Check that the 'default' strategy was called for each package
        self.assertEqual(self.manager._strategies['default'].execute.call_count, 2)
        self.manager._strategies['default'].execute.assert_any_call("numpy")
        self.manager._strategies['default'].execute.assert_any_call("pandas")

    def test_fix_dependencies_mutually_exclusive_args(self):
        """Test that providing both packages and requirements_file raises an error."""
        with self.assertRaises(ValueError):
            self.manager.fix_dependencies(packages=["numpy"], requirements_file="req.txt")

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager.run_command_in_conda_env', return_value=0)
    def test_fix_dependencies_for_subproject(self, mock_run_command):
        """Test dependency fixing for a subproject like abs_arg_dung."""
        # Configure the mocked project_root to handle the '/' operator and subsequent `is_file` call.
        self.mock_project_root.__truediv__.return_value.is_file.return_value = True
        
        requirements_path = "abs_arg_dung/requirements.txt"
        result = self.manager.fix_dependencies(requirements_file=requirements_path)

        self.assertTrue(result, "fix_dependencies should return True on success")
        
        # Verify that the is_file check was performed on the object resulting from the path operation
        self.mock_project_root.__truediv__.return_value.is_file.assert_called_once()
        
        # Verify the correct command was run
        expected_command = f"pip install -r {requirements_path}"
        mock_run_command.assert_called_once_with(expected_command)

    def test_fix_dependencies_aggressive_strategy_success_on_first_try(self):
        """Test the aggressive strategy succeeds on the first attempt."""
        self.manager._strategies['simple'].execute.return_value = True

        result = self.manager.fix_dependencies(packages=["JPype1"], strategy_name='aggressive')
        
        self.assertTrue(result)
        self.manager._strategies['simple'].execute.assert_called_once_with('JPype1')
        self.manager._strategies['no-binary'].execute.assert_not_called()

    def test_fix_dependencies_aggressive_strategy_success_on_second_try(self):
        """Test the aggressive strategy succeeds on the second attempt (no binary)."""
        self.manager._strategies['simple'].execute.return_value = False
        self.manager._strategies['no-binary'].execute.return_value = True
        
        result = self.manager.fix_dependencies(packages=["JPype1"], strategy_name='aggressive')
        
        self.assertTrue(result)
        self.manager._strategies['simple'].execute.assert_called_once_with('JPype1')
        self.manager._strategies['no-binary'].execute.assert_called_once_with('JPype1')
        self.manager._strategies['wheel-install'].execute.assert_not_called()

    def test_fix_dependencies_aggressive_strategy_all_fail(self):
        """Test the aggressive strategy when all attempts fail."""
        for strategy in self.manager._strategies.values():
            strategy.execute.return_value = False
            
        result = self.manager.fix_dependencies(packages=["acme"], strategy_name='aggressive')
            
        self.assertFalse(result)
        self.manager._strategies['simple'].execute.assert_called_once_with('acme')
        self.manager._strategies['no-binary'].execute.assert_called_once_with('acme')
        self.manager._strategies['wheel-install'].execute.assert_called_once_with('acme')
        if sys.platform == 'win32':
            self.manager._strategies['msvc-build'].execute.assert_called_once_with('acme')

    def test_fix_dependencies_aggressive_strategy_success_on_wheel(self):
        """Test the aggressive strategy succeeding with the precompiled wheel."""
        self.manager._strategies['simple'].execute.return_value = False
        self.manager._strategies['no-binary'].execute.return_value = False
        self.manager._strategies['wheel-install'].execute.return_value = True
        
        result = self.manager.fix_dependencies(packages=["JPype1"], strategy_name='aggressive')
        
        self.assertTrue(result)
        self.manager._strategies['simple'].execute.assert_called_once_with('JPype1')
        self.manager._strategies['no-binary'].execute.assert_called_once_with('JPype1')
        self.manager._strategies['wheel-install'].execute.assert_called_once_with('JPype1')
        self.manager._strategies['msvc-build'].execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
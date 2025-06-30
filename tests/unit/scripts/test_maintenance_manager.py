# -*- coding: utf-8 -*-
"""
Tests for the Maintenance Manager CLI.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

from scripts.maintenance_manager import main

class TestMaintenanceManager(unittest.TestCase):
    """
    Test suite for the command-line interface of the maintenance manager.
    """

    @patch('scripts.maintenance_manager.EnvironmentManager')
    def test_env_validate_command(self, mock_environment_manager):
        """
        Tests that the 'env --validate' command correctly instantiates
        and runs the EnvironmentManager's validation method.
        """
        # Configure the mock
        mock_instance = mock_environment_manager.return_value
        mock_instance.validate_environment.return_value = True
        
        # Run the command
        with patch.object(sys, 'argv', ['maintenance_manager.py', 'env', '--validate', 'test_env']):
            main()
        
        # Assert that the manager was instantiated and validate_environment was called
        mock_environment_manager.assert_called_once()
        mock_instance.validate_environment.assert_called_once_with('test_env')
        
if __name__ == '__main__':
    unittest.main()
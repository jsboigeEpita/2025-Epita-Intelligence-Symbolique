# -*- coding: utf-8 -*-
"""
Tests for the Maintenance Manager CLI.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Adjust the path to import maintenance_manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../scripts')))

from maintenance_manager import main

class TestMaintenanceManager(unittest.TestCase):
    """
    Test suite for the command-line interface of the maintenance manager.
    """

    @patch('maintenance_manager.ValidationEngine')
    def test_project_validate_command(self, mock_validation_engine):
        """
        Tests that the 'project --validate' command correctly instantiates
        and runs the ValidationEngine.
        """
        # Configure the mock
        mock_instance = mock_validation_engine.return_value
        mock_instance.run.return_value = [
            MagicMock(success=True, rule_name='TestRule', message='Test success')
        ]
        
        # Run the command
        with patch.object(sys, 'argv', ['maintenance_manager.py', 'project', '--validate']):
            main()
        
        # Assert that the engine was instantiated, rules loaded, and run
        mock_validation_engine.assert_called_once()
        mock_instance.load_rules.assert_called_once()
        mock_instance.run.assert_called_once()
        
if __name__ == '__main__':
    unittest.main()
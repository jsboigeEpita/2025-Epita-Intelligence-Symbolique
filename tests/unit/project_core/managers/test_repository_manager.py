# -*- coding: utf-8 -*-
"""
Unit tests for the RepositoryManager class.
"""

import unittest
from unittest.mock import patch
from project_core.managers.repository_manager import RepositoryManager

class TestRepositoryManager(unittest.TestCase):
    """
    Test suite for the RepositoryManager class.
    """

    @patch('project_core.managers.repository_manager.run_shell_command')
    def test_find_untracked_files(self, mock_run_shell_command):
        """
        Test that find_untracked_files correctly parses the output of 'git status'.
        """
        # Arrange
        mock_output = (
            "M  file1.py\n"
            "A  file2.py\n"
            "?? new_file.txt\n"
            "?? another/new_file.log\n"
        )
        mock_run_shell_command.return_value = (0, mock_output, "")

        # Act
        untracked_files = RepositoryManager.find_untracked_files()

        # Assert
        expected_files = ['new_file.txt', 'another/new_file.log']
        self.assertEqual(untracked_files, expected_files)
        
        # Verify that the mocked function was called correctly
        command = ['git', 'status', '--porcelain']
        mock_run_shell_command.assert_called_once_with(
            command,
            description="Checking for untracked files"
        )

    @patch('project_core.managers.repository_manager.run_shell_command')
    def test_find_untracked_files_no_untracked(self, mock_run_shell_command):
        """
        Test find_untracked_files when there are no untracked files.
        """
        # Arrange
        mock_output = (
            "M  file1.py\n"
            "A  file2.py\n"
        )
        mock_run_shell_command.return_value = (0, mock_output, "")

        # Act
        untracked_files = RepositoryManager.find_untracked_files()

        # Assert
        self.assertEqual(untracked_files, [])

    @patch('project_core.managers.repository_manager.run_shell_command')
    def test_find_untracked_files_empty_status(self, mock_run_shell_command):
        """
        Test find_untracked_files with empty output from git status.
        """
        # Arrange
        mock_run_shell_command.return_value = (0, "", "")

        # Act
        untracked_files = RepositoryManager.find_untracked_files()

        # Assert
        self.assertEqual(untracked_files, [])

    @patch('project_core.managers.repository_manager.run_shell_command')
    def test_find_untracked_files_command_error(self, mock_run_shell_command):
        """
        Test find_untracked_files when the git command fails.
        """
        # Arrange
        mock_run_shell_command.return_value = (1, "", "git error")

        # Act
        untracked_files = RepositoryManager.find_untracked_files()

        # Assert
        self.assertEqual(untracked_files, [])

if __name__ == '__main__':
    unittest.main()
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
from project_core.managers.repository_manager import RepositoryManager

class TestRepositoryManager(unittest.TestCase):
    """
    Unit tests for the RepositoryManager class.
    """

    @patch('project_core.managers.repository_manager.run_shell_command')
    def test_find_untracked_files_with_untracked_files(self, mock_run_shell_command):
        """
        Test that find_untracked_files correctly identifies untracked files.
        """
        # Arrange
        git_output = "?? file1.py\n?? another/dir/file2.txt"
        mock_run_shell_command.return_value = (0, git_output, "")
        
        # Act
        untracked_files = RepositoryManager.find_untracked_files()
        
        # Assert
        self.assertEqual(len(untracked_files), 2)
        self.assertIn("file1.py", untracked_files)
        self.assertIn("another/dir/file2.txt", untracked_files)
        mock_run_shell_command.assert_called_once_with(
            ['git', 'status', '--porcelain'],
            description="Checking for untracked files"
        )

    @patch('project_core.managers.repository_manager.run_shell_command')
    def test_find_untracked_files_with_no_untracked_files(self, mock_run_shell_command):
        """
        Test that find_untracked_files returns an empty list when there are no untracked files.
        """
        # Arrange
        git_output = " M modified_file.py"
        mock_run_shell_command.return_value = (0, git_output, "")
        
        # Act
        untracked_files = RepositoryManager.find_untracked_files()
        
        # Assert
        self.assertEqual(len(untracked_files), 0)
        mock_run_shell_command.assert_called_once()

    @patch('project_core.managers.repository_manager.run_shell_command')
    def test_find_untracked_files_with_git_error(self, mock_run_shell_command):
        """
        Test that find_untracked_files returns an empty list when git command fails.
        """
        # Arrange
        mock_run_shell_command.return_value = (1, "", "git error")
        
        # Act
        untracked_files = RepositoryManager.find_untracked_files()
        
        # Assert
        self.assertEqual(len(untracked_files), 0)
        mock_run_shell_command.assert_called_once()

if __name__ == '__main__':
    unittest.main()
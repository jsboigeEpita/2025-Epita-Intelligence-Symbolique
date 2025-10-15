# -*- coding: utf-8 -*-
import os
import unittest
from unittest.mock import patch, mock_open
from project_core.core_from_scripts.repository_manager import RepositoryManager


class TestRepositoryManager(unittest.TestCase):
    def setUp(self):
        self.manager = RepositoryManager()
        self.project_root = "/fake/project"
        self.template_path = os.path.join(
            self.project_root, "project_core/templates/project.gitignore.template"
        )
        self.gitignore_path = os.path.join(self.project_root, ".gitignore")

    def test_update_gitignore_from_template_no_existing_gitignore(self):
        template_content = "__pycache__/\nresults/\n"

        with patch("os.path.exists", return_value=False), patch(
            "builtins.open", mock_open(read_data=template_content)
        ) as mock_file:
            added_rules = self.manager.update_gitignore_from_template(
                self.project_root, self.template_path
            )

            self.assertEqual(sorted(["__pycache__/", "results/"]), sorted(added_rules))

            # Check write calls
            mock_file.assert_any_call(self.template_path, "r", encoding="utf-8")
            mock_file.assert_any_call(self.gitignore_path, "a", encoding="utf-8")

            handle = mock_file()
            handle.write.assert_any_call("\n# Managed by Project Core\n")
            handle.write.assert_any_call("__pycache__/\n")
            handle.write.assert_any_call("results/\n")

    def test_update_gitignore_from_template_with_existing_gitignore(self):
        template_content = "__pycache__/\nresults/\n.vscode/\n"
        gitignore_content = "__pycache__/\n"

        mock_files = {
            self.template_path: mock_open(read_data=template_content).return_value,
            self.gitignore_path: mock_open(read_data=gitignore_content).return_value,
        }

        def open_side_effect(path, *args, **kwargs):
            if path in mock_files:
                return mock_files[path]
            return mock_open(read_data="").return_value

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=open_side_effect
        ) as mock_open_func:
            added_rules = self.manager.update_gitignore_from_template(
                self.project_root, self.template_path
            )

            self.assertEqual(sorted([".vscode/", "results/"]), sorted(added_rules))

            # Get the mock for the .gitignore file to check the write calls
            gitignore_handle = mock_files[self.gitignore_path]
            gitignore_handle.write.assert_any_call("\n# Managed by Project Core\n")
            gitignore_handle.write.assert_any_call("results/\n")
            gitignore_handle.write.assert_any_call(".vscode/\n")

    def test_update_gitignore_from_template_no_new_rules(self):
        template_content = "__pycache__/\nresults/\n"
        gitignore_content = "__pycache__/\nresults/\n# some comment\n"

        # This mock will handle the multiple file reads
        mock_files = {
            self.template_path: mock_open(read_data=template_content).return_value,
            self.gitignore_path: mock_open(read_data=gitignore_content).return_value,
        }

        def open_side_effect(path, *args, **kwargs):
            if path in mock_files:
                return mock_files[path]
            # Fallback for any other calls to open
            return mock_open(read_data="").return_value

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=open_side_effect
        ) as mock_open_func:
            added_rules = self.manager.update_gitignore_from_template(
                self.project_root, self.template_path
            )

            self.assertEqual([], added_rules)

            # Check that open was not called in 'a' (append) mode
            was_write_called = any(
                "a" in call.args for call in mock_open_func.mock_calls if call[0] == ""
            )
            self.assertFalse(
                was_write_called,
                "open() should not be called in append mode if there are no new rules.",
            )


if __name__ == "__main__":
    unittest.main()

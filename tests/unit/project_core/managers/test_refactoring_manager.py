# -*- coding: utf-8 -*-
import json
import pytest
import tempfile
from pathlib import Path

from project_core.core_from_scripts.refactoring_manager import RefactoringManager


class TestRefactoringManager:
    """
    Unit tests for the RefactoringManager.
    """

    def setup_method(self):
        """Set up test environment with a temporary directory."""
        self._tmpdir = tempfile.mkdtemp(prefix="test_refactor_")
        self.test_dir = Path(self._tmpdir)
        self.manager = RefactoringManager()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_apply_refactoring_plan_update_import(self):
        """
        Test that `update_import` refactoring is correctly applied.
        """
        # 1. Create a dummy source file with valid Python
        source_content = "from a.b.c import MyClass\n\nclass Test(MyClass):\n    pass\n"
        source_file = self.test_dir / "source_module.py"
        source_file.write_text(source_content, encoding="utf-8")

        # 2. Create a refactoring plan
        plan = {
            "transformations": [
                {
                    "action": "update_import",
                    "old_path": "a.b.c",
                    "new_path": "x.y.z",
                    "target_dir": str(self.test_dir),
                }
            ]
        }
        plan_file = self.test_dir / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        # 3. Apply the plan (use test_dir to avoid scanning the entire project)
        self.manager.apply_refactoring_plan(
            plan_file, dry_run=False, project_root=self.test_dir
        )

        # 4. Verify the result
        modified_content = source_file.read_text(encoding="utf-8")
        assert "from x.y.z import MyClass" in modified_content
        assert "from a.b.c import MyClass" not in modified_content

    def test_apply_refactoring_plan_dry_run(self):
        """
        Test that `dry_run` computes diffs but does not modify files.
        """
        # 1. Create a dummy source file
        source_content = "from old.place import Thing\n"
        source_file = self.test_dir / "another_module.py"
        source_file.write_text(source_content, encoding="utf-8")

        # 2. Create a refactoring plan
        plan = {
            "transformations": [
                {
                    "action": "update_import",
                    "old_path": "old.place",
                    "new_path": "new.place",
                    "target_dir": str(self.test_dir),
                }
            ]
        }
        plan_file = self.test_dir / "dry_run_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        # 3. Apply the plan in dry_run mode
        diffs = self.manager.apply_refactoring_plan(
            plan_file, dry_run=True, project_root=self.test_dir
        )

        # 4. Verify diffs were computed
        assert len(diffs) > 0, "No diffs were computed"
        diff_values = "\n".join(diffs.values())
        assert "-from old.place import Thing" in diff_values
        assert "+from new.place import Thing" in diff_values

        # 5. Ensure the original file is unchanged
        original_content_after = source_file.read_text(encoding="utf-8")
        assert source_content == original_content_after

    def test_apply_refactoring_plan_rename_function(self):
        """
        Test that `rename_function` refactoring is correctly applied.
        """
        # 1. Create a dummy source file
        source_content = "def old_func():\n    pass\n\nold_func()\n"
        source_file = self.test_dir / "func_rename_module.py"
        source_file.write_text(source_content, encoding="utf-8")

        # 2. Create a refactoring plan
        plan = {
            "transformations": [
                {
                    "action": "rename_function",
                    "old_name": "old_func",
                    "new_name": "new_func",
                }
            ]
        }
        plan_file = self.test_dir / "rename_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        # 3. Apply the plan
        self.manager.apply_refactoring_plan(
            plan_file, dry_run=False, project_root=self.test_dir
        )

        # 4. Verify the result
        modified_content = source_file.read_text(encoding="utf-8")
        assert "new_func()" in modified_content

# -*- coding: utf-8 -*-
import unittest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from project_core.core_from_scripts.refactoring_manager import RefactoringManager

class TestRefactoringManager(unittest.TestCase):
    """
    Unit tests for the RefactoringManager.
    """
    def setUp(self):
        """Set up test environment."""
        self.manager = RefactoringManager()
        self.test_dir = Path("./temp_test_refactor")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        for f in self.test_dir.glob("**/*"):
            if f.is_file():
                f.unlink()
        for d in self.test_dir.glob("**/"):
             if d.is_dir():
                try:
                    d.rmdir()
                except OSError: # ignore if not empty
                    pass
        try:
            self.test_dir.rmdir()
        except OSError:
             pass


    def test_apply_refactoring_plan_update_import(self):
        """
        Test that `update_import` refactoring is correctly applied.
        """
        # 1. Create a dummy source file
        source_content = "from a.b.c import MyClass\\n\\nclass Test(MyClass):\\n    pass"
        source_file = self.test_dir / "source_module.py"
        source_file.write_text(source_content, encoding="utf-8")

        # 2. Create a refactoring plan
        plan = {
            "transformations": [{
                "action": "update_import",
                "old_path": "a.b.c",
                "new_path": "x.y.z",
                "target_dir": str(self.test_dir)
            }]
        }
        plan_file = self.test_dir / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        # 3. Apply the plan
        self.manager.apply_refactoring_plan(plan_file, dry_run=False, project_root=Path("."))

        # 4. Verify the result
        modified_content = source_file.read_text(encoding="utf-8")
        expected_content = "from x.y.z import MyClass\\n\\nclass Test(MyClass):\\n    pass\\n"
        self.assertEqual(modified_content.strip(), expected_content.strip())
        
    def test_apply_refactoring_plan_dry_run(self):
        """
        Test that `dry_run` computes diffs but does not modify files.
        """
        # 1. Create a dummy source file
        source_content = "from old.place import Thing"
        source_file = self.test_dir / "another_module.py"
        source_file.write_text(source_content, encoding="utf-8")

        # 2. Create a refactoring plan
        plan = {
            "transformations": [{
                "action": "update_import",
                "old_path": "old.place",
                "new_path": "new.place",
                "target_dir": str(self.test_dir)
            }]
        }
        plan_file = self.test_dir / "dry_run_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        # 3. Apply the plan in dry_run mode
        diffs = self.manager.apply_refactoring_plan(plan_file, dry_run=True, project_root=Path("."))

        # 4. Verify the result
        self.assertIn(str(source_file), diffs)
        self.assertIn("-from old.place import Thing", diffs[str(source_file)])
        self.assertIn("+from new.place import Thing", diffs[str(source_file)])

        # 5. Ensure the original file is unchanged
        original_content_after = source_file.read_text(encoding="utf-8")
        self.assertEqual(source_content, original_content_after)

if __name__ == '__main__':
    unittest.main()
    def test_apply_refactoring_plan_rename_function(self):
        """
        Test that `rename_function` refactoring is correctly applied.
        """
        # 1. Create a dummy source file
        source_content = "def old_func():\\n    pass\\n\\nold_func()"
        source_file = self.test_dir / "func_rename_module.py"
        source_file.write_text(source_content, encoding="utf-8")

        # 2. Create a refactoring plan
        plan = {
            "transformations": [{
                "action": "rename_function",
                "old_name": "old_func",
                "new_name": "new_func"
            }]
        }
        plan_file = self.test_dir / "rename_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        # 3. Apply the plan
        self.manager.apply_refactoring_plan(plan_file, dry_run=False, project_root=self.test_dir)

        # 4. Verify the result
        modified_content = source_file.read_text(encoding="utf-8")
        # ast.unparse might add extra newlines
        expected_content = "def old_func():\\n    pass\\n\\nnew_func()"
        self.assertIn(expected_content.strip(), modified_content.strip())
import os
import unittest
import shutil
import json
from unittest.mock import patch, MagicMock

from project_core.core_from_scripts.organization_manager import OrganizationManager


class TestOrganizationManager(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory structure for testing."""
        self.test_root = os.path.join(os.path.dirname(__file__), "temp_test_org")
        self.results_dir = os.path.join(self.test_root, "results")
        self.archive_dir = os.path.join(self.test_root, "results_archive")

        # Clean up previous test runs
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

        os.makedirs(self.results_dir)
        os.makedirs(self.archive_dir)

        # Create some dummy files
        with open(os.path.join(self.results_dir, "test_image1.png"), "w") as f:
            f.write("dummy png")
        with open(os.path.join(self.results_dir, "test_log.txt"), "w") as f:
            f.write("dummy log")

        # For apply_organization_plan test
        self.file_to_delete = os.path.join(self.test_root, "to_delete.log")
        self.file_to_move = os.path.join(self.test_root, "to_move.txt")
        self.move_dest_dir = os.path.join(self.test_root, "destination_dir")
        os.makedirs(self.move_dest_dir)
        with open(self.file_to_delete, "w") as f:
            f.write("delete me")
        with open(self.file_to_move, "w") as f:
            f.write("move me")

        self.manager = OrganizationManager(project_root=self.test_root)
        # We need to explicitly set the archive dir for the test instance
        self.manager.archive_dir = self.archive_dir

    def tearDown(self):
        """Clean up the temporary directory after tests."""
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def test_organize_results_directory(self):
        """
        Test the successful organization of the results directory.
        """
        report = self.manager.organize_results_directory()

        # Check report status
        self.assertTrue(report["archived"])
        self.assertTrue(report["new_structure_created"])
        self.assertTrue(report["readme_generated"])
        self.assertEqual(len(report["errors"]), 0)

        # Check that the new results directory exists
        self.assertTrue(os.path.exists(self.results_dir))

        # Check that the README.md was created
        readme_path = os.path.join(self.results_dir, "README.md")
        self.assertTrue(os.path.exists(readme_path))

        # Check that files were moved correctly
        expected_image_dir = os.path.join(self.results_dir, "images")
        self.assertTrue(os.path.exists(expected_image_dir))
        moved_image_path = os.path.join(expected_image_dir, "test_image1.png")
        self.assertTrue(os.path.exists(moved_image_path))

        # Check that the old results directory is now in the archive
        self.assertEqual(len(os.listdir(self.archive_dir)), 1)
        archived_results = os.path.join(
            self.archive_dir, os.listdir(self.archive_dir)[0]
        )
        self.assertTrue(os.path.isdir(archived_results))
        # The log file should be in the archive, but not the moved png
        self.assertTrue(os.path.exists(os.path.join(archived_results, "test_log.txt")))
        self.assertFalse(
            os.path.exists(os.path.join(archived_results, "test_image1.png"))
        )

    def test_apply_organization_plan(self):
        """Test applying a valid organization plan."""
        plan = {
            "actions": [
                {"action": "delete", "path": "to_delete.log"},
                {
                    "action": "move",
                    "source": "to_move.txt",
                    "destination": "destination_dir/moved.txt",
                },
            ]
        }
        plan_path = os.path.join(self.test_root, "plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan, f)

        report = self.manager.apply_organization_plan(plan_path)

        self.assertEqual(report["operations_success"], 2)
        self.assertEqual(report["operations_failed"], 0)
        self.assertEqual(len(report["errors"]), 0)
        self.assertFalse(os.path.exists(self.file_to_delete))
        self.assertFalse(os.path.exists(self.file_to_move))
        self.assertTrue(os.path.exists(os.path.join(self.move_dest_dir, "moved.txt")))

    def test_apply_organization_plan_with_errors(self):
        """Test applying a plan with invalid actions and files."""
        plan = {
            "actions": [
                {"action": "delete", "path": "non_existent_file.log"},
                {"action": "unknown_action", "path": "some_file.txt"},
            ]
        }
        plan_path = os.path.join(self.test_root, "plan_error.json")
        with open(plan_path, "w") as f:
            json.dump(plan, f)

        report = self.manager.apply_organization_plan(plan_path)

        self.assertEqual(report["operations_success"], 0)
        self.assertEqual(report["operations_failed"], 2)
        self.assertEqual(len(report["errors"]), 2)
        self.assertIn("File to delete not found", report["errors"][0])
        self.assertIn("Unknown action in plan", report["errors"][1])


if __name__ == "__main__":
    unittest.main()

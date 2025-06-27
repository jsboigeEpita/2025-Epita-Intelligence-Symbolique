# -*- coding: utf-8 -*-
import os
import shutil
import unittest
from pathlib import Path

from project_core.core_from_scripts.cleanup_manager import CleanupManager

class TestCleanupManager(unittest.TestCase):
    """
    Unit tests for the CleanupManager.
    """

    def setUp(self):
        """
        Set up a temporary directory structure for testing.
        """
        self.test_dir = Path("./temp_test_for_cleanup")
        self.test_dir.mkdir(exist_ok=True)

        # Create dummy files and directories to be cleaned
        (self.test_dir / "__pycache__").mkdir()
        (self.test_dir / "subdir/__pycache__").mkdir(parents=True)
        (self.test_dir / "file.pyc").touch()
        (self.test_dir / "subdir/another.pyc").touch()
        (self.test_dir / ".pytest_cache").mkdir()

        # Create dummy files and directories that should NOT be cleaned
        (self.test_dir / "important.txt").touch()
        (self.test_dir / "code.py").touch()
        (self.test_dir / "data").mkdir()
        (self.test_dir / "data/persists.txt").touch()

    def tearDown(self):
        """
        Remove the temporary directory after tests.
        """
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_cleanup_temporary_files(self):
        """
        Test that temporary files and directories are correctly removed.
        """
        # --- Act ---
        report = CleanupManager.cleanup_temporary_files(root_dir=str(self.test_dir))

        # --- Assert ---
        # Check that targeted files/dirs are gone
        self.assertFalse((self.test_dir / "__pycache__").exists())
        self.assertFalse((self.test_dir / "subdir/__pycache__").exists())
        self.assertFalse((self.test_dir / "file.pyc").exists())
        self.assertFalse((self.test_dir / "subdir/another.pyc").exists())
        self.assertFalse((self.test_dir / ".pytest_cache").exists())

        # Check that important files/dirs remain
        self.assertTrue((self.test_dir / "important.txt").exists())
        self.assertTrue((self.test_dir / "code.py").exists())
        self.assertTrue((self.test_dir / "data").exists())
        self.assertTrue((self.test_dir / "data/persists.txt").exists())

        # Check the report
        self.assertEqual(len(report["dirs"]), 3)
        self.assertEqual(len(report["files"]), 2)
        
    def test_cleanup_temporary_files_on_clean_dir(self):
        """
        Test that the function runs without error on a clean directory.
        """
        # --- Arrange ---
        clean_dir = self.test_dir / "clean_subdirectory"
        clean_dir.mkdir()
        (clean_dir / "some_file.txt").touch()
        
        # --- Act ---
        report = CleanupManager.cleanup_temporary_files(root_dir=str(clean_dir))

        # --- Assert ---
        self.assertTrue((clean_dir / "some_file.txt").exists())
        self.assertEqual(len(report["dirs"]), 0)
        self.assertEqual(len(report["files"]), 0)

if __name__ == '__main__':
    unittest.main()
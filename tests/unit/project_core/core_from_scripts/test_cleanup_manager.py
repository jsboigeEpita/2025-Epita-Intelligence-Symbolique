# -*- coding: utf-8 -*-
"""
Tests for CleanupManager.
"""

import os
import shutil
import unittest
from pathlib import Path

from project_core.core_from_scripts.cleanup_manager import CleanupManager

class TestCleanupManager(unittest.TestCase):
    """
    Test suite for the CleanupManager.
    """

    def setUp(self):
        """
        Set up a temporary test directory with dummy __pycache__ dirs and .pyc files.
        """
        self.test_dir = Path("test_temp_for_cleanup_2").resolve()
        self.test_dir.mkdir(exist_ok=True)

        # Structure to be cleaned
        self.pycache_dir1 = self.test_dir / "dir1" / "__pycache__"
        self.pycache_dir1.mkdir(parents=True, exist_ok=True)
        (self.pycache_dir1 / "test1.cpython-310.pyc").touch()
        
        self.pyc_file1 = self.test_dir / "dir1" / "file1.pyc"
        self.pyc_file1.touch()

        self.pycache_dir2 = self.test_dir / "dir2" / "subdir" / "__pycache__"
        self.pycache_dir2.mkdir(parents=True, exist_ok=True)
        (self.pycache_dir2 / "test2.cpython-310.pyc").touch()
        
        # Structure to be kept
        self.not_pycache = self.test_dir / "dir1" / "not__pycache__"
        self.not_pycache.mkdir()
        (self.not_pycache / "some_file.txt").touch()


    def tearDown(self):
        """
        Remove the temporary test directory.
        """
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_cleanup_pycache(self):
        """
        Test the cleanup_pycache method.
        """
        # Execute the cleanup on the temporary directory
        report = CleanupManager.cleanup_pycache(root_dir=str(self.test_dir))

        # Check the report
        self.assertEqual(len(report["dirs"]), 2)
        self.assertIn(str(self.pycache_dir1), report["dirs"])
        self.assertIn(str(self.pycache_dir2), report["dirs"])

        self.assertEqual(len(report["files"]), 3)
        self.assertIn(str(self.pyc_file1), report["files"])
        self.assertIn(str(self.pycache_dir1 / "test1.cpython-310.pyc"), report["files"])
        self.assertIn(str(self.pycache_dir2 / "test2.cpython-310.pyc"), report["files"])

        # Check the file system
        self.assertFalse(self.pycache_dir1.exists())
        self.assertFalse(self.pycache_dir2.exists())
        self.assertFalse(self.pyc_file1.exists())
        self.assertTrue(self.not_pycache.exists())
        self.assertTrue((self.not_pycache / "some_file.txt").exists())


if __name__ == '__main__':
    unittest.main()
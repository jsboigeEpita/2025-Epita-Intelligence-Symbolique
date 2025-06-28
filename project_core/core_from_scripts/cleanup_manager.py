# -*- coding: utf-8 -*-
"""
Cleanup Manager
"""

import os
import shutil

class CleanupManager:
    """
    Manages the cleaning of the project.
    """

    @staticmethod
    def cleanup_temporary_files(root_dir=None):
        """
        Finds and removes all temporary files and directories like __pycache__, .pyc, .pytest_cache.
        It avoids traversing into symlinks to prevent issues with recursive links.

        Args:
            root_dir (str, optional): The root directory to clean. Defaults to project root.

        Returns:
            dict: A report of the deleted items.
        """
        if root_dir is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        deleted_items = {"dirs": [], "files": []}
        dirs_to_remove_names = ['__pycache__', '.pytest_cache']
        files_to_remove_patterns = ['.pyc']

        # Use topdown=True to be able to modify `dirs` in-place and avoid traversing
        # into directories that are going to be deleted, or symbolic links causing loops.
        # followlinks=False is the default but we make it explicit.
        for root, dirs, files in os.walk(root_dir, topdown=True, followlinks=False):
            # First, remove directories that match the criteria.
            # We iterate over a copy of `dirs` (using `dirs[:]`) because we are modifying the list in-place.
            # Modifying `dirs` in-place is how os.walk with topdown=True prunes traversal.
            for d in dirs[:]:
                if d in dirs_to_remove_names:
                    dir_path = os.path.join(root, d)
                    try:
                        shutil.rmtree(dir_path)
                        deleted_items["dirs"].append(dir_path)
                        dirs.remove(d)  # Prune from traversal
                    except OSError as e:
                        print(f"Error removing directory {dir_path}: {e}")
                        dirs.remove(d) # Also prune if error to avoid descending into it

            # Second, clean files in the current directory.
            for name in files:
                if any(name.endswith(pattern) for pattern in files_to_remove_patterns):
                    file_path = os.path.join(root, name)
                    try:
                        os.remove(file_path)
                        deleted_items["files"].append(file_path)
                    except OSError as e:
                        print(f"Error removing file {file_path}: {e}")
        
        return deleted_items
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
    def cleanup_pycache(root_dir=None):
        """
        Finds and removes all __pycache__ directories and .pyc files efficiently.

        Args:
            root_dir (str, optional): The root directory to clean. Defaults to project root.

        Returns:
            dict: A report of the deleted items.
        """
        if root_dir is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        deleted_items = {"dirs": [], "files": []}
        
        # A single walk through the directory tree
        for root, dirs, files in os.walk(root_dir, topdown=False): # topdown=False allows safe removal
            
            # Remove .pyc files
            for name in files:
                if name.endswith('.pyc'):
                    file_path = os.path.join(root, name)
                    try:
                        os.remove(file_path)
                        deleted_items["files"].append(file_path)
                    except OSError as e:
                        print(f"Error removing file {file_path}: {e}")

            # Remove __pycache__ directories
            if os.path.basename(root) == '__pycache__':
                try:
                    # The .pyc files inside are already removed by the loop above
                    shutil.rmtree(root) 
                    deleted_items["dirs"].append(root)
                except OSError as e:
                    print(f"Error removing directory {root}: {e}")
        
        return deleted_items
# -*- coding: utf-8 -*-
"""
Manages environment variables for the project.
"""

import os
from dotenv import load_dotenv, find_dotenv

class EnvironmentManager:
    """
    Handles loading and retrieving environment variables.
    It now tracks if a .env file was found and loaded.
    """
    def __init__(self, override=False):
        # find_dotenv() searches for the .env file (useful for scripts deep in the hierarchy)
        # It returns the path to the file, or an empty string if not found.
        self.dotenv_path = find_dotenv()
        
        # load_dotenv() returns True if it found and loaded a file.
        self.dotenv_loaded = load_dotenv(dotenv_path=self.dotenv_path or None, override=override)

    def get_variable(self, name: str, default=None):
        """
        Retrieves an environment variable.
        """
        return os.getenv(name, default)
# -*- coding: utf-8 -*-
"""
Manages environment variables for the project.
"""

import os
from dotenv import load_dotenv

class EnvironmentManager:
    """
    Handles loading and retrieving environment variables.
    """
    def __init__(self):
        load_dotenv()

    def get_variable(self, name: str, default=None):
        """
        Retrieves an environment variable.
        """
        return os.getenv(name, default)
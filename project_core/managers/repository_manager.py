# -*- coding: utf-8 -*-
"""
Module for managing Git repositories.
"""

import logging
from typing import List
from argumentation_analysis.core.utils.shell_utils import run_shell_command

logger = logging.getLogger(__name__)

class RepositoryManager:
    """
    Provides utilities for interacting with a Git repository.
    """

    @staticmethod
    def find_untracked_files() -> List[str]:
        """
        Finds all files in the repository that are not tracked by Git.

        This method executes `git status --porcelain` and parses the output
        to identify files marked with '??'.

        Returns:
            A list of paths for untracked files.
        """
        logger.info("Searching for untracked files in the repository...")
        
        command = ['git', 'status', '--porcelain']
        return_code, stdout, stderr = run_shell_command(
            command,
            description="Checking for untracked files"
        )
        
        if return_code != 0:
            logger.error(f"Failed to execute git status. Stderr: {stderr}")
            return []

        untracked_files: List[str] = []
        if not stdout:
            logger.info("No untracked files found.")
            return untracked_files

        for line in stdout.strip().split('\n'):
            if line.startswith('?? '):
                # The line is '?? path/to/file', so we slice from index 3
                untracked_files.append(line[3:])
        
        if untracked_files:
            logger.info(f"Found {len(untracked_files)} untracked files.")
            logger.debug(f"Untracked files: {untracked_files}")
        else:
            logger.info("No untracked files found.")
            
        return untracked_files

# -*- coding: utf-8 -*-
"""
Maintenance Manager CLI
"""

import argparse
import sys
import os

# Add project path to find project_core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_core.managers.repository_manager import RepositoryManager

def handle_repo_commands(args):
    """
    Handles commands related to the Git repository.
    """
    if args.repo_command == 'find-orphans':
        files = RepositoryManager.find_untracked_files()
        if files:
            print("Fichiers non suivis (orphelins) :")
            for f in files:
                print(f"- {f}")
        else:
            print("Aucun fichier orphelin trouvé.")

def main():
    """
    Main function for the Maintenance Manager CLI.
    """
    parser = argparse.ArgumentParser(description="Maintenance Manager CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # 'repo' command
    repo_parser = subparsers.add_parser('repo', help='Commands related to the Git repository')
    repo_subparsers = repo_parser.add_subparsers(dest='repo_command', help='Action to perform on the repository')
    
    # 'repo find-orphans' command
    repo_subparsers.add_parser('find-orphans', help='Find untracked (orphan) files in the repository')

    args = parser.parse_args()

    if args.command == 'repo':
        if args.repo_command:
            handle_repo_commands(args)
        else:
            repo_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
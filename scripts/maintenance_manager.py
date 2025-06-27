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
from project_core.core_from_scripts.cleanup_manager import CleanupManager
from project_core.core_from_scripts.environment_manager import EnvironmentManager
from project_core.core_from_scripts.organization_manager import OrganizationManager

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

def handle_project_commands(args):
    """
    Handles project maintenance commands.
    """
    if args.project_command == 'cleanup-cache':
        print("Nettoyage des répertoires __pycache__ et des fichiers .pyc...")
        report = CleanupManager.cleanup_pycache()
        print(f"Rapport de nettoyage :")
        print(f"  - {len(report['dirs'])} répertoires __pycache__ supprimés.")
        for d in report['dirs']:
            print(f"    - {d}")
        print(f"  - {len(report['files'])} fichiers .pyc supprimés.")
        for f in report['files']:
            print(f"    - {f}")
        print("Nettoyage terminé.")

def handle_env_commands(args):
    """
    Handles commands related to environment .env files.
    """
    manager = EnvironmentManager()
    if args.switch_to:
        if manager.switch_environment(args.switch_to):
            print(f"Successfully switched to environment: {args.switch_to}")
        else:
            print(f"Failed to switch to environment: {args.switch_to}")
    elif args.create:
        if manager.create_environment(args.create):
            print(f"Successfully created environment: {args.create}")
        else:
            print(f"Failed to create environment: {args.create}")
    elif args.validate:
        if manager.validate_environment(args.validate):
            print(f"Environment '{args.validate}' is valid.")
        else:
            print(f"Environment '{args.validate}' is invalid.")

def handle_organize_commands(args):
    """
    Handles commands related to project organization.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manager = OrganizationManager(project_root)

    if args.target == 'results':
        print("Organizing the 'results' directory...")
        report = manager.organize_results_directory()
        if report["errors"]:
            print("Errors occurred:")
            for error in report["errors"]:
                print(f"- {error}")
        else:
            print("Successfully organized the 'results' directory.")
            print(f"  - Archived: {report['archived']}")
            print(f"  - Files moved: {len(report['files_moved'])}")
            print(f"  - README generated: {report['readme_generated']}")
    elif args.apply_plan:
        print(f"Applying organization plan from: {args.apply_plan}...")
        report = manager.apply_organization_plan(args.apply_plan)
        if report["errors"]:
            print("Errors occurred during plan application:")
            for error in report["errors"]:
                print(f"- {error}")
        print(f"Plan application summary:")
        print(f"  - Successful operations: {report['operations_success']}")
        print(f"  - Failed operations: {report['operations_failed']}")
    else:
        print(f"Unknown target for organization: {args.target}")

def main():
    """
    Main function for the Maintenance Manager CLI.
    """
    parser = argparse.ArgumentParser(description="Maintenance Manager CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # 'repo' command
    repo_parser = subparsers.add_parser('repo', help='Commands related to the Git repository')
    repo_subparsers = repo_parser.add_subparsers(dest='repo_command', help='Action to perform on the repository')
    repo_subparsers.add_parser('find-orphans', help='Find untracked (orphan) files in the repository')

    # 'project' command
    project_parser = subparsers.add_parser('project', help='Project maintenance commands')
    project_subparsers = project_parser.add_subparsers(dest='project_command', help='Action to perform on the project')
    project_subparsers.add_parser('cleanup-cache', help='Find and remove all __pycache__ directories and .pyc files')

    # 'env' command
    env_parser = subparsers.add_parser('env', help='Manage .env environment files')
    env_group = env_parser.add_mutually_exclusive_group(required=True)
    env_group.add_argument('--switch-to', metavar='NAME', help='Switch the main .env file to the specified environment')
    env_group.add_argument('--create', metavar='NAME', help='Create a new environment file from the template')
    env_group.add_argument('--validate', metavar='NAME', help='Validate an environment file against the template')

    # 'organize' command
    # 'organize' command
    organize_parser = subparsers.add_parser('organize', help='Organize project directories')
    organize_group = organize_parser.add_mutually_exclusive_group(required=True)
    organize_group.add_argument('--target', choices=['results'], help='The target directory to organize')
    organize_group.add_argument('--apply-plan', metavar='PLAN_FILE', help='Apply an organization plan from a JSON file')
    
    args = parser.parse_args()

    if args.command == 'repo':
        if args.repo_command:
            handle_repo_commands(args)
        else:
            repo_parser.print_help()
    elif args.command == 'project':
        if args.project_command:
            handle_project_commands(args)
        else:
            project_parser.print_help()
    elif args.command == 'env':
        handle_env_commands(args)
    elif args.command == 'organize':
        if args.target or args.apply_plan:
             handle_organize_commands(args)
        else:
             organize_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
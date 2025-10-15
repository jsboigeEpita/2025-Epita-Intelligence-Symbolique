# -*- coding: utf-8 -*-
"""
Maintenance Manager CLI
"""

import argparse
import sys
import os


from project_core.core_from_scripts.cleanup_manager import CleanupManager
from project_core.core_from_scripts.environment_manager import EnvironmentManager
from project_core.core_from_scripts.organization_manager import OrganizationManager
from project_core.core_from_scripts.repository_manager import RepositoryManager
from project_core.core_from_scripts.refactoring_manager import RefactoringManager


def handle_refactor_commands(args):
    """Handles refactoring commands."""
    manager = RefactoringManager()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.plan:
        print(f"Applying refactoring plan: {args.plan}...")
        diffs = manager.apply_refactoring_plan(
            args.plan, args.dry_run, project_root=project_root
        )

        if args.dry_run:
            print("Dry run requested. The following changes would be made:")
            for file_path, diff in diffs.items():
                print(f"\n--- Diff for {file_path} ---")
                print(diff)
        else:
            print("Refactoring applied.")
            if diffs:
                print("Changes were made to the following files:")
                for file_path in diffs.keys():
                    print(f" - {file_path}")
            else:
                print("No changes were necessary based on the plan.")


def handle_repo_commands(args):
    """Handles commands related to the Git repository."""
    manager = RepositoryManager()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.repo_command == "find-orphans":
        # This part of the function seems to call a class method, which might be an error.
        # Assuming it should be an instance method for consistency.
        # If RepositoryManager.find_untracked_files is indeed a static/class method,
        # this would need to be adjusted.
        files = manager.find_untracked_files()
        if files:
            print("Fichiers non suivis (orphelins) :")
            for f in files:
                print(f"- {f}")
        else:
            print("Aucun fichier orphelin trouvé.")
    elif args.repo_command == "update-gitignore":
        template_path = os.path.join(
            project_root, "project_core", "templates", "project.gitignore.template"
        )
        added_rules = manager.update_gitignore_from_template(
            project_root, template_path
        )
        if added_rules:
            print(f"Successfully added {len(added_rules)} new rules to .gitignore:")
            for rule in added_rules:
                print(f" - {rule}")
        else:
            print(".gitignore is already up to date.")


def handle_cleanup_commands(args):
    """Handles cleanup commands."""
    if args.default:
        print("Nettoyage des fichiers et répertoires temporaires...")
        report = CleanupManager.cleanup_temporary_files()
        print("Rapport de nettoyage :")
        print(f"  - {len(report['dirs'])} répertoires supprimés.")
        for d in report["dirs"]:
            print(f"    - {d}")
        print(f"  - {len(report['files'])} fichiers supprimés.")
        for f in report["files"]:
            print(f"    - {f}")
        print("Nettoyage terminé.")


def handle_env_commands(args):
    """Handles commands related to environment .env files."""
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
    """Handles commands related to project organization."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manager = OrganizationManager(project_root)

    if args.target == "results":
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
        print("Plan application summary:")
        print(f"  - Successful operations: {report['operations_success']}")
        print(f"  - Failed operations: {report['operations_failed']}")
    else:
        print(f"Unknown target for organization: {args.target}")


def main():
    """Main function for the Maintenance Manager CLI."""
    parser = argparse.ArgumentParser(description="Maintenance Manager CLI")
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", required=True
    )

    # 'repo' command
    repo_parser = subparsers.add_parser(
        "repo", help="Commands related to the Git repository"
    )
    repo_subparsers = repo_parser.add_subparsers(
        dest="repo_command", help="Action to perform on the repository", required=True
    )
    find_orphans_parser = repo_subparsers.add_parser(
        "find-orphans", help="Find untracked (orphan) files in the repository"
    )
    update_gitignore_parser = repo_subparsers.add_parser(
        "update-gitignore", help="Update .gitignore from template."
    )

    # 'cleanup' command
    cleanup_parser = subparsers.add_parser("cleanup", help="Project cleanup commands")
    cleanup_parser.add_argument(
        "--default",
        action="store_true",
        help="Perform default cleanup of temporary files and directories.",
    )

    # 'env' command
    env_parser = subparsers.add_parser("env", help="Manage .env environment files")
    env_group = env_parser.add_mutually_exclusive_group(required=True)
    env_group.add_argument(
        "--switch-to",
        metavar="NAME",
        help="Switch the main .env file to the specified environment",
    )
    env_group.add_argument(
        "--create",
        metavar="NAME",
        help="Create a new environment file from the template",
    )
    env_group.add_argument(
        "--validate",
        metavar="NAME",
        help="Validate an environment file against the template",
    )

    # 'organize' command
    organize_parser = subparsers.add_parser(
        "organize", help="Organize project directories"
    )
    organize_group = organize_parser.add_mutually_exclusive_group(required=True)
    organize_group.add_argument(
        "--target", choices=["results"], help="The target directory to organize"
    )
    organize_group.add_argument(
        "--apply-plan",
        metavar="PLAN_FILE",
        help="Apply an organization plan from a JSON file",
    )

    # 'refactor' command
    refactor_parser = subparsers.add_parser(
        "refactor", help="Automated code refactoring"
    )
    refactor_parser.add_argument(
        "--plan", required=True, help="Path to the JSON refactoring plan."
    )
    refactor_parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying them."
    )

    args = parser.parse_args()

    command_handlers = {
        "repo": handle_repo_commands,
        "cleanup": handle_cleanup_commands,
        "env": handle_env_commands,
        "organize": handle_organize_commands,
        "refactor": handle_refactor_commands,
    }

    handler = command_handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

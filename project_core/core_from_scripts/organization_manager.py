import os
import shutil
import datetime
import json
from argumentation_analysis.core.utils import filesystem_utils


class OrganizationManager:
    """
    Manages the organization of project directories, such as the results directory.
    """

    def __init__(self, project_root: str):
        """
        Initializes the OrganizationManager.

        Args:
            project_root: The root directory of the project.
        """
        self.project_root = project_root
        self.results_dir = os.path.join(self.project_root, "results")
        self.archive_dir = os.path.join(self.project_root, "results_archive")

    def organize_results_directory(self) -> dict:
        """
        Organizes the results/ directory by archiving the current content,
        creating a new structure, moving files, and generating a README.

        This function is inspired by the workflow from 'clean_project.ps1'.

        Returns:
            A dictionary reporting on the operations performed.
        """
        report = {
            "archived": False,
            "new_structure_created": False,
            "files_moved": [],
            "readme_generated": False,
            "errors": [],
        }

        if not os.path.exists(self.results_dir):
            report["errors"].append("The 'results' directory does not exist.")
            return report

        try:
            # 1. Archive the current results directory
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = os.path.join(self.archive_dir, f"results_{timestamp}")
            shutil.move(self.results_dir, archive_path)
            report["archived"] = True

            # Create a new empty results directory
            os.makedirs(self.results_dir, exist_ok=True)
            report["new_structure_created"] = True

            # 2. Walk through the archived files and move them
            # This is a placeholder for the actual organization logic
            # which will depend on file patterns.

            # For now, let's imagine a simple case: moving .png files to a 'images' subfolder.
            images_dir = os.path.join(self.results_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            for root, _, files in os.walk(archive_path):
                for file in files:
                    if file.endswith(".png"):
                        shutil.move(
                            os.path.join(root, file), os.path.join(images_dir, file)
                        )
                        report["files_moved"].append(file)

            # 3. Generate a README.md
            readme_content = f"""# Results Directory organized on {timestamp}

This directory was automatically organized. 
The original content was archived to: {archive_path}

## Summary of operations:
- **{len(report['files_moved'])}** files were moved.
"""
            with open(
                os.path.join(self.results_dir, "README.md"), "w", encoding="utf-8"
            ) as f:
                f.write(readme_content)
            report["readme_generated"] = True

        except Exception as e:
            report["errors"].append(str(e))

        return report

    def apply_organization_plan(self, plan_path: str) -> dict:
        """
        Applies file organization actions from a JSON plan file.

        The plan can define actions like 'delete' or 'move'.

        Args:
            plan_path: The path to the JSON file containing the organization plan.

        Returns:
            A dictionary reporting on the operations performed.
        """
        report = {
            "plan_applied": plan_path,
            "operations_success": 0,
            "operations_failed": 0,
            "errors": [],
        }

        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
        except FileNotFoundError:
            report["errors"].append(f"Plan file not found: {plan_path}")
            return report
        except json.JSONDecodeError:
            report["errors"].append(f"Invalid JSON in plan file: {plan_path}")
            return report
        except Exception as e:
            report["errors"].append(f"Error reading plan file: {e}")
            return report

        for item in plan.get("actions", []):
            action = item.get("action")
            try:
                if action == "delete":
                    target_path = os.path.join(self.project_root, item["path"])
                    if os.path.exists(target_path):
                        os.remove(target_path)
                        report["operations_success"] += 1
                    else:
                        raise FileNotFoundError(
                            f"File to delete not found: {target_path}"
                        )
                elif action == "move":
                    source_path = os.path.join(self.project_root, item["source"])
                    dest_path = os.path.join(self.project_root, item["destination"])
                    shutil.move(source_path, dest_path)
                    report["operations_success"] += 1
                else:
                    raise ValueError(f"Unknown action in plan: {action}")
            except Exception as e:
                report["operations_failed"] += 1
                report["errors"].append(str(e))

        return report

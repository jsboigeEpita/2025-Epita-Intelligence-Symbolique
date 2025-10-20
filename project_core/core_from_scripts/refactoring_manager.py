# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, Any, Union

from argumentation_analysis.core.utils import code_manipulation_utils

# from argumentation_analysis.core.utils.filesystem_utils import get_all_files_in_directory # Obsolete
import difflib


class RefactoringManager:
    """
    Applies large-scale code transformations based on a declarative plan.
    """

    def _apply_single_transformation(
        self, original_code: str, transformation: Dict[str, Any]
    ) -> str:
        """Applies a single transformation rule to a string of code."""
        action = transformation.get("action")

        if action == "update_import":
            return code_manipulation_utils.refactor_update_import(
                original_code,
                transformation.get("old_path"),
                transformation.get("new_path"),
            )
        elif action == "rename_function":
            return code_manipulation_utils.refactor_rename_function(
                original_code,
                transformation.get("old_name"),
                transformation.get("new_name"),
            )

        return original_code

    def apply_refactoring_plan(
        self,
        plan_path: Union[str, Path],
        dry_run: bool = False,
        project_root: Path = None,
    ) -> Dict[str, str]:
        """
        Applies a series of refactoring actions defined in a JSON plan.

        Args:
            plan_path: Path to the JSON refactoring plan.
            dry_run: If True, computes and returns the diffs without applying them.
            project_root: The root directory of the project. Defaults to current dir.

        Returns:
            A dictionary where keys are file paths and values are the diffs of changes.
        """
        plan_path = Path(plan_path)
        if not plan_path.is_file():
            raise FileNotFoundError(f"Refactoring plan not found at: {plan_path}")

        if project_root is None:
            project_root = Path.cwd()

        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)

        all_diffs = {}
        excluded_dirs = {
            "node_modules",
            ".venv",
            ".git",
            "__pycache__",
            "build",
            "dist",
            "env",
        }

        all_files = list(project_root.rglob("*.py"))
        target_files = []
        for p in all_files:
            if not any(excluded in p.parts for excluded in excluded_dirs):
                target_files.append(p)

        for file_path in target_files:
            try:
                original_code = file_path.read_text(encoding="utf-8")
                modified_code = original_code

                for transformation in plan.get("transformations", []):
                    # Apply transformation sequentially on the modified code
                    modified_code = self._apply_single_transformation(
                        modified_code, transformation
                    )

                if original_code != modified_code:
                    diff = "".join(
                        difflib.unified_diff(
                            original_code.splitlines(True),
                            modified_code.splitlines(True),
                            fromfile=str(file_path),
                            tofile=str(file_path),
                        )
                    )
                    all_diffs[str(file_path)] = diff

                    if not dry_run:
                        file_path.write_text(modified_code, encoding="utf-8")

            except OSError as e:
                print(f"Skipping file due to OSError: {file_path} - {e}")
                continue

        return all_diffs

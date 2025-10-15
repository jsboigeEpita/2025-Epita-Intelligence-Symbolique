# -*- coding: utf-8 -*-
"""
Manager for repository-related operations.
"""


class RepositoryManager:
    """
    Manages repository operations like Git interactions.
    """

    def __init__(self):
        """
        Initializes the RepositoryManager.
        """
        pass

    def update_gitignore_from_template(
        self, project_root: str, template_path: str
    ) -> list[str]:
        """
        Updates the .gitignore file from a template.

        Args:
            project_root: The root directory of the project.
            template_path: The path to the .gitignore.template file.

        Returns:
            A list of added rules.
        """
        import os

        gitignore_path = os.path.join(project_root, ".gitignore")

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_rules = {
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                }
        except FileNotFoundError:
            raise ValueError(f"Template file not found at {template_path}")

        existing_rules = set()
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_rules = {
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                }

        new_rules = sorted(list(template_rules - existing_rules))

        if new_rules:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Managed by Project Core\n")
                for rule in new_rules:
                    f.write(f"{rule}\n")

        return new_rules

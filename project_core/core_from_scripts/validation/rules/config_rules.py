"""
Règles de validation liées à la configuration.
"""

import os
from ..validation_engine import ValidationRule, ValidationResult


class ConfigValidationRule(ValidationRule):
    """Vérifie la présence des fichiers de configuration essentiels."""

    def validate(self) -> ValidationResult:
        essential_files = [
            ".env.example",
            "pyproject.toml",
            "config/unified_config.py",
            "run_in_env.ps1",
        ]

        missing_files = []
        for file_path in essential_files:
            full_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)

        if missing_files:
            return ValidationResult(
                success=False,
                rule_name=self.name,
                message=f"Fichiers de configuration manquants: {', '.join(missing_files)}",
                details={"missing_files": missing_files},
            )

        return ValidationResult(
            success=True,
            rule_name=self.name,
            message="Tous les fichiers de configuration essentiels sont présents.",
        )

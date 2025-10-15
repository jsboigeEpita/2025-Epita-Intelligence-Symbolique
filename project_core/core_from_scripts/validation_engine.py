import os
import sys
import importlib.util
from pathlib import Path

from argumentation_analysis.core.utils import shell_utils


class ValidationEngine:
    """
    Orchestrates various validation checks to assess project health.
    """

    def __init__(self, project_root: str = None):
        """
        Initializes the ValidationEngine.

        Args:
            project_root: The root directory of the project. If None, it's detected automatically.
        """
        self.project_root = (
            Path(project_root) if project_root else Path(__file__).resolve().parents[3]
        )

    def validate_build_tools(self) -> dict:
        """
        Checks for the presence of Visual Studio Build Tools on Windows.

        Returns:
            A dictionary with status and a message.
        """
        if sys.platform != "win32":
            return {
                "status": "skipped",
                "message": "Validation non applicable sur les systèmes non-Windows.",
            }

        # Common paths for vcvarsall.bat
        vcvars_paths = [
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            / "Microsoft Visual Studio"
            / "2022"
            / "BuildTools"
            / "VC"
            / "Auxiliary"
            / "Build"
            / "vcvarsall.bat",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            / "Microsoft Visual Studio"
            / "2019"
            / "BuildTools"
            / "VC"
            / "Auxiliary"
            / "Build"
            / "vcvarsall.bat",
        ]

        for path in vcvars_paths:
            if path.exists():
                return {
                    "status": "success",
                    "message": f"Outils de compilation trouvés : {path}",
                }

        return {
            "status": "failure",
            "message": "Les Visual Studio Build Tools semblent manquer. Veuillez exécuter 'scripts/setup/install_build_tools.ps1' avec les droits administrateur.",
        }

    def validate_jvm_bridge(self) -> dict:
        """
        Validates that the JPype bridge for the JVM is installed and importable.
        """
        try:
            importlib.import_module("jpype")
            return {
                "status": "success",
                "message": "Le pont JVM (JPype) est correctement installé.",
            }
        except ImportError:
            return {
                "status": "failure",
                "message": "JPype n'est pas installé. Essayez de le réparer avec 'setup_manager.py fix-deps --package JPype1 --strategy=aggressive'.",
            }

    def validate_critical_imports(self, config: dict) -> dict:
        """
        Validates that critical project modules can be imported.
        (SKELETON)
        """
        return {"status": "pending", "message": "Fonction non implémentée."}

    def validate_project_structure(self, config: dict) -> dict:
        """
        Validates that the project's directory structure is correct.
        (SKELETON)
        """
        return {"status": "pending", "message": "Fonction non implémentée."}

    def run_test_coverage(self) -> dict:
        """
        Runs pytest with coverage and returns the result.
        (SKELETON)
        """
        return {"status": "pending", "message": "Fonction non implémentée."}

    def run_full_validation(self) -> dict:
        """
        Runs all validation checks and compiles a report.
        """
        results = {
            "build_tools": self.validate_build_tools(),
            "jvm_bridge": self.validate_jvm_bridge(),
            # Add other validations here as they are implemented
        }
        return results

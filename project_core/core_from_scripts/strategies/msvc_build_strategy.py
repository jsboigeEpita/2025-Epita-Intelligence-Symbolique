import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy


class MsvcBuildStrategy(BaseStrategy):
    """
    Stratégie de réparation qui tente d'utiliser les outils de compilation MSVC.
    """

    @property
    def name(self) -> str:
        return "msvc-build"

    def execute(self, package: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Tente de compiler en utilisant l'environnement MSVC.
        """
        self.logger.info(
            f"[{package}] Exécution de la stratégie de réparation '{self.name}'..."
        )
        if not sys.platform == "win32":
            self.logger.warning(
                f"[{package}] La stratégie '{self.name}' n'est applicable que sur Windows."
            )
            return False

        vcvars_path = self._find_vcvarsall()
        if vcvars_path:
            self.logger.info(
                "La stratégie de compilation MSVC automatique n'est pas encore implémentée."
            )
            self.logger.info(
                "Pour une installation manuelle, utilisez une 'x64 Native Tools Command Prompt' et exécutez les commandes suivantes:"
            )
            self.logger.info(
                f"conda activate {self.manager_env.get_conda_env_name_from_dotenv()}"
            )
            self.logger.info(f'pip install "{package}"')
        else:
            self.logger.warning(
                f"[{package}] Outils de compilation MSVC (vcvarsall.bat) introuvables. Échec de cette étape."
            )

        return False  # Retourne toujours False car l'action automatique n'est pas faite

    def _find_vcvarsall(self) -> Optional[Path]:
        """Trouve le script vcvarsall.bat dans les emplacements d'installation courants de Visual Studio."""
        program_files = Path(
            os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")
        )
        vs_versions = ["2022", "2019", "2017"]
        editions = ["Community", "Professional", "Enterprise", "BuildTools"]

        for version in vs_versions:
            for edition in editions:
                vcvars_path = (
                    program_files
                    / "Microsoft Visual Studio"
                    / version
                    / edition
                    / "VC"
                    / "Auxiliary"
                    / "Build"
                    / "vcvarsall.bat"
                )
                if vcvars_path.is_file():
                    self.logger.info(f"vcvarsall.bat trouvé : {vcvars_path}")
                    return vcvars_path
        self.logger.warning("vcvarsall.bat introuvable.")
        return None

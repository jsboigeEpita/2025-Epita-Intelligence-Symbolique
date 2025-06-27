import shutil
import sys
import logging
import argparse
import sys
import os
import platform
from pathlib import Path
from typing import Optional, List, Union, Dict

# Importation corrigée pour utiliser l'utilitaire central du projet
from argumentation_analysis.core.utils.shell_utils import run_shell_command

# Configuration du logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='[ENV_MGR] [%(asctime)s] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """Gère la création, la validation, le changement de fichiers .env et l'exécution de commandes."""

    def __init__(self, project_root: Optional[Path] = None, logger_instance: Optional[logging.Logger] = None):
        """
        Initialise le gestionnaire.

        Args:
            project_root: Le chemin racine du projet.
            logger_instance: Le logger à utiliser.
        """
        self.project_root = project_root or Path(__file__).resolve().parent.parent.parent
        self.logger = logger_instance or logging.getLogger(__name__)
        self.env_files_dir = self.project_root / "config" / "environments"
        self.template_path = self.project_root / "config" / "templates" / ".env.tpl"
        self.target_env_file = self.project_root / ".env"

    def get_conda_env_name_from_dotenv(self) -> Optional[str]:
        """Lit le nom de l'environnement Conda depuis le fichier .env à la racine."""
        if not self.target_env_file.is_file():
            self.logger.error(f"Le fichier .env cible est introuvable à : {self.target_env_file}")
            return None
        
        try:
            # Utiliser utf-8-sig pour gérer de manière transparente le BOM (Byte Order Mark)
            # qui peut être ajouté par certains éditeurs ou outils sur Windows.
            with open(self.target_env_file, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.strip().startswith("CONDA_ENV_NAME="):
                        env_name = line.split('=', 1)[1].strip()
                        # Retirer les guillemets si présents
                        return env_name.strip('\'"')

            self.logger.warning(f"La variable CONDA_ENV_NAME n'a pas été trouvée dans {self.target_env_file}")
            return None
        except IOError as e:
            self.logger.error(f"Erreur de lecture du fichier .env : {e}")
            return None

    def run_command_in_conda_env(self, command_to_run: str) -> int:
        """
        Exécute une commande dans l'environnement Conda spécifié par le .env.
        Utilise `conda run` pour une exécution propre dans un sous-processus.
        """
        conda_env_name = self.get_conda_env_name_from_dotenv()
        if not conda_env_name:
            self.logger.error("Impossible d'exécuter la commande car le nom de l'environnement Conda n'a pas pu être déterminé.")
            return 1

        # Nouvelle stratégie : Utiliser directement les fonctionnalités de `conda run`.
        # On supprime la surcouche PowerShell qui s'est avérée peu fiable.
        # On utilise --cwd pour définir le répertoire de travail, ce qui est la méthode
        # la plus propre et recommandée.
        self.logger.info(f"Utilisation de --cwd='{self.project_root}' pour l'exécution.")

        # La commande à exécuter doit être passée en tant que liste d'arguments après `conda run`.
        command_parts = command_to_run.split()

        full_command = [
            "conda", "run",
            "-n", conda_env_name,
            "--cwd", str(self.project_root),
            "--no-capture-output",
            "--live-stream",
        ] + command_parts
        
        description = f"Exécution de '{command_to_run[:50]}...' dans l'env '{conda_env_name}' via `conda run --cwd`"
        
        # On exécute la commande, en s'assurant que `run_shell_command` n'utilise pas `shell=True`
        # car on passe une liste d'arguments bien formée.
        exit_code, _, _ = run_shell_command(
            command=full_command,
            description=description,
            capture_output=False,
            shell_mode=False
        )
        
        return exit_code

    def switch_environment(self, target_name: str) -> bool:
        """Bascule vers un fichier .env nommé."""
        source_path = self.env_files_dir / f"{target_name}.env"
        if not source_path.is_file():
            self.logger.error(f"Le fichier d'environnement source n'existe pas : {source_path}")
            return False
        try:
            shutil.copy(source_path, self.target_env_file)
            self.logger.info(f"L'environnement a été basculé vers '{target_name}'. Fichier '{source_path}' copié vers '{self.target_env_file}'.")
            return True
        except IOError as e:
            self.logger.error(f"Erreur lors de la copie du fichier d'environnement : {e}")
            return False

    def fix_dependencies(self, packages: Optional[List[str]] = None, requirements_file: Optional[str] = None, strategy: str = 'default') -> bool:
        """
        Répare les dépendances en les réinstallant.

        Args:
            packages: Une liste de noms de paquets à réinstaller.
            requirements_file: Le chemin vers un fichier requirements.txt.
            strategy: La stratégie à utiliser ('default' ou 'aggressive').

        Returns:
            True si l'opération a réussi, False sinon.
        """
        if packages and requirements_file:
            raise ValueError("Les arguments 'packages' et 'requirements_file' sont mutuellement exclusifs.")

        if not packages and not requirements_file:
            self.logger.warning("Aucun paquet ou fichier de requirements fourni.")
            return True
            
        if requirements_file:
            if not (self.project_root / requirements_file).is_file():
                self.logger.error(f"Fichier de requirements introuvable: {requirements_file}")
                return False
            command = f"pip install -r {requirements_file}"
            self.logger.info(f"Exécution de la réparation depuis le fichier de requirements : {command}")
            return self.run_command_in_conda_env(command) == 0

        if packages:
            if strategy == 'default':
                package_str = " ".join(packages)
                command = f"pip install --force-reinstall --no-cache-dir {package_str}"
                self.logger.info(f"Exécution de la réparation (stratégie par défaut) : {command}")
                return self.run_command_in_conda_env(command) == 0
            elif strategy == 'aggressive':
                self.logger.info(f"Lancement de la stratégie de réparation AGRESSIVE pour : {', '.join(packages)}")
                for package in packages:
                    if not self._aggressive_fix_for_package(package):
                        self.logger.error(f"Échec de la stratégie agressive pour le paquet '{package}'.")
                        return False
                self.logger.info("Stratégie de réparation agressive terminée avec succès.")
                return True

        return False

    def _find_vcvarsall(self) -> Optional[Path]:
        """Trouve le script vcvarsall.bat dans les emplacements d'installation courants de Visual Studio."""
        program_files = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        vs_versions = ["2022", "2019", "2017"]
        editions = ["Community", "Professional", "Enterprise", "BuildTools"]
        
        for version in vs_versions:
            for edition in editions:
                vcvars_path = program_files / "Microsoft Visual Studio" / version / edition / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                if vcvars_path.is_file():
                    self.logger.info(f"vcvarsall.bat trouvé : {vcvars_path}")
                    return vcvars_path
        self.logger.warning("vcvarsall.bat introuvable.")
        return None

    def _get_python_version_for_wheel(self) -> str:
        """Retourne la version de Python formatée pour les noms de wheels (ex: cp312)."""
        return f"cp{sys.version_info.major}{sys.version_info.minor}"

    def _try_wheel_install(self, package: str) -> bool:
        """Tente de deviner et d'installer un wheel précompilé."""
        if not sys.platform == 'win32':
            return False

        python_version = self._get_python_version_for_wheel()
        architecture = 'win_amd64' if platform.architecture()[0] == '64bit' else 'win32'
        
        # Heuristique pour JPype1, qui est le cas d'usage principal
        if package.lower() == 'jpype1':
            # Exemple: JPype1-1.5.0-cp312-cp312-win_amd64.whl
            # Note : la version est difficile à deviner, on tente une version commune
            # Idéalement, il faudrait une API pour lister les versions disponibles
            versions_to_try = ["1.5.0", "1.4.1", "1.4.0"]
            for version in versions_to_try:
                wheel_name = f"{package}-{version}-{python_version}-{python_version}-{architecture}.whl"
                # L'URL est une supposition, pointant vers pypi.
                wheel_url = f"https://files.pythonhosted.org/packages/source/J/JPype1/{wheel_name}"
                
                self.logger.info(f"Tentative de téléchargement et installation du wheel: {wheel_url}")
                command = f'pip install "{wheel_url}"'
                if self.run_command_in_conda_env(command) == 0:
                    self.logger.info(f"Succès de l'installation via le wheel précompilé '{wheel_name}'.")
                    return True
        
        self.logger.warning(f"Impossible de deviner un wheel pour le paquet '{package}'.")
        return False

    def _aggressive_fix_for_package(self, package: str) -> bool:
        """Applique une séquence de stratégies de réparation pour un seul paquet."""
        
        # Stratégie 1: Installation simple
        self.logger.info(f"[{package}] Stratégie 1 : Tentative d'installation simple...")
        command1 = f'pip install "{package}"'
        if self.run_command_in_conda_env(command1) == 0:
            self.logger.info(f"[{package}] Succès de l'installation simple.")
            return True
        self.logger.warning(f"[{package}] L'installation simple a échoué. Passage à la stratégie suivante.")

        # Stratégie 2: Installation sans binaire
        self.logger.info(f"[{package}] Stratégie 2 : Tentative d'installation sans binaire...")
        command2 = f'pip install --no-binary :all: "{package}"'
        if self.run_command_in_conda_env(command2) == 0:
            self.logger.info(f"[{package}] Succès de l'installation sans binaire.")
            return True
        self.logger.warning(f"[{package}] L'installation sans binaire a échoué. Passage à la stratégie suivante.")

        # Stratégie 3: Installation via Wheel précompilé (Windows)
        self.logger.info(f"[{package}] Stratégie 3 : Tentative d'installation via un wheel précompilé...")
        if self._try_wheel_install(package):
            return True
        self.logger.warning(f"[{package}] La recherche de wheel précompilé a échoué. Passage à la stratégie suivante.")

        # Stratégie 4: Utilisation de vcvarsall.bat (Windows uniquement)
        if sys.platform == 'win32':
            self.logger.info(f"[{package}] Stratégie 4 : Tentative d'installation avec les outils de compilation MSVC...")
            vcvars_path = self._find_vcvarsall()
            if vcvars_path:
                # La commande doit être exécutée dans un sous-shell qui a initialisé l'environnement de compilation.
                # `conda run` ne peut pas facilement gérer `&&` ici, donc nous construisons une commande shell complète.
                # Note: cette partie est complexe et dépend fortement de la configuration du shell.
                # pour le moment, on se contente de logger une note car la commande est complexe à construire
                self.logger.info(f"Pour une installation manuelle, utilisez une console développeur et lancez :")
                self.logger.info(f'"{vcvars_path}" x64')
                self.logger.info(f'conda activate {self.get_conda_env_name_from_dotenv()}')
                self.logger.info(f'pip install "{package}"')
                self.logger.warning(f"[{package}] La stratégie MSVC automatique n'est pas encore entièrement implémentée. Échec de cette étape.")

            else:
                self.logger.warning(f"[{package}] Outils de compilation MSVC (vcvarsall.bat) introuvables. Échec de cette étape.")

        self.logger.error(f"[{package}] Toutes les stratégies de réparation ont échoué.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gestionnaire d'environnement de projet. Gère les fichiers .env et exécute des commandes dans l'environnement Conda approprié.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles", required=True)

    # --- Commande pour exécuter une commande ---
    run_parser = subparsers.add_parser("run", help="Exécute une commande dans l'environnement Conda configuré via .env.")
    run_parser.add_argument("command_to_run", help="La commande à exécuter, à mettre entre guillemets si elle contient des espaces.")

    # --- Commande pour basculer d'environnement ---
    switch_parser = subparsers.add_parser("switch", help="Bascule vers un autre environnement .env en copiant le fichier de configuration.")
    switch_parser.add_argument("name", help="Le nom de l'environnement à activer (ex: dev, prod). Le fichier correspondant doit exister dans config/environments.")
    
    args = parser.parse_args()

    manager = EnvironmentManager()
    exit_code = 0

    if args.command == "run":
        exit_code = manager.run_command_in_conda_env(args.command_to_run)
    elif args.command == "switch":
        if not manager.switch_environment(args.name):
            exit_code = 1
    else:
        # Ne devrait jamais être atteint grâce à `required=True` sur les subparsers
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)

import shutil
import logging
import argparse
import sys
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
            with open(self.target_env_file, 'r', encoding='utf-8') as f:
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

    def fix_dependencies(self, packages: Optional[List[str]] = None, requirements_file: Optional[str] = None) -> bool:
        """
        Répare les dépendances en les réinstallant.

        Peut fonctionner à partir d'une liste de paquets ou d'un fichier requirements.
        Les deux options sont mutuellement exclusives.

        Args:
            packages: Une liste de noms de paquets à réinstaller.
            requirements_file: Le chemin vers un fichier requirements.txt.

        Returns:
            True si l'opération a réussi, False sinon.
        """
        if packages and requirements_file:
            self.logger.error("Les arguments 'packages' et 'requirements_file' sont mutuellement exclusifs.")
            raise ValueError("Les arguments 'packages' et 'requirements_file' sont mutuellement exclusifs.")

        if not packages and not requirements_file:
            self.logger.warning("Aucun paquet ni fichier de requirements n'a été fourni. Aucune action effectuée.")
            return True

        command_to_run = ""
        if packages:
            package_str = " ".join(packages)
            command_to_run = f"pip install --force-reinstall --no-cache-dir {package_str}"
        
        elif requirements_file:
            # Vérifier si le fichier existe
            if not (self.project_root / requirements_file).is_file():
                self.logger.error(f"Le fichier de requirements '{requirements_file}' est introuvable.")
                return False
            command_to_run = f"pip install -r {requirements_file}"

        if command_to_run:
            self.logger.info(f"Exécution de la commande de réparation de dépendances : {command_to_run}")
            exit_code = self.run_command_in_conda_env(command_to_run)
            return exit_code == 0
        
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

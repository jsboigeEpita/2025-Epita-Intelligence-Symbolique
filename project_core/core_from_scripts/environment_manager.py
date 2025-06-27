"""
Gestionnaire de fichiers d'environnement (.env)

Ce module centralise la logique pour la gestion des fichiers de configuration
d'environnement, permettant de basculer, créer et valider des configurations
stockées dans des fichiers .env.
"""

import shutil
import logging
from pathlib import Path
from typing import Optional, List

# Assumant l'existence de cet utilitaire comme défini dans la roadmap
from argumentation_analysis.core.utils.shell_utils import execute_command

# Configuration du logger
logging.basicConfig(level=logging.INFO, format='[ENV_MGR] [%(asctime)s] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """Gère la création, la validation et le changement de fichiers .env."""

    def __init__(self, project_root: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """
        Initialise le gestionnaire.

        Args:
            project_root: Le chemin racine du projet.
            logger: Le logger à utiliser.
        """
        if project_root and isinstance(project_root, Path):
            self.project_root = project_root
        else:
            self.project_root = Path(__file__).resolve().parent.parent.parent
        
        self.logger = logger or logging.getLogger(__name__)

        self.env_files_dir = self.project_root / "config" / "environments"
        self.template_path = self.project_root / "config" / "templates" / ".env.tpl"
        self.target_env_file = self.project_root / ".env"

    def switch_environment(self, target_name: str) -> bool:
        """
        Bascule l'environnement en copiant un fichier .env de configuration
        vers la racine du projet.

        Args:
            target_name: Le nom de l'environnement à activer (ex: 'dev', 'prod').

        Returns:
            True si le basculement a réussi, False sinon.
        """
        source_path = self.env_files_dir / f"{target_name}.env"
        if not source_path.is_file():
            logger.error(f"Le fichier d'environnement source n'existe pas : {source_path}")
            return False

        try:
            shutil.copy(source_path, self.target_env_file)
            logger.info(f"L'environnement a été basculé vers '{target_name}'.")
            return True
        except IOError as e:
            logger.error(f"Erreur lors de la copie du fichier d'environnement : {e}")
            return False

    def create_environment(self, new_name: str) -> bool:
        """
        Crée un nouveau fichier d'environnement à partir du template.

        Args:
            new_name: Le nom du nouvel environnement.

        Returns:
            True si la création a réussi, False sinon.
        """
        if not self.template_path.is_file():
            logger.error(f"Le template d'environnement n'existe pas : {self.template_path}")
            return False

        new_env_path = self.env_files_dir / f"{new_name}.env"
        if new_env_path.exists():
            logger.warning(f"Le fichier d'environnement '{new_name}' existe déjà. Aucune action n'a été effectuée.")
            return False

        try:
            shutil.copy(self.template_path, new_env_path)
            logger.info(f"Le nouveau fichier d'environnement '{new_name}.env' a été créé.")
            return True
        except IOError as e:
            logger.error(f"Erreur lors de la création du fichier d'environnement : {e}")
            return False

    def validate_environment(self, target_name: str) -> bool:
        """
        Valide qu'un fichier d'environnement contient toutes les clés
        requises par le template.

        Args:
            target_name: Le nom de l'environnement à valider.

        Returns:
            True si l'environnement est valide, False sinon.
        """
        if not self.template_path.is_file():
            logger.error(f"Le template d'environnement n'existe pas : {self.template_path}")
            return False

        target_path = self.env_files_dir / f"{target_name}.env"
        if not target_path.is_file():
            logger.error(f"Le fichier d'environnement à valider n'existe pas : {target_path}")
            return False

        try:
            with open(self.template_path, 'r') as f:
                template_keys = {line.split('=')[0].strip() for line in f if '=' in line and not line.strip().startswith('#')}
            
            with open(target_path, 'r') as f:
                target_keys = {line.split('=')[0].strip() for line in f if '=' in line and not line.strip().startswith('#')}

            missing_keys = template_keys - target_keys
            if missing_keys:
                logger.error(f"Validation échouée. Clés manquantes dans '{target_name}.env': {', '.join(missing_keys)}")
                return False
            
            logger.info(f"Le fichier d'environnement '{target_name}.env' est valide.")
            return True

        except IOError as e:
            logger.error(f"Erreur de lecture lors de la validation : {e}")
            return False

    def fix_dependencies(self, packages: List[str], strategy: str = 'default') -> bool:
        """
        Répare les dépendances Python spécifiées en les réinstallant de force.

        Args:
            packages: Une liste de noms de paquets à réparer.
            strategy: La stratégie d'installation à utiliser (non utilisée dans ce lot).

        Returns:
            True si la commande de réparation a été exécutée avec succès, False sinon.
        """
        if not packages:
            self.logger.warning("Aucun paquet spécifié pour la réparation.")
            return False

        self.logger.info(f"Détection de la version de Python : {sys.version_info.major}.{sys.version_info.minor}")
        
        command = [
            "pip", "install",
            "--force-reinstall",
            "--no-cache-dir"
        ] + packages

        self.logger.info(f"Exécution de la commande de réparation : {' '.join(command)}")

        try:
            # L'utilitaire execute_command est supposé retourner un tuple (stdout, stderr, exit_code)
            stdout, stderr, exit_code = execute_command(' '.join(command))
            
            if exit_code == 0:
                self.logger.info(f"Les paquets {', '.join(packages)} ont été réinstallés avec succès.")
                self.logger.debug(f"Sortie de Pip:\n{stdout}")
                return True
            else:
                self.logger.error(f"Erreur lors de la réinstallation des paquets {', '.join(packages)}.")
                self.logger.error(f"Erreur Pip:\n{stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Une exception est survenue lors de la tentative de réparation des dépendances : {e}")
            return False
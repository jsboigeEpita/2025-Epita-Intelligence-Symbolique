"""
Gestionnaire de fichiers d'environnement (.env)

Ce module centralise la logique pour la gestion des fichiers de configuration
d'environnement, permettant de basculer, créer et valider des configurations
stockées dans des fichiers .env.
"""

import shutil
import logging
from pathlib import Path
from typing import Optional

# Configuration du logger
logging.basicConfig(level=logging.INFO, format='[ENV_MGR] [%(asctime)s] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """Gère la création, la validation et le changement de fichiers .env."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialise le gestionnaire.

        Args:
            project_root: Le chemin racine du projet. S'il n'est pas fourni,
                          il est déduit de l'emplacement de ce fichier.
        """
        if project_root:
            self.project_root = project_root
        else:
            self.project_root = Path(__file__).resolve().parent.parent.parent

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
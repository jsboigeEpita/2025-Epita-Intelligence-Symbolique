import shutil
import sys
import logging
import argparse
import sys
import os
import platform
import importlib
import pkgutil
from pathlib import Path
from typing import Optional, List, Union, Dict, Type

# Importation corrigée pour utiliser l'utilitaire central du projet
from argumentation_analysis.core.utils.shell_utils import run_shell_command
from .strategies.base_strategy import BaseStrategy
from project_core.environment.conda_manager import CondaManager

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
        self._project_root = project_root
        self.logger = logger_instance or logging.getLogger(__name__)
        self.conda_manager = CondaManager(logger=self.logger, project_root=self.project_root)
        self._strategies: Dict[str, BaseStrategy] = {}
        self._load_strategies()

    def check_conda_available(self) -> bool:
        """Vérifie si l'exécutable Conda est disponible."""
        return self.conda_manager._find_conda_executable() is not None

    def check_conda_env_exists(self, env_name: str = "projet-is") -> bool:
        """Vérifie si un environnement Conda spécifique existe."""
        return self.conda_manager.check_conda_env_exists(env_name)

    def check_python_version(self) -> bool:
        """Vérifie la version de Python (simulé pour l'instant)."""
        # TODO: Implémenter une vraie vérification de version si nécessaire.
        return True

    @property
    def project_root(self) -> Path:
        """Retourne la racine du projet, la calculant si nécessaire."""
        if self._project_root is None:
            self._project_root = Path(__file__).resolve().parent.parent.parent
        return self._project_root

    @property
    def env_files_dir(self) -> Path:
        """Retourne le chemin vers le répertoire des fichiers d'environnement."""
        return self.project_root / "config" / "environments"

    @property
    def template_path(self) -> Path:
        """Retourne le chemin vers le template .env."""
        return self.project_root / "config" / "templates" / ".env.tpl"

    @property
    def strategies_dir(self) -> Path:
        """Retourne le chemin vers le répertoire des stratégies."""
        # Chemin corrigé pour pointer vers le répertoire des stratégies local.
        return Path(__file__).resolve().parent / "strategies"

    @property
    def target_env_file(self) -> Path:
        """Retourne le chemin vers le fichier .env cible à la racine du projet."""
        return self.project_root / ".env"

    def get_var_from_dotenv(self, var_name: str) -> Optional[str]:
        """Lit une variable spécifique depuis le fichier .env à la racine."""
        if not self.target_env_file.is_file():
            self.logger.error(f"Le fichier .env cible est introuvable à : {self.target_env_file}")
            return None
        
        try:
            with open(self.target_env_file, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Utiliser startswith pour une correspondance préfixe robuste
                    if line.startswith(f"{var_name}="):
                        value = line.split('=', 1)[1].strip()
                        # Retirer les guillemets optionnels
                        return value.strip('\'"')

            self.logger.warning(f"La variable '{var_name}' n'a pas été trouvée dans {self.target_env_file}")
            return None
        except IOError as e:
            self.logger.error(f"Erreur de lecture du fichier .env pour la variable '{var_name}': {e}")
            return None

    def get_conda_env_name_from_dotenv(self) -> Optional[str]:
        """Lit le nom de l'environnement Conda depuis le fichier .env à la racine."""
        return self.get_var_from_dotenv("CONDA_ENV_NAME")

    def get_java_home_from_dotenv(self) -> Optional[str]:
        """Lit le chemin JAVA_HOME depuis le fichier .env à la racine."""
        return self.get_var_from_dotenv("JAVA_HOME")

    def run_command_in_conda_env(self, command_parts: List[str]) -> int:
        """
        Exécute une commande DANS l'environnement Conda supposément déjà activé.
        Ce script est destiné à être lancé via `conda run`, donc il exécute la commande directement.
        Il configure l'environnement (ex: JAVA_HOME) de manière dynamique si nécessaire.
        """
        # La validation du nom de l'environnement n'est plus nécessaire ici car on est déjà dedans.
        # On garde la logique de configuration des variables d'environnement.
        
        # Préparation des variables d'environnement
        env_vars = os.environ.copy()
        
        # 1. Gestion du PYTHONPATH
        python_path = env_vars.get('PYTHONPATH', '')
        project_root_str = str(self.project_root)
        if project_root_str not in python_path.split(os.pathsep):
            self.logger.info(f"Ajout de {project_root_str} au PYTHONPATH.")
            env_vars['PYTHONPATH'] = f"{project_root_str}{os.pathsep}{python_path}"
            
        # 2. Gestion spécifique pour Pytest (JAVA_HOME)
        if command_parts and 'pytest' in command_parts[0].lower():
            self.logger.info("Détection de 'pytest'. Configuration de l'environnement Java...")
            java_home_path = self.get_java_home_from_dotenv()
            if java_home_path:
                # S'assurer que le chemin est absolu
                if not os.path.isabs(java_home_path):
                    java_home_path = os.path.normpath(os.path.join(self.project_root, java_home_path))
                
                self.logger.info(f"Utilisation de JAVA_HOME: {java_home_path}")
                env_vars['JAVA_HOME'] = java_home_path
                
                # Ajout de JAVA_HOME/bin au PATH
                path_var = env_vars.get('PATH', '')
                java_bin_path = os.path.join(java_home_path, 'bin')
                if java_bin_path not in path_var.split(os.pathsep):
                    self.logger.info(f"Ajout de '{java_bin_path}' au PATH.")
                    env_vars['PATH'] = f"{java_bin_path}{os.pathsep}{path_var}"
            else:
                self.logger.warning("JAVA_HOME n'a pas été trouvé dans le .env. Les tests dépendants de Java pourraient échouer.")

        # La commande à exécuter est directement `command_parts`, car ce script
        # est déjà DANS l'environnement Conda activé par `activate_project_env.ps1`.
        
        command_str = " ".join(command_parts)
        description = f"Exécution de '{command_str[:70]}...' dans l'environnement courant"
        
        # Remplacer 'python' par le chemin complet de l'exécutable python de l'env
        env_name = self.get_conda_env_name_from_dotenv() or "projet-is"
        env_path = self.conda_manager._get_conda_env_path(env_name)
        if not env_path:
            self.logger.error(f"Impossible de trouver le chemin de l'environnement '{env_name}' pour construire le chemin python.")
            return 1
            
        python_exe = str(Path(env_path) / "python.exe")
        
        final_command_parts = [part.replace("python", python_exe, 1) if part == "python" else part for part in command_parts]
        
        exit_code, _, _ = run_shell_command(
            command=final_command_parts,
            description=description,
            capture_output=False,
            shell_mode=False, # Important pour exécuter `pytest` ou `npx` directement
            env=env_vars,
            cwd=self.project_root # S'assurer que la commande s'exécute à la racine
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

    def _load_strategies(self):
        """Charge dynamiquement les stratégies de réparation depuis le répertoire des stratégies."""
        strategies_package = 'project_core.core_from_scripts.strategies'
        if not self.strategies_dir.is_dir():
            self.logger.warning(f"Le répertoire des stratégies '{self.strategies_dir}' est introuvable.")
            return

        for _, module_name, _ in pkgutil.iter_modules([str(self.strategies_dir)]):
            if module_name == 'base_strategy':
                continue
            try:
                module = importlib.import_module(f".{module_name}", package=strategies_package)
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if isinstance(attribute, type) and issubclass(attribute, BaseStrategy) and attribute is not BaseStrategy:
                        strategy_instance = attribute(self)
                        self._strategies[strategy_instance.name] = strategy_instance
                        self.logger.debug(f"Stratégie '{strategy_instance.name}' chargée depuis '{module_name}'.")
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement de la stratégie depuis {module_name}: {e}")

    def fix_dependencies(self, packages: Optional[List[str]] = None, requirements_file: Optional[str] = None, strategy_name: str = 'default') -> bool:
        """
        Répare les dépendances en les réinstallant à l'aide d'un moteur de stratégies.

        Args:
            packages: Une liste de noms de paquets à réinstaller.
            requirements_file: Le chemin vers un fichier requirements.txt.
            strategy_name: Le nom de la stratégie à utiliser ('default', 'aggressive', ou une stratégie spécifique).

        Returns:
            True si l'opération a réussi, False sinon.
        """
        if not self._strategies:
            self.logger.warning("Aucune stratégie de réparation n'a été chargée. Tentative d'installation directe via pip.")
            if requirements_file:
                if not (self.project_root / requirements_file).is_file():
                    self.logger.error(f"Fichier de requirements introuvable: {requirements_file}")
                    return False
                command = f"pip install -r {requirements_file}"
                self.logger.info(f"Exécution de l'installation directe : {command}")
                import shlex
                # Utilise une méthode d'exécution qui ne dépend pas de l'environnement déjà activé,
                # mais qui peut le trouver. `conda_manager.run_in_conda_env` est fait pour ça.
                env_name = self.get_conda_env_name_from_dotenv() or "projet-is"
                result = self.conda_manager.run_in_conda_env(shlex.split(command), env_name=env_name)
                return result.returncode == 0
            else:
                self.logger.error("Aucune stratégie et aucun fichier de requirements fourni. Impossible de continuer.")
                return False

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
            import shlex
            return self.run_command_in_conda_env(shlex.split(command)) == 0

        if packages:
            if strategy_name == 'aggressive':
                return self._run_aggressive_strategy(packages)

            strategy = self._strategies.get(strategy_name)
            if not strategy:
                self.logger.error(f"Stratégie inconnue : '{strategy_name}'. Stratégies disponibles : {', '.join(self._strategies.keys())}")
                return False

            self.logger.info(f"Lancement de la stratégie de réparation '{strategy_name}' pour : {', '.join(packages)}")
            for package in packages:
                if not strategy.execute(package):
                    self.logger.error(f"Échec de la stratégie '{strategy_name}' pour le paquet '{package}'.")
                    return False
            return True

        return False

    def _run_aggressive_strategy(self, packages: List[str]) -> bool:
        """Exécute une séquence prédéfinie de stratégies pour une réparation agressive."""
        self.logger.info(f"Lancement de la stratégie de réparation AGRESSIVE pour : {', '.join(packages)}")
        
        # Ordre d'exécution des stratégies
        strategy_order = ['simple', 'no-binary', 'wheel-install', 'msvc-build']
        
        for package in packages:
            success = False
            for strategy_name in strategy_order:
                strategy = self._strategies.get(strategy_name)
                if not strategy:
                    self.logger.warning(f"Stratégie '{strategy_name}' non trouvée, ignorée.")
                    continue
                
                if strategy.execute(package):
                    self.logger.info(f"Réparation réussie pour '{package}' avec la stratégie '{strategy_name}'.")
                    success = True
                    break # Passe au paquet suivant
            
            if not success:
                self.logger.error(f"Toutes les stratégies agressives ont échoué pour le paquet '{package}'.")
                return False
                
        self.logger.info("Stratégie de réparation agressive terminée avec succès.")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gestionnaire d'environnement de projet. Gère les fichiers .env et exécute des commandes dans l'environnement Conda approprié.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles", required=True)

    # --- Commande pour exécuter une commande ---
    run_parser = subparsers.add_parser("run", help="Exécute une commande dans l'environnement Conda configuré via .env.")
    run_parser.add_argument("command_parts", nargs=argparse.REMAINDER, help="La commande à exécuter et ses arguments.")

    # --- Commande pour basculer d'environnement ---
    switch_parser = subparsers.add_parser("switch", help="Bascule vers un autre environnement .env en copiant le fichier de configuration.")
    switch_parser.add_argument("name", help="Le nom de l'environnement à activer (ex: dev, prod). Le fichier correspondant doit exister dans config/environments.")
    
    # --- Commande pour obtenir le nom de l'environnement ---
    get_name_parser = subparsers.add_parser("get-env-name", help="Affiche le nom de l'environnement Conda configuré dans .env.")

    # --- Nouvelle commande pour la réparation des dépendances ---
    fix_parser = subparsers.add_parser("fix", help="Répare les dépendances d'un ou plusieurs paquets.")
    fix_parser.add_argument("packages", nargs='*', help="Liste des paquets à réparer.")
    fix_parser.add_argument("-r", "--requirements", dest="requirements_file", help="Chemin vers un fichier requirements.txt.")
    fix_parser.add_argument("-s", "--strategy", default="default", help="La stratégie de réparation à utiliser (ex: default, aggressive, simple, no-binary).")


    args = parser.parse_args()

    manager = EnvironmentManager()
    exit_code = 0

    if args.command == "run":
        if not args.command_parts:
            logger.error("Aucune commande fournie pour l'action 'run'.")
            parser.print_help()
            exit_code = 1
        else:
            # Si la commande est passée comme une seule chaîne (ex: "pip install tenacity"),
            # argparse.REMAINDER la capture comme ['pip install tenacity'].
            # On la divise en ['pip', 'install', 'tenacity'] pour la passer correctement à subprocess.
            import shlex
            
            command_to_run = args.command_parts
            if len(command_to_run) == 1 and ' ' in command_to_run[0]:
                logger.info(f"La commande '{command_to_run[0]}' semble être une chaîne unique, division avec shlex (mode non-posix pour Windows).")
                command_to_run = shlex.split(command_to_run[0], posix=False)

            exit_code = manager.run_command_in_conda_env(command_to_run)
    elif args.command == "switch":
        if not manager.switch_environment(args.name):
            exit_code = 1
    elif args.command == "get-env-name":
        env_name = manager.get_conda_env_name_from_dotenv()
        if env_name:
            print(env_name)
            exit_code = 0
        else:
            exit_code = 1
    elif args.command == "fix":
        if not manager.fix_dependencies(args.packages, args.requirements_file, args.strategy):
            exit_code = 1
    else:
        # Ne devrait jamais être atteint grâce à `required=True` sur les subparsers
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)

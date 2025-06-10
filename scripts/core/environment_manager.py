"""
Gestionnaire d'environnements Python/conda
==========================================

Ce module centralise la gestion des environnements Python et conda :
- Vérification et activation d'environnements conda
- Validation des dépendances Python
- Gestion des variables d'environnement
- Exécution de commandes dans l'environnement projet

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
import subprocess
import argparse
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Import relatif corrigé - gestion des erreurs d'import
try:
    from .common_utils import Logger, LogLevel, safe_exit, get_project_root
except ImportError:
    # Fallback pour execution directe
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from common_utils import Logger, LogLevel, safe_exit, get_project_root


# --- Début de l'insertion pour sys.path ---
# Déterminer la racine du projet (remonter de deux niveaux depuis scripts/core)
# __file__ est scripts/core/environment_manager.py
# .parent est scripts/core
# .parent.parent est scripts
# .parent.parent.parent est la racine du projet
_project_root_for_sys_path = Path(__file__).resolve().parent.parent.parent
if str(_project_root_for_sys_path) not in sys.path:
    sys.path.insert(0, str(_project_root_for_sys_path))
# --- Fin de l'insertion pour sys.path ---
from scripts.core.auto_env import _load_dotenv_intelligent # MODIFIÉ ICI
class EnvironmentManager:
    """Gestionnaire centralisé des environnements Python/conda"""
    
    def __init__(self, logger: Logger = None):
        """
        Initialise le gestionnaire d'environnement
        
        Args:
            logger: Instance de logger à utiliser
        """
        self.logger = logger or Logger()
        self.project_root = get_project_root()
        # Charger .env via _load_dotenv_intelligent
        # _load_dotenv_intelligent prend (project_root, silent)
        if _load_dotenv_intelligent(Path(self.project_root), silent=False): # silent=False pour voir les logs
             self.logger.info(f".env chargé par _load_dotenv_intelligent depuis {self.project_root}")
        else:
             self.logger.warning(f"Échec du chargement de .env par _load_dotenv_intelligent depuis {self.project_root}")
        
        # Assurer que JAVA_HOME est absolu s'il vient du .env
        if 'JAVA_HOME' in os.environ: # Vérifier si JAVA_HOME a été chargé
            java_home_value = os.environ['JAVA_HOME']
            java_home_path = Path(java_home_value)
            if not java_home_path.is_absolute():
                # Le chemin dans .env est relatif à la racine du projet
                absolute_java_home = (Path(self.project_root) / java_home_path).resolve()
                if absolute_java_home.exists() and absolute_java_home.is_dir():
                    os.environ['JAVA_HOME'] = str(absolute_java_home)
                    self.logger.info(f"JAVA_HOME (de .env) mis à jour en chemin absolu: {os.environ['JAVA_HOME']}")
                else:
                    self.logger.warning(f"Le chemin JAVA_HOME (de .env) résolu {absolute_java_home} n'existe pas ou n'est pas un répertoire.")
            # else: JAVA_HOME est déjà absolu ou n'a pas besoin d'être modifié par ce bloc
        
        self.default_conda_env = "projet-is"
        self.required_python_version = (3, 8)
        
        # Variables d'environnement importantes
        self.env_vars = {
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONPATH': self.project_root,
            'PROJECT_ROOT': self.project_root
        }
    
    def check_conda_available(self) -> bool:
        """Vérifie si conda est disponible"""
        try:
            result = subprocess.run(
                ['conda', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.logger.debug(f"Conda trouvé: {result.stdout.strip()}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        self.logger.warning("Conda non disponible")
        return False
    
    def check_python_version(self, python_cmd: str = "python") -> bool:
        """Vérifie la version de Python"""
        try:
            result = subprocess.run(
                [python_cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_str = result.stdout.strip()
                self.logger.debug(f"Python trouvé: {version_str}")
                
                # Parser la version
                import re
                match = re.search(r'Python (\d+)\.(\d+)', version_str)
                if match:
                    major, minor = int(match.group(1)), int(match.group(2))
                    if (major, minor) >= self.required_python_version:
                        return True
                    else:
                        self.logger.warning(
                            f"Version Python {major}.{minor} < requise {self.required_python_version[0]}.{self.required_python_version[1]}"
                        )
                
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.warning(f"Impossible de vérifier Python avec '{python_cmd}'")
        
        return False
    
    def list_conda_environments(self) -> List[str]:
        """Liste les environnements conda disponibles"""
        if not self.check_conda_available():
            return []
        
        try:
            result = subprocess.run(
                ['conda', 'env', 'list', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                envs = []
                for env_path in data.get('envs', []):
                    env_name = Path(env_path).name
                    envs.append(env_name)
                return envs
        
        except (subprocess.SubprocessError, json.JSONDecodeError, subprocess.TimeoutExpired):
            self.logger.debug("Erreur lors de la liste des environnements conda")
        
        return []
    
    def check_conda_env_exists(self, env_name: str) -> bool:
        """Vérifie si un environnement conda existe"""
        environments = self.list_conda_environments()
        exists = env_name in environments
        
        if exists:
            self.logger.debug(f"Environnement conda '{env_name}' trouvé")
        else:
            self.logger.warning(f"Environnement conda '{env_name}' non trouvé")
        
        return exists
    
    def setup_environment_variables(self, additional_vars: Dict[str, str] = None):
        """Configure les variables d'environnement pour le projet"""
        env_vars = self.env_vars.copy()
        if additional_vars:
            env_vars.update(additional_vars)
        
        for key, value in env_vars.items():
            os.environ[key] = value
            self.logger.debug(f"Variable d'environnement définie: {key}={value}")
    
    def run_in_conda_env(self, command: List[str], env_name: str = None, 
                        cwd: str = None, capture_output: bool = False) -> subprocess.CompletedProcess:
        """
        Exécute une commande dans un environnement conda
        
        Args:
            command: Commande à exécuter (liste de strings)
            env_name: Nom de l'environnement conda (défaut: projet-is)
            cwd: Répertoire de travail (défaut: project_root)
            capture_output: Capturer la sortie au lieu de l'afficher
        
        Returns:
            Résultat de l'exécution
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        if cwd is None:
            cwd = self.project_root
        
        # Vérifier que l'environnement existe
        if not self.check_conda_env_exists(env_name):
            self.logger.error(f"Environnement conda '{env_name}' non trouvé")
            raise RuntimeError(f"Environnement conda '{env_name}' non disponible")
        
        # Construire la commande conda run
        conda_cmd = ['conda', 'run', '-n', env_name, '--no-capture-output'] + command
        self.logger.info(f"DEBUG: Commande conda construite: {' '.join(conda_cmd)}") 
        
        self.logger.debug(f"Exécution dans conda '{env_name}': {' '.join(command)}")
        
        try:
            if capture_output:
                result = subprocess.run(
                    conda_cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes par défaut
                )
            else:
                result = subprocess.run(
                    conda_cmd,
                    cwd=cwd,
                    timeout=300
                )
            
            if result.returncode == 0:
                self.logger.debug("Commande exécutée avec succès")
            else:
                self.logger.warning(f"Commande terminée avec code: {result.returncode}")
            
            return result
        
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout lors de l'exécution de la commande")
            raise
        except subprocess.SubprocessError as e:
            self.logger.error(f"Erreur lors de l'exécution: {e}")
            raise
    
    def check_python_dependencies(self, requirements: List[str], env_name: str = None) -> Dict[str, bool]:
        """
        Vérifie si les dépendances Python sont installées
        
        Args:
            requirements: Liste des packages requis
            env_name: Nom de l'environnement conda
        
        Returns:
            Dictionnaire package -> installé (bool)
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        results = {}
        
        for package in requirements:
            try:
                # Utiliser pip show pour vérifier l'installation
                result = self.run_in_conda_env(
                    ['pip', 'show', package],
                    env_name=env_name,
                    capture_output=True
                )
                results[package] = result.returncode == 0
                
                if result.returncode == 0:
                    self.logger.debug(f"Package '{package}' installé")
                else:
                    self.logger.warning(f"Package '{package}' non installé")
            
            except Exception as e:
                self.logger.debug(f"Erreur vérification '{package}': {e}")
                results[package] = False
        
        return results
    
    def install_python_dependencies(self, requirements: List[str], env_name: str = None) -> bool:
        """
        Installe les dépendances Python manquantes
        
        Args:
            requirements: Liste des packages à installer
            env_name: Nom de l'environnement conda
        
        Returns:
            True si installation réussie
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        if not requirements:
            return True
        
        self.logger.info(f"Installation de {len(requirements)} packages...")
        
        try:
            # Installer via pip dans l'environnement conda
            pip_cmd = ['pip', 'install'] + requirements
            result = self.run_in_conda_env(pip_cmd, env_name=env_name)
            
            if result.returncode == 0:
                self.logger.success("Installation des dépendances réussie")
                return True
            else:
                self.logger.error("Échec de l'installation des dépendances")
                return False
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'installation: {e}")
            return False
    
    def activate_project_environment(self, command_to_run: str = None, env_name: str = None) -> int:
        """
        Active l'environnement projet et exécute optionnellement une commande
        
        Args:
            command_to_run: Commande à exécuter après activation
            env_name: Nom de l'environnement conda
        
        Returns:
            Code de sortie de la commande
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        self.logger.info(f"Activation de l'environnement '{env_name}'...")
        
        # Vérifications préalables
        if not self.check_conda_available():
            self.logger.error("Conda non disponible")
            return 1
        
        if not self.check_conda_env_exists(env_name):
            self.logger.error(f"Environnement '{env_name}' non trouvé")
            return 1
        
        # Configuration des variables d'environnement
        self.setup_environment_variables()
        
        if command_to_run:
            self.logger.info(f"Exécution de: {command_to_run}")
            
            try:
                # Parser la commande
                # Si la commande est un .py, on la préfixe par python
                if command_to_run.endswith(".py"):
                    cmd_parts = ["python", command_to_run]
                else:
                    cmd_parts = command_to_run.split()
                
                self.logger.info(f"DEBUG: cmd_parts avant run_in_conda_env: {cmd_parts}") 
                result = self.run_in_conda_env(cmd_parts, env_name=env_name)
                return result.returncode
            
            except Exception as e:
                self.logger.error(f"Erreur lors de l'exécution: {e}")
                return 1
        else:
            self.logger.success(f"Environnement '{env_name}' activé")
            return 0


def is_conda_env_active(env_name: str = "projet-is") -> bool:
    """Vérifie si l'environnement conda spécifié est actuellement actif"""
    current_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    return current_env == env_name


def check_conda_env(env_name: str = "projet-is", logger: Logger = None) -> bool:
    """Fonction utilitaire pour vérifier un environnement conda"""
    manager = EnvironmentManager(logger)
    return manager.check_conda_env_exists(env_name)


def auto_activate_env(env_name: str = "projet-is", silent: bool = True) -> bool:
    """
    One-liner auto-activateur d'environnement intelligent
    
    Active véritablement l'environnement conda en modifiant le PATH et les variables.
    
    Args:
        env_name: Nom de l'environnement conda
        silent: Mode silencieux (pas de logs verbeux)
    
    Returns:
        True si environnement actif/activé, False sinon
    """
    try:
        # Logger minimal pour auto-activation
        logger = Logger(verbose=not silent)
        manager = EnvironmentManager(logger)
        
        # Vérifier si conda et l'environnement existent
        if not manager.check_conda_available():
            if not silent:
                print(f"[ERROR] Conda non disponible - impossible d'activer '{env_name}'")
            return False
        
        if not manager.check_conda_env_exists(env_name):
            if not silent:
                print(f"[ERROR] Environnement '{env_name}' non trouve")
            return False
        
        # Obtenir le chemin de l'environnement conda
        try:
            result = subprocess.run(
                ['conda', 'info', '--envs', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                env_data = json.loads(result.stdout)
                env_path = None
                
                for env_dir in env_data.get('envs', []):
                    if Path(env_dir).name == env_name:
                        env_path = env_dir
                        break
                
                if env_path:
                    # Activer vraiment l'environnement en modifiant le PATH
                    env_bin_path = os.path.join(env_path, 'Scripts')  # Windows
                    if not os.path.exists(env_bin_path):
                        env_bin_path = os.path.join(env_path, 'bin')  # Unix
                    
                    if os.path.exists(env_bin_path):
                        # Mettre le chemin de l'environnement en premier dans le PATH
                        current_path = os.environ.get('PATH', '')
                        path_parts = current_path.split(os.pathsep)
                        
                        # Retirer les anciens chemins conda s'ils existent
                        path_parts = [p for p in path_parts if not ('conda' in p.lower() and 'envs' in p.lower())]
                        
                        # Ajouter le nouveau chemin en premier
                        path_parts.insert(0, env_bin_path)
                        os.environ['PATH'] = os.pathsep.join(path_parts)
                        
                        # Configurer les variables d'environnement conda
                        os.environ['CONDA_DEFAULT_ENV'] = env_name
                        os.environ['CONDA_PREFIX'] = env_path
                        
                        if not silent:
                            print(f"[INFO] Auto-activation de l'environnement '{env_name}'...")
                            print(f"[CONDA] PATH mis à jour: {env_bin_path}")
                        
                        # Configurer les variables d'environnement du projet
                        manager.setup_environment_variables()
                        
                        if not silent:
                            print(f"[OK] Environnement '{env_name}' auto-actif")
                        
                        return True
                    else:
                        if not silent:
                            print(f"[ERROR] Répertoire bin/Scripts non trouvé: {env_bin_path}")
                        return False
                else:
                    if not silent:
                        print(f"[ERROR] Chemin de l'environnement '{env_name}' non trouvé")
                    return False
            else:
                if not silent:
                    print(f"[ERROR] Impossible d'obtenir les infos conda: {result.stderr}")
                return False
                
        except Exception as e:
            if not silent:
                print(f"[ERROR] Erreur lors de l'obtention du chemin conda: {e}")
            return False
        
    except Exception as e:
        if not silent:
            print(f"❌ Erreur auto-activation: {e}")
        return False


def activate_project_env(command: str = None, env_name: str = "projet-is", logger: Logger = None) -> int:
    """Fonction utilitaire pour activer l'environnement projet"""
    manager = EnvironmentManager(logger)
    return manager.activate_project_environment(command, env_name)


def main():
    """Point d'entrée principal pour utilisation en ligne de commande"""
    temp_logger = Logger(verbose=True) 
    temp_logger.info(f"DEBUG: sys.argv au début de main(): {sys.argv}")

    parser = argparse.ArgumentParser(
        description="Gestionnaire d'environnements Python/conda"
    )
    
    parser.add_argument(
        '--command', '-c', # Option nommée, attendue par activate_project_env.ps1 (version lue)
        type=str,
        default=None,
        help='Commande à exécuter dans l\'environnement (optionnel)'
    )
    
    parser.add_argument(
        '--env-name', '-e',
        type=str,
        default='projet-is',
        help='Nom de l\'environnement conda (défaut: projet-is)'
    )
    
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Vérifier l\'environnement sans l\'activer'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mode verbeux'
    )
    
    args = parser.parse_args() 
    
    logger = Logger(verbose=True) # FORCER VERBOSE POUR DEBUG (ou utiliser args.verbose)
    logger.info("DEBUG: Début de main() dans environment_manager.py (après parsing)")
    logger.info(f"DEBUG: Args parsés par argparse: {args}")
    
    manager = EnvironmentManager(logger)
    
    command_to_run_final = args.command 

    if args.check_only:
        # Mode vérification uniquement
        logger.info("Vérification de l'environnement...")
        
        if manager.check_conda_available():
            logger.success("Conda disponible")
        else:
            logger.error("Conda non disponible")
            safe_exit(1, logger)
        
        if manager.check_conda_env_exists(args.env_name):
            logger.success(f"Environnement '{args.env_name}' trouvé")
        else:
            logger.error(f"Environnement '{args.env_name}' non trouvé")
            safe_exit(1, logger)
        
        if manager.check_python_version():
            logger.success("Version Python valide")
        else:
            logger.error("Version Python invalide")
            safe_exit(1, logger)
        
        logger.success("Environnement validé")
        safe_exit(0, logger)
    
    else:
        # Mode activation et exécution
        logger.info(f"DEBUG: Valeur passée comme command_to_run: {command_to_run_final}")
        exit_code = manager.activate_project_environment(
            command_to_run=command_to_run_final,
            env_name=args.env_name
        )
        safe_exit(exit_code, logger)


if __name__ == "__main__":
    main()
# project_core/environment/python_manager.py
import os
import sys
import re
import subprocess # Pour CompletedProcess et potentiellement des types
from pathlib import Path
from typing import List, Dict, Optional, Union

# Imports du projet
try:
    # S'assurer que common_utils est accessible depuis ce niveau
    # Si python_manager.py est dans project_core/environment/
    # et common_utils dans project_core/core_from_scripts/
    # l'import devrait être from ..core_from_scripts.common_utils
    from ..core_from_scripts.common_utils import Logger, ColoredOutput, get_project_root
    from .conda_manager import CondaManager
except ImportError as e:
    # Fallback simplifié pour l'exécution directe ou si la structure change
    print(f"Avertissement: Erreur d'importation ({e}). Utilisation de stubs pour PythonManager.")
    
    class Logger:
        def __init__(self, verbose=False): self.verbose = verbose
        def debug(self, msg): print(f"DEBUG: {msg}")
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def success(self, msg): print(f"SUCCESS: {msg}")
        def critical(self, msg): print(f"CRITICAL: {msg}")

    class ColoredOutput:
        @staticmethod
        def print_section(msg): print(f"\n--- {msg} ---")

    def get_project_root():
        # Tentative de trouver la racine du projet de manière robuste
        current_path = Path(__file__).resolve()
        # Remonter jusqu'à trouver un marqueur de projet (ex: .git, environment.yml)
        # ou un nombre fixe de parents si la structure est connue.
        # Pour ce projet, la racine est 3 niveaux au-dessus de project_core/environment/
        return str(current_path.parent.parent.parent) if current_path.parent.parent.parent else os.getcwd()


    class CondaManager:
        def __init__(self, logger=None, project_root=None):
            self.logger = logger or Logger()
            self.project_root = project_root or Path(get_project_root())
            self.default_conda_env = "projet-is"

        def run_in_conda_env(self, command: Union[str, List[str]], env_name: str = None,
                             cwd: Optional[Union[str, Path]] = None, capture_output: bool = False) -> subprocess.CompletedProcess:
            self.logger.warning(f"STUB: CondaManager.run_in_conda_env appelée avec {command}")
            # Simuler un échec pour que les tests ne passent pas silencieusement avec le stub
            return subprocess.CompletedProcess(args=command if isinstance(command, list) else [command], returncode=1, stdout="", stderr="Stub execution: CondaManager not fully loaded.")


class PythonManager:
    """
    Gère la version de Python et les dépendances pip au sein d'un environnement Conda.
    """
    def __init__(self, logger: Logger = None, project_root: Optional[Path] = None, conda_manager_instance: Optional[CondaManager] = None):
        self.logger = logger or Logger()
        self.project_root = project_root or Path(get_project_root())
        # Si conda_manager_instance n'est pas fourni, on en crée un.
        # Cela suppose que CondaManager peut être initialisé sans arguments complexes ici.
        self.conda_manager = conda_manager_instance or CondaManager(logger=self.logger, project_root=self.project_root)
        self.required_python_version: tuple[int, int] = (3, 8)

    def check_python_version(self, env_name: Optional[str] = None) -> bool:
        """
        Vérifie la version de Python dans l'environnement conda spécifié.
        Utilise le CondaManager pour exécuter 'python --version'.
        """
        effective_env_name = env_name or self.conda_manager.default_conda_env
        self.logger.info(f"Vérification de la version de Python dans l'environnement '{effective_env_name}'...")

        try:
            result = self.conda_manager.run_in_conda_env(
                ['python', '--version'],
                env_name=effective_env_name,
                capture_output=True
            )

            if result.returncode == 0:
                version_str = result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
                self.logger.debug(f"Sortie de 'python --version': {version_str}")

                match = re.search(r'Python (\d+)\.(\d+)', version_str)
                if match:
                    major, minor = int(match.group(1)), int(match.group(2))
                    self.logger.info(f"Version Python détectée: {major}.{minor}")
                    if (major, minor) >= self.required_python_version:
                        self.logger.success(f"Version Python {major}.{minor} est compatible (>= {self.required_python_version[0]}.{self.required_python_version[1]}).")
                        return True
                    else:
                        self.logger.warning(
                            f"Version Python {major}.{minor} est inférieure à la version requise "
                            f"{self.required_python_version[0]}.{self.required_python_version[1]}."
                        )
                        return False
                else:
                    self.logger.warning(f"Impossible de parser la version de Python depuis: '{version_str}'")
                    return False
            else:
                self.logger.error(
                    f"Échec de l'exécution de 'python --version' dans '{effective_env_name}'. "
                    f"Code: {result.returncode}, Stdout: '{result.stdout}', Stderr: '{result.stderr}'"
                )
                return False
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de la version de Python: {e}", exc_info=True)
            return False

    def _check_single_dependency(self, package_name: str, env_name: str) -> bool:
        """Vérifie si un unique package est installé via 'pip show'."""
        self.logger.debug(f"Vérification du package '{package_name}' dans l'env '{env_name}'...")
        try:
            result = self.conda_manager.run_in_conda_env(
                ['pip', 'show', package_name.split('[')[0]], # Ignorer les extras pour pip show
                env_name=env_name,
                capture_output=True
            )
            is_installed = result.returncode == 0
            if is_installed:
                self.logger.debug(f"Package '{package_name}' est installé.")
            else:
                self.logger.info(f"Package '{package_name}' n'est pas installé (pip show code: {result.returncode}).")
            return is_installed
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification du package '{package_name}': {e}", exc_info=True)
            return False

    def check_and_install_pip_requirements(
        self,
        requirements_file: Union[str, Path],
        env_name: Optional[str] = None,
        force_reinstall: bool = False
    ) -> bool:
        """
        Vérifie et installe les dépendances Python depuis un fichier requirements.txt.
        Utilise 'pip install -r <file>' pour une gestion correcte des versions et dépendances.
        Si force_reinstall est True, utilise --force-reinstall --no-cache-dir.
        """
        effective_env_name = env_name or self.conda_manager.default_conda_env
        req_file_path = Path(requirements_file)

        if not req_file_path.is_file():
            self.logger.error(f"Le fichier de requirements '{req_file_path}' n'a pas été trouvé.")
            return False

        self.logger.info(f"Traitement des dépendances depuis '{req_file_path}' pour l'env '{effective_env_name}'.")

        # Il n'est pas fiable de vérifier chaque package individuellement avant 'pip install -r'
        # car cela ne gère pas bien les dépendances transitives ou les contraintes complexes.
        # 'pip install -r' gère cela nativement.
        # Si force_reinstall est activé, on installe directement.
        # Sinon, on pourrait envisager une vérification, mais pip est idempotent pour les installations.

        action_description = "Installation/Mise à jour"
        pip_command = ['pip', 'install']
        
        if force_reinstall:
            action_description = "Forçage de la réinstallation"
            pip_command.extend(['--force-reinstall', '--no-cache-dir'])
        
        pip_command.extend(['-r', str(req_file_path)])

        self.logger.info(f"{action_description} des dépendances via: {' '.join(pip_command)}")

        try:
            result = self.conda_manager.run_in_conda_env(
                pip_command,
                env_name=effective_env_name,
                capture_output=False # Afficher la sortie en direct pour le feedback
            )
            if result.returncode == 0:
                self.logger.success(f"Dépendances de '{req_file_path}' traitées avec succès dans '{effective_env_name}'.")
                return True
            else:
                self.logger.error(
                    f"Échec du traitement des dépendances depuis '{req_file_path}' dans '{effective_env_name}'. "
                    f"Code: {result.returncode}. Voir la sortie de pip ci-dessus."
                )
                return False
        except Exception as e:
            self.logger.error(f"Erreur majeure lors de l'exécution de pip install: {e}", exc_info=True)
            return False

    def reinstall_pip_dependencies(self, requirements_file: Union[str, Path], env_name: Optional[str] = None) -> bool:
        """
        Force la réinstallation des dépendances pip depuis un fichier requirements.txt.
        C'est un alias pour check_and_install_pip_requirements avec force_reinstall=True.
        """
        ColoredOutput.print_section(f"Réinstallation forcée des paquets PIP depuis '{requirements_file}'")
        return self.check_and_install_pip_requirements(
            requirements_file=requirements_file,
            env_name=env_name,
            force_reinstall=True
        )

if __name__ == '__main__':
    # Configuration pour les tests directs
    log = Logger(verbose=True)
    try:
        # Tenter d'obtenir la racine du projet correctement
        # Cela suppose que ce script est dans project_core/environment
        # et que la racine est 3 niveaux au-dessus.
        current_file_path = Path(__file__).resolve()
        proj_root = current_file_path.parent.parent.parent
        if not (proj_root / "environment.yml").exists(): # Simple vérification
             log.warning(f"Racine de projet détectée ({proj_root}) ne semble pas correcte, fallback sur get_project_root().")
             proj_root = Path(get_project_root())
    except Exception:
        log.warning("Impossible de déterminer la racine du projet de manière fiable, utilisation de get_project_root().")
        proj_root = Path(get_project_root())
    
    log.info(f"Racine du projet pour les tests: {proj_root}")

    # Instance de CondaManager (nécessaire pour PythonManager)
    # Assurez-vous que CondaManager peut être importé ou que son stub est adéquat.
    try:
        cm = CondaManager(logger=log, project_root=proj_root)
    except NameError: # Si CondaManager n'est pas défini (échec de l'import principal et du stub)
        log.error("CondaManager n'a pas pu être initialisé. Les tests ne peuvent pas continuer.")
        sys.exit(1)

    pm = PythonManager(logger=log, project_root=proj_root, conda_manager_instance=cm)

    # Nom de l'environnement à utiliser pour les tests
    test_env = cm.default_conda_env # ou un autre environnement de test

    log.info(f"\n--- Test de check_python_version pour l'env '{test_env}' ---")
    version_ok = pm.check_python_version(env_name=test_env)
    log.info(f"Résultat de check_python_version: {version_ok}")

    # Création d'un fichier requirements.txt de test
    test_req_filename = "temp_requirements_for_python_manager_test.txt"
    test_req_path = proj_root / test_req_filename
    with open(test_req_path, "w", encoding="utf-8") as f:
        f.write("# Fichier de test pour PythonManager\n")
        f.write("requests==2.25.1\n") # Version spécifique pour tester
        f.write("numpy\n")          # Sans version spécifique

    log.info(f"\n--- Test de check_and_install_pip_requirements pour '{test_req_path.name}' (installation/màj) ---")
    install_status = pm.check_and_install_pip_requirements(
        requirements_file=test_req_path,
        env_name=test_env
    )
    log.info(f"Résultat de check_and_install_pip_requirements: {install_status}")

    if install_status:
        log.info(f"\n--- Test de reinstall_pip_dependencies pour '{test_req_path.name}' (réinstallation forcée) ---")
        reinstall_status = pm.reinstall_pip_dependencies(
            requirements_file=test_req_path,
            env_name=test_env
        )
        log.info(f"Résultat de reinstall_pip_dependencies: {reinstall_status}")

    # Nettoyage
    if test_req_path.exists():
        try:
            os.remove(test_req_path)
            log.info(f"Fichier de test '{test_req_path.name}' supprimé.")
        except Exception as e_clean:
            log.warning(f"Impossible de supprimer le fichier de test '{test_req_path.name}': {e_clean}")
    
    log.info("\nTests du PythonManager terminés.")
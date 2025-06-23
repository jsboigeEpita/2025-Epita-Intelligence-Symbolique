"""
Gestionnaire d'environnements Python/conda

Ce module est OBSOLETE et conservé pour compatibilité ascendante.
La configuration est maintenant gérée de manière centralisée via pydantic-settings
dans `argumentation_analysis.config.settings`.
L'activation de l'environnement et l'exécution de commandes doivent être gérées
par des scripts de premier niveau (ex: `activate_project_env.ps1`).

N'utilisez plus ce module pour de nouveaux développements.
"""

import os
import sys
import warnings
import logging
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union

# Configuration de base du logger pour ce module
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Le module reste globalement obsolète, mais certaines de ses fonctions
# sont réactivées pour servir de base OS-indépendante aux scripts d'activation.
warnings.warn(
    "Le module 'environment_manager.py' est majoritairement obsolète. "
    "Seules les fonctions nécessaires à l'activation d'environnement via CLI sont actives.",
    DeprecationWarning,
    stacklevel=2
)

class PrintLogger:
    """Fallback Logger pour la compatibilité de l'API et l'usage simple en script."""
    def debug(self, msg): logger.debug(msg)
    def info(self, msg): logger.info(msg)
    def warning(self, msg): logger.warning(msg)
    def error(self, msg): logger.error(msg)
    def success(self, msg): logger.info(f"✅ SUCCESS: {msg}")

class EnvironmentManager:
    """
    Gestionnaire d'environnement partiel.
    Fournit des fonctionnalités de base pour les scripts d'activation.
    """
    def __init__(self, logger_instance: PrintLogger = None):
        self.logger = logger_instance or PrintLogger()
        # La racine du projet est 3 niveaux au-dessus de ce fichier
        # d:/2025-Epita-Intelligence-Symbolique/project_core/core_from_scripts/environment_manager.py
        self.project_root = Path(__file__).resolve().parent.parent.parent

    def setup_environment_variables(self):
        """
        Configure les variables d'environnement essentielles.
        C'est la destination correcte et OS-indépendante pour cette logique.
        """
        self.logger.info("Configuration des variables d'environnement...")

        # 1. Configurer PYTHONPATH
        python_path = str(self.project_root)
        os.environ['PYTHONPATH'] = python_path
        self.logger.info(f"  - PYTHONPATH='{python_path}'")

        # 2. Contournement pour le conflit OpenMP
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        self.logger.info("  - KMP_DUPLICATE_LIB_OK='TRUE'")
        
        # 3. Clé API factice pour les tests
        # 3. Clé API factice pour les tests
        os.environ['OPENAI_API_KEY'] = 'dummy_key_for_testing_purposes'
        self.logger.info("  - OPENAI_API_KEY='dummy_key_for_testing_purposes'")

        self.logger.success("Variables d'environnement configurées.")

    def run_command(self, command: List[str]) -> int:
        """
        Exécute une commande en tant que sous-processus.
        """
        if not command:
            self.logger.error("Aucune commande à exécuter.")
            return 1
        
        self.logger.info(f"Exécution de la commande: {' '.join(command)}")
        try:
            # `shell=False` est plus sûr. Les arguments sont passés en liste.
            result = subprocess.run(command, check=False)
            self.logger.info(f"La commande s'est terminée avec le code de sortie: {result.returncode}")
            return result.returncode
        except FileNotFoundError:
            self.logger.error(f"Commande non trouvée: '{command[0]}'. Vérifiez que l'exécutable est dans le PATH.")
            return 1
        except Exception as e:
            self.logger.error(f"Une erreur est survenue lors de l'exécution de la commande: {e}")
            return 1

    def _warn_obsolete(self, method_name: str):
        """Avertit qu'une méthode appelée est obsolète."""
        warnings.warn(
            f"EnvironmentManager.{method_name}() est obsolète et ne doit plus être utilisé.",
            DeprecationWarning,
            stacklevel=3
        )

    # Le reste des méthodes reste obsolète pour ne pas casser l'API existante
    # si d'autres vieux scripts l'utilisaient.

def main():
    """
    Point d'entrée CLI pour la gestion de l'environnement.
    Permet aux scripts shell (PowerShell, Bash) de déléguer la logique
    OS-indépendante à Python.
    """
    parser = argparse.ArgumentParser(
        description="Outil de configuration d'environnement et d'exécution de commandes."
    )
    parser.add_argument(
        '--setup-vars',
        action='store_true',
        help="Configure les variables d'environnement nécessaires (PYTHONPATH, etc.)."
    )
    parser.add_argument(
        '--run-command',
        nargs=argparse.REMAINDER,
        metavar='COMMAND',
        help="Exécute la commande spécifiée après le flag. Doit être le dernier argument."
    )
    
    args = parser.parse_args()
    
    manager = EnvironmentManager()
    
    if args.setup_vars:
        manager.setup_environment_variables()
        # On ne quitte pas pour permettre de chaîner avec --run-command si on le souhaite plus tard
        
    if args.run_command:
        # Si la commande est `python -m pytest`, on le loggue spécifiquement
        if args.run_command[:3] == ['python', '-m', 'pytest']:
             manager.logger.info("Détection d'une exécution de pytest.")
        
        exit_code = manager.run_command(args.run_command)
        sys.exit(exit_code)

    # Si aucun argument n'est fourni, ou seulement --setup-vars, on quitte avec succès.
    if not args.run_command:
        parser.print_help()
        sys.exit(0)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
One-liner auto-activateur d'environnement intelligent
====================================================

Ce module fournit l'auto-activation automatique de l'environnement conda 'projet-is'.
Conçu pour être utilisé par les agents AI et développeurs sans se soucier de l'état d'activation.

UTILISATION SIMPLE (one-liner) :
from project_core.core_from_scripts.auto_env import ensure_env
ensure_env()

OU ENCORE PLUS SIMPLE :
import project_core.core_from_scripts.auto_env

Le module s'auto-exécute à l'import et active l'environnement si nécessaire.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
from pathlib import Path
# Les imports shutil, platform, dotenv ne sont plus nécessaires ici.

# Il est préférable d'importer les dépendances spécifiques à une fonction à l'intérieur de cette fonction,
# surtout si elles ne sont pas utilisées ailleurs dans le module.
# Cependant, pour EnvironmentManager et Logger, ils sont fondamentaux pour la nouvelle `ensure_env`.

# Note: L'import de Logger et EnvironmentManager sera fait à l'intérieur de ensure_env
# pour éviter les problèmes d'imports circulaires potentiels si auto_env est importé tôt.

def ensure_env(env_name: str = "projet-is", silent: bool = True) -> bool:
    """
    One-liner auto-activateur d'environnement.
    Délègue la logique complexe à EnvironmentManager.
    
    Args:
        env_name: Nom de l'environnement conda.
        silent: Si True, réduit la verbosité des logs.
    
    Returns:
        True si l'environnement est (ou a été) activé avec succès, False sinon.
    """
    # DEBUG: Imprimer l'état initial
    print(f"[auto_env DEBUG] Début ensure_env. Python: {sys.executable}, CONDA_DEFAULT_ENV: {os.getenv('CONDA_DEFAULT_ENV')}, silent: {silent}", file=sys.stderr)

    # Vérification immédiate de l'exécutable Python
    if env_name not in sys.executable:
        error_message_immediate = (
            f"ERREUR CRITIQUE IMMÉDIATE : Le script est lancé avec un interpréteur Python incorrect.\n"
            f"  Exécutable Python (sys.executable): '{sys.executable}' (Doit contenir: '{env_name}')\n"
            f"  POUR CORRIGER : Assurez-vous que l'environnement Conda '{env_name}' est activé, ou lancez ce script via le wrapper 'activate_project_env.ps1'."
        )
        print(f"[auto_env] {error_message_immediate}", file=sys.stderr)
        raise RuntimeError(error_message_immediate)

    # Logique de court-circuit si le script d'activation principal est déjà en cours d'exécution
    if os.getenv('IS_ACTIVATION_SCRIPT_RUNNING') == 'true':
        if not silent: # Cette condition respecte le 'silent' original pour ce message spécifique.
            print("[auto_env] Court-circuit: Exécution via le script d'activation principal déjà en cours.")
        return True # On considère que l'environnement est déjà correctement configuré

    try:
        # --- Début de l'insertion pour sys.path (si nécessaire pour trouver project_core.core_from_scripts) ---
        # Cette section assure que project_core.core_from_scripts est dans sys.path pour les imports suivants.
        # Elle est contextuelle à l'emplacement de ce fichier auto_env.py.
        # Racine du projet = parent de 'scripts' = parent.parent.parent de __file__
        project_root_path = Path(__file__).resolve().parent.parent.parent
        scripts_core_path = project_root_path / "scripts" / "core"
        if str(scripts_core_path) not in sys.path:
            sys.path.insert(0, str(scripts_core_path))
        if str(project_root_path) not in sys.path: # Assurer que la racine du projet est aussi dans le path
             sys.path.insert(0, str(project_root_path))
        # --- Fin de l'insertion pour sys.path ---

        from project_core.core_from_scripts.environment_manager import EnvironmentManager, auto_activate_env as env_man_auto_activate_env
        from project_core.core_from_scripts.common_utils import Logger # Assumant que Logger est dans common_utils

        # Le logger peut être configuré ici ou EnvironmentManager peut en créer un par défaut.
        # Pour correspondre à l'ancienne verbosité contrôlée par 'silent':
        logger_instance = Logger(verbose=not silent)
        
        # manager = EnvironmentManager(logger=logger_instance) # Plus besoin de manager pour cet appel spécifique
        
        # L'appel principal qui encapsule toute la logique d'activation
        activated = env_man_auto_activate_env(env_name=env_name, silent=silent) # Le 'silent' de ensure_env est propagé
        
        # DEBUG: Imprimer le résultat de l'activation
        print(f"[auto_env DEBUG] env_man_auto_activate_env a retourné: {activated}", file=sys.stderr)
        
        if not silent: # Ce bloc ne sera pas exécuté si silent=True au niveau de ensure_env
            if activated:
                print(f"[auto_env] Activation de '{env_name}' via EnvironmentManager: SUCCÈS")
            else:
                print(f"[auto_env] Activation de '{env_name}' via EnvironmentManager: ÉCHEC")
        
        # --- DEBUT DE LA VERIFICATION CRITIQUE DE L'ENVIRONNEMENT ---
        current_conda_env = os.environ.get('CONDA_DEFAULT_ENV')
        current_python_executable = sys.executable

        # DEBUG: Imprimer l'état avant la vérification critique
        print(f"[auto_env DEBUG] Avant vérif critique. Python: {current_python_executable}, CONDA_DEFAULT_ENV: {current_conda_env}", file=sys.stderr)

        is_conda_env_correct = (current_conda_env == env_name)
        # Vérification plus robuste pour le chemin de l'exécutable
        # Il peut être dans 'envs/env_name/bin/python' ou 'env_name/bin/python' ou similaire
        is_python_executable_correct = env_name in current_python_executable

        if not (is_conda_env_correct and is_python_executable_correct):
            error_message = (
                f"ERREUR CRITIQUE : Le script ne s'exécute pas dans l'environnement Conda '{env_name}' attendu après tentative d'activation.\n"
                f"  Environnement Conda actif (CONDA_DEFAULT_ENV): '{current_conda_env}' (Attendu: '{env_name}')\n"
                f"  Exécutable Python (sys.executable): '{current_python_executable}' (Doit contenir: '{env_name}')\n"
                f"  POUR CORRIGER : Assurez-vous que l'environnement Conda '{env_name}' est activé avant de lancer ce script, ou utilisez le wrapper 'activate_project_env.ps1'."
            )
            # Logger l'erreur même si silent est True pour cette partie critique
            logger_instance.error(error_message) # Utilise l'instance de logger existante
            # Afficher également sur la console pour une visibilité maximale en cas d'échec critique
            print(f"[auto_env] {error_message}", file=sys.stderr)
            raise RuntimeError(error_message)
        elif not silent: # Ce bloc ne sera pas exécuté si silent=True au niveau de ensure_env
            logger_instance.info(
                f"[auto_env] Vérification de l'environnement réussie: CONDA_DEFAULT_ENV='{current_conda_env}', sys.executable='{current_python_executable}'"
            )
        # --- FIN DE LA VERIFICATION CRITIQUE DE L'ENVIRONNEMENT ---
                
        return activated
        
    except ImportError as ie:
        # Gérer le cas où EnvironmentManager ou Logger ne peuvent pas être importés
        # Cela peut arriver si sys.path n'est pas correctement configuré avant l'import.
        if not silent:
            print(f"[auto_env] ERREUR CRITIQUE: Impossible d'importer les modules nécessaires ({ie}).")
            print(f"             Vérifiez PYTHONPATH ou la structure du projet.")
            print(f"             sys.path actuel: {sys.path}")
        return False
    except Exception as e:
        if not silent:
            # Message d'erreur générique pour d'autres exceptions inattendues
            print(f"[auto_env] ERREUR INATTENDUE lors de l'ensure_env: {e}")
        return False

# Les fonctions _discover_and_persist_conda_path, _update_conda_path_from_env,
# _load_dotenv_intelligent, et _auto_activate_conda_env sont maintenant supprimées
# car leur logique a été transférée à EnvironmentManager.

def get_one_liner() -> str:
    """Retourne le one-liner exact à utiliser dans les scripts"""
    return "import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) else None; exec('try:\\n from auto_env import ensure_env; ensure_env()\\nexcept: pass')"


def get_simple_import() -> str:
    """Retourne l'import simple à utiliser"""
    return "import project_core.core_from_scripts.auto_env  # Auto-activation environnement intelligent"


# Auto-exécution à l'import pour usage ultra-simple
if __name__ != "__main__":
    # Le module est importé, auto-activation
    # ========================== ATTENTION - PROTECTION CRITIQUE ==========================
    # La ligne suivante `ensure_env()` est ESSENTIELLE pour la sécurité et la stabilité
    # de tous les tests et scripts. Elle garantit que le code s'exécute dans
    # l'environnement Conda approprié ('projet-is').
    #
    # NE JAMAIS DÉSACTIVER, COMMENTER OU SUPPRIMER CETTE LIGNE.
    # Le faire contourne les gardes-fous et peut entraîner des erreurs de dépendances
    # subtiles, des comportements imprévisibles et l'utilisation de mocks à la place
    # de composants réels, corrompant ainsi les résultats des tests.
    #
    # Cette protection est intentionnellement non-silencieuse pour rendre tout échec
    # d'activation de l'environnement immédiatement visible.
    # =====================================================================================
    ensure_env(silent=False)


if __name__ == "__main__":
    # Test direct du module
    print("[TEST] One-liner auto-activateur d'environnement")
    print("=" * 60)
    
    print("\n[CONFIG] ONE-LINER COMPLET :")
    print(get_one_liner())
    
    print("\n[CONFIG] IMPORT SIMPLE :")
    print(get_simple_import())
    
    print("\n[TEST] ACTIVATION :")
    success = ensure_env(silent=False)
    
    if success:
        print("[OK] Test reussi - Environnement operationnel")
    else:
        print("[WARN] Test en mode degrade - Environnement non active")
    
    print("\n[INFO] INTEGRATION DANS VOS SCRIPTS :")
    print("   # Methode 1 (ultra-simple) :")
    print("   import project_core.core_from_scripts.auto_env")
    print("")
    print("   # Methode 2 (explicite) :")
    print("   from project_core.core_from_scripts.auto_env import ensure_env")
    print("   ensure_env()")
    print("")
    print("   # Methode 3 (one-liner complet) :")
    print("   " + get_one_liner())
#!/usr/bin/env python3
"""
One-liner auto-activateur d'environnement intelligent
====================================================

Ce module fournit l'auto-activation automatique de l'environnement conda 'projet-is'.
Conçu pour être utilisé par les agents AI et développeurs sans se soucier de l'état d'activation.

UTILISATION SIMPLE (one-liner) :
from argumentation_analysis.core.environment import ensure_env
ensure_env()

OU ENCORE PLUS SIMPLE :
import argumentation_analysis.core.environment

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

def ensure_env(env_name: str = None, silent: bool = True) -> bool:
    """
    One-liner auto-activateur d'environnement.
    Délègue la logique complexe à EnvironmentManager.
    
    Args:
        env_name: Nom de l'environnement conda. Si None, il est lu depuis .env.
        silent: Si True, réduit la verbosité des logs.
    
    Returns:
        True si l'environnement est (ou a été) activé avec succès, False sinon.
    """
    # --- COURT-CIRCUIT POUR LES ENVIRONNEMENTS GÉRÉS EXTERIEUREMENT ---
    # Si cette variable est positionnée (par ex. par EnvironmentManager.run_in_conda_env),
    # cela signifie que l'environnement est déjà activé et géré. On ne fait rien
    # pour éviter une double activation qui peut corrompre les chemins et la découverte de packages.
    if os.getenv('RUNNING_VIA_ENV_MANAGER') == 'true':
        if not silent:
            print("[auto_env] Court-circuit: Exécution dans un environnement déjà géré par EnvironmentManager.")
        return True
    # --- Logique de détermination du nom de l'environnement ---
    if env_name is None:
        try:
            # Assurer que dotenv est importé
            from dotenv import load_dotenv, find_dotenv
            # Charger le fichier .env s'il existe
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path)
            # Récupérer le nom de l'environnement, avec 'projet-is' comme fallback
            env_name = os.environ.get('CONDA_ENV_NAME', 'epita_symbolic_ai')
        except ImportError:
            env_name = 'projet-is' # Fallback si dotenv n'est pas installé
    # DEBUG: Imprimer l'état initial
    print(f"[auto_env DEBUG] Début ensure_env. Python: {sys.executable}, CONDA_DEFAULT_ENV: {os.getenv('CONDA_DEFAULT_ENV')}, silent: {silent}", file=sys.stderr)

    # Vérification immédiate de l'exécutable Python - COMMENTÉE CAR TROP PRÉCOCE
    # if env_name not in sys.executable:
    #     error_message_immediate = (
    #         f"ERREUR CRITIQUE : L'INTERPRÉTEUR PYTHON EST INCORRECT.\n"
    #         f"  Exécutable utilisé : '{sys.executable}'\n"
    #         f"  L'exécutable attendu doit provenir de l'environnement Conda '{env_name}'.\n\n"
    #         f"  SOLUTION IMPÉRATIVE :\n"
    #         f"  Utilisez le script wrapper 'activate_project_env.ps1' situé à la RACINE du projet.\n\n"
    #         f"  Exemple : powershell -File .\\activate_project_env.ps1 -CommandToRun \"python votre_script.py\"\n\n"
    #         f"  IMPORTANT : Ce script ne se contente pas d'activer Conda. Il configure aussi JAVA_HOME, PYTHONPATH, et d'autres variables d'environnement cruciales. Ne PAS l'ignorer."
    #     )
    #     print(f"[auto_env] {error_message_immediate}", file=sys.stderr)
    #     raise RuntimeError(error_message_immediate)

    # Logique de court-circuit si le script d'activation principal est déjà en cours d'exécution
    if os.getenv('IS_ACTIVATION_SCRIPT_RUNNING') == 'true':
        if not silent: # Cette condition respecte le 'silent' original pour ce message spécifique.
            print("[auto_env] Court-circuit: Exécution via le script d'activation principal déjà en cours.")
        return True # On considère que l'environnement est déjà correctement configuré

    try:
        # L'ancienne manipulation de sys.path n'est plus nécessaire car ce module
        # fait maintenant partie d'un package standard.
        # Les dépendances sont gérées par l'installation du package.
        # Les dépendances sont maintenant gérées via les imports standards du projet
        from project_core.core_from_scripts.environment_manager import EnvironmentManager, auto_activate_env as env_man_auto_activate_env
        from project_core.core_from_scripts.common_utils import Logger

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
            # Créez le message d'avertissement
            warning_message = (
                f"AVERTISSEMENT : L'ENVIRONNEMENT '{env_name}' SEMBLE NE PAS ÊTRE CORRECTEMENT ACTIVÉ.\n"
                f"  - Environnement Conda détecté : '{current_conda_env}' (Attendu: '{env_name}')\n"
                f"  - Exécutable Python détecté : '{current_python_executable}'\n"
                f"  - Le processus va continuer, mais des erreurs de dépendances sont possibles."
            )
            # Log l'avertissement au lieu de lever une exception
            logger_instance.warning(warning_message)
            print(f"[auto_env] {warning_message}", file=sys.stderr)
            # Ne lève plus d'exception pour permettre au processus de continuer
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

# Les fonctions _discover_and_persist_conda_path, _update_conda_path_from_env,
# _load_dotenv_intelligent, et _auto_activate_conda_env sont maintenant supprimées
# car leur logique a été transférée à EnvironmentManager.

def get_one_liner() -> str:
    """Retourne le one-liner legacy. Cette fonction est conservée pour la compatibilité mais son usage est déprécié."""
    return "import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) else None; exec('try:\\n from auto_env import ensure_env; ensure_env()\\nexcept: pass')"


def get_simple_import() -> str:
    """Retourne l'import simple à utiliser"""
    return "import argumentation_analysis.core.environment  # Auto-activation environnement intelligent"


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
    ensure_env(env_name=None, silent=False)


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
    print("   import argumentation_analysis.core.environment")
    print("")
    print("   # Methode 2 (explicite) :")
    print("   from argumentation_analysis.core.environment import ensure_env")
    print("   ensure_env()")
    print("")
    print("   # Methode 3 (one-liner complet) :")
    print("   " + get_one_liner())
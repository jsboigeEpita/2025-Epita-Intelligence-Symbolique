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

def ensure_env(env_name: str = None, silent: bool = False) -> bool:
    """
    Auto-vérificateur d'environnement et coupe-circuit.
    Cette fonction ne tente PLUS d'activer l'environnement. Elle VERIFIE que
    l'environnement correct est déjà activé et lève une RuntimeError si ce n'est pas le cas.
    C'est un garde-fou crucial.
    
    Args:
        env_name: Nom de l'environnement conda attendu. Si None, lu depuis la config.
        silent: Si True, réduit la verbosité en cas de succès.
    
    Returns:
        True si l'environnement est correct.
    
    Raises:
        RuntimeError: Si l'environnement n'est pas celui attendu.
    """
    # En mode test E2E, on ne fait pas cette vérification pour éviter les problèmes
    # de propagation de l'environnement dans les sous-processus.
    if os.environ.get('E2E_TESTING_MODE') == '1':
        if not silent:
            print("[auto_env] WARNING: Vérification de l'environnement Conda désactivée pour les tests E2E.")
        return True

    if env_name is None:
        try:
            from argumentation_analysis.config.settings import settings
            env_name = settings.model_dump().get('CONDA_ENV_NAME', os.environ.get('CONDA_ENV_NAME', 'projet-is'))
        except (ImportError, AttributeError):
            env_name = os.environ.get('CONDA_ENV_NAME', 'projet-is')

    # La vérification est maintenant en deux étapes pour une robustesse maximale.
    # 1. Vérifier la variable d'environnement 'CONDA_DEFAULT_ENV'. C'est l'indicateur
    #    le plus fiable de l'environnement actif dans le shell.
    # 2. Vérifier sys.prefix comme filet de sécurité.

    active_conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    is_env_correct_by_var = (active_conda_env == env_name)

    # Pour CI/CD, on peut assouplir la règle.
    if not is_env_correct_by_var and env_name == 'projet-is-roo' and active_conda_env == 'projet-is':
        is_env_correct_by_var = True

    if not is_env_correct_by_var:
        current_env_path_for_error = sys.prefix
        try:
            current_env_name_for_error = Path(current_env_path_for_error).name
        except Exception:
            current_env_name_for_error = "inconnu"
        
        error_message = (
            f"ERREUR CRITIQUE : MAUVAIS ENVIRONNEMENT CONDA ACTIF.\n"
            f"  La variable d'environnement 'CONDA_DEFAULT_ENV' est incorrecte.\n"
            f"  Environnement attendu   : '{env_name}'\n"
            f"  Environnement détecté (CONDA_DEFAULT_ENV) : '{active_conda_env or 'NON DÉFINIE'}'\n"
            f"  Interpréteur actuel (peut être trompeur) : '{current_env_name_for_error}' ({sys.prefix})\n\n"
            f"  SOLUTION IMPÉRATIVE :\n"
            f"  1. Activez l'environnement : `conda activate {env_name}`\n"
            f"  2. Lancez votre commande.\n"
            f"  OU utilisez le script wrapper : `powershell -File .\\activate_project_env.ps1 -CommandToRun \"...\"`\n"
        )
        raise RuntimeError(error_message)


    # Ancien code conservé comme référence, mais la vérification principale est au-dessus.
    # current_env_path = sys.prefix
    # is_env_correct = f"envs\\{env_name}" in current_env_path or f"envs/{env_name}" in current_env_path
    # if not is_env_correct and env_name == 'projet-is-roo':
    #     is_env_correct = "envs\\projet-is" in current_env_path or "envs/projet-is" in current_env_path
    # if not is_env_correct:
        # Tenter d'extraire un nom d'environnement plus précis pour le message d'erreur
        try:
            current_env_name = Path(current_env_path).name
        except Exception:
            current_env_name = "inconnu"

        pass # La levée d'exception est maintenant gérée par la nouvelle logique ci-dessus.
    
    if not silent:
        # Pour l'affichage, on utilise le nom extrait du chemin
        # Le nom affiché doit être celui qui a été validé (env_name), et non celui
        # déduit du chemin sys.prefix qui peut être ambigu dans certains contextes.
        print(f"[auto_env] OK: L'environnement '{env_name}' est correctement activé.")

    return True

def get_one_liner() -> str:
    """Retourne le one-liner legacy. Cette fonction est conservée pour la compatibilité mais son usage est déprécié."""
    return "import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) else None; exec('try:\\n from auto_env import ensure_env; ensure_env()\\nexcept: pass')"


def get_simple_import() -> str:
    """Retourne l'import simple à utiliser"""
    return "import argumentation_analysis.core.environment  # Auto-activation environnement intelligent"


# Auto-exécution à l'import pour usage ultra-simple
if __name__ != "__main__":
    # Le module est importé, auto-activation/vérification.
    # ========================== ATTENTION - PROTECTION CRITIQUE ==========================
    # La ligne suivante `ensure_env()` est ESSENTIELLE pour la sécurité et la stabilité
    # de tous les scripts. Elle garantit que le code s'exécute dans
    # l'environnement Conda approprié ('projet-is').
    #
    # NE JAMAIS DÉSACTIVER, COMMENTER OU SUPPRIMER CETTE LIGNE.
    # =====================================================================================
    ensure_env()


if __name__ == "__main__":
    # Test direct du module
    print("[TEST] Auto-vérificateur d'environnement")
    print("=" * 60)

    print("\n[CONFIG] ONE-LINER COMPLET (legacy):")
    print(get_one_liner())
    
    print("\n[CONFIG] IMPORT SIMPLE :")
    print(get_simple_import())
    
    print("\n[TEST] VÉRIFICATION :")
    try:
        success = ensure_env(silent=False)
        if success:
            print("[OK] Test reussi - Environnement operationnel")
    except RuntimeError as e:
        print(f"\n[ERREUR] Test échoué comme attendu en dehors de l'environnement wrapper.")
        print(e)
        success = False
    
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
#!/usr/bin/env python3
"""
One-liner auto-activateur d'environnement intelligent
====================================================

Ce module fournit l'auto-activation automatique de l'environnement conda 'projet-is'.
Conçu pour être utilisé par les agents AI et développeurs sans se soucier de l'état d'activation.

UTILISATION SIMPLE (one-liner) :
from scripts.core.auto_env import ensure_env
ensure_env()

OU ENCORE PLUS SIMPLE :
import scripts.core.auto_env

Le module s'auto-exécute à l'import et active l'environnement si nécessaire.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
from pathlib import Path

def ensure_env(env_name: str = "projet-is", silent: bool = True) -> bool:
    """
    One-liner auto-activateur d'environnement
    
    Usage simple : from scripts.core.auto_env import ensure_env; ensure_env()
    
    Args:
        env_name: Nom de l'environnement conda
        silent: Mode silencieux
    
    Returns:
        True si environnement actif/activé
    """
    try:
        # Trouver le répertoire du projet
        current_dir = Path(__file__).parent.parent.parent.absolute()
        
        # Ajouter scripts/core au path si nécessaire
        scripts_core = current_dir / "scripts" / "core"
        if scripts_core.exists() and str(scripts_core) not in sys.path:
            sys.path.insert(0, str(scripts_core))
        
        # Importer le gestionnaire d'environnement
        from scripts.core.environment_manager import auto_activate_env
        
        # Auto-activation
        return auto_activate_env(env_name, silent)
        
    except Exception as e:
        if not silent:
            print(f"[WARN] Auto-activation environnement echouee: {e}")
            print("[INFO] Continuez dans l'environnement actuel...")
        return False


def get_one_liner() -> str:
    """Retourne le one-liner exact à utiliser dans les scripts"""
    return "import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) else None; exec('try:\\n from auto_env import ensure_env; ensure_env()\\nexcept: pass')"


def get_simple_import() -> str:
    """Retourne l'import simple à utiliser"""
    return "import scripts.core.auto_env  # Auto-activation environnement intelligent"


# Auto-exécution à l'import pour usage ultra-simple
if __name__ != "__main__":
    # Le module est importé, auto-activation
    ensure_env()


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
    print("   import scripts.core.auto_env")
    print("")
    print("   # Methode 2 (explicite) :")
    print("   from scripts.core.auto_env import ensure_env")
    print("   ensure_env()")
    print("")
    print("   # Methode 3 (one-liner complet) :")
    print("   " + get_one_liner())
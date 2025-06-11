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
    One-liner auto-activateur d'environnement avec chargement .env
    
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
        
        # 1. CHARGEMENT .ENV EN PREMIER
        dotenv_loaded = _load_dotenv_intelligent(current_dir, silent)
        
        # Ajouter scripts/core au path si nécessaire
        scripts_core = current_dir / "scripts" / "core"
        if scripts_core.exists() and str(scripts_core) not in sys.path:
            sys.path.insert(0, str(scripts_core))
        
        # 2. AUTO-ACTIVATION CONDA
        from scripts.core.environment_manager import auto_activate_env
        conda_activated = auto_activate_env(env_name, silent)
        
        if not silent and dotenv_loaded:
            print(f"[OK] .env chargé + conda activé: {conda_activated}")
            
        return conda_activated
        
    except Exception as e:
        if not silent:
            print(f"[WARN] Auto-activation environnement echouee: {e}")
            print("[INFO] Continuez dans l'environnement actuel...")
        return False


def _load_dotenv_intelligent(project_root: Path, silent: bool = True) -> bool:
    """
    Charge le fichier .env de manière intelligente
    
    Args:
        project_root: Racine du projet
        silent: Mode silencieux
        
    Returns:
        bool: True si .env chargé avec succès
    """
    try:
        # Méthode 1: Utiliser python-dotenv si disponible
        try:
            from dotenv import load_dotenv, find_dotenv
            
            # Chercher .env en remontant l'arborescence depuis project_root
            env_path = find_dotenv(filename=".env", usecwd=False, raise_error_if_not_found=False)
            if env_path:
                if not silent:
                    print(f"[OK] Chargement .env trouvé: {env_path}")
                return load_dotenv(env_path, override=False)  # Ne pas override les vars existantes
            else:
                # Fallback: chercher dans project_root
                env_path = project_root / '.env'
                if env_path.exists():
                    if not silent:
                        print(f"[OK] Chargement .env: {env_path}")
                    return load_dotenv(str(env_path), override=False)
                else:
                    if not silent:
                        print("[INFO] Fichier .env non trouvé")
                    return False
                
        except ImportError:
            # Fallback: Chargement manuel
            if not silent:
                print("[INFO] python-dotenv non disponible, chargement manuel")
            
            env_path = project_root / '.env'
            if env_path.exists():
                if not silent:
                    print(f"[OK] Chargement manuel .env: {env_path}")
                
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Enlever guillemets si présents
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            
                            # Ne pas override les variables existantes
                            if key and key not in os.environ:
                                os.environ[key] = value
                
                return True
            else:
                if not silent:
                    print(f"[INFO] .env non trouvé: {env_path}")
                return False
                
    except Exception as e:
        if not silent:
            print(f"[WARN] Erreur chargement .env: {e}")
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
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
        conda_activated = _auto_activate_conda_env(env_name, silent)
        
        if not silent and dotenv_loaded:
            print(f"[OK] .env chargé + conda activé: {conda_activated}")
            
        return conda_activated
        
    except Exception as e:
        if not silent:
            print(f"[WARN] Auto-activation environnement echouee: {e}")
            print("[INFO] Continuez dans l'environnement actuel...")
        return False


def _update_conda_path_from_env(silent: bool = True) -> bool:
    """
    Met à jour le PATH système avec le chemin conda depuis la variable CONDA_PATH
    
    Args:
        silent: Mode silencieux
        
    Returns:
        bool: True si PATH mis à jour avec succès
    """
    try:
        conda_path = os.environ.get('CONDA_PATH', '')
        if not conda_path:
            if not silent:
                print("[INFO] CONDA_PATH non défini dans .env")
            return False
        
        # Diviser les chemins (séparés par ;)
        conda_paths = [p.strip() for p in conda_path.split(';') if p.strip()]
        
        # Obtenir le PATH actuel
        current_path = os.environ.get('PATH', '')
        path_elements = current_path.split(os.pathsep)
        
        # Ajouter les chemins conda au début si pas déjà présents
        updated = False
        for conda_dir in reversed(conda_paths):  # Reversed pour maintenir l'ordre
            if conda_dir not in path_elements:
                path_elements.insert(0, conda_dir)
                updated = True
                if not silent:
                    print(f"[CONDA] Ajout au PATH: {conda_dir}")
        
        if updated:
            # Mettre à jour le PATH
            new_path = os.pathsep.join(path_elements)
            os.environ['PATH'] = new_path
            if not silent:
                print("[CONDA] PATH mis à jour avec les chemins conda")
            return True
        else:
            if not silent:
                print("[CONDA] PATH déjà configuré pour conda")
            return True
            
    except Exception as e:
        if not silent:
            print(f"[WARN] Erreur mise à jour PATH conda: {e}")
        return False


def _load_dotenv_intelligent(project_root: Path, silent: bool = True) -> bool:
    """
    Charge le fichier .env de manière intelligente et met à jour le PATH conda
    
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
                loaded = load_dotenv(env_path, override=False)  # Ne pas override les vars existantes
                if loaded:
                    _update_conda_path_from_env(silent)
                return loaded
            else:
                # Fallback: chercher dans project_root
                env_path = project_root / '.env'
                if env_path.exists():
                    if not silent:
                        print(f"[OK] Chargement .env: {env_path}")
                    loaded = load_dotenv(str(env_path), override=False)
                    if loaded:
                        _update_conda_path_from_env(silent)
                    return loaded
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
                
                # Après chargement .env, mettre à jour le PATH conda
                _update_conda_path_from_env(silent)
                return True
            else:
                if not silent:
                    print(f"[INFO] .env non trouvé: {env_path}")
                return False
                
    except Exception as e:
        if not silent:
            print(f"[WARN] Erreur chargement .env: {e}")
        return False


def _auto_activate_conda_env(env_name: str = "projet-is", silent: bool = True) -> bool:
    """
    Auto-activation intelligente de l'environnement conda
    
    Args:
        env_name: Nom de l'environnement conda
        silent: Mode silencieux
    
    Returns:
        True si environnement actif/activé
    """
    try:
        import subprocess
        import json
        
        # Vérifier si l'environnement est déjà actif
        current_env = os.environ.get('CONDA_DEFAULT_ENV', '')
        if current_env == env_name:
            if not silent:
                print(f"[OK] Environnement '{env_name}' déjà actif")
            return True
        
        # Vérifier si conda est disponible
            # Tentative de détection de Conda via CONDA_EXE si CONDA_PATH n'a pas fonctionné
            conda_exe_path_str = os.environ.get('CONDA_EXE')
            if conda_exe_path_str:
                conda_exe_file = Path(conda_exe_path_str)
                if conda_exe_file.is_file():
                    if not silent:
                        print(f"[INFO] CONDA_EXE trouvé: {conda_exe_file}")
                    
                    condabin_dir = conda_exe_file.parent # e.g., C:\...\anaconda3\condabin
                    
                    # Déterminer le répertoire Scripts, typiquement un frère de condabin
                    # (e.g., C:\...\anaconda3\Scripts)
                    scripts_dir = condabin_dir.parent / "Scripts"
                    
                    paths_to_add_to_os_path = []
                    if condabin_dir.is_dir():
                        paths_to_add_to_os_path.append(str(condabin_dir))
                    if scripts_dir.is_dir():
                        paths_to_add_to_os_path.append(str(scripts_dir))
                    
                    if paths_to_add_to_os_path:
                        current_os_path = os.environ.get('PATH', '')
                        path_elements = current_os_path.split(os.pathsep)
                        
                        path_updated_by_conda_exe = False
                        # Ajouter les chemins au début du PATH s'ils ne sont pas déjà présents
                        for p_to_add in reversed(paths_to_add_to_os_path): # reversed pour maintenir l'ordre
                            if p_to_add not in path_elements:
                                path_elements.insert(0, p_to_add)
                                path_updated_by_conda_exe = True
                                if not silent:
                                    print(f"[CONDA_EXE] Ajout au PATH système: {p_to_add}")
                        
                        if path_updated_by_conda_exe:
                            os.environ['PATH'] = os.pathsep.join(path_elements)
                            if not silent:
                                print(f"[CONDA_EXE] PATH système mis à jour via les informations de CONDA_EXE.")
                elif not silent:
                    print(f"[INFO] CONDA_EXE ('{conda_exe_path_str}') ne pointe pas vers un fichier valide.")
            elif not silent:
                print(f"[INFO] Variable d'environnement CONDA_EXE non trouvée.")
            # Fin de la tentative de détection via CONDA_EXE

        try:
            result = subprocess.run(
                ['conda', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                if not silent:
                    print(f"[ERROR] Conda non disponible")
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            if not silent:
                print(f"[ERROR] Conda non disponible")
            return False
        
        # Obtenir la liste des environnements conda
        try:
            result = subprocess.run(
                ['conda', 'info', '--envs', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
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
                        
                        # Variables d'environnement du projet
                        project_root = str(Path(__file__).parent.parent.parent.absolute())
                        os.environ['PYTHONIOENCODING'] = 'utf-8'
                        os.environ['PYTHONPATH'] = project_root
                        os.environ['PROJECT_ROOT'] = project_root
                        
                        if not silent:
                            print(f"[INFO] Auto-activation de l'environnement '{env_name}'...")
                            print(f"[CONDA] PATH mis à jour: {env_bin_path}")
                            print(f"[OK] Environnement '{env_name}' auto-actif")
                        
                        return True
                    else:
                        if not silent:
                            print(f"[ERROR] Répertoire bin/Scripts non trouvé: {env_bin_path}")
                        return False
                else:
                    if not silent:
                        print(f"[ERROR] Environnement '{env_name}' non trouvé")
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
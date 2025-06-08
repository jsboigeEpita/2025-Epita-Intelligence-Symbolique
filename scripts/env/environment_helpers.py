#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helpers pour la gestion de l'environnement dédié - Oracle Enhanced v2.1.0

Fonctions utilitaires pour détecter, valider et configurer l'environnement projet.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXPECTED_ENV_NAME = "projet-is"
ENVIRONMENT_YML = PROJECT_ROOT / "environment.yml"
SETUP_SCRIPT = PROJECT_ROOT / "setup_project_env.ps1"

class EnvironmentError(Exception):
    """Erreur liée à l'environnement."""
    pass

def is_project_environment_active() -> Tuple[bool, str]:
    """
    Vérifie si l'environnement projet est actif.
    
    Returns:
        Tuple[bool, str]: (est_actif, message_diagnostic)
    """
    # Vérifier conda
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env == EXPECTED_ENV_NAME:
        return True, f"✅ Environnement conda correct: {conda_env}"
    
    # Vérifier venv local
    virtual_env = os.environ.get('VIRTUAL_ENV')
    if virtual_env:
        venv_name = Path(virtual_env).name
        if any(name in venv_name.lower() for name in ['projet', 'oracle', 'argum']):
            return True, f"✅ Environnement venv projet: {venv_name}"
        else:
            return False, f"⚠️  Environnement venv non-projet: {venv_name}"
    
    # Vérifier PYTHONPATH projet
    if str(PROJECT_ROOT) in sys.path:
        if conda_env and conda_env != "base":
            return True, f"ℹ️  Environnement conda: {conda_env} avec PYTHONPATH projet"
        else:
            return False, f"⚠️  Python système avec PYTHONPATH projet (non optimal)"
    
    return False, "❌ Aucun environnement projet détecté"

def detect_available_environments() -> Dict[str, List[str]]:
    """
    Détecte les environnements disponibles.
    
    Returns:
        Dict contenant les environnements conda et venv disponibles
    """
    environments = {
        'conda': [],
        'venv_local': [],
        'venv_global': []
    }
    
    # Environnements conda
    try:
        result = subprocess.run(['conda', 'env', 'list'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('#'):
                    env_name = line.split()[0]
                    environments['conda'].append(env_name)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Venv locaux
    for venv_name in ['venv', 'env', '.venv', 'projet-is']:
        venv_path = PROJECT_ROOT / venv_name
        if venv_path.exists() and (venv_path / "Scripts").exists():
            environments['venv_local'].append(str(venv_path))
    
    return environments

def ensure_project_environment():
    """
    S'assure que l'environnement projet est utilisé.
    
    Raises:
        EnvironmentError: Si l'environnement n'est pas correct
    """
    is_active, message = is_project_environment_active()
    
    if not is_active:
        error_msg = f"""
{message}

🔧 SOLUTION RECOMMANDÉE:
Utilisez le script d'activation pour exécuter ce script:

Windows PowerShell:
    .\\setup_project_env.ps1 -CommandToRun "python {' '.join(sys.argv)}"

Linux/Mac:
    source scripts/env/activate_project_env.sh
    python {' '.join(sys.argv)}

ALTERNATIVE:
Activez manuellement l'environnement conda:
    conda activate {EXPECTED_ENV_NAME}
    python {' '.join(sys.argv)}
"""
        raise EnvironmentError(error_msg.strip())
    
    print(message)

def configure_project_paths():
    """Configure les chemins du projet dans sys.path."""
    paths_to_add = [
        str(PROJECT_ROOT),
        str(PROJECT_ROOT / "project_core"),
        str(PROJECT_ROOT / "libs"),
        str(PROJECT_ROOT / "argumentation_analysis")
    ]
    
    added_paths = []
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
            added_paths.append(path)
    
    if added_paths:
        print(f"📂 Ajout de {len(added_paths)} chemins au PYTHONPATH")

def get_environment_status() -> Dict:
    """
    Obtient le statut complet de l'environnement.
    
    Returns:
        Dict avec les informations d'environnement
    """
    is_active, message = is_project_environment_active()
    environments = detect_available_environments()
    
    return {
        'is_project_env': is_active,
        'status_message': message,
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'python_executable': sys.executable,
        'project_root': str(PROJECT_ROOT),
        'available_environments': environments,
        'conda_env': os.environ.get('CONDA_DEFAULT_ENV'),
        'virtual_env': os.environ.get('VIRTUAL_ENV'),
        'pythonpath_configured': str(PROJECT_ROOT) in sys.path
    }

def print_environment_warning():
    """Affiche un avertissement si l'environnement n'est pas optimal."""
    is_active, message = is_project_environment_active()
    
    if not is_active:
        print("⚠️" + "=" * 60)
        print("⚠️  AVERTISSEMENT ENVIRONNEMENT")
        print("⚠️" + "=" * 60)
        print(f"⚠️  {message}")
        print("⚠️")
        print("⚠️  Pour des résultats optimaux, utilisez:")
        print(f"⚠️  .\\setup_project_env.ps1 -CommandToRun \"python {' '.join(sys.argv)}\"")
        print("⚠️" + "=" * 60)

def auto_setup_project_paths():
    """
    Configuration automatique des chemins projet.
    Utilisé par les scripts qui veulent une configuration transparente.
    """
    # Ajouter les chemins projet
    configure_project_paths()
    
    # Configurer l'encodage
    if not os.environ.get('PYTHONIOENCODING'):
        os.environ['PYTHONIOENCODING'] = 'utf-8'

def recommend_activation_command(script_path: str) -> str:
    """
    Recommande la commande d'activation pour un script donné.
    
    Args:
        script_path: Chemin du script à exécuter
        
    Returns:
        Commande d'activation recommandée
    """
    relative_path = Path(script_path).relative_to(PROJECT_ROOT)
    return f".\\setup_project_env.ps1 -CommandToRun \"python {relative_path}\""

# Décorateur pour forcer l'environnement projet
def require_project_environment(func):
    """
    Décorateur qui s'assure que l'environnement projet est actif.
    
    Usage:
        @require_project_environment
        def my_function():
            # Code qui nécessite l'environnement projet
    """
    def wrapper(*args, **kwargs):
        try:
            ensure_project_environment()
        except EnvironmentError as e:
            print(str(e))
            sys.exit(1)
        return func(*args, **kwargs)
    return wrapper

# Auto-configuration au niveau module
def _auto_configure():
    """Configuration automatique lors de l'import."""
    # Ne pas forcer, juste configurer les chemins
    auto_setup_project_paths()

# Exécuter l'auto-configuration
_auto_configure()
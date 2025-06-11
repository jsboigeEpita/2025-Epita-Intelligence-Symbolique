#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestionnaire central de l'environnement dédié - Oracle Enhanced v2.1.0

Point d'entrée unique pour toutes les opérations d'environnement.
"""

import sys
import os
import subprocess
from pathlib import Path
import argparse
import shutil

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _find_conda():
    """Trouve l'exécutable conda de manière simple."""
    conda_exe = os.environ.get('CONDA_EXE')
    if conda_exe and Path(conda_exe).exists():
        return conda_exe
    
    conda_exe = shutil.which('conda')
    if conda_exe:
        return conda_exe
        
    return None

def print_banner():
    """Affiche la bannière du gestionnaire."""
    print("[MONDE] ================================================================")
    print("[MONDE] GESTIONNAIRE ENVIRONNEMENT DÉDIÉ - Oracle Enhanced v2.1.0")
    print("[MONDE] ================================================================")

def cmd_status():
    """Affiche le statut de l'environnement."""
    print_banner()
    
    try:
        from scripts.env.environment_helpers import get_environment_status
        status = get_environment_status()
        
        print(f"\n📍 STATUT ENVIRONNEMENT")
        print(f"   Environnement projet: {'[OK] OUI' if status['is_project_env'] else '[X] NON'}")
        print(f"   Message: {status['status_message']}")
        print(f"   Python: {status['python_version']}")
        print(f"   Exécutable: {status['python_executable']}")
        print(f"   PYTHONPATH: {'[OK] Configuré' if status['pythonpath_configured'] else '[X] Non configuré'}")
        
        if status['conda_env']:
            print(f"   Conda: {status['conda_env']}")
        if status['virtual_env']:
            print(f"   VirtualEnv: {Path(status['virtual_env']).name}")
        
        return 0 if status['is_project_env'] else 1
        
    except ImportError:
        print("\n[X] Helpers d'environnement non disponibles")
        print("[AMPOULE] Utilisez: .\\setup_project_env.ps1 -CommandToRun \"python scripts/env/manage_environment.py status\"")
        return 1

def cmd_check():
    """Vérification rapide de l'environnement."""
    print_banner()
    print("\n[LOUPE] VÉRIFICATION RAPIDE...")
    
    try:
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/env/check_environment.py")], 
                              capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"[X] Erreur lors de la vérification: {e}")
        return 1

def cmd_diagnose():
    """Diagnostic complet de l'environnement."""
    print_banner()
    print("\n🔬 DIAGNOSTIC COMPLET...")
    
    try:
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/env/diagnose_environment.py"), "--full"], 
                              capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"[X] Erreur lors du diagnostic: {e}")
        return 1

def cmd_setup():
    """Configuration initiale de l'environnement."""
    print_banner()
    print("\n[FUSEE] CONFIGURATION INITIALE...")
    
    env_yml = PROJECT_ROOT / "environment.yml"
    if not env_yml.exists():
        print("[X] Fichier environment.yml non trouvé!")
        return 1
    
    print("1. Création de l'environnement conda...")
    try:
        result = subprocess.run(["conda", "env", "create", "-f", str(env_yml)], 
                              capture_output=False)
        if result.returncode != 0:
            print("[X] Échec de la création de l'environnement conda")
            return 1
    except FileNotFoundError:
        print("[X] Conda non disponible!")
        print("[AMPOULE] Installez Anaconda/Miniconda d'abord")
        return 1
    
    print("2. Vérification de l'installation...")
    try:
        result = subprocess.run(["conda", "activate", "projet-is", "&&", "python", "--version"], 
                              shell=True, capture_output=False)
    except Exception as e:
        print(f"[ATTENTION]  Vérification manuelle requise: {e}")
    
    print("\n[OK] Configuration terminée!")
    print("[AMPOULE] Testez avec: conda activate projet-is")
    return 0

def cmd_fix():
    """Tentative de réparation automatique."""
    print_banner()
    print("\n[CLE] RÉPARATION AUTOMATIQUE...")
    
    # 1. Trouver l'exécutable conda
    print("   [1/3] Recherche de l'exécutable Conda...")
    conda_exe = _find_conda()
    if not conda_exe:
        print("[X] Conda non disponible, impossible de réparer.")
        return 1
    print(f"   [OK] Conda trouvé : {conda_exe}")

    # 2. Vérifier si l'environnement existe
    print("   [2/3] Vérification de l'existence de l'environnement 'projet-is'...")
    try:
        result = subprocess.run([conda_exe, "env", "list"], capture_output=True, text=True, check=True)
        if "projet-is" not in result.stdout:
            print("[ATTENTION]  Environnement 'projet-is' absent. Lancement de la configuration initiale...")
            return cmd_setup()
        print("   [OK] L'environnement 'projet-is' existe.")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"[X] Erreur lors de la vérification de l'environnement : {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"   [STDERR] {e.stderr}")
        return 1
    
    # 3. Réinstaller les dépendances
    print("   [3/3] Mise à jour des dépendances depuis environment.yml...")
    print("   [ATTENTION] Cette opération peut prendre plusieurs minutes. La progression s'affichera ci-dessous.")
    try:
        env_file = str(PROJECT_ROOT / "environment.yml")
        command = [
            conda_exe, "env", "update", "--name", "projet-is",
            "--file", env_file, "--prune"
        ]
        print(f"   [CMD] Exécution de: {' '.join(command)}\n")
        
        # On utilise capture_output=False pour voir la sortie en temps réel
        result = subprocess.run(command, capture_output=False)
        
        if result.returncode == 0:
            print("\n[OK] Les dépendances ont été mises à jour avec succès.")
        else:
            print(f"\n[X] Échec de la mise à jour des dépendances (code de retour: {result.returncode}).")
            print("[AMPOULE] Vérifiez les erreurs ci-dessus. Un conflit de paquets est possible.")
            return 1
            
    except Exception as e:
        print(f"\n[X] Une erreur inattendue est survenue lors de la mise à jour: {e}")
        return 1
    
    print("\n[ROBOT] Réparation terminée.")
    return 0

def cmd_update_scripts():
    """Met à jour les scripts pour utiliser l'environnement dédié."""
    print_banner()
    print("\n[CLE] MISE À JOUR DES SCRIPTS...")
    
    try:
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/env/update_demo_scripts.py")], 
                              capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"[X] Erreur mise à jour scripts: {e}")
        return 1

def cmd_help():
    """Affiche l'aide."""
    print_banner()
    print("""
🆘 COMMANDES DISPONIBLES:

[GRAPHIQUE] DIAGNOSTIC:
   status     - Affiche le statut actuel de l'environnement
   check      - Vérification rapide (recommandé pour débuter)
   diagnose   - Diagnostic complet avec détails

[CLE] CONFIGURATION:
   setup      - Configuration initiale (première fois)
   fix        - Tentative de réparation automatique
   update     - Met à jour les scripts de démonstration

[AMPOULE] UTILISATION RECOMMANDÉE:
   1. python scripts/env/manage_environment.py check
   2. Si problème: python scripts/env/manage_environment.py setup
   3. Pour diagnostic: python scripts/env/manage_environment.py diagnose

[ATTENTION]  IMPORTANT: Pour un environnement optimal, utilisez:
   .\\setup_project_env.ps1 -CommandToRun "python scripts/env/manage_environment.py <commande>"
""")
    return 0

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Gestionnaire environnement Oracle Enhanced v2.1.0")
    parser.add_argument('command', nargs='?', default='help',
                       choices=['status', 'check', 'diagnose', 'setup', 'fix', 'update', 'help'],
                       help='Commande à exécuter')
    
    args = parser.parse_args()
    
    # Mapping des commandes
    commands = {
        'status': cmd_status,
        'check': cmd_check,
        'diagnose': cmd_diagnose,
        'setup': cmd_setup,
        'fix': cmd_fix,
        'update': cmd_update_scripts,
        'help': cmd_help
    }
    
    try:
        return commands[args.command]()
    except KeyboardInterrupt:
        print("\n\n[ATTENTION]  Opération interrompue par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\n[X] Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
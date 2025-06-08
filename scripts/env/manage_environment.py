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

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def print_banner():
    """Affiche la bannière du gestionnaire."""
    print("🌍 ================================================================")
    print("🌍 GESTIONNAIRE ENVIRONNEMENT DÉDIÉ - Oracle Enhanced v2.1.0")
    print("🌍 ================================================================")

def cmd_status():
    """Affiche le statut de l'environnement."""
    print_banner()
    
    try:
        from scripts.env.environment_helpers import get_environment_status
        status = get_environment_status()
        
        print(f"\n📍 STATUT ENVIRONNEMENT")
        print(f"   Environnement projet: {'✅ OUI' if status['is_project_env'] else '❌ NON'}")
        print(f"   Message: {status['status_message']}")
        print(f"   Python: {status['python_version']}")
        print(f"   Exécutable: {status['python_executable']}")
        print(f"   PYTHONPATH: {'✅ Configuré' if status['pythonpath_configured'] else '❌ Non configuré'}")
        
        if status['conda_env']:
            print(f"   Conda: {status['conda_env']}")
        if status['virtual_env']:
            print(f"   VirtualEnv: {Path(status['virtual_env']).name}")
        
        return 0 if status['is_project_env'] else 1
        
    except ImportError:
        print("\n❌ Helpers d'environnement non disponibles")
        print("💡 Utilisez: .\\setup_project_env.ps1 -CommandToRun \"python scripts/env/manage_environment.py status\"")
        return 1

def cmd_check():
    """Vérification rapide de l'environnement."""
    print_banner()
    print("\n🔍 VÉRIFICATION RAPIDE...")
    
    try:
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/env/check_environment.py")], 
                              capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
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
        print(f"❌ Erreur lors du diagnostic: {e}")
        return 1

def cmd_setup():
    """Configuration initiale de l'environnement."""
    print_banner()
    print("\n🚀 CONFIGURATION INITIALE...")
    
    env_yml = PROJECT_ROOT / "environment.yml"
    if not env_yml.exists():
        print("❌ Fichier environment.yml non trouvé!")
        return 1
    
    print("1. Création de l'environnement conda...")
    try:
        result = subprocess.run(["conda", "env", "create", "-f", str(env_yml)], 
                              capture_output=False)
        if result.returncode != 0:
            print("❌ Échec de la création de l'environnement conda")
            return 1
    except FileNotFoundError:
        print("❌ Conda non disponible!")
        print("💡 Installez Anaconda/Miniconda d'abord")
        return 1
    
    print("2. Vérification de l'installation...")
    try:
        result = subprocess.run(["conda", "activate", "projet-is", "&&", "python", "--version"], 
                              shell=True, capture_output=False)
    except Exception as e:
        print(f"⚠️  Vérification manuelle requise: {e}")
    
    print("\n✅ Configuration terminée!")
    print("💡 Testez avec: conda activate projet-is")
    return 0

def cmd_fix():
    """Tentative de réparation automatique."""
    print_banner()
    print("\n🔧 RÉPARATION AUTOMATIQUE...")
    
    # 1. Vérifier si l'environnement existe
    try:
        result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
        if "projet-is" not in result.stdout:
            print("⚠️  Environnement 'projet-is' absent, création...")
            return cmd_setup()
    except FileNotFoundError:
        print("❌ Conda non disponible, impossible de réparer")
        return 1
    
    # 2. Réinstaller les dépendances
    print("🔄 Mise à jour des dépendances...")
    try:
        result = subprocess.run(["conda", "env", "update", "-f", str(PROJECT_ROOT / "environment.yml")], 
                              capture_output=False)
        if result.returncode == 0:
            print("✅ Dépendances mises à jour")
        else:
            print("⚠️  Mise à jour partielle")
    except Exception as e:
        print(f"❌ Erreur mise à jour: {e}")
        return 1
    
    return 0

def cmd_update_scripts():
    """Met à jour les scripts pour utiliser l'environnement dédié."""
    print_banner()
    print("\n🔧 MISE À JOUR DES SCRIPTS...")
    
    try:
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/env/update_demo_scripts.py")], 
                              capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Erreur mise à jour scripts: {e}")
        return 1

def cmd_help():
    """Affiche l'aide."""
    print_banner()
    print("""
🆘 COMMANDES DISPONIBLES:

📊 DIAGNOSTIC:
   status     - Affiche le statut actuel de l'environnement
   check      - Vérification rapide (recommandé pour débuter)
   diagnose   - Diagnostic complet avec détails

🔧 CONFIGURATION:
   setup      - Configuration initiale (première fois)
   fix        - Tentative de réparation automatique
   update     - Met à jour les scripts de démonstration

💡 UTILISATION RECOMMANDÉE:
   1. python scripts/env/manage_environment.py check
   2. Si problème: python scripts/env/manage_environment.py setup
   3. Pour diagnostic: python scripts/env/manage_environment.py diagnose

⚠️  IMPORTANT: Pour un environnement optimal, utilisez:
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
        print("\n\n⚠️  Opération interrompue par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Lancement Simplifié - Application Web Intelligence Symbolique
======================================================================

OBJECTIF :
- Remplace l'ancien start_web_application.ps1
- Active automatiquement l'environnement conda 'projet-is'
- Lance l'UnifiedWebOrchestrator avec des options par défaut intelligentes
- Interface CLI simple et intuitive

USAGE :
    python start_webapp.py                    # Démarrage complet par défaut
    python start_webapp.py --visible          # Interface visible (non headless)
    python start_webapp.py --frontend         # Avec frontend React
    python start_webapp.py --backend-only     # Backend seulement
    python start_webapp.py --help             # Aide complète

Auteur: Projet Intelligence Symbolique EPITA
Date: 08/06/2025
Version: 1.0.0
"""

import os
import sys
import subprocess
import argparse
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configuration encodage UTF-8 pour Windows
def configure_utf8():
    """Configure UTF-8 pour éviter les problèmes d'encodage Unicode"""
    if os.name == 'nt':  # Windows
        try:
            # Tenter de configurer la sortie console en UTF-8
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except:
            # Si ça échoue, on continuera avec ASCII
            pass

# Configuration encodage dès l'import
configure_utf8()

# Configuration du projet - CORRIGÉ pour racine du projet
PROJECT_ROOT = Path(__file__).parent.absolute()  # Maintenant à la racine
CONDA_ENV_NAME = "projet-is"
ORCHESTRATOR_PATH = "scripts.webapp.unified_web_orchestrator"

class Colors:
    """Couleurs pour l'affichage terminal"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def safe_print(text: str, fallback_text: str = None):
    """Affichage sécurisé avec fallback ASCII"""
    try:
        print(text)
    except UnicodeEncodeError:
        if fallback_text:
            print(fallback_text)
        else:
            # Remplacer les emojis par des alternatives ASCII
            ascii_text = text
            emoji_replacements = {
                '🚀': '[LAUNCH]',
                '📋': '[ENV]',
                '📂': '[DIR]',
                '🎯': '[TARGET]',
                '✅': '[OK]',
                '❌': '[ERROR]',
                '⚠️': '[WARNING]',
                '🛑': '[STOP]',
                '💡': '[INFO]',
                '🔍': '[CHECK]',
                '🎉': '[SUCCESS]',
                '💥': '[FAILURE]',
                '🐍': '[PYTHON]'
            }
            for emoji, replacement in emoji_replacements.items():
                ascii_text = ascii_text.replace(emoji, replacement)
            print(ascii_text)

def setup_logging() -> logging.Logger:
    """Configure le logging pour le script"""
    logger = logging.getLogger('start_webapp')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def print_banner():
    """Affiche la bannière de démarrage"""
    banner = f"""
{Colors.BLUE}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║             [LAUNCH] DÉMARRAGE APPLICATION WEB - EPITA      ║
║                    Intelligence Symbolique                   ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.YELLOW}[ENV] ENVIRONNEMENT:{Colors.END} {CONDA_ENV_NAME}
{Colors.YELLOW}[DIR] PROJET:{Colors.END} {PROJECT_ROOT}
{Colors.YELLOW}[TARGET] ORCHESTRATEUR:{Colors.END} UnifiedWebOrchestrator
"""
    safe_print(banner)

def find_conda_executable() -> Optional[str]:
    """Trouve l'exécutable conda sur le système"""
    # Essayer avec which/where
    conda_exe = shutil.which("conda")
    if conda_exe:
        return conda_exe
    
    # Variables d'environnement communes
    for env_var in ["CONDA_EXE", "CONDA_ROOT"]:
        conda_path = os.environ.get(env_var)
        if conda_path:
            if env_var == "CONDA_ROOT":
                # Sur Windows : CONDA_ROOT/Scripts/conda.exe
                # Sur Unix : CONDA_ROOT/bin/conda
                conda_exe = os.path.join(conda_path, "Scripts", "conda.exe")
                if os.path.exists(conda_exe):
                    return conda_exe
                conda_exe = os.path.join(conda_path, "bin", "conda")
                if os.path.exists(conda_exe):
                    return conda_exe
            elif os.path.exists(conda_path):
                return conda_path
    
    # Chemins typiques Windows
    if os.name == 'nt':
        common_paths = [
            os.path.expanduser("~/miniconda3/Scripts/conda.exe"),
            os.path.expanduser("~/anaconda3/Scripts/conda.exe"),
            "C:/ProgramData/miniconda3/Scripts/conda.exe",
            "C:/ProgramData/anaconda3/Scripts/conda.exe"
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    
    return None

def check_conda_environment(logger: logging.Logger) -> bool:
    """Vérifie si l'environnement conda existe"""
    conda_exe = find_conda_executable()
    if not conda_exe:
        logger.error("❌ Conda non trouvé sur le système")
        return False
    
    try:
        # Lister les environnements
        result = subprocess.run(
            [conda_exe, "env", "list"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Vérifier si notre environnement existe
        if CONDA_ENV_NAME in result.stdout:
            logger.info(f"[OK] Environnement conda '{CONDA_ENV_NAME}' trouvé")
            return True
        else:
            logger.error(f"[ERROR] Environnement conda '{CONDA_ENV_NAME}' non trouvé")
            logger.info("[INFO] Conseil: Créez l'environnement avec:")
            logger.info(f"   conda env create -f environment.yml")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] Erreur lors de la vérification conda: {e}")
        return False

def run_orchestrator_with_conda(args: argparse.Namespace, logger: logging.Logger) -> bool:
    """Lance l'orchestrateur via conda run"""
    conda_exe = find_conda_executable()
    if not conda_exe:
        return False
    
    # Construction de la commande orchestrateur
    orchestrator_cmd = [
        "python", "-m", ORCHESTRATOR_PATH
    ]
    
    # Ajout des options selon les arguments
    if args.visible:
        orchestrator_cmd.append("--visible")
    elif args.headless:
        orchestrator_cmd.append("--headless")
    
    if args.frontend:
        orchestrator_cmd.append("--frontend")
    
    if args.backend_only:
        orchestrator_cmd.append("--start")
        # Note: pas d'option --no-frontend, on n'active pas --frontend
    
    if args.config:
        orchestrator_cmd.extend(["--config", args.config])
    
    if args.timeout:
        orchestrator_cmd.extend(["--timeout", str(args.timeout)])
    
    # Commande complète à exécuter directement (en supposant que l'environnement est activé)
    full_cmd = orchestrator_cmd # Utiliser directement orchestrator_cmd
    
    print(f"\n{Colors.GREEN}🚀 LANCEMENT ORCHESTRATEUR (direct après activation){Colors.END}")
    print(f"{Colors.YELLOW}📋 Commande:{Colors.END} {' '.join(full_cmd)}")
    print(f"{Colors.YELLOW}🐍 Environnement (attendu):{Colors.END} {CONDA_ENV_NAME}")
    print()
    
    try:
        # Changement vers le répertoire projet
        os.chdir(PROJECT_ROOT)
        
        # Préparer l'environnement pour la commande conda run
        env_vars = os.environ.copy()
        # S'assurer que PROJECT_ROOT est dans PYTHONPATH pour l'exécution de l'orchestrateur
        project_root_str = str(PROJECT_ROOT)
        current_python_path = env_vars.get('PYTHONPATH', '')
        if project_root_str not in current_python_path.split(os.pathsep):
            env_vars['PYTHONPATH'] = project_root_str + os.pathsep + current_python_path
        else:
            env_vars['PYTHONPATH'] = current_python_path

        logger.info(f"PYTHONPATH pour conda run: {env_vars['PYTHONPATH']}")

        # TEST D'IMPORTATION de l'application ASGI avant de lancer l'orchestrateur (TEMPORAIREMENT COMMENTÉ POUR TEST MANUEL)
        # logger.info("Tentative d'importation manuelle de l'application ASGI (depuis start_webapp.py)...")
        # try:
        #     # S'assurer que le PROJECT_ROOT est bien dans sys.path pour ce test
        #     # car l'orchestrateur et le backend_manager en dépendent.
        #     if str(PROJECT_ROOT) not in sys.path:
        #         sys.path.insert(0, str(PROJECT_ROOT))
        #     from argumentation_analysis.services.web_api import app as asgi_app_test
        #     logger.info(f"Importation de test réussie: {asgi_app_test}")
        # except Exception as import_err:
        #     logger.error("ERREUR D'IMPORTATION DE L'APPLICATION ASGI (depuis start_webapp.py):", exc_info=True)
        #     logger.error("Veuillez corriger l'erreur d'importation ci-dessus avant de continuer.")
        #     return False # Arrêter ici si l'import échoue

        # Lancement avec gestion interactive et environnement modifié
        # L'activation de l'environnement est gérée par le script appelant (activate_project_env.ps1)
        # On exécute donc directement la commande python.
        process = subprocess.run(
            full_cmd, # La commande est maintenant juste ["python", "-m", "scripts.webapp.unified_web_orchestrator", ...]
            cwd=PROJECT_ROOT,
            check=False, # Ne pas lever d'exception sur code de retour non-zéro
            env=env_vars # Passer les variables d'environnement modifiées (surtout PYTHONPATH)
        )
        
        success = process.returncode == 0
        if success:
            print(f"\n{Colors.GREEN}✅ APPLICATION LANCÉE AVEC SUCCÈS{Colors.END}")
        else:
            print(f"\n{Colors.RED}❌ ÉCHEC DU LANCEMENT (code: {process.returncode}){Colors.END}")
        
        return success
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 INTERRUPTION UTILISATEUR{Colors.END}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
        return False

def fallback_direct_launch(args: argparse.Namespace, logger: logging.Logger) -> bool:
    """Lancement direct sans conda (fallback)"""
    logger.warning("⚠️  Tentative de lancement direct (sans conda)")
    
    try:
        # Ajout du répertoire projet au Python path
        sys.path.insert(0, str(PROJECT_ROOT))
        
        # Import et lancement direct
        from scripts.webapp.unified_web_orchestrator import main as orchestrator_main
        
        # Simulation des arguments sys.argv pour l'orchestrateur
        original_argv = sys.argv.copy()
        sys.argv = ["unified_web_orchestrator.py"]
        
        if args.visible:
            sys.argv.append("--visible")
        elif args.headless:
            sys.argv.append("--headless")
        
        if args.frontend:
            sys.argv.append("--frontend")
        
        if args.backend_only:
            sys.argv.append("--start")
            # Note: pas d'argument --frontend = backend seulement
        
        if args.config:
            sys.argv.extend(["--config", args.config])
        
        try:
            orchestrator_main()
            return True
        finally:
            sys.argv = original_argv
            
    except ImportError as e:
        logger.error(f"❌ Import impossible: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement direct: {e}")
        return False

def create_argument_parser() -> argparse.ArgumentParser:
    """Crée le parser d'arguments"""
    parser = argparse.ArgumentParser(
        description="[LAUNCH] Lanceur simplifié pour l'application web Intelligence Symbolique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLES D'USAGE:
  python start_webapp.py                    # Démarrage complet par défaut
  python start_webapp.py --visible          # Interface visible (debugging)
  python start_webapp.py --frontend         # Avec interface React
  python start_webapp.py --backend-only     # API seulement
  python start_webapp.py --config custom.yml # Configuration personnalisée

NOTES:
  - Active automatiquement l'environnement conda 'projet-is'
  - Remplace l'ancien start_web_application.ps1
  - Par défaut: mode headless, backend seulement
  - Gestion d'erreurs intégrée et logs détaillés
        """
    )
    
    # Options d'affichage
    display_group = parser.add_mutually_exclusive_group()
    display_group.add_argument(
        '--visible', action='store_true',
        help='Interface browser visible (désactive headless)'
    )
    display_group.add_argument(
        '--headless', action='store_true', default=True,
        help='Mode headless (par défaut)'
    )
    
    # Options de composants
    component_group = parser.add_mutually_exclusive_group()
    component_group.add_argument(
        '--frontend', action='store_true',
        help='Lance avec interface React frontend'
    )
    component_group.add_argument(
        '--backend-only', action='store_true', default=True,
        help='Backend API seulement (par défaut)'
    )
    
    # Configuration
    parser.add_argument(
        '--config', type=str,
        default='config/webapp_config.yml',
        help='Fichier de configuration (défaut: config/webapp_config.yml)'
    )
    
    parser.add_argument(
        '--timeout', type=int, default=10,
        help='Timeout en minutes (défaut: 10)'
    )
    
    # Options système
    parser.add_argument(
        '--no-conda', action='store_true',
        help='Désactive l\'activation conda (lancement direct)'
    )
    
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Logs détaillés'
    )
    
    return parser

def main():
    """Fonction principale"""
    try:
        # Configuration logging
        logger = setup_logging()
        
        # Parsing arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        if args.verbose:
            logger.setLevel(logging.DEBUG)
        
        # Bannière de démarrage
        print_banner()
        
        # Validation environnement conda (sauf si --no-conda)
        if not args.no_conda:
            safe_print(f"{Colors.BLUE}[CHECK] VÉRIFICATION ENVIRONNEMENT{Colors.END}")
            if not check_conda_environment(logger):
                safe_print(f"\n{Colors.RED}[ERROR] ÉCHEC: Environnement conda non disponible{Colors.END}")
                safe_print(f"{Colors.YELLOW}[INFO] Solutions:{Colors.END}")
                safe_print("   1. Créer l'environnement: conda env create -f environment.yml")
                safe_print("   2. Lancement direct: python start_webapp.py --no-conda")
                sys.exit(1)
            
            # Lancement via conda
            success = run_orchestrator_with_conda(args, logger)
        else:
            # Lancement direct
            success = fallback_direct_launch(args, logger)
        
        # Résultat final
        if success:
            safe_print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] SUCCÈS: Application démarrée{Colors.END}")
        else:
            safe_print(f"\n{Colors.RED}{Colors.BOLD}[FAILURE] ÉCHEC: Problème lors du démarrage{Colors.END}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        safe_print(f"\n{Colors.YELLOW}[STOP] ARRÊT DEMANDÉ PAR L'UTILISATEUR{Colors.END}")
        sys.exit(130)
    except Exception as e:
        safe_print(f"\n{Colors.RED}[FAILURE] ERREUR FATALE: {e}{Colors.END}")
        if '--verbose' in sys.argv or '-v' in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
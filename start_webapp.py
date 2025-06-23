#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Lancement Robuste - Application Web Intelligence Symbolique
======================================================================

OBJECTIF :
- Remplace l'ancien start_web_application.ps1 et les logiques de lancement complexes.
- Utilise EXCLUSIVEMENT `conda run` via le `CondaManager` pour garantir une exécution dans le bon environnement.
- Lance l'UnifiedWebOrchestrator avec des options par défaut intelligentes.
- Interface CLI simple et intuitive.

USAGE :
    python start_webapp.py                    # Démarrage complet par défaut
    python start_webapp.py --visible          # Interface visible (non headless)
    python start_webapp.py --frontend         # Avec frontend React
    python start_webapp.py --backend-only     # Backend seulement
    python start_webapp.py --help             # Aide complète

Auteur: Projet Intelligence Symbolique EPITA
Date: 23/06/2025
Version: 2.0.0
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List

# Assurer que le CWD est la racine du projet pour la robustesse des imports
os.chdir(Path(__file__).parent.absolute())
sys.path.insert(0, str(Path.cwd()))

from project_core.environment.conda_manager import CondaManager

# Configuration encodage UTF-8 pour Windows
def configure_utf8():
    """Configure UTF-8 pour éviter les problèmes d'encodage Unicode"""
    if os.name == 'nt':
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except (ImportError, AttributeError):
            pass

configure_utf8()

PROJECT_ROOT = Path.cwd()
CONDA_ENV_NAME = "projet-is"
ORCHESTRATOR_MODULE_PATH = "argumentation_analysis.webapp.orchestrator"

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
            ascii_text = text.encode('ascii', 'replace').decode('ascii')
            print(ascii_text)

def setup_logging() -> logging.Logger:
    """Configure le logging pour le script."""
    logger = logging.getLogger('start_webapp')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def print_banner():
    """Affiche la bannière de démarrage."""
    banner = f"""
{Colors.BLUE}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║             [LAUNCH] DÉMARRAGE APPLICATION WEB - EPITA      ║
║                    Intelligence Symbolique                   ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.YELLOW}[ENV] ENVIRONNEMENT:{Colors.END} {CONDA_ENV_NAME}
{Colors.YELLOW}[DIR] PROJET:{Colors.END} {PROJECT_ROOT}
{Colors.YELLOW}[TARGET] ORCHESTRATEUR:{Colors.END} {ORCHESTRATOR_MODULE_PATH}
"""
    safe_print(banner)

def create_argument_parser() -> argparse.ArgumentParser:
    """Crée le parser d'arguments pour le script."""
    parser = argparse.ArgumentParser(
        description="[LAUNCH] Lanceur robuste pour l'application web Intelligence Symbolique.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLES D'USAGE:
  python start_webapp.py                    # Démarrage complet par défaut
  python start_webapp.py --visible          # Interface visible (debugging)
  python start_webapp.py --frontend         # Avec interface React
  python start_webapp.py --backend-only     # API seulement
  python start_webapp.py --config custom.yml # Configuration personnalisée

NOTES:
  - Garantit l'exécution dans l'environnement conda 'projet-is' via `conda run`.
  - Remplace les anciens scripts de lancement et les mécanismes de fallback.
  - Par défaut: mode headless, backend seulement.
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
        help='Lance avec interface React frontend (inclut le backend)'
    )
    component_group.add_argument(
        '--backend-only', action='store_true', default=True,
        help='Backend API seulement (par défaut)'
    )

    # Configuration
    parser.add_argument(
        '--config', type=str,
        default='config/webapp_config.yml',
        help='Fichier de configuration YAML (défaut: config/webapp_config.yml)'
    )

    parser.add_argument(
        '--timeout', type=int, default=10,
        help="Timeout en minutes pour l'orchestrateur (défaut: 10)"
    )

    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Logs détaillés'
    )

    return parser

def main():
    """Point d'entrée principal du script."""
    logger = setup_logging()
    parser = create_argument_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    print_banner()

    try:
        conda_manager = CondaManager(logger)

        # Construction de la commande pour l'orchestrateur
        orchestrator_cmd_list: List[str] = ["python", "-m", ORCHESTRATOR_MODULE_PATH]

        if args.visible:
            orchestrator_cmd_list.append("--visible")
        elif args.headless:
            orchestrator_cmd_list.append("--headless")

        if args.frontend:
            orchestrator_cmd_list.append("--frontend")
            orchestrator_cmd_list.append("--start") # --frontend inclut le backend

        if args.backend_only:
            orchestrator_cmd_list.append("--start")

        if args.config:
            orchestrator_cmd_list.extend(["--config", args.config])

        if args.timeout:
            orchestrator_cmd_list.extend(["--timeout", str(args.timeout)])

        safe_print(f"\n{Colors.GREEN}🚀 LANCEMENT VIA CONDAMANAGER...{Colors.END}")
        safe_print(f"{Colors.YELLOW}📋 Commande préparée:{Colors.END} {' '.join(orchestrator_cmd_list)}")

        # Lancement via CondaManager qui gère `conda run` de manière robuste
        result = conda_manager.run_in_conda_env(
            command=orchestrator_cmd_list,
            env_name=CONDA_ENV_NAME
        )

        if result and result.returncode == 0:
            safe_print(f"\n{Colors.GREEN}{Colors.BOLD}✅ SUCCÈS: Le processus s'est terminé proprement.{Colors.END}")
            sys.exit(0)
        else:
            error_code = result.returncode if result else 'inconnu'
            safe_print(f"\n{Colors.RED}{Colors.BOLD}❌ ÉCHEC: Problème lors du démarrage (code: {error_code}).{Colors.END}")
            safe_print(f"{Colors.YELLOW}Veuillez vérifier les logs ci-dessus pour les détails de l'erreur.{Colors.END}")
            sys.exit(1)

    except (FileNotFoundError, ValueError) as e:
        safe_print(f"\n{Colors.RED}{Colors.BOLD}[ERREUR FATALE] {type(e).__name__}: {e}{Colors.END}")
        safe_print(f"{Colors.YELLOW}Assurez-vous que l'environnement Conda '{CONDA_ENV_NAME}' existe et que `conda` est dans le PATH.{Colors.END}")
        sys.exit(1)
    except KeyboardInterrupt:
        safe_print(f"\n{Colors.YELLOW}[STOP] ARRÊT DEMANDÉ PAR L'UTILISATEUR.{Colors.END}")
        sys.exit(130)
    except Exception as e:
        safe_print(f"\n{Colors.RED}{Colors.BOLD}[ERREUR INATTENDUE] {type(e).__name__}: {e}{Colors.END}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
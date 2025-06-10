"""
Gestionnaire de setup et configuration projet
===========================================

Centralise la configuration et le setup du projet.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
import argparse
from typing import Dict, List, Optional, Any

from .common_utils import Logger, LogLevel
from .environment_manager import EnvironmentManager
from .validation_engine import ValidationEngine


class ProjectSetup:
    """Gestionnaire de setup projet"""
    
    def __init__(self, logger: Logger = None):
        self.logger = logger or Logger()
        self.env_manager = EnvironmentManager(self.logger)
        self.validator = ValidationEngine(self.logger)
    
    def setup_environment(self, force: bool = False) -> bool:
        """Setup complet de l'environnement"""
        self.logger.info("Setup de l'environnement projet...")
        
        # Vérifications préalables
        issues = self.validator.check_prerequisites()
        if issues and not force:
            self.logger.error("Setup impossible - Prérequis manquants")
            for issue in issues:
                self.logger.error(f"  - {issue}")
            return False
        
        # Configuration variables d'environnement
        self.env_manager.setup_environment_variables()
        
        self.logger.success("Setup environnement terminé")
        return True
    
    def check_project_status(self) -> Dict[str, Any]:
        """Vérifie le statut complet du projet"""
        status = {
            "conda_available": self.env_manager.check_conda_available(),
            "conda_env_exists": self.env_manager.check_conda_env_exists(),
            "python_version_ok": self.env_manager.check_python_version(),
            "prerequisites_ok": len(self.validator.check_prerequisites()) == 0
        }
        
        status["overall_status"] = all(status.values())
        return status


def setup_environment(force: bool = False, logger: Logger = None) -> bool:
    """Fonction utilitaire de setup"""
    setup = ProjectSetup(logger)
    return setup.setup_environment(force)


def check_project_status(logger: Logger = None) -> Dict[str, Any]:
    """Fonction utilitaire de vérification statut"""
    setup = ProjectSetup(logger)
    return setup.check_project_status()


def main():
    """Point d'entrée CLI"""
    parser = argparse.ArgumentParser(description="Setup projet")
    parser.add_argument('--setup', action='store_true', help='Setup environnement')
    parser.add_argument('--status', action='store_true', help='Vérifier statut')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    logger = Logger(verbose=args.verbose)
    
    if args.setup:
        success = setup_environment(logger=logger)
        sys.exit(0 if success else 1)
    elif args.status:
        status = check_project_status(logger)
        for key, value in status.items():
            logger.info(f"{key}: {'✓' if value else '✗'}")
        sys.exit(0 if status["overall_status"] else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
"""
Modules Python mutualisés pour les scripts de projet
===================================================

Ce package contient les composants réutilisables pour l'orchestration
des scripts PowerShell et shell du projet Intelligence Symbolique.

Modules disponibles:
- common_utils: Utilitaires de base (logging, couleurs, etc.)
- environment_manager: Gestion des environnements Python/conda
- test_runner: Orchestration des tests et pytest
- validation_engine: Moteurs de validation et vérification
- project_setup: Setup et configuration du projet

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

__version__ = "1.0.0"
__author__ = "Intelligence Symbolique EPITA"

from .common_utils import *
from .environment_manager import *
from .test_config_definition import *
from .validation.validation_engine import *
from .project_setup import *

__all__ = [
    # Common utils
    "Logger",
    "ColoredOutput",
    "format_timestamp",
    "safe_exit",
    # Environment manager
    "EnvironmentManager",
    "check_conda_env",
    "activate_project_env",
    # Test runner
    "TestRunner",
    "TestConfig",
    "TestMode",
    "run_pytest",
    "run_python_script",
    # Validation engine
    "ValidationEngine",
    "check_prerequisites",
    "validate_system",
    # Project setup
    "ProjectSetup",
    "setup_environment",
    "check_project_status",
]

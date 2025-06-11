"""
Project Core - Module unifié pour la gestion des services
Remplace les patterns PowerShell/CMD identifiés dans la cartographie

Modules disponibles:
- service_manager: Gestion centralisée des services avec failover
- test_runner: Exécution unifiée des tests avec gestion des services

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

from .service_manager import (
    ServiceManager,
    ServiceConfig, 
    PortManager,
    ProcessCleanup,
    create_default_configs
)

from .test_runner import (
    TestRunner,
    TestConfig,
    TestType,
    EnvironmentManager
)

__version__ = "1.0.0"
__all__ = [
    'ServiceManager',
    'ServiceConfig',
    'PortManager', 
    'ProcessCleanup',
    'create_default_configs',
    'TestRunner',
    'TestConfig',
    'TestType',
    'EnvironmentManager'
]
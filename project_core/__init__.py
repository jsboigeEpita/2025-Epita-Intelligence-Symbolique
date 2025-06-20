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

# Les modules de test ont été refactorisés dans core_from_scripts
# Pour éviter de polluer l'api publique de project_core, ils ne sont
# plus exposés ici. Les utilisateurs devraient importer directement depuis
# project_core.core_from_scripts si nécessaire.

__version__ = "1.0.0"
__all__ = [
    'ServiceManager',
    'ServiceConfig',
    'PortManager',
    'ProcessCleanup',
    'create_default_configs'
]
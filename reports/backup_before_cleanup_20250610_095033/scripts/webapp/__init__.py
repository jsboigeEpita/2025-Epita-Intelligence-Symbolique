#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module WebApp - Orchestrateur unifié d'application web Python
=============================================================

Module principal pour l'orchestration d'applications web avec :
- Gestionnaire backend Flask avec failover
- Gestionnaire frontend React optionnel
- Runner de tests Playwright intégrés
- Nettoyage automatique des processus
- Tracing complet des opérations

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

from .unified_web_orchestrator import UnifiedWebOrchestrator, WebAppStatus, TraceEntry, WebAppInfo
from .backend_manager import BackendManager
from .frontend_manager import FrontendManager
from .playwright_runner import PlaywrightRunner
from .process_cleaner import ProcessCleaner

__version__ = "1.0.0"
__author__ = "Projet Intelligence Symbolique EPITA"

__all__ = [
    'UnifiedWebOrchestrator',
    'BackendManager', 
    'FrontendManager',
    'PlaywrightRunner',
    'ProcessCleaner',
    'WebAppStatus',
    'TraceEntry',
    'WebAppInfo'
]
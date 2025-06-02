#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour évaluer les procédures de récupération après erreur.
"""

import sys
import os
import time
# import json # json n'est plus utilisé directement ici
# from unittest.mock import patch, MagicMock # unittest.mock n'est plus utilisé directement ici

# Ajouter le répertoire du projet au PYTHONPATH
# sys.path.insert(0, os.path.abspath('.')) # Plus nécessaire si les tests sont correctement structurés

from argumentation_analysis.core.utils.error_management import StateManager, ErrorRecoveryManager

def test_network_error_recovery():
    print("\n=== Test de récupération après erreur réseau ===")
    state_manager = StateManager()
    recovery_manager = ErrorRecoveryManager(state_manager)
    
    # Ajouter une erreur réseau récupérable
    state_manager.add_error("network", "Connection timed out after 30 seconds", "FetchService", True)
    
    # Tenter de récupérer
    success = recovery_manager.recover_from_errors()
    
    print(f"Récupération réussie: {success}")
    print(f"Erreurs restantes: {len(state_manager.get_errors())}")
    print(f"Erreurs traitées: {sum(1 for e in state_manager.get_errors() if e.get('handled', False))}")

def test_service_error_recovery():
    print("\n=== Test de récupération après erreur de service ===")
    state_manager = StateManager()
    recovery_manager = ErrorRecoveryManager(state_manager)
    
    # Ajouter une erreur de service récupérable
    state_manager.add_error("service", "Rate limit exceeded. Please try again in 20 seconds.", "LLMService", True)
    
    # Ajouter une erreur de service non récupérable
    state_manager.add_error("service", "Invalid API key provided.", "LLMService", False)
    
    # Tenter de récupérer
    success = recovery_manager.recover_from_errors()
    
    print(f"Récupération réussie: {success}")
    print(f"Erreurs restantes: {len(state_manager.get_errors())}")
    print(f"Erreurs traitées: {sum(1 for e in state_manager.get_errors() if e.get('handled', False))}")
    print(f"Erreurs non récupérables: {len(state_manager.get_unrecoverable_errors())}")

def test_validation_error_recovery():
    print("\n=== Test de récupération après erreur de validation ===")
    state_manager = StateManager()
    recovery_manager = ErrorRecoveryManager(state_manager)
    
    # Ajouter une erreur de validation récupérable
    state_manager.add_error("validation", "Source 'Source incomplète': Chemin manquant", "ValidationService", True)
    
    # Tenter de récupérer
    success = recovery_manager.recover_from_errors()
    
    print(f"Récupération réussie: {success}")
    print(f"Erreurs restantes: {len(state_manager.get_errors())}")
    print(f"Erreurs traitées: {sum(1 for e in state_manager.get_errors() if e.get('handled', False))}")

def test_multiple_errors_recovery():
    print("\n=== Test de récupération après erreurs multiples ===")
    state_manager = StateManager()
    recovery_manager = ErrorRecoveryManager(state_manager)
    
    # Ajouter plusieurs erreurs
    state_manager.add_error("network", "Connection timed out after 30 seconds", "FetchService", True)
    state_manager.add_error("service", "Rate limit exceeded. Please try again in 20 seconds.", "LLMService", True)
    state_manager.add_error("validation", "Source 'Source incomplète': Chemin manquant", "ValidationService", True)
    state_manager.add_error("service", "Invalid API key provided.", "LLMService", False)
    
    # Tenter de récupérer
    success = recovery_manager.recover_from_errors()
    
    print(f"Récupération réussie: {success}")
    print(f"Erreurs restantes: {len(state_manager.get_errors())}")
    print(f"Erreurs traitées: {sum(1 for e in state_manager.get_errors() if e.get('handled', False))}")
    print(f"Erreurs non récupérables: {len(state_manager.get_unrecoverable_errors())}")

def test_clear_errors():
    print("\n=== Test d'effacement des erreurs ===")
    state_manager = StateManager()
    
    # Ajouter plusieurs erreurs
    state_manager.add_error("network", "Connection timed out after 30 seconds", "FetchService", True)
    state_manager.add_error("service", "Rate limit exceeded. Please try again in 20 seconds.", "LLMService", True)
    
    print(f"Erreurs avant effacement: {len(state_manager.get_errors())}")
    
    # Effacer les erreurs
    state_manager.clear_errors()
    
    print(f"Erreurs après effacement: {len(state_manager.get_errors())}")

if __name__ == "__main__":
    print("=== Tests des procédures de récupération après erreur ===")
    test_network_error_recovery()
    test_service_error_recovery()
    test_validation_error_recovery()
    test_multiple_errors_recovery()
    test_clear_errors()
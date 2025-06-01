#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour évaluer les procédures de récupération après erreur.
"""

import sys
import os
import time
import json
from unittest.mock import patch, MagicMock

# Ajouter le répertoire du projet au PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))

# Définir une classe StateManager simplifiée pour les tests
class StateManager:
    def __init__(self):
        self.state = {
            "tasks": [],
            "arguments": [],
            "fallacies": [],
            "belief_sets": {},
            "extracts": [],
            "errors": [],
            "conclusion": None
        }
    
    def add_error(self, error_type, error_message, agent_name=None, recoverable=True):
        """Ajoute une erreur à l'état."""
        error = {
            "type": error_type,
            "message": error_message,
            "timestamp": time.time(),
            "agent": agent_name,
            "recoverable": recoverable
        }
        self.state["errors"].append(error)
        print(f"Erreur ajoutée: {error_type} - {error_message}")
        return error
    
    def get_errors(self):
        """Récupère toutes les erreurs de l'état."""
        return self.state["errors"]
    
    def get_recoverable_errors(self):
        """Récupère les erreurs récupérables de l'état."""
        return [e for e in self.state["errors"] if e.get("recoverable", True)]
    
    def get_unrecoverable_errors(self):
        """Récupère les erreurs non récupérables de l'état."""
        return [e for e in self.state["errors"] if not e.get("recoverable", True)]
    
    def clear_errors(self):
        """Efface toutes les erreurs de l'état."""
        self.state["errors"] = []
        print("Erreurs effacées.")
    
    def mark_error_as_handled(self, error_index):
        """Marque une erreur comme traitée."""
        if 0 <= error_index < len(self.state["errors"]):
            self.state["errors"][error_index]["handled"] = True
            print(f"Erreur {error_index} marquée comme traitée.")
            return True
        return False

# Définir une classe ErrorRecoveryManager simplifiée pour les tests
class ErrorRecoveryManager:
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
    def handle_error(self, error):
        """Gère une erreur spécifique."""
        error_type = error.get("type", "unknown")
        
        if error_type == "network":
            return self._handle_network_error(error)
        elif error_type == "service":
            return self._handle_service_error(error)
        elif error_type == "validation":
            return self._handle_validation_error(error)
        else:
            print(f"Type d'erreur inconnu: {error_type}")
            return False
    
    def _handle_network_error(self, error):
        """Gère une erreur réseau."""
        message = error.get("message", "")
        
        if "timeout" in message.lower():
            print("Tentative de récupération après timeout...")
            # Simuler une récupération après timeout
            time.sleep(0.001)
            return True
        elif "dns" in message.lower():
            print("Tentative de récupération après erreur DNS...")
            # Simuler une récupération après erreur DNS
            time.sleep(0.001)
            return True
        else:
            print("Erreur réseau non récupérable.")
            return False
    
    def _handle_service_error(self, error):
        """Gère une erreur de service."""
        message = error.get("message", "")
        
        if "rate limit" in message.lower():
            print("Tentative de récupération après rate limit...")
            # Simuler une récupération après rate limit
            time.sleep(0.001)
            return True
        elif "api key" in message.lower():
            print("Erreur d'API key non récupérable.")
            return False
        else:
            print("Tentative de récupération après erreur de service générique...")
            time.sleep(0.001)
            return True
    
    def _handle_validation_error(self, error):
        """Gère une erreur de validation."""
        message = error.get("message", "")
        
        if "missing" in message.lower():
            print("Tentative de récupération après champ manquant...")
            # Simuler une récupération après champ manquant
            time.sleep(0.001)
            return True
        elif "invalid" in message.lower():
            print("Tentative de récupération après valeur invalide...")
            # Simuler une récupération après valeur invalide
            time.sleep(0.001)
            return True
        else:
            print("Erreur de validation non récupérable.")
            return False
    
    def recover_from_errors(self):
        """Tente de récupérer de toutes les erreurs récupérables."""
        recoverable_errors = self.state_manager.get_recoverable_errors()
        
        if not recoverable_errors:
            print("Aucune erreur récupérable à traiter.")
            return True
        
        success = True
        for i, error in enumerate(recoverable_errors):
            if not error.get("handled", False):
                print(f"Tentative de récupération de l'erreur {i}: {error['type']} - {error['message']}")
                if self.handle_error(error):
                    self.state_manager.mark_error_as_handled(i)
                else:
                    success = False
        
        return success

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
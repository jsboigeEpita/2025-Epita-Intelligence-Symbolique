#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time


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
            "conclusion": None,
        }

    def add_error(self, error_type, error_message, agent_name=None, recoverable=True):
        """Ajoute une erreur à l'état."""
        error = {
            "type": error_type,
            "message": error_message,
            "timestamp": time.time(),
            "agent": agent_name,
            "recoverable": recoverable,
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
                print(
                    f"Tentative de récupération de l'erreur {i}: {error['type']} - {error['message']}"
                )
                if self.handle_error(error):
                    self.state_manager.mark_error_as_handled(i)
                else:
                    success = False

        return success

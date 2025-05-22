"""
Exemple simple d'utilisation du système de communication multi-canal.

Ce script démontre l'utilisation de base du système de communication multi-canal
avec un échange simple entre un agent stratégique et un agent tactique.
"""

import time
import threading
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentation_analysis.core.communication.strategic_adapter import StrategicAdapter
from argumentation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentation_analysis.core.communication.message import MessagePriority


def main():
    # Créer et initialiser le middleware
    print("Initialisation du middleware...")
    middleware = MessageMiddleware()
    middleware.initialize()

    # Créer et enregistrer le canal hiérarchique
    print("Création du canal hiérarchique...")
    hierarchical_channel = HierarchicalChannel("hierarchical")
    middleware.register_channel(hierarchical_channel)
    middleware.initialize_protocols()

    # Créer les adaptateurs
    print("Création des adaptateurs...")
    strategic_adapter = StrategicAdapter("strategic-agent-1", middleware)
    tactical_adapter = TacticalAdapter("tactical-agent-1", middleware)

    # Fonction simulant un agent tactique
    def tactical_agent():
        print("Agent tactique en attente d'une directive...")
        # Recevoir la directive
        directive = tactical_adapter.receive_directive(timeout=5.0)
        
        if directive:
            print(f"Directive reçue: {directive.content}")
            
            # Simuler un traitement
            print("Traitement de la directive...")
            time.sleep(1.0)
            
            # Envoyer un rapport
            print("Envoi d'un rapport...")
            tactical_adapter.send_report(
                report_type="status_update",
                content={"status": "in_progress", "completion": 50},
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )

    # Démarrer un thread pour l'agent tactique
    tactical_thread = threading.Thread(target=tactical_agent)
    tactical_thread.start()

    # Simuler un agent stratégique
    print("Agent stratégique émet une directive...")
    # Émettre une directive
    strategic_adapter.issue_directive(
        directive_type="analyze_text",
        parameters={"text_id": "text-123"},
        recipient_id="tactical-agent-1",
        priority=MessagePriority.HIGH
    )

    # Attendre un peu
    time.sleep(0.5)

    # Recevoir un rapport
    print("Agent stratégique en attente d'un rapport...")
    report = strategic_adapter.receive_report(timeout=5.0)
    if report:
        print(f"Rapport reçu: {report.content}")
    else:
        print("Aucun rapport reçu dans le délai imparti.")

    # Attendre que le thread se termine
    tactical_thread.join()
    
    print("Communication terminée.")


if __name__ == "__main__":
    main()
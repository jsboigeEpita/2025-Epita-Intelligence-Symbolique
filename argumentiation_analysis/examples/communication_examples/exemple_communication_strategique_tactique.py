"""
Exemple de communication entre agents stratégiques et tactiques.

Ce script démontre un flux de travail complet entre les niveaux stratégique et tactique,
incluant l'émission de directives, la remontée de rapports, et l'utilisation de l'interface
stratégique-tactique pour traduire les objectifs et traiter les rapports.
"""

import time
import threading
import asyncio
from argumentiation_analysis.core.communication.middleware import MessageMiddleware
from argumentiation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentiation_analysis.core.communication.strategic_adapter import StrategicAdapter
from argumentiation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentiation_analysis.core.communication.message import MessagePriority, MessageType
from argumentiation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentiation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentiation_analysis.orchestration.hierarchical.tactical.state import TacticalState


def main():
    # Créer et initialiser le middleware
    print("Initialisation du middleware...")
    middleware = MessageMiddleware()
    middleware.initialize()

    # Créer et enregistrer le canal hiérarchique
    print("Création du canal hiérarchique...")
    hierarchical_channel = HierarchicalChannel(
        name="hierarchical",
        config={
            "priority_levels": 4,
            "message_ordering": True,
            "delivery_guarantee": True
        }
    )
    middleware.register_channel(hierarchical_channel)
    middleware.initialize_protocols()

    # Créer les états
    strategic_state = StrategicState()
    tactical_state = TacticalState()

    # Créer l'interface stratégique-tactique
    interface = StrategicTacticalInterface(strategic_state, tactical_state, middleware)

    # Créer les adaptateurs
    print("Création des adaptateurs...")
    strategic_adapter = StrategicAdapter("strategic-agent-1", middleware)
    tactical_adapter = TacticalAdapter("tactical-agent-1", middleware)

    # Fonction simulant un agent tactique
    def tactical_agent():
        print("Agent tactique démarré...")
        
        # Recevoir les directives
        directives_received = 0
        while directives_received < 2:
            directive = tactical_adapter.receive_directive(timeout=5.0)
            
            if directive:
                directives_received += 1
                print(f"Directive {directives_received} reçue: {directive.content}")
                
                # Simuler un traitement
                print(f"Traitement de la directive {directives_received}...")
                time.sleep(1.0)
                
                # Envoyer un rapport de progression
                print(f"Envoi d'un rapport de progression pour la directive {directives_received}...")
                tactical_adapter.send_report(
                    report_type="progress_update",
                    content={
                        "directive_id": directive.id,
                        "status": "in_progress",
                        "completion": 50,
                        "details": {
                            "current_step": f"Étape 1 de la directive {directives_received}",
                            "estimated_completion_time": time.time() + 60
                        }
                    },
                    recipient_id="strategic-agent-1",
                    priority=MessagePriority.NORMAL
                )
                
                # Simuler la fin du traitement
                time.sleep(2.0)
                
                # Envoyer un rapport final
                print(f"Envoi d'un rapport final pour la directive {directives_received}...")
                tactical_adapter.send_report(
                    report_type="completion_report",
                    content={
                        "directive_id": directive.id,
                        "status": "completed",
                        "completion": 100,
                        "results": {
                            "success": True,
                            "output": f"Résultat de la directive {directives_received}",
                            "metrics": {
                                "execution_time": 3.0,
                                "resources_used": "CPU: 50%, Memory: 200MB"
                            }
                        }
                    },
                    recipient_id="strategic-agent-1",
                    priority=MessagePriority.HIGH
                )
        
        print("Agent tactique: toutes les directives ont été traitées.")

    # Fonction simulant un agent stratégique
    def strategic_agent():
        print("Agent stratégique démarré...")
        
        # Définir les objectifs stratégiques
        objectives = [
            {
                "id": "obj-1",
                "description": "Analyser la structure argumentative du texte",
                "priority": "high"
            },
            {
                "id": "obj-2",
                "description": "Identifier les sophismes potentiels",
                "priority": "medium"
            }
        ]
        
        # Mettre à jour l'état stratégique
        strategic_state.set_objectives(objectives)
        
        # Traduire les objectifs en directives tactiques via l'interface
        print("Traduction des objectifs en directives tactiques...")
        tactical_directives = interface.translate_objectives(objectives)
        
        # Émettre les directives
        for directive in tactical_directives:
            print(f"Émission de la directive pour l'objectif {directive['objective_id']}...")
            strategic_adapter.issue_directive(
                directive_type=directive["directive_type"],
                parameters=directive["parameters"],
                recipient_id="tactical-agent-1",
                priority=MessagePriority.HIGH if directive["objective_id"] == "obj-1" else MessagePriority.NORMAL
            )
        
        # Recevoir et traiter les rapports
        reports_received = 0
        final_reports_received = 0
        
        while final_reports_received < 2:
            report = strategic_adapter.receive_report(timeout=10.0)
            
            if report:
                reports_received += 1
                print(f"Rapport {reports_received} reçu: {report.content}")
                
                # Traiter le rapport via l'interface
                strategic_info = interface.process_tactical_report(report.content)
                
                # Mettre à jour l'état stratégique
                if "objective_progress" in strategic_info:
                    for obj_id, progress in strategic_info["objective_progress"].items():
                        strategic_state.update_objective_progress(obj_id, progress)
                
                # Vérifier si c'est un rapport final
                if report.content.get("report_type") == "completion_report":
                    final_reports_received += 1
                    print(f"Rapport final {final_reports_received} traité.")
                    
                    # Si tous les rapports finaux ont été reçus, générer un résumé
                    if final_reports_received == 2:
                        print("Génération du résumé stratégique...")
                        summary = strategic_state.generate_summary()
                        print(f"Résumé stratégique: {summary}")
        
        print("Agent stratégique: tous les rapports ont été traités.")

    # Démarrer les threads pour les agents
    tactical_thread = threading.Thread(target=tactical_agent)
    strategic_thread = threading.Thread(target=strategic_agent)
    
    tactical_thread.start()
    strategic_thread.start()
    
    # Attendre que les threads se terminent
    tactical_thread.join()
    strategic_thread.join()
    
    print("Communication terminée.")


if __name__ == "__main__":
    main()
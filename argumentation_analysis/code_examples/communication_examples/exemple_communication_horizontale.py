"""
Exemple de communication horizontale entre agents.

Ce script démontre la communication horizontale entre agents de même niveau
en utilisant le canal de collaboration. Il illustre la création de groupes
de collaboration, l'échange de messages entre pairs, et la résolution
collaborative de problèmes.
"""

import time
import threading
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.collaboration_channel import CollaborationChannel
from argumentation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentation_analysis.core.communication.message import MessagePriority, MessageType


def main():
    # Créer et initialiser le middleware
    print("Initialisation du middleware...")
    middleware = MessageMiddleware()
    middleware.initialize()

    # Créer et enregistrer le canal de collaboration
    print("Création du canal de collaboration...")
    collaboration_channel = CollaborationChannel(
        name="collaboration",
        config={
            "max_participants": 10,
            "context_retention": True,
            "broadcast_enabled": True
        }
    )
    middleware.register_channel(collaboration_channel)
    
    # Configurer le routage pour le canal de collaboration
    middleware.add_routing_rule(MessageType.REQUEST, "collaboration")
    middleware.add_routing_rule(MessageType.RESPONSE, "collaboration")
    middleware.add_content_routing_rule("content.request_type", "collaboration", "collaboration")
    
    middleware.initialize_protocols()

    # Créer les adaptateurs pour les agents tactiques
    print("Création des adaptateurs...")
    tactical_adapter1 = TacticalAdapter("tactical-agent-1", middleware)
    tactical_adapter2 = TacticalAdapter("tactical-agent-2", middleware)
    tactical_adapter3 = TacticalAdapter("tactical-agent-3", middleware)

    # Créer un groupe de collaboration
    group_id = collaboration_channel.create_collaboration_group(
        "analyse-argumentative",
        ["tactical-agent-1", "tactical-agent-2", "tactical-agent-3"]
    )
    print(f"Groupe de collaboration créé avec ID: {group_id}")

    # Fonction simulant le premier agent tactique (coordinateur)
    def tactical_agent1():
        print("Agent tactique 1 (coordinateur) démarré...")
        
        # Diffuser un message au groupe
        print("Diffusion d'un message au groupe...")
        message = {
            "type": MessageType.INFORMATION,
            "sender": "tactical-agent-1",
            "content": {
                "info_type": "task_allocation",
                "task": "analyse_argumentative",
                "text_id": "text-123",
                "allocations": {
                    "tactical-agent-1": "structure_globale",
                    "tactical-agent-2": "identification_premisses",
                    "tactical-agent-3": "identification_conclusions"
                }
            },
            "priority": MessagePriority.HIGH
        }
        collaboration_channel.broadcast_to_group(group_id, message)
        
        # Attendre un peu
        time.sleep(1.0)
        
        # Recevoir les demandes d'assistance
        print("En attente de demandes d'assistance...")
        assistance_request = tactical_adapter1.receive_assistance_request(timeout=10.0)
        
        if assistance_request:
            print(f"Demande d'assistance reçue: {assistance_request.content}")
            
            # Fournir de l'aide
            print("Envoi d'une réponse d'assistance...")
            tactical_adapter1.send_assistance_response(
                request_id=assistance_request.id,
                response={
                    "solution": "Pour identifier les prémisses implicites, cherchez les suppositions nécessaires pour que l'argument soit valide.",
                    "examples": [
                        {
                            "text": "Il pleut, donc la route est mouillée.",
                            "implicit_premise": "Quand il pleut, les surfaces exposées deviennent mouillées."
                        }
                    ]
                },
                recipient_id=assistance_request.sender,
                priority=MessagePriority.HIGH
            )
        
        # Attendre les résultats des autres agents
        results = {}
        results_received = 0
        
        while results_received < 2:
            print("En attente des résultats...")
            message = tactical_adapter1.receive_message(
                timeout=10.0,
                filter_criteria={
                    "content.info_type": "task_result"
                }
            )
            
            if message:
                results_received += 1
                sender = message.sender
                result = message.content.get("result", {})
                results[sender] = result
                print(f"Résultat reçu de {sender}: {result}")
        
        # Combiner les résultats
        print("Combinaison des résultats...")
        combined_result = {
            "structure_globale": {
                "type": "argument_complexe",
                "nombre_arguments": 3
            },
            "premisses": results.get("tactical-agent-2", {}).get("premisses", []),
            "conclusions": results.get("tactical-agent-3", {}).get("conclusions", [])
        }
        
        # Diffuser le résultat combiné
        print("Diffusion du résultat combiné...")
        final_message = {
            "type": MessageType.INFORMATION,
            "sender": "tactical-agent-1",
            "content": {
                "info_type": "combined_result",
                "task": "analyse_argumentative",
                "text_id": "text-123",
                "result": combined_result
            },
            "priority": MessagePriority.NORMAL
        }
        collaboration_channel.broadcast_to_group(group_id, final_message)
        
        print("Agent tactique 1: tâche terminée.")

    # Fonction simulant le deuxième agent tactique (identification des prémisses)
    def tactical_agent2():
        print("Agent tactique 2 (identification des prémisses) démarré...")
        
        # Recevoir l'allocation de tâche
        print("En attente de l'allocation de tâche...")
        message = tactical_adapter2.receive_message(
            timeout=5.0,
            filter_criteria={
                "content.info_type": "task_allocation"
            }
        )
        
        if message:
            print(f"Allocation de tâche reçue: {message.content}")
            
            # Simuler le traitement
            print("Traitement de la tâche d'identification des prémisses...")
            time.sleep(2.0)
            
            # Demander de l'aide pour les prémisses implicites
            print("Demande d'assistance pour les prémisses implicites...")
            assistance = tactical_adapter2.request_tactical_assistance(
                request_type="collaboration",
                parameters={
                    "description": "Besoin d'aide pour identifier les prémisses implicites",
                    "context": {
                        "text_id": "text-123",
                        "segment": {"start": 100, "end": 200}
                    }
                },
                recipient_id="tactical-agent-1",
                timeout=5.0,
                priority=MessagePriority.HIGH
            )
            
            if assistance:
                print(f"Assistance reçue: {assistance}")
                
                # Utiliser l'assistance pour améliorer le résultat
                print("Amélioration du résultat avec l'assistance reçue...")
                time.sleep(1.0)
            
            # Envoyer le résultat
            print("Envoi du résultat...")
            result_message = {
                "type": MessageType.INFORMATION,
                "sender": "tactical-agent-2",
                "recipient": "tactical-agent-1",
                "content": {
                    "info_type": "task_result",
                    "task": "identification_premisses",
                    "text_id": "text-123",
                    "result": {
                        "premisses": [
                            {
                                "id": "p1",
                                "text": "Tous les hommes sont mortels",
                                "type": "universelle",
                                "position": {"start": 10, "end": 35}
                            },
                            {
                                "id": "p2",
                                "text": "Socrate est un homme",
                                "type": "particulière",
                                "position": {"start": 40, "end": 60}
                            },
                            {
                                "id": "p3",
                                "text": "Quand il pleut, les surfaces exposées deviennent mouillées",
                                "type": "implicite",
                                "inferred_from": "assistance"
                            }
                        ]
                    }
                },
                "priority": MessagePriority.NORMAL
            }
            middleware.send_message(result_message)
        
        # Attendre le résultat combiné
        print("En attente du résultat combiné...")
        combined_result = tactical_adapter2.receive_message(
            timeout=10.0,
            filter_criteria={
                "content.info_type": "combined_result"
            }
        )
        
        if combined_result:
            print(f"Résultat combiné reçu: {combined_result.content}")
        
        print("Agent tactique 2: tâche terminée.")

    # Fonction simulant le troisième agent tactique (identification des conclusions)
    def tactical_agent3():
        print("Agent tactique 3 (identification des conclusions) démarré...")
        
        # Recevoir l'allocation de tâche
        print("En attente de l'allocation de tâche...")
        message = tactical_adapter3.receive_message(
            timeout=5.0,
            filter_criteria={
                "content.info_type": "task_allocation"
            }
        )
        
        if message:
            print(f"Allocation de tâche reçue: {message.content}")
            
            # Simuler le traitement
            print("Traitement de la tâche d'identification des conclusions...")
            time.sleep(3.0)
            
            # Envoyer le résultat
            print("Envoi du résultat...")
            result_message = {
                "type": MessageType.INFORMATION,
                "sender": "tactical-agent-3",
                "recipient": "tactical-agent-1",
                "content": {
                    "info_type": "task_result",
                    "task": "identification_conclusions",
                    "text_id": "text-123",
                    "result": {
                        "conclusions": [
                            {
                                "id": "c1",
                                "text": "Socrate est mortel",
                                "type": "déductive",
                                "position": {"start": 65, "end": 85},
                                "premises": ["p1", "p2"]
                            },
                            {
                                "id": "c2",
                                "text": "La route est mouillée",
                                "type": "inductive",
                                "position": {"start": 120, "end": 140},
                                "premises": ["p3"]
                            }
                        ]
                    }
                },
                "priority": MessagePriority.NORMAL
            }
            middleware.send_message(result_message)
        
        # Attendre le résultat combiné
        print("En attente du résultat combiné...")
        combined_result = tactical_adapter3.receive_message(
            timeout=10.0,
            filter_criteria={
                "content.info_type": "combined_result"
            }
        )
        
        if combined_result:
            print(f"Résultat combiné reçu: {combined_result.content}")
        
        print("Agent tactique 3: tâche terminée.")

    # Démarrer les threads pour les agents
    agent1_thread = threading.Thread(target=tactical_agent1)
    agent2_thread = threading.Thread(target=tactical_agent2)
    agent3_thread = threading.Thread(target=tactical_agent3)
    
    agent1_thread.start()
    agent2_thread.start()
    agent3_thread.start()
    
    # Attendre que les threads se terminent
    agent1_thread.join()
    agent2_thread.join()
    agent3_thread.join()
    
    print("Communication horizontale terminée.")


if __name__ == "__main__":
    main()
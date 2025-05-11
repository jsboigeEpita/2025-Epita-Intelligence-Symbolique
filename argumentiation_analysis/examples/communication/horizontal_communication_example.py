# Horizontal Communication Example

import asyncio
from argumentiation_analysis.orchestration.hierarchical.tactical.resolver import TacticalResolver
from argumentiation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentiation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

async def run_horizontal_communication():
    """
    Exemple de communication horizontale entre agents tactiques et opérationnels
    """
    # Initialisation des composants
    tactical_resolver = TacticalResolver()
    operational_manager = OperationalManager()
    interface = TacticalOperationalInterface()
    
    # Configuration de la communication
    await interface.connect(tactical_resolver, operational_manager)
    
    # Message initial du niveau tactique
    tactical_message = {
        "type": "task_request",
        "content": {
            "task_id": "horizontal-task-1",
            "description": "Analyser les arguments sur l'immunité collective",
            "required_capabilities": ["epidemiology", "argument_analysis"]
        }
    }
    
    # Envoi du message au niveau opérationnel
    logger.info("Envoi du message tactique vers opérationnel")
    operational_response = await interface.send_to_operational(tactical_message)
    
    # Traitement de la réponse
    logger.info(f"Réponse opérationnelle reçue: {json.dumps(operational_response, indent=2)}")
    
    # Message de feedback du niveau opérationnel
    operational_feedback = {
        "type": "task_update",
        "content": {
            "task_id": "horizontal-task-1",
            "status": "in_progress",
            "progress": 75,
            "intermediate_results": {
                "arguments_found": 3,
                "fallacies_detected": 1
            }
        }
    }
    
    # Envoi du feedback au niveau tactique
    logger.info("Envoi du feedback opérationnel vers tactique")
    tactical_response = await interface.send_to_tactical(operational_feedback)
    
    # Affichage du résultat final
    logger.info(f"Résultat final: {json.dumps(tactical_response, indent=2)}")

if __name__ == "__main__":
    asyncio.run(run_horizontal_communication())
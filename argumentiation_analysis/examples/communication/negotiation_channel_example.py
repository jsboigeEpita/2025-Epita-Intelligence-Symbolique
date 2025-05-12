# Negotiation Channel Example

import asyncio
from argumentiation_analysis.orchestration.hierarchical.tactical.resolver import TacticalResolver
from argumentiation_analysis.orchestration.hierarchical.tactical.manager import TacticalManager
from argumentiation_analysis.orchestration.hierarchical.interfaces.negotiation import NegotiationInterface

async def run_negotiation_example():
    """
    Exemple de résolution de conflits via le canal de négociation
    """
    # Initialisation des composants
    interface = NegotiationInterface()
    resolver = TacticalResolver()
    manager = TacticalManager()
    
    # Connexion des composants
    await interface.connect(resolver, manager)
    
    # Conflit à résoudre
    conflict = {
        "type": "analysis_discrepancy",
        "content": {
            "task_id": "negotiation-task-1",
            "discrepancy": "Agent A détecte un sophisme, Agent B le valide",
            "proposed_solutions": [
                {"agent": "A", "solution": "Relancer l'analyse avec plus de contexte"},
                {"agent": "B", "solution": "Utiliser un modèle de validation alternatif"}
            ]
        }
    }
    
    # Processus de négociation
    logger.info("Initiation du processus de négociation...")
    resolution = await interface.resolve_conflict(conflict)
    
    # Affichage de la résolution
    logger.info(f"Résolution du conflit: {json.dumps(resolution, indent=2)}")

if __name__ == "__main__":
    asyncio.run(run_negotiation_example())
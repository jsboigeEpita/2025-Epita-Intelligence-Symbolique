# Data Transfer Example

import asyncio
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import TacticalResolver
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

async def run_data_transfer():
    """
    Exemple de transfert de données volumineuses entre niveaux
    """
    # Initialisation des composants
    interface = TacticalOperationalInterface()
    tactical_resolver = TacticalResolver()
    operational_manager = OperationalManager()
    
    # Connexion des composants
    await interface.connect(tactical_resolver, operational_manager)
    
    # Données volumineuses à transférer
    large_data = {
        "text_segments": ["Segment 1" * 1000, "Segment 2" * 1000, "Segment 3" * 1000],
        "metadata": {
            "source": "article_scientifique.txt",
            "format": "json",
            "analysis_type": "complete"
        }
    }
    
    # Envoi des données
    logger.info("Transfert de données volumineuses vers le niveau opérationnel")
    transfer_result = await interface.send_large_data(large_data)
    
    # Affichage des résultats
    logger.info(f"Statut du transfert: {transfer_result['status']}")
    logger.info(f"Taille des données reçues: {len(transfer_result['processed_data'])} segments")

if __name__ == "__main__":
    asyncio.run(run_data_transfer())
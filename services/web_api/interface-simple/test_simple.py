#!/usr/bin/env python3
"""
Test simple de l'intégration ServiceManager.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Configuration des chemins
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Configuration du logging sans émojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


async def test_integration():
    """Test simple de l'intégration."""
    logger.info("Début du test d'intégration ServiceManager")
    
    try:
        # Import et test de disponibilité
        from app import ServiceManager, SERVICE_MANAGER_AVAILABLE, initialize_services
        
        logger.info(f"ServiceManager disponible: {SERVICE_MANAGER_AVAILABLE}")
        
        if not SERVICE_MANAGER_AVAILABLE:
            logger.error("ServiceManager non disponible")
            return False
        
        # Test d'initialisation
        await initialize_services()
        
        # Import de la variable globale
        from app import service_manager
        
        if service_manager:
            logger.info("ServiceManager initialisé avec succès")
            
            # Test d'analyse simple
            text_test = "Si nous acceptons cela, alors tout va mal se passer. C'est un raisonnement fallacieux."
            
            result = await service_manager.analyze_text(
                text=text_test,
                analysis_type="comprehensive"
            )
            
            logger.info(f"Analyse terminée, clés du résultat: {list(result.keys())}")
            logger.info("SUCCESS: Intégration ServiceManager fonctionnelle")
            return True
        else:
            logger.error("ServiceManager non initialisé")
            return False
            
    except Exception as e:
        logger.error(f"Erreur: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_integration())
    print(f"Test {'RÉUSSI' if success else 'ÉCHOUÉ'}")
    sys.exit(0 if success else 1)
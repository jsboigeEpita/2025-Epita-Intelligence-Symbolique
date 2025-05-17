"""
Script pour exécuter le test direct du protocole de requête-réponse.
"""

import asyncio
import sys
import os
import logging

# Configuration du logger
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   datefmt='%H:%M:%S')
logger = logging.getLogger("RunDirectTest")

# Ajouter le répertoire parent au PYTHONPATH
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(parent_dir)
logger.info(f"Répertoire parent ajouté au PYTHONPATH: {parent_dir}")

# Importer le module de test
import argumentation_analysis.tests.test_request_response_direct as test_module

async def run_test():
    """Exécute le test direct du protocole de requête-réponse."""
    logger.info("Exécution du test direct du protocole de requête-réponse")
    
    test = test_module.TestRequestResponseDirect()
    
    try:
        await test.asyncSetUp()
        await test.test_direct_request_response()
        logger.info("✅ Test direct du protocole de requête-réponse PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Test direct du protocole de requête-réponse FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await test.asyncTearDown()

if __name__ == "__main__":
    # Exécuter la boucle d'événements asyncio
    result = asyncio.run(run_test())
    
    # Retourner un code d'erreur si le test a échoué
    if not result:
        sys.exit(1)
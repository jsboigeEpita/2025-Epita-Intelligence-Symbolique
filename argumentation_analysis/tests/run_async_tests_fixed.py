"""
Script pour exécuter les tests asynchrones corrigés de manière non bloquante.
"""

import asyncio
import sys
import os
import unittest
import importlib
import logging
from unittest.mock import patch

# Configuration du logger
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   datefmt='%H:%M:%S')
logger = logging.getLogger("RunAsyncTests")

# Ajouter le répertoire parent au PYTHONPATH
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(parent_dir)
logger.info(f"Répertoire parent ajouté au PYTHONPATH: {parent_dir}")

# Importer le module de test
import argumentation_analysis.tests.test_async_communication_fixed as test_module

async def run_test(test_case, test_method):
    """Exécute un test asynchrone et affiche le résultat."""
    logger.info(f"Exécution du test: {test_case.__name__}.{test_method}")
    
    test = test_case()
    if hasattr(test, 'asyncSetUp'):
        await test.asyncSetUp()
    
    try:
        await getattr(test, test_method)()
        logger.info(f"✅ {test_case.__name__}.{test_method} PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ {test_case.__name__}.{test_method} FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if hasattr(test, 'asyncTearDown'):
            await test.asyncTearDown()

async def main():
    """Fonction principale qui exécute tous les tests asynchrones."""
    logger.info("Démarrage des tests asynchrones corrigés")
    
    # Exécuter les tests asynchrones
    test_case = test_module.TestAsyncCommunicationFixed
    
    # Liste des méthodes de test à exécuter
    test_methods = [
        'test_async_request_response',
        'test_async_parallel_requests'
    ]
    
    # Exécuter chaque test individuellement
    results = []
    for method in test_methods:
        result = await run_test(test_case, method)
        results.append(result)
    
    # Afficher le résumé
    logger.info("\n=== Test Summary ===")
    logger.info(f"Total: {len(results)}")
    logger.info(f"Passed: {results.count(True)}")
    logger.info(f"Failed: {results.count(False)}")
    
    # Retourner un code d'erreur si des tests ont échoué
    if False in results:
        sys.exit(1)

if __name__ == "__main__":
    # Exécuter la boucle d'événements asyncio
    asyncio.run(main())
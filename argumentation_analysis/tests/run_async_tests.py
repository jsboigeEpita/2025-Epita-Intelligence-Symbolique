"""
Script pour exécuter les tests asynchrones de manière non bloquante.

Ce script a été amélioré avec:
1. Une meilleure gestion des logs
2. Une terminaison propre des ressources
3. Une gestion des erreurs améliorée
4. Des timeouts augmentés
"""

import asyncio
import sys
import os
import unittest
import importlib
import logging
import signal
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
import argumentation_analysis.tests.test_communication_integration as test_module

# Variable pour stocker les tâches en cours
running_tasks = set()

# Gestionnaire de signal pour une terminaison propre
def signal_handler(sig, frame):
    logger.info(f"Signal reçu: {sig}. Arrêt propre en cours...")
    for task in running_tasks:
        if not task.done():
            task.cancel()
    sys.exit(0)

# Enregistrer le gestionnaire de signal
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
    except asyncio.CancelledError:
        logger.warning(f"⚠️ {test_case.__name__}.{test_method} CANCELLED")
        return None
    except Exception as e:
        logger.error(f"❌ {test_case.__name__}.{test_method} FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if hasattr(test, 'asyncTearDown'):
            try:
                await test.asyncTearDown()
            except Exception as e:
                logger.error(f"Erreur lors du tearDown: {str(e)}")

async def main():
    """Fonction principale qui exécute tous les tests asynchrones."""
    logger.info("Démarrage des tests asynchrones")
    
    # Exécuter les tests asynchrones
    test_case = test_module.TestAsyncCommunicationIntegration
    
    # Liste des méthodes de test à exécuter
    test_methods = [
        'test_async_request_response',
        'test_async_parallel_requests'
    ]
    
    # Exécuter chaque test individuellement
    results = []
    for method in test_methods:
        task = asyncio.create_task(run_test(test_case, method))
        running_tasks.add(task)
        try:
            result = await asyncio.wait_for(task, timeout=60.0)  # Timeout global augmenté
            results.append(result)
        except asyncio.TimeoutError:
            logger.error(f"Timeout global pour {test_case.__name__}.{method}")
            task.cancel()
            results.append(False)
        finally:
            running_tasks.remove(task)
    
    # Afficher le résumé
    logger.info("\n=== Test Summary ===")
    logger.info(f"Total: {len(results)}")
    logger.info(f"Passed: {results.count(True)}")
    logger.info(f"Failed: {results.count(False)}")
    if None in results:
        logger.info(f"Cancelled: {results.count(None)}")
    
    # Retourner un code d'erreur si des tests ont échoué
    if False in results:
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Exécuter la boucle d'événements asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrompus par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erreur non gérée: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("Fin de l'exécution des tests")
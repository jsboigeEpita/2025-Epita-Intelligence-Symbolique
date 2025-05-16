"""
Script pour exécuter les tests asynchrones de manière non bloquante.
"""

import asyncio
import sys
import os
import unittest
import importlib
from unittest.mock import patch

# Importer le module de test
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import argumentation_analysis.tests.test_communication_integration as test_module

async def run_test(test_case, test_method):
    """Exécute un test asynchrone et affiche le résultat."""
    test = test_case()
    if hasattr(test, 'asyncSetUp'):
        await test.asyncSetUp()
    
    try:
        await getattr(test, test_method)()
        print(f"✅ {test_case.__name__}.{test_method} PASSED")
        return True
    except Exception as e:
        print(f"❌ {test_case.__name__}.{test_method} FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if hasattr(test, 'asyncTearDown'):
            await test.asyncTearDown()

async def main():
    """Fonction principale qui exécute tous les tests asynchrones."""
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
        result = await run_test(test_case, method)
        results.append(result)
    
    # Afficher le résumé
    print("\n=== Test Summary ===")
    print(f"Total: {len(results)}")
    print(f"Passed: {results.count(True)}")
    print(f"Failed: {results.count(False)}")
    
    # Retourner un code d'erreur si des tests ont échoué
    if False in results:
        sys.exit(1)

if __name__ == "__main__":
    # Exécuter la boucle d'événements asyncio
    asyncio.run(main())
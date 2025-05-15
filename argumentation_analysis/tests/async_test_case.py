"""
Classe de base pour les tests asynchrones.
"""

import unittest
import asyncio


class AsyncTestCase(unittest.TestCase):
    """Classe de base pour les tests asynchrones."""

    def run_async(self, coroutine):
        """Exécute une coroutine dans une boucle d'événements asyncio."""
        return asyncio.run(coroutine)

    def run(self, result=None):
        """Exécute le test, en prenant en charge les méthodes asynchrones."""
        # Récupérer la méthode de test
        method = getattr(self, self._testMethodName)
        
        # Sauvegarder la méthode originale
        original_method = method
        
        # Si la méthode est une coroutine, la remplacer par une version synchrone
        if asyncio.iscoroutinefunction(method):
            def wrapped_method(*args, **kwargs):
                return self.run_async(original_method(*args, **kwargs))
            setattr(self, self._testMethodName, wrapped_method)
        
        # Exécuter le test normalement
        super().run(result)
        
        # Restaurer la méthode originale
        if asyncio.iscoroutinefunction(original_method):
            setattr(self, self._testMethodName, original_method)
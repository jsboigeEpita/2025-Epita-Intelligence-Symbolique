"""
Classe de base pour les tests asynchrones.

Cette classe fournit une base pour les tests asynchrones, compatible à la fois
avec unittest et pytest-asyncio. Elle permet d'exécuter des coroutines asyncio
dans les tests unittest traditionnels, tout en étant compatible avec l'approche
pytest-asyncio utilisée dans le reste du projet.
"""

import unittest
import asyncio
import pytest
import inspect


class AsyncTestCase(unittest.TestCase):
    """
    Classe de base pour les tests asynchrones.
    
    Cette classe est compatible à la fois avec unittest et pytest-asyncio.
    Elle détecte automatiquement les méthodes de test asynchrones et les exécute
    correctement, que ce soit dans un contexte unittest ou pytest.
    
    Pour les tests pytest, les méthodes asynchrones sont automatiquement marquées
    avec @pytest.mark.asyncio grâce à la configuration dans conftest.py.
    """

    def run_async(self, coroutine):
        """
        Exécute une coroutine dans une boucle d'événements asyncio.
        
        Cette méthode est utilisée pour exécuter des coroutines dans un contexte unittest.
        Dans un contexte pytest, les coroutines sont exécutées directement par pytest-asyncio.
        
        Args:
            coroutine: La coroutine à exécuter.
            
        Returns:
            Le résultat de l'exécution de la coroutine.
        """
        return asyncio.run(coroutine)

    def run(self, result=None):
        """
        Exécute le test, en prenant en charge les méthodes asynchrones.
        
        Cette méthode est appelée par unittest pour exécuter le test.
        Elle détecte si la méthode de test est une coroutine et l'exécute
        correctement dans ce cas.
        
        Args:
            result: L'objet result de unittest.
        """
        # Vérifier si nous sommes dans un contexte pytest
        in_pytest = hasattr(pytest, "config")
        
        # Si nous sommes dans pytest, laisser pytest-asyncio gérer les coroutines
        if in_pytest:
            return super().run(result)
        
        # Sinon, gérer les coroutines nous-mêmes pour unittest
        method = getattr(self, self._testMethodName)
        original_method = method
        
        if asyncio.iscoroutinefunction(method):
            def wrapped_method(*args, **kwargs):
                return self.run_async(original_method(*args, **kwargs))
            setattr(self, self._testMethodName, wrapped_method)
        
        # Exécuter le test normalement
        super().run(result)
        
        # Restaurer la méthode originale
        if asyncio.iscoroutinefunction(original_method):
            setattr(self, self._testMethodName, original_method)
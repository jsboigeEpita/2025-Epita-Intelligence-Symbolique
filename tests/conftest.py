"""
Configuration pour les tests pytest.

Ce fichier est automatiquement chargé par pytest avant l'exécution des tests.
Il configure les mocks nécessaires pour les tests et utilise les vraies bibliothèques
lorsqu'elles sont disponibles. Pour Python 3.12 et supérieur, le mock JPype1 est
automatiquement utilisé en raison de problèmes de compatibilité.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# --- Hooks Pytest ---

def pytest_sessionstart(session):
    """
    S'exécute au début de la session de test.
    Initialise le mock JPype si nécessaire.
    """
    # Exposer jpype_setup au reste de la session de test si nécessaire
    # session.config.jpype_setup = jpype_setup
    print("pytest_sessionstart: Démarrage de la session de test.")

def pytest_sessionfinish(session, exitstatus):
    """
    S'exécute à la fin de la session de test.
    Nettoie les ressources, comme la JVM.
    """
    print(f"pytest_sessionfinish: Fin de la session de test avec le statut {exitstatus}.")
    # Si jpype_setup a ete utilise et a demarre la JVM, l'arreter.
    # from .mocks import jpype_setup # Import local pour eviter les problemes de dependance circulaire
    # jpype_setup.shutdown_jvm_if_needed()

# --- Fixtures ---

# Importer les fixtures depuis jpype_setup pour les rendre disponibles globalement
# Les fixtures seront importées dynamiquement pour éviter les problèmes d'import circulaire.
try:
    from .mocks.jpype_setup import mock_jpype, restore_jpype, real_jpype_fixture
    print("Fixtures JPype importées avec succès depuis tests.mocks.jpype_setup")
except ImportError as e:
    print(f"Avertissement: Impossible d'importer les fixtures JPype: {e}")
    # Définir des fixtures vides pour éviter les erreurs si l'import échoue
    @pytest.fixture(scope="session")
    def mock_jpype():
        yield
    @pytest.fixture(scope="session")
    def restore_jpype():
        yield
    @pytest.fixture(scope="session")
    def real_jpype_fixture():
        yield None

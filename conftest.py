"""
Configuration pytest pour le projet.

Ce fichier configure pytest pour les tests asynchrones en utilisant pytest-asyncio.
Il permet notamment de marquer automatiquement les fonctions de test asynchrones
et de résoudre les avertissements liés à @pytest.mark.asyncio.
"""

import pytest
# Initialisation du mock JPype1 pour Python 3.12+
import sys
try:
    if sys.version_info.major == 3 and sys.version_info.minor >= 12:
        print("Python 3.12+ détecté, utilisation directe du mock JPype1")
        # Importer directement le mock JPype1
        from tests.mocks import jpype_mock
        # Installer le mock dans sys.modules
        sys.modules['jpype'] = jpype_mock
        sys.modules['_jpype'] = jpype_mock._jpype
    else:
        print(f"Python {sys.version_info.major}.{sys.version_info.minor} détecté, pas besoin de mock JPype1")
except ImportError:
    print("Avertissement: Mock JPype1 non trouvé")



def pytest_configure(config):
    """
    Configure pytest avec les paramètres nécessaires pour pytest-asyncio.
    
    Cette fonction est appelée automatiquement par pytest lors de son initialisation.
    """
    # Enregistrer le marqueur asyncio pour éviter les avertissements
    config.addinivalue_line(
        "markers",
        "asyncio: marque les tests asynchrones qui nécessitent une boucle d'événements"
    )


@pytest.fixture
def event_loop_policy():
    """
    Fixture pour configurer la politique de boucle d'événements asyncio.
    
    Retourne None pour utiliser la politique par défaut.
    """
    return None


# Configuration pour auto-marquer les fonctions de test asynchrones
def pytest_collection_modifyitems(items):
    """
    Marque automatiquement les fonctions de test asynchrones avec @pytest.mark.asyncio.
    
    Cette fonction est appelée automatiquement par pytest après la collecte des tests.
    """
    for item in items:
        if item.name.startswith('test_') and 'async' in item.name:
            # Si le nom de la fonction commence par 'test_' et contient 'async'
            item.add_marker(pytest.mark.asyncio)
        
        # Marquer automatiquement les méthodes de test asynchrones
        if hasattr(item.function, '__code__'):
            if item.function.__code__.co_flags & 0x80:  # 0x80 est le flag pour les fonctions async
                item.add_marker(pytest.mark.asyncio)
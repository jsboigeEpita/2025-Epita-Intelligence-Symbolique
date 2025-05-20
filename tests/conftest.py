"""
Configuration pour les tests pytest.

Ce fichier est automatiquement chargé par pytest avant l'exécution des tests.
Il configure les mocks nécessaires pour les tests.
"""

import sys
import os
import pytest
from unittest.mock import patch

# Ajouter le répertoire parent au PYTHONPATH pour pouvoir importer les modules du projet
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Fonction pour configurer le mock de jpype
def setup_jpype_mock():
    """Configure le mock de jpype pour les tests."""
    # Importer le mock de jpype
    from tests.mocks.jpype_mock import (
        isJVMStarted, startJVM, getJVMPath, getJVMVersion, getDefaultJVMPath,
        JClass, JException, JObject, JVMNotFoundException, imports, _jpype
    )
    
    # Installer les mocks dans sys.modules
    sys.modules['jpype'] = type('jpype', (), {
        'isJVMStarted': isJVMStarted,
        'startJVM': startJVM,
        'getJVMPath': getJVMPath,
        'getJVMVersion': getJVMVersion,
        'getDefaultJVMPath': getDefaultJVMPath,
        'JClass': JClass,
        'JException': JException,
        'JObject': JObject,
        'JVMNotFoundException': JVMNotFoundException,
        'imports': imports,
    })
    
    sys.modules['_jpype'] = _jpype
    
    return sys.modules['jpype'], sys.modules['_jpype']

# Fixture pour configurer le mock de jpype
@pytest.fixture(scope="session", autouse=True)
def mock_jpype():
    """Fixture pour configurer le mock de jpype pour tous les tests."""
    # Vérifier si nous sommes en mode test
    if 'PYTEST_CURRENT_TEST' in os.environ:
        # Configurer le mock de jpype
        jpype_mock, _jpype_mock = setup_jpype_mock()
        
        # Patcher les importations de jpype dans les modules qui l'utilisent
        modules_to_patch = [
            'argumentation_analysis.core.jvm_setup',
            'argumentation_analysis.agents.core.pl.pl_definitions',
            'argumentation_analysis.orchestration.analysis_runner',
            'jpype',  # Patcher le module jpype lui-même
        ]
        
        # Patcher jpype directement dans sys.modules
        if 'jpype' not in sys.modules:
            from tests.mocks.jpype_mock import (
                isJVMStarted, startJVM, getJVMPath, getJVMVersion, getDefaultJVMPath,
                JClass, JException, JObject, JVMNotFoundException, imports, _jpype
            )
            sys.modules['jpype'] = type('jpype', (), {
                'isJVMStarted': isJVMStarted,
                'startJVM': startJVM,
                'getJVMPath': getJVMPath,
                'getJVMVersion': getJVMVersion,
                'getDefaultJVMPath': getDefaultJVMPath,
                'JClass': JClass,
                'JException': JException,
                'JObject': JObject,
                'JVMNotFoundException': JVMNotFoundException,
                'imports': imports,
            })
            sys.modules['_jpype'] = _jpype
        
        patches = []
        for module_name in modules_to_patch:
            if module_name in sys.modules:
                # Patcher jpype dans le module
                patcher = patch.object(sys.modules[module_name], 'jpype', jpype_mock)
                patcher.start()
                patches.append(patcher)
                
                # Patcher _jpype dans le module si nécessaire
                if hasattr(sys.modules[module_name], '_jpype'):
                    patcher = patch.object(sys.modules[module_name], '_jpype', _jpype_mock)
                    patcher.start()
                    patches.append(patcher)
        
        yield
        
        # Arrêter tous les patchers
        for patcher in patches:
            patcher.stop()
    else:
        yield
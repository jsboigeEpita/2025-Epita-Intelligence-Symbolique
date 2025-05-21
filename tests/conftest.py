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

# Fonction pour configurer le mock de numpy
def setup_numpy_mock():
    """Configure le mock de numpy pour les tests."""
    # Importer le mock de numpy
    from tests.mocks.numpy_mock import array, ndarray, mean, sum, zeros, ones, dot, concatenate, vstack, hstack, argmax, argmin, max, min, random
    
    # Installer les mocks dans sys.modules
    sys.modules['numpy'] = type('numpy', (), {
        'array': array,
        'ndarray': ndarray,
        'mean': mean,
        'sum': sum,
        'zeros': zeros,
        'ones': ones,
        'dot': dot,
        'concatenate': concatenate,
        'vstack': vstack,
        'hstack': hstack,
        'argmax': argmax,
        'argmin': argmin,
        'max': max,
        'min': min,
        'random': random,
    })
    
    return sys.modules['numpy']

# Fonction pour configurer le mock de pandas
def setup_pandas_mock():
    """Configure le mock de pandas pour les tests."""
    # Importer le mock de pandas
    from tests.mocks.pandas_mock import DataFrame, read_csv, read_json
    
    # Installer les mocks dans sys.modules
    sys.modules['pandas'] = type('pandas', (), {
        'DataFrame': DataFrame,
        'read_csv': read_csv,
        'read_json': read_json,
        'Series': list,
        'NA': None,
        'NaT': None,
        'isna': lambda x: x is None,
        'notna': lambda x: x is not None
    })
    
    return sys.modules['pandas']

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
            'argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter',
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

# Fixture pour configurer le mock de numpy
@pytest.fixture(scope="session", autouse=True)
def mock_numpy():
    """Fixture pour configurer le mock de numpy pour tous les tests."""
    # Vérifier si nous sommes en mode test
    if 'PYTEST_CURRENT_TEST' in os.environ:
        # Configurer le mock de numpy
        numpy_mock = setup_numpy_mock()
        
        # Patcher les importations de numpy dans les modules qui l'utilisent
        modules_to_patch = [
            'argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator',
            'argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer',
            'argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator',
            'argumentation_analysis.agents.tools.analysis.rhetorical_result_analyzer',
            'numpy',  # Patcher le module numpy lui-même
        ]
        
        # Patcher numpy directement dans sys.modules
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = numpy_mock
        
        patches = []
        for module_name in modules_to_patch:
            if module_name in sys.modules:
                # Patcher numpy dans le module
                patcher = patch.object(sys.modules[module_name], 'numpy', numpy_mock)
                patcher.start()
                patches.append(patcher)
                
                # Patcher np dans le module si nécessaire
                if hasattr(sys.modules[module_name], 'np'):
                    patcher = patch.object(sys.modules[module_name], 'np', numpy_mock)
                    patcher.start()
                    patches.append(patcher)
        
        yield
        
        # Arrêter tous les patchers
        for patcher in patches:
            patcher.stop()
    else:
        yield

# Fixture pour configurer le mock de pandas
@pytest.fixture(scope="session", autouse=True)
def mock_pandas():
    """Fixture pour configurer le mock de pandas pour tous les tests."""
    # Vérifier si nous sommes en mode test
    if 'PYTEST_CURRENT_TEST' in os.environ:
        # Configurer le mock de pandas
        pandas_mock = setup_pandas_mock()
        
        # Patcher les importations de pandas dans les modules qui l'utilisent
        modules_to_patch = [
            'argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator',
            'argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer',
            'argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator',
            'argumentation_analysis.agents.tools.analysis.rhetorical_result_analyzer',
            'argumentation_analysis.agents.core.informal.informal_definitions',
            'pandas',  # Patcher le module pandas lui-même
        ]
        
        # Patcher pandas directement dans sys.modules
        if 'pandas' not in sys.modules:
            sys.modules['pandas'] = pandas_mock
        
        patches = []
        for module_name in modules_to_patch:
            if module_name in sys.modules:
                # Patcher pandas dans le module
                patcher = patch.object(sys.modules[module_name], 'pandas', pandas_mock)
                patcher.start()
                patches.append(patcher)
                
                # Patcher pd dans le module si nécessaire
                if hasattr(sys.modules[module_name], 'pd'):
                    patcher = patch.object(sys.modules[module_name], 'pd', pandas_mock)
                    patcher.start()
                    patches.append(patcher)
        
        yield
        
        # Arrêter tous les patchers
        for patcher in patches:
            patcher.stop()
    else:
        yield
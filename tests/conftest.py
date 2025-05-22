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
from unittest.mock import patch
import importlib.util

# Ajouter le répertoire parent au PYTHONPATH pour pouvoir importer les modules du projet
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Fonction pour vérifier si un module est disponible
def is_module_available(module_name):
    """Vérifie si un module Python est disponible."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

def is_python_version_compatible_with_jpype():
    """
    Vérifie si la version actuelle de Python est compatible avec JPype1.
    JPype1 n'est pas compatible avec Python 3.12 et supérieur.
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    
    # Python 3.12 et supérieur n'est pas compatible avec JPype1
    if (major == 3 and minor >= 12) or major > 3:
        return False
    
    return True

# Fonction pour configurer jpype (réel ou mock)
def setup_jpype():
    """
    Configure jpype pour les tests, en utilisant la vraie bibliothèque si disponible
    et compatible avec la version de Python actuelle.
    """
    # Vérifier si la version de Python est compatible avec JPype1
    python_compatible = is_python_version_compatible_with_jpype()
    
    if python_compatible and is_module_available('jpype'):
        # Utiliser la vraie bibliothèque jpype
        import jpype
        
        # Créer un mock pour _jpype car la structure a changé dans la version 1.5.2
        _jpype_mock = type('_jpype', (), {})
        
        print(f"Utilisation de la vraie bibliothèque JPype1 (version {getattr(jpype, '__version__', 'inconnue')})")
        return jpype, _jpype_mock
    else:
        # Si Python 3.12+ ou JPype1 n'est pas disponible, utiliser le mock
        if not python_compatible:
            print(f"Python {sys.version_info.major}.{sys.version_info.minor} détecté, "
                  f"utilisation du mock JPype1 (JPype1 n'est pas compatible avec Python 3.12+)")
        else:
            print("JPype1 non disponible, utilisation du mock")
            
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
            '__version__': '1.4.1',  # Version simulée
        })
        
        sys.modules['_jpype'] = _jpype
        
        return sys.modules['jpype'], sys.modules['_jpype']

# Fonction pour configurer numpy (réel ou mock)
def setup_numpy():
    """Configure numpy pour les tests, en utilisant la vraie bibliothèque si disponible."""
    # Pour Python 3.12+, toujours utiliser le mock
    if sys.version_info.major == 3 and sys.version_info.minor >= 12:
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
            '__version__': '1.24.3',  # Version simulée
        })
        
        return sys.modules['numpy']
    elif is_module_available('numpy'):
        # Utiliser la vraie bibliothèque numpy
        import numpy
        return numpy
    else:
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
            '__version__': '1.24.3',  # Version simulée
        })
        
        return sys.modules['numpy']

# Fonction pour configurer le mock de pandas ou utiliser la vraie bibliothèque
def setup_pandas():
    """Configure pandas pour les tests, en utilisant la vraie bibliothèque si disponible."""
    # Pour Python 3.12+, toujours utiliser le mock
    if sys.version_info.major == 3 and sys.version_info.minor >= 12:
        # Utiliser le mock de pandas
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
    elif is_module_available('pandas'):
        # Utiliser la vraie bibliothèque pandas
        import pandas
        return pandas
    else:
        # Utiliser le mock de pandas
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

# Fixture pour configurer jpype (réel ou mock)
@pytest.fixture(scope="session", autouse=True)
def setup_jpype_for_tests():
    """Fixture pour configurer jpype pour tous les tests."""
    # Vérifier si nous sommes en mode test
    if 'PYTEST_CURRENT_TEST' in os.environ:
        # Configurer jpype (réel ou mock)
        jpype_module, _jpype_module = setup_jpype()
        
        # Modules qui utilisent jpype
        modules_to_patch = [
            'argumentation_analysis.core.jvm_setup',
            'argumentation_analysis.agents.core.pl.pl_definitions',
            'argumentation_analysis.orchestration.analysis_runner',
            'argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter',
        ]
        
        # Patcher jpype directement dans sys.modules si ce n'est pas déjà la vraie bibliothèque
        if 'jpype' not in sys.modules or not is_module_available('jpype'):
            sys.modules['jpype'] = jpype_module
            sys.modules['_jpype'] = _jpype_module
        
        for module_name in modules_to_patch:
            if module_name in sys.modules:
                try:
                    # Si le module utilise jpype via import jpype
                    if not hasattr(sys.modules[module_name], 'jpype'):
                        sys.modules[module_name].jpype = jpype_module
                    
                    # Si le module utilise _jpype
                    if hasattr(sys.modules[module_name], '_jpype'):
                        sys.modules[module_name]._jpype = _jpype_module
                except Exception as e:
                    print(f"Erreur lors du patch de jpype pour {module_name}: {e}")
        
        yield
    else:
        yield

# Fixture pour configurer numpy (réel ou mock)
@pytest.fixture(scope="session", autouse=True)
def setup_numpy_for_tests():
    """Fixture pour configurer numpy pour tous les tests."""
    # Vérifier si nous sommes en mode test
    if 'PYTEST_CURRENT_TEST' in os.environ:
        # Configurer numpy (réel ou mock)
        numpy_module = setup_numpy()
        
        # Modules qui utilisent numpy
        modules_to_patch = [
            'argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator',
            'argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer',
            'argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer',
            'argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator',
            'argumentation_analysis.agents.tools.analysis.rhetorical_result_analyzer',
        ]
        
        # Patcher numpy directement dans sys.modules si ce n'est pas déjà la vraie bibliothèque
        if 'numpy' not in sys.modules or not is_module_available('numpy'):
            sys.modules['numpy'] = numpy_module
        
        patches = []
        for module_name in modules_to_patch:
            if module_name in sys.modules:
                try:
                    # Vérifier si le module a déjà un attribut numpy
                    if not hasattr(sys.modules[module_name], 'numpy'):
                        # Si le module utilise numpy via import numpy
                        sys.modules[module_name].numpy = numpy_module
                    
                    # Vérifier si le module a déjà un attribut np (alias courant pour numpy)
                    if hasattr(sys.modules[module_name], 'np'):
                        # Si le module utilise numpy via import numpy as np
                        sys.modules[module_name].np = numpy_module
                except Exception as e:
                    print(f"Erreur lors du patch de numpy pour {module_name}: {e}")
        
        yield
        
        # Pas besoin de nettoyer les patches car nous avons modifié les modules directement
    else:
        yield

# Fixture pour configurer pandas (réel ou mock)
@pytest.fixture(scope="session", autouse=True)
def setup_pandas_for_tests():
    """Fixture pour configurer pandas pour tous les tests."""
    # Vérifier si nous sommes en mode test
    if 'PYTEST_CURRENT_TEST' in os.environ:
        # Configurer pandas (réel ou mock)
        pandas_module = setup_pandas()
        
        # Modules qui utilisent pandas
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
        ]
        
        # Patcher pandas directement dans sys.modules si ce n'est pas déjà la vraie bibliothèque
        if 'pandas' not in sys.modules or not is_module_available('pandas'):
            sys.modules['pandas'] = pandas_module
        
        for module_name in modules_to_patch:
            if module_name in sys.modules:
                try:
                    # Si le module utilise pandas via import pandas
                    if not hasattr(sys.modules[module_name], 'pandas'):
                        sys.modules[module_name].pandas = pandas_module
                    
                    # Si le module utilise pandas via import pandas as pd
                    if hasattr(sys.modules[module_name], 'pd'):
                        sys.modules[module_name].pd = pandas_module
                except Exception as e:
                    print(f"Erreur lors du patch de pandas pour {module_name}: {e}")
        
        yield
    else:
        yield
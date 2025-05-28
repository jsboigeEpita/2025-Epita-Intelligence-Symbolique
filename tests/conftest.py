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
import importlib.util

# --- Mock Matplotlib et NetworkX au plus tôt ---
try:
    current_dir_for_mock = os.path.dirname(os.path.abspath(__file__))
    mocks_dir_for_mock = os.path.join(current_dir_for_mock, 'mocks')
    if mocks_dir_for_mock not in sys.path:
        sys.path.insert(0, mocks_dir_for_mock) # Ajoute tests/mocks au path

    # Matplotlib
    from matplotlib_mock import pyplot as mock_pyplot_instance # Import direct car mocks_dir_for_mock est dans le path
    from matplotlib_mock import cm as mock_cm_instance
    from matplotlib_mock import MatplotlibMock as MockMatplotlibModule_class
    
    sys.modules['matplotlib.pyplot'] = mock_pyplot_instance
    sys.modules['matplotlib.cm'] = mock_cm_instance
    mock_mpl_module = MockMatplotlibModule_class()
    mock_mpl_module.pyplot = mock_pyplot_instance
    mock_mpl_module.cm = mock_cm_instance
    sys.modules['matplotlib'] = mock_mpl_module
    print("INFO: Matplotlib mocké globalement.")

    # NetworkX
    from networkx_mock import NetworkXMock as MockNetworkXModule_class # Import direct
    sys.modules['networkx'] = MockNetworkXModule_class()
    print("INFO: NetworkX mocké globalement.")

except ImportError as e:
    print(f"ERREUR CRITIQUE lors du mocking global de matplotlib ou networkx: {e}")
    # Fallback à des MagicMock génériques
    if 'matplotlib' not in str(e).lower():
        sys.modules['matplotlib.pyplot'] = MagicMock()
        sys.modules['matplotlib.cm'] = MagicMock()
        sys.modules['matplotlib'] = MagicMock()
        sys.modules['matplotlib'].pyplot = sys.modules['matplotlib.pyplot']
        sys.modules['matplotlib'].cm = sys.modules['matplotlib.cm']
    if 'networkx' not in str(e).lower():
        sys.modules['networkx'] = MagicMock()
# --- Fin des Mocks Globaux ---

# --- Mock NumPy Immédiat ---
# Installation immédiate du mock NumPy pour éviter les problèmes d'import pandas
# def _install_numpy_mock_immediately():
#     """Installe le mock NumPy immédiatement pour éviter les conflits avec pandas."""
#     if 'numpy' not in sys.modules:
#         try:
#             from numpy_mock import array, ndarray, mean, sum, zeros, ones, dot, concatenate, vstack, hstack, argmax, argmin, max, min, random, rec, _core, core, bool_, number, object_, float64, float32, int64, int32, int_, uint, uint64, uint32
#             sys.modules['numpy'] = type('numpy', (), {
#                 'array': array, 'ndarray': ndarray, 'mean': mean, 'sum': sum, 'zeros': zeros, 'ones': ones,
#                 'dot': dot, 'concatenate': concatenate, 'vstack': vstack, 'hstack': hstack,
#                 'argmax': argmax, 'argmin': argmin, 'max': max, 'min': min, 'random': random, 'rec': rec,
#                 '_core': _core, 'core': core, '__version__': '1.24.3',
#                 # Types de données pour compatibilité PyTorch
#                 'bool_': bool_, 'number': number, 'object_': object_,
#                 'float64': float64, 'float32': float32, 'int64': int64, 'int32': int32, 'int_': int_,
#                 'uint': uint, 'uint64': uint64, 'uint32': uint32,
#             })
#             # Installation explicite des sous-modules dans sys.modules
#             sys.modules['numpy._core'] = _core
#             sys.modules['numpy.core'] = core
#             sys.modules['numpy._core.multiarray'] = _core.multiarray
#             sys.modules['numpy.core.multiarray'] = core.multiarray
#             print("INFO: Mock NumPy installé immédiatement dans conftest.py")
#         except ImportError as e:
#             print(f"ERREUR lors de l'installation immédiate du mock NumPy: {e}")

# Installation immédiate si Python 3.12+ ou si numpy n'est pas disponible
# if (sys.version_info.major == 3 and sys.version_info.minor >= 12):
#     _install_numpy_mock_immediately()

# --- Mock Pandas Immédiat ---
# Installation immédiate du mock Pandas pour éviter les problèmes d'import
# def _install_pandas_mock_immediately():
#     """Installe le mock Pandas immédiatement pour éviter les conflits avec numpy."""
#     if 'pandas' not in sys.modules:
#         try:
#             from pandas_mock import DataFrame, read_csv, read_json
#             sys.modules['pandas'] = type('pandas', (), {
#                 'DataFrame': DataFrame, 'read_csv': read_csv, 'read_json': read_json, 'Series': list,
#                 'NA': None, 'NaT': None, 'isna': lambda x: x is None, 'notna': lambda x: x is not None,
#                 '__version__': '1.5.3',
#             })
#             # Installation des sous-modules pandas critiques
#             sys.modules['pandas.core'] = type('pandas.core', (), {})
#             sys.modules['pandas.core.api'] = type('pandas.core.api', (), {})
#             sys.modules['pandas._libs'] = type('pandas._libs', (), {})
#             sys.modules['pandas._libs.pandas_datetime'] = type('pandas._libs.pandas_datetime', (), {})
#             print("INFO: Mock Pandas installé immédiatement dans conftest.py")
#         except ImportError as e:
#             print(f"ERREUR lors de l'installation immédiate du mock Pandas: {e}")

# Installation immédiate si Python 3.12+ ou si pandas n'est pas disponible
# if (sys.version_info.major == 3 and sys.version_info.minor >= 12):
#     _install_pandas_mock_immediately()

# --- Mock JPype ---
# mocks_dir_for_mock (tests/mocks) est déjà dans sys.path depuis le bloc ci-dessus.
try:
    from jpype_mock import ( # Import direct car tests/mocks est dans sys.path
        isJVMStarted, startJVM, getJVMPath, getJVMVersion, getDefaultJVMPath,
        JClass, JException, JObject, JVMNotFoundException
    )

    mock_jpype_imports_module = MagicMock(name="jpype.imports_mock")
    sys.modules['jpype.imports'] = mock_jpype_imports_module

    jpype_module_mock_obj = MagicMock(name="jpype_module_mock")
    jpype_module_mock_obj.__path__ = []
    jpype_module_mock_obj.isJVMStarted = isJVMStarted
    jpype_module_mock_obj.startJVM = startJVM
    jpype_module_mock_obj.getJVMPath = getJVMPath
    jpype_module_mock_obj.getJVMVersion = getJVMVersion
    jpype_module_mock_obj.getDefaultJVMPath = getDefaultJVMPath
    jpype_module_mock_obj.JClass = JClass
    jpype_module_mock_obj.JException = JException
    jpype_module_mock_obj.JObject = JObject
    jpype_module_mock_obj.JVMNotFoundException = JVMNotFoundException
    jpype_module_mock_obj.__version__ = '1.4.1.mock'
    jpype_module_mock_obj.imports = mock_jpype_imports_module

    sys.modules['jpype'] = jpype_module_mock_obj
    sys.modules['_jpype'] = MagicMock(name="_jpype_mock")
    print("INFO: JPype (et jpype.imports) mocké globalement.")
except ImportError as e_jpype:
    print(f"ERREUR CRITIQUE lors du mocking global de JPype: {e_jpype}")
    # Créer un mock JPype plus robuste avec les méthodes nécessaires
    fallback_jpype = MagicMock(name="jpype_fallback_mock")
    
    # Variables globales pour simuler l'état de la JVM
    class JVMState:
        def __init__(self):
            self.started = False
    
    jvm_state = JVMState()
    
    def mock_isJVMStarted():
        return jvm_state.started
    
    def mock_startJVM(*args, **kwargs):
        jvm_state.started = True
    
    def mock_shutdownJVM():
        jvm_state.started = False
    
    class MockJClass:
        def __init__(self, name):
            self.__name__ = name
            self.class_name = name
        
        def __call__(self, *args, **kwargs):
            """Permet d'instancier la classe Java mockée."""
            return MagicMock()
    
    def mock_JClass(name):
        return MockJClass(name)
    
    class MockJException(Exception):
        def __init__(self, message="Mock Java Exception"):
            super().__init__(message)
            self.message = message
        
        def getClass(self):
            class MockClass:
                def getName(self):
                    return "org.mockexception.MockException"
            return MockClass()
        
        def getMessage(self):
            return self.message
    
    # Configurer le mock fallback
    fallback_jpype.isJVMStarted = mock_isJVMStarted
    fallback_jpype.startJVM = mock_startJVM
    fallback_jpype.shutdownJVM = mock_shutdownJVM
    fallback_jpype.JClass = mock_JClass
    fallback_jpype.JException = MockJException
    fallback_jpype.getDefaultJVMPath = lambda: "C:\\Program Files\\Java\\jdk-11\\bin\\server\\jvm.dll"
    
    # Ajouter des attributs pour la compatibilité avec les tests
    def get_jvm_started():
        return jvm_state.started
    
    def set_jvm_started(value):
        jvm_state.started = value
    
    fallback_jpype._jvm_started = property(get_jvm_started, set_jvm_started)
    
    # Permettre aussi l'accès direct comme attribut
    class JPypeMockWrapper:
        def __getattr__(self, name):
            if name == '_jvm_started':
                return jvm_state.started
            return getattr(fallback_jpype, name)
        
        def __setattr__(self, name, value):
            if name == '_jvm_started':
                jvm_state.started = value
            else:
                setattr(fallback_jpype, name, value)
    
    jpype_wrapper = JPypeMockWrapper()
    # Copier tous les attributs du fallback_jpype vers le wrapper
    for attr_name in dir(fallback_jpype):
        if not attr_name.startswith('_'):
            setattr(jpype_wrapper, attr_name, getattr(fallback_jpype, attr_name))
    
    sys.modules['jpype'] = jpype_wrapper
    sys.modules['jpype.imports'] = MagicMock(name="jpype.imports_fallback_mock")
    sys.modules['_jpype'] = MagicMock(name="_jpype_fallback_mock")
# --- Fin Mock JPype ---

# --- Mock ExtractDefinitions ---
try:
    # mocks_dir_for_mock (tests/mocks) est déjà dans sys.path
    from extract_definitions_mock import setup_extract_definitions_mock
    setup_extract_definitions_mock()
    print("INFO: ExtractDefinitions mocké globalement.")
except ImportError as e_extract:
    print(f"ERREUR lors du mocking d'ExtractDefinitions: {e_extract}")
except Exception as e_extract_setup:
    print(f"ERREUR lors de la configuration du mock ExtractDefinitions: {e_extract_setup}")
# --- Fin Mock ExtractDefinitions ---

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def is_module_available(module_name):
    if module_name in sys.modules:
        # Vérifier si c'est un de nos mocks principaux ou un MagicMock générique
        if isinstance(sys.modules[module_name], MagicMock) or \
           (module_name == 'jpype' and sys.modules[module_name] is jpype_module_mock_obj):
            return True
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError):
        return False

def is_python_version_compatible_with_jpype():
    major = sys.version_info.major
    minor = sys.version_info.minor
    if (major == 3 and minor >= 12) or major > 3:
        return False
    return True

# def setup_numpy():
#     if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('numpy'):
#         if not is_module_available('numpy'): print("NumPy non disponible, utilisation du mock.")
#         else: print("Python 3.12+ détecté, utilisation du mock NumPy.")
#         # mocks_dir_for_mock (tests/mocks) est déjà dans sys.path
#         from numpy_mock import array, ndarray, mean, sum, zeros, ones, dot, concatenate, vstack, hstack, argmax, argmin, max, min, random, rec, _core, core, bool_, number, object_, float64, float32, int64, int32, int_, uint, uint64, uint32
#         sys.modules['numpy'] = type('numpy', (), {
#             'array': array, 'ndarray': ndarray, 'mean': mean, 'sum': sum, 'zeros': zeros, 'ones': ones,
#             'dot': dot, 'concatenate': concatenate, 'vstack': vstack, 'hstack': hstack,
#             'argmax': argmax, 'argmin': argmin, 'max': max, 'min': min, 'random': random, 'rec': rec,
#             '_core': _core, 'core': core, '__version__': '1.24.3',
#             # Types de données pour compatibilité PyTorch
#             'bool_': bool_, 'number': number, 'object_': object_,
#             'float64': float64, 'float32': float32, 'int64': int64, 'int32': int32, 'int_': int_,
#             'uint': uint, 'uint64': uint64, 'uint32': uint32,
#         })
#         # Installation explicite des sous-modules dans sys.modules
#         sys.modules['numpy._core'] = _core
#         sys.modules['numpy.core'] = core
#         sys.modules['numpy._core.multiarray'] = _core.multiarray
#         sys.modules['numpy.core.multiarray'] = core.multiarray
#         return sys.modules['numpy']
#     else:
#         import numpy
#         print(f"Utilisation de la vraie bibliothèque NumPy (version {getattr(numpy, '__version__', 'inconnue')})")
#         return numpy

# def setup_pandas():
#     if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('pandas'):
#         if not is_module_available('pandas'): print("Pandas non disponible, utilisation du mock.")
#         else: print("Python 3.12+ détecté, utilisation du mock Pandas.")
#         # mocks_dir_for_mock (tests/mocks) est déjà dans sys.path
#         from pandas_mock import DataFrame, read_csv, read_json
#         sys.modules['pandas'] = type('pandas', (), {
#             'DataFrame': DataFrame, 'read_csv': read_csv, 'read_json': read_json, 'Series': list,
#             'NA': None, 'NaT': None, 'isna': lambda x: x is None, 'notna': lambda x: x is not None,
#             '__version__': '1.5.3',
#         })
#         return sys.modules['pandas']
#     else:
#         import pandas
#         print(f"Utilisation de la vraie bibliothèque Pandas (version {getattr(pandas, '__version__', 'inconnue')})")
#         return pandas

# @pytest.fixture(scope="session", autouse=True)
# def setup_numpy_for_tests_fixture():
#     if 'PYTEST_CURRENT_TEST' in os.environ:
#         # numpy_module = setup_numpy() # Commenté
#         import numpy # Forcer l'utilisation du vrai numpy
#         sys.modules['numpy'] = numpy
#         if sys.modules.get('numpy') is not numpy:
#              sys.modules['numpy'] = numpy
#         print(f"INFO: conftest.py force l'utilisation du vrai NumPy (version {getattr(numpy, '__version__', 'inconnue')})")
#         yield
#     else:
#         yield

# @pytest.fixture(scope="session", autouse=True)
# def setup_pandas_for_tests_fixture():
#     if 'PYTEST_CURRENT_TEST' in os.environ:
#         # pandas_module = setup_pandas() # Commenté
#         import pandas # Forcer l'utilisation du vrai pandas
#         sys.modules['pandas'] = pandas
#         if sys.modules.get('pandas') is not pandas:
#             sys.modules['pandas'] = pandas
#         print(f"INFO: conftest.py force l'utilisation du vrai Pandas (version {getattr(pandas, '__version__', 'inconnue')})")
#         yield
#     else:
#         yield
# Ajouter le répertoire racine au chemin Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configuration asyncio provenant de l'ancien conftest.py racine
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

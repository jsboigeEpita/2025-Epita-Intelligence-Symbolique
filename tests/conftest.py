"""
Configuration pour les tests pytest.

Ce fichier est automatiquement chargé par pytest avant l'exécution des tests.
Il configure les mocks nécessaires pour les tests et utilise les vraies bibliothèques
lorsqu'elles sont disponibles. Pour Python 3.12 et supérieur, le mock JPype1 est
automatiquement utilisé en raison de problèmes de compatibilité.
"""
# Ignorer la collecte de run_tests.py qui n'est pas un fichier de test
# Déplacé plus bas pour avoir accès à os
# collect_ignore = ["../argumentation_analysis/run_tests.py"]

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import importlib.util
# Ignorer la collecte de run_tests.py qui n'est pas un fichier de test
# Chemin relatif depuis tests/conftest.py vers argumentation_analysis/run_tests.py
# collect_ignore = ["../argumentation_analysis/run_tests.py"] # Commenté pour tester l'effet de python_classes
import logging
import threading # Ajout de l'import pour l'inspection des threads

# --- Configuration du Logger (déplacé avant la sauvegarde JPype pour l'utiliser) ---
logger = logging.getLogger(__name__)

# --- Sauvegarde du module JPype potentiellement pré-importé ou import frais ---
_REAL_JPYPE_MODULE = None
_PRE_EXISTING_JPYPE_IN_SYS_MODULES = sys.modules.get('jpype')

if _PRE_EXISTING_JPYPE_IN_SYS_MODULES:
    # Si jpype est déjà dans sys.modules (probablement par le conftest racine), on l'utilise.
    # On suppose qu'il est fonctionnel ou que les erreurs se manifesteront de toute façon.
    _REAL_JPYPE_MODULE = _PRE_EXISTING_JPYPE_IN_SYS_MODULES
    logger.info(f"tests/conftest.py: _REAL_JPYPE_MODULE initialisé à partir de _PRE_EXISTING_JPYPE_IN_SYS_MODULES (ID: {id(_REAL_JPYPE_MODULE)}).")
else:
    # Si jpype n'était pas dans sys.modules, on tente un import standard.
    logger.info("tests/conftest.py: JPype non préchargé, tentative d'import frais.")
    try:
        import jpype as r_jpype_fresh_import
        _REAL_JPYPE_MODULE = r_jpype_fresh_import
        logger.info(f"tests/conftest.py: Vrai module JPype importé fraîchement (ID: {id(_REAL_JPYPE_MODULE)}).")
        # Laisser ce jpype importé dans sys.modules pour l'instant.
        # La fixture activate_jpype_mock_if_needed le remplacera par le mock si nécessaire pour les tests unitaires.
    except ImportError as e_fresh_import:
        logger.warning(f"tests/conftest.py: Le vrai module JPype n'a pas pu être importé fraîchement: {e_fresh_import}")
        _REAL_JPYPE_MODULE = None # S'assurer qu'il est None en cas d'échec
    except NameError as e_name_error_fresh_import: # Capturer le NameError potentiel ici aussi
        logger.error(f"tests/conftest.py: NameError lors de l'import frais de JPype: {e_name_error_fresh_import}. Cela indique un problème d'installation/configuration de JPype.")
        _REAL_JPYPE_MODULE = None # S'assurer qu'il est None en cas d'échec

if _REAL_JPYPE_MODULE is None:
    logger.error("tests/conftest.py: _REAL_JPYPE_MODULE EST NONE après la tentative d'initialisation.")
else:
    logger.info(f"tests/conftest.py: _REAL_JPYPE_MODULE est initialisé (ID: {id(_REAL_JPYPE_MODULE)}) avant la définition des fixtures.")

# Nécessaire pour la fixture integration_jvm
_integration_jvm_started_session_scope = False
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm, TWEETY_VERSION # download_tweety_jars retiré
    from argumentation_analysis.paths import LIBS_DIR # Importer LIBS_DIR depuis paths.py
except ImportError as e_jvm_related_import:
    import traceback
    # Message d'erreur combinant les détails des deux versions
    print(f"AVERTISSEMENT: tests/conftest.py: Échec de l'import pour initialize_jvm, TWEETY_VERSION, LIBS_DIR (depuis jvm_setup/paths).")
    print(f"  Erreur détaillée: {type(e_jvm_related_import).__name__}: {e_jvm_related_import}")
    print(f"  Traceback de l'échec d'import:\n{traceback.format_exc()}")
    initialize_jvm = None
    LIBS_DIR = None
    TWEETY_VERSION = None # S'assurer qu'il est None en cas d'échec

# --- Gestion du Path pour les Mocks ---
current_dir_for_mock = os.path.dirname(os.path.abspath(__file__))
mocks_dir_for_mock = os.path.join(current_dir_for_mock, 'mocks')
if mocks_dir_for_mock not in sys.path:
    sys.path.insert(0, mocks_dir_for_mock)
    print(f"INFO: tests/conftest.py: Ajout de {mocks_dir_for_mock} à sys.path.")

# print("INFO: conftest.py: Logger configuré pour pytest hooks jpype.") # Déjà fait plus haut

# --- Mock Matplotlib et NetworkX au plus tôt ---
# try:
#     from matplotlib_mock import pyplot as mock_pyplot_instance
#     from matplotlib_mock import cm as mock_cm_instance
#     from matplotlib_mock import MatplotlibMock as MockMatplotlibModule_class
    
#     sys.modules['matplotlib.pyplot'] = mock_pyplot_instance
#     sys.modules['matplotlib.cm'] = mock_cm_instance
#     mock_mpl_module = MockMatplotlibModule_class()
#     mock_mpl_module.pyplot = mock_pyplot_instance
#     mock_mpl_module.cm = mock_cm_instance
#     sys.modules['matplotlib'] = mock_mpl_module
#     print("INFO: Matplotlib mocké globalement.")

#     from networkx_mock import NetworkXMock as MockNetworkXModule_class
#     sys.modules['networkx'] = MockNetworkXModule_class()
#     print("INFO: NetworkX mocké globalement.")

# except ImportError as e:
#     print(f"ERREUR CRITIQUE lors du mocking global de matplotlib ou networkx: {e}")
#     if 'matplotlib' not in str(e).lower():
#         sys.modules['matplotlib.pyplot'] = MagicMock()
#         sys.modules['matplotlib.cm'] = MagicMock()
#         sys.modules['matplotlib'] = MagicMock()
#         sys.modules['matplotlib'].pyplot = sys.modules['matplotlib.pyplot']
#         sys.modules['matplotlib'].cm = sys.modules['matplotlib.cm']
#     if 'networkx' not in str(e).lower():
#         sys.modules['networkx'] = MagicMock()
print("INFO: Mocking global de Matplotlib et NetworkX commenté pour débogage.")

# --- Mock NumPy Immédiat ---
def _install_numpy_mock_immediately():
    # Toujours installer/réinstaller le mock pour s'assurer qu'il est prioritaire
    # et correctement configuré, surtout si d'autres tests modifient sys.modules['numpy']
    print("INFO: _install_numpy_mock_immediately: Tentative d'installation/réinstallation du mock NumPy.")
    try:
        import numpy_mock # Assurez-vous que tests/mocks est dans sys.path
        
        # Sauvegarder l'ancien sys.modules['numpy'] s'il existe et n'est pas déjà notre mock principal
        # pour éviter les récursions si cette fonction est appelée plusieurs fois.
        # Note: Cette logique de sauvegarde/restauration est complexe et peut être source d'erreurs.
        # Pour l'instant, on écrase simplement.
        # original_numpy = sys.modules.get('numpy')

        # Créer un dictionnaire à partir de tous les attributs de numpy_mock
        mock_numpy_attrs = {attr: getattr(numpy_mock, attr) for attr in dir(numpy_mock) if not attr.startswith('__')}
        # S'assurer que __version__ est bien celle du mock
        mock_numpy_attrs['__version__'] = numpy_mock.__version__ if hasattr(numpy_mock, '__version__') else '1.24.3.mock'
        
        mock_numpy_module = type('numpy', (), mock_numpy_attrs)
        mock_numpy_module.__path__ = [] # Indiquer que c'est un package
        sys.modules['numpy'] = mock_numpy_module
        
        # Exposer explicitement les sous-modules nécessaires qui pourraient ne pas être des attributs directs
        if hasattr(numpy_mock, 'typing'):
            sys.modules['numpy.typing'] = numpy_mock.typing
        if hasattr(numpy_mock, '_core'):
            sys.modules['numpy._core'] = numpy_mock._core
        if hasattr(numpy_mock, 'core'):
            sys.modules['numpy.core'] = numpy_mock.core
        
        # Création explicite du mock pour numpy.rec et numpy.rec.recarray
        _mock_rec_submodule = type('rec', (), {})
        _mock_rec_submodule.recarray = type('recarray', (), {}) # Un type simple suffit pour isinstance

        # Mettre le sous-module mocké dans sys.modules pour les imports directs `from numpy import rec` ou `import numpy.rec`
        sys.modules['numpy.rec'] = _mock_rec_submodule

        # Attacher le sous-module mocké comme attribut au module numpy principal mocké (mock_numpy_module)
        # mock_numpy_module est déjà sys.modules['numpy'] à ce stade.
        if 'numpy' in sys.modules and sys.modules['numpy'] is mock_numpy_module:
            mock_numpy_module.rec = _mock_rec_submodule
        else:
            # Fallback si mock_numpy_module n'est pas (encore) sys.modules['numpy'] ou a été écrasé.
            # Cela ne devrait pas arriver si la logique est correcte.
            print("AVERTISSEMENT: mock_numpy_module n'était pas sys.modules['numpy'] lors de l'attribution de .rec")
            # Tentative de l'assigner quand même si sys.modules['numpy'] existe et est un mock
            if 'numpy' in sys.modules and hasattr(sys.modules['numpy'], '__dict__'): # Check si c'est un objet modifiable
                setattr(sys.modules['numpy'], 'rec', _mock_rec_submodule)

        print(f"INFO: Mock numpy.rec configuré. sys.modules['numpy.rec'] (ID: {id(sys.modules.get('numpy.rec'))}), mock_numpy_module.rec (ID: {id(getattr(mock_numpy_module, 'rec', None))})")

        # Assurer que les multiarray sont là si _core/core les ont
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'multiarray'):
             sys.modules['numpy._core.multiarray'] = numpy_mock._core.multiarray
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'multiarray'):
             sys.modules['numpy.core.multiarray'] = numpy_mock.core
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'numeric'):
             sys.modules['numpy.core.numeric'] = numpy_mock.core.numeric
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'numeric'):
             sys.modules['numpy._core.numeric'] = numpy_mock._core.numeric
        if hasattr(numpy_mock, 'linalg'):
             sys.modules['numpy.linalg'] = numpy_mock.linalg
        if hasattr(numpy_mock, 'fft'):
             sys.modules['numpy.fft'] = numpy_mock.fft
        if hasattr(numpy_mock, 'lib'):
             sys.modules['numpy.lib'] = numpy_mock.lib
        
        # S'assurer que le module lui-même est bien dans sys.modules
        # Cela peut être redondant si type() le fait déjà, mais ne nuit pas.
        # Les lignes suivantes étaient problématiques car numpy_typing_mock, _core, core n'étaient pas définis ici.
        # La logique ci-dessus avec hasattr devrait suffire.
        # sys.modules['numpy'] = sys.modules['numpy']
        # sys.modules['numpy.typing'] = numpy_typing_mock
        # sys.modules['numpy._core'] = _core
        # sys.modules['numpy.core'] = core
        # sys.modules['numpy._core.multiarray'] = _core.multiarray
        # sys.modules['numpy.core.multiarray'] = core.multiarray
        # if 'rec' in sys.modules['numpy'].__dict__:
        #     sys.modules['numpy.rec'] = sys.modules['numpy'].rec
        print("INFO: Mock NumPy installé immédiatement dans conftest.py (avec sous-modules).")
    except ImportError as e:
        print(f"ERREUR lors de l'installation immédiate du mock NumPy: {e}")

if (sys.version_info.major == 3 and sys.version_info.minor >= 10): # Modifié pour inclure 3.10
    _install_numpy_mock_immediately()
    # print("INFO: Installation immédiate du mock NumPy commentée pour débogage.") # Commenté pour activer

# --- Mock Pandas Immédiat ---
# def _install_pandas_mock_immediately():
#     if 'pandas' not in sys.modules:
#         try:
#             from pandas_mock import DataFrame, read_csv, read_json
#             sys.modules['pandas'] = type('pandas', (), {
#                 'DataFrame': DataFrame, 'read_csv': read_csv, 'read_json': read_json, 'Series': list,
#                 'NA': None, 'NaT': None, 'isna': lambda x: x is None, 'notna': lambda x: x is not None,
#                 '__version__': '1.5.3',
#             })
#             sys.modules['pandas.core'] = type('pandas.core', (), {})
#             sys.modules['pandas.core.api'] = type('pandas.core.api', (), {})
#             sys.modules['pandas._libs'] = type('pandas._libs', (), {})
#             sys.modules['pandas._libs.pandas_datetime'] = type('pandas._libs.pandas_datetime', (), {})
#             print("INFO: Mock Pandas installé immédiatement dans conftest.py")
#         except ImportError as e:
#             print(f"ERREUR lors de l'installation immédiate du mock Pandas: {e}")

# Installation immédiate si Python 3.12+ ou si pandas n'est pas disponible (de HEAD)
# if (sys.version_info.major == 3 and sys.version_info.minor >= 12):
#     _install_pandas_mock_immediately()
print("INFO: Installation immédiate du mock Pandas commentée pour débogage.")

# --- Mock JPype ---
try:
    from jpype_mock import (
        isJVMStarted, startJVM, getJVMPath, getJVMVersion, getDefaultJVMPath,
        JClass, JException, JObject, JVMNotFoundException, _jpype as mock_dot_jpype_module
    )
    # Importer le vrai module mock d'imports
    from tests.mocks.jpype_components.imports import imports_module as actual_mock_jpype_imports_module
    # sys.modules['jpype.imports'] = mock_jpype_imports_module # Commenté: sera géré par la logique de _REAL_JPYPE_MODULE ou _JPYPE_MODULE_MOCK_OBJ_GLOBAL
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
    jpype_module_mock_obj.imports = actual_mock_jpype_imports_module # Utiliser le vrai mock
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = jpype_module_mock_obj
    _MOCK_DOT_JPYPE_MODULE_GLOBAL = mock_dot_jpype_module
    print("INFO: Mock JPype préparé (sera installé conditionnellement par activate_jpype_mock_if_needed).")
except ImportError as e_jpype:
    print(f"ERREUR CRITIQUE lors de l'import de jpype_mock: {e_jpype}. Utilisation de mocks de fallback pour JPype.")
    _fb_jpype_mock = MagicMock(name="jpype_fallback_mock")
    _fb_jpype_mock.imports = MagicMock(name="jpype.imports_fallback_mock")
    _fb_dot_jpype_mock = MagicMock(name="_jpype_fallback_mock")
    
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = _fb_jpype_mock
    _MOCK_DOT_JPYPE_MODULE_GLOBAL = _fb_dot_jpype_mock
    print("INFO: Mock JPype de FALLBACK préparé et assigné aux variables globales de mock.")

# --- Mock ExtractDefinitions ---
# try:
#     from extract_definitions_mock import setup_extract_definitions_mock
#     setup_extract_definitions_mock()
#     print("INFO: ExtractDefinitions mocké globalement.")
# except ImportError as e_extract:
#     print(f"ERREUR lors du mocking d'ExtractDefinitions: {e_extract}")
# except Exception as e_extract_setup:
#     print(f"ERREUR lors de la configuration du mock ExtractDefinitions: {e_extract_setup}")
print("INFO: Mocking global de ExtractDefinitions commenté pour débogage.")

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def is_module_available(module_name):
    if module_name in sys.modules:
        if isinstance(sys.modules[module_name], MagicMock) or \
           (module_name == 'jpype' and 'jpype_module_mock_obj' in globals() and sys.modules[module_name] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL): # Modifié pour utiliser la globale
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

def setup_numpy():
    if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('numpy'):
        if not is_module_available('numpy'): print("NumPy non disponible, utilisation du mock.")
        else: print("Python 3.12+ détecté, utilisation du mock NumPy.")
        import numpy_mock
        # Créer un dictionnaire à partir de tous les attributs de numpy_mock
        mock_numpy_attrs = {attr: getattr(numpy_mock, attr) for attr in dir(numpy_mock) if not attr.startswith('__')}
        # S'assurer que __version__ est bien celle du mock
        mock_numpy_attrs['__version__'] = numpy_mock.__version__ if hasattr(numpy_mock, '__version__') else '1.24.3.mock'

        mock_numpy_module_setup_func = type('numpy', (), mock_numpy_attrs)
        mock_numpy_module_setup_func.__path__ = [] # Indiquer que c'est un package
        sys.modules['numpy'] = mock_numpy_module_setup_func
        
        # Exposer explicitement les sous-modules nécessaires
        if hasattr(numpy_mock, 'typing'):
            sys.modules['numpy.typing'] = numpy_mock.typing
        if hasattr(numpy_mock, '_core'):
            sys.modules['numpy._core'] = numpy_mock._core
        if hasattr(numpy_mock, 'core'):
            sys.modules['numpy.core'] = numpy_mock.core
            # Assurer l'attribut sur le mock principal si sys.modules['numpy'] est bien notre mock_numpy_module
            if 'numpy' in sys.modules and hasattr(sys.modules['numpy'], 'core'):
                sys.modules['numpy'].core = numpy_mock.core


        # Création explicite et assignation du mock pour numpy.rec et numpy.rec.recarray
        _mock_rec_submodule_setup = type('rec', (), {})
        _mock_rec_submodule_setup.recarray = type('recarray', (), {}) # Un type simple suffit pour isinstance

        # Mettre le sous-module mocké dans sys.modules pour les imports directs `from numpy import rec` ou `import numpy.rec`
        sys.modules['numpy.rec'] = _mock_rec_submodule_setup
        
        # Attacher le sous-module mocké comme attribut au module numpy principal mocké (mock_numpy_module_setup_func)
        # mock_numpy_module_setup_func est déjà sys.modules['numpy'] à ce stade.
        if 'numpy' in sys.modules and sys.modules['numpy'] is mock_numpy_module_setup_func:
            mock_numpy_module_setup_func.rec = _mock_rec_submodule_setup
        else:
            # Fallback
            print("AVERTISSEMENT: mock_numpy_module_setup_func n'était pas sys.modules['numpy'] lors de l'attribution de .rec dans setup_numpy")
            if 'numpy' in sys.modules and hasattr(sys.modules['numpy'], '__dict__'):
                 setattr(sys.modules['numpy'], 'rec', _mock_rec_submodule_setup)
        
        print(f"INFO: Mock numpy.rec configuré dans setup_numpy. sys.modules['numpy.rec'] (ID: {id(sys.modules.get('numpy.rec'))}), mock_numpy_module_setup_func.rec (ID: {id(getattr(mock_numpy_module_setup_func, 'rec', None))})")
        
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'multiarray'):
            sys.modules['numpy._core.multiarray'] = numpy_mock._core.multiarray
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'multiarray'):
            sys.modules['numpy.core.multiarray'] = numpy_mock.core
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'numeric'):
            sys.modules['numpy.core.numeric'] = numpy_mock.core.numeric
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'numeric'):
            sys.modules['numpy._core.numeric'] = numpy_mock._core.numeric
        if hasattr(numpy_mock, 'linalg'):
            sys.modules['numpy.linalg'] = numpy_mock.linalg
        if hasattr(numpy_mock, 'fft'):
            sys.modules['numpy.fft'] = numpy_mock.fft
        if hasattr(numpy_mock, 'lib'):
            sys.modules['numpy.lib'] = numpy_mock.lib

        print("INFO: Mock NumPy configuré dynamiquement (avec tous les attributs et sous-modules de numpy_mock).")
        return sys.modules['numpy']
    else:
        import numpy
        print(f"Utilisation de la vraie bibliothèque NumPy (version {getattr(numpy, '__version__', 'inconnue')})")
        return numpy

def setup_pandas():
    if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('pandas'):
        if not is_module_available('pandas'): print("Pandas non disponible, utilisation du mock.")
        else: print("Python 3.12+ détecté, utilisation du mock Pandas.")
        
        try:
            from pandas_mock import (
                PandasMock, DataFrame, read_csv, read_json, get_option, set_option,
                MockPandasIO, MockPandasIOFormats, MockPandasIOFormatsConsole
            )
            _pandas_module_instance = PandasMock()
            sys.modules['pandas'] = _pandas_module_instance
            setattr(sys.modules['pandas'], 'get_option', get_option)
            setattr(sys.modules['pandas'], 'set_option', set_option)
            _pandas_io_instance = MockPandasIO()
            sys.modules['pandas.io'] = _pandas_io_instance
            sys.modules['pandas.io.formats'] = _pandas_io_instance.formats
            sys.modules['pandas.io.formats.console'] = _pandas_io_instance.formats.console
            print("INFO: Mock Pandas complet (avec io.formats.console) installé depuis conftest.py")
        except ImportError as e:
            print(f"ERREUR CRITIQUE lors de l'importation des composants de pandas_mock dans conftest.py: {e}")
            from pandas_mock import DataFrame, read_csv, read_json # Fallback
            sys.modules['pandas'] = type('pandas', (), {
                'DataFrame': DataFrame, 'read_csv': read_csv, 'read_json': read_json, 'Series': list,
                'NA': None, 'NaT': None, 'isna': lambda x: x is None, 'notna': lambda x: x is not None,
                '__version__': '1.5.3.mock_fallback',
            })
            sys.modules['pandas.io'] = MagicMock()
            sys.modules['pandas.io.formats'] = MagicMock()
            sys.modules['pandas.io.formats.console'] = MagicMock()
        return sys.modules['pandas']
    else:
        import pandas
        print(f"Utilisation de la vraie bibliothèque Pandas (version {getattr(pandas, '__version__', 'inconnue')})")
        return pandas

# @pytest.fixture(scope="session", autouse=True)
# def setup_numpy_for_tests_fixture():
#     if 'PYTEST_CURRENT_TEST' in os.environ:
#         numpy_module = setup_numpy()
#         if sys.modules.get('numpy') is not numpy_module:
#             sys.modules['numpy'] = numpy_module
#         yield
#     else:
#         yield
print("INFO: Fixture setup_numpy_for_tests_fixture commentée pour débogage.")

# @pytest.fixture(scope="session", autouse=True)
# def setup_pandas_for_tests_fixture():
#     if 'PYTEST_CURRENT_TEST' in os.environ:
#         pandas_module = setup_pandas()
#         if sys.modules.get('pandas') is not pandas_module:
#             sys.modules['pandas'] = pandas_module
#         yield
#     else:
#         yield
print("INFO: Fixture setup_pandas_for_tests_fixture commentée pour débogage.")

# Configuration du logger spécifique pour les fixtures d'intégration JPype
logger_conftest_integration = logging.getLogger("conftest_integration_jvm_specific")
if not logger_conftest_integration.handlers:
    handler_conftest_integration = logging.StreamHandler(sys.stdout)
    formatter_conftest_integration = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler_conftest_integration.setFormatter(formatter_conftest_integration)
    logger_conftest_integration.addHandler(handler_conftest_integration)
    logger_conftest_integration.setLevel(logging.INFO)
    logger_conftest_integration.propagate = False

@pytest.fixture(scope="session")
def integration_jvm(request):
    logger.info("tests/conftest.py: Début de la fixture 'integration_jvm'.")
    global _integration_jvm_started_session_scope, _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL # Déplacé ici pour être avant son utilisation
    """
    Fixture de session pour démarrer et arrêter la JVM pour les tests d'intégration JPype.
    - Gère le démarrage unique de la JVM pour toute la session de test si nécessaire.
    - Utilise la logique de `initialize_jvm` de `argumentation_analysis.core.jvm_setup`.
    - S'assure que le VRAI module `jpype` est utilisé pendant son exécution.
    - Tente de s'assurer que `jpype.config` est accessible avant `shutdownJVM` pour éviter
      les `ModuleNotFoundError` dans les handlers `atexit` de JPype.
    - Laisse le vrai module `jpype` dans `sys.modules` après un arrêt réussi de la JVM
      par cette fixture, pour permettre aux handlers `atexit` de JPype de s'exécuter correctement.
    """
    # global _integration_jvm_started_session_scope, _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL # Déjà déclaré plus haut

    logger.info(f"tests/conftest.py: Dans 'integration_jvm', vérification de _REAL_JPYPE_MODULE. Est-il None? {_REAL_JPYPE_MODULE is None}")
    if _REAL_JPYPE_MODULE is not None:
        logger.info(f"tests/conftest.py: Dans 'integration_jvm', _REAL_JPYPE_MODULE ID: {id(_REAL_JPYPE_MODULE)}")

    if _REAL_JPYPE_MODULE is None:
        logger.error("tests/conftest.py: ERREUR FATALE dans 'integration_jvm': _REAL_JPYPE_MODULE est None. Appel de pytest.fail.")
        pytest.fail("Le vrai module JPype (_REAL_JPYPE_MODULE) est None dans la fixture integration_jvm. Tests d'intégration JPype impossibles.", pytrace=False)
        return

    # Sauvegarder l'état actuel de sys.modules pour jpype et _jpype
    original_sys_jpype = sys.modules.get('jpype')
    original_sys_dot_jpype = sys.modules.get('_jpype')

    # Installer le vrai JPype pour la durée de cette fixture
    sys.modules['jpype'] = _REAL_JPYPE_MODULE
    if hasattr(_REAL_JPYPE_MODULE, '_jpype'): # Le module C interne
        sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
    elif '_jpype' in sys.modules: # S'il y avait un _jpype (peut-être du mock), l'enlever
        del sys.modules['_jpype']
    
    current_jpype_in_use = sys.modules['jpype'] # Devrait être _REAL_JPYPE_MODULE
    logger.info(f"Fixture 'integration_jvm' (session scope) appelée. Utilisation de JPype ID: {id(current_jpype_in_use)}")

    try:
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - Début. current_jpype_in_use (ID: {id(current_jpype_in_use)}).isJVMStarted() = {current_jpype_in_use.isJVMStarted()}")
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - _integration_jvm_started_session_scope = {_integration_jvm_started_session_scope}")

        if current_jpype_in_use.isJVMStarted() and not _integration_jvm_started_session_scope:
            logger.error("integration_jvm: ERREUR CRITIQUE - La JVM est déjà démarrée (par un mécanisme externe ou un précédent test non nettoyé) alors que _integration_jvm_started_session_scope est False. Cela indique un problème de gestion de la JVM.")
            # Envisager un pytest.fail ici si cela ne devrait jamais arriver.
            # Pour l'instant, on loggue l'erreur et on continue en espérant que la JVM existante est utilisable.
            # Cependant, cela peut masquer la cause racine du problème.
            # Si on continue, on devrait peut-être marquer _integration_jvm_started_session_scope = True
            # pour refléter que la JVM est démarrée, bien que pas par cette instance de la fixture.
            # Mais cela complique la logique de shutdown.
            # Pour l'instant, on loggue et on laisse la logique suivante potentiellement re-démarrer ou échouer.
            # pytest.fail("JVM démarrée prématurément par un mécanisme externe. La fixture 'integration_jvm' doit contrôler son initialisation.", pytrace=False)
            # return # Ou laisser la logique ci-dessous échouer si elle tente de redémarrer.

        if _integration_jvm_started_session_scope and current_jpype_in_use.isJVMStarted():
            logger.info("integration_jvm: La JVM a déjà été initialisée par cette fixture dans cette session. Yielding.")
            yield
            return
        
        logger.info(f"integration_jvm: Vérification des dépendances pour initialize_jvm: initialize_jvm is None: {initialize_jvm is None}, LIBS_DIR is None: {LIBS_DIR is None}, TWEETY_VERSION is None: {TWEETY_VERSION is None}")
        if LIBS_DIR is not None:
            logger.info(f"integration_jvm: LIBS_DIR = {LIBS_DIR} (exists: {os.path.exists(LIBS_DIR)})")
        if TWEETY_VERSION is not None:
            logger.info(f"integration_jvm: TWEETY_VERSION = {TWEETY_VERSION}")


        if initialize_jvm is None or LIBS_DIR is None or TWEETY_VERSION is None:
            logger.error("integration_jvm: ERREUR FATALE - Dépendances manquantes: initialize_jvm, LIBS_DIR ou TWEETY_VERSION non disponible. Impossible de démarrer la JVM.")
            pytest.fail("ERREUR FATALE FIXTURE: Dépendances manquantes pour démarrer la JVM (initialize_jvm, LIBS_DIR, TWEETY_VERSION).", pytrace=False)
            return

        logger.info("integration_jvm: Tentative d'initialisation de la JVM via initialize_jvm...")
        # initialize_jvm devrait utiliser le jpype actuellement dans sys.modules
        success = initialize_jvm(
            lib_dir_path=str(LIBS_DIR),
            tweety_version=TWEETY_VERSION
        )
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - initialize_jvm() APPELÉ. Résultat (success variable): {success}")
        
        # Vérification explicite de l'état de la JVM *après* l'appel à initialize_jvm
        jvm_actually_started_after_call = current_jpype_in_use.isJVMStarted()
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - Après initialize_jvm - current_jpype_in_use.isJVMStarted() = {jvm_actually_started_after_call}")
        
        if not success or not jvm_actually_started_after_call:
            logger.error(f"integration_jvm: ÉCHEC CRITIQUE de l'initialisation de la JVM. success: {success}, jvm_actually_started_after_call: {jvm_actually_started_after_call}.")
            _integration_jvm_started_session_scope = False # Assurer que c'est False
            # Restauration immédiate en cas d'échec de démarrage avant même le yield
            logger.info("integration_jvm: Restauration de sys.modules pour jpype/_jpype après échec de démarrage.")
            if original_sys_jpype is not None: sys.modules['jpype'] = original_sys_jpype
            elif 'jpype' in sys.modules: del sys.modules['jpype']
            if original_sys_dot_jpype is not None: sys.modules['_jpype'] = original_sys_dot_jpype
            elif '_jpype' in sys.modules: del sys.modules['_jpype']
            pytest.fail(f"ÉCHEC FIXTURE integration_jvm: Démarrage JVM a échoué (success: {success}, isJVMStarted: {jvm_actually_started_after_call}).", pytrace=False)
        else:
            _integration_jvm_started_session_scope = True # Marquer comme démarrée par cette fixture
            logger.info(f"integration_jvm: JVM initialisée avec succès par cette fixture. Yielding _REAL_JPYPE_MODULE (ID: {id(_REAL_JPYPE_MODULE)}).")
            
        yield _REAL_JPYPE_MODULE # Le test s'exécute ici, et les fixtures dépendantes reçoivent _REAL_JPYPE_MODULE
        
    finally:
        logger.info("integration_jvm: Bloc finally atteint (après yield ou en cas d'exception pendant le test).")
        # La logique de shutdown est maintenant ici, au lieu d'être dans un finalizer séparé.
        current_jpype_for_shutdown = sys.modules.get('jpype')
        jvm_was_shutdown_by_this_fixture = False

        if _integration_jvm_started_session_scope and current_jpype_for_shutdown is _REAL_JPYPE_MODULE and current_jpype_for_shutdown.isJVMStarted():
            try:
                logger.info("integration_jvm (finally): Vérification/Import de jpype.config avant shutdown...")
                if hasattr(current_jpype_for_shutdown, 'config'): # Utiliser current_jpype_for_shutdown
                    logger.info(f"   jpype.config déjà présent (type: {type(current_jpype_for_shutdown.config)}).")
                else:
                    try:
                        import jpype.config # Assumant que jpype est _REAL_JPYPE_MODULE
                        logger.info("   Import explicite de jpype.config réussi.")
                    except Exception as e_cfg_imp_finally:
                         logger.error(f"   Erreur lors de l'import de jpype.config dans finally: {type(e_cfg_imp_finally).__name__}: {e_cfg_imp_finally}")


                logger.info("integration_jvm (finally): Tentative d'arrêt de la JVM (vrai JPype)...")
                logger.info("integration_jvm (finally): APPEL IMMINENT DE current_jpype_for_shutdown.shutdownJVM()")
                current_jpype_for_shutdown.shutdownJVM()
                logger.info("integration_jvm (finally): current_jpype_for_shutdown.shutdownJVM() APPELÉ.")
                logger.info("integration_jvm (finally): JVM arrêtée (vrai JPype).")
                jvm_was_shutdown_by_this_fixture = True
            except Exception as e_shutdown:
                logger.error(f"integration_jvm (finally): Erreur arrêt JVM (vrai JPype): {e_shutdown}", exc_info=True)
            finally: # Nested finally pour s'assurer que _integration_jvm_started_session_scope est réinitialisé
                logger.info(f"integration_jvm (finally - nested): Réinitialisation de _integration_jvm_started_session_scope (valeur actuelle: {_integration_jvm_started_session_scope}) à False.")
                _integration_jvm_started_session_scope = False
        
        if not jvm_was_shutdown_by_this_fixture:
            logger.info("integration_jvm (finally): La JVM n'a pas été arrêtée par cette fixture ou une erreur s'est produite. Restauration de sys.modules.")
        else:
            logger.info("integration_jvm (finally): La JVM a été arrêtée. sys.modules['jpype'] reste _REAL_JPYPE_MODULE pour les handlers atexit.")
            # Laisser _REAL_JPYPE_MODULE en place pour atexit, mais s'assurer que _jpype correspond
            if _REAL_JPYPE_MODULE and hasattr(_REAL_JPYPE_MODULE, '_jpype'):
                sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
            elif _REAL_JPYPE_MODULE and '_jpype' in sys.modules and sys.modules['_jpype'] is _MOCK_DOT_JPYPE_MODULE_GLOBAL:
                logger.info("integration_jvm (finally): _REAL_JPYPE_MODULE laissé, suppression du _MOCK_DOT_JPYPE_MODULE_GLOBAL de sys.modules['_jpype'].")
                if '_jpype' in sys.modules: del sys.modules['_jpype'] # Vérifier avant de supprimer
            # Ne pas restaurer original_sys_jpype et original_sys_dot_jpype si shutdown réussi
            return # Sortir du finally pour éviter la restauration ci-dessous si shutdown ok

        # Restauration si shutdown n'a pas eu lieu ou a échoué
        logger.info("integration_jvm (finally): Restauration de l'état original de sys.modules pour jpype/_jpype.")
        if original_sys_jpype is not None:
            sys.modules['jpype'] = original_sys_jpype
        elif 'jpype' in sys.modules and sys.modules['jpype'] is _REAL_JPYPE_MODULE : # Si c'est notre vrai module et qu'on doit restaurer
             del sys.modules['jpype']

        if original_sys_dot_jpype is not None:
            sys.modules['_jpype'] = original_sys_dot_jpype
        elif '_jpype' in sys.modules and hasattr(_REAL_JPYPE_MODULE, '_jpype') and sys.modules['_jpype'] is _REAL_JPYPE_MODULE._jpype:
             del sys.modules['_jpype']
        logger.info("État original de sys.modules pour jpype/_jpype restauré (cas non-shutdown ou erreur dans finally).")


# Fixture pour activer le mock JPype pour les tests unitaires
@pytest.fixture(scope="function", autouse=True)
def activate_jpype_mock_if_needed(request):
    """
    Fixture à portée "function" et "autouse=True" pour gérer la sélection entre le mock JPype et le vrai JPype.

    Logique de sélection :
    1. Si un test est marqué avec `@pytest.mark.real_jpype`, le vrai module JPype (`_REAL_JPYPE_MODULE`)
       est placé dans `sys.modules['jpype']`.
    2. Si le chemin du fichier de test contient 'tests/integration/' ou 'tests/minimal_jpype_tweety_tests/',
       le vrai JPype est également utilisé.
    3. Dans tous les autres cas (tests unitaires par défaut), le mock JPype (`_JPYPE_MODULE_MOCK_OBJ_GLOBAL`)
       est activé.

    Gestion de l'état du mock :
    - Avant chaque test utilisant le mock, l'état interne du mock JPype est réinitialisé :
        - `tests.mocks.jpype_components.jvm._jvm_started` est mis à `False`.
        - `tests.mocks.jpype_components.jvm._jvm_path` est mis à `None`.
        - `_JPYPE_MODULE_MOCK_OBJ_GLOBAL.config.jvm_path` est mis à `None`.
      Cela garantit que chaque test unitaire commence avec une JVM mockée "propre" et non démarrée.
      `jpype.isJVMStarted()` (version mockée) retournera donc `False` au début de ces tests.
      Un appel à `jpype.startJVM()` (version mockée) mettra `_jvm_started` à `True` pour la durée du test.

    Restauration :
    - Après chaque test, l'état original de `sys.modules['jpype']`, `sys.modules['_jpype']`,
      et `sys.modules['jpype.imports']` est restauré.

    Interaction avec `integration_jvm` :
    - Pour les tests nécessitant la vraie JVM (marqués `real_jpype` ou dans les chemins d'intégration),
      cette fixture s'assure que le vrai `jpype` est dans `sys.modules`. La fixture `integration_jvm`
      (scope session) est alors responsable du démarrage effectif de la vraie JVM une fois par session
      et de sa gestion.
    """
    global _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL, _REAL_JPYPE_MODULE
    
    use_real_jpype = False
    if request.node.get_closest_marker("real_jpype"):
        use_real_jpype = True
    path_str = str(request.node.fspath).replace(os.sep, '/')
    if 'tests/integration/' in path_str or 'tests/minimal_jpype_tweety_tests/' in path_str:
        use_real_jpype = True

    if use_real_jpype:
        logger.info(f"Test {request.node.name} demande REAL JPype. Configuration de sys.modules pour utiliser le vrai JPype.")
        if _REAL_JPYPE_MODULE:
            sys.modules['jpype'] = _REAL_JPYPE_MODULE
            if hasattr(_REAL_JPYPE_MODULE, '_jpype'):
                sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
            elif '_jpype' in sys.modules and sys.modules.get('_jpype') is not getattr(_REAL_JPYPE_MODULE, '_jpype', None) :
                del sys.modules['_jpype']
            if hasattr(_REAL_JPYPE_MODULE, 'imports'):
                sys.modules['jpype.imports'] = _REAL_JPYPE_MODULE.imports
            elif 'jpype.imports' in sys.modules and sys.modules.get('jpype.imports') is not getattr(_REAL_JPYPE_MODULE, 'imports', None):
                del sys.modules['jpype.imports']
            logger.debug(f"REAL JPype (ID: {id(_REAL_JPYPE_MODULE)}) est maintenant sys.modules['jpype'].")
        else:
            logger.error(f"Test {request.node.name} demande REAL JPype, mais _REAL_JPYPE_MODULE n'est pas disponible. Test échouera probablement.")
        yield
    else:
        logger.info(f"Test {request.node.name} utilise MOCK JPype.")

        # --- Début de la fusion des logiques ---

        # 1. Réinitialiser l'état _jvm_started et _jvm_path du mock JPype (de origin/main)
        try:
            jpype_components_jvm_module = sys.modules.get('tests.mocks.jpype_components.jvm')
            if jpype_components_jvm_module:
                if hasattr(jpype_components_jvm_module, '_jvm_started'):
                    jpype_components_jvm_module._jvm_started = False
                if hasattr(jpype_components_jvm_module, '_jvm_path'):
                    jpype_components_jvm_module._jvm_path = None
                if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config') and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL.config, 'jvm_path'):
                    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config.jvm_path = None
                logger.info("État (_jvm_started, _jvm_path, config.jvm_path) du mock JPype réinitialisé pour le test.")
            else:
                logger.warning("Impossible de réinitialiser l'état du mock JPype: module 'tests.mocks.jpype_components.jvm' non trouvé.")
        except Exception as e_reset_mock:
            logger.error(f"Erreur lors de la réinitialisation de l'état du mock JPype: {e_reset_mock}")

        # 2. Logique de gestion agressive de sys.modules (de HEAD)
        original_modules = {}
        # Modules à potentiellement supprimer et remplacer par des mocks
        modules_to_handle = ['jpype', '_jpype', 'jpype._core', 'jpype.imports', 'jpype.types', 'jpype.config', 'jpype.JProxy']
        
        # Tentative de patcher directement jpype.imports._jpype
        if 'jpype.imports' in sys.modules and \
           hasattr(sys.modules['jpype.imports'], '_jpype') and \
           _MOCK_DOT_JPYPE_MODULE_GLOBAL is not None and \
           hasattr(_MOCK_DOT_JPYPE_MODULE_GLOBAL, 'isStarted'):
            if sys.modules['jpype.imports']._jpype is not _MOCK_DOT_JPYPE_MODULE_GLOBAL:
                if 'jpype.imports._jpype_original' not in original_modules:
                     original_modules['jpype.imports._jpype_original'] = sys.modules['jpype.imports']._jpype
                logger.debug(f"Patch direct de sys.modules['jpype.imports']._jpype avec notre mock _jpype.")
                sys.modules['jpype.imports']._jpype = _MOCK_DOT_JPYPE_MODULE_GLOBAL
            else:
                logger.debug("sys.modules['jpype.imports']._jpype est déjà notre mock.")
        
        for module_name in modules_to_handle:
            if module_name in sys.modules:
                is_current_module_our_mock = False
                if module_name == 'jpype' and sys.modules[module_name] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL: is_current_module_our_mock = True
                elif module_name in ['_jpype', 'jpype._core'] and sys.modules[module_name] is _MOCK_DOT_JPYPE_MODULE_GLOBAL: is_current_module_our_mock = True
                elif module_name == 'jpype.imports' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'imports') and sys.modules[module_name] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports: is_current_module_our_mock = True
                elif module_name == 'jpype.config' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config') and sys.modules[module_name] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config: is_current_module_our_mock = True
                
                if not is_current_module_our_mock and module_name not in original_modules:
                    original_modules[module_name] = sys.modules.pop(module_name)
                    logger.debug(f"Supprimé et sauvegardé sys.modules['{module_name}']")
                elif module_name in sys.modules and is_current_module_our_mock:
                    del sys.modules[module_name]
                    logger.debug(f"Supprimé notre mock préexistant pour sys.modules['{module_name}'].")
                elif module_name in sys.modules:
                    del sys.modules[module_name]
                    logger.debug(f"Supprimé sys.modules['{module_name}'] (sauvegarde prioritaire existante).")

        # 3. Mettre en place nos mocks principaux (de HEAD, légèrement adapté)
        sys.modules['jpype'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL
        sys.modules['_jpype'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
        sys.modules['jpype._core'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL # Assurer que _core est aussi notre mock
        if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'imports'):
            sys.modules['jpype.imports'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports
        else: # Fallback si le mock global n'a pas d'attribut 'imports'
            sys.modules['jpype.imports'] = MagicMock(name="jpype.imports_fallback_in_fixture")

        if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config'):
            sys.modules['jpype.config'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config
        else: # Fallback
            sys.modules['jpype.config'] = MagicMock(name="jpype.config_fallback_in_fixture")
            
        mock_types_module = MagicMock(name="jpype.types_mock_module_dynamic_in_fixture")
        for type_name in ["JString", "JArray", "JObject", "JBoolean", "JInt", "JDouble", "JLong", "JFloat", "JShort", "JByte", "JChar"]:
            if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, type_name):
                setattr(mock_types_module, type_name, getattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, type_name))
            else:
                setattr(mock_types_module, type_name, MagicMock(name=f"Mock{type_name}_in_fixture"))
        sys.modules['jpype.types'] = mock_types_module
        
        sys.modules['jpype.JProxy'] = MagicMock(name="jpype.JProxy_mock_module_dynamic_in_fixture")

        logger.debug(f"Mocks JPype (principal, _jpype/_core, imports, config, types, JProxy) mis en place.")

        # --- Fin de la fusion des logiques ---

        yield # Exécution du test
        
        logger.debug(f"Nettoyage après test {request.node.name} (utilisation du mock).")
        
        # Restaurer _jpype de jpype.imports s'il a été patché directement (de HEAD)
        if 'jpype.imports._jpype_original' in original_modules:
            if 'jpype.imports' in sys.modules and hasattr(sys.modules['jpype.imports'], '_jpype'):
                sys.modules['jpype.imports']._jpype = original_modules['jpype.imports._jpype_original']
                logger.debug("Restauré jpype.imports._jpype à sa valeur originale.")
            del original_modules['jpype.imports._jpype_original']

        # Supprimer les mocks que nous avons mis en place (de HEAD, adapté)
        modules_we_set_up_in_fixture = ['jpype', '_jpype', 'jpype._core', 'jpype.imports', 'jpype.config', 'jpype.types', 'jpype.JProxy']
        for module_name in modules_we_set_up_in_fixture:
            current_module_in_sys = sys.modules.get(module_name)
            is_our_specific_mock_from_fixture = False
            if module_name == 'jpype' and current_module_in_sys is _JPYPE_MODULE_MOCK_OBJ_GLOBAL: is_our_specific_mock_from_fixture = True
            elif module_name in ['_jpype', 'jpype._core'] and current_module_in_sys is _MOCK_DOT_JPYPE_MODULE_GLOBAL: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.imports' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'imports') and current_module_in_sys is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.config' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config') and current_module_in_sys is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.types' and current_module_in_sys is mock_types_module: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.JProxy' and isinstance(current_module_in_sys, MagicMock) and hasattr(current_module_in_sys, 'name') and "jpype.JProxy_mock_module_dynamic_in_fixture" in current_module_in_sys.name : is_our_specific_mock_from_fixture = True
            
            if is_our_specific_mock_from_fixture:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                    logger.debug(f"Supprimé notre mock pour sys.modules['{module_name}']")

        # Restaurer les modules originaux (de HEAD)
        for module_name, original_module in original_modules.items():
            sys.modules[module_name] = original_module
            logger.debug(f"Restauré sys.modules['{module_name}'] à {original_module}")
        
        logger.info(f"État de JPype restauré après test {request.node.name} (utilisation du mock).")

# @pytest.fixture(scope="session")
# # def integration_jvm(request, ensure_tweety_libs): # Temporairement retiré ensure_tweety_libs
# def integration_jvm(request):
#     """
#     Fixture à portée "session" pour gérer le cycle de vie de la VRAIE JVM pour les tests d'intégration.
#
#     Objectifs et fonctionnement :
#     1. Démarrage unique de la JVM : La JVM est démarrée une seule fois pour toute la session de test
#        lorsque cette fixture est activée pour la première fois.
#     2. Utilisation du vrai JPype : Force l'utilisation du module `_REAL_JPYPE_MODULE` (le vrai JPype)
#        pendant toute la durée de son scope. Elle manipule `sys.modules` pour s'assurer que
#        `jpype`, `_jpype` et `jpype.imports` pointent vers les vrais modules, en sauvegardant
#        et restaurant les versions précédentes (potentiellement des mocks).
#     3. Gestion de `initialize_jvm` : Utilise la fonction `initialize_jvm` de
#        `argumentation_analysis.core.jvm_setup` pour démarrer la JVM avec le classpath approprié.
#     4. État de la JVM : Utilise la variable globale `_integration_jvm_started_session_scope` pour
#        suivre si la JVM a été démarrée par *cette* fixture au sein de la session.
#        `jpype.isJVMStarted()` (du vrai JPype) reflète l'état réel.
#     5. Arrêt de la JVM : La JVM est arrêtée à la fin de la session de test via `request.addfinalizer`.
#     6. Gestion de `jpype.config` pour `atexit` : Avant d'appeler `shutdownJVM`, cette fixture tente
#        de s'assurer que `jpype.config` est importé et accessible. Ceci vise à prévenir les
#        `ModuleNotFoundError: No module named 'jpype.config'` qui peuvent survenir si des handlers
#        `atexit` enregistrés par JPype tentent d'accéder à `jpype.config` après que le module
#        principal `jpype` ait été partiellement déchargé ou modifié.
#     7. Restauration de `sys.modules` : Après l'arrêt de la JVM (ou en cas d'échec), les modules
#        `jpype` originaux (qui pouvaient être des mocks) sont restaurés dans `sys.modules`.
#        Cependant, si la JVM est arrêtée avec succès par cette fixture, `sys.modules['jpype']`
#        est laissé comme `_REAL_JPYPE_MODULE` pour permettre aux handlers `atexit` du vrai JPype
#        de s'exécuter correctement.
#
#     Dépendances :
#     - `_REAL_JPYPE_MODULE`: Doit être le vrai module JPype, initialisé au début de `tests/conftest.py`.
#
#     Utilisation :
#     - Les tests d'intégration qui nécessitent une vraie JVM doivent dépendre de cette fixture
#       (directement ou indirectement, par exemple via `dung_classes`, `qbf_classes`, etc.).
#     - La fixture `activate_jpype_mock_if_needed` s'assurera que `sys.modules['jpype']` est
#       le vrai module JPype avant que `integration_jvm` ne s'exécute pour ces tests.
#     """
#     global _integration_jvm_started_session_scope, _REAL_JPYPE_MODULE
#
#     logger_conftest_integration.info("Fixture 'integration_jvm' (session scope) appelée.")
#
#     original_jpype_module = sys.modules.get('jpype')
#     original_dot_jpype_module = sys.modules.get('_jpype')
#
#     saved_jpype_modules = {}
#     for name in list(sys.modules.keys()):
#         if name == 'jpype' or name.startswith('jpype.') or name == '_jpype':
#             saved_jpype_modules[name] = sys.modules[name]
#             logger_conftest_integration.info(f"integration_jvm: Sauvegarde et suppression de sys.modules['{name}'] (actuel: {getattr(sys.modules[name], '__file__', 'N/A')})")
#             del sys.modules[name]
#
#     jpype_real = None
#     current_conftest_dir = os.path.dirname(os.path.abspath(__file__))
#     mocks_path = os.path.join(current_conftest_dir, 'mocks')
#     mocks_path_in_sys_path = False
#     original_sys_path = list(sys.path)
#
#     if mocks_path in sys.path:
#         mocks_path_in_sys_path = True
#         logger_conftest_integration.info(f"integration_jvm: Temporarily removing '{mocks_path}' from sys.path to import real jpype.")
#         sys.path = [p for p in sys.path if p != mocks_path]
#
#     try:
#         logger_conftest_integration.info("integration_jvm: Tentative d'import du vrai module 'jpype'.")
#         if _REAL_JPYPE_MODULE is None:
#             logger_conftest_integration.warning("integration_jvm: _REAL_JPYPE_MODULE est None, tentative d'import frais de jpype.")
#             spec = importlib.util.find_spec('jpype')
#             if spec:
#                 _REAL_JPYPE_MODULE = importlib.util.module_from_spec(spec)
#                 sys.modules['jpype'] = _REAL_JPYPE_MODULE
#                 spec.loader.exec_module(_REAL_JPYPE_MODULE)
#                 logger_conftest_integration.info(f"integration_jvm: JPype importé fraîchement dans la fixture: {getattr(_REAL_JPYPE_MODULE, '__file__', 'N/A')}")
#             else:
#                 raise ImportError("Impossible de trouver le spec pour jpype lors de l'import frais dans integration_jvm")
#
#         jpype_real = _REAL_JPYPE_MODULE
#         if not jpype_real:
#              raise ImportError("integration_jvm: _REAL_JPYPE_MODULE est None même après tentative d'import.")
#
#         sys.modules['jpype'] = jpype_real
#
#         if hasattr(jpype_real, '_core') and hasattr(jpype_real._core, '__file__'):
#              sys.modules['_jpype'] = jpype_real._core
#              logger_conftest_integration.info(f"integration_jvm: '_jpype' mis à jpype_real._core ({getattr(jpype_real._core, '__file__', 'N/A')}).")
#         elif hasattr(jpype_real, '_jpype') and hasattr(jpype_real._jpype, '__file__'):
#              sys.modules['_jpype'] = jpype_real._jpype
#              logger_conftest_integration.info(f"integration_jvm: '_jpype' mis à jpype_real._jpype ({getattr(jpype_real._jpype, '__file__', 'N/A')}).")
#         else:
#             if '_jpype' in sys.modules and original_dot_jpype_module and sys.modules['_jpype'] is original_dot_jpype_module:
#                  logger_conftest_integration.info("integration_jvm: Le module '_jpype' semble être le mock original, tentative de le supprimer pour recharger le vrai.")
#                  del sys.modules['_jpype']
#             logger_conftest_integration.warning("integration_jvm: Impossible de déterminer explicitement le module C (_jpype) à partir de jpype_real.")
#         logger_conftest_integration.info(f"integration_jvm: Vrai jpype (depuis _REAL_JPYPE_MODULE ou import frais) utilisé: {getattr(jpype_real, '__file__', 'N/A')}")
#     except ImportError as e:
#         logger_conftest_integration.error(f"integration_jvm: CRITICAL - Impossible d'utiliser/importer le vrai jpype: {e}")
#         logger_conftest_integration.info(f"integration_jvm: Restauration des modules sys.modules originaux après échec.")
#         for name, module_obj in saved_jpype_modules.items():
#             sys.modules[name] = module_obj
#         if original_jpype_module and 'jpype' not in sys.modules : sys.modules['jpype'] = original_jpype_module
#         if original_dot_jpype_module and '_jpype' not in sys.modules: sys.modules['_jpype'] = original_dot_jpype_module
#         pytest.skip(f"Impossible d'utiliser/importer le vrai jpype pour integration_jvm: {e}. Tests sautés.")
#     finally:
#         if sys.path[:] != original_sys_path:
#             sys.path[:] = original_sys_path
#             logger_conftest_integration.info(f"integration_jvm: sys.path restauré.")
#         if mocks_path_in_sys_path and mocks_path not in sys.path:
#             sys.path.insert(0, mocks_path)
#             logger_conftest_integration.info(f"integration_jvm: '{mocks_path}' ré-inséré dans sys.path.")
#
#     if jpype_real.isJVMStarted() and not _integration_jvm_started_session_scope:
#         logger_conftest_integration.error("integration_jvm: ERREUR - La JVM (vrai jpype) est déjà démarrée par un mécanisme externe.")
#         if original_jpype_module: sys.modules['jpype'] = original_jpype_module
#         elif 'jpype' in sys.modules and sys.modules['jpype'] is jpype_real: del sys.modules['jpype']
#         if original_dot_jpype_module: sys.modules['_jpype'] = original_dot_jpype_module
#         elif '_jpype' in sys.modules and ((hasattr(jpype_real, '_core') and sys.modules['_jpype'] is jpype_real._core) or \
#                                            (hasattr(jpype_real, '_jpype') and sys.modules['_jpype'] is jpype_real._jpype)):
#             del sys.modules['_jpype']
#         pytest.skip("JVM (vrai jpype) démarrée prématurément. Tests sautés.")
#
#     if _integration_jvm_started_session_scope and jpype_real.isJVMStarted():
#         logger_conftest_integration.info("integration_jvm: La JVM (vrai jpype) a déjà été initialisée par cette fixture.")
#         yield jpype_real
#         return
#
#     logger_conftest_integration.info("integration_jvm: Tentative d'initialisation de la JVM avec le vrai jpype...")
#     if initialize_jvm is None or LIBS_DIR is None or TWEETY_VERSION is None:
#         logger_conftest_integration.critical("integration_jvm: Dépendances (initialize_jvm, LIBS_DIR, TWEETY_VERSION) non disponibles.")
#         pytest.skip("Dépendances manquantes pour démarrer la JVM. Tests sautés.")
#
#     success = initialize_jvm(lib_dir_path=str(LIBS_DIR), tweety_version=TWEETY_VERSION)
#
#     if not success or not jpype_real.isJVMStarted():
#         logger_conftest_integration.error("integration_jvm: Échec critique de l'initialisation de la JVM avec le vrai jpype.")
#         _integration_jvm_started_session_scope = False
#         if original_jpype_module: sys.modules['jpype'] = original_jpype_module
#         elif 'jpype' in sys.modules and sys.modules['jpype'] is jpype_real: del sys.modules['jpype']
#         if original_dot_jpype_module: sys.modules['_jpype'] = original_dot_jpype_module
#         elif '_jpype' in sys.modules and ((hasattr(jpype_real, '_core') and sys.modules['_jpype'] is jpype_real._core) or \
#                                            (hasattr(jpype_real, '_jpype') and sys.modules['_jpype'] is jpype_real._jpype)):
#             del sys.modules['_jpype']
#         pytest.skip("Échec de démarrage de la JVM (vrai jpype). Tests sautés.")
#     else:
#         logger_conftest_integration.info("integration_jvm: JVM initialisée avec succès par la fixture avec le vrai jpype.")
#         _integration_jvm_started_session_scope = True
#
#     def fin_integration_jvm():
#         global _integration_jvm_started_session_scope
#         logger_conftest_integration.info("integration_jvm: Finalisation (arrêt JVM si démarrée par elle).")
#         if _integration_jvm_started_session_scope and jpype_real and jpype_real.isJVMStarted():
#             try:
#                 # S'assurer que jpype.config est accessible avant shutdownJVM pour éviter ModuleNotFoundError dans atexit.
#                 # Cette logique est inspirée de la première fixture integration_jvm (maintenant inactive).
#                 if jpype_real and sys.modules.get('jpype') is jpype_real: # Assure que jpype_real est le module jpype actuel
#                     logger_conftest_integration.info("integration_jvm (fin): Vérification/Import de jpype.config avant shutdown...")
#                     try:
#                         # Tenter d'accéder ou d'importer jpype.config pour s'assurer qu'il est chargé
#                         if not hasattr(jpype_real, 'config'):
#                              logger_conftest_integration.info("   jpype.config non trouvé comme attribut sur jpype_real, tentative d'import explicite via jpype_real.")
#                              # Essayer d'importer via l'objet jpype_real si possible, ou globalement
#                              if hasattr(jpype_real, '__name__') and jpype_real.__name__ == 'jpype':
#                                  import jpype.config # Importe le config du module jpype actuellement dans sys.modules
#                                  logger_conftest_integration.info("   Import explicite de jpype.config (via import global) réussi.")
#                              else: # Fallback si jpype_real n'est pas le 'jpype' global
#                                  # Ceci est moins probable si on a bien restauré sys.modules['jpype'] = jpype_real
#                                  temp_jpype_config = importlib.import_module(f"{jpype_real.__name__}.config")
#                                  setattr(jpype_real, 'config', temp_jpype_config)
#                                  logger_conftest_integration.info(f"   Import explicite de {jpype_real.__name__}.config réussi et attaché.")
#
#                         elif jpype_real.config is None : # Cas où l'attribut existe mais est None
#                              logger_conftest_integration.info("   jpype_real.config est None, tentative d'import explicite.")
#                              if hasattr(jpype_real, '__name__') and jpype_real.__name__ == 'jpype':
#                                  import jpype.config
#                                  logger_conftest_integration.info("   Import explicite de jpype.config (après None, via import global) réussi.")
#                              else:
#                                  temp_jpype_config = importlib.import_module(f"{jpype_real.__name__}.config")
#                                  setattr(jpype_real, 'config', temp_jpype_config)
#                                  logger_conftest_integration.info(f"   Import explicite de {jpype_real.__name__}.config (après None) réussi et attaché.")
#                         else:
#                              logger_conftest_integration.info(f"   jpype_real.config déjà présent (type: {type(jpype_real.config)}).")
#                     except ModuleNotFoundError:
#                         logger_conftest_integration.error("   ModuleNotFoundError pour jpype.config lors de la vérification/import avant shutdown.")
#                     except ImportError:
#                         logger_conftest_integration.error("   ImportError pour jpype.config lors de la vérification/import avant shutdown.")
#                     except Exception as e_cfg_imp:
#                         logger_conftest_integration.error(f"   Erreur lors de la vérification/import de jpype.config: {type(e_cfg_imp).__name__}: {e_cfg_imp}")
#                 else:
#                     logger_conftest_integration.warning("integration_jvm (fin): jpype_real n'est pas le module 'jpype' actuel dans sys.modules, ou jpype_real est None. Skip vérification jpype.config.")
#
#                 logger_conftest_integration.info("integration_jvm: Tentative d'arrêt de la JVM avec le vrai jpype...")
#                 jpype_real.shutdownJVM()
#                 logger_conftest_integration.info("integration_jvm: JVM (vrai jpype) arrêtée.")
#             except Exception as e_shutdown:
#                 logger_conftest_integration.error(f"integration_jvm: Erreur arrêt JVM (vrai jpype): {e_shutdown}", exc_info=True)
#             finally: _integration_jvm_started_session_scope = False
#         elif jpype_real and not jpype_real.isJVMStarted():
#             logger_conftest_integration.info("integration_jvm: JVM (vrai jpype) non démarrée à la finalisation.")
#             _integration_jvm_started_session_scope = False
#         else:
#             logger_conftest_integration.info("integration_jvm: JVM (vrai jpype) non démarrée par cette fixture ou jpype_real est None.")
#             _integration_jvm_started_session_scope = False
#
#         logger_conftest_integration.info("integration_jvm (fin): Restauration des modules sys.modules originaux.")
#         if jpype_real:
#             if 'jpype' in sys.modules and sys.modules['jpype'] is jpype_real: del sys.modules['jpype']
#             real_jpype_c_module = getattr(jpype_real, '_core', getattr(jpype_real, '_jpype', None))
#             if real_jpype_c_module and '_jpype' in sys.modules and sys.modules['_jpype'] is real_jpype_c_module:
#                 del sys.modules['_jpype']
#         for name, module_obj in saved_jpype_modules.items(): sys.modules[name] = module_obj
#         if 'jpype' not in sys.modules and original_jpype_module: sys.modules['jpype'] = original_jpype_module
#         if '_jpype' not in sys.modules and original_dot_jpype_module: sys.modules['_jpype'] = original_dot_jpype_module
#     request.addfinalizer(fin_integration_jvm)
#     yield jpype_real
#
@pytest.fixture(scope="module")
def dung_classes(integration_jvm): 
    jpype_instance = integration_jvm 
    if not jpype_instance or not jpype_instance.isJVMStarted(): pytest.skip("JVM non démarrée ou jpype_instance None (dung_classes).")
    try:
        TgfParser_class = None
        try: TgfParser_class = jpype_instance.JClass("org.tweetyproject.arg.dung.io.TgfParser")
        except jpype_instance.JException: 
            logger_conftest_integration.info("dung_classes: TgfParser non trouvé dans .io, essai avec .parser")
            try: TgfParser_class = jpype_instance.JClass("org.tweetyproject.arg.dung.parser.TgfParser")
            except jpype_instance.JException as e_parser: logger_conftest_integration.warning(f"dung_classes: TgfParser non trouvé: {e_parser}")
        classes_to_return = {
            "DungTheory": jpype_instance.JClass("org.tweetyproject.arg.dung.syntax.DungTheory"),
            "Argument": jpype_instance.JClass("org.tweetyproject.arg.dung.syntax.Argument"),
            "Attack": jpype_instance.JClass("org.tweetyproject.arg.dung.syntax.Attack"),
            "PreferredReasoner": jpype_instance.JClass("org.tweetyproject.arg.dung.reasoner.PreferredReasoner"),
            "GroundedReasoner": jpype_instance.JClass("org.tweetyproject.arg.dung.reasoner.GroundedReasoner"),
            "CompleteReasoner": jpype_instance.JClass("org.tweetyproject.arg.dung.reasoner.CompleteReasoner"),
            "StableReasoner": jpype_instance.JClass("org.tweetyproject.arg.dung.reasoner.StableReasoner"),
        }
        if TgfParser_class: classes_to_return["TgfParser"] = TgfParser_class
        return classes_to_return
    except jpype_instance.JException as e: pytest.fail(f"Echec import classes Dung: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
    except Exception as e_py: pytest.fail(f"Erreur Python (dung_classes): {str(e_py)}")

@pytest.fixture(scope="module")
def qbf_classes(integration_jvm):
    jpype_instance = integration_jvm
    if not jpype_instance or not jpype_instance.isJVMStarted(): pytest.skip("JVM non démarrée ou jpype_instance None (qbf_classes).")
    try:
        return {
            "QuantifiedBooleanFormula": jpype_instance.JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula"),
            "Quantifier": jpype_instance.JClass("org.tweetyproject.logics.qbf.syntax.Quantifier"),
            "QbfParser": jpype_instance.JClass("org.tweetyproject.logics.qbf.parser.QbfParser"),
            "Variable": jpype_instance.JClass("org.tweetyproject.logics.commons.syntax.Variable"),
        }
    except jpype_instance.JException as e: pytest.fail(f"Echec import classes QBF: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
    except Exception as e_py: pytest.fail(f"Erreur Python (qbf_classes): {str(e_py)}")

@pytest.fixture(scope="module")
def belief_revision_classes(integration_jvm):
    logger.info("tests/conftest.py: Début de la fixture 'belief_revision_classes'.")
    jpype_instance = integration_jvm
    
    if jpype_instance is None:
        logger.error("tests/conftest.py: belief_revision_classes - jpype_instance (résultat de integration_jvm) est None!")
        pytest.skip("belief_revision_classes: jpype_instance (integration_jvm) est None.")
        return

    logger.info(f"tests/conftest.py: belief_revision_classes - jpype_instance (ID: {id(jpype_instance)}) obtenu. Vérification de isJVMStarted()...")
    
    # Tentative de s'assurer que l'on utilise le bon objet jpype pour la vérification
    # Cela peut être redondant si integration_jvm garantit déjà que sys.modules['jpype'] est correct.
    # Mais ajoutons un log pour voir quel jpype est dans sys.modules ici.
    current_sys_jpype = sys.modules.get('jpype')
    logger.info(f"tests/conftest.py: belief_revision_classes - sys.modules['jpype'] (ID: {id(current_sys_jpype)}) au moment de la vérification.")
    logger.info(f"tests/conftest.py: belief_revision_classes - _REAL_JPYPE_MODULE (ID: {id(_REAL_JPYPE_MODULE)})")

    # Utiliser jpype_instance qui est le résultat de integration_jvm
    jvm_is_started_check = jpype_instance.isJVMStarted()
    logger.info(f"tests/conftest.py: belief_revision_classes - jpype_instance.isJVMStarted() a retourné: {jvm_is_started_check}")

    if not jvm_is_started_check:
        logger.warning("tests/conftest.py: belief_revision_classes - Appel de pytest.skip car jpype_instance.isJVMStarted() est False.")
        pytest.skip("JVM non démarrée ou jpype_instance None (belief_revision_classes).")
    
    logger.info("tests/conftest.py: belief_revision_classes - JVM démarrée, tentative de chargement des classes.")
    try:
        # Essayer d'obtenir et d'utiliser le ContextClassLoader
        loader_to_use = None
        try:
            JavaThread = jpype_instance.JClass("java.lang.Thread")
            current_thread = JavaThread.currentThread()
            loader_to_use = current_thread.getContextClassLoader()
            if loader_to_use is None: # Fallback si getContextClassLoader retourne null
                 loader_to_use = jpype_instance.JClass("java.lang.ClassLoader").getSystemClassLoader()
            logger.info(f"tests/conftest.py: belief_revision_classes - Utilisation du ClassLoader: {loader_to_use}")
        except Exception as e_loader:
            logger.warning(f"tests/conftest.py: belief_revision_classes - Erreur lors de l'obtention du ClassLoader: {e_loader}. JClass utilisera le loader par défaut.")
            loader_to_use = None # Assurer que c'est None pour que JClass utilise son défaut

        pl_classes = {
            "PlFormula": jpype_instance.JClass("org.tweetyproject.logics.pl.syntax.PlFormula", loader=loader_to_use),
            "PlBeliefSet": jpype_instance.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet", loader=loader_to_use),
            "PlParser": jpype_instance.JClass("org.tweetyproject.logics.pl.parser.PlParser", loader=loader_to_use),
            "SimplePlReasoner": jpype_instance.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner", loader=loader_to_use),
            "Negation": jpype_instance.JClass("org.tweetyproject.logics.pl.syntax.Negation", loader=loader_to_use),
            "PlSignature": jpype_instance.JClass("org.tweetyproject.logics.pl.syntax.PlSignature", loader=loader_to_use),
        }
        revision_ops = {
            "KernelContractionOperator": jpype_instance.JClass("org.tweetyproject.beliefdynamics.kernels.KernelContractionOperator", loader=loader_to_use),
            "RandomIncisionFunction": jpype_instance.JClass("org.tweetyproject.beliefdynamics.kernels.RandomIncisionFunction", loader=loader_to_use),
            "DefaultMultipleBaseExpansionOperator": jpype_instance.JClass("org.tweetyproject.beliefdynamics.DefaultMultipleBaseExpansionOperator", loader=loader_to_use),
            "LeviMultipleBaseRevisionOperator": jpype_instance.JClass("org.tweetyproject.beliefdynamics.LeviMultipleBaseRevisionOperator", loader=loader_to_use),
        }
        crmas_classes = {
            "CrMasBeliefSet": jpype_instance.JClass("org.tweetyproject.beliefdynamics.mas.CrMasBeliefSet", loader=loader_to_use),
            "InformationObject": jpype_instance.JClass("org.tweetyproject.beliefdynamics.mas.InformationObject", loader=loader_to_use),
            "CrMasRevisionWrapper": jpype_instance.JClass("org.tweetyproject.beliefdynamics.mas.CrMasRevisionWrapper", loader=loader_to_use),
            "CrMasSimpleRevisionOperator": jpype_instance.JClass("org.tweetyproject.beliefdynamics.operators.CrMasSimpleRevisionOperator", loader=loader_to_use),
            "CrMasArgumentativeRevisionOperator": jpype_instance.JClass("org.tweetyproject.beliefdynamics.operators.CrMasArgumentativeRevisionOperator", loader=loader_to_use),
            "DummyAgent": jpype_instance.JClass("org.tweetyproject.agents.DummyAgent", loader=loader_to_use),
            "Order": jpype_instance.JClass("org.tweetyproject.comparator.Order", loader=loader_to_use),
        }
        inconsistency_measures = {
            "ContensionInconsistencyMeasure": jpype_instance.JClass("org.tweetyproject.logics.pl.analysis.ContensionInconsistencyMeasure", loader=loader_to_use),
            "NaiveMusEnumerator": jpype_instance.JClass("org.tweetyproject.logics.commons.analysis.NaiveMusEnumerator", loader=loader_to_use),
            "SatSolver": jpype_instance.JClass("org.tweetyproject.logics.pl.sat.SatSolver", loader=loader_to_use),
        }
        return {**pl_classes, **revision_ops, **crmas_classes, **inconsistency_measures}
    except jpype_instance.JException as e: pytest.fail(f"Echec import classes Belief Revision: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
    except Exception as e_py: pytest.fail(f"Erreur Python (belief_revision_classes): {str(e_py)}")

@pytest.fixture(scope="module")
def dialogue_classes(integration_jvm):
    jpype_instance = integration_jvm
    if not jpype_instance or not jpype_instance.isJVMStarted(): pytest.skip("JVM non démarrée ou jpype_instance None (dialogue_classes).")
    try:
        return {
            "ArgumentationAgent": jpype_instance.JClass("org.tweetyproject.agents.dialogues.ArgumentationAgent"),
            "GroundedAgent": jpype_instance.JClass("org.tweetyproject.agents.dialogues.GroundedAgent"),
            "OpponentModel": jpype_instance.JClass("org.tweetyproject.agents.dialogues.OpponentModel"),
            "Dialogue": jpype_instance.JClass("org.tweetyproject.agents.dialogues.Dialogue"),
            "DialogueTrace": jpype_instance.JClass("org.tweetyproject.agents.dialogues.DialogueTrace"),
            "DialogueResult": jpype_instance.JClass("org.tweetyproject.agents.dialogues.DialogueResult"),
            "PersuasionProtocol": jpype_instance.JClass("org.tweetyproject.agents.dialogues.PersuasionProtocol"),
            "Position": jpype_instance.JClass("org.tweetyproject.agents.dialogues.Position"),
            "SimpleBeliefSet": jpype_instance.JClass("org.tweetyproject.logics.commons.syntax.SimpleBeliefSet"), 
            "DefaultStrategy": jpype_instance.JClass("org.tweetyproject.agents.dialogues.strategies.DefaultStrategy"),
        }
    except jpype_instance.JException as e: pytest.fail(f"Echec import classes Dialogue: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
    except Exception as e_py: pytest.fail(f"Erreur Python (dialogue_classes): {str(e_py)}")

# --- Pytest Session Hooks pour la gestion globale de JPype ---

def pytest_sessionstart(session):
    """
    Appelé après la collecte des tests et avant l'exécution.
    Configure jpype.config.destroy_jvm = False si le vrai JPype est utilisé.
    """
    global _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL, logger # logger est défini en haut du fichier
    
    logger.info("tests/conftest.py: pytest_sessionstart hook triggered.")
    
    # S'assurer que logger est bien le logger de ce conftest
    if not hasattr(logger, 'info'): # Simple check
        # Récupérer le logger défini au début du fichier si besoin
        import logging
        logger = logging.getLogger(__name__) # Ou le nom spécifique utilisé au début

    if _REAL_JPYPE_MODULE and _REAL_JPYPE_MODULE is not _JPYPE_MODULE_MOCK_OBJ_GLOBAL:
        logger.info("   pytest_sessionstart: Real JPype module is available.")
        try:
            # Sauvegarder l'état actuel de sys.modules['jpype'] pour le restaurer si on le modifie temporairement
            original_sys_jpype_module = sys.modules.get('jpype')
            
            # S'assurer que sys.modules['jpype'] est _REAL_JPYPE_MODULE pour l'import de config
            if sys.modules.get('jpype') is not _REAL_JPYPE_MODULE:
                sys.modules['jpype'] = _REAL_JPYPE_MODULE
                logger.info("   pytest_sessionstart: Temporarily set sys.modules['jpype'] to _REAL_JPYPE_MODULE for config import.")

            # Tenter d'importer jpype.config. Cela devrait le mettre dans sys.modules['jpype.config']
            # et potentiellement l'attacher à _REAL_JPYPE_MODULE.config
            if not hasattr(_REAL_JPYPE_MODULE, 'config') or _REAL_JPYPE_MODULE.config is None:
                logger.info("   pytest_sessionstart: Attempting to import jpype.config explicitly.")
                import jpype.config # Cet import utilise sys.modules['jpype']
            
            # Restaurer sys.modules['jpype'] s'il a été modifié et n'était pas None
            if original_sys_jpype_module is not None and sys.modules.get('jpype') is not original_sys_jpype_module:
                sys.modules['jpype'] = original_sys_jpype_module
                logger.info("   pytest_sessionstart: Restored original sys.modules['jpype'].")
            elif original_sys_jpype_module is None and 'jpype' in sys.modules and sys.modules['jpype'] is _REAL_JPYPE_MODULE:
                # Si on l'a mis et qu'il n'y avait rien avant, on le laisse pour l'instant,
                # car _REAL_JPYPE_MODULE est ce que nous voulons utiliser.
                pass


            if hasattr(_REAL_JPYPE_MODULE, 'config') and _REAL_JPYPE_MODULE.config is not None:
                _REAL_JPYPE_MODULE.config.destroy_jvm = False
                logger.info(f"   pytest_sessionstart: _REAL_JPYPE_MODULE.config.destroy_jvm set to False. Current value: {_REAL_JPYPE_MODULE.config.destroy_jvm}")
                
                # S'assurer que le module config est bien dans sys.modules
                if 'jpype.config' not in sys.modules or sys.modules.get('jpype.config') is not _REAL_JPYPE_MODULE.config:
                    sys.modules['jpype.config'] = _REAL_JPYPE_MODULE.config
                    logger.info("   pytest_sessionstart: Ensured _REAL_JPYPE_MODULE.config is in sys.modules['jpype.config'].")
            else:
                logger.warning("   pytest_sessionstart: _REAL_JPYPE_MODULE does not have 'config' attribute or it's None after import attempt. Cannot set destroy_jvm.")
        
        except ImportError as e_cfg_imp:
            logger.error(f"   pytest_sessionstart: ImportError when trying to import or use jpype.config: {e_cfg_imp}")
        except Exception as e:
            logger.error(f"   pytest_sessionstart: Unexpected error when handling jpype.config: {type(e).__name__}: {e}", exc_info=True)
    
    elif _JPYPE_MODULE_MOCK_OBJ_GLOBAL and _REAL_JPYPE_MODULE is _JPYPE_MODULE_MOCK_OBJ_GLOBAL:
        logger.info("   pytest_sessionstart: JPype module is the MOCK. No changes to destroy_jvm needed for the mock.")
    else:
        logger.info("   pytest_sessionstart: Real JPype module not definitively available or identified as mock. Cannot set destroy_jvm.")

def pytest_sessionfinish(session, exitstatus):
    """
    Appelé après l'exécution de tous les tests.
    S'assure que jpype et jpype.config sont correctement dans sys.modules si la JVM n'a pas été détruite,
    pour aider les handlers atexit de JPype.
    """
    global _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL, logger
    logger.info(f"tests/conftest.py: pytest_sessionfinish hook triggered. Exit status: {exitstatus}")

    if _REAL_JPYPE_MODULE and _REAL_JPYPE_MODULE is not _JPYPE_MODULE_MOCK_OBJ_GLOBAL:
        logger.info("   pytest_sessionfinish: Real JPype module is available.")
        try:
            # Vérifier si la JVM est démarrée et si destroy_jvm est False
            jvm_started = hasattr(_REAL_JPYPE_MODULE, 'isJVMStarted') and _REAL_JPYPE_MODULE.isJVMStarted()
            destroy_jvm_is_false = False
            if hasattr(_REAL_JPYPE_MODULE, 'config') and _REAL_JPYPE_MODULE.config is not None and hasattr(_REAL_JPYPE_MODULE.config, 'destroy_jvm'):
                destroy_jvm_is_false = not _REAL_JPYPE_MODULE.config.destroy_jvm
            
            logger.info(f"   pytest_sessionfinish: JVM started: {jvm_started}, destroy_jvm is False: {destroy_jvm_is_false}")

            if jvm_started and destroy_jvm_is_false:
                logger.info("   pytest_sessionfinish: JVM is active and not set to be destroyed. Ensuring jpype modules are correctly in sys.modules for atexit.")
                
                current_sys_jpype = sys.modules.get('jpype')
                if current_sys_jpype is not _REAL_JPYPE_MODULE:
                    logger.warning(f"   pytest_sessionfinish: sys.modules['jpype'] (ID: {id(current_sys_jpype)}) is not _REAL_JPYPE_MODULE (ID: {id(_REAL_JPYPE_MODULE)}). Restoring _REAL_JPYPE_MODULE.")
                    sys.modules['jpype'] = _REAL_JPYPE_MODULE
                else:
                    logger.info("   pytest_sessionfinish: sys.modules['jpype'] is already _REAL_JPYPE_MODULE.")

                if hasattr(_REAL_JPYPE_MODULE, 'config') and _REAL_JPYPE_MODULE.config is not None:
                    current_sys_jpype_config = sys.modules.get('jpype.config')
                    if current_sys_jpype_config is not _REAL_JPYPE_MODULE.config:
                        logger.warning(f"   pytest_sessionfinish: sys.modules['jpype.config'] (ID: {id(current_sys_jpype_config)}) is not _REAL_JPYPE_MODULE.config (ID: {id(_REAL_JPYPE_MODULE.config)}). Restoring.")
                        sys.modules['jpype.config'] = _REAL_JPYPE_MODULE.config
                    else:
                        logger.info("   pytest_sessionfinish: sys.modules['jpype.config'] is already _REAL_JPYPE_MODULE.config.")
                else:
                    logger.warning("   pytest_sessionfinish: _REAL_JPYPE_MODULE.config not available, cannot ensure sys.modules['jpype.config'].")
            else:
                logger.info("   pytest_sessionfinish: JVM not started or destroy_jvm is True. No special sys.modules handling for atexit needed from here.")
        
        except AttributeError as ae:
             logger.error(f"   pytest_sessionfinish: AttributeError encountered: {ae}. This might happen if JPype was not fully initialized or is mocked.", exc_info=True)
        except Exception as e:
            logger.error(f"   pytest_sessionfinish: Unexpected error: {type(e).__name__}: {e}", exc_info=True)
    else:
        logger.info("   pytest_sessionfinish: Real JPype module not available or is mock. No action.")

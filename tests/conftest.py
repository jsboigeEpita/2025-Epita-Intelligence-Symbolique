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
import logging

# --- Configuration du Logger (déplacé avant la sauvegarde JPype pour l'utiliser) ---
logger = logging.getLogger(__name__)

# --- Sauvegarde du module JPype potentiellement pré-importé ou import frais ---
_REAL_JPYPE_MODULE = None
_PRE_EXISTING_JPYPE_IN_SYS_MODULES = sys.modules.get('jpype')

if _PRE_EXISTING_JPYPE_IN_SYS_MODULES:
    # Si jpype est déjà dans sys.modules (probablement par le conftest racine), on l'utilise.
    # On suppose qu'il est fonctionnel ou que les erreurs se manifesteront de toute façon.
    _REAL_JPYPE_MODULE = _PRE_EXISTING_JPYPE_IN_SYS_MODULES
    logger.info(f"Utilisation du module JPype préchargé dans sys.modules (ID: {id(_REAL_JPYPE_MODULE)}).")
else:
    # Si jpype n'était pas dans sys.modules, on tente un import standard.
    try:
        import jpype as r_jpype_fresh_import
        _REAL_JPYPE_MODULE = r_jpype_fresh_import
        logger.info(f"Vrai module JPype importé fraîchement (ID: {id(_REAL_JPYPE_MODULE)}).")
        # Laisser ce jpype importé dans sys.modules pour l'instant.
        # La fixture activate_jpype_mock_if_needed le remplacera par le mock si nécessaire pour les tests unitaires.
    except ImportError as e_fresh_import:
        logger.warning(f"Le vrai module JPype n'a pas pu être importé fraîchement: {e_fresh_import}")
    except NameError as e_name_error_fresh_import: # Capturer le NameError potentiel ici aussi
        logger.error(f"NameError lors de l'import frais de JPype: {e_name_error_fresh_import}. Cela indique un problème d'installation/configuration de JPype.")


# Nécessaire pour la fixture integration_jvm
_integration_jvm_started_session_scope = False
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    # Importer LIBS_DIR depuis argumentation_analysis.paths
    # Importer TWEETY_VERSION depuis argumentation_analysis.core.jvm_setup (où il est défini)
    from argumentation_analysis.paths import LIBS_DIR
    from argumentation_analysis.core.jvm_setup import TWEETY_VERSION as CORE_TWEETY_VERSION # Renommer pour éviter conflit si TWEETY_VERSION est déjà une globale
    TWEETY_VERSION = CORE_TWEETY_VERSION # Assigner à la variable globale attendue par la fixture
except ImportError as e_jvm_related_import:
    import traceback
    print(f"AVERTISSEMENT: tests/conftest.py: Échec de l'import pour jvm_setup, paths ou settings.")
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
try:
    from matplotlib_mock import pyplot as mock_pyplot_instance
    from matplotlib_mock import cm as mock_cm_instance
    from matplotlib_mock import MatplotlibMock as MockMatplotlibModule_class
    
    sys.modules['matplotlib.pyplot'] = mock_pyplot_instance
    sys.modules['matplotlib.cm'] = mock_cm_instance
    mock_mpl_module = MockMatplotlibModule_class()
    mock_mpl_module.pyplot = mock_pyplot_instance
    mock_mpl_module.cm = mock_cm_instance
    sys.modules['matplotlib'] = mock_mpl_module
    print("INFO: Matplotlib mocké globalement.")

    from networkx_mock import NetworkXMock as MockNetworkXModule_class
    sys.modules['networkx'] = MockNetworkXModule_class()
    print("INFO: NetworkX mocké globalement.")

except ImportError as e:
    print(f"ERREUR CRITIQUE lors du mocking global de matplotlib ou networkx: {e}")
    if 'matplotlib' not in str(e).lower():
        sys.modules['matplotlib.pyplot'] = MagicMock()
        sys.modules['matplotlib.cm'] = MagicMock()
        sys.modules['matplotlib'] = MagicMock()
        sys.modules['matplotlib'].pyplot = sys.modules['matplotlib.pyplot']
        sys.modules['matplotlib'].cm = sys.modules['matplotlib.cm']
    if 'networkx' not in str(e).lower():
        sys.modules['networkx'] = MagicMock()

# --- Mock NumPy Immédiat ---
def _install_numpy_mock_immediately():
    if 'numpy' not in sys.modules:
        try:
            from numpy_mock import array, ndarray, mean, sum, zeros, ones, dot, concatenate, vstack, hstack, argmax, argmin, max, min, random, rec, _core, core
            sys.modules['numpy'] = type('numpy', (), {
                'array': array, 'ndarray': ndarray, 'mean': mean, 'sum': sum, 'zeros': zeros, 'ones': ones,
                'dot': dot, 'concatenate': concatenate, 'vstack': vstack, 'hstack': hstack,
                'argmax': argmax, 'argmin': argmin, 'max': max, 'min': min, 'random': random, 'rec': rec,
                '_core': _core, 'core': core, '__version__': '1.24.3',
            })
            sys.modules['numpy._core'] = _core
            sys.modules['numpy.core'] = core
            sys.modules['numpy._core.multiarray'] = _core.multiarray
            sys.modules['numpy.core.multiarray'] = core.multiarray
            if 'rec' in sys.modules['numpy'].__dict__: # Assurer que rec est bien un attribut
                sys.modules['numpy.rec'] = sys.modules['numpy'].rec
            print("INFO: Mock NumPy installé immédiatement dans conftest.py")
        except ImportError as e:
            print(f"ERREUR lors de l'installation immédiate du mock NumPy: {e}")

if (sys.version_info.major == 3 and sys.version_info.minor >= 12):
    _install_numpy_mock_immediately()

# --- Mock Pandas Immédiat ---
def _install_pandas_mock_immediately():
    if 'pandas' not in sys.modules:
        try:
            from pandas_mock import DataFrame, read_csv, read_json
            sys.modules['pandas'] = type('pandas', (), {
                'DataFrame': DataFrame, 'read_csv': read_csv, 'read_json': read_json, 'Series': list,
                'NA': None, 'NaT': None, 'isna': lambda x: x is None, 'notna': lambda x: x is not None,
                '__version__': '1.5.3',
            })
            sys.modules['pandas.core'] = type('pandas.core', (), {})
            sys.modules['pandas.core.api'] = type('pandas.core.api', (), {})
            sys.modules['pandas._libs'] = type('pandas._libs', (), {})
            sys.modules['pandas._libs.pandas_datetime'] = type('pandas._libs.pandas_datetime', (), {})
            print("INFO: Mock Pandas installé immédiatement dans conftest.py")
        except ImportError as e:
            print(f"ERREUR lors de l'installation immédiate du mock Pandas: {e}")

# Installation immédiate si Python 3.12+ ou si pandas n'est pas disponible (de HEAD)
if (sys.version_info.major == 3 and sys.version_info.minor >= 12):
    _install_pandas_mock_immediately()

# --- Mock JPype ---
try:
    from jpype_mock import (
        isJVMStarted, startJVM, getJVMPath, getJVMVersion, getDefaultJVMPath,
        JClass, JException, JObject, JVMNotFoundException, _jpype as mock_dot_jpype_module
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
    # Le mock est préparé ici, mais son installation dans sys.modules sera gérée par une fixture
    # ou conditionnellement plus tard. Pour l'instant, on le garde en variable.
    # sys.modules['jpype'] = jpype_module_mock_obj
    # sys.modules['_jpype'] = mock_dot_jpype_module
    # print("INFO: JPype (et jpype.imports) mocké globalement.") -> différé
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = jpype_module_mock_obj
    _MOCK_DOT_JPYPE_MODULE_GLOBAL = mock_dot_jpype_module
    print("INFO: Mock JPype préparé (sera installé conditionnellement).")
except ImportError as e_jpype:
    print(f"ERREUR CRITIQUE lors de l'import de jpype_mock: {e_jpype}. Utilisation de mocks de fallback pour JPype.")
    _fb_jpype_mock = MagicMock(name="jpype_fallback_mock")
    _fb_jpype_mock.imports = MagicMock(name="jpype.imports_fallback_mock")
    _fb_dot_jpype_mock = MagicMock(name="_jpype_fallback_mock")
    
    # Définir les globales avec les fallbacks
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = _fb_jpype_mock
    _MOCK_DOT_JPYPE_MODULE_GLOBAL = _fb_dot_jpype_mock
    
    # Optionnellement, mettre aussi ces fallbacks dans sys.modules pour une cohérence minimale
    # si quelque chose essaie d'importer jpype avant que la fixture ne s'exécute.
    # Cependant, la fixture activate_jpype_mock_if_needed devrait gérer cela.
    # Pour l'instant, on se contente de définir les globales.
    # sys.modules['jpype'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL
    # sys.modules['_jpype'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
    # sys.modules['jpype.imports'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports
    print("INFO: Mock JPype de FALLBACK préparé et assigné aux variables globales de mock.")

# --- Mock ExtractDefinitions ---
try:
    from extract_definitions_mock import setup_extract_definitions_mock
    setup_extract_definitions_mock()
    print("INFO: ExtractDefinitions mocké globalement.")
except ImportError as e_extract:
    print(f"ERREUR lors du mocking d'ExtractDefinitions: {e_extract}")
except Exception as e_extract_setup:
    print(f"ERREUR lors de la configuration du mock ExtractDefinitions: {e_extract_setup}")

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def is_module_available(module_name):
    if module_name in sys.modules:
        if isinstance(sys.modules[module_name], MagicMock) or \
           (module_name == 'jpype' and 'jpype_module_mock_obj' in globals() and sys.modules[module_name] is jpype_module_mock_obj):
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
        from numpy_mock import array, ndarray, mean, sum, zeros, ones, dot, concatenate, vstack, hstack, argmax, argmin, max, min, random, rec, _core, core, bool_, number, object_, float64, float32, int64, int32, int_, uint, uint64, uint32
        sys.modules['numpy'] = type('numpy', (), {
            'array': array, 'ndarray': ndarray, 'mean': mean, 'sum': sum, 'zeros': zeros, 'ones': ones,
            'dot': dot, 'concatenate': concatenate, 'vstack': vstack, 'hstack': hstack,
            'argmax': argmax, 'argmin': argmin, 'max': max, 'min': min, 'random': random, 'rec': rec,
            '_core': _core, 'core': core, '__version__': '1.24.3',
            'bool_': bool_, 'number': number, 'object_': object_,
            'float64': float64, 'float32': float32, 'int64': int64, 'int32': int32, 'int_': int_,
            'uint': uint, 'uint64': uint64, 'uint32': uint32,
        })
        sys.modules['numpy._core'] = _core
        sys.modules['numpy.core'] = core
        sys.modules['numpy._core.multiarray'] = _core.multiarray
        sys.modules['numpy.core.multiarray'] = core.multiarray
        # Enregistrer explicitement numpy.rec
        if hasattr(sys.modules['numpy'], 'rec'):
            sys.modules['numpy.rec'] = sys.modules['numpy'].rec
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

            # Créer et installer le mock principal de pandas
            _pandas_module_instance = PandasMock()
            sys.modules['pandas'] = _pandas_module_instance
            
            # Assurer que get_option et set_option sont accessibles directement sur le module mocké
            setattr(sys.modules['pandas'], 'get_option', get_option)
            setattr(sys.modules['pandas'], 'set_option', set_option)

            # Créer et installer les mocks pour les sous-modules io
            _pandas_io_instance = MockPandasIO()
            sys.modules['pandas.io'] = _pandas_io_instance
            sys.modules['pandas.io.formats'] = _pandas_io_instance.formats
            sys.modules['pandas.io.formats.console'] = _pandas_io_instance.formats.console
            
            print("INFO: Mock Pandas complet (avec io.formats.console) installé depuis conftest.py")

        except ImportError as e:
            print(f"ERREUR CRITIQUE lors de l'importation des composants de pandas_mock dans conftest.py: {e}")
            # Fallback vers un mock plus simple si l'import détaillé échoue
            from pandas_mock import DataFrame, read_csv, read_json
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

@pytest.fixture(scope="session", autouse=True)
def setup_numpy_for_tests_fixture(): 
    if 'PYTEST_CURRENT_TEST' in os.environ:
        numpy_module = setup_numpy()
        if sys.modules.get('numpy') is not numpy_module:
            sys.modules['numpy'] = numpy_module
        yield
    else: # Ajout d'un yield pour le cas où PYTEST_CURRENT_TEST n'est pas dans l'env
        yield


@pytest.fixture(scope="session", autouse=True)
def setup_pandas_for_tests_fixture(): 
    if 'PYTEST_CURRENT_TEST' in os.environ:
        pandas_module = setup_pandas()
        if sys.modules.get('pandas') is not pandas_module:
            sys.modules['pandas'] = pandas_module
        yield
    else:
        yield

@pytest.fixture(scope="session")
def integration_jvm(request):
    """
    Fixture de session pour démarrer et arrêter la JVM pour les tests d'intégration JPype.
    Utilise la logique de initialize_jvm de argumentation_analysis.core.jvm_setup.
    Cette fixture s'assure que le VRAI module jpype est utilisé.
    """
    global _integration_jvm_started_session_scope, _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL

    if _REAL_JPYPE_MODULE is None:
        pytest.fail("Le vrai module JPype n'est pas disponible. Tests d'intégration JPype impossibles.", pytrace=False)
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
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - Début - current_jpype_in_use.isJVMStarted() = {current_jpype_in_use.isJVMStarted()}")

        if current_jpype_in_use.isJVMStarted() and not _integration_jvm_started_session_scope:
            logger.error("integration_jvm: ERREUR - La JVM est déjà démarrée par un mécanisme externe alors que _integration_jvm_started_session_scope est False.")
            # Ne pas fail ici, car un autre test d'intégration aurait pu la démarrer via cette même fixture.
            # La variable _integration_jvm_started_session_scope est la clé.
            # pytest.fail("JVM démarrée prématurément. La fixture 'integration_jvm' doit contrôler son initialisation.", pytrace=False)
            # return

        if _integration_jvm_started_session_scope and current_jpype_in_use.isJVMStarted():
            logger.info("integration_jvm: La JVM a déjà été initialisée par cette fixture dans cette session.")
            yield
            return

        if initialize_jvm is None or LIBS_DIR is None or TWEETY_VERSION is None:
            logger.error("integration_jvm: initialize_jvm, LIBS_DIR ou TWEETY_VERSION non disponible. Impossible de démarrer la JVM.")
            pytest.fail("Dépendances manquantes pour démarrer la JVM (initialize_jvm, LIBS_DIR, TWEETY_VERSION).", pytrace=False)
            return

        logger.info("integration_jvm: Tentative d'initialisation de la JVM (via initialize_jvm)...")
        # initialize_jvm devrait utiliser le jpype actuellement dans sys.modules
        success = initialize_jvm(
            lib_dir_path=str(LIBS_DIR),
            tweety_version=TWEETY_VERSION
        )
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - initialize_jvm() APPELÉ. success = {success}")
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - Après initialize_jvm - current_jpype_in_use.isJVMStarted() = {current_jpype_in_use.isJVMStarted()}")
        
        if not success or not current_jpype_in_use.isJVMStarted():
            logger.error("integration_jvm: Échec critique de l'initialisation de la JVM.")
            _integration_jvm_started_session_scope = False
            pytest.fail("Échec de démarrage de la JVM pour les tests d'intégration.", pytrace=False)
        else:
            _integration_jvm_started_session_scope = True # Marquer comme démarrée par cette fixture
            logger.info("integration_jvm: JVM initialisée avec succès par cette fixture.")
            
        yield
        
    finally:
        # Le finalizer de session s'exécute une seule fois à la fin de tous les tests.
        # Il est important d'arrêter la JVM si cette fixture l'a démarrée.
        # La restauration de sys.modules au mock se fera par une autre fixture si nécessaire (ex: activate_jpype_mock_if_needed)
        # ou on assume que la session de test est terminée.
        # Pour l'instant, on se concentre sur l'arrêt de la JVM.
        
        # La restauration de sys.modules['jpype'] à son état original (mock ou rien)
        # doit se faire à la fin de la fixture pour que les tests suivants ne soient pas affectés
        # si cette fixture n'est pas la dernière de la session.
        # Cependant, avec scope="session", ce finalizer s'exécute tout à la fin.
        
        logger.info("integration_jvm: Finalisation de la session (arrêt JVM si démarrée par cette fixture).")
        current_jpype_for_shutdown = sys.modules.get('jpype') # Récupérer le jpype actuel (devrait être le vrai)
        
        if _integration_jvm_started_session_scope and current_jpype_for_shutdown is _REAL_JPYPE_MODULE and current_jpype_for_shutdown.isJVMStarted():
            try:
                logger.info("integration_jvm: Tentative d'arrêt de la JVM (vrai JPype)...")
                current_jpype_for_shutdown.shutdownJVM()
                logger.info("integration_jvm: JVM arrêtée (vrai JPype).")
            except Exception as e_shutdown:
                logger.error(f"integration_jvm: Erreur arrêt JVM (vrai JPype): {e_shutdown}", exc_info=True)
            finally:
                _integration_jvm_started_session_scope = False # Marquer comme non démarrée pour la prochaine session
        
        # Restaurer l'état original de sys.modules pour jpype et _jpype
        if original_sys_jpype is not None:
            sys.modules['jpype'] = original_sys_jpype
        elif 'jpype' in sys.modules: # S'il a été mis par nous et qu'il n'y avait rien avant
            del sys.modules['jpype']

        if original_sys_dot_jpype is not None:
            sys.modules['_jpype'] = original_sys_dot_jpype
        elif '_jpype' in sys.modules: # Idem
            del sys.modules['_jpype']
        logger.info("État original de sys.modules pour jpype/_jpype restauré après integration_jvm.")

# Fixture pour activer le mock JPype pour les tests unitaires
@pytest.fixture(scope="function", autouse=True)
def activate_jpype_mock_if_needed(request):
    """
    Active le mock JPype pour les tests, sauf si le marqueur 'real_jpype' est présent
    ou si le test est dans un chemin d'intégration connu.
    """
    global _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL, _REAL_JPYPE_MODULE
    
    use_real_jpype = False
    if request.node.get_closest_marker("real_jpype"):
        use_real_jpype = True
    
    # Heuristique basée sur le chemin (moins robuste que les marqueurs)
    path_str = str(request.node.fspath).replace(os.sep, '/')
    if 'tests/integration/' in path_str or 'tests/minimal_jpype_tweety_tests/' in path_str:
        use_real_jpype = True

    if use_real_jpype:
        logger.info(f"Test {request.node.name} demande REAL JPype. Configuration de sys.modules pour utiliser le vrai JPype.")
        if _REAL_JPYPE_MODULE:
            # Assurer que le vrai JPype est dans sys.modules
            # Cette opération est idempotente si déjà correctement configuré.
            sys.modules['jpype'] = _REAL_JPYPE_MODULE
            if hasattr(_REAL_JPYPE_MODULE, '_jpype'):
                sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
            elif '_jpype' in sys.modules and sys.modules.get('_jpype') is not getattr(_REAL_JPYPE_MODULE, '_jpype', None) : # Si un _jpype existe mais n'est pas celui du vrai module
                del sys.modules['_jpype']
            logger.debug(f"REAL JPype (ID: {id(_REAL_JPYPE_MODULE)}) est maintenant sys.modules['jpype'].")
        else:
            logger.error(f"Test {request.node.name} demande REAL JPype, mais _REAL_JPYPE_MODULE n'est pas disponible. Test échouera probablement.")
            # Ne pas yield ici pourrait être une option pour faire échouer le test plus tôt si _REAL_JPYPE_MODULE est None.
            # Mais la fixture integration_jvm le fera déjà.
        
        # On ne fait pas de restauration ici. La fixture integration_jvm (session) gère la JVM.
        # Le prochain test (s'il n'est pas real_jpype) verra cette fixture s'exécuter à nouveau
        # et la branche 'else' installera le mock.
        yield
    else:
        logger.info(f"Test {request.node.name} utilise MOCK JPype.")
        original_sys_jpype = sys.modules.get('jpype')
        original_sys_dot_jpype = sys.modules.get('_jpype')

        sys.modules['jpype'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL
        sys.modules['_jpype'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
        # S'assurer que le mock est bien celui qu'on a préparé
        assert sys.modules['jpype'] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL, "Mock JPype global n'a pas été correctement appliqué!"

        yield

        # Restaurer après le test si ce n'était pas déjà le mock global
        # (ou si on veut isoler les modifications du mock par test, mais le mock est global)
        if original_sys_jpype is not None:
            sys.modules['jpype'] = original_sys_jpype
        elif 'jpype' in sys.modules: # S'il a été mis par nous et qu'il n'y avait rien avant
             del sys.modules['jpype']

        if original_sys_dot_jpype is not None:
            sys.modules['_jpype'] = original_sys_dot_jpype
        elif '_jpype' in sys.modules: # Idem
            del sys.modules['_jpype']
        logger.info(f"État de JPype restauré après test {request.node.name} (utilisation du mock).")

# @pytest.fixture(scope="module")
# def dung_classes(integration_jvm):
#     import jpype 
#     logger.info(f"DEBUG_JVM_SETUP: dung_classes - Début - jpype.isJVMStarted() = {jpype.isJVMStarted()}")
#     if not jpype.isJVMStarted(): pytest.skip("JVM non démarrée (dung_classes).")
#     try:
#         TgfParser_class = None
#         try:
#             TgfParser_class = jpype.JClass("org.tweetyproject.arg.dung.io.TgfParser")
#         except jpype.JException:
#             logger.info("dung_classes: TgfParser non trouvé dans org.tweetyproject.arg.dung.io, essai avec .parser")
#             try:
#                 TgfParser_class = jpype.JClass("org.tweetyproject.arg.dung.parser.TgfParser")
#             except jpype.JException as e_parser:
#                 logger.warning(f"dung_classes: TgfParser non trouvé ni dans .io ni dans .parser: {e_parser}")
#
#         classes_to_return = {
#             "DungTheory": jpype.JClass("net.sf.tweety.arg.dung.syntax.DungTheory"),
#             "Argument": jpype.JClass("net.sf.tweety.arg.dung.syntax.Argument"),
#             "Attack": jpype.JClass("net.sf.tweety.arg.dung.syntax.Attack"),
#             "PreferredReasoner": jpype.JClass("net.sf.tweety.arg.dung.reasoner.PreferredReasoner"),
#             "GroundedReasoner": jpype.JClass("net.sf.tweety.arg.dung.reasoner.GroundedReasoner"),
#             "CompleteReasoner": jpype.JClass("net.sf.tweety.arg.dung.reasoner.CompleteReasoner"),
#             "StableReasoner": jpype.JClass("net.sf.tweety.arg.dung.reasoner.StableReasoner"),
#         }
#         if TgfParser_class:
#             classes_to_return["TgfParser"] = TgfParser_class
#         return classes_to_return
#
#     except jpype.JException as e: pytest.fail(f"Echec import classes Dung: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
#     except Exception as e_py: pytest.fail(f"Erreur Python (dung_classes): {str(e_py)}")
#
# @pytest.fixture(scope="module")
# def qbf_classes(integration_jvm):
#     import jpype 
#     logger.info(f"DEBUG_JVM_SETUP: qbf_classes - Début - jpype.isJVMStarted() = {jpype.isJVMStarted()}")
#     if not jpype.isJVMStarted(): pytest.skip("JVM non démarrée (qbf_classes).")
#     try:
#         return {
#             "QuantifiedBooleanFormula": jpype.JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula"),
#             "Quantifier": jpype.JClass("org.tweetyproject.logics.qbf.syntax.Quantifier"),
#             "QbfParser": jpype.JClass("org.tweetyproject.logics.qbf.parser.QbfParser"),
#             "Variable": jpype.JClass("org.tweetyproject.logics.commons.syntax.Variable"),
#         }
#     except jpype.JException as e: pytest.fail(f"Echec import classes QBF: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
#     except Exception as e_py: pytest.fail(f"Erreur Python (qbf_classes): {str(e_py)}")
#
# @pytest.fixture(scope="module")
# def belief_revision_classes(integration_jvm):
#     import jpype 
#     logger.info(f"DEBUG_JVM_SETUP: belief_revision_classes - Début - jpype.isJVMStarted() = {jpype.isJVMStarted()}")
#     if not jpype.isJVMStarted(): pytest.skip("JVM non démarrée (belief_revision_classes).")
#     try:
#         pl_classes = {
#             "PlFormula": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula"),
#             "PlBeliefSet": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet"),
#             "PlParser": jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser"),
#             "SimplePlReasoner": jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner"),
#             "Negation": jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation"),
#             "PlSignature": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature"),
#         }
#         revision_ops = {
#             "KernelContractionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.operators.KernelContractionOperator"),
#             "RandomIncisionFunction": jpype.JClass("org.tweetyproject.beliefdynamics.kernels.RandomIncisionFunction"),
#             "DefaultMultipleBaseExpansionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.operators.DefaultMultipleBaseExpansionOperator"),
#             "LeviMultipleBaseRevisionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.operators.LeviMultipleBaseRevisionOperator"),
#         }
#         crmas_classes = {
#             "CrMasBeliefSet": jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasBeliefSet"),
#             "InformationObject": jpype.JClass("org.tweetyproject.beliefdynamics.mas.InformationObject"),
#             "CrMasRevisionWrapper": jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasRevisionWrapper"),
#             "CrMasSimpleRevisionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasSimpleRevisionOperator"),
#             "CrMasArgumentativeRevisionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasArgumentativeRevisionOperator"),
#             "DummyAgent": jpype.JClass("org.tweetyproject.agents.DummyAgent"),
#             "Order": jpype.JClass("org.tweetyproject.commons.util.Order"),
#         }
#         inconsistency_measures = {
#             "ContensionInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.ContensionInconsistencyMeasure"),
#             "NaiveMusEnumerator": jpype.JClass("org.tweetyproject.logics.pl.analysis.NaiveMusEnumerator"),
#             "SatSolver": jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver"),
#         }
#         return {**pl_classes, **revision_ops, **crmas_classes, **inconsistency_measures}
#     except jpype.JException as e: pytest.fail(f"Echec import classes Belief Revision: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
#     except Exception as e_py: pytest.fail(f"Erreur Python (belief_revision_classes): {str(e_py)}")
#
# @pytest.fixture(scope="module")
# def dialogue_classes(integration_jvm):
#     import jpype 
#     logger.info(f"DEBUG_JVM_SETUP: dialogue_classes - Début - jpype.isJVMStarted() = {jpype.isJVMStarted()}")
#     if not jpype.isJVMStarted(): pytest.skip("JVM non démarrée (dialogue_classes).")
#     try:
#         return {
#             "ArgumentationAgent": jpype.JClass("org.tweetyproject.agents.dialogues.ArgumentationAgent"),
#             "GroundedAgent": jpype.JClass("org.tweetyproject.agents.dialogues.GroundedAgent"),
#             "OpponentModel": jpype.JClass("org.tweetyproject.agents.dialogues.OpponentModel"),
#             "Dialogue": jpype.JClass("org.tweetyproject.agents.dialogues.Dialogue"),
#             "DialogueTrace": jpype.JClass("org.tweetyproject.agents.dialogues.DialogueTrace"),
#             "DialogueResult": jpype.JClass("org.tweetyproject.agents.dialogues.DialogueResult"),
#             "PersuasionProtocol": jpype.JClass("org.tweetyproject.agents.dialogues.PersuasionProtocol"),
#             "Position": jpype.JClass("org.tweetyproject.agents.dialogues.Position"),
#             "SimpleBeliefSet": jpype.JClass("org.tweetyproject.logics.commons.syntax.SimpleBeliefSet"),
#             "DefaultStrategy": jpype.JClass("org.tweetyproject.agents.dialogues.strategies.DefaultStrategy"),
#         }
#     except jpype.JException as e: pytest.fail(f"Echec import classes Dialogue: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
#     except Exception as e_py: pytest.fail(f"Erreur Python (dialogue_classes): {str(e_py)}")

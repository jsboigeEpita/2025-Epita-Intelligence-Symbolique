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
    from argumentation_analysis.core.jvm_setup import initialize_jvm, TWEETY_VERSION # Importer TWEETY_VERSION directement
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
            import numpy_mock
            # Créer un dictionnaire à partir de tous les attributs de numpy_mock
            mock_numpy_attrs = {attr: getattr(numpy_mock, attr) for attr in dir(numpy_mock) if not attr.startswith('__')}
            # S'assurer que __version__ est bien celle du mock
            mock_numpy_attrs['__version__'] = numpy_mock.__version__ if hasattr(numpy_mock, '__version__') else '1.24.3.mock'
            
            sys.modules['numpy'] = type('numpy', (), mock_numpy_attrs)
            
            # Exposer explicitement les sous-modules nécessaires qui pourraient ne pas être des attributs directs
            if hasattr(numpy_mock, 'typing'):
                sys.modules['numpy.typing'] = numpy_mock.typing
            if hasattr(numpy_mock, '_core'):
                sys.modules['numpy._core'] = numpy_mock._core
            if hasattr(numpy_mock, 'core'):
                sys.modules['numpy.core'] = numpy_mock.core
            if hasattr(numpy_mock, 'rec'):
                 sys.modules['numpy.rec'] = numpy_mock.rec
            # Assurer que les multiarray sont là si _core/core les ont
            if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'multiarray'):
                 sys.modules['numpy._core.multiarray'] = numpy_mock._core.multiarray
            if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'multiarray'):
                 sys.modules['numpy.core.multiarray'] = numpy_mock.core
            
            # S'assurer que le module lui-même est bien dans sys.modules
            # Cela peut être redondant si type() le fait déjà, mais ne nuit pas.
            sys.modules['numpy'] = sys.modules['numpy']
            sys.modules['numpy.typing'] = numpy_typing_mock # Exposer le sous-module typing
            sys.modules['numpy._core'] = _core
            sys.modules['numpy.core'] = core
            sys.modules['numpy._core.multiarray'] = _core.multiarray
            sys.modules['numpy.core.multiarray'] = core.multiarray
            if 'rec' in sys.modules['numpy'].__dict__: # Assurer que rec est bien un attribut
                sys.modules['numpy.rec'] = sys.modules['numpy'].rec
            print("INFO: Mock NumPy installé immédiatement dans conftest.py (avec typing).")
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
        import numpy_mock
        # Créer un dictionnaire à partir de tous les attributs de numpy_mock
        mock_numpy_attrs = {attr: getattr(numpy_mock, attr) for attr in dir(numpy_mock) if not attr.startswith('__')}
        # S'assurer que __version__ est bien celle du mock
        mock_numpy_attrs['__version__'] = numpy_mock.__version__ if hasattr(numpy_mock, '__version__') else '1.24.3.mock'

        sys.modules['numpy'] = type('numpy', (), mock_numpy_attrs)
        
        # Exposer explicitement les sous-modules nécessaires
        if hasattr(numpy_mock, 'typing'):
            sys.modules['numpy.typing'] = numpy_mock.typing
        if hasattr(numpy_mock, '_core'):
            sys.modules['numpy._core'] = numpy_mock._core
        if hasattr(numpy_mock, 'core'):
            sys.modules['numpy.core'] = numpy_mock.core
        if hasattr(numpy_mock, 'rec'):
            sys.modules['numpy.rec'] = numpy_mock.rec
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'multiarray'):
            sys.modules['numpy._core.multiarray'] = numpy_mock._core.multiarray
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'multiarray'):
            sys.modules['numpy.core.multiarray'] = numpy_mock.core

        print("INFO: Mock NumPy configuré dynamiquement (avec tous les attributs de numpy_mock).")
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
    - Gère le démarrage unique de la JVM pour toute la session de test si nécessaire.
    - Utilise la logique de `initialize_jvm` de `argumentation_analysis.core.jvm_setup`.
    - S'assure que le VRAI module `jpype` est utilisé pendant son exécution.
    - Tente de s'assurer que `jpype.config` est accessible avant `shutdownJVM` pour éviter
      les `ModuleNotFoundError` dans les handlers `atexit` de JPype.
    - Laisse le vrai module `jpype` dans `sys.modules` après un arrêt réussi de la JVM
      par cette fixture, pour permettre aux handlers `atexit` de JPype de s'exécuter correctement.
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
        logger.info("integration_jvm: Finalisation de la session (arrêt JVM si démarrée par cette fixture).")
        current_jpype_for_shutdown = sys.modules.get('jpype') 

        jvm_was_shutdown_by_this_fixture = False
        if _integration_jvm_started_session_scope and current_jpype_for_shutdown is _REAL_JPYPE_MODULE and current_jpype_for_shutdown.isJVMStarted():
            try:
                # S'assurer que jpype.config est accessible avant shutdownJVM pour éviter ModuleNotFoundError dans atexit.
                if _REAL_JPYPE_MODULE: # Assure que _REAL_JPYPE_MODULE est le module jpype actuel
                    logger.info("integration_jvm: Vérification/Import de jpype.config avant shutdown...")
                    try:
                        # Tenter d'accéder ou d'importer jpype.config pour s'assurer qu'il est chargé
                        if not hasattr(sys.modules['jpype'], 'config'):
                             logger.info("   jpype.config non trouvé comme attribut, tentative d'import explicite.")
                             import jpype.config # Importe le config du module jpype actuellement dans sys.modules
                             logger.info("   Import explicite de jpype.config réussi.")
                        elif sys.modules['jpype'].config is None : # Cas où l'attribut existe mais est None
                             logger.info("   jpype.config est None, tentative d'import explicite.")
                             import jpype.config
                             logger.info("   Import explicite de jpype.config (après None) réussi.")
                        else:
                             logger.info(f"   jpype.config déjà présent (type: {type(sys.modules['jpype'].config)}).")
                    except ModuleNotFoundError:
                        logger.error("   ModuleNotFoundError pour jpype.config lors de la vérification/import avant shutdown.")
                    except ImportError:
                        logger.error("   ImportError pour jpype.config lors de la vérification/import avant shutdown.")
                    except Exception as e_cfg_imp:
                        logger.error(f"   Erreur lors de la vérification/import de jpype.config: {type(e_cfg_imp).__name__}: {e_cfg_imp}")

                logger.info("integration_jvm: Tentative d'arrêt de la JVM (vrai JPype)...")
                current_jpype_for_shutdown.shutdownJVM()
                logger.info("integration_jvm: JVM arrêtée (vrai JPype).")
                jvm_was_shutdown_by_this_fixture = True
            except Exception as e_shutdown:
                logger.error(f"integration_jvm: Erreur arrêt JVM (vrai JPype): {e_shutdown}", exc_info=True)
            finally:
                # Toujours marquer comme non démarrée pour la prochaine session potentielle (bien que session scope)
                _integration_jvm_started_session_scope = False 
        
        # Si la JVM a été gérée (démarrée et potentiellement arrêtée) par cette fixture,
        # et que _REAL_JPYPE_MODULE était utilisé, laissons _REAL_JPYPE_MODULE en place dans sys.modules
        # pour que les handlers atexit du vrai JPype fonctionnent correctement.
        # Sinon (si la JVM n'a pas été démarrée par nous, ou si _REAL_JPYPE_MODULE n'était pas là,
        # ou si une erreur a empêché le shutdown normal), restaurer comme avant.
        if not jvm_was_shutdown_by_this_fixture:
            logger.info("integration_jvm: La JVM n'a pas été (ou n'a pas pu être) arrêtée par cette fixture, ou _REAL_JPYPE_MODULE n'était pas actif. Restauration de sys.modules à l'état original.")
            if original_sys_jpype is not None:
                sys.modules['jpype'] = original_sys_jpype
            elif 'jpype' in sys.modules: 
                del sys.modules['jpype']

            if original_sys_dot_jpype is not None:
                sys.modules['_jpype'] = original_sys_dot_jpype
            elif '_jpype' in sys.modules: 
                del sys.modules['_jpype']
            logger.info("État original de sys.modules pour jpype/_jpype restauré après integration_jvm (cas non-shutdown ou erreur).")
        else:
            logger.info("integration_jvm: La JVM a été arrêtée par cette fixture. sys.modules['jpype'] reste _REAL_JPYPE_MODULE pour les handlers atexit.")
            # S'assurer que _jpype (le C module) correspond aussi au _REAL_JPYPE_MODULE si celui-ci en a un.
            if _REAL_JPYPE_MODULE and hasattr(_REAL_JPYPE_MODULE, '_jpype'):
                sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
            elif _REAL_JPYPE_MODULE and '_jpype' in sys.modules and sys.modules['_jpype'] is _MOCK_DOT_JPYPE_MODULE_GLOBAL:
                # Si le mock _jpype est toujours là mais qu'on laisse le vrai jpype, il faut aussi enlever le mock _jpype
                logger.info("integration_jvm: _REAL_JPYPE_MODULE laissé, suppression du _MOCK_DOT_JPYPE_MODULE_GLOBAL de sys.modules['_jpype'].")
                del sys.modules['_jpype']


# Fixture pour activer le mock JPype pour les tests unitaires
@pytest.fixture(scope="function", autouse=True)
def activate_jpype_mock_if_needed(request):
    """
    Active le mock JPype pour les tests, sauf si le marqueur 'real_jpype' est présent
    ou si le test est dans un chemin d'intégration connu.
    Cette fixture s'assure également que l'état de la JVM mockée (_jvm_started et _jvm_path)
    est réinitialisé avant chaque test utilisant le mock, pour garantir l'isolation.
    Comment utiliser:
    - Par défaut (tests unitaires): Le mock JPype est activé. `jpype.isJVMStarted()` retournera `False`
      au début de chaque test (grâce à la réinitialisation ici), et les appels à `jpype.startJVM()`
      utiliseront la version mockée qui mettra `_jvm_started` à `True` pour ce test.
    - Tests d'intégration nécessitant le vrai JPype:
        - Marquer le test ou la classe avec `@pytest.mark.real_jpype`.
        - S'assurer que la fixture `integration_jvm` est demandée par le test (directement ou via
          une autre fixture qui en dépend, comme `dung_classes`). `integration_jvm` démarrera
          la vraie JVM une fois par session et la laissera active pour tous les tests marqués.
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
            sys.modules['jpype'] = _REAL_JPYPE_MODULE
            if hasattr(_REAL_JPYPE_MODULE, '_jpype'):
                sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
            elif '_jpype' in sys.modules and sys.modules.get('_jpype') is not getattr(_REAL_JPYPE_MODULE, '_jpype', None) :
                del sys.modules['_jpype']
            logger.debug(f"REAL JPype (ID: {id(_REAL_JPYPE_MODULE)}) est maintenant sys.modules['jpype'].")
        else:
            logger.error(f"Test {request.node.name} demande REAL JPype, mais _REAL_JPYPE_MODULE n'est pas disponible. Test échouera probablement.")
        yield
    else:
        logger.info(f"Test {request.node.name} utilise MOCK JPype.")
        
        # Réinitialiser l'état _jvm_started et _jvm_path du mock JPype avant chaque test l'utilisant.
        # Cela se fait en accédant directement au module où ces variables sont définies.
        # Note: jpype_mock.py importe _jvm_started de tests.mocks.jpype_components.jvm
        try:
            jpype_components_jvm_module = sys.modules.get('tests.mocks.jpype_components.jvm')
            if jpype_components_jvm_module:
                if hasattr(jpype_components_jvm_module, '_jvm_started'):
                    jpype_components_jvm_module._jvm_started = False
                if hasattr(jpype_components_jvm_module, '_jvm_path'):
                    jpype_components_jvm_module._jvm_path = None
                # Réinitialiser aussi config.jvm_path dans le mock de config si le module jvm l'utilise
                # Le module jvm.py a sa propre instance locale de MinimalMockConfig.
                # Le module config.py a la principale instance `config` de MockConfig.
                # Il faut s'assurer que le _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config.jvm_path est aussi None.
                if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config') and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL.config, 'jvm_path'):
                    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config.jvm_path = None

                logger.info("État (_jvm_started, _jvm_path, config.jvm_path) du mock JPype réinitialisé pour le test.")
            else:
                # Essayer d'importer le module s'il n'est pas encore dans sys.modules, bien que ce soit peu probable ici
                # car jpype_mock.py l'importe.
                logger.warning("Impossible de réinitialiser l'état du mock JPype: module 'tests.mocks.jpype_components.jvm' non trouvé dans sys.modules.")
        except Exception as e_reset_mock:
            logger.error(f"Erreur lors de la réinitialisation de l'état du mock JPype: {e_reset_mock}")

        original_sys_jpype = sys.modules.get('jpype')
        original_sys_dot_jpype = sys.modules.get('_jpype')

        sys.modules['jpype'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL
        sys.modules['_jpype'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
        assert sys.modules['jpype'] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL, "Mock JPype global n'a pas été correctement appliqué!"

        yield

        if original_sys_jpype is not None:
            sys.modules['jpype'] = original_sys_jpype
        elif 'jpype' in sys.modules:
             del sys.modules['jpype']

        if original_sys_dot_jpype is not None:
            sys.modules['_jpype'] = original_sys_dot_jpype
        elif '_jpype' in sys.modules:
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

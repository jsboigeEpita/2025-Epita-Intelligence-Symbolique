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

# Nécessaire pour la fixture integration_jvm
_integration_jvm_started_session_scope = False
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm, TWEETY_VERSION # Importer TWEETY_VERSION directement
    from argumentation_analysis.paths import LIBS_DIR # Importer LIBS_DIR depuis paths.py
except ImportError as e_jvm_related_import:
    print(f"AVERTISSEMENT: tests/conftest.py: Échec de l'import pour initialize_jvm, TWEETY_VERSION ou LIBS_DIR: {e_jvm_related_import}")
    initialize_jvm = None
    LIBS_DIR = None
    TWEETY_VERSION = None

# --- Gestion du Path pour les Mocks ---
current_dir_for_mock = os.path.dirname(os.path.abspath(__file__))
mocks_dir_for_mock = os.path.join(current_dir_for_mock, 'mocks')
if mocks_dir_for_mock not in sys.path:
    sys.path.insert(0, mocks_dir_for_mock)
    print(f"INFO: tests/conftest.py: Ajout de {mocks_dir_for_mock} à sys.path.")

# --- Configuration du Logger ---
logger = logging.getLogger(__name__)
# print("INFO: conftest.py: Logger configuré pour pytest hooks jpype.")

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
    sys.modules['jpype'] = jpype_module_mock_obj
    sys.modules['_jpype'] = mock_dot_jpype_module
    print("INFO: JPype (et jpype.imports) mocké globalement.")
except ImportError as e_jpype:
    print(f"ERREUR CRITIQUE lors du mocking global de JPype: {e_jpype}")
    sys.modules['jpype'] = MagicMock(name="jpype_fallback_mock")
    sys.modules['jpype.imports'] = MagicMock(name="jpype.imports_fallback_mock")
    sys.modules['_jpype'] = MagicMock(name="_jpype_fallback_mock")

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
        return sys.modules['numpy']
    else: 
        import numpy
        print(f"Utilisation de la vraie bibliothèque NumPy (version {getattr(numpy, '__version__', 'inconnue')})")
        return numpy

def setup_pandas():
    if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('pandas'):
        if not is_module_available('pandas'): print("Pandas non disponible, utilisation du mock.")
        else: print("Python 3.12+ détecté, utilisation du mock Pandas.")
        from pandas_mock import DataFrame, read_csv, read_json
        sys.modules['pandas'] = type('pandas', (), {
            'DataFrame': DataFrame, 'read_csv': read_csv, 'read_json': read_json, 'Series': list,
            'NA': None, 'NaT': None, 'isna': lambda x: x is None, 'notna': lambda x: x is not None,
            '__version__': '1.5.3', 
        })
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
    """
    global _integration_jvm_started_session_scope
    import jpype # Assurer que jpype est importé ici, même si mocké/réel
    
    logger.info("Fixture 'integration_jvm' (session scope) appelée.")
    logger.info(f"DEBUG_JVM_SETUP: integration_jvm - Début - jpype.isJVMStarted() = {jpype.isJVMStarted()}")

    if jpype.isJVMStarted() and not _integration_jvm_started_session_scope:
        logger.error("integration_jvm: ERREUR - La JVM est déjà démarrée par un mécanisme externe.")
        pytest.fail("JVM démarrée prématurément. La fixture 'integration_jvm' doit contrôler son initialisation.", pytrace=False)
        return

    if _integration_jvm_started_session_scope and jpype.isJVMStarted():
        logger.info("integration_jvm: La JVM a déjà été initialisée par cette fixture dans cette session.")
        yield
        return

    if initialize_jvm is None or LIBS_DIR is None or TWEETY_VERSION is None:
        logger.error("integration_jvm: initialize_jvm, LIBS_DIR ou TWEETY_VERSION non disponible. Impossible de démarrer la JVM.")
        pytest.fail("Dépendances manquantes pour démarrer la JVM (initialize_jvm, LIBS_DIR, TWEETY_VERSION).", pytrace=False)
        return

    logger.info("integration_jvm: Tentative d'initialisation de la JVM...")
    success = initialize_jvm(
        lib_dir_path=str(LIBS_DIR),
        tweety_version=TWEETY_VERSION
    )
    logger.info(f"DEBUG_JVM_SETUP: integration_jvm - initialize_jvm() APPELÉ. success = {success}")
    logger.info(f"DEBUG_JVM_SETUP: integration_jvm - Après initialize_jvm - jpype.isJVMStarted() = {jpype.isJVMStarted()}")
    
    if not success or not jpype.isJVMStarted():
        logger.error("integration_jvm: Échec critique de l'initialisation de la JVM.")
        _integration_jvm_started_session_scope = False
        pytest.fail("Échec de démarrage de la JVM pour les tests d'intégration.", pytrace=False)
    else:
        _integration_jvm_started_session_scope = True # Marquer comme démarrée par cette fixture
        logger.info("integration_jvm: JVM initialisée avec succès par cette fixture.")
        
    def fin():
        global _integration_jvm_started_session_scope
        logger.info("integration_jvm: Finalisation (arrêt JVM si démarrée par elle).")
        logger.info(f"DEBUG_JVM_SETUP: integration_jvm - Début fin() - jpype.isJVMStarted() = {jpype.isJVMStarted()}")
        if _integration_jvm_started_session_scope and jpype.isJVMStarted():
            try:
                logger.info("integration_jvm: Tentative d'arrêt de la JVM...")
                jpype.shutdownJVM()
                logger.info("integration_jvm: JVM arrêtée.")
            except Exception as e_shutdown:
                logger.error(f"integration_jvm: Erreur arrêt JVM: {e_shutdown}", exc_info=True)
            finally:
                _integration_jvm_started_session_scope = False
        elif not jpype.isJVMStarted():
            logger.info("integration_jvm: JVM non démarrée à la finalisation.")
            _integration_jvm_started_session_scope = False
        else:
            logger.info("integration_jvm: JVM non démarrée par cette fixture ou déjà arrêtée.")

    request.addfinalizer(fin)
    yield

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

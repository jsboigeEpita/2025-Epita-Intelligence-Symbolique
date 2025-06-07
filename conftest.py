# pytest_plugins = ["pytest_playwright"]  # Temporairement désactivé pour les tests
print("INFO: conftest.py (RACINE): Fichier en cours de lecture par pytest.")

import sys
import os
import pytest # Importé plus haut pour être disponible globalement
import jpype
import jpype.imports # Assurer que jpype.imports est disponible

# Charger .env le plus tôt possible, dès l'import de ce conftest.py racine
# Ceci est fait avant que pytest ne charge les conftest.py des sous-répertoires ou les modules de test.
_DOTENV_LOADED_SUCCESSFULLY = False
try:
    from dotenv import load_dotenv
    _project_root_for_dotenv_early = os.path.dirname(os.path.abspath(__file__))
    _dotenv_path_early = os.path.join(_project_root_for_dotenv_early, '.env')
    print(f"INFO: conftest.py (RACINE) [NIVEAU SUPÉRIEUR]: Tentative de chargement du .env depuis: {_dotenv_path_early}")
    _loaded_early = load_dotenv(dotenv_path=_dotenv_path_early, override=True)
    if _loaded_early:
        _DOTENV_LOADED_SUCCESSFULLY = True
        print(f"INFO: conftest.py (RACINE) [NIVEAU SUPÉRIEUR]: .env chargé. USE_REAL_JPYPE='{os.getenv('USE_REAL_JPYPE')}'")
    else:
        print(f"INFO: conftest.py (RACINE) [NIVEAU SUPÉRIEUR]: .env non trouvé ou vide à {_dotenv_path_early}.")
except ImportError:
    print("ERREUR: conftest.py (RACINE) [NIVEAU SUPÉRIEUR]: python-dotenv non installé. Impossible de charger .env.")
    print("INFO: conftest.py (RACINE) [NIVEAU SUPÉRIEUR]: Veuillez installer via: pip install -r requirements.txt")
except Exception as e_dotenv_early:
    print(f"ERREUR: conftest.py (RACINE) [NIVEAU SUPÉRIEUR]: Erreur lors du chargement de .env: {e_dotenv_early}")

# Ajout précoce du chemin pour trouver argumentation_analysis
current_script_dir_for_path = os.path.dirname(os.path.abspath(__file__))
project_root_for_path = current_script_dir_for_path
if project_root_for_path not in sys.path:
    sys.path.insert(0, project_root_for_path)
    print(f"INFO: conftest.py (RACINE): Ajout de {project_root_for_path} à sys.path.")
else:
    print(f"INFO: conftest.py (RACINE): {project_root_for_path} déjà dans sys.path.")

initialize_jvm_func = None
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm as init_jvm_actual
    initialize_jvm_func = init_jvm_actual
    print("INFO: conftest.py (RACINE): Import de 'initialize_jvm' réussi.")
except Exception as e_import_jvm_setup:
    print(f"ERREUR CRITIQUE: conftest.py (RACINE): Échec de l'import de 'initialize_jvm': {e_import_jvm_setup}")

USE_REAL_JVM = True
jpype_real_jvm_initialized_value = "0"

if initialize_jvm_func is None:
    print("ERREUR CRITIQUE: conftest.py (RACINE): initialize_jvm_func non disponible. La JVM ne sera pas démarrée par ce conftest.")
elif USE_REAL_JVM:
    print("INFO: conftest.py (RACINE): Tentative d'initialisation de la VRAIE JVM... (MAINTENANT COMMENTÉE POUR LAISSER tests/conftest.py GÉRER)")
    # try:
    #     # if initialize_jvm_func(): # Appel commenté
    #     #     print("INFO: conftest.py (RACINE): VRAIE JVM initialisée avec succès par initialize_jvm_func().")
    #     #     jpype_real_jvm_initialized_value = "1"
    #     # else:
    #     #     print("ERREUR: conftest.py (RACINE): initialize_jvm_func() a retourné False (échec de l'initialisation).")
    #     print("INFO: conftest.py (RACINE): L'appel à initialize_jvm_func() est commenté. La JVM ne sera PAS démarrée par ce conftest racine.")
    #     jpype_real_jvm_initialized_value = "0" # Assurer que c'est 0 si on ne démarre pas
    # except Exception as e_init_jvm_conftest:
    #     print(f"ERREUR CRITIQUE: conftest.py (RACINE) lors de l'appel (commenté) à initialize_jvm_func: {e_init_jvm_conftest}")
    #     jpype_real_jvm_initialized_value = "0" # Assurer que c'est 0 en cas d'erreur même dans le bloc commenté
    print("INFO: conftest.py (RACINE): L'initialisation de la JVM par le conftest racine est DÉSACTIVÉE.")
    jpype_real_jvm_initialized_value = "0" # Explicitement non initialisé par ce fichier
else:
    print("INFO: conftest.py (RACINE): USE_REAL_JVM est False. Initialisation de la vraie JVM sautée.")

os.environ["JPYPE_REAL_JVM_INITIALIZED"] = jpype_real_jvm_initialized_value
print(f"INFO: conftest.py (RACINE): os.environ['JPYPE_REAL_JVM_INITIALIZED'] défini à '{jpype_real_jvm_initialized_value}'.")

print("INFO: conftest.py (RACINE): Initialisation minimale terminée.")

if jpype.isJVMStarted():
    print("INFO: conftest.py (RACINE): Vérification jpype.isJVMStarted() = True. L'enregistrement des domaines est géré par jvm_setup.py.")
    pass 
else:
    print("INFO: conftest.py (RACINE): jpype.isJVMStarted() = False. L'enregistrement des domaines sera géré par jvm_setup.py lors du démarrage.")


# @pytest.fixture(scope="module")
# def dung_classes():
#     import jpype
#     print(f"DEBUG: ROOT conftest - dung_classes fixture: jpype.isJVMStarted() = {jpype.isJVMStarted()}")
#     if not jpype.isJVMStarted():
#         pytest.skip("JVM non démarrée, skip dung_classes fixture.")
    
#     context_class_loader = None
#     try:
#         JavaThread = jpype.JClass("java.lang.Thread")
#         current_thread = JavaThread.currentThread()
#         context_class_loader = current_thread.getContextClassLoader()
#     except Exception as e_cl:
#         print(f"WARNING: ROOT conftest - Erreur obtention ContextClassLoader: {e_cl}")
    
#     loader_to_use = context_class_loader if context_class_loader else jpype.java.lang.ClassLoader.getSystemClassLoader()

#     classes_to_load = {
#         "DungTheory": "org.tweetyproject.arg.dung.syntax.DungTheory",
#         "Argument": "org.tweetyproject.arg.dung.syntax.Argument",
#         "Attack": "org.tweetyproject.arg.dung.syntax.Attack",
#         "PreferredReasoner": "org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner",
#         "GroundedReasoner": "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner",
#         "CompleteReasoner": "org.tweetyproject.arg.dung.reasoner.SimpleCompleteReasoner",
#         "StableReasoner": "org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner"
#     }
#     loaded_classes = {}
#     try:
#         for name, class_str in classes_to_load.items():
#             print(f"INFO: ROOT conftest - Chargement de {name} ({class_str}) avec loader={loader_to_use}")
#             loaded_classes[name] = jpype.JClass(class_str, loader=loader_to_use)
#         print("INFO: ROOT conftest - dung_classes: Toutes les classes Dung ont été chargées.")
#         return loaded_classes
#     except jpype.JException as e:
#         print(f"ERREUR CRITIQUE JPYPE dans dung_classes: {type(e).__name__}: {e}")
#         if hasattr(e, 'stacktrace') and callable(e.stacktrace): print(f"Stacktrace Java:\n{e.stacktrace()}")
#         pytest.fail(f"Échec JPype dans dung_classes (ROOT conftest): {e}")
#     except Exception as e_gen:
#         print(f"ERREUR CRITIQUE GENERALE dans dung_classes: {type(e_gen).__name__}: {e_gen}")
#         import traceback
#         print(f"Stacktrace Python:\n{traceback.format_exc()}")
#         pytest.fail(f"Erreur générale inattendue dans dung_classes (ROOT conftest): {e_gen}")


# @pytest.fixture(scope="module")
# def qbf_classes():
#     import jpype
#     if not jpype.isJVMStarted(): pytest.skip("JVM non démarrée")
#     print(f"DEBUG QBF_CLASSES: Classpath: {jpype.getClassPath(True)}") # Ajout du log classpath
#     loader_to_use = jpype.JClass("java.lang.Thread").currentThread().getContextClassLoader() or jpype.java.lang.ClassLoader.getSystemClassLoader()
#     try:
#         return {
#             "QuantifiedBooleanFormula": jpype.JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula", loader=loader_to_use),
#             "Quantifier": jpype.JClass("org.tweetyproject.logics.qbf.syntax.Quantifier", loader=loader_to_use),
#             "QbfParser": jpype.JClass("org.tweetyproject.logics.qbf.parser.QbfParser", loader=loader_to_use),
#             "Variable": jpype.JClass("org.tweetyproject.logics.commons.syntax.Variable", loader=loader_to_use),
#         }
#     except Exception as e: pytest.fail(f"Erreur chargement qbf_classes: {e}")

# @pytest.fixture(scope="module")
# def belief_revision_classes():
#     import jpype
#     if not jpype.isJVMStarted(): pytest.skip("JVM non démarrée")
#     print(f"DEBUG BELIEF_REVISION_CLASSES: Classpath: {jpype.getClassPath(True)}") # Ajout du log classpath
#     loader_to_use = jpype.JClass("java.lang.Thread").currentThread().getContextClassLoader() or jpype.java.lang.ClassLoader.getSystemClassLoader()
#     try:
#         return {
#             "PlFormula": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula", loader=loader_to_use),
#             "PlBeliefSet": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet", loader=loader_to_use),
#             "PlParser": jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser", loader=loader_to_use),
#             # ... (ajouter toutes les autres classes avec org.tweetyproject et loader_to_use)
#             "SimplePlReasoner": jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner", loader=loader_to_use),
#             "Negation": jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation", loader=loader_to_use),
#             "KernelContractionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.kernels.KernelContractionOperator", loader=loader_to_use),
#             "RandomIncisionFunction": jpype.JClass("org.tweetyproject.beliefdynamics.kernels.RandomIncisionFunction", loader=loader_to_use),
#             "DefaultMultipleBaseExpansionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.DefaultMultipleBaseExpansionOperator", loader=loader_to_use), # Correction du chemin
#             "LeviMultipleBaseRevisionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.LeviMultipleBaseRevisionOperator", loader=loader_to_use), # Correction du chemin
#             "CrMasBeliefSet": jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasBeliefSet", loader=loader_to_use),
#             "InformationObject": jpype.JClass("org.tweetyproject.beliefdynamics.mas.InformationObject", loader=loader_to_use),
#             "CrMasRevisionWrapper": jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasRevisionWrapper", loader=loader_to_use),
#             "CrMasSimpleRevisionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.operators.CrMasSimpleRevisionOperator", loader=loader_to_use), # Correction du chemin
#             "CrMasArgumentativeRevisionOperator": jpype.JClass("org.tweetyproject.beliefdynamics.operators.CrMasArgumentativeRevisionOperator", loader=loader_to_use), # Correction du chemin
#             "DummyAgent": jpype.JClass("org.tweetyproject.agents.DummyAgent", loader=loader_to_use),
#             "Order": jpype.JClass("org.tweetyproject.commons.util.Order", loader=loader_to_use),
#             "PlSignature": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature", loader=loader_to_use),
#             "ContensionInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.ContensionInconsistencyMeasure", loader=loader_to_use),
#             "NaiveMusEnumerator": jpype.JClass("org.tweetyproject.logics.pl.analysis.NaiveMusEnumerator", loader=loader_to_use),
#             "SatSolver": jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver", loader=loader_to_use),
#             "MaInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.MaInconsistencyMeasure", loader=loader_to_use),
#             "McscInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.McscInconsistencyMeasure", loader=loader_to_use),
#             "PossibleWorldIterator": jpype.JClass("org.tweetyproject.logics.pl.syntax.PossibleWorldIterator", loader=loader_to_use),
#             "DalalDistance": jpype.JClass("org.tweetyproject.logics.pl.util.DalalDistance", loader=loader_to_use),
#             "DSumInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.DSumInconsistencyMeasure", loader=loader_to_use),
#             "DMaxInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.DMaxInconsistencyMeasure", loader=loader_to_use),
#             "DHitInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.DHitInconsistencyMeasure", loader=loader_to_use),
#             "ProductNorm": jpype.JClass("org.tweetyproject.math.tnorms.ProductNorm", loader=loader_to_use),
#             "FuzzyInconsistencyMeasure": jpype.JClass("org.tweetyproject.logics.pl.analysis.FuzzyInconsistencyMeasure", loader=loader_to_use),
#             "PriorityIncisionFunction": jpype.JClass("org.tweetyproject.beliefdynamics.kernels.PriorityIncisionFunction", loader=loader_to_use),
#         }
#     except Exception as e: pytest.fail(f"Erreur chargement belief_revision_classes: {e}")

# @pytest.fixture(scope="module")
# def dialogue_classes():
#     import jpype
#     if not jpype.isJVMStarted(): pytest.skip("JVM non démarrée")
#     print(f"DEBUG DIALOGUE_CLASSES: Classpath: {jpype.getClassPath(True)}") # Ajout du log classpath
#     loader_to_use = jpype.JClass("java.lang.Thread").currentThread().getContextClassLoader() or jpype.java.lang.ClassLoader.getSystemClassLoader()
#     try:
#         return {
#             "ArgumentationAgent": jpype.JClass("org.tweetyproject.agents.dialogues.ArgumentationAgent", loader=loader_to_use),
#             "GroundedAgent": jpype.JClass("org.tweetyproject.agents.dialogues.GroundedAgent", loader=loader_to_use),
#             "OpponentModel": jpype.JClass("org.tweetyproject.agents.dialogues.OpponentModel", loader=loader_to_use),
#             "Dialogue": jpype.JClass("org.tweetyproject.agents.dialogues.Dialogue", loader=loader_to_use),
#             "DialogueTrace": jpype.JClass("org.tweetyproject.agents.dialogues.DialogueTrace", loader=loader_to_use),
#             "DialogueResult": jpype.JClass("org.tweetyproject.agents.dialogues.DialogueResult", loader=loader_to_use),
#             "PersuasionProtocol": jpype.JClass("org.tweetyproject.agents.dialogues.PersuasionProtocol", loader=loader_to_use),
#             "Position": jpype.JClass("org.tweetyproject.agents.dialogues.Position", loader=loader_to_use),
#             "SimpleBeliefSet": jpype.JClass("org.tweetyproject.logics.commons.syntax.SimpleBeliefSet", loader=loader_to_use),
#             "DefaultStrategy": jpype.JClass("org.tweetyproject.agents.dialogues.strategies.DefaultStrategy", loader=loader_to_use),
#         }
#     except Exception as e: pytest.fail(f"Erreur chargement dialogue_classes: {e}")
# Forcer anyio à utiliser uniquement le backend asyncio
@pytest.fixture(autouse=True)
def anyio_backend():
    return "asyncio"
# Ajout de fixtures pour les nouveaux modules Oracle Enhanced

import pytest
from argumentation_analysis.agents.core.oracle.error_handling import OracleErrorHandler
from argumentation_analysis.agents.core.oracle.interfaces import StandardOracleResponse

@pytest.fixture
def oracle_error_handler():
    """Fixture pour OracleErrorHandler"""
    return OracleErrorHandler()

@pytest.fixture  
def standard_oracle_response_success():
    """Fixture pour StandardOracleResponse de succès"""
    return StandardOracleResponse(
        success=True,
        data={"test": "data"},
        message="Test successful"
    )

@pytest.fixture
def standard_oracle_response_error():
    """Fixture pour StandardOracleResponse d'erreur"""
    return StandardOracleResponse(
        success=False,
        message="Test error",
        error_code="TEST_ERROR"
    )

# Ajout de fixtures pour Oracle Enhanced v2.1.0

import pytest
from argumentation_analysis.agents.core.oracle.error_handling import OracleErrorHandler
from argumentation_analysis.agents.core.oracle.interfaces import StandardOracleResponse

@pytest.fixture
def oracle_error_handler():
    """Fixture pour OracleErrorHandler"""
    return OracleErrorHandler()

@pytest.fixture  
def standard_oracle_response_success():
    """Fixture pour StandardOracleResponse de succès"""
    return StandardOracleResponse(
        success=True,
        data={"test": "data"},
        message="Test successful"
    )

@pytest.fixture
def standard_oracle_response_error():
    """Fixture pour StandardOracleResponse d'erreur"""
    return StandardOracleResponse(
        success=False,
        message="Test error",
        error_code="TEST_ERROR"
    )

# Ajout de fixtures pour Oracle Enhanced v2.1.0

import pytest
from argumentation_analysis.agents.core.oracle.error_handling import OracleErrorHandler
from argumentation_analysis.agents.core.oracle.interfaces import StandardOracleResponse

@pytest.fixture
def oracle_error_handler():
    """Fixture pour OracleErrorHandler"""
    return OracleErrorHandler()

@pytest.fixture  
def standard_oracle_response_success():
    """Fixture pour StandardOracleResponse de succès"""
    return StandardOracleResponse(
        success=True,
        data={"test": "data"},
        message="Test successful"
    )

@pytest.fixture
def standard_oracle_response_error():
    """Fixture pour StandardOracleResponse d'erreur"""
    return StandardOracleResponse(
        success=False,
        message="Test error",
        error_code="TEST_ERROR"
    )

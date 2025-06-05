import pytest
import sys
import os
import logging
from unittest.mock import MagicMock
import pathlib # Ajout pour la manipulation des chemins
import platform # Ajout pour platform.system()

# --- Configuration du Logger (DOIT ÊTRE AVANT TOUTE UTILISATION DE LOGGER) ---
logger = logging.getLogger(__name__)
if not logger.handlers: # Vérifier si des handlers existent déjà pour éviter la duplication
    handler = logging.StreamHandler(sys.stdout) # Utiliser sys.stdout pour pytest
    # Format de log plus concis pour les fixtures, les détails sont dans jvm_setup
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s_fixture] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # INFO est un bon niveau pour les fixtures
    logger.propagate = False # Empêcher la propagation au logger racine si configuré ailleurs

# Importation de la fonction d'initialisation centralisée et des constantes nécessaires
# Placé APRÈS la configuration du logger, au cas où ces imports déclencheraient des logs.
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm, LIBS_DIR, TWEETY_VERSION
    logger.info("initialize_jvm, LIBS_DIR, TWEETY_VERSION importés avec succès.")
except ImportError as e:
    logger.error(f"ERREUR CRITIQUE - Impossible d'importer depuis core.jvm_setup: {e}")
    # Définir des placeholders pour que le reste du fichier ne plante pas à l'import,
    # mais les tests utilisant la JVM seront skippés.
    initialize_jvm = None
    LIBS_DIR = None
    TWEETY_VERSION = None


# Importer _REAL_JPYPE_MODULE depuis jpype_setup
# et potentiellement _JPYPE_MODULE_MOCK_OBJ_GLOBAL si des comparaisons sont faites
try:
    from tests.mocks.jpype_setup import _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL
    logger.info("_REAL_JPYPE_MODULE et _JPYPE_MODULE_MOCK_OBJ_GLOBAL importés de jpype_setup.")
except ImportError:
    logger.error("ERREUR CRITIQUE: Impossible d'importer _REAL_JPYPE_MODULE de jpype_setup.")
    _REAL_JPYPE_MODULE = None # Fallback pour éviter des NameError, mais les tests d'intégration échoueront.
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = MagicMock(name="fallback_jpype_mock_obj_global_in_integration_fixtures")

# Variable globale pour suivre si initialize_jvm a été appelée avec succès dans la session
_initialize_jvm_called_successfully_session = False

@pytest.fixture(scope="session")
def integration_jvm():
    global _initialize_jvm_called_successfully_session
    logger.info("Début de la fixture integration_jvm (scope session).")

    if initialize_jvm is None:
        logger.error("La fonction initialize_jvm n'est pas disponible. Skip.")
        pytest.skip("initialize_jvm non importée, skip tests d'intégration JPype.")
        return None

    if _REAL_JPYPE_MODULE is None:
        logger.error("_REAL_JPYPE_MODULE est None. Impossible de démarrer la JVM pour les tests d'intégration.")
        pytest.skip("Le vrai module JPype n'a pas pu être chargé, skip tests d'intégration.")
        return None

    # S'assurer que sys.modules['jpype'] est le vrai module pour cette fixture
    original_sys_jpype = sys.modules.get('jpype')
    sys.modules['jpype'] = _REAL_JPYPE_MODULE
    logger.info(f"integration_fixtures.py: sys.modules['jpype'] (ID: {id(sys.modules['jpype'])}) mis à _REAL_JPYPE_MODULE (ID: {id(_REAL_JPYPE_MODULE)}).")

    jpype_for_integration = _REAL_JPYPE_MODULE
    
    try:
        if not _initialize_jvm_called_successfully_session:
            logger.info("initialize_jvm n'a pas encore été appelée avec succès dans cette session. Appel...")
            
            if LIBS_DIR is None or TWEETY_VERSION is None:
                logger.error("LIBS_DIR ou TWEETY_VERSION non défini. Impossible d'appeler initialize_jvm.")
                pytest.skip("LIBS_DIR ou TWEETY_VERSION manquant pour initialize_jvm.")
                return None

            success = initialize_jvm(
                lib_dir_path=str(LIBS_DIR)
                # tweety_version=TWEETY_VERSION, # Argument non attendu
                # use_exclusive_tweety_full_jar=False, # Argument non attendu
                # extra_jvm_args=None # Argument non attendu
            )
            if success:
                logger.info("initialize_jvm a réussi.")
                _initialize_jvm_called_successfully_session = True
            else:
                logger.error("initialize_jvm a échoué.")
                pytest.skip("Échec de initialize_jvm pour les tests d'intégration.")
                return None
        else:
            logger.info("initialize_jvm a déjà été appelée avec succès dans cette session. Utilisation de la JVM existante.")

        if not jpype_for_integration.isJVMStarted():
            logger.error("ERREUR CRITIQUE - JVM non démarrée même après l'appel à initialize_jvm.")
            pytest.skip("JVM non démarrée après initialize_jvm.")
            return None
            
        yield jpype_for_integration

    finally:
        logger.info("Nettoyage de la fixture integration_jvm (restauration de sys.modules['jpype'] si besoin).")
        if original_sys_jpype is not None:
            sys.modules['jpype'] = original_sys_jpype
        elif 'jpype' in sys.modules and sys.modules['jpype'] is _REAL_JPYPE_MODULE:
            if _REAL_JPYPE_MODULE is not _JPYPE_MODULE_MOCK_OBJ_GLOBAL :
                 del sys.modules['jpype']
        logger.info("Fin de la fixture integration_jvm.")


# Fixtures pour les classes Tweety (nécessitent une JVM active via integration_jvm)
@pytest.fixture(scope="session")
def dung_classes(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour dung_classes.")
    JClass = integration_jvm.JClass
loader_to_use = None
    try:
        JavaThread = integration_jvm.JClass("java.lang.Thread")
        current_thread = JavaThread.currentThread()
        loader_to_use = current_thread.getContextClassLoader()
        if loader_to_use is None: 
             loader_to_use = integration_jvm.JClass("java.lang.ClassLoader").getSystemClassLoader()
        logger.info(f"integration_fixtures.py: dung_classes - Utilisation du ClassLoader: {loader_to_use}")
    except Exception as e_loader:
        logger.warning(f"integration_fixtures.py: dung_classes - Erreur lors de l'obtention du ClassLoader: {str(e_loader)}. JClass utilisera le loader par défaut.")
        loader_to_use = None
    return {
        "DungTheory": JClass("org.tweetyproject.arg.dung.syntax.DungTheory"),
        "Argument": JClass("org.tweetyproject.arg.dung.syntax.Argument"),
        "Attack": JClass("org.tweetyproject.arg.dung.syntax.Attack"),
        "StableExtension": JClass("org.tweetyproject.arg.dung.semantics.StableExtension"),
        "PreferredExtension": JClass("org.tweetyproject.arg.dung.semantics.PreferredExtension"),
        "GroundedExtension": JClass("org.tweetyproject.arg.dung.semantics.GroundedExtension"),
        "CompleteExtension": JClass("org.tweetyproject.arg.dung.semantics.CompleteExtension"),
        "AbstractExtensionReasoner": JClass("org.tweetyproject.arg.dung.reasoner.AbstractExtensionReasoner"),
        "SimpleDungReasoner": JClass("org.tweetyproject.arg.dung.reasoner.SimpleDungReasoner")
    }

@pytest.fixture(scope="session")
def dl_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour dl_syntax_parser.")
    return integration_jvm.JClass("org.tweetyproject.logics.dl.parser.DlParser")

@pytest.fixture(scope="session")
def fol_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour fol_syntax_parser.")
    return integration_jvm.JClass("org.tweetyproject.logics.fol.parser.FolParser")

@pytest.fixture(scope="session")
def pl_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour pl_syntax_parser.")
    return integration_jvm.JClass("org.tweetyproject.logics.pl.parser.PlParser")

@pytest.fixture(scope="session")
def cl_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour cl_syntax_parser.")
    return integration_jvm.JClass("org.tweetyproject.logics.cl.parser.ClParser")


@pytest.fixture(scope="session")
def tweety_logics_classes(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_logics_classes.")
    JClass = integration_jvm.JClass
    return {
        # Propositional Logic
        "PlBeliefSet": JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet"),
        "PropositionalSignature": JClass("org.tweetyproject.logics.pl.syntax.PropositionalSignature"),
        "Proposition": JClass("org.tweetyproject.logics.pl.syntax.Proposition"),
        "PlReasoner": JClass("org.tweetyproject.logics.pl.reasoner.PlReasoner"), # Interface
        "SatReasoner": JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner"),
        "PlParser": JClass("org.tweetyproject.logics.pl.parser.PlParser"),
        # First-Order Logic
        "FolBeliefSet": JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet"),
        "FolSignature": JClass("org.tweetyproject.logics.fol.syntax.FolSignature"),
        "FolParser": JClass("org.tweetyproject.logics.fol.parser.FolParser"),
        "Prover9Reasoner": JClass("org.tweetyproject.logics.fol.reasoner.Prover9Reasoner"),
        # Conditional Logic
        "ClBeliefSet": JClass("org.tweetyproject.logics.cl.syntax.ClBeliefSet"),
        "Conditional": JClass("org.tweetyproject.logics.cl.syntax.Conditional"),
        "ClParser": JClass("org.tweetyproject.logics.cl.parser.ClParser"),
        "ZReasoner": JClass("org.tweetyproject.logics.cl.reasoner.ZReasoner"),
        # Description Logic
        "DlBeliefSet": JClass("org.tweetyproject.logics.dl.syntax.DlBeliefSet"),
        "DescriptionLogicSignature": JClass("org.tweetyproject.logics.dl.syntax.DescriptionLogicSignature"),
        "DlParser": JClass("org.tweetyproject.logics.dl.parser.DlParser"),
        "PelletReasoner": JClass("org.tweetyproject.logics.dl.reasoner.PelletReasoner"),
        # ASP
        "AspBeliefSet": JClass("org.tweetyproject.logics.asp.syntax.AspBeliefSet"),
        "DLVReasoner": JClass("org.tweetyproject.logics.asp.reasoner.DLVReasoner"),
        "ClingoReasoner": JClass("org.tweetyproject.logics.asp.reasoner.ClingoReasoner"),
        # General
        "BeliefSet": JClass("org.tweetyproject.commons.BeliefSet"),
        "Formula": JClass("org.tweetyproject.logics.commons.syntax.Formula"),
        "Signature": JClass("org.tweetyproject.logics.commons.syntax.Signature"),
        "Reasoner": JClass("org.tweetyproject.logics.commons.reasoner.Reasoner"), # Interface
        "QueryResult": JClass("org.tweetyproject.logics.commons.reasoner.QueryResult"),
        # Argumentation
        "ProbabilisticArgumentationFramework": JClass("org.tweetyproject.arg.prob.ProbabilisticArgumentationFramework"),
        "ProbabilisticFact": JClass("org.tweetyproject.arg.prob.ProbabilisticFact"),
        "ProbabilisticReasoner": JClass("org.tweetyproject.arg.prob.reasoner.ProbabilisticReasoner"),
        "EpistemicProbabilityReasoner": JClass("org.tweetyproject.arg.prob.reasoner.EpistemicProbabilityReasoner"),
        "DungTheory": JClass("org.tweetyproject.arg.dung.DungTheory"), # Répété de dung_classes pour complétude
        "Argument": JClass("org.tweetyproject.arg.dung.syntax.Argument"),
        "Attack": JClass("org.tweetyproject.arg.dung.syntax.Attack"),
        "SimpleDungReasoner": JClass("org.tweetyproject.arg.dung.reasoner.SimpleDungReasoner"),
        # Belief Revision
        "RevisionOperator": JClass("org.tweetyproject.beliefdynamics.RevisionOperator"), # Interface
        "DalalRevision": JClass("org.tweetyproject.beliefdynamics.revops.DalalRevision"),
        # Other useful classes
        "ArrayList": JClass("java.util.ArrayList"),
        "HashSet": JClass("java.util.HashSet"),
        "File": JClass("java.io.File"),
        "System": JClass("java.lang.System"),
        "TweetyConfiguration": JClass("org.tweetyproject.commons.TweetyConfiguration"),
    }

@pytest.fixture(scope="session")
def tweety_string_utils(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_string_utils.")
    return integration_jvm.JClass("org.tweetyproject.commons.util.string.StringUtils")

@pytest.fixture(scope="session")
def tweety_math_utils(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_math_utils.")
    return integration_jvm.JClass("org.tweetyproject.math.util.MathUtils")

@pytest.fixture(scope="session")
def tweety_probability(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_probability.")
    return integration_jvm.JClass("org.tweetyproject.math.probability.Probability")

@pytest.fixture(scope="session")
def tweety_conditional_probability(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_conditional_probability.")
    return integration_jvm.JClass("org.tweetyproject.math.probability.ConditionalProbability")

@pytest.fixture(scope="session")
def tweety_parser_exception(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_parser_exception.")
    return integration_jvm.JClass("org.tweetyproject.parsers.ParserException")

@pytest.fixture(scope="session")
def tweety_io_exception(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_io_exception.")
    return integration_jvm.JClass("java.io.IOException")

@pytest.fixture(scope="session")
def tweety_qbf_classes(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_qbf_classes.")
    JClass = integration_jvm.JClass
    return {
        "QuantifiedBooleanFormula": JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula"),
        "QbfNode": JClass("org.tweetyproject.logics.qbf.syntax.QbfNode"),
        "ExistsQuantifiedFormula": JClass("org.tweetyproject.logics.qbf.syntax.ExistsQuantifiedFormula"),
        "ForAllQuantifiedFormula": JClass("org.tweetyproject.logics.qbf.syntax.ForAllQuantifiedFormula"),
        "QbfReasoner": JClass("org.tweetyproject.logics.qbf.reasoner.QbfReasoner"), # Interface
        "CAQEReasoner": JClass("org.tweetyproject.logics.qbf.reasoner.CAQEReasoner"),
        "QbfParser": JClass("org.tweetyproject.logics.qbf.parser.QbfParser")
    }
@pytest.fixture(scope="session") # Changé scope à session pour correspondre aux autres fixtures Tweety
def belief_revision_classes(integration_jvm):
    logger.info("integration_fixtures.py: Début de la fixture 'belief_revision_classes'.")
    jpype_instance = integration_jvm
    
    if jpype_instance is None:
        logger.error("integration_fixtures.py: belief_revision_classes - jpype_instance (résultat de integration_jvm) est None!")
        pytest.skip("belief_revision_classes: jpype_instance (integration_jvm) est None.")
        return

    logger.info(f"integration_fixtures.py: belief_revision_classes - jpype_instance (ID: {id(jpype_instance)}) obtenu. Vérification de isJVMStarted()...")
    
    jvm_is_started_check = jpype_instance.isJVMStarted()
    logger.info(f"integration_fixtures.py: belief_revision_classes - jpype_instance.isJVMStarted() a retourné: {jvm_is_started_check}")

    if not jvm_is_started_check:
        logger.warning("integration_fixtures.py: belief_revision_classes - Appel de pytest.skip car jpype_instance.isJVMStarted() est False.")
        pytest.skip("JVM non démarrée ou jpype_instance None (belief_revision_classes).")
    
    logger.info("integration_fixtures.py: belief_revision_classes - JVM démarrée, tentative de chargement des classes.")
    try:
        loader_to_use = None
        try:
            JavaThread = jpype_instance.JClass("java.lang.Thread")
            current_thread = JavaThread.currentThread()
            loader_to_use = current_thread.getContextClassLoader()
            if loader_to_use is None: 
                 loader_to_use = jpype_instance.JClass("java.lang.ClassLoader").getSystemClassLoader()
            logger.info(f"integration_fixtures.py: belief_revision_classes - Utilisation du ClassLoader: {loader_to_use}")
        except Exception as e_loader:
            logger.warning(f"integration_fixtures.py: belief_revision_classes - Erreur lors de l'obtention du ClassLoader: {e_loader}. JClass utilisera le loader par défaut.")
            loader_to_use = None

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

@pytest.fixture(scope="session") # Changé scope à session
def dialogue_classes(integration_jvm):
    logger.info("integration_fixtures.py: Début de la fixture 'dialogue_classes'.")
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
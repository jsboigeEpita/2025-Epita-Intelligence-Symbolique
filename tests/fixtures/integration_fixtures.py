
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

import pytest
import sys
import os
import logging

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
# L'import de jpype_setup est obsolète. Le bootstrap gère le mock.
# Pour les tests d'intégration, nous attendons que l'environnement soit configuré
# pour utiliser le vrai JPype.
import jpype
from unittest.mock import MagicMock
# MagicMock peut être nécessaire si jpype est un mock et que nous voulons vérifier ses attributs
# Définir des placeholders pour la clarté, mais le but est d'utiliser le module 'jpype' importé directement
_REAL_JPYPE_MODULE = jpype if hasattr(jpype, 'isJVMStarted') and not isinstance(jpype, MagicMock) else None
_JPYPE_MODULE_MOCK_OBJ_GLOBAL = jpype if isinstance(jpype, MagicMock) else MagicMock(name="fallback_jpype_mock_obj_global_in_integration_fixtures")

# Variable globale pour suivre si initialize_jvm a été appelée avec succès dans la session
_integration_jvm_started_session_scope = False

@pytest.fixture(scope="session")
def integration_jvm(request):
    """
    Fixture à portée "session" pour gérer le cycle de vie de la VRAIE JVM pour les tests d'intégration.
    - Gère le démarrage unique de la JVM pour toute la session de test si nécessaire.
    - Utilise la logique de `initialize_jvm` de `argumentation_analysis.core.jvm_setup`.
    - S'assure que le VRAI module `jpype` est utilisé pendant son exécution.
    - Tente de s'assurer que `jpype.config` est accessible avant `shutdownJVM` pour éviter
      les `ModuleNotFoundError` dans les handlers `atexit` de JPype.
    - Laisse le vrai module `jpype` dans `sys.modules` après un arrêt réussi de la JVM
      par cette fixture, pour permettre aux handlers `atexit` de JPype de s'exécuter correctement.
    """
    global _integration_jvm_started_session_scope, _REAL_JPYPE_MODULE
    logger_conftest_integration = logger # Utiliser le logger de ce module

    if _REAL_JPYPE_MODULE is None:
        pytest.skip("Le vrai module JPype n'est pas disponible. Tests d'intégration JPype impossibles.", pytrace=False)
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
        if current_jpype_in_use.isJVMStarted() and _integration_jvm_started_session_scope:
            logger.info("integration_jvm: La JVM a déjà été initialisée par cette fixture dans cette session.")
            yield current_jpype_in_use
            return

        if initialize_jvm is None or LIBS_DIR is None or TWEETY_VERSION is None:
            pytest.skip("Dépendances manquantes pour démarrer la JVM (initialize_jvm, LIBS_DIR, TWEETY_VERSION).", pytrace=False)
            return

        logger.info("integration_jvm: Tentative d'initialisation de la JVM (via initialize_jvm)...")
        success = initialize_jvm(
            lib_dir_path=str(LIBS_DIR),
            tweety_version=TWEETY_VERSION
        )
        
        if not success or not current_jpype_in_use.isJVMStarted():
            _integration_jvm_started_session_scope = False
            pytest.skip("Échec de démarrage de la JVM pour les tests d'intégration.", pytrace=False)
        else:
            _integration_jvm_started_session_scope = True # Marquer comme démarrée par cette fixture
            logger.info("integration_jvm: JVM initialisée avec succès par cette fixture.")
            
        # Le 'yield' doit être ici pour que le code du test s'exécute, il manquait dans la version du stash
        yield current_jpype_in_use
        
    finally:
        # La finalisation est maintenant gérée par request.addfinalizer pour un meilleur contrôle
        pass

    def fin_integration_jvm():
        global _integration_jvm_started_session_scope
        logger_conftest_integration.info("integration_jvm: Finalisation (arrêt JVM si démarrée par elle).")
        current_jpype_for_shutdown = sys.modules.get('jpype')
        jvm_was_shutdown_by_this_fixture = False

        if _integration_jvm_started_session_scope and current_jpype_for_shutdown is _REAL_JPYPE_MODULE and current_jpype_for_shutdown.isJVMStarted():
            try:
                # S'assurer que jpype.config est accessible avant shutdownJVM
                if _REAL_JPYPE_MODULE:
                    logger_conftest_integration.info("integration_jvm: Vérification/Import de jpype.config avant shutdown...")
                    try:
                        if not hasattr(sys.modules['jpype'], 'config') or sys.modules['jpype'].config is None:
                             import jpype.config
                             logger_conftest_integration.info("   Import explicite de jpype.config réussi.")
                        else:
                             logger_conftest_integration.info(f"   jpype.config déjà présent.")
                    except Exception as e_cfg_imp:
                        logger_conftest_integration.error(f"   Erreur lors de la vérification/import de jpype.config: {e_cfg_imp}")

                logger_conftest_integration.info("integration_jvm: Tentative d'arrêt de la JVM (vrai JPype)...")
                current_jpype_for_shutdown.shutdownJVM()
                logger_conftest_integration.info("integration_jvm: JVM arrêtée (vrai JPype).")
                jvm_was_shutdown_by_this_fixture = True
            except Exception as e_shutdown:
                logger_conftest_integration.error(f"integration_jvm: Erreur arrêt JVM (vrai JPype): {e_shutdown}", exc_info=True)
            finally:
                _integration_jvm_started_session_scope = False
        
        if not jvm_was_shutdown_by_this_fixture:
            logger_conftest_integration.info("integration_jvm: Restauration de sys.modules à l'état original (cas non-shutdown ou erreur).")
            if original_sys_jpype is not None:
                sys.modules['jpype'] = original_sys_jpype
            elif 'jpype' in sys.modules:
                del sys.modules['jpype']
            if original_sys_dot_jpype is not None:
                sys.modules['_jpype'] = original_sys_dot_jpype
            elif '_jpype' in sys.modules:
                del sys.modules['_jpype']
        else:
            logger_conftest_integration.info("integration_jvm: La JVM a été arrêtée. sys.modules['jpype'] reste _REAL_JPYPE_MODULE.")
            if _REAL_JPYPE_MODULE and hasattr(_REAL_JPYPE_MODULE, '_jpype'):
                sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
    
    request.addfinalizer(fin_integration_jvm)


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
        "DungTheory": JClass("org.tweetyproject.arg.dung.syntax.DungTheory", loader=loader_to_use),
        "Argument": JClass("org.tweetyproject.arg.dung.syntax.Argument", loader=loader_to_use),
        "Attack": JClass("org.tweetyproject.arg.dung.syntax.Attack", loader=loader_to_use),
        "StableExtension": JClass("org.tweetyproject.arg.dung.semantics.StableExtension", loader=loader_to_use),
        "PreferredExtension": JClass("org.tweetyproject.arg.dung.semantics.PreferredExtension", loader=loader_to_use),
        "GroundedExtension": JClass("org.tweetyproject.arg.dung.semantics.GroundedExtension", loader=loader_to_use),
        "CompleteExtension": JClass("org.tweetyproject.arg.dung.semantics.CompleteExtension", loader=loader_to_use),
        "AbstractExtensionReasoner": JClass("org.tweetyproject.arg.dung.reasoner.AbstractExtensionReasoner", loader=loader_to_use),
        "SimpleDungReasoner": JClass("org.tweetyproject.arg.dung.reasoner.SimpleDungReasoner", loader=loader_to_use)
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
    loader_to_use = None
    try:
        JavaThread = integration_jvm.JClass("java.lang.Thread")
        current_thread = JavaThread.currentThread()
        loader_to_use = current_thread.getContextClassLoader()
        if loader_to_use is None:
             loader_to_use = integration_jvm.JClass("java.lang.ClassLoader").getSystemClassLoader()
        logger.info(f"integration_fixtures.py: tweety_logics_classes - Utilisation du ClassLoader: {loader_to_use}")
    except Exception as e_loader:
        logger.warning(f"integration_fixtures.py: tweety_logics_classes - Erreur lors de l'obtention du ClassLoader: {str(e_loader)}. JClass utilisera le loader par défaut.")
        loader_to_use = None
    return {
        # Propositional Logic
        "PlBeliefSet": JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet", loader=loader_to_use),
        "PropositionalSignature": JClass("org.tweetyproject.logics.pl.syntax.PropositionalSignature", loader=loader_to_use),
        "Proposition": JClass("org.tweetyproject.logics.pl.syntax.Proposition", loader=loader_to_use),
        "PlReasoner": JClass("org.tweetyproject.logics.pl.reasoner.PlReasoner", loader=loader_to_use), # Interface
        "SatReasoner": JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner", loader=loader_to_use),
        "PlParser": JClass("org.tweetyproject.logics.pl.parser.PlParser", loader=loader_to_use),
        # First-Order Logic
        "FolBeliefSet": JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet", loader=loader_to_use),
        "FolSignature": JClass("org.tweetyproject.logics.fol.syntax.FolSignature", loader=loader_to_use),
        "FolParser": JClass("org.tweetyproject.logics.fol.parser.FolParser", loader=loader_to_use),
        "Prover9Reasoner": JClass("org.tweetyproject.logics.fol.reasoner.Prover9Reasoner", loader=loader_to_use),
        # Conditional Logic
        "ClBeliefSet": JClass("org.tweetyproject.logics.cl.syntax.ClBeliefSet", loader=loader_to_use),
        "Conditional": JClass("org.tweetyproject.logics.cl.syntax.Conditional", loader=loader_to_use),
        "ClParser": JClass("org.tweetyproject.logics.cl.parser.ClParser", loader=loader_to_use),
        "ZReasoner": JClass("org.tweetyproject.logics.cl.reasoner.ZReasoner", loader=loader_to_use),
        # Description Logic
        "DlBeliefSet": JClass("org.tweetyproject.logics.dl.syntax.DlBeliefSet", loader=loader_to_use),
        "DescriptionLogicSignature": JClass("org.tweetyproject.logics.dl.syntax.DescriptionLogicSignature", loader=loader_to_use),
        "DlParser": JClass("org.tweetyproject.logics.dl.parser.DlParser", loader=loader_to_use),
        "PelletReasoner": JClass("org.tweetyproject.logics.dl.reasoner.PelletReasoner", loader=loader_to_use),
        # ASP
        "AspBeliefSet": JClass("org.tweetyproject.logics.asp.syntax.AspBeliefSet", loader=loader_to_use),
        "DLVReasoner": JClass("org.tweetyproject.logics.asp.reasoner.DLVReasoner", loader=loader_to_use),
        "ClingoReasoner": JClass("org.tweetyproject.logics.asp.reasoner.ClingoReasoner", loader=loader_to_use),
        # General
        "BeliefSet": JClass("org.tweetyproject.commons.BeliefSet", loader=loader_to_use),
        "Formula": JClass("org.tweetyproject.logics.commons.syntax.Formula", loader=loader_to_use),
        "Signature": JClass("org.tweetyproject.logics.commons.syntax.Signature", loader=loader_to_use),
        "Reasoner": JClass("org.tweetyproject.logics.commons.reasoner.Reasoner", loader=loader_to_use), # Interface
        "QueryResult": JClass("org.tweetyproject.logics.commons.reasoner.QueryResult", loader=loader_to_use),
        # Argumentation
        "ProbabilisticArgumentationFramework": JClass("org.tweetyproject.arg.prob.ProbabilisticArgumentationFramework", loader=loader_to_use),
        "ProbabilisticFact": JClass("org.tweetyproject.arg.prob.ProbabilisticFact", loader=loader_to_use),
        "ProbabilisticReasoner": JClass("org.tweetyproject.arg.prob.reasoner.ProbabilisticReasoner", loader=loader_to_use),
        "EpistemicProbabilityReasoner": JClass("org.tweetyproject.arg.prob.reasoner.EpistemicProbabilityReasoner", loader=loader_to_use),
        "DungTheory": JClass("org.tweetyproject.arg.dung.DungTheory", loader=loader_to_use), # Répété de dung_classes pour complétude
        "Argument": JClass("org.tweetyproject.arg.dung.syntax.Argument", loader=loader_to_use),
        "Attack": JClass("org.tweetyproject.arg.dung.syntax.Attack", loader=loader_to_use),
        "SimpleDungReasoner": JClass("org.tweetyproject.arg.dung.reasoner.SimpleDungReasoner", loader=loader_to_use),
        # Belief Revision
        "RevisionOperator": JClass("org.tweetyproject.beliefdynamics.RevisionOperator", loader=loader_to_use), # Interface
        "DalalRevision": JClass("org.tweetyproject.beliefdynamics.revops.DalalRevision", loader=loader_to_use),
        # Other useful classes
        "ArrayList": JClass("java.util.ArrayList", loader=loader_to_use),
        "HashSet": JClass("java.util.HashSet", loader=loader_to_use),
        "File": JClass("java.io.File", loader=loader_to_use),
        "System": JClass("java.lang.System", loader=loader_to_use),
        "TweetyConfiguration": JClass("org.tweetyproject.commons.TweetyConfiguration", loader=loader_to_use),
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
    loader_to_use = None
    try:
        JavaThread = integration_jvm.JClass("java.lang.Thread") # integration_jvm est le paramètre ici
        current_thread = JavaThread.currentThread()
        loader_to_use = current_thread.getContextClassLoader()
        if loader_to_use is None:
             loader_to_use = integration_jvm.JClass("java.lang.ClassLoader").getSystemClassLoader()
        logger.info(f"integration_fixtures.py: tweety_qbf_classes - Utilisation du ClassLoader: {loader_to_use}")
    except Exception as e_loader:
        logger.warning(f"integration_fixtures.py: tweety_qbf_classes - Erreur lors de l'obtention du ClassLoader: {str(e_loader)}. JClass utilisera le loader par défaut.")
        loader_to_use = None
    return {
        "QuantifiedBooleanFormula": JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula", loader=loader_to_use),
        "QbfNode": JClass("org.tweetyproject.logics.qbf.syntax.QbfNode", loader=loader_to_use),
        "ExistsQuantifiedFormula": JClass("org.tweetyproject.logics.qbf.syntax.ExistsQuantifiedFormula", loader=loader_to_use),
        "ForAllQuantifiedFormula": JClass("org.tweetyproject.logics.qbf.syntax.ForAllQuantifiedFormula", loader=loader_to_use),
        "QbfReasoner": JClass("org.tweetyproject.logics.qbf.reasoner.QbfReasoner", loader=loader_to_use), # Interface
        "CAQEReasoner": JClass("org.tweetyproject.logics.qbf.reasoner.CAQEReasoner", loader=loader_to_use),
        "QbfParser": JClass("org.tweetyproject.logics.qbf.parser.QbfParser", loader=loader_to_use)
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
        loader_to_use = None
        try:
            JavaThread = jpype_instance.JClass("java.lang.Thread") # jpype_instance est déjà défini dans cette fixture
            current_thread = JavaThread.currentThread()
            loader_to_use = current_thread.getContextClassLoader()
            if loader_to_use is None:
                 loader_to_use = jpype_instance.JClass("java.lang.ClassLoader").getSystemClassLoader()
            logger.info(f"integration_fixtures.py: dialogue_classes - Utilisation du ClassLoader: {loader_to_use}")
        except Exception as e_loader:
            logger.warning(f"integration_fixtures.py: dialogue_classes - Erreur lors de l'obtention du ClassLoader: {str(e_loader)}. JClass utilisera le loader par défaut.")
            loader_to_use = None
        return {
            "ArgumentationAgent": jpype_instance.JClass("org.tweetyproject.agents.dialogues.ArgumentationAgent", loader=loader_to_use),
            "GroundedAgent": jpype_instance.JClass("org.tweetyproject.agents.dialogues.GroundedAgent", loader=loader_to_use),
            "OpponentModel": jpype_instance.JClass("org.tweetyproject.agents.dialogues.OpponentModel", loader=loader_to_use),
            "Dialogue": jpype_instance.JClass("org.tweetyproject.agents.dialogues.Dialogue", loader=loader_to_use),
            "DialogueTrace": jpype_instance.JClass("org.tweetyproject.agents.dialogues.DialogueTrace", loader=loader_to_use),
            "DialogueResult": jpype_instance.JClass("org.tweetyproject.agents.dialogues.DialogueResult", loader=loader_to_use),
            "PersuasionProtocol": jpype_instance.JClass("org.tweetyproject.agents.dialogues.PersuasionProtocol", loader=loader_to_use),
            "Position": jpype_instance.JClass("org.tweetyproject.agents.dialogues.Position", loader=loader_to_use),
            "SimpleBeliefSet": jpype_instance.JClass("org.tweetyproject.logics.commons.syntax.SimpleBeliefSet", loader=loader_to_use),
            "DefaultStrategy": jpype_instance.JClass("org.tweetyproject.agents.dialogues.strategies.DefaultStrategy", loader=loader_to_use),
        }
    except jpype_instance.JException as e: pytest.fail(f"Echec import classes Dialogue: {e.stacktrace() if hasattr(e, 'stacktrace') else str(e)}")
    except Exception as e_py: pytest.fail(f"Erreur Python (dialogue_classes): {str(e_py)}")
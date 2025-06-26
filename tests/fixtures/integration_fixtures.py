
# Authentic gpt-4o-mini imports (replacing mocks)
from semantic_kernel.contents.chat_history import ChatHistory
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
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    logger.info("initialize_jvm importé avec succès.")
except ImportError as e:
    logger.error(f"ERREUR CRITIQUE - Impossible d'importer 'initialize_jvm' depuis core.jvm_setup: {e}")
    # Définir des placeholders pour que le reste du fichier ne plante pas à l'import,
    # mais les tests utilisant la JVM seront skippés.
    initialize_jvm = None


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

@pytest.fixture(scope="session")
def jvm_session(request):
    """
    Fixture de portée session qui initialise la JVM de manière paresseuse (lazy).

    Cette fixture garantit que la JVM est démarrée une seule fois pour toute la
    session de test, mais uniquement lorsque le premier test qui en a besoin
    l'appelle. Le nettoyage est géré par le hook `pytest_sessionfinish`.
    """
    fixture_logger = logging.getLogger("tests.fixtures.jvm_session_fixture")
    fixture_logger.info("--- Entrée dans la fixture 'jvm_session' ---")

    if not jpype.isJVMStarted():
        fixture_logger.info("La JVM n'est pas démarrée. Tentative d'initialisation...")
        initialized = initialize_jvm(session_fixture_owns_jvm=True)
        if not initialized:
            pytest.fail(
                "L'initialisation de la JVM a échoué dans la fixture 'jvm_session'.",
                pytrace=False
            )
        fixture_logger.info("JVM initialisée avec succès par la fixture 'jvm_session'.")
    else:
        fixture_logger.info("La JVM était déjà démarrée. La fixture 'jvm_session' n'a rien fait.")

    yield jpype

    fixture_logger.info("--- Sortie de la fixture 'jvm_session'. Le nettoyage sera fait par pytest_sessionfinish. ---")


@pytest.fixture(scope="session")
def tweety_classpath_initializer(jvm_session):
    """
    [OBSOLETE] Fixture qui garantissait l'initialisation du classpath.
    Cette logique est maintenant gérée directement au sein de `integration_jvm` qui passe
    le classpath au moment du `startJVM`.
    Cette fixture est conservée pour ne pas briser le graphe de dépendances des tests
    existants, mais elle ne fait plus rien.
    """
    logger.info("integration_fixtures.py: Fixture 'tweety_classpath_initializer' appelée (maintenant obsolète, aucune action).")
    # Vérifie simplement que la dépendance à integration_jvm est résolue.
    if jvm_session is None:
        pytest.skip("Dépendance 'jvm_session' non résolue pour tweety_classpath_initializer.")
    yield


# Fixtures pour les classes Tweety (nécessitent une JVM active via integration_jvm)
@pytest.fixture(scope="session")
def dung_classes(tweety_classpath_initializer, jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour dung_classes.")
    JClass = jvm_session.JClass
    loader_to_use = None
    try:
        JavaThread = jvm_session.JClass("java.lang.Thread")
        current_thread = JavaThread.currentThread()
        loader_to_use = current_thread.getContextClassLoader()
        if loader_to_use is None:
             loader_to_use = jvm_session.JClass("java.lang.ClassLoader").getSystemClassLoader()
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
def dl_syntax_parser(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour dl_syntax_parser.")
    return jvm_session.JClass("org.tweetyproject.logics.dl.parser.DlParser")

@pytest.fixture(scope="session")
def fol_syntax_parser(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour fol_syntax_parser.")
    return jvm_session.JClass("org.tweetyproject.logics.fol.parser.FolParser")

@pytest.fixture(scope="session")
def pl_syntax_parser(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour pl_syntax_parser.")
    return jvm_session.JClass("org.tweetyproject.logics.pl.parser.PlParser")

@pytest.fixture(scope="session")
def cl_syntax_parser(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour cl_syntax_parser.")
    return jvm_session.JClass("org.tweetyproject.logics.cl.parser.ClParser")


@pytest.fixture(scope="session")
def tweety_logics_classes(tweety_classpath_initializer, jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_logics_classes.")
    JClass = jvm_session.JClass
    loader_to_use = None
    try:
        JavaThread = jvm_session.JClass("java.lang.Thread")
        current_thread = JavaThread.currentThread()
        loader_to_use = current_thread.getContextClassLoader()
        if loader_to_use is None:
             loader_to_use = jvm_session.JClass("java.lang.ClassLoader").getSystemClassLoader()
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
def tweety_string_utils(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_string_utils.")
    return jvm_session.JClass("org.tweetyproject.commons.util.string.StringUtils")

@pytest.fixture(scope="session")
def tweety_math_utils(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_math_utils.")
    return jvm_session.JClass("org.tweetyproject.math.util.MathUtils")

@pytest.fixture(scope="session")
def tweety_probability(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_probability.")
    return jvm_session.JClass("org.tweetyproject.math.probability.Probability")

@pytest.fixture(scope="session")
def tweety_conditional_probability(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_conditional_probability.")
    return jvm_session.JClass("org.tweetyproject.math.probability.ConditionalProbability")

@pytest.fixture(scope="session")
def tweety_parser_exception(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_parser_exception.")
    return jvm_session.JClass("org.tweetyproject.parsers.ParserException")

@pytest.fixture(scope="session")
def tweety_io_exception(jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_io_exception.")
    return jvm_session.JClass("java.io.IOException")

@pytest.fixture(scope="session")
def tweety_qbf_classes(tweety_classpath_initializer, jvm_session):
    if jvm_session is None: pytest.skip("JVM non disponible pour tweety_qbf_classes.")
    JClass = jvm_session.JClass
    loader_to_use = None
    try:
        JavaThread = jvm_session.JClass("java.lang.Thread") # jvm_session est le paramètre ici
        current_thread = JavaThread.currentThread()
        loader_to_use = current_thread.getContextClassLoader()
        if loader_to_use is None:
             loader_to_use = jvm_session.JClass("java.lang.ClassLoader").getSystemClassLoader()
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
def belief_revision_classes(tweety_classpath_initializer, jvm_session):
    logger.info("integration_fixtures.py: Début de la fixture 'belief_revision_classes'.")
    jpype_instance = jvm_session
    
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
def dialogue_classes(tweety_classpath_initializer, jvm_session):
    logger.info("integration_fixtures.py: Début de la fixture 'dialogue_classes'.")
    jpype_instance = jvm_session
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
# --- Fixture pour les tests E2E ---
import sys
from pathlib import Path
project_root_fixture = Path(__file__).parent.parent.parent.resolve()
if str(project_root_fixture) not in sys.path:
    sys.path.insert(0, str(project_root_fixture))
import asyncio
from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator
import argparse

@pytest.fixture(scope="session", autouse=True)
def webapp_service(request):
    """
    Fixture E2E qui NE démarre PAS les serveurs, mais récupère leurs URLs
    depuis les options de la ligne de commande fournies par l'orchestrateur principal.
    Ceci évite le conflit de double démarrage.
    """
    logger.info("--- DEBUT FIXTURE 'webapp_service' (récupération des URLs E2E) ---")

    # Vérifier si la fixture est désactivée explicitement (garde la porte ouverte)
    if request.config.getoption("--disable-e2e-servers-fixture"):
        pytest.skip("Fixture webapp_service désactivée via la ligne de commande.")

    # Récupérer les URLs depuis les options pytest
    backend_url = request.config.getoption("--backend-url")
    frontend_url = request.config.getoption("--frontend-url")

    # Valider que les URLs sont bien présentes, sinon les tests E2E n'ont pas de sens.
    if not backend_url or not frontend_url:
        logger.info("URLs non fournies, la fixture 'webapp_service' ne fait rien.")
        yield None
        return

    logger.info(f"URL Backend récupérée: {backend_url}")
    logger.info(f"URL Frontend récupérée: {frontend_url}")

    # Pour résoudre `TypeError: 'Namespace' object is not subscriptable`,
    # on retourne un simple dictionnaire, qui est l'interface attendue par les tests.
    service_info = {
        "backend_url": backend_url,
        "frontend_url": frontend_url,
        # On inclut la structure imbriquée `app_info` pour la compatibilité
        # avec les tests qui pourraient utiliser `service.app_info.backend_url`.
        "app_info": argparse.Namespace(
            backend_url=backend_url,
            frontend_url=frontend_url,
            backend_pid=None,
            frontend_pid=None
        )
    }

    # Le yield fournit le dictionnaire aux tests.
    yield service_info
    
    logger.info("--- FIN FIXTURE 'webapp_service' ---")
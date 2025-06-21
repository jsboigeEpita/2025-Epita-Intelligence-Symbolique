
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
    Fixture à portée "session" pour la VRAIE JVM.
    Version simplifiée pour résoudre les crashs `access violation`.
    - Supprime la manipulation de sys.modules et l'état global.
    - Simplifie la vérification de l'état : si la JVM tourne, on l'utilise.
    - Si la JVM ne tourne pas, on la démarre et on la ferme à la fin.
    - Le classpath est passé directement au démarrage.
    """
    logger.info("--- DEBUT FIXTURE 'integration_jvm' ---")

    # Condition 1: Le vrai module JPype n'est pas disponible.
    if not hasattr(jpype, 'isJVMStarted') or isinstance(jpype, MagicMock):
        logger.warning("Le vrai module JPype n'est pas disponible. SKIP.")
        pytest.skip("Le vrai module JPype n'est pas disponible.")

    # Condition 2: La JVM est DÉJÀ démarrée par un autre composant.
    # On l'utilise telle quelle et on ne la gère pas (ni démarrage, ni arrêt).
    if jpype.isJVMStarted():
        logger.info("La JVM est déjà démarrée. Réutilisation de l'instance existante pour cette session.")
        yield jpype
        logger.info("--- FIN FIXTURE 'integration_jvm' (instance réutilisée) ---")
        return

    # --- Point de non-retour : la JVM n'est pas démarrée, cette fixture va la gérer ---
    logger.info("La JVM n'est pas démarrée. Cette fixture va prendre en charge son cycle de vie pour la session.")

    # Vérification des dépendances pour le démarrage
    if not all([initialize_jvm, LIBS_DIR, TWEETY_VERSION]):
         pytest.skip("Dépendances (initialize_jvm, LIBS_DIR, TWEETY_VERSION) manquantes.")

    # Construction explicite et robuste du classpath pour la JVM
    logger.info(f"Construction du classpath à partir du répertoire configuré : {LIBS_DIR.resolve()}")
    if not LIBS_DIR or not LIBS_DIR.is_dir():
        pytest.fail(f"Le répertoire des bibliothèques ({LIBS_DIR}) est manquant ou invalide.", pytrace=False)

    all_jars = [str(p.resolve()) for p in LIBS_DIR.glob("*.jar")]
    if not all_jars:
        # Échec si aucun JAR n'est trouvé, car le classpath sera vide.
        pytest.fail(f"Aucun fichier .jar trouvé dans {LIBS_DIR}. Le test ne peut pas continuer.", pytrace=False)

    classpath_str = os.pathsep.join(all_jars)
    logger.info(f"Classpath construit avec {len(all_jars)} JARs. Longueur: {len(classpath_str)} caractères.")
    logger.debug(f"Classpath final: {classpath_str}")

    # Démarrage de la JVM. `initialize_jvm` gère l'appel à jpype.startJVM.
    try:
        # *** BLOC CRITIQUE ***
        # L'appel est maintenant corrigé pour passer le classpath construit explicitement.
        logger.info("APPEL imminent à initialize_jvm avec classpath explicite...")
        success = initialize_jvm(classpath=classpath_str)
        logger.info("RETOUR de initialize_jvm. Si le crash n'a pas eu lieu, le classpath a été accepté.")
        if not success:
            pytest.fail("La fonction initialize_jvm() a renvoyé False, échec du démarrage de la JVM.")
    except Exception as e:
        logger.error(f"EXCEPTION CRITIQUE lors de l'appel à initialize_jvm : {e}", exc_info=True)
        pytest.fail(f"Exception critique lors de l'appel à initialize_jvm (startJVM) : {e}", pytrace=True)

    # Si on arrive ici, on a démarré la JVM. On doit donc la fermer à la fin.
    # On enregistre une fonction de finalisation pour garantir l'arrêt.
    def finalizer():
        logger.info("--- DEBUT FINALIZER pour 'integration_jvm' (portée session) ---")
        if jpype.isJVMStarted():
            logger.info("Le finalizer va appeler jpype.shutdownJVM().")
            jpype.shutdownJVM()
            logger.info("Le finalizer a appelé jpype.shutdownJVM() avec succès.")
        else:
            logger.warning("Le finalizer a été appelé, mais la JVM n'était plus démarrée.")
        logger.info("--- FIN FINALIZER pour 'integration_jvm' ---")

    request.addfinalizer(finalizer)

    logger.info("JVM initialisée avec succès par la fixture. Le test peut s'exécuter.")
    yield jpype
    logger.info("--- FIN FIXTURE 'integration_jvm' (yield terminé) ---")


@pytest.fixture(scope="session")
def tweety_classpath_initializer(integration_jvm):
    """
    [OBSOLETE] Fixture qui garantissait l'initialisation du classpath.
    Cette logique est maintenant gérée directement au sein de `integration_jvm` qui passe
    le classpath au moment du `startJVM`.
    Cette fixture est conservée pour ne pas briser le graphe de dépendances des tests
    existants, mais elle ne fait plus rien.
    """
    logger.info("integration_fixtures.py: Fixture 'tweety_classpath_initializer' appelée (maintenant obsolète, aucune action).")
    # Vérifie simplement que la dépendance à integration_jvm est résolue.
    if integration_jvm is None:
        pytest.skip("Dépendance 'integration_jvm' non résolue pour tweety_classpath_initializer.")
    yield


# Fixtures pour les classes Tweety (nécessitent une JVM active via integration_jvm)
@pytest.fixture(scope="session")
def dung_classes(tweety_classpath_initializer, integration_jvm):
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
def tweety_logics_classes(tweety_classpath_initializer, integration_jvm):
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
def tweety_qbf_classes(tweety_classpath_initializer, integration_jvm):
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
def belief_revision_classes(tweety_classpath_initializer, integration_jvm):
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
def dialogue_classes(tweety_classpath_initializer, integration_jvm):
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
# --- Fixture pour les tests E2E ---
import asyncio
from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator
import argparse

@pytest.fixture(scope="session")
def e2e_servers(request):
    """
    Fixture à portée session qui démarre les serveurs backend et frontend
    pour les tests End-to-End.
    """
    logger.info("--- DEBUT FIXTURE 'e2e_servers' (démarrage des serveurs E2E) ---")

    # Crée un Namespace d'arguments simple pour l'orchestrateur
    # On force les valeurs nécessaires pour un scénario de test E2E.
    args = argparse.Namespace(
        config='argumentation_analysis/webapp/config/webapp_config.yml',
        headless=True,
        visible=False,
        frontend=True,  # Crucial pour les tests E2E
        tests=None,
        timeout=5, # Timeout plus court pour le démarrage en test
        log_level='DEBUG',
        no_trace=True, # Pas besoin de trace MD pour les tests automatisés
        no_playwright=True, # On ne veut pas que l'orchestrateur lance les tests, seulement les serveurs
        exit_after_start=False,
        start=True, # Simule l'option de démarrage
        stop=False,
        test=False,
        integration=False,
    )

    orchestrator = UnifiedWebOrchestrator(args)

    # Le scope "session" de pytest s'exécute en dehors de la boucle d'événement
    # d'un test individuel. On doit gérer la boucle manuellement ici.
    loop = asyncio.get_event_loop_policy().get_event_loop()
    if loop.is_running():
        # Si la boucle tourne (rare en scope session), on ne peut pas utiliser run_until_complete
        # C'est un scénario complexe, on skippe pour l'instant.
        pytest.skip("Impossible de démarrer les serveurs E2E dans une boucle asyncio déjà active.")

    success = loop.run_until_complete(orchestrator.start_webapp(headless=True, frontend_enabled=True))
    
    # Vérification que le backend est bien démarré, car c'est bloquant.
    if not orchestrator.app_info.backend_pid:
        logger.error("Le backend n'a pas pu démarrer. Arrêt de la fixture.")
        loop.run_until_complete(orchestrator.stop_webapp())
        pytest.fail("Echec du démarrage du serveur backend pour les tests E2E.", pytrace=False)
        
    def finalizer():
        logger.info("--- FIN FIXTURE 'e2e_servers' (arrêt des serveurs E2E) ---")
        # S'assurer que la boucle est disponible pour le nettoyage
        cleanup_loop = asyncio.get_event_loop_policy().get_event_loop()
        cleanup_loop.run_until_complete(orchestrator.stop_webapp())

    request.addfinalizer(finalizer)

    # Fournir l'orchestrateur aux tests s'ils en ont besoin
    yield orchestrator
import pytest
import sys
import os
import logging
from unittest.mock import MagicMock
import pathlib # Ajout pour la manipulation des chemins
import platform # Ajout pour platform.system()
from argumentation_analysis.core.jvm_setup import find_valid_java_home

# --- Configuration du Logger ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

# Importer _REAL_JPYPE_MODULE depuis jpype_setup
# et potentiellement _JPYPE_MODULE_MOCK_OBJ_GLOBAL si des comparaisons sont faites
try:
    from tests.mocks.jpype_setup import _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL
    logger.info("integration_fixtures.py: _REAL_JPYPE_MODULE et _JPYPE_MODULE_MOCK_OBJ_GLOBAL importés de jpype_setup.")
except ImportError:
    logger.error("integration_fixtures.py: ERREUR CRITIQUE: Impossible d'importer _REAL_JPYPE_MODULE de jpype_setup.")
    _REAL_JPYPE_MODULE = None # Fallback pour éviter des NameError, mais les tests d'intégration échoueront.
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = MagicMock(name="fallback_jpype_mock_obj_global_in_integration_fixtures")


@pytest.fixture(scope="session")
def integration_jvm():
    logger.info("integration_fixtures.py: Début de la fixture integration_jvm (scope session).")
    if _REAL_JPYPE_MODULE is None:
        logger.error("integration_fixtures.py: _REAL_JPYPE_MODULE est None. Impossible de démarrer la JVM pour les tests d'intégration.")
        pytest.skip("Le vrai module JPype n'a pas pu être chargé, skip tests d'intégration.")
        return None

    # S'assurer que sys.modules['jpype'] est le vrai module pour cette fixture
    original_sys_jpype = sys.modules.get('jpype')
    original_sys_jpype_core = sys.modules.get('jpype._core')
    original_sys_jpype_imports = sys.modules.get('jpype.imports')

    sys.modules['jpype'] = _REAL_JPYPE_MODULE
    logger.info(f"integration_fixtures.py: sys.modules['jpype'] (ID: {id(sys.modules['jpype'])}) mis à _REAL_JPYPE_MODULE (ID: {id(_REAL_JPYPE_MODULE)}).")

    if hasattr(_REAL_JPYPE_MODULE, '_jpype'):
        sys.modules['jpype._core'] = _REAL_JPYPE_MODULE._jpype
        logger.info(f"integration_fixtures.py: sys.modules['jpype._core'] mis à _REAL_JPYPE_MODULE._jpype (ID: {id(_REAL_JPYPE_MODULE._jpype)}).")
    elif '_jpype' in sys.modules and sys.modules['_jpype'] is not getattr(_REAL_JPYPE_MODULE, '_jpype', None):
         # Si _jpype existe mais n'est pas celui du REAL_JPYPE_MODULE, on le supprime pour éviter confusion
        del sys.modules['_jpype']
        logger.info("integration_fixtures.py: Ancien sys.modules['_jpype'] supprimé car différent de _REAL_JPYPE_MODULE._jpype.")


    if hasattr(_REAL_JPYPE_MODULE, 'imports'):
        sys.modules['jpype.imports'] = _REAL_JPYPE_MODULE.imports
        logger.info(f"integration_fixtures.py: sys.modules['jpype.imports'] mis à _REAL_JPYPE_MODULE.imports (ID: {id(_REAL_JPYPE_MODULE.imports)}).")
    elif 'jpype.imports' in sys.modules and sys.modules['jpype.imports'] is not getattr(_REAL_JPYPE_MODULE, 'imports', None):
        del sys.modules['jpype.imports']
        logger.info("integration_fixtures.py: Ancien sys.modules['jpype.imports'] supprimé.")


    jpype_for_integration = _REAL_JPYPE_MODULE
    
    try:
        logger.info(f"integration_fixtures.py: Vérification de la JVM. jpype_for_integration.isJVMStarted() = {jpype_for_integration.isJVMStarted()}")
        if not jpype_for_integration.isJVMStarted():
            logger.info("integration_fixtures.py: JVM non démarrée. Tentative de démarrage.")
            
            jvm_path_to_use = None # Initialisation
            logger.info("integration_fixtures.py: Tentative de recherche de JAVA_HOME via find_valid_java_home() de core.jvm_setup.")
            java_home_found = find_valid_java_home() # Cette fonction logue déjà beaucoup

            if java_home_found:
                logger.info(f"integration_fixtures.py: find_valid_java_home() a retourné: {java_home_found}")
                java_home_path = pathlib.Path(java_home_found)
                system_os = platform.system()
                potential_jvm_path = None # Initialisation pour cette portée
                
                if system_os == "Windows":
                    potential_jvm_path = java_home_path / "bin" / "server" / "jvm.dll"
                elif system_os == "Darwin": # macOS
                    # Chemin standard pour les JDK décompressés
                    potential_jvm_path = java_home_path / "lib" / "server" / "libjvm.dylib"
                    # Vérifier la structure .app/Contents/Home si le précédent échoue
                    if not (potential_jvm_path and potential_jvm_path.is_file()):
                         _alt_path = java_home_path / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib"
                         if _alt_path.is_file():
                             potential_jvm_path = _alt_path
                    # Vérifier la structure JRE si les précédents échouent
                    if not (potential_jvm_path and potential_jvm_path.is_file()):
                        _alt_path_jre = java_home_path / "jre" / "lib" / "server" / "libjvm.dylib"
                        if _alt_path_jre.is_file():
                            potential_jvm_path = _alt_path_jre
                else: # Linux et autres
                    potential_jvm_path = java_home_path / "lib" / "server" / "libjvm.so"
                    if not (potential_jvm_path and potential_jvm_path.is_file()): # Structure JRE
                        _alt_path_jre = java_home_path / "jre" / "lib" / "server" / "libjvm.so"
                        if _alt_path_jre.is_file():
                            potential_jvm_path = _alt_path_jre

                if potential_jvm_path and potential_jvm_path.is_file():
                    jvm_path_to_use = str(potential_jvm_path.resolve())
                    logger.info(f"integration_fixtures.py: Chemin JVM construit à partir de find_valid_java_home(): {jvm_path_to_use}")
                else:
                    logger.warning(f"integration_fixtures.py: JAVA_HOME trouvé par find_valid_java_home() ({java_home_found}), mais impossible de construire un chemin JVM valide (testé: {potential_jvm_path}).")
            else:
                logger.warning("integration_fixtures.py: find_valid_java_home() n'a pas trouvé de JDK valide.")

            # Fallback sur jpype.getDefaultJVMPath() si find_valid_java_home échoue ou ne donne pas de chemin JVM
            if not jvm_path_to_use:
                logger.warning("integration_fixtures.py: Tentative de fallback avec jpype.getDefaultJVMPath().")
                try:
                    jvm_path_to_use = jpype_for_integration.getDefaultJVMPath()
                    logger.info(f"integration_fixtures.py: jpype.getDefaultJVMPath() a retourné: {jvm_path_to_use}")
                except jpype_for_integration.JVMNotFoundException as e:
                    logger.error(f"integration_fixtures.py: JVMNotFoundException lors de getDefaultJVMPath() (fallback): {e}")
                    pytest.skip(f"Impossible de trouver la JVM (find_valid_java_home et getDefaultJVMPath ont échoué): {e}. Vérifiez JAVA_HOME ou JDK portable.")
                    return # Important pour sortir de la fixture après skip
            
            if not jvm_path_to_use: # Si toujours None après tous les essais
                 logger.error("integration_fixtures.py: Échec final de la détermination du chemin JVM après toutes les tentatives.")
                 pytest.skip("Échec final de la détermination du chemin JVM. Vérifiez la configuration JAVA_HOME ou le JDK portable.")
                 return # Important pour sortir de la fixture après skip

            logger.info(f"integration_fixtures.py: Chemin JVM final à utiliser: {jvm_path_to_use}")

            # Recherche des JARs Tweety dans le sous-répertoire libs/tweety
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            tweety_libs_path = os.path.join(project_root, 'libs') # Corrigé: les JARs sont directement dans libs/
            
            if not os.path.isdir(tweety_libs_path):
                logger.error(f"integration_fixtures.py: Répertoire des bibliothèques Tweety non trouvé: {tweety_libs_path}")
                pytest.skip(f"Répertoire {tweety_libs_path} non trouvé.") # Message de skip mis à jour
                return None

            tweety_jars = [os.path.join(tweety_libs_path, f) for f in os.listdir(tweety_libs_path) if f.endswith('.jar')]

            if not tweety_jars:
                logger.error(f"integration_fixtures.py: Aucun JAR trouvé dans {tweety_libs_path}")
                pytest.skip(f"Aucun JAR Tweety trouvé dans {tweety_libs_path}.") # Message de skip mis à jour
                return None
            
            classpath_arg = "-Djava.class.path=" + os.pathsep.join(tweety_jars)
            logger.info(f"integration_fixtures.py: Classpath pour la JVM: {classpath_arg}")

            try:
                jpype_for_integration.startJVM(jvm_path_to_use, classpath_arg, convertStrings=False)
                logger.info("integration_fixtures.py: JVM démarrée avec succès.")
            except Exception as e_start_jvm:
                logger.error(f"integration_fixtures.py: Erreur lors du démarrage de la JVM: {e_start_jvm}", exc_info=True)
                pytest.skip(f"Impossible de démarrer la JVM pour les tests d'intégration: {e_start_jvm}")
                return None
        else:
            logger.info("integration_fixtures.py: JVM déjà démarrée.")

        # S'assurer que destroy_jvm est False pour la session
        if hasattr(jpype_for_integration, 'config') and jpype_for_integration.config is not None:
            jpype_for_integration.config.destroy_jvm = False
            logger.info(f"integration_fixtures.py: jpype_for_integration.config.destroy_jvm mis à False.")
        else:
            logger.warning("integration_fixtures.py: jpype_for_integration.config non disponible, impossible de régler destroy_jvm.")

        yield jpype_for_integration

    finally:
        logger.info("integration_fixtures.py: Nettoyage de la fixture integration_jvm.")
        # Restaurer les modules originaux
        if original_sys_jpype is not None:
            sys.modules['jpype'] = original_sys_jpype
            logger.info("integration_fixtures.py: sys.modules['jpype'] restauré.")
        elif 'jpype' in sys.modules and sys.modules['jpype'] is _REAL_JPYPE_MODULE :
            # Si on l'a mis et qu'il n'y avait rien, on le retire pour ne pas polluer
            # sauf si c'est le mock global, ce qui ne devrait pas être le cas ici.
            if _REAL_JPYPE_MODULE is not _JPYPE_MODULE_MOCK_OBJ_GLOBAL :
                 del sys.modules['jpype']
                 logger.info("integration_fixtures.py: sys.modules['jpype'] (notre _REAL_JPYPE_MODULE) supprimé car rien n'était là avant.")

        if original_sys_jpype_core is not None:
            sys.modules['jpype._core'] = original_sys_jpype_core
            logger.info("integration_fixtures.py: sys.modules['jpype._core'] restauré.")
        elif 'jpype._core' in sys.modules and hasattr(_REAL_JPYPE_MODULE, '_jpype') and sys.modules['jpype._core'] is _REAL_JPYPE_MODULE._jpype:
            if _REAL_JPYPE_MODULE._jpype is not getattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, '_jpype', None): # Ne pas supprimer le mock global par erreur
                del sys.modules['jpype._core']
                logger.info("integration_fixtures.py: sys.modules['jpype._core'] (notre _REAL_JPYPE_MODULE._jpype) supprimé.")
        
        if original_sys_jpype_imports is not None:
            sys.modules['jpype.imports'] = original_sys_jpype_imports
            logger.info("integration_fixtures.py: sys.modules['jpype.imports'] restauré.")
        elif 'jpype.imports' in sys.modules and hasattr(_REAL_JPYPE_MODULE, 'imports') and sys.modules['jpype.imports'] is _REAL_JPYPE_MODULE.imports:
            if _REAL_JPYPE_MODULE.imports is not getattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'imports', None):
                del sys.modules['jpype.imports']
                logger.info("integration_fixtures.py: sys.modules['jpype.imports'] (notre _REAL_JPYPE_MODULE.imports) supprimé.")
        logger.info("integration_fixtures.py: Fin de la fixture integration_jvm.")


# Fixtures pour les classes Tweety (nécessitent une JVM active via integration_jvm)
@pytest.fixture(scope="session")
def dung_classes(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour dung_classes.")
    JClass = integration_jvm.JClass
    return {
        "DungTheory": JClass("net.sf.tweety.arg.dung.DungTheory"),
        "Argument": JClass("net.sf.tweety.arg.dung.syntax.Argument"),
        "Attack": JClass("net.sf.tweety.arg.dung.syntax.Attack"),
        "StableExtension": JClass("net.sf.tweety.arg.dung.semantics.StableExtension"),
        "PreferredExtension": JClass("net.sf.tweety.arg.dung.semantics.PreferredExtension"),
        "GroundedExtension": JClass("net.sf.tweety.arg.dung.semantics.GroundedExtension"),
        "CompleteExtension": JClass("net.sf.tweety.arg.dung.semantics.CompleteExtension"),
        "AbstractExtensionReasoner": JClass("net.sf.tweety.arg.dung.reasoner.AbstractExtensionReasoner"),
        "SimpleDungReasoner": JClass("net.sf.tweety.arg.dung.reasoner.SimpleDungReasoner")
    }

@pytest.fixture(scope="session")
def dl_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour dl_syntax_parser.")
    return integration_jvm.JClass("net.sf.tweety.logics.dl.parser.DlParser")

@pytest.fixture(scope="session")
def fol_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour fol_syntax_parser.")
    return integration_jvm.JClass("net.sf.tweety.logics.fol.parser.FolParser")

@pytest.fixture(scope="session")
def pl_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour pl_syntax_parser.")
    return integration_jvm.JClass("net.sf.tweety.logics.pl.parser.PlParser")

@pytest.fixture(scope="session")
def cl_syntax_parser(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour cl_syntax_parser.")
    return integration_jvm.JClass("net.sf.tweety.logics.cl.parser.ClParser")


@pytest.fixture(scope="session")
def tweety_logics_classes(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_logics_classes.")
    JClass = integration_jvm.JClass
    return {
        # Propositional Logic
        "PlBeliefSet": JClass("net.sf.tweety.logics.pl.syntax.PlBeliefSet"),
        "PropositionalSignature": JClass("net.sf.tweety.logics.pl.syntax.PropositionalSignature"),
        "Proposition": JClass("net.sf.tweety.logics.pl.syntax.Proposition"),
        "PlReasoner": JClass("net.sf.tweety.logics.pl.reasoner.PlReasoner"), # Interface
        "SatReasoner": JClass("net.sf.tweety.logics.pl.reasoner.SatReasoner"),
        "PlParser": JClass("net.sf.tweety.logics.pl.parser.PlParser"),
        # First-Order Logic
        "FolBeliefSet": JClass("net.sf.tweety.logics.fol.syntax.FolBeliefSet"),
        "FolSignature": JClass("net.sf.tweety.logics.fol.syntax.FolSignature"),
        "FolParser": JClass("net.sf.tweety.logics.fol.parser.FolParser"),
        "Prover9Reasoner": JClass("net.sf.tweety.logics.fol.reasoner.Prover9Reasoner"),
        # Conditional Logic
        "ClBeliefSet": JClass("net.sf.tweety.logics.cl.syntax.ClBeliefSet"),
        "Conditional": JClass("net.sf.tweety.logics.cl.syntax.Conditional"),
        "ClParser": JClass("net.sf.tweety.logics.cl.parser.ClParser"),
        "ZReasoner": JClass("net.sf.tweety.logics.cl.reasoner.ZReasoner"),
        # Description Logic
        "DlBeliefSet": JClass("net.sf.tweety.logics.dl.syntax.DlBeliefSet"),
        "DescriptionLogicSignature": JClass("net.sf.tweety.logics.dl.syntax.DescriptionLogicSignature"),
        "DlParser": JClass("net.sf.tweety.logics.dl.parser.DlParser"),
        "PelletReasoner": JClass("net.sf.tweety.logics.dl.reasoner.PelletReasoner"),
        # ASP
        "AspBeliefSet": JClass("net.sf.tweety.logics.asp.syntax.AspBeliefSet"),
        "DLVReasoner": JClass("net.sf.tweety.logics.asp.reasoner.DLVReasoner"),
        "ClingoReasoner": JClass("net.sf.tweety.logics.asp.reasoner.ClingoReasoner"),
        # General
        "BeliefSet": JClass("net.sf.tweety.commons.BeliefSet"),
        "Formula": JClass("net.sf.tweety.logics.commons.syntax.Formula"),
        "Signature": JClass("net.sf.tweety.logics.commons.syntax.Signature"),
        "Reasoner": JClass("net.sf.tweety.logics.commons.reasoner.Reasoner"), # Interface
        "QueryResult": JClass("net.sf.tweety.logics.commons.reasoner.QueryResult"),
        # Argumentation
        "ProbabilisticArgumentationFramework": JClass("net.sf.tweety.arg.prob.ProbabilisticArgumentationFramework"),
        "ProbabilisticFact": JClass("net.sf.tweety.arg.prob.ProbabilisticFact"),
        "ProbabilisticReasoner": JClass("net.sf.tweety.arg.prob.reasoner.ProbabilisticReasoner"),
        "EpistemicProbabilityReasoner": JClass("net.sf.tweety.arg.prob.reasoner.EpistemicProbabilityReasoner"),
        "DungTheory": JClass("net.sf.tweety.arg.dung.DungTheory"), # Répété de dung_classes pour complétude
        "Argument": JClass("net.sf.tweety.arg.dung.syntax.Argument"),
        "Attack": JClass("net.sf.tweety.arg.dung.syntax.Attack"),
        "SimpleDungReasoner": JClass("net.sf.tweety.arg.dung.reasoner.SimpleDungReasoner"),
        # Belief Revision
        "RevisionOperator": JClass("net.sf.tweety.beliefdynamics.RevisionOperator"), # Interface
        "DalalRevision": JClass("net.sf.tweety.beliefdynamics.revops.DalalRevision"),
        # Other useful classes
        "ArrayList": JClass("java.util.ArrayList"),
        "HashSet": JClass("java.util.HashSet"),
        "File": JClass("java.io.File"),
        "System": JClass("java.lang.System"),
        "TweetyConfiguration": JClass("net.sf.tweety.commons.TweetyConfiguration"),
    }

@pytest.fixture(scope="session")
def tweety_string_utils(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_string_utils.")
    return integration_jvm.JClass("net.sf.tweety.commons.util.string.StringUtils")

@pytest.fixture(scope="session")
def tweety_math_utils(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_math_utils.")
    return integration_jvm.JClass("net.sf.tweety.math.util.MathUtils")

@pytest.fixture(scope="session")
def tweety_probability(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_probability.")
    return integration_jvm.JClass("net.sf.tweety.math.probability.Probability")

@pytest.fixture(scope="session")
def tweety_conditional_probability(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_conditional_probability.")
    return integration_jvm.JClass("net.sf.tweety.math.probability.ConditionalProbability")

@pytest.fixture(scope="session")
def tweety_parser_exception(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_parser_exception.")
    return integration_jvm.JClass("net.sf.tweety.parsers.ParserException")

@pytest.fixture(scope="session")
def tweety_io_exception(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_io_exception.")
    return integration_jvm.JClass("java.io.IOException")

@pytest.fixture(scope="session")
def tweety_qbf_classes(integration_jvm):
    if integration_jvm is None: pytest.skip("JVM non disponible pour tweety_qbf_classes.")
    JClass = integration_jvm.JClass
    return {
        "QuantifiedBooleanFormula": JClass("net.sf.tweety.logics.qbf.syntax.QuantifiedBooleanFormula"),
        "QbfNode": JClass("net.sf.tweety.logics.qbf.syntax.QbfNode"),
        "ExistsQuantifiedFormula": JClass("net.sf.tweety.logics.qbf.syntax.ExistsQuantifiedFormula"),
        "ForAllQuantifiedFormula": JClass("net.sf.tweety.logics.qbf.syntax.ForAllQuantifiedFormula"),
        "QbfReasoner": JClass("net.sf.tweety.logics.qbf.reasoner.QbfReasoner"), # Interface
        "CAQEReasoner": JClass("net.sf.tweety.logics.qbf.reasoner.CAQEReasoner"),
        "QbfParser": JClass("net.sf.tweety.logics.qbf.parser.QbfParser")
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
    
    # _REAL_JPYPE_MODULE est importé au début de ce fichier
    # logger.info(f"integration_fixtures.py: belief_revision_classes - _REAL_JPYPE_MODULE (ID: {id(_REAL_JPYPE_MODULE)})")

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
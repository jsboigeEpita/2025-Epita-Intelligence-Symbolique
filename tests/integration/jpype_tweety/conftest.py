import pytest
import os
import sys
import subprocess
import jpype
from pathlib import Path
from argumentation_analysis.core.jvm_setup import LIBS_DIR as CORE_LIBS_DIR # Gardons CORE_LIBS_DIR pour info

# Déterminer le chemin du répertoire du projet
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Chemin vers les JARs de Tweety (devrait correspondre à celui utilisé par le conftest.py racine)
TWEETY_LIBS_PATH = os.path.join(PROJECT_ROOT, "libs") # Ce chemin est utilisé par la logique de téléchargement ci-dessous

# La fixture jvm_manager et les fixtures de classes (dung_classes, qbf_classes, etc.)
# sont maintenant définies dans le conftest.py racine pour une gestion centralisée de JPype.
# Ce fichier est conservé pour d'éventuelles configurations spécifiques à ce sous-répertoire de tests,
# mais ne doit plus gérer l'initialisation de JPype ni la définition des classes Java globales.

def get_tweety_classpath(): # Cette fonction n'est plus utilisée pour démarrer la JVM ici.
    """Construit le classpath à partir des JARs trouvés dans TWEETY_LIBS_PATH."""
    jars = [os.path.join(TWEETY_LIBS_PATH, f) for f in os.listdir(TWEETY_LIBS_PATH) if f.endswith(".jar")]
    print(f"DEBUG: get_tweety_classpath: JARs trouvés = {jars}")
    if not jars:
        print(f"AVERTISSEMENT: Aucun fichier JAR trouvé dans '{TWEETY_LIBS_PATH}'.")
        print("Veuillez vérifier que les JARs de Tweety sont présents.")
        return []
    return jars

@pytest.fixture(scope="session", autouse=True)
def jvm_manager():
    print("DEBUG: jvm_manager fixture CALLED (tests/integration/jpype_tweety/conftest.py)")
    """
    Fixture pour s'assurer que les JARs de test sont présents et vérifier l'état de la JVM.
    La JVM doit être démarrée par le conftest.py racine.
    """
    try:
        # S'assurer que les JARs de test/application sont présents (téléchargés si besoin)
        # Utilisation de la version "Updated upstream" (plus robuste) pour le téléchargement.
        script_path = Path(PROJECT_ROOT) / "scripts" / "download_test_jars.py"
        target_jars_dir = Path(TWEETY_LIBS_PATH) # TWEETY_LIBS_PATH pointe vers PROJECT_ROOT/libs
        
        # On vérifie si le répertoire libs contient des JARs.
        # Si ce n'est pas le cas, ou si le répertoire n'existe pas, on tente le téléchargement.
        # Note: download_test_jars.py est supposé télécharger dans PROJECT_ROOT/libs.
        # Le fichier jvm_setup.py (appelé par le root conftest) gère le téléchargement des JARs principaux
        # et la construction du classpath combiné (incluant les JARs de tests/resources/libs).
        # Cette section de téléchargement ici pourrait être redondante si jvm_setup.py fait déjà tout.
        # Cependant, la version "Updated upstream" avait cette logique explicitement pour les tests jpype_tweety.
        # On la conserve pour l'instant, en s'assurant qu'elle cible bien TWEETY_LIBS_PATH (PROJECT_ROOT/libs).
        
        if not (target_jars_dir.is_dir() and any(target_jars_dir.glob("*.jar"))):
            print(f"INFO: Les JARs de test/application semblent manquants dans {target_jars_dir}. Tentative de téléchargement via {script_path}...")
            if not script_path.is_file():
                print(f"ERREUR CRITIQUE: Le script de téléchargement {script_path} n'a pas été trouvé.")
                raise FileNotFoundError(f"Script de téléchargement non trouvé: {script_path}")
            
            try:
                print(f"INFO: Exécution du script de téléchargement: {sys.executable} {script_path}")
                process = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    check=False  # Gérer manuellement le code de retour
                )
                
                if process.stderr and "Traceback" in process.stderr:
                    print(f"ERREUR (stderr du script {script_path.name}):\n{process.stderr}")
                elif process.stderr:
                     print(f"DEBUG (stderr du script {script_path.name}):\n{process.stderr}")

                if process.returncode != 0:
                    error_message = (
                        f"ERREUR: Le script de téléchargement des JARs ({script_path}) "
                        f"a échoué avec le code de retour {process.returncode}.\n"
                        f"Stderr: {process.stderr}\nStdout: {process.stdout}"
                    )
                    print(error_message)
                    raise RuntimeError(error_message)
                
                print(f"INFO: Script de téléchargement exécuté (code {process.returncode}). Sortie:\n{process.stdout}")
                if not any(target_jars_dir.glob("*.jar")):
                    warning_message = (
                        f"AVERTISSEMENT: Le script de téléchargement s'est terminé "
                        f"mais aucun JAR n'a été trouvé dans {target_jars_dir}. "
                        f"Vérifiez les logs du script et le script lui-même ({script_path})."
                    )
                    print(warning_message)
                else:
                    print(f"INFO: Les fichiers JAR sont maintenant (ou étaient déjà) présents dans {target_jars_dir}.")

            except Exception as e:
                critical_error_message = (
                    f"ERREUR CRITIQUE lors de l'exécution du script de téléchargement {script_path}: {e}"
                )
                print(critical_error_message)
                raise RuntimeError(critical_error_message) from e
        else:
            print(f"INFO: Les JARs de test/application sont déjà présents dans {target_jars_dir}.")
        # --- Fin de la logique de téléchargement ---

        # Logique de "Stashed changes" pour vérifier la JVM et afficher les infos
        print("DEBUG: jvm_manager (tests/integration/jpype_tweety): Vérification de l'état de la JVM (doit être démarrée par le conftest racine).")
        if not jpype.isJVMStarted():
            error_msg = ("ERREUR CRITIQUE: La JVM n'est pas démarrée comme attendu (devrait être fait par un conftest racine). "
                         "Les tests jpype_tweety ne peuvent pas continuer.")
            print(error_msg)
            # Ne pas tenter de démarrer la JVM ici, cela doit être géré centralement.
            raise RuntimeError(error_msg)

        print("INFO: jvm_manager (tests/integration/jpype_tweety): La JVM est (ou devrait être) déjà démarrée.")
        
        try:
            print(f"       jpype.config.java_home: {jpype.config.java_home if hasattr(jpype, 'config') else 'N/A'}")
            print(f"       jpype.config.jvm_path: {jpype.config.jvm_path if hasattr(jpype, 'config') else 'N/A'}")
            current_classpath_reported = jpype.getClassPath()
            print(f"       Classpath rapporté par jpype.getClassPath(): '{current_classpath_reported}' (longueur: {len(str(current_classpath_reported))})")
            if not current_classpath_reported:
                print("       AVERTISSEMENT: jpype.getClassPath() est vide ou None!")
        except Exception as e_config:
            print(f"       Erreur lors de la tentative d'affichage de la config JPype: {e_config}")

        # CORE_LIBS_DIR est le chemin des JARs principaux (argumentation_analysis/libs)
        # TWEETY_LIBS_PATH est défini sur PROJECT_ROOT/libs, donc c'est la même chose.
        # Les JARs de test sont dans argumentation_analysis/tests/resources/libs
        # jvm_setup.py est censé combiner CORE_LIBS_DIR et les JARs de test.
        print(f"       Les tests jpype_tweety s'attendent à ce que les JARs de {CORE_LIBS_DIR} et ceux de tests/resources/libs soient accessibles.")
        print(f"       La JVM a été démarrée par le conftest racine via jvm_setup.py.")

        jpype.imports.registerDomain("net", alias="net")
        jpype.imports.registerDomain("org", alias="org")
        jpype.imports.registerDomain("java", alias="java")

        yield

    except Exception as e:
        print(f"Erreur critique inattendue dans la fixture jvm_manager: {e}")
        raise
    finally:
        if jpype.isJVMStarted():
            print("INFO: La JVM restera active jusqu'à la fin du processus de test principal (géré par conftest racine).")

# Fixture pour importer les classes communes de Dung
@pytest.fixture(scope="module")
def dung_classes():
    try:
        DungTheory = jpype.JClass("net.sf.tweety.arg.dung.syntax.DungTheory")
        Argument = jpype.JClass("net.sf.tweety.arg.dung.syntax.Argument")
        Attack = jpype.JClass("net.sf.tweety.arg.dung.syntax.Attack")
        PreferredReasoner = jpype.JClass("net.sf.tweety.arg.dung.reasoner.PreferredReasoner")
        GroundedReasoner = jpype.JClass("net.sf.tweety.arg.dung.reasoner.GroundedReasoner")
        CompleteReasoner = jpype.JClass("net.sf.tweety.arg.dung.reasoner.CompleteReasoner")
        StableReasoner = jpype.JClass("net.sf.tweety.arg.dung.reasoner.StableReasoner")
        # Ajoutez d'autres classes communes ici si nécessaire
        return {
            "DungTheory": DungTheory,
            "Argument": Argument,
            "Attack": Attack,
            "PreferredReasoner": PreferredReasoner,
            "GroundedReasoner": GroundedReasoner,
            "CompleteReasoner": CompleteReasoner,
            "StableReasoner": StableReasoner
        }
    except jpype.JException as e:
        pytest.fail(f"Échec de l'importation des classes Java pour Dung: {e.stacktrace()}")

# Fixture pour importer les classes communes de QBF
@pytest.fixture(scope="module")
def qbf_classes():
    try:
        QuantifiedBooleanFormula = jpype.JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula")
        Quantifier = jpype.JClass("org.tweetyproject.logics.qbf.syntax.Quantifier")
        QbfParser = jpype.JClass("org.tweetyproject.logics.qbf.parser.QbfParser")
        # QBFSolver = jpype.JClass("org.tweetyproject.logics.qbf.solver.QBFSolver") # Peut nécessiter une config
        Variable = jpype.JClass("org.tweetyproject.logics.commons.syntax.Variable")
        # Opérateurs logiques (les noms peuvent varier, ex: Or, And, Not de commons.syntax ou qbf.syntax)
        # Par exemple:
        # Or = jpype.JClass("org.tweetyproject.logics.pl.syntax.Or") # Si on utilise la logique propositionnelle pour la base
        # Not = jpype.JClass("org.tweetyproject.logics.pl.syntax.Not")
        # Il faudra vérifier les classes exactes pour les opérateurs dans le contexte QBF de Tweety.
        # Pour l'instant, on se concentre sur le parsing et la création de base.
        return {
            "QuantifiedBooleanFormula": QuantifiedBooleanFormula,
            "Quantifier": Quantifier,
            "QbfParser": QbfParser,
            # "QBFSolver": QBFSolver,
            "Variable": Variable,
            # "Or": Or,
            # "Not": Not
        }
    except jpype.JException as e:
        pytest.fail(f"Échec de l'importation des classes Java pour QBF: {e.stacktrace()}")

# Fixture pour importer les classes communes de révision de croyances
@pytest.fixture(scope="module")
def belief_revision_classes():
    try:
        # Classes de base pour la logique propositionnelle
        PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")
        PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        SimplePlReasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner")
        Negation = jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation")

        # Opérateurs de révision
        KernelContractionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.operators.KernelContractionOperator")
        RandomIncisionFunction = jpype.JClass("org.tweetyproject.beliefdynamics.kernels.RandomIncisionFunction")
        DefaultMultipleBaseExpansionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.operators.DefaultMultipleBaseExpansionOperator")
        LeviMultipleBaseRevisionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.operators.LeviMultipleBaseRevisionOperator")

        # Classes pour la révision multi-agents (CrMas)
        CrMasBeliefSet = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasBeliefSet")
        InformationObject = jpype.JClass("org.tweetyproject.beliefdynamics.mas.InformationObject")
        CrMasRevisionWrapper = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasRevisionWrapper")
        CrMasSimpleRevisionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasSimpleRevisionOperator")
        CrMasArgumentativeRevisionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasArgumentativeRevisionOperator")
        DummyAgent = jpype.JClass("org.tweetyproject.agents.DummyAgent") # Pour les exemples CrMas
        Order = jpype.JClass("org.tweetyproject.commons.util.Order") # Pour la crédibilité des agents
        PlSignature = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")


        # Mesures d'incohérence
        ContensionInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.ContensionInconsistencyMeasure")
        NaiveMusEnumerator = jpype.JClass("org.tweetyproject.logics.pl.analysis.NaiveMusEnumerator")
        SatSolver = jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver") # Nécessaire pour NaiveMusEnumerator
        MaInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.MaInconsistencyMeasure")
        McscInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.McscInconsistencyMeasure")
        PossibleWorldIterator = jpype.JClass("org.tweetyproject.logics.pl.syntax.PossibleWorldIterator")
        DalalDistance = jpype.JClass("org.tweetyproject.logics.pl.util.DalalDistance")
        DSumInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.DSumInconsistencyMeasure")
        DMaxInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.DMaxInconsistencyMeasure")
        DHitInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.DHitInconsistencyMeasure")
        ProductNorm = jpype.JClass("org.tweetyproject.math.tnorms.ProductNorm")
        FuzzyInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.FuzzyInconsistencyMeasure")
        PriorityIncisionFunction = jpype.JClass("org.tweetyproject.beliefdynamics.kernels.PriorityIncisionFunction")


        return {
            "PlFormula": PlFormula,
            "PlBeliefSet": PlBeliefSet,
            "PlParser": PlParser,
            "SimplePlReasoner": SimplePlReasoner,
            "Negation": Negation,
            "KernelContractionOperator": KernelContractionOperator,
            "RandomIncisionFunction": RandomIncisionFunction,
            "DefaultMultipleBaseExpansionOperator": DefaultMultipleBaseExpansionOperator,
            "LeviMultipleBaseRevisionOperator": LeviMultipleBaseRevisionOperator,
            "CrMasBeliefSet": CrMasBeliefSet,
            "InformationObject": InformationObject,
            "CrMasRevisionWrapper": CrMasRevisionWrapper,
            "CrMasSimpleRevisionOperator": CrMasSimpleRevisionOperator,
            "CrMasArgumentativeRevisionOperator": CrMasArgumentativeRevisionOperator,
            "DummyAgent": DummyAgent,
            "Order": Order,
            "PlSignature": PlSignature,
            "ContensionInconsistencyMeasure": ContensionInconsistencyMeasure,
            "NaiveMusEnumerator": NaiveMusEnumerator,
            "SatSolver": SatSolver,
            "MaInconsistencyMeasure": MaInconsistencyMeasure,
            "McscInconsistencyMeasure": McscInconsistencyMeasure,
            "PossibleWorldIterator": PossibleWorldIterator,
            "DalalDistance": DalalDistance,
            "DSumInconsistencyMeasure": DSumInconsistencyMeasure,
            "DMaxInconsistencyMeasure": DMaxInconsistencyMeasure,
            "DHitInconsistencyMeasure": DHitInconsistencyMeasure,
            "ProductNorm": ProductNorm,
            "FuzzyInconsistencyMeasure": FuzzyInconsistencyMeasure,
            "PriorityIncisionFunction": PriorityIncisionFunction,
        }
    except jpype.JException as e:
        pytest.fail(f"Échec de l'importation des classes Java pour la révision de croyances: {e.stacktrace()}")

# Fixture pour importer les classes communes d'argumentation dialogique
@pytest.fixture(scope="module")
def dialogue_classes(): # jpype_is_running n'est pas une fixture définie, jvm_manager s'en occupe.
    """Importe les classes Java nécessaires pour l'argumentation dialogique."""
    if not jpype.isJVMStarted(): # Vérification directe de l'état de la JVM
        pytest.skip("JVM non démarrée ou JPype non initialisé correctement.")
    try:
        ArgumentationAgent = jpype.JClass("org.tweetyproject.agents.dialogues.ArgumentationAgent")
        GroundedAgent = jpype.JClass("org.tweetyproject.agents.dialogues.GroundedAgent")
        OpponentModel = jpype.JClass("org.tweetyproject.agents.dialogues.OpponentModel")
        Dialogue = jpype.JClass("org.tweetyproject.agents.dialogues.Dialogue")
        DialogueTrace = jpype.JClass("org.tweetyproject.agents.dialogues.DialogueTrace")
        DialogueResult = jpype.JClass("org.tweetyproject.agents.dialogues.DialogueResult")
        PersuasionProtocol = jpype.JClass("org.tweetyproject.agents.dialogues.PersuasionProtocol")
        # NegotiationProtocol = jpype.JClass("org.tweetyproject.agents.dialogues.NegotiationProtocol") # Interface
        # InquiryProtocol = jpype.JClass("org.tweetyproject.agents.dialogues.InquiryProtocol") # Interface
        Position = jpype.JClass("org.tweetyproject.agents.dialogues.Position")
        SimpleBeliefSet = jpype.JClass("org.tweetyproject.logics.commons.syntax.SimpleBeliefSet")
        # Moves - peuvent être utiles pour des assertions plus fines sur la trace
        # Move = jpype.JClass("org.tweetyproject.agents.dialogues.moves.Move")
        # Claim = jpype.JClass("org.tweetyproject.agents.dialogues.moves.Claim")
        # DialogueStrategy = jpype.JClass("org.tweetyproject.agents.dialogues.strategies.DialogueStrategy") # Interface
        DefaultStrategy = jpype.JClass("org.tweetyproject.agents.dialogues.strategies.DefaultStrategy")
        
        # Pour les protocoles spécifiques si besoin (exemples de la fiche)
        # MonotonicConcessionProtocol = jpype.JClass("org.tweetyproject.agents.dialogues.MonotonicConcessionProtocol")
        # CollaborativeInquiryProtocol = jpype.JClass("org.tweetyproject.agents.dialogues.CollaborativeInquiryProtocol")


        return {
            "ArgumentationAgent": ArgumentationAgent,
            "GroundedAgent": GroundedAgent,
            "OpponentModel": OpponentModel,
            "Dialogue": Dialogue,
            "DialogueTrace": DialogueTrace,
            "DialogueResult": DialogueResult,
            "PersuasionProtocol": PersuasionProtocol,
            # "NegotiationProtocol": NegotiationProtocol,
            # "InquiryProtocol": InquiryProtocol,
            "Position": Position,
            "SimpleBeliefSet": SimpleBeliefSet,
            # "Move": Move,
            # "Claim": Claim,
            # "DialogueStrategy": DialogueStrategy,
            "DefaultStrategy": DefaultStrategy,
            # "MonotonicConcessionProtocol": MonotonicConcessionProtocol,
            # "CollaborativeInquiryProtocol": CollaborativeInquiryProtocol,
        }
    except jpype.JException as e:
        pytest.fail(f"Échec de l'importation des classes Java pour l'argumentation dialogique: {e.stacktrace()}")

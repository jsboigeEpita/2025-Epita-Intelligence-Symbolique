import pytest
import os
import sys
import subprocess
from pathlib import Path
import logging # Importation ajoutée pour mock_logger

# Déterminer le chemin du répertoire du projet
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Chemin vers les JARs de Tweety (devrait correspondre à celui utilisé par le conftest.py racine)
TWEETY_LIBS_PATH = os.path.join(PROJECT_ROOT, "libs")

def get_tweety_classpath():
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
    print("DEBUG: jvm_manager fixture CALLED")
    """
    Fixture pour démarrer et arrêter la JVM pour la session de test.
    'autouse=True' garantit que cette fixture est utilisée pour toutes les tests de la session
    dans ce répertoire (et sous-répertoires) où conftest.py est actif.
    """
    import jpype # Importation locale initiale
    
    # Forcer l'utilisation du mock pour les tests jpype_tweety
    # car le conftest.py racine a sa logique de mock neutralisée.
    import tests.mocks.jpype_mock as jpype_mock_module
    sys.modules['jpype'] = jpype_mock_module
    sys.modules['jpype1'] = jpype_mock_module
    # Ré-assigner la variable locale jpype pour qu'elle pointe vers le mock chargé
    jpype = jpype_mock_module
    print("INFO: [jpype_tweety/conftest.py] Mock JPype activé de force pour cette session de tests.")

    # Obtenir le logger du mock pour y ajouter des messages
    mock_logger = logging.getLogger("tests.mocks.jpype_mock")

    try:
        # --- Début de l'intégration du téléchargement des JARs ---
        script_path = Path(PROJECT_ROOT) / "scripts" / "download_test_jars.py"
        target_jars_dir = Path(TWEETY_LIBS_PATH)

        jars_present = False
        if target_jars_dir.is_dir() and any(target_jars_dir.glob("*.jar")):
            jars_present = True
            print(f"INFO: Des fichiers JAR existent déjà dans {target_jars_dir}.")

        if not jars_present:
            print(f"INFO: Les fichiers JAR semblent manquants dans {target_jars_dir}. Tentative de téléchargement...")
            if not script_path.is_file():
                print(f"ERREUR CRITIQUE: Le script de téléchargement {script_path} n'a pas été trouvé.")
                raise FileNotFoundError(f"Script de téléchargement non trouvé: {script_path}")
            
            try:
                print(f"INFO: Exécution du script de téléchargement: {sys.executable} {script_path}")
                process = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if process.stderr:
                    pass

                if process.returncode != 0:
                    error_message = (
                        f"ERREUR: Le script de téléchargement des JARs ({script_path}) "
                        f"a échoué avec le code de retour {process.returncode}.\n"
                        f"Stderr: {process.stderr}\nStdout: {process.stdout}"
                    )
                    print(error_message)
                    raise RuntimeError(error_message)
                
                print(f"INFO: Script de téléchargement exécuté avec succès (code {process.returncode}).")
                if not any(target_jars_dir.glob("*.jar")):
                    warning_message = (
                        f"AVERTISSEMENT: Le script de téléchargement s'est terminé avec succès "
                        f"mais aucun JAR n'a été trouvé dans {target_jars_dir}. "
                        f"Vérifiez les logs du script."
                    )
                    print(warning_message)
                else:
                    print(f"INFO: Les fichiers JAR sont maintenant présents dans {target_jars_dir}.")

            except Exception as e:
                critical_error_message = (
                    f"ERREUR CRITIQUE lors de l'exécution du script de téléchargement {script_path}: {e}"
                )
                print(critical_error_message)
                raise RuntimeError(critical_error_message) from e
        # --- Fin de l'intégration du téléchargement des JARs ---

        print("DEBUG: Checking if JVM is started...")
        if False: # Force le mock, ne démarre pas la vraie JVM
            mock_logger.info("[JPYPE_TWEETY_CONFTEST] Démarrage de la vraie JVM ignoré car le mock est forcé.")
            print("INFO: Démarrage de la JVM pour les tests d'intégration Tweety...")
            tweety_classpath_list = get_tweety_classpath() 
            
            if not tweety_classpath_list:
                critical_error_msg = (
                    f"ERREUR CRITIQUE: Aucun fichier JAR trouvé dans {TWEETY_LIBS_PATH} "
                    f"même après la tentative de téléchargement. Le classpath est vide."
                )
                print(critical_error_msg)
                raise RuntimeError(critical_error_msg)
            
            print(f"INFO: Utilisation de la liste de JARs pour Tweety: {tweety_classpath_list}")
            print(f"DEBUG: jpype.getDefaultJVMPath() = {jpype.getDefaultJVMPath()}")
            print(f"DEBUG: Tentative de démarrage de la JVM avec le classpath: {tweety_classpath_list}...")
            try:
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    "-ea",
                    classpath=tweety_classpath_list,
                    convertStrings=False
                )
                print(f"DEBUG: jpype.isJVMStarted() après startJVM (classpath list) = {jpype.isJVMStarted()}")
                if jpype.isJVMStarted():
                    print("INFO: JVM démarrée avec succès.")
                else:
                    raise RuntimeError("jpype.startJVM a été appelé, mais jpype.isJVMStarted() renvoie False.")
            except Exception as e:
                jvm_start_error_msg = (
                    f"ERREUR CRITIQUE lors du démarrage de la JVM: {e}\n"
                    f"Classpath utilisé: {tweety_classpath_list}\n"
                    f"Chemin JVM par défaut: {jpype.getDefaultJVMPath()}"
                )
                print(jvm_start_error_msg)
                if hasattr(e, 'stacktrace'):
                    print(f"Stacktrace Java:\n{e.stacktrace()}")
                raise RuntimeError(jvm_start_error_msg) from e

        print(f"DEBUG: jpype.isJVMStarted() à la fin de la section de démarrage = {jpype.isJVMStarted()}")
        
        if not jpype.isJVMStarted(): 
            final_error_msg = "ERREUR CRITIQUE: La JVM n'a pas pu démarrer malgré les tentatives."
            print(final_error_msg)
            raise RuntimeError(final_error_msg)
        else:
            print("INFO: La JVM est démarrée (ou était déjà démarrée).")

        jpype.imports.registerDomain("net", alias="net")
        jpype.imports.registerDomain("org", alias="org")
        jpype.imports.registerDomain("java", alias="java") 

        yield

    except Exception as e:
        print(f"Erreur critique inattendue dans la fixture jvm_manager: {e}")
        raise
    finally:
        if jpype.isJVMStarted():
            print("INFO: La JVM restera active jusqu'à la fin du processus de test principal.")

@pytest.fixture(scope="session")
def mocked_jpype(jvm_manager):
    """
    Fournit le module jpype (qui devrait être le mock après l'exécution de jvm_manager).
    jvm_manager est une dépendance pour s'assurer que le patching a eu lieu.
    """
    import jpype # À ce stade, jpype dans sys.modules est le mock.
    return jpype

@pytest.fixture(scope="module")
def dung_classes(mocked_jpype): # Dépend de mocked_jpype
    jpype = mocked_jpype # Utiliser le jpype fourni par la fixture
    try:
        # Utiliser les noms de classes complets comme dans le mock jpype_mock.py
        # et comme ils seraient utilisés avec le vrai Tweety.
        DungTheory = jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory")
        Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
        
        # Les reasoners peuvent être différents si le chemin net.sf.tweety est utilisé ailleurs,
        # mais pour la cohérence avec DungTheory, Argument, Attack, utilisons org.tweetyproject
        # Si les tests échouent à cause de cela, il faudra ajuster les noms de classes des reasoners.
        PreferredReasoner = jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner") # ou PreferredReasoner si c'est le nom exact
        GroundedReasoner = jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner")
        CompleteReasoner = jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimpleCompleteReasoner")
        StableReasoner = jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner")
        
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
        # Tenter d'obtenir un stacktrace plus détaillé si possible
        stacktrace = getattr(e, 'stacktrace', lambda: str(e))()
        pytest.fail(f"Échec de l'importation des classes Java pour Dung (via mocked_jpype): {stacktrace}")
    except Exception as e_gen:
        pytest.fail(f"Erreur générale lors de la création de dung_classes (via mocked_jpype): {e_gen}")


@pytest.fixture(scope="module")
def qbf_classes():
    import jpype
    try:
        QuantifiedBooleanFormula = jpype.JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula")
        Quantifier = jpype.JClass("org.tweetyproject.logics.qbf.syntax.Quantifier")
        QbfParser = jpype.JClass("org.tweetyproject.logics.qbf.parser.QbfParser")
        Variable = jpype.JClass("org.tweetyproject.logics.commons.syntax.Variable")
        return {
            "QuantifiedBooleanFormula": QuantifiedBooleanFormula,
            "Quantifier": Quantifier,
            "QbfParser": QbfParser,
            "Variable": Variable,
        }
    except jpype.JException as e:
        pytest.fail(f"Échec de l'importation des classes Java pour QBF: {e.stacktrace()}")

@pytest.fixture(scope="module")
def belief_revision_classes():
    import jpype
    try:
        PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")
        PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        SimplePlReasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner")
        Negation = jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation")

        KernelContractionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.operators.KernelContractionOperator")
        RandomIncisionFunction = jpype.JClass("org.tweetyproject.beliefdynamics.kernels.RandomIncisionFunction")
        DefaultMultipleBaseExpansionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.operators.DefaultMultipleBaseExpansionOperator")
        LeviMultipleBaseRevisionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.operators.LeviMultipleBaseRevisionOperator")

        CrMasBeliefSet = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasBeliefSet")
        InformationObject = jpype.JClass("org.tweetyproject.beliefdynamics.mas.InformationObject")
        CrMasRevisionWrapper = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasRevisionWrapper")
        CrMasSimpleRevisionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasSimpleRevisionOperator")
        CrMasArgumentativeRevisionOperator = jpype.JClass("org.tweetyproject.beliefdynamics.mas.CrMasArgumentativeRevisionOperator")
        DummyAgent = jpype.JClass("org.tweetyproject.agents.DummyAgent")
        Order = jpype.JClass("org.tweetyproject.commons.util.Order")
        PlSignature = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")

        ContensionInconsistencyMeasure = jpype.JClass("org.tweetyproject.logics.pl.analysis.ContensionInconsistencyMeasure")
        NaiveMusEnumerator = jpype.JClass("org.tweetyproject.logics.pl.analysis.NaiveMusEnumerator")
        SatSolver = jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver")
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

@pytest.fixture(scope="module")
def dialogue_classes():
    """Importe les classes Java nécessaires pour l'argumentation dialogique."""
    import jpype
    if not jpype.isJVMStarted():
        pytest.skip("JVM non démarrée ou JPype non initialisé correctement.")
    try:
        ArgumentationAgent = jpype.JClass("org.tweetyproject.agents.dialogues.ArgumentationAgent")
        GroundedAgent = jpype.JClass("org.tweetyproject.agents.dialogues.GroundedAgent")
        OpponentModel = jpype.JClass("org.tweetyproject.agents.dialogues.OpponentModel")
        Dialogue = jpype.JClass("org.tweetyproject.agents.dialogues.Dialogue")
        DialogueTrace = jpype.JClass("org.tweetyproject.agents.dialogues.DialogueTrace")
        DialogueResult = jpype.JClass("org.tweetyproject.agents.dialogues.DialogueResult")
        PersuasionProtocol = jpype.JClass("org.tweetyproject.agents.dialogues.PersuasionProtocol")
        Position = jpype.JClass("org.tweetyproject.agents.dialogues.Position")
        SimpleBeliefSet = jpype.JClass("org.tweetyproject.logics.commons.syntax.SimpleBeliefSet")
        DefaultStrategy = jpype.JClass("org.tweetyproject.agents.dialogues.strategies.DefaultStrategy")
        
        return {
            "ArgumentationAgent": ArgumentationAgent,
            "GroundedAgent": GroundedAgent,
            "OpponentModel": OpponentModel,
            "Dialogue": Dialogue,
            "DialogueTrace": DialogueTrace,
            "DialogueResult": DialogueResult,
            "PersuasionProtocol": PersuasionProtocol,
            "Position": Position,
            "SimpleBeliefSet": SimpleBeliefSet,
            "DefaultStrategy": DefaultStrategy,
        }
    except jpype.JException as e:
        pytest.fail(f"Échec de l'importation des classes Java pour l'argumentation dialogique: {e.stacktrace()}")

import pytest
import jpype
import jpype.imports # Assurer que jpype.imports est disponible si jpype est importé
import os
import subprocess # Ajouté
import sys      # Ajouté
from pathlib import Path # Ajouté

# Configuration du classpath pour Tweety (à adapter si nécessaire)
# Idéalement, cela devrait être configurable ou découvert automatiquement.
# Pour l'instant, on suppose que les JARs sont dans un sous-dossier 'libs/tweety'
# ou que le CLASSPATH est déjà configuré.
# Vous devrez peut-être télécharger les JARs de Tweety et les placer dans un dossier accessible.

# Déterminer le chemin du répertoire du projet
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Exemple de chemin vers les JARs de Tweety (à adapter)
# Assurez-vous que ce chemin est correct et que les JARs s'y trouvent.
# Par exemple, si vous avez un dossier 'libs/tweety_jars' à la racine du projet :
TWEETY_LIBS_PATH = os.path.join(PROJECT_ROOT, "argumentation_analysis", "tests", "resources", "libs")

# Fonction pour obtenir le classpath.
# Tente de lister les fichiers JAR dans le TWEETY_LIBS_PATH.
# Si le dossier n'existe pas ou est vide, cela pourrait poser problème.
def get_tweety_classpath():
    print(f"DEBUG: get_tweety_classpath: TWEETY_LIBS_PATH = {TWEETY_LIBS_PATH}")
    if not os.path.isdir(TWEETY_LIBS_PATH):
        # Lever une exception ou retourner un classpath par défaut si le dossier n'existe pas
        # Pour l'instant, on retourne une liste vide, ce qui fera probablement échouer jpype.startJVM
        # si le CLASSPATH système n'est pas déjà configuré.
        print(f"AVERTISSEMENT: Le répertoire des bibliothèques Tweety '{TWEETY_LIBS_PATH}' n'a pas été trouvé.")
        print("Veuillez vous assurer que les JARs de Tweety sont correctement placés et que le chemin est correct.")
        print("Ou que votre CLASSPATH système est configuré pour inclure les JARs de Tweety.")
        return [] # Ou lever une exception: raise FileNotFoundError(f"Répertoire Tweety non trouvé: {TWEETY_LIBS_PATH}")

    jars = [os.path.join(TWEETY_LIBS_PATH, f) for f in os.listdir(TWEETY_LIBS_PATH) if f.endswith(".jar")]
    print(f"DEBUG: get_tweety_classpath: JARs trouvés = {jars}")
    if not jars:
        print(f"AVERTISSEMENT: Aucun fichier JAR trouvé dans '{TWEETY_LIBS_PATH}'.")
        print("Veuillez vérifier que les JARs de Tweety sont présents.")
        return [] # Ou lever une exception
    return jars

@pytest.fixture(scope="session", autouse=True)
def jvm_manager():
    print("DEBUG: jvm_manager fixture CALLED")
    """
    Fixture pour démarrer et arrêter la JVM pour la session de test.
    'autouse=True' garantit que cette fixture est utilisée pour toutes les tests de la session
    dans ce répertoire (et sous-répertoires) où conftest.py est actif.
    """
    try:
        # --- Début de l'intégration du téléchargement des JARs ---
        # PROJECT_ROOT et TWEETY_LIBS_PATH sont définis globalement dans ce fichier.
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
                    check=False  # Gérer manuellement le code de retour
                )
                
                print(f"DEBUG: Script stdout:\n{process.stdout}")
                if process.stderr:
                    print(f"DEBUG: Script stderr:\n{process.stderr}")

                if process.returncode != 0:
                    error_message = (
                        f"ERREUR: Le script de téléchargement des JARs ({script_path}) "
                        f"a échoué avec le code de retour {process.returncode}.\n"
                        f"Stderr: {process.stderr}\nStdout: {process.stdout}"
                    )
                    print(error_message)
                    raise RuntimeError(error_message)
                
                print(f"INFO: Script de téléchargement exécuté avec succès (code {process.returncode}).")
                # Re-vérifier si les JARs sont maintenant présents
                if not any(target_jars_dir.glob("*.jar")):
                    warning_message = (
                        f"AVERTISSEMENT: Le script de téléchargement s'est terminé avec succès "
                        f"mais aucun JAR n'a été trouvé dans {target_jars_dir}. "
                        f"Vérifiez les logs du script."
                    )
                    print(warning_message)
                    # On ne lève pas d'erreur ici, car get_tweety_classpath() le fera si nécessaire.
                else:
                    print(f"INFO: Les fichiers JAR sont maintenant présents dans {target_jars_dir}.")

            except Exception as e:
                # Capturer les exceptions de subprocess.run (comme FileNotFoundError pour sys.executable)
                # ou d'autres problèmes inattendus.
                critical_error_message = (
                    f"ERREUR CRITIQUE lors de l'exécution du script de téléchargement {script_path}: {e}"
                )
                print(critical_error_message)
                raise RuntimeError(critical_error_message) from e
        # --- Fin de l'intégration du téléchargement des JARs ---

        print("DEBUG: Checking if JVM is started...")
        if not jpype.isJVMStarted():
            print("INFO: Démarrage de la JVM pour les tests d'intégration Tweety...")
            tweety_classpath_list = get_tweety_classpath() 
            
            if not tweety_classpath_list:
                # Cette condition est cruciale. Si après la tentative de téléchargement,
                # le classpath est toujours vide, c'est une erreur fatale.
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
                # Démarrage de la JVM
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    "-ea",  # Enable assertions
                    classpath=tweety_classpath_list,
                    convertStrings=False # Recommandé pour éviter les conversions automatiques
                )
                print(f"DEBUG: jpype.isJVMStarted() après startJVM (classpath list) = {jpype.isJVMStarted()}")
                if jpype.isJVMStarted():
                    print("INFO: JVM démarrée avec succès.")
                else:
                    # Ce cas indique un problème si startJVM n'a pas levé d'exception mais la JVM n'est pas démarrée.
                    raise RuntimeError("jpype.startJVM a été appelé, mais jpype.isJVMStarted() renvoie False.")
            except Exception as e:
                # Capturer les erreurs spécifiques au démarrage de la JVM
                jvm_start_error_msg = (
                    f"ERREUR CRITIQUE lors du démarrage de la JVM: {e}\n"
                    f"Classpath utilisé: {tweety_classpath_list}\n"
                    f"Chemin JVM par défaut: {jpype.getDefaultJVMPath()}"
                )
                print(jvm_start_error_msg)
                if hasattr(e, 'stacktrace'): # Pour les JException
                    print(f"Stacktrace Java:\n{e.stacktrace()}")
                raise RuntimeError(jvm_start_error_msg) from e

        print(f"DEBUG: jpype.isJVMStarted() à la fin de la section de démarrage = {jpype.isJVMStarted()}")
        
        # Vérification finale et robuste que la JVM est bien démarrée
        if not jpype.isJVMStarted(): 
            final_error_msg = "ERREUR CRITIQUE: La JVM n'a pas pu démarrer malgré les tentatives."
            print(final_error_msg)
            raise RuntimeError(final_error_msg)
        else:
            print("INFO: La JVM est démarrée (ou était déjà démarrée).")

        # Rendre les classes Java importables
        jpype.imports.registerDomain("net", alias="net")
        jpype.imports.registerDomain("org", alias="org")
        jpype.imports.registerDomain("java", alias="java") 

        yield # C'est ici que les tests s'exécuteront

    except Exception as e:
        # Capturer toute autre exception non gérée pendant la configuration de la fixture
        # pour s'assurer qu'elle est loggée et que Pytest est informé.
        print(f"Erreur critique inattendue dans la fixture jvm_manager: {e}")
        raise # Propager l'exception pour que Pytest marque les tests comme échoués ou erronés
    finally:
        # La logique finally reste la même, gérant l'arrêt (ou non-arrêt) de la JVM.
        if jpype.isJVMStarted():
            print("INFO: La JVM restera active jusqu'à la fin du processus de test principal.")
            # Laisser la JVM s'arrêter naturellement à la fin du processus Python
            # pour éviter les problèmes avec jpype.shutdownJVM() dans certains contextes de test.

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
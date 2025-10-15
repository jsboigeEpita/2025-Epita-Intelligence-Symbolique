import jpype
import jpype.imports
from jpype.types import JString
import os

# Définition des chemins en dehors de la fonction de test
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIBS_DIR = os.path.join(PROJECT_ROOT, "libs")
NATIVE_LIBS_DIR = os.path.join(LIBS_DIR, "native")

# Inclure tous les JARs du répertoire libs, sauf celui sans "with-dependencies" s'il existe
all_jars_in_libs = [
    os.path.join(LIBS_DIR, f) for f in os.listdir(LIBS_DIR) if f.endswith(".jar")
]
TWEETY_JARS = [
    jar
    for jar in all_jars_in_libs
    if "tweety-full-1.28.jar" != os.path.basename(jar)
    or "with-dependencies" in os.path.basename(jar)
]
jar_simple = os.path.join(LIBS_DIR, "org.tweetyproject.tweety-full-1.28.jar")
jar_with_deps = os.path.join(
    LIBS_DIR, "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
)

if jar_simple in TWEETY_JARS and jar_with_deps in TWEETY_JARS:
    TWEETY_JARS.remove(jar_simple)
    print(f"Removed {jar_simple} to avoid conflict with {jar_with_deps}")

print(f"Dynamically included JARS for test_load_theory: {TWEETY_JARS}")

# Vérifier l'existence de ces JARs spécifiques
for jar_path_check in TWEETY_JARS:
    if not os.path.exists(jar_path_check):
        raise FileNotFoundError(
            f"JAR file {jar_path_check} not found. Please run download_test_jars.py or ensure correct paths."
        )


def test_load_theory(jvm_session):
    """
    Teste le chargement d'une théorie propositionnelle à partir d'un fichier,
    en utilisant une fixture de session pour gérer la JVM.
    """
    try:
        print("Démarrage du test de chargement de théorie...")

        # La fixture jvm_session s'est déjà occupée de démarrer la JVM.
        assert (
            jpype.isJVMStarted()
        ), "La JVM devrait être démarrée par la fixture jvm_session"

        PlBeliefSet = jpype.JClass("net.sf.tweety.logics.pl.syntax.PlBeliefSet")
        PlParser = jpype.JClass("net.sf.tweety.logics.pl.parser.PlParser")

        print("JVM démarrée et classes Tweety chargées via JClass (espérons-le).")

        # Chemin vers le fichier de théorie
        theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
        print(f"Chemin du fichier de théorie : {theory_file_path}")

        if not os.path.exists(theory_file_path):
            raise FileNotFoundError(
                f"Le fichier de théorie {theory_file_path} n'a pas été trouvé."
            )

        # Créer un parser et charger la théorie
        parser = PlParser()
        belief_set = PlBeliefSet()  # Crée un ensemble de croyances vide

        # La méthode parseBeliefBaseFromFile de PlParser prend un java.io.File
        # Nous devons donc créer un objet File Java
        JFile = jpype.JClass("java.io.File")
        java_file = JFile(JString(theory_file_path))

        # Parse le fichier dans l'ensemble de croyances existant
        # La méthode exacte peut varier selon la version de Tweety et le type de logique.
        # Pour la logique propositionnelle (PlBeliefSet), on peut utiliser `add` après avoir parsé des formules,
        # ou une méthode de parsing direct si disponible.
        # Une approche courante est de parser et d'ajouter.
        # Alternativement, certains parsers peuvent retourner directement un BeliefSet.
        # Ici, nous allons essayer de parser le fichier et d'ajouter à belief_set.
        # PlParser.parseBeliefBaseFromFile retourne un BeliefSet, donc on peut l'assigner directement.

        # Tentative de chargement direct
        # Note: La signature exacte peut varier. Vérifiez la documentation de Tweety.
        # Si PlParser().parseBeliefBaseFromFile(java_file) est la bonne méthode:
        parsed_belief_set = parser.parseBeliefBaseFromFile(theory_file_path)

        # Copier les formules dans notre belief_set ou utiliser directement parsed_belief_set
        # Pour cet exemple, nous allons considérer que parsed_belief_set est ce que nous voulons.
        belief_set = parsed_belief_set

        print(f"Théorie chargée avec succès. Nombre de formules : {belief_set.size()}")
        # Vous pouvez ajouter d'autres vérifications ici, par exemple, imprimer les formules
        # print("Formules chargées :")
        # for formula in belief_set:
        #     print(f"- {formula.toString()}")

        print("Test de chargement de théorie RÉUSSI.")

    except Exception as e:
        print(f"Test de chargement de théorie ÉCHOUÉ : {e}")
        import traceback

        traceback.print_exc()
        # pytest se chargera de lever l'exception
        raise e

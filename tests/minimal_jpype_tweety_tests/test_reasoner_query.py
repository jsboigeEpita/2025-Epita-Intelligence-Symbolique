import os
import jpype  # Déplacé ici
import jpype.imports  # Idem
from jpype.types import JString  # Idem

# from jpype.types import JString # Sera importé si nécessaire

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

print(f"Dynamically included JARS for test_reasoner_query: {TWEETY_JARS}")

# Vérifier l'existence de ces JARs spécifiques
for jar_path_check in TWEETY_JARS:
    if not os.path.exists(jar_path_check):
        raise FileNotFoundError(
            f"JAR file {jar_path_check} not found. Please run download_test_jars.py or ensure correct paths."
        )


def test_reasoner_query(jvm_session):
    """
    Teste un raisonneur PL simple et une requête, en utilisant une fixture
    de session pour gérer la JVM.
    """
    try:
        print("Démarrage du test du raisonneur et de requête simple...")

        # La fixture jvm_session assure que la JVM est démarrée.
        assert (
            jpype.isJVMStarted()
        ), "La JVM devrait être démarrée par la fixture jvm_session"

        PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        # PropositionalSignature = jpype.JClass("org.tweetyproject.logics.pl.syntax.PropositionalSignature") # Remplacé par PlSignature
        PlSignature = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
        Proposition = jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
        SimplePlReasoner = jpype.JClass(
            "org.tweetyproject.logics.pl.reasoner.SimplePlReasoner"
        )
        Predicate = jpype.JClass("org.tweetyproject.logics.commons.syntax.Predicate")

        print("JVM démarrée et classes Tweety chargées via JClass (espérons-le).")

        # theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
        # print(f"Chemin du fichier de théorie : {theory_file_path}")

        # if not os.path.exists(theory_file_path):
        #     raise FileNotFoundError(f"Le fichier de théorie {theory_file_path} n'a pas été trouvé.")

        parser = PlParser()
        # JFile = jpype.JClass("java.io.File")
        # java_file = JFile(JString(theory_file_path))
        # belief_set_from_file = parser.parseBeliefBaseFromFile(theory_file_path)
        # print(f"Théorie chargée depuis fichier. Nombre de formules : {belief_set_from_file.size()}")

        # Construction programmatique du PlBeliefSet
        belief_set = PlBeliefSet()
        prop_a = parser.parseFormula(JString("a"))  # Proposition a
        prop_b = parser.parseFormula(JString("b"))  # Proposition b
        # prop_c = parser.parseFormula(JString("c")) # Proposition c
        # prop_d = parser.parseFormula(JString("d")) # Proposition d

        # Ajout de "b." (b est un fait)
        belief_set.add(prop_b)
        print(f"Ajout de '{prop_b.toString()}' au belief_set.")

        # Ajout de "a :- b." (a si b)
        # Une implication "X :- Y" est équivalente à "Y => X" ou "!Y || X"
        # TweetyProject utilise souvent des classes spécifiques pour les implications ou les parse directement.
        # Essayons de parser la règle directement.
        rule_a_if_b = parser.parseFormula(
            JString("b => a")
        )  # ou "a :- b" si le parser le gère pour les formules individuelles
        belief_set.add(rule_a_if_b)
        print(f"Ajout de la règle '{rule_a_if_b.toString()}' au belief_set.")

        # Optionnel: ajout des autres règles pour la complétude si nécessaire pour d'autres tests,
        # mais pour "a", ce qui précède devrait suffire.
        # rule_c_if_not_d = parser.parseFormula(JString("not d => c"))
        # belief_set.add(rule_c_if_not_d)
        # print(f"Ajout de la règle '{rule_c_if_not_d.toString()}' au belief_set.")
        # rule_d_if_not_c = parser.parseFormula(JString("not c => d"))
        # belief_set.add(rule_d_if_not_c)
        # print(f"Ajout de la règle '{rule_d_if_not_c.toString()}' au belief_set.")

        print(
            f"Théorie construite programmatiquement. Nombre de formules : {belief_set.size()}"
        )

        print("Formules dans belief_set (construit programmatiquement):")
        # Tentative d'itération directe sur belief_set ou via sa méthode iterator()
        # PlBeliefSet pourrait implémenter Iterable ou avoir une méthode iterator()
        try:
            java_iterator = belief_set.iterator()  # Standard pour les collections Java
            while java_iterator.hasNext():
                print(f"  - {java_iterator.next().toString()}")
        except AttributeError:
            print(
                "  - belief_set.iterator() n'est pas disponible. Tentative d'autres approches si nécessaire ou log d'erreur."
            )
            # Si PlBeliefSet est une collection de formules, il pourrait être directement itérable en Python via JPype
            # ou nécessiter une conversion explicite si JPype ne le gère pas automatiquement.
            # Pour l'instant, on logue et on continue pour voir si le reste du test fonctionne,
            # bien que l'inspection des formules soit utile.

        print("Méthodes de belief_set:", dir(belief_set))

        # Instancier un raisonneur simple
        reasoner = SimplePlReasoner()  # Utiliser le nom de classe importé
        # Le belief_set sera pass  la mthode query
        print("SimpleReasoner instancié.")
        print("Méthodes de reasoner:", dir(reasoner))

        # Créer une formule à interroger (par exemple, "a")
        # D'abord, créer une signature propositionnelle si nécessaire ou l'obtenir
        # Pour créer une Proposition, nous avons besoin d'un Predicate.
        # Un Predicate a un nom et une arité (0 pour les propositions).

        # Créer la proposition "a"
        # Note: La création de propositions peut varier.
        # Souvent, on les parse à partir d'une chaîne ou on les construit.
        # Si le parser peut parser une seule formule :
        query_formula_str = "a"
        # query_formula = parser.parseFormula(JString(query_formula_str))

        # Alternativement, construire la proposition directement:
        # Obtenir la signature de la base de connaissances ou créer une nouvelle
        signature = belief_set.getSignature()
        if not signature:
            # Si la signature n'est pas automatiquement créée ou récupérable,
            # il faut la créer manuellement et s'assurer que les propositions y sont.
            # Pour cet exemple, nous supposons que le parser crée les propositions
            # et qu'elles sont accessibles ou que le raisonneur peut les gérer.
            # Une manière plus directe de créer une proposition si elle existe déjà dans la signature :
            # Proposition propA = signature.getProposition("a");
            # Cependant, si "a" n'est pas explicitement dans la signature (par ex. si elle est vide au départ),
            # il faut la créer.
            # Le plus simple est souvent de parser la formule.
            # Si PlParser.parseFormula n'existe pas ou ne fonctionne pas comme attendu,
            # on peut créer un Predicate et ensuite une Proposition.
            # predicate_a = Predicate("a", 0) # Nom "a", arité 0
            # query_formula = Proposition(predicate_a)
            # Ou, si le parser a une méthode pour parser une formule simple :
            query_formula = parser.parseFormula(JString("a"))

        else:
            # Essayer de récupérer la proposition de la signature existante
            # Ou parser la formule directement
            query_formula = parser.parseFormula(JString("a"))

        print(f"Formule de requête créée : {query_formula.toString()}")

        # Vérifier si la formule est une conséquence
        is_consequence = reasoner.query(belief_set, query_formula)
        print(
            f"La formule '{query_formula.toString()}' est-elle une conséquence ? {is_consequence}"
        )

        if is_consequence:
            print(
                "Test du raisonneur et de requête simple RÉUSSI (a est une conséquence)."
            )
        else:
            # Dans notre sample_theory.lp, "a" est une conséquence (a :- b. et b.)
            raise AssertionError(
                f"ÉCHEC : La formule '{query_formula.toString()}' devrait être une conséquence, mais le raisonneur a retourné {is_consequence}."
            )

    except Exception as e:
        print(f"Test du raisonneur et de requête simple ÉCHOUÉ : {e}")
        import traceback

        traceback.print_exc()
        # L'exception sera automatiquement propagée par pytest
        raise

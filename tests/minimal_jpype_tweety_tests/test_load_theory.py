import jpype
import jpype.imports
from jpype.types import JString
import os

# Définir le chemin vers les JARs de Tweety (à adapter si nécessaire)
# Cela suppose que les JARs sont dans un sous-répertoire 'libs' du répertoire parent du projet
# ou que le CLASSPATH est déjà configuré.
# Pour cet exemple, nous allons supposer que le CLASSPATH est configuré
# ou que les JARs sont accessibles via les options JVM.
def test_load_theory():
    try:
        print("Démarrage du test de chargement de théorie...")

        # Démarrer la JVM si ce n'est pas déjà fait
        # L'initialisation de la JVM est maintenant gérée globalement par conftest.py
        if not jpype.isJVMStarted():
            # Cette condition ne devrait plus être vraie si conftest.py fonctionne correctement.
            print("ERREUR CRITIQUE: La JVM n'a pas été démarrée par conftest.py comme attendu dans test_load_theory.")
            # Lever une exception pour que le test échoue clairement si la JVM n'est pas prête.
            raise RuntimeError("JVM non démarrée par conftest.py, test_load_theory ne peut pas continuer.")
        # Importer les classes Java nécessaires de Tweety
        # Assurez-vous que les noms de package sont corrects pour votre version de Tweety
        from org.tweetyproject.logics.pl.syntax import PlBeliefSet
        from org.tweetyproject.logics.pl.parser import PlParser

        print("JVM démarrée et classes Tweety importées.")

        # Chemin vers le fichier de théorie
        theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
        print(f"Chemin du fichier de théorie : {theory_file_path}")

        if not os.path.exists(theory_file_path):
            raise FileNotFoundError(f"Le fichier de théorie {theory_file_path} n'a pas été trouvé.")

        # Créer un parser et charger la théorie
        parser = PlParser()
        belief_set = PlBeliefSet() # Crée un ensemble de croyances vide

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

    except Exception as e_main: # Renommé pour clarté
        print(f"Test de chargement de théorie ÉCHOUÉ : {e_main}")
        import traceback
        traceback.print_exc()
        # L'exception sera levée dans le finally si elle existe
        
    finally:
        if jpype.isJVMStarted():
            try:
                System = jpype.JClass("java.lang.System")
                actual_classpath = System.getProperty("java.class.path")
                print(f"DEBUG_FINALLY_CLASSPATH (test_load_theory): {actual_classpath}")
            except Exception as e_jvm_debug_finally:
                print(f"DEBUG_FINALLY_CLASSPATH_ERROR (test_load_theory): {e_jvm_debug_finally}")
        
        # Optionnel: arrêter la JVM si ce script est le seul utilisateur
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("JVM arrêtée.")
        
        # Relancer l'exception originale si elle a eu lieu pour que le test échoue
        if 'e_main' in locals() and isinstance(e_main, Exception):
            raise e_main # s'assure que le test échoue si une exception a été attrapée
        pass
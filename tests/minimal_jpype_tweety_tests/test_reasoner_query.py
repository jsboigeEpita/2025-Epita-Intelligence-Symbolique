import jpype
import jpype.imports
from jpype.types import JString
import os

def main():
    try:
        print("Démarrage du test du raisonneur et de requête simple...")

        if not jpype.isJVMStarted():
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            jvm_dll_path = os.path.join(project_root, "portable_jdk", "jdk-17.0.15+6", "bin", "server", "jvm.dll")

            if not os.path.exists(jvm_dll_path):
                jvm_dll_path_client = os.path.join(project_root, "portable_jdk", "jdk-17.0.15+6", "bin", "client", "jvm.dll")
                if os.path.exists(jvm_dll_path_client):
                    jvm_dll_path = jvm_dll_path_client
                else:
                    java_home = os.environ.get("JAVA_HOME")
                    if java_home:
                        potential_jvm_path_server = os.path.join(java_home, "bin", "server", "jvm.dll")
                        potential_jvm_path_client = os.path.join(java_home, "bin", "client", "jvm.dll")
                        if os.path.exists(potential_jvm_path_server):
                            jvm_dll_path = potential_jvm_path_server
                        elif os.path.exists(potential_jvm_path_client):
                            jvm_dll_path = potential_jvm_path_client
                        else:
                            print(f"AVERTISSEMENT: jvm.dll non trouvée dans le JDK portable ({jvm_dll_path}) ni dans JAVA_HOME ({java_home}).")
                            # On ne spécifie pas de jvm_dll_path si non trouvé, JPype essaiera de trouver par défaut
                            jvm_dll_path = None
                    else:
                        print(f"ERREUR: jvm.dll non trouvée dans le JDK portable ({jvm_dll_path}) et JAVA_HOME n'est pas défini.")
                        jvm_dll_path = None # Laisser JPype essayer de trouver par défaut ou échouer

            if jvm_dll_path:
                 print(f"Utilisation de jvm.dll : {jvm_dll_path}")
            else:
                print("Aucun chemin jvm.dll explicite fourni à JPype. Tentative de détection automatique.")

            # Essayer de lire CLASSPATH depuis l'environnement et le passer explicitement
            env_classpath = os.environ.get("CLASSPATH")
            if env_classpath:
                print(f"Utilisation de CLASSPATH depuis l'environnement : {env_classpath}")
                classpath_list = env_classpath.split(os.pathsep)
                if jvm_dll_path:
                    jpype.startJVM(jvm_dll_path, classpath=classpath_list, convertStrings=False)
                else:
                    jpype.startJVM(classpath=classpath_list, convertStrings=False) # Sans jvm_dll_path explicite
            else:
                print("AVERTISSEMENT: CLASSPATH non trouvé dans l'environnement. Tentative de démarrage sans classpath explicite.")
                if jvm_dll_path:
                    jpype.startJVM(jvm_dll_path, convertStrings=False)
                else:
                    jpype.startJVM(convertStrings=False) # Sans jvm_dll_path et sans classpath explicite

        from net.sf.tweety.logics.pl import PlBeliefSet
        from net.sf.tweety.logics.pl.parser import PlParser
        from net.sf.tweety.logics.pl.syntax import PropositionalSignature, Proposition
        from net.sf.tweety.logics.pl.reasoner import SimpleReasoner
        from net.sf.tweety.logics.commons.syntax.Predicate import Predicate

        print("JVM démarrée et classes Tweety importées.")

        theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
        print(f"Chemin du fichier de théorie : {theory_file_path}")

        if not os.path.exists(theory_file_path):
            raise FileNotFoundError(f"Le fichier de théorie {theory_file_path} n'a pas été trouvé.")

        parser = PlParser()
        JFile = jpype.JClass("java.io.File")
        java_file = JFile(JString(theory_file_path))
        belief_set = parser.parseBeliefBaseFromFile(java_file)

        print(f"Théorie chargée avec succès. Nombre de formules : {belief_set.size()}")

        # Instancier un raisonneur simple
        reasoner = SimpleReasoner(belief_set)
        print("SimpleReasoner instancié.")

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
        print(f"La formule '{query_formula.toString()}' est-elle une conséquence ? {is_consequence}")

        if is_consequence:
            print("Test du raisonneur et de requête simple RÉUSSI (a est une conséquence).")
        else:
            # Dans notre sample_theory.lp, "a" est une conséquence (a :- b. et b.)
            raise AssertionError(f"ÉCHEC : La formule '{query_formula.toString()}' devrait être une conséquence, mais le raisonneur a retourné {is_consequence}.")

    except Exception as e:
        print(f"Test du raisonneur et de requête simple ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("JVM arrêtée.")
        pass

if __name__ == "__main__":
    main()
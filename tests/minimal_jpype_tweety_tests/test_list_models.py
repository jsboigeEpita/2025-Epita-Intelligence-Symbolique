import jpype
import jpype.imports
from jpype.types import JString
import os

def main():
    try:
        print("Démarrage du test de listage des modèles...")

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
                            jvm_dll_path = None
                    else:
                        print(f"ERREUR: jvm.dll non trouvée dans le JDK portable ({jvm_dll_path}) et JAVA_HOME n'est pas défini.")
                        jvm_dll_path = None

            if jvm_dll_path:
                 print(f"Utilisation de jvm.dll : {jvm_dll_path}")
            else:
                print("Aucun chemin jvm.dll explicite fourni à JPype. Tentative de détection automatique.")

            env_classpath = os.environ.get("CLASSPATH")
            if env_classpath:
                print(f"Utilisation de CLASSPATH depuis l'environnement : {env_classpath}")
                classpath_list = env_classpath.split(os.pathsep)
                if jvm_dll_path:
                    jpype.startJVM(jvm_dll_path, classpath=classpath_list, convertStrings=False)
                else:
                    jpype.startJVM(classpath=classpath_list, convertStrings=False)
            else:
                print("AVERTISSEMENT: CLASSPATH non trouvé dans l'environnement. Tentative de démarrage sans classpath explicite.")
                if jvm_dll_path:
                    jpype.startJVM(jvm_dll_path, convertStrings=False)
                else:
                    jpype.startJVM(convertStrings=False)

        from net.sf.tweety.logics.pl import PlBeliefSet
        from net.sf.tweety.logics.pl.parser import PlParser
        from net.sf.tweety.logics.pl.reasoner import SimpleReasoner
        # Pour afficher les modèles, nous pourrions avoir besoin de PlInterpretation ou similaire
        from net.sf.tweety.logics.pl.syntax import PlInterpretation # Ou PlPossibleWorld

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
        # Note: SimpleReasoner ne fournit pas directement une méthode getModels().
        # Pour obtenir les modèles, on utilise souvent un solver spécifique ou un raisonneur plus avancé,
        # ou on vérifie la satisfiabilité.
        # Cependant, si l'objectif est de lister les modèles,
        # il faut s'assurer que le raisonneur utilisé le permet.
        # Pour la logique propositionnelle, `SatReasoner` est plus approprié pour lister les modèles.
        # from net.sf.tweety.arg.dung.reasoner import SatReasoner <- Ceci est pour l'argumentation
        # Pour la logique PL, il faut un solveur SAT. Tweety intègre des solveurs.
        # Par exemple, net.sf.tweety.logics.pl.sat.Sat4jSolver
        # from net.sf.tweety.logics.pl.sat import Sat4jSolver # ou un autre solveur SAT disponible

        # Si SimpleReasoner ne peut pas lister les modèles, ce test devra être adapté
        # ou utiliser un autre raisonneur.
        # Vérifions la documentation de Tweety ou les exemples pour le listage de modèles.
        # Typiquement, un `ModelEnumerator` ou une méthode sur un `SatSolver` est utilisée.

        # Pour l'instant, supposons que nous voulons vérifier la cohérence (existence d'au moins un modèle)
        # ou si un raisonneur plus apte est disponible.
        # Si `SimpleReasoner` ne peut pas lister les modèles, nous allons utiliser `Sat4jSolver`
        # qui est un wrapper pour un solveur SAT et peut généralement énumérer les modèles.

        # Tentative avec un solveur SAT si SimpleReasoner ne suffit pas.
        # Assurez-vous que le JAR de Sat4j (ou un autre solveur configuré) est dans le classpath.
        try:
            from net.sf.tweety.logics.pl.sat import Sat4jSolver
            solver = Sat4jSolver()
            print("Utilisation de Sat4jSolver.")
        except jpype.JClassNotfoundException:
            print("Sat4jSolver non trouvé, tentative avec SimpleReasoner (peut ne pas lister les modèles).")
            # SimpleReasoner est principalement pour les requêtes d'implication.
            # Il ne liste pas les modèles. Ce test échouera probablement ou nécessitera une adaptation.
            # Pour l'objectif de "lister les modèles", SimpleReasoner n'est pas le bon outil.
            # Nous allons lever une exception si Sat4jSolver n'est pas disponible,
            # car le but du test est de lister les modèles.
            raise RuntimeError("Sat4jSolver non trouvé. Impossible de lister les modèles avec SimpleReasoner.")


        # Obtenir les modèles de la base de connaissances
        # La méthode pour obtenir les modèles peut être `getModels(belief_set)` ou similaire.
        models = solver.getModels(belief_set) # Sat4jSolver a cette méthode

        print(f"Nombre de modèles trouvés : {models.size()}")

        if models.isEmpty():
            print("Aucun modèle trouvé. La théorie est incohérente.")
            # Pour notre sample_theory.lp, elle est cohérente.
            raise AssertionError("ÉCHEC : Aucun modèle trouvé pour une théorie cohérente.")
        else:
            print("Modèles trouvés :")
            # Un modèle est souvent une collection de littéraux vrais (ou une interprétation)
            # L'itération sur `models` (qui est une Collection<PlInterpretation>)
            model_count = 0
            for model in models: # model est un PlInterpretation
                model_str = model.toString() # Ou une autre méthode pour obtenir une représentation textuelle
                print(f"- {model_str}")
                model_count += 1
            
            # Vérification du nombre de modèles attendus (3 pour notre théorie)
            # a, b, (c v d)
            # Modèles: {a,b,c,d}, {a,b,c,~d}, {a,b,~c,d}
            # Les représentations de Tweety peuvent varier (par ex. seulement les atomes positifs)
            # {a,b,c}, {a,b,d} si on ne liste que les positifs et que d est vrai si c est faux et vice-versa
            # Pour c v d: (c=T, d=T), (c=T, d=F), (c=F, d=T)
            # Donc 3 modèles pour (c,d), et a,b sont toujours vrais.
            # Le nombre de modèles attendu est 3.
            expected_models = 3
            if model_count == expected_models:
                 print(f"Test de listage des modèles RÉUSSI. {model_count} modèles trouvés comme attendu.")
            else:
                raise AssertionError(f"ÉCHEC : Nombre de modèles incorrect. Attendu : {expected_models}, Trouvé : {model_count}")


    except Exception as e:
        print(f"Test de listage des modèles ÉCHOUÉ : {e}")
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
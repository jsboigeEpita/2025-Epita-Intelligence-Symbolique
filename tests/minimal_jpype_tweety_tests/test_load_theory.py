import jpype
import jpype.imports
from jpype.types import JString
import os

# Définir le chemin vers les JARs de Tweety (à adapter si nécessaire)
# Cela suppose que les JARs sont dans un sous-répertoire 'libs' du répertoire parent du projet
# ou que le CLASSPATH est déjà configuré.
# Pour cet exemple, nous allons supposer que le CLASSPATH est configuré
# ou que les JARs sont accessibles via les options JVM.

def main():
    try:
        print("Démarrage du test de chargement de théorie...")

        # Démarrer la JVM si ce n'est pas déjà fait
        if not jpype.isJVMStarted():
            # Adaptez le classpath si nécessaire.
            # Exemple: jpype.startJVM(classpath=['path/to/tweety.jar', 'path/to/other.jar'])
            # Pour cet exemple, nous supposons que le CLASSPATH est configuré
            # ou que les JARs sont dans le répertoire de travail ou un chemin connu.
            # Vous devrez peut-être spécifier le chemin vers les JARs de Tweety ici.
            # Par exemple, si les JARs sont dans un dossier 'libs' à la racine du projet:
            # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            # tweety_libs_path = os.path.join(project_root, "libs", "*") # Chemin vers les JARs
            # jpype.startJVM(classpath=[tweety_libs_path])
            # Pour une configuration plus robuste, utilisez les chemins exacts des JARs.
            # Exemple simplifié, en supposant que les JARs sont trouvables:
            # Construire le chemin vers jvm.dll dynamiquement
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            jvm_dll_path = os.path.join(project_root, "portable_jdk", "jdk-17.0.15+6", "bin", "server", "jvm.dll")

            if not os.path.exists(jvm_dll_path):
                # Essayer le chemin client si le chemin serveur n'existe pas (moins courant pour les JDK récents)
                jvm_dll_path_client = os.path.join(project_root, "portable_jdk", "jdk-17.0.15+6", "bin", "client", "jvm.dll")
                if os.path.exists(jvm_dll_path_client):
                    jvm_dll_path = jvm_dll_path_client
                else:
                    # Tenter de récupérer JAVA_HOME si défini, sinon lever une erreur plus informative
                    java_home = os.environ.get("JAVA_HOME")
                    if java_home:
                        # Tenter de construire le chemin à partir de JAVA_HOME
                        # Cela suppose une structure JDK standard
                        potential_jvm_path_server = os.path.join(java_home, "bin", "server", "jvm.dll")
                        potential_jvm_path_client = os.path.join(java_home, "bin", "client", "jvm.dll")
                        if os.path.exists(potential_jvm_path_server):
                            jvm_dll_path = potential_jvm_path_server
                        elif os.path.exists(potential_jvm_path_client):
                            jvm_dll_path = potential_jvm_path_client
                        else:
                            print(f"AVERTISSEMENT: jvm.dll non trouvée dans le JDK portable ({jvm_dll_path}) ni dans JAVA_HOME ({java_home}). Tentative de démarrage sans jvmpath explicite.")
                            jpype.startJVM(convertStrings=False) # Tentative sans jvmpath explicite
                            # Le reste du code continue après cet appel
                    else:
                        print(f"ERREUR: jvm.dll non trouvée dans le JDK portable ({jvm_dll_path}) et JAVA_HOME n'est pas défini.")
                        # Lever une exception ou gérer l'erreur comme il convient
                        raise FileNotFoundError(f"jvm.dll non trouvée. Vérifiez le chemin du JDK portable: {jvm_dll_path} ou configurez JAVA_HOME.")
            
            print(f"Utilisation de jvm.dll : {jvm_dll_path}")
            
            # Configurer le classpath pour les JARs de Tweety
            tweety_libs_path_glob = os.path.join(project_root, "libs", "*")
            # jpype.startJVM(jvm_dll_path, classpath=[tweety_libs_path_glob], convertStrings=False)
            # Utiliser une liste de fichiers JAR explicites est plus robuste que le glob '*'
            libs_dir = os.path.join(project_root, "libs")
            if os.path.isdir(libs_dir):
                tweety_jars = [os.path.join(libs_dir, f) for f in os.listdir(libs_dir) if f.endswith(".jar")]
                if not tweety_jars:
                    print(f"AVERTISSEMENT: Aucun fichier .jar trouvé dans {libs_dir}. Le classpath pourrait être incorrect.")
                    # Si aucun JAR n'est trouvé, on ne définit pas de classpath explicite pour JPype,
                    # en espérant une configuration globale ou un fallback au glob (qui a échoué).
                    # Cela mènera probablement à une erreur, mais c'est pour être cohérent.
                    jpype.startJVM(jvm_dll_path, convertStrings=False)
                else:
                    # Construire la chaîne CLASSPATH
                    # Essayer de lire CLASSPATH depuis l'environnement et le passer explicitement
                    env_classpath = os.environ.get("CLASSPATH")
                    if env_classpath:
                        print(f"Utilisation de CLASSPATH depuis l'environnement : {env_classpath}")
                        # JPype s'attend à une liste de chemins pour l'argument classpath
                        classpath_list = env_classpath.split(os.pathsep)
                        jpype.startJVM(jvm_dll_path, classpath=classpath_list, convertStrings=False)
                    else:
                        print("AVERTISSEMENT: CLASSPATH non trouvé dans l'environnement. Tentative de démarrage sans classpath explicite.")
                        jpype.startJVM(jvm_dll_path, convertStrings=False)
            else:
                print(f"ERREUR: Le répertoire libs ({libs_dir}) n'a pas été trouvé. Vérifiez la structure du projet.")
                # Essayer de lire CLASSPATH depuis l'environnement si libs n'est pas trouvé
                env_classpath = os.environ.get("CLASSPATH")
                if env_classpath:
                    print(f"Utilisation de CLASSPATH depuis l'environnement (fallback libs non trouvé): {env_classpath}")
                    jpype.startJVM(jvm_dll_path, classpath=[env_classpath], convertStrings=False) # Passer comme liste
                else:
                    print("AVERTISSEMENT: CLASSPATH non trouvé dans l'environnement et répertoire libs non trouvé.")
                    jpype.startJVM(jvm_dll_path, convertStrings=False) # Démarrer sans classpath explicite

        # Importer les classes Java nécessaires de Tweety
        # Assurez-vous que les noms de package sont corrects pour votre version de Tweety
        from net.sf.tweety.logics.pl import PlBeliefSet
        from net.sf.tweety.logics.pl.parser import PlParser

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
        parsed_belief_set = parser.parseBeliefBaseFromFile(java_file)
        
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
        raise # Relancer l'exception pour indiquer l'échec du test

    finally:
        # Optionnel: arrêter la JVM si ce script est le seul utilisateur
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("JVM arrêtée.")
        pass # Laisser la JVM active pour d'autres tests potentiels dans la même session

if __name__ == "__main__":
    main()
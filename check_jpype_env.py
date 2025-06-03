# Ce script vérifie la configuration de l'environnement pour l'utilisation de JPype
# avec TweetyProject. Il s'assure que Python, Java (JDK), JPype et les JARs de Tweety
# sont correctement configurés et accessibles.
# Il sert de première démonstration simple de l'intégration JPype/Tweety.

import sys
import os
import glob

# 1. Importer les modules nécessaires
print("--- Vérification de l'environnement JPype/JVM ---")
print("1. Importation des modules...")
try:
    import jpype
    import jpype.imports
    print("   jpype et jpype.imports importés avec succès.")
except ImportError as e:
    print(f"ERREUR: Impossible d'importer jpype ou jpype.imports: {e}")
    print("Veuillez vous assurer que JPype est correctement installé (pip install JPype1).")
    sys.exit(1)
except Exception as e:
    print(f"ERREUR inattendue lors de l'import de jpype: {e}")
    sys.exit(1)

# 2. Afficher la version de Python
print(f"\n2. Version de Python: {sys.version}")

# 3. Afficher le chemin de l'exécutable Python
print(f"3. Exécutable Python: {sys.executable}")

# 4. Afficher la valeur de JAVA_HOME
java_home = os.environ.get('JAVA_HOME')
print(f"4. JAVA_HOME (os.environ.get): {java_home if java_home else 'Non défini'}")

# 5. L'import de jpype a déjà été tenté à l'étape 1.

# 6. Afficher le chemin par défaut de la JVM
print("\n6. Tentative d'obtention du chemin JVM par défaut...")
try:
    default_jvm_path = jpype.getDefaultJVMPath()
    print(f"   Chemin JVM par défaut (jpype.getDefaultJVMPath()): {default_jvm_path}")
except Exception as e:
    print(f"ERREUR lors de l'obtention du chemin JVM par défaut: {e}")
    default_jvm_path = None # Pour la suite, même si on ne pourra pas démarrer

# 7. Construire le classpath pour les JARs de Tweety
print("\n7. Construction du classpath pour les JARs Tweety...")
script_dir = os.path.dirname(os.path.abspath(__file__))
libs_dir = os.path.join(script_dir, "libs")
classpath_entries = []
if os.path.isdir(libs_dir):
    for jar_file in glob.glob(os.path.join(libs_dir, "*.jar")):
        classpath_entries.append(jar_file)
    tweety_classpath = classpath_entries
    if not tweety_classpath:
        print(f"   AVERTISSEMENT: Le répertoire 'libs' ({libs_dir}) existe mais ne contient aucun fichier .jar.")
        print("   La JVM démarrera sans le classpath Tweety.")
    else:
        print(f"   Répertoire 'libs' trouvé: {libs_dir}")
else:
    print(f"   AVERTISSEMENT: Le répertoire 'libs' ({libs_dir}) n'a pas été trouvé.")
    print("   La JVM démarrera sans le classpath Tweety. Les tests Tweety échoueront probablement.")
    tweety_classpath = [] # Pas de classpath si le répertoire n'existe pas

# 8. Afficher le classpath construit
print(f"8. Classpath construit pour Tweety: {os.pathsep.join(tweety_classpath) if tweety_classpath else 'Vide'}")
# 7. Détection du JDK 17 portable
print("\n7. Détection du JDK 17 portable...")
portable_jdk17_dir = os.path.join(script_dir, "portable_jdk", "jdk-17.0.15+6")
portable_jdk17_jvm_path = os.path.join(portable_jdk17_dir, "bin", "server", "jvm.dll") # Trouvé via list_files
print(f"   Chemin base du JDK 17 portable: {portable_jdk17_dir}")
if os.path.exists(portable_jdk17_jvm_path):
    print(f"   Chemin jvm.dll du JDK 17 portable trouvé: {portable_jdk17_jvm_path}")
else:
    print(f"   AVERTISSEMENT: jvm.dll du JDK 17 portable NON trouvé à: {portable_jdk17_jvm_path}")
    portable_jdk17_jvm_path = None # S'assurer qu'il est None s'il n'est pas trouvé

# 8. Détermination du chemin JVM à utiliser
print("\n8. Détermination du chemin JVM à utiliser...")
jvm_path_to_use = None
preferred_jvm_source = ""

# Priorité 1: JDK 17 Portable (fourni avec le projet)
# C'est la méthode privilégiée pour assurer un environnement cohérent pour tous les utilisateurs.
if portable_jdk17_jvm_path and os.path.exists(portable_jdk17_jvm_path):
    jvm_path_to_use = portable_jdk17_jvm_path
    preferred_jvm_source = "JDK 17 Portable"
    print(f"   INFO: Priorité 1 - Utilisation du JDK 17 Portable: {jvm_path_to_use}")
else:
    print(f"   INFO: JDK 17 Portable non utilisé (chemin: {portable_jdk17_jvm_path}).")

# Priorité 2: Variable d'environnement JAVA_HOME
# Si le JDK portable n'est pas trouvé, on se rabat sur JAVA_HOME configuré par l'utilisateur.
if not jvm_path_to_use and java_home:
    print(f"   INFO: Priorité 2 - Tentative avec JAVA_HOME ({java_home})...")
    # Tenter de construire le chemin vers jvm.dll/libjvm.so à partir de JAVA_HOME
    jvm_path_candidates = []
    if sys.platform == "win32":
        jvm_path_candidates = [
            os.path.join(java_home, 'bin', 'server', 'jvm.dll'),
            os.path.join(java_home, 'jre', 'bin', 'server', 'jvm.dll'),
            os.path.join(java_home, 'bin', 'jvm.dll')
        ]
    elif sys.platform == "darwin": # macOS
        jvm_path_candidates = [
            os.path.join(java_home, 'lib', 'server', 'libjvm.dylib'),
            os.path.join(java_home, 'jre', 'lib', 'server', 'libjvm.dylib')
        ]
    else: # Linux et autres
        jvm_path_candidates = [
            os.path.join(java_home, 'lib', 'server', 'libjvm.so'),
            os.path.join(java_home, 'jre', 'lib', 'server', 'libjvm.so')
        ]

    found_jvm_in_java_home = False
    for i, candidate_path in enumerate(jvm_path_candidates):
        if os.path.exists(candidate_path):
            jvm_path_to_use = candidate_path
            preferred_jvm_source = f"JAVA_HOME (essai {i+1})" # Mise à jour de la source
            print(f"   INFO: Chemin JVM trouvé dans JAVA_HOME: {jvm_path_to_use}")
            found_jvm_in_java_home = True
            break
    
    if not found_jvm_in_java_home:
        print(f"   AVERTISSEMENT: Aucun chemin JVM valide trouvé dans JAVA_HOME ({java_home}).")
        # Afficher les candidats testés si on le souhaite (déjà fait par l'ancienne logique si c'était la source principale)
        # for candidate_path in jvm_path_candidates:
        #     print(f"     - {candidate_path} (non trouvé lors de la recherche via JAVA_HOME)")
elif not jvm_path_to_use: # Si JDK17 portable non utilisé ET JAVA_HOME non défini
     print(f"   INFO: JAVA_HOME n'est pas défini (et JDK 17 portable non utilisé ou non trouvé).")

# Priorité 3: Chemin JVM par défaut détecté par JPype
# En dernier recours, si ni le JDK portable ni JAVA_HOME ne sont utilisables,
# on essaie avec le chemin que JPype trouve par défaut sur le système.
if not jvm_path_to_use and default_jvm_path:
    print(f"   INFO: Priorité 3 - Utilisation du chemin JVM par défaut de JPype: {default_jvm_path}")
    jvm_path_to_use = default_jvm_path
    preferred_jvm_source = "JPype Default"
elif not jvm_path_to_use: # Si default_jvm_path est aussi None (ne devrait pas arriver si JPype est installé et fonctionnel)
    print("   ERREUR CRITIQUE: Aucun chemin JVM (Portable, JAVA_HOME, ou JPype par défaut) n'est disponible ou valide.")
    # jvm_path_to_use reste None, ce qui sera géré avant le démarrage de la JVM

# La variable jvm_started_successfully est définie plus loin, juste avant la section de démarrage.
# On la met ici pour que le bloc remplacé soit cohérent.
jvm_started_successfully = False

# 9. Tenter de démarrer la JVM
print("\n9. Tentative de démarrage de la JVM...")
if not jvm_path_to_use:
    print("   ERREUR: Impossible de démarrer la JVM car aucun chemin JVM valide n'a pu être déterminé.")
    # jvm_started_successfully est déjà False (défini à la fin du bloc de détermination du chemin)
else:
    if not jpype.isJVMStarted():
        print(f"   INFO: Tentative de démarrage avec la JVM de '{preferred_jvm_source}': {jvm_path_to_use}")
        if tweety_classpath: # tweety_classpath est une liste de chemins
            print(f"   Utilisation du classpath: {os.pathsep.join(tweety_classpath)}")
        else:
            print("   INFO: Démarrage de la JVM sans classpath Tweety spécifique.")
        
        try:
            # jpype.startJVM attend que classpath soit une liste de strings (ce que tweety_classpath est)
            jpype.startJVM(jvm_path_to_use, "-ea", classpath=tweety_classpath, convertStrings=False)
            jvm_started_successfully = True # Mettre à True seulement après succès
            print("   INFO: JVM démarrée avec succès.")
        except Exception as e_start_jvm:
            print(f"   ERREUR lors du démarrage de la JVM avec '{preferred_jvm_source}' ({jvm_path_to_use}): {e_start_jvm}")
            jvm_started_successfully = False
            # Ici, on pourrait ajouter une logique pour tenter une autre source de JVM si la première échoue.
            # Par exemple, si JDK 17 portable échoue, tenter JAVA_HOME, puis le défaut JPype.
            # Pour l'instant, on s'arrête à la première erreur de démarrage pour la source JVM choisie.
    else:
        print("   INFO: La JVM est déjà démarrée.")
        jvm_started_successfully = True # Supposer qu'elle a bien démarré précédemment et est valide.
# 10. Si la JVM a démarré, tester l'import Tweety
print("\n    --- Test d'import Java Standard ---")
try:
    jpype.imports.registerDomain("java") # Bonne pratique
    from java.util import ArrayList
    print("      Import de java.util.ArrayList réussi.")
    my_list = ArrayList()
    my_list.add("TestItem")
    print(f"      Instanciation et utilisation de java.util.ArrayList réussies: {my_list}")
except Exception as e_java_std:
    print(f"ERREUR lors du test d'import Java standard: {e_java_std}")
print("    --- Fin Test d'import Java Standard ---\n")
print("\n10. Vérification de l'état de la JVM et test d'import Tweety...")
if jpype.isJVMStarted():
    print("    La JVM est démarrée.")
    if not tweety_classpath:
        print("    AVERTISSEMENT: Le classpath Tweety est vide. Le test d'import de classe Tweety sera ignoré.")
    else:
        print("    Tentative d'import d'une classe Tweety (PlSignature)...")
        try:
            # Enregistrer le domaine de premier niveau (par exemple, "org" pour "org.tweetyproject")
            # aide JPype à résoudre les imports de classes Java.
            # C'est une bonne pratique pour éviter les ambiguïtés et faciliter la découverte des classes.
            jpype.imports.registerDomain("org")
            from org.tweetyproject.logics.pl.syntax import PlSignature
            print("      Import de org.tweetyproject.logics.pl.syntax.PlSignature réussi.")
            try:
                # Instanciation simple d'un objet PlSignature.
                # Cela confirme que la classe est non seulement importable mais aussi utilisable.
                sig = PlSignature()
                print(f"      Instanciation de PlSignature réussie: {sig}")
                print("\n      #####################################################################")
                print("      ### SUCCÈS : L'environnement JPype et Tweety est opérationnel ! ###")
                print("      ### Vous pouvez maintenant utiliser les classes Java de Tweety  ###")
                print("      ### dans vos scripts Python.                                  ###")
                print("      #####################################################################")
            except Exception as e_inst:
                print(f"ERREUR lors de l'instanciation de PlSignature: {e_inst}")
        except ImportError as e_import_class:
             print(f"ERREUR: Classe Tweety non trouvée (JClassNotfoundException) - tentative avec org.tweetyproject.logics.pl.syntax.PlSignature: {e_import_class}")
             print("      Causes possibles :")
             print("        - Les JARs de Tweety ne sont pas dans le classpath ou sont corrompus.")
             print(f"        - Le classpath utilisé était: {tweety_classpath}")
        except Exception as e_import:
            print(f"ERREUR lors de l'import de la classe Tweety: {e_import}")
else:
    print("    La JVM n'est pas démarrée. Impossible de tester l'import Tweety.")

# 11. Afficher l'état retourné par jpype.isJVMStarted()
print(f"\n11. État final de la JVM (jpype.isJVMStarted()): {jpype.isJVMStarted()}")

# 12. Tenter d'arrêter la JVM
print("\n12. Tentative d'arrêt de la JVM...")
if jpype.isJVMStarted():
    try:
        jpype.shutdownJVM()
        print("    JVM arrêtée avec succès.")
    except Exception as e:
        print(f"ERREUR lors de l'arrêt de la JVM (jpype.shutdownJVM): {e}")
        print("    Cela peut parfois se produire si la JVM a eu des problèmes internes ou si des threads Java sont toujours actifs.")
else:
    print("    La JVM n'était pas démarrée (ou n'a pas pu être démarrée), pas besoin de l'arrêter.")

print("\n--- Fin de la vérification ---")
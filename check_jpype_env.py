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

# Déterminer quel chemin JVM utiliser
jvm_path_to_use = None
if java_home:
    # Tenter de construire le chemin vers jvm.dll à partir de JAVA_HOME
    # Pour Windows, c'est typiquement JAVA_HOME/bin/server/jvm.dll
    # Pour Linux/macOS, ce serait JAVA_HOME/lib/server/libjvm.so ou similaire
    jvm_path_candidates = []
    if sys.platform == "win32":
        jvm_path_candidates = [
            os.path.join(java_home, 'bin', 'server', 'jvm.dll'), # Standard JDK
            os.path.join(java_home, 'jre', 'bin', 'server', 'jvm.dll'), # JDK plus ancien avec JRE interne
            os.path.join(java_home, 'bin', 'jvm.dll') # Parfois pour JRE embarqué / GraalVM-like
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
            print(f"   INFO: Utilisation du chemin JVM dérivé de JAVA_HOME (essai {i+1}): {jvm_path_to_use}")
            found_jvm_in_java_home = True
            break
    
    if not found_jvm_in_java_home:
        print(f"   AVERTISSEMENT: JAVA_HOME est défini ({java_home}), mais aucun des chemins JVM attendus n'a été trouvé:")
        for candidate_path in jvm_path_candidates:
            print(f"     - {candidate_path} (non trouvé)")
        print(f"   Retour à l'utilisation du chemin JVM par défaut de JPype: {default_jvm_path}")
        jvm_path_to_use = default_jvm_path
else:
    print("   INFO: JAVA_HOME n'est pas défini. Utilisation du chemin JVM par défaut de JPype.")
    jvm_path_to_use = default_jvm_path

jvm_started_successfully = False

# 9. Tenter de démarrer la JVM
print("\n9. Tentative de démarrage de la JVM...")
if not jvm_path_to_use:
    print("   ERREUR: Impossible de démarrer la JVM car aucun chemin JVM valide n'a pu être déterminé (ni via JAVA_HOME, ni via JPype par défaut).")
else:
    try:
        print(f"   Utilisation du chemin JVM: {jvm_path_to_use}")
        if tweety_classpath:
            print(f"   Utilisation du classpath: {os.pathsep.join(tweety_classpath)}")
            jpype.startJVM(jvm_path_to_use, "-ea", classpath=tweety_classpath)
        else:
            print("   Démarrage de la JVM sans classpath spécifique.")
            jpype.startJVM(jvm_path_to_use, "-ea")
        print("   JVM démarrée avec succès (ou déjà démarrée).")
        jvm_started_successfully = jpype.isJVMStarted() # Confirmer
    except Exception as e:
        print(f"ERREUR lors du démarrage de la JVM (jpype.startJVM) avec le chemin {jvm_path_to_use}: {e}")
        print("   Causes possibles :")
        print("     - JAVA_HOME mal configuré ou pointe vers une installation JRE/JDK invalide.")
        print("     - Conflit de version de la DLL JVM (si plusieurs JDK/JRE sont installés).")
        print("     - Problème avec les JARs dans le classpath (si fourni).")

# 10. Si la JVM a démarré, tester l'import Tweety
print("\n10. Vérification de l'état de la JVM et test d'import Tweety...")
if jpype.isJVMStarted():
    print("    La JVM est démarrée.")
    if not tweety_classpath:
        print("    AVERTISSEMENT: Le classpath Tweety est vide. Le test d'import de classe Tweety sera ignoré.")
    else:
        print("    Tentative d'import d'une classe Tweety (PropositionalSignature)...")
        try:
# Enregistrer le domaine de premier niveau peut aider JPype à trouver les classes
            jpype.imports.registerDomain("org")
            from org.tweetyproject.logics.pl.syntax import PropositionalSignature
            print("      Import de org.tweetyproject.logics.pl.syntax.PropositionalSignature réussi.")
            try:
                sig = PropositionalSignature()
                print(f"      Instanciation de PropositionalSignature réussie: {sig}")
                print("      SUCCESS: L'environnement JPype et Tweety semble fonctionner !")
            except Exception as e_inst:
                print(f"ERREUR lors de l'instanciation de PropositionalSignature: {e_inst}")
        except ImportError as e_import_class:
             print(f"ERREUR: Classe Tweety non trouvée (JClassNotfoundException): {e_import_class}")
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
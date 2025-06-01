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
    tweety_classpath = os.pathsep.join(classpath_entries)
    if not tweety_classpath:
        print(f"   AVERTISSEMENT: Le répertoire 'libs' ({libs_dir}) existe mais ne contient aucun fichier .jar.")
        print("   La JVM démarrera sans le classpath Tweety.")
    else:
        print(f"   Répertoire 'libs' trouvé: {libs_dir}")
else:
    print(f"   AVERTISSEMENT: Le répertoire 'libs' ({libs_dir}) n'a pas été trouvé.")
    print("   La JVM démarrera sans le classpath Tweety. Les tests Tweety échoueront probablement.")
    tweety_classpath = "" # Pas de classpath si le répertoire n'existe pas

# 8. Afficher le classpath construit
print(f"8. Classpath construit pour Tweety: {tweety_classpath if tweety_classpath else 'Vide'}")

jvm_started_successfully = False

# 9. Tenter de démarrer la JVM
print("\n9. Tentative de démarrage de la JVM...")
if not default_jvm_path:
    print("   ERREUR: Impossible de démarrer la JVM car le chemin par défaut n'a pas pu être déterminé.")
else:
    try:
        jpype.startJVM(default_jvm_path, "-ea", classpath=tweety_classpath if tweety_classpath else None)
        print("   JVM démarrée avec succès (ou déjà démarrée).")
        jvm_started_successfully = jpype.isJVMStarted() # Confirmer
    except Exception as e:
        print(f"ERREUR lors du démarrage de la JVM (jpype.startJVM): {e}")
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
            from org.tweetyproject.logics.pl.syntax import PropositionalSignature
            print("      Import de org.tweetyproject.logics.pl.syntax.PropositionalSignature réussi.")
            try:
                sig = PropositionalSignature()
                print(f"      Instanciation de PropositionalSignature réussie: {sig}")
                print("      SUCCESS: L'environnement JPype et Tweety semble fonctionner !")
            except Exception as e_inst:
                print(f"ERREUR lors de l'instanciation de PropositionalSignature: {e_inst}")
        except jpype.JClassNotfoundException as e_import_class:
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
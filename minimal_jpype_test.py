import jpype
import os
import traceback

# Configuration des chemins (identique à integration_fixtures.py)
project_root = os.path.dirname(os.path.abspath(__file__)) # Suppose que le script est à la racine
jdk_portable_path = os.path.join(project_root, 'libs', 'portable_jdk', 'jdk-17.0.11+9')
jvm_dll_path = os.path.join(jdk_portable_path, 'bin', 'server', 'jvm.dll')

tweety_libs_path = os.path.join(project_root, 'libs')
full_jar_name = "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
full_jar_path = os.path.join(tweety_libs_path, full_jar_name)
classpath_arg_value = full_jar_path

print(f"Début du test JPype minimal.")
print(f"Chemin JVM à utiliser : {jvm_dll_path}")
print(f"Classpath JAR : {classpath_arg_value}")

if not os.path.exists(jvm_dll_path):
    print(f"ERREUR : Fichier jvm.dll non trouvé : {jvm_dll_path}")
    exit(1)

if not os.path.exists(classpath_arg_value):
    print(f"ERREUR : Fichier JAR non trouvé : {classpath_arg_value}")
    exit(1)

try:
    if not jpype.isJVMStarted():
        print("Tentative de démarrage de la JVM...")
        jpype.startJVM(
            jvm_dll_path,
            f"-Djava.class.path={classpath_arg_value}",
            "-Xcheck:jni",  # Gardons cette option pour le moment
            convertStrings=False
        )
        print("JVM démarrée avec succès via JPype.")

        # Test simple d'accès à une classe Java
        System = jpype.JClass("java.lang.System")
        java_version = System.getProperty("java.version")
        print(f"Version Java obtenue via JPype System.getProperty: {java_version}")

        print("Test JPype minimal terminé avec succès.")

    else:
        print("La JVM était déjà démarrée (inattendu dans ce script isolé).")

except Exception as e:
    print(f"Une erreur s'est produite lors du test JPype minimal : {e}")
    traceback.print_exc()

finally:
    if jpype.isJVMStarted():
        # Pour un test isolé, il est bon de l'arrêter,
        # mais si on veut inspecter après un crash, on peut commenter la ligne suivante.
        # jpype.shutdownJVM()
        # print("Appel à shutdownJVM() effectué (commenté pour inspection si besoin).")
        pass
# test_jpype_minimal.py
import jpype
import jpype.imports # Nécessaire pour certaines versions/configurations de JPype
import os
import sys # Pour afficher la version de Python

print(f"--- Début du script de test JPype minimal ---")
print(f"Version de Python: {sys.version}")
print(f"Version de JPype: {jpype.__version__}")

# Chemin absolu vers le JDK portable
jdk_base_path = r"D:\Dev\2025-Epita-Intelligence-Symbolique\libs\portable_jdk\jdk-17.0.11+9"
# Construire le chemin vers jvm.dll (Windows)
jvm_dll_path = os.path.join(jdk_base_path, "bin", "server", "jvm.dll")

print(f"Chemin du JDK portable utilisé: {jdk_base_path}")
print(f"Chemin attendu pour jvm.dll: {jvm_dll_path}")

if not os.path.exists(jvm_dll_path):
    print(f"ERREUR CRITIQUE: jvm.dll non trouvé à l'emplacement : {jvm_dll_path}")
    print(f"Veuillez vérifier que le JDK portable est correctement installé à {jdk_base_path}")
    exit(1)
else:
    print(f"Fichier jvm.dll trouvé à : {jvm_dll_path}")

# Classpath vide
classpath_jars = []
print(f"Classpath utilisé (vide): {classpath_jars}")

# Options JVM (minimales)
jvm_options = ["-Xms64m", "-Xmx128m"] # Réduire l'usage mémoire pour le test
print(f"Options JVM utilisées: {jvm_options}")

try:
    print(f"\nTentative de démarrage de la JVM avec jpype.startJVM()...")
    print(f"  jvmpath='{jvm_dll_path}'")
    print(f"  classpath={classpath_jars}")
    print(f"  options={jvm_options}")

    jpype.startJVM(
        jvmpath=jvm_dll_path,
        classpath=classpath_jars,
        *jvm_options,
        convertStrings=False # Option standard que nous utilisons
    )
    print("SUCCESS: JVM démarrée avec succès.")

    # Test simple après démarrage
    try:
        print("Tentative d'accès à java.lang.System...")
        System = jpype.JClass("java.lang.System")
        java_version_from_jvm = System.getProperty("java.version")
        print(f"SUCCESS: Version Java obtenue depuis la JVM: {java_version_from_jvm}")
    except Exception as e_jclass:
        print(f"ERREUR lors du test post-démarrage (JClass): {e_jclass}")
        import traceback
        traceback.print_exc()

except Exception as e_start_jvm:
    print(f"ERREUR CRITIQUE lors de jpype.startJVM(): {e_start_jvm}")
    import traceback
    traceback.print_exc()
finally:
    if jpype.isJVMStarted():
        print("\nTentative d'arrêt de la JVM...")
        jpype.shutdownJVM()
        print("SUCCESS: JVM arrêtée.")
    else:
        print("\nINFO: La JVM n'a pas été démarrée ou a échoué avant l'arrêt.")

print(f"--- Fin du script de test JPype minimal ---")
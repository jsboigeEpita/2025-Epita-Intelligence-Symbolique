import jpype
import jpype.imports
import os
import sys # Ajout de sys
import time
import pathlib # Ajout de pathlib
import platform # Ajout de platform

# Ajoute le répertoire parent (racine du projet) à sys.path
# pour permettre les imports de argumentation_analysis
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

# Importer la fonction refactorisée et find_valid_java_home
from argumentation_analysis.core.jvm_setup import find_valid_java_home, _build_effective_classpath
from argumentation_analysis.paths import LIBS_DIR, PROJECT_ROOT_DIR # Pour les chemins par défaut

def main():
    max_iterations = 500  # Nombre d'itérations pour le test
    delay_between_iterations = 0.01  # Petite pause pour éviter de surcharger trop vite

    try:
        # 1. Trouver JAVA_HOME
        java_home_selected = find_valid_java_home()
        if not java_home_selected:
            print("Chemin JAVA_HOME valide non trouvé. Vérifiez votre configuration Java.")
            return

        # 2. Obtenir le chemin JVM spécifique (dll/so)
        jvm_dll_path = jpype.getDefaultJVMPath() # Valeur par défaut de JPype
        # Essayer de construire un chemin plus spécifique si possible (logique similaire à initialize_jvm)
        _java_home_path = pathlib.Path(java_home_selected)
        _system = platform.system()
        _potential_jvm_dll = None
        if _system == "Windows":
            _potential_jvm_dll = _java_home_path / "bin" / "server" / "jvm.dll"
        elif _system == "Darwin": # macOS
            _potential_jvm_dll = _java_home_path / "lib" / "server" / "libjvm.dylib"
            if not _potential_jvm_dll.is_file() and (_java_home_path / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib").is_file():
                 _potential_jvm_dll = _java_home_path / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib"
        else: # Linux
            _potential_jvm_dll = _java_home_path / "lib" / "server" / "libjvm.so"
        
        if _potential_jvm_dll and _potential_jvm_dll.is_file():
            jvm_dll_path = str(_potential_jvm_dll.resolve())
            print(f"Utilisation du chemin JVM spécifique: {jvm_dll_path}")
        else:
            print(f"Chemin JVM spécifique non trouvé dans {java_home_selected}, utilisation du chemin par défaut de JPype: {jvm_dll_path}")

        # 3. Construire le classpath
        # Utiliser les chemins par défaut définis dans paths.py pour LIBS_DIR et PROJECT_ROOT_DIR
        # si le script est bien dans tests/
        script_dir = pathlib.Path(__file__).parent
        project_root_for_classpath = script_dir.parent # Remonte de tests/ à la racine du projet

        # S'assurer que LIBS_DIR est correct par rapport à la racine du projet détectée
        actual_libs_dir = project_root_for_classpath / "libs"

        combined_jar_list, classpath_str = _build_effective_classpath(
            lib_dir_path_str=str(actual_libs_dir),
            project_root_dir_str=str(project_root_for_classpath)
        )

        if not combined_jar_list:
            print("Classpath Tweety non construit ou vide. Assurez-vous que les JARs sont dans le répertoire libs/.")
            return

        print(f"Classpath (liste de JARs): {len(combined_jar_list)} JARs")
        # print(f"Classpath (chaîne): {classpath_str}") # Peut être très long
        print("Démarrage de la JVM avec -Xcheck:jni...")
        
        # Démarrer la JVM
        jpype.startJVM(jvm_dll_path, "-Xcheck:jni", classpath=combined_jar_list, convertStrings=False, ignoreUnrecognized=True)
        print("JVM démarrée.")

        JFile = jpype.JClass("java.io.File")

        print(f"Début de la boucle de test ({max_iterations} itérations)...")
        for i in range(max_iterations):
            temp_file = None
            try:
                # Appel à File.createTempFile()
                temp_file = JFile.createTempFile("test_jni_leak_", ".tmp")
                # print(f"Itération {i+1}/{max_iterations}: Fichier temporaire créé: {temp_file.getAbsolutePath()}")

                if temp_file is not None and temp_file.exists():
                    deleted = temp_file.delete()
                    # if not deleted:
                    #     print(f"Attention: Le fichier temporaire {temp_file.getAbsolutePath()} n'a pas pu être supprimé.")
                
                # Petite pause
                time.sleep(delay_between_iterations)

            except jpype.JException as e:
                print(f"Erreur Java lors de l'itération {i+1}: {e}")
                print(f"Message: {e.message()}")
                if hasattr(e, 'stacktrace'):
                    print(f"Stacktrace: {e.stacktrace()}")
                break 
            except Exception as e:
                print(f"Erreur Python lors de l'itération {i+1}: {e}")
                break
            finally:
                # Assurer la suppression même en cas d'erreur avant la suppression explicite
                if temp_file is not None and temp_file.exists():
                    temp_file.delete()
        
        print("Boucle de test terminée.")

    except Exception as e:
        print(f"Erreur lors de l'initialisation ou de l'exécution : {e}")
        if isinstance(e, jpype.JException) and hasattr(e, 'stacktrace'):
            print(f"Stacktrace Java: {e.stacktrace()}")

    finally:
        if jpype.isJVMStarted():
            print("Arrêt de la JVM.")
            jpype.shutdownJVM()
            print("JVM arrêtée.")

if __name__ == "__main__":
    main()
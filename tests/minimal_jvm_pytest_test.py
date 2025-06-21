import os
import pytest # Importer pytest pour s'assurer qu'on est dans son contexte
import jpype
from pathlib import Path # Pour construire jvmpath dans la fonction locale
from argumentation_analysis.core.jvm_setup import shutdown_jvm, find_valid_java_home, LIBS_DIR # initialize_jvm n'est plus utilisé directement ici
import logging

# Configurer un logger pour voir les messages de jvm_setup et d'autres modules
# Cela aidera à capturer plus d'informations si le test échoue.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Récupérer le logger spécifique utilisé dans jvm_setup.py pour s'assurer que ses messages sont visibles
jpype_logger = logging.getLogger("Orchestration.JPype")
jpype_logger.setLevel(logging.INFO) # Assurer que les messages INFO de jvm_setup sont capturés

# Si d'autres loggers sont pertinents (par exemple, celui de jpype_setup.py), les configurer aussi.
# jpype_setup_logger = logging.getLogger("JPypeSetup") # Ajuster le nom si nécessaire
# jpype_setup_logger.setLevel(logging.INFO)


def local_start_the_jvm_directly():
    """Fonction locale pour encapsuler l'appel direct à jpype.startJVM qui fonctionnait."""
    print("Appel direct de jpype.startJVM() depuis une fonction LOCALE au test...")
    
    portable_jdk_path = find_valid_java_home()
    if not portable_jdk_path:
        pytest.fail("Impossible de trouver un JDK valide pour le test minimal.")
    jvmpath = str(Path(portable_jdk_path) / "bin" / "server" / "jvm.dll")
    classpath = [] # Classpath vide pour le test
    # Utiliser les options qui ont fonctionné lors de l'appel direct
    jvm_options = ['-Xms128m', '-Xmx512m', '-Dfile.encoding=UTF-8', '-Djava.awt.headless=true']
    
    print(f"  LOCAL_CALL jvmpath: {jvmpath}")
    print(f"  LOCAL_CALL classpath: {classpath}")
    print(f"  LOCAL_CALL jvm_options: {jvm_options}")
    print(f"  LOCAL_CALL convertStrings: False")

    jpype.startJVM(
        jvmpath=jvmpath,
        classpath=classpath,
        *jvm_options,
        convertStrings=False
    )
    print(f"LOCAL_CALL jpype.startJVM() exécuté.")
    return True # Simuler le retour de initialize_jvm

@pytest.mark.real_jpype # Marqueur pour indiquer que ce test nécessite la vraie JVM
def test_minimal_jvm_startup_in_pytest(caplog): # Nom de fixture retiré
    """
    Teste le démarrage minimal de la JVM via une fonction LOCALE dans un contexte pytest.
    """
    caplog.set_level(logging.INFO)

    print(f"\n--- Début de test_minimal_jvm_startup_in_pytest (appel local) ---")
    original_use_real_jpype = os.environ.get('USE_REAL_JPYPE')
    os.environ['USE_REAL_JPYPE'] = 'true'
    print(f"Variable d'environnement USE_REAL_JPYPE (forcée pour ce test): '{os.environ.get('USE_REAL_JPYPE')}'")
    
    # La ligne suivante est supprimée car PORTABLE_JDK_PATH n'est plus importé.
    # Le chemin est maintenant obtenu dynamiquement dans local_start_the_jvm_directly.
    print(f"Chemin LIBS_DIR (variable globale importée): {LIBS_DIR}")

    jvm_was_started_before_this_test = jpype.isJVMStarted()
    print(f"JVM démarrée avant l'appel à la fonction locale (jpype.isJVMStarted()): {jvm_was_started_before_this_test}")
    
    call_succeeded = False
    try:
        print("Appel de local_start_the_jvm_directly()...")
        call_succeeded = local_start_the_jvm_directly()
        
        print(f"local_start_the_jvm_directly() a retourné: {call_succeeded}")
        assert call_succeeded, "local_start_the_jvm_directly devrait retourner True."
        
        current_jvm_status = jpype.isJVMStarted()
        print(f"État de la JVM après local_start_the_jvm_directly (jpype.isJVMStarted()): {current_jvm_status}")
        assert current_jvm_status, "La JVM devrait être marquée comme démarrée après un appel local réussi."
        
        print("SUCCESS: JVM démarrée via une fonction LOCALE dans le contexte pytest.")

    except Exception as e:
        print(f"ERREUR CRITIQUE lors de l'appel à local_start_the_jvm_directly ou des assertions: {e}")
        # Afficher les logs capturés par caplog pour aider au diagnostic
        log_messages = "\n".join([f"LOG CAPTURÉ ({record.levelname}): {record.message}" for record in caplog.records])
        print(f"Logs capturés par caplog:\n{log_messages}")
        raise # Relancer l'exception pour que pytest la marque comme un échec
    finally:
        print(f"--- Bloc finally de test_minimal_jvm_startup_in_pytest ---")
        # N'arrêter la JVM que si ce test l'a potentiellement démarrée et qu'elle est toujours active.
        # Si jvm_was_started_before_this_test est True, un autre test/fixture l'a démarrée.
        if call_succeeded and jpype.isJVMStarted() and not jvm_was_started_before_this_test:
             print("Tentative d'arrêt de la JVM (car démarrée par l'appel local)...")
             shutdown_jvm() # Utilise toujours la fonction de jvm_setup pour l'arrêt
             print("Arrêt de la JVM tenté.")
        elif not call_succeeded and jpype.isJVMStarted() and not jvm_was_started_before_this_test:
             print("Appel local a échoué mais la JVM semble démarrée. Tentative d'arrêt...")
             shutdown_jvm()
             print("Arrêt de la JVM tenté après échec de l'appel local.")
        else:
            print("La JVM n'a pas été (re)démarrée par ce test ou était déjà démarrée / est déjà arrêtée.")
        
        # Restaurer la variable d'environnement USE_REAL_JPYPE si elle existait
        if original_use_real_jpype is not None:
            os.environ['USE_REAL_JPYPE'] = original_use_real_jpype
        elif 'USE_REAL_JPYPE' in os.environ: # Si elle n'existait pas, la supprimer
            del os.environ['USE_REAL_JPYPE']
        print(f"Variable d'environnement USE_REAL_JPYPE restaurée à: '{os.environ.get('USE_REAL_JPYPE')}'")
        print(f"--- Fin de test_minimal_jvm_startup_in_pytest ---")
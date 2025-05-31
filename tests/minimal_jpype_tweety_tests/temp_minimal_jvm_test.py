import jpype
import jpype.imports
import os
import pathlib
import platform
import logging

# Configuration minimale du logger pour voir les messages de jvm_setup
logger = logging.getLogger()
# Si aucun handler n'est configuré pour le root logger, en ajouter un.
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO) # Mettre DEBUG pour plus de détails de jvm_setup

# Importer initialize_jvm depuis le chemin relatif correct
# Supposons que ce test est exécuté depuis la racine du projet
# ou que le PYTHONPATH est configuré pour trouver argumentation_analysis
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm, find_valid_java_home
    from argumentation_analysis.paths import PROJECT_ROOT_DIR, LIBS_DIR
except ImportError as e:
    print(f"Erreur d'importation critique pour le test minimal: {e}")
    print("Veuillez vérifier votre PYTHONPATH ou le répertoire d'exécution.")
    # Tenter une importation relative si exécuté depuis tests/minimal_jpype_tweety_tests
    import sys
    # Aller deux niveaux plus haut pour atteindre 'tests', puis un de plus pour la racine du projet
    # afin d'ajouter 'argumentation_analysis' au path.
    # Ceci est une rustine et dépend de la structure du projet.
    # Une meilleure solution est d'exécuter avec `python -m pytest` depuis la racine
    # ou d'avoir le projet installé en mode éditable.
    current_dir = pathlib.Path(__file__).parent.resolve()
    project_root_from_test = current_dir.parent.parent 
    sys.path.insert(0, str(project_root_from_test))
    print(f"Ajout de {project_root_from_test} au sys.path")
    try:
        from argumentation_analysis.core.jvm_setup import initialize_jvm, find_valid_java_home
        from argumentation_analysis.paths import PROJECT_ROOT_DIR, LIBS_DIR
    except ImportError as e2:
        print(f"Échec de l'importation même après ajustement du path: {e2}")
        # Si cela échoue toujours, on ne peut pas exécuter le test.
        # On pourrait lever une exception ici ou laisser JPype échouer.
        # Pour ce test, on va essayer de continuer avec un jpype.startJVM basique
        # si initialize_jvm n'est pas disponible, bien que cela ne reflète pas
        # la configuration réelle du projet.
        initialize_jvm = None 
        find_valid_java_home = None
        PROJECT_ROOT_DIR = pathlib.Path(".").resolve().parent.parent # Estimation
        LIBS_DIR = PROJECT_ROOT_DIR / "libs"


def test_minimal_jvm_startup_and_shutdown():
    """
    Teste uniquement le démarrage et l'arrêt de la JVM en utilisant la logique
    de jvm_setup.py si possible, ou un démarrage JPype basique sinon.
    """
    logging.info("Début du test minimal de la JVM.")
    jvm_started_by_this_test = False
    try:
        if jpype.isJVMStarted():
            logging.info("La JVM est déjà démarrée (probablement par conftest.py ou un test précédent).")
            # On ne peut pas vraiment tester l'arrêt/redémarrage proprement dans ce cas
            # sans affecter d'autres tests si la JVM est partagée.
            # Pour ce test isolé, on va juste vérifier qu'on peut interagir.
            java_version = jpype.java.lang.System.getProperty("java.version")
            logging.info(f"Version Java (depuis JVM existante): {java_version}")
            assert java_version is not None
            return

        logging.info("Tentative d'initialisation de la JVM via initialize_jvm...")
        
        # Utiliser la logique d'initialisation du projet si disponible
        if initialize_jvm:
            # S'assurer que LIBS_DIR est un str pour initialize_jvm
            # et que PROJECT_ROOT_DIR est bien défini.
            # Note: initialize_jvm s'attend à ce que PROJECT_ROOT_DIR soit défini dans argumentation_analysis.paths
            # et LIBS_DIR aussi.
            # Si on les a importés, ils devraient être corrects.
            
            # On s'assure que les répertoires nécessaires existent ou sont créés par jvm_setup
            # (comme _temp et portable_jdk s'ils sont utilisés)
            
            # Afficher le JAVA_HOME que find_valid_java_home trouverait
            if find_valid_java_home:
                logging.info(f"JAVA_HOME qui serait utilisé par find_valid_java_home: {find_valid_java_home()}")

            # Afficher le chemin de la JVM par défaut que JPype utiliserait
            try:
                default_jvm_path = jpype.getDefaultJVMPath()
                logging.info(f"Chemin JVM par défaut selon JPype (avant startJVM): {default_jvm_path}")
            except jpype.JVMNotFoundException:
                logging.info("JPype ne trouve pas de JVM par défaut (avant startJVM).")


            success = initialize_jvm(lib_dir_path=str(LIBS_DIR)) # Utilise les valeurs par défaut pour native_subdir et tweety_version
            
            if not success:
                # initialize_jvm loggue déjà beaucoup, mais on peut ajouter un message ici.
                logging.error("initialize_jvm a retourné False. La JVM n'a pas pu être démarrée correctement par la logique du projet.")
                # On pourrait lever une exception ici pour faire échouer le test clairement.
                # Pour l'instant, on laisse la vérification isJVMStarted() plus bas gérer cela.
            assert jpype.isJVMStarted(), "La JVM devrait être démarrée par initialize_jvm"
            jvm_started_by_this_test = True # Marquer que cette fonction a démarré la JVM
            logging.info("JVM démarrée avec succès via initialize_jvm.")

        else: # Fallback à un démarrage JPype basique si initialize_jvm n'a pas pu être importé
            logging.warning("initialize_jvm non disponible. Tentative de démarrage JPype basique.")
            # Essayer de trouver JAVA_HOME manuellement ou laisser JPype faire
            java_home = os.getenv("JAVA_HOME")
            jvm_path = None
            if java_home:
                logging.info(f"Utilisation de JAVA_HOME: {java_home}")
                # Construire le chemin vers jvm.dll/libjvm.so si possible
                # Ceci est une simplification et peut ne pas être robuste
                system = platform.system()
                if system == "Windows":
                    jvm_path_try = pathlib.Path(java_home) / "bin" / "server" / "jvm.dll"
                    if jvm_path_try.is_file(): jvm_path = str(jvm_path_try)
                elif system == "Darwin": # macOS
                    jvm_path_try = pathlib.Path(java_home) / "lib" / "server" / "libjvm.dylib"
                    if jvm_path_try.is_file(): jvm_path = str(jvm_path_try)
                else: # Linux
                    jvm_path_try = pathlib.Path(java_home) / "lib" / "server" / "libjvm.so"
                    if jvm_path_try.is_file(): jvm_path = str(jvm_path_try)
                
                if jvm_path:
                    logging.info(f"Chemin JVM explicite pour startJVM (basique): {jvm_path}")
                    jpype.startJVM(jvm_path, convertStrings=False)
                else:
                    logging.info("Chemin JVM non construit depuis JAVA_HOME, démarrage JPype sans chemin explicite.")
                    jpype.startJVM(convertStrings=False)
            else:
                logging.info("JAVA_HOME non défini, démarrage JPype sans chemin explicite.")
                jpype.startJVM(convertStrings=False) # Laisse JPype trouver la JVM
            
            assert jpype.isJVMStarted(), "La JVM devrait être démarrée par jpype.startJVM (basique)"
            jvm_started_by_this_test = True
            logging.info("JVM démarrée avec succès (mode basique).")

        # Vérification simple
        java_version = jpype.java.lang.System.getProperty("java.version")
        logging.info(f"Version Java (après démarrage): {java_version}")
        assert java_version is not None

    except Exception as e:
        logging.error(f"Une exception est survenue pendant le test minimal de la JVM: {e}", exc_info=True)
        # Afficher le statut de la JVM en cas d'erreur
        logging.error(f"Statut JVM au moment de l'exception: {'Démarrée' if jpype.isJVMStarted() else 'Arrêtée'}")
        raise # Propager l'exception pour faire échouer le test
    finally:
        # N'arrêter la JVM que si ce test l'a démarrée ET qu'elle est effectivement démarrée.
        # Cela évite d'arrêter une JVM partagée par conftest.py ou d'autres tests.
        if jvm_started_by_this_test and jpype.isJVMStarted():
            logging.info("Arrêt de la JVM démarrée par ce test.")
            jpype.shutdownJVM()
            logging.info("JVM arrêtée.")
        elif not jvm_started_by_this_test and jpype.isJVMStarted():
            logging.info("La JVM était déjà démarrée avant ce test et ne sera pas arrêtée par celui-ci.")
        elif not jpype.isJVMStarted():
            logging.info("La JVM n'est pas (ou plus) démarrée à la fin du test.")

if __name__ == "__main__":
    # Permet d'exécuter ce fichier directement avec `python tests/minimal_jpype_tweety_tests/temp_minimal_jvm_test.py`
    # pour un débogage plus facile.
    print("Exécution du test minimal en mode standalone...")
    # Configurer un logger basique si exécuté en standalone
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    
    # Créer une instance de test et appeler la méthode de test
    # Ceci est une simulation de ce que pytest ferait.
    class TestMinimal:
        def run_test(self):
            test_minimal_jvm_startup_and_shutdown()

    test_runner = TestMinimal()
    try:
        test_runner.run_test()
        print("\nTest minimal de la JVM terminé avec succès (standalone).")
    except Exception as e:
        print(f"\nTest minimal de la JVM a échoué (standalone): {e}")
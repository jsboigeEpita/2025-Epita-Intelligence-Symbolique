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
logger.setLevel(logging.DEBUG) # Mettre DEBUG pour plus de détails de jvm_setup

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


def test_minimal_jvm_startup_and_shutdown(integration_jvm): # Utilise la fixture
    """
    Teste que la JVM est démarrée lorsque la fixture integration_jvm est utilisée.
    """
    # L'import de jpype doit se faire ici, APRES que les fixtures aient potentiellement
    # modifié sys.modules pour utiliser le vrai jpype.
    import jpype
    import jpype.imports # Nécessaire pour jpype.java...

    logging.info("Début du test minimal de la JVM (utilisant la fixture integration_jvm).")
    
    # La fixture integration_jvm (via activate_jpype_mock_if_needed) devrait avoir:
    # 1. Mis le vrai module jpype dans sys.modules.
    # 2. Démarré la JVM.
    
    assert jpype.isJVMStarted(), "La JVM devrait être démarrée par la fixture integration_jvm."
    logging.info("Assertion jpype.isJVMStarted() est VRAIE.")
    
    # Vérification simple que nous pouvons interagir avec la JVM
    try:
        java_version = jpype.java.lang.System.getProperty("java.version")
        logging.info(f"Version Java (depuis JVM gérée par fixture): {java_version}")
        assert java_version is not None
    except Exception as e:
        logging.error(f"Erreur lors de l'interaction avec la JVM démarrée: {e}", exc_info=True)
        pytest.fail(f"Erreur interaction JVM: {e}")
    
    logging.info("Test minimal de la JVM (avec fixture) terminé avec succès.")

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
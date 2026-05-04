import jpype
import jpype.imports
import os
import logging
import time  # Ajout de l'import time

# Configuration du logging pour voir les messages de JPype et les nôtres
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_jvm_path():
    """Trouve un chemin valide vers la JVM."""
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        # Essayer les emplacements courants pour libjvm.so ou jvm.dll
        potential_paths = [
            os.path.join(
                java_home, "jre", "lib", "server", "jvm.dll"
            ),  # Windows Oracle JRE style
            os.path.join(
                java_home, "lib", "server", "jvm.dll"
            ),  # Windows OpenJDK style
            os.path.join(
                java_home, "jre", "lib", "amd64", "server", "libjvm.so"
            ),  # Linux
            os.path.join(
                java_home, "lib", "server", "libjvm.so"
            ),  # Linux OpenJDK style
        ]
        for path in potential_paths:
            if os.path.exists(path):
                logger.info(f"Utilisation de la JVM trouvée à : {path}")
                return path
    logger.warning(
        "JAVA_HOME n'est pas défini ou JVM non trouvée aux emplacements standards. Utilisation de jpype.getDefaultJVMPath()."
    )
    return jpype.getDefaultJVMPath()


def main():
    jvm_path = find_jvm_path()
    # max_iterations = 10000  # Nombre d'itérations pour le test - Remplacé par iteration_limit

    # Limites pour l'arrêt automatique
    max_duration_seconds = 15
    iteration_limit = 200  # Limite d'itérations pour un arrêt rapide

    actual_max_iterations = (
        iteration_limit  # Le script s'arrêtera au premier des deux seuils atteints
    )

    start_time = time.time()

    try:
        logger.info(f"Démarrage de la JVM depuis : {jvm_path}")
        jpype.startJVM(
            jvm_path,
            "-Xcheck:jni",  # Activer les vérifications JNI
            "-Djava.class.path=.",  # Chemin de classe minimal
            convertStrings=False,
        )
        logger.info("JVM démarrée avec succès.")

        # Importer les classes Java nécessaires
        JFile = jpype.JClass("java.io.File")
        JNetworkInterface = jpype.JClass("java.net.NetworkInterface")

        logger.info(
            f"Début de la boucle de test (jusqu'à {actual_max_iterations} itérations ou {max_duration_seconds} secondes)..."
        )
        for i in range(actual_max_iterations):
            current_time = time.time()
            elapsed_time = current_time - start_time

            if elapsed_time > max_duration_seconds:
                logger.info(
                    f"Arrêt du script après {elapsed_time:.2f} secondes (limite de {max_duration_seconds}s atteinte)."
                )
                break

            if (
                i >= actual_max_iterations
            ):  # Devrait être géré par la range, mais double sécurité
                logger.info(
                    f"Arrêt du script après {i} itérations (limite de {actual_max_iterations} atteinte)."
                )
                break

            if (i + 1) % 50 == 0:  # Log plus fréquent pour voir la progression
                logger.info(
                    f"Itération {i + 1}/{actual_max_iterations}, Temps écoulé: {elapsed_time:.2f}s"
                )

            # Test 1: File.createTempFile
            temp_file = None
            try:
                temp_file = JFile.createTempFile("jniLeakTest", ".tmp")
                # logger.debug(f"Fichier temporaire créé : {temp_file.getAbsolutePath()}")
            except jpype.JavaException as e:
                logger.error(
                    f"Erreur Java lors de la création du fichier temporaire : {e}"
                )
                logger.error(f"Stacktrace Java : \n{e.stacktrace()}")
            finally:
                if temp_file and temp_file.exists():
                    temp_file.delete()

            # Test 2: NetworkInterface.getNetworkInterfaces
            try:
                interfaces = JNetworkInterface.getNetworkInterfaces()
                if interfaces:
                    while interfaces.hasMoreElements():
                        iface = interfaces.nextElement()
                        # logger.debug(f"Interface : {iface.getName()}")
                        # Simuler une petite opération pour s'assurer que l'objet est utilisé
                        _ = iface.getDisplayName()
            except jpype.JavaException as e:
                logger.error(
                    f"Erreur Java lors de la récupération des interfaces réseau : {e}"
                )
                logger.error(f"Stacktrace Java : \n{e.stacktrace()}")

        logger.info("Boucle de test terminée.")

    except Exception as e:
        logger.error(f"Une erreur Python s'est produite : {e}", exc_info=True)
    finally:
        if jpype.isJVMStarted():
            logger.info("Arrêt de la JVM...")
            jpype.shutdownJVM()
            logger.info("JVM arrêtée.")


if __name__ == "__main__":
    # Assurer que JAVA_HOME est pris depuis .env si setup_project_env.ps1 a été exécuté
    # Pour un test standalone, il est préférable de le configurer manuellement ou via l'IDE
    # Ici, on suppose qu'il est déjà dans l'environnement si nécessaire.
    # Alternativement, charger .env ici aussi:
    try:
        from dotenv import load_dotenv

        # Supposer que .env est à la racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dotenv_path = os.path.join(project_root, ".env")
        if os.path.exists(dotenv_path):
            logger.info(
                f"Chargement des variables d'environnement depuis {dotenv_path}"
            )
            load_dotenv(dotenv_path=dotenv_path, override=True)
        else:
            logger.info(
                f".env non trouvé à {dotenv_path}, utilisation des variables d'environnement existantes."
            )
    except ImportError:
        logger.warning(
            "python-dotenv non installé. Utilisation des variables d'environnement existantes."
        )

    main()

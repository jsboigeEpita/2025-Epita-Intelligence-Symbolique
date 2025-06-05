import jpype
import jpype.imports
import os
import logging
import time
from tqdm import tqdm

# Configuration du logging basic pour voir les messages de JPype si `-Djpype.debug=true` est utilisé
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("standalone_jpype_test")

# Chemins essentiels
project_root = os.path.dirname(os.path.abspath(__file__)) # Devrait être c:\dev\2025-Epita-Intelligence-Symbolique
jvm_path = os.path.join(project_root, "portable_jdk", "jdk-17.0.15+6", "bin", "server", "jvm.dll")
libs_dir = os.path.join(project_root, "libs")
native_libs_dir = os.path.join(libs_dir, "native")

# Classpath minimal - juste le JAR principal de Tweety pour commencer
# (on pourrait ajouter d'autres JARs si nécessaire pour des tests plus poussés)
core_tweety_jar = os.path.join(libs_dir, "org.tweetyproject.tweety-full-1.28-with-dependencies.jar")
classpath_arg = [core_tweety_jar]

# Arguments JVM
jvm_args = [
    f"-Djava.library.path={native_libs_dir}",
    "-Xms128m", # Mémoire réduite pour ce test minimal
    "-Xmx256m",
    # "-Djpype.debug=true", # Peut être décommenté plus tard
    # "-Djpype.trace=true"  # Peut être décommenté plus tard
]

logger.info(f"Utilisation de jvm_path: {jvm_path}")
logger.info(f"Utilisation du classpath: {classpath_arg}")
logger.info(f"Utilisation des arguments JVM: {jvm_args}")

# Test avec tqdm avant de démarrer la JVM
logger.info("Test de tqdm avant le démarrage de la JVM...")
for i in tqdm(range(5), desc="Test tqdm"):
    time.sleep(0.1)
logger.info("Test de tqdm terminé.")

try:
    if jpype.isJVMStarted():
        logger.info("JVM déjà démarrée (inattendu dans ce script standalone). Arrêt...")
        jpype.shutdownJVM()
        logger.info("JVM arrêtée.")

    logger.info("Tentative de démarrage de la JVM...")
    jpype.startJVM(
        jvm_path,
        classpath=classpath_arg,
        *jvm_args,
        convertStrings=False,
        ignoreUnrecognized=True
    )
    logger.info(f"JVM démarrée avec succès: {jpype.isJVMStarted()}")

    if jpype.isJVMStarted():
        # Test simple : importer une classe Java
        try:
            System = jpype.JClass("java.lang.System")
            logger.info(f"java.lang.System.getProperty('java.version'): {System.getProperty('java.version')}")
        except Exception as e:
            logger.error(f"Erreur lors de l'utilisation de JClass: {e}")

except Exception as e:
    logger.error(f"Une erreur s'est produite lors du démarrage ou de l'utilisation de la JVM: {e}", exc_info=True)
    # Afficher la trace de la pile Python complète
    import traceback
    traceback.print_exc()


finally:
    if jpype.isJVMStarted():
        logger.info("Tentative d'arrêt de la JVM...")
        jpype.shutdownJVM()
        logger.info("JVM arrêtée.")
    else:
        logger.info("La JVM n'a pas été démarrée ou a déjà été arrêtée.")

logger.info("Script standalone terminé.")
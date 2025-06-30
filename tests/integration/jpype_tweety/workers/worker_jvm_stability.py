# -*- coding: utf-8 -*-
import jpype
import jpype.imports
import os
from pathlib import Path
import sys
import logging

# Configuration du logger pour le worker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_project_root_from_env() -> Path:
    """
    Récupère la racine du projet depuis la variable d'environnement PROJECT_ROOT.
    """
    project_root_str = os.getenv("PROJECT_ROOT")
    if not project_root_str:
        raise RuntimeError("La variable d'environnement PROJECT_ROOT n'est pas définie.")
    return Path(project_root_str)

def test_jvm_stability_logic():
    """
    Contient la logique de test pour la stabilité de base de la JVM,
    exécutée dans un sous-processus.
    """
    print("--- Début du worker pour test_jvm_stability_logic ---")

    # Construction du classpath
    project_root = get_project_root_from_env()
    libs_dir = project_root / "libs" / "tweety"
    
    if not libs_dir.exists():
        raise FileNotFoundError(f"Le répertoire des bibliothèques Tweety n'existe pas : {libs_dir}")

    full_jar_path = libs_dir / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
    if not full_jar_path.exists():
        raise FileNotFoundError(f"Le JAR complet 'tweety-full' n'a pas été trouvé dans {libs_dir}")

    classpath = str(full_jar_path.resolve())
    print(f"Classpath construit : {classpath}")

    # Démarrage de la JVM
    if not jpype.isJVMStarted():
        try:
            print("--- La JVM n'est pas démarrée. Tentative de démarrage par le worker... ---")
            jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", classpath=classpath, convertStrings=False)
            print("--- JVM démarrée avec succès par le worker ---")
        except Exception as e:
            print(f"ERREUR: Échec du démarrage de la JVM par le worker : {e}", file=sys.stderr)
            raise
    else:
        print("--- La JVM est déjà démarrée (probablement par pytest). Le worker l'utilise. ---")

    # Logique de test issue de TestJvmStability
    try:
        logger.info("Vérification si la JVM est démarrée...")
        assert jpype.isJVMStarted(), "La JVM devrait être démarrée."
        logger.info("JVM démarrée avec succès.")

        logger.info("Tentative de chargement de java.lang.String...")
        StringClass = jpype.JClass("java.lang.String")
        assert StringClass is not None, "java.lang.String n'a pas pu être chargée."
        logger.info("java.lang.String chargée avec succès.")
        
        # Test simple d'utilisation
        java_string = StringClass("Hello from JPype worker")
        py_string = str(java_string)
        assert py_string == "Hello from JPype worker", "La conversion de chaîne Java en Python a échoué."
        logger.info(f"Chaîne Java créée et convertie: '{py_string}'")

    except Exception as e:
        logger.error(f"Erreur lors du test de stabilité de la JVM: {e}")
        # En cas d'erreur, nous voulons que le processus worker échoue
        # et propage l'erreur au test principal.
        raise
    finally:
        # Ne pas arrêter la JVM ici. La fixture pytest s'en chargera.
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("--- JVM arrêtée avec succès dans le worker ---")
        print("--- Le worker a terminé sa tâche. La gestion de l'arrêt de la JVM est laissée au processus principal. ---")

    print("--- Assertions du worker réussies ---")


if __name__ == "__main__":
    try:
        test_jvm_stability_logic()
        print("--- Le worker de stabilité JVM s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker de stabilité JVM : {e}", file=sys.stderr)
        sys.exit(1)
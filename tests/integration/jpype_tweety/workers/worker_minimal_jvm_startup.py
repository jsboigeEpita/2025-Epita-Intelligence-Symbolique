# -*- coding: utf-8 -*-
import jpype
import jpype.imports
import os
from pathlib import Path
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_project_root_from_env() -> Path:
    project_root_str = os.getenv("PROJECT_ROOT")
    if not project_root_str:
        raise RuntimeError("La variable d'environnement PROJECT_ROOT n'est pas définie.")
    return Path(project_root_str)

def test_minimal_startup_logic():
    """
    Logique de test pour un démarrage minimal de la JVM.
    S'assure que la JVM peut être démarrée et qu'une classe de base est accessible.
    """
    print("--- Début du worker pour test_minimal_startup_logic ---")
    
    if jpype.isJVMStarted():
        logger.warning("La JVM était déjà démarrée au début du worker. Ce n'est pas attendu.")
        # Ce n'est pas une erreur fatale, mais c'est bon à savoir.
    
    # Construction du classpath (même si vide, la logique est là)
    project_root = get_project_root_from_env()
    libs_dir = project_root / "libs" / "tweety"
    
    # Pour un test de démarrage minimal, le classpath peut être vide ou pointer
    # vers un JAR connu et non corrompu si on veut tester le chargement.
    # Pour rester minimal, on utilise que le JAR 'tweety-full'.
    full_jar_path = libs_dir / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
    if not full_jar_path.exists():
         # On ne peut pas continuer sans le jar.
        print(f"ERREUR: Le JAR Tweety est introuvable à {full_jar_path}", file=sys.stderr)
        raise FileNotFoundError(f"Le JAR Tweety est introuvable à {full_jar_path}")

    classpath = str(full_jar_path)
    
    # Démarrage de la JVM
    try:
        jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", classpath=classpath, convertStrings=False)
        print("--- JVM démarrée avec succès dans le worker ---")
    except Exception as e:
        print(f"ERREUR: Échec du démarrage de la JVM : {e}", file=sys.stderr)
        raise

    try:
        assert jpype.isJVMStarted(), "La JVM devrait être active après startJVM."
        logger.info("Assertion jpype.isJVMStarted() réussie.")
        
        # Test de base pour s'assurer que la JVM est fonctionnelle
        StringClass = jpype.JClass("java.lang.String")
        java_string = StringClass("Test minimal réussi")
        assert str(java_string) == "Test minimal réussi"
        logger.info("Test de création/conversion de java.lang.String réussi.")
        
        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(f"Erreur durant l'exécution de la logique du worker: {e}", exc_info=True)
        raise
    finally:
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
            print("--- JVM arrêtée avec succès dans le worker ---")


if __name__ == "__main__":
    try:
        test_minimal_startup_logic()
        print("--- Le worker de démarrage minimal s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker de démarrage minimal : {e}", file=sys.stderr)
        sys.exit(1)
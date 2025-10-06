import sys
import pytest
import logging

# Configurer le logging de base pour voir ce qui se passe
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

logging.info("--- safe_pytest_runner.py: Démarrage ---")

# Étape 1: Initialisation de la JVM avant tout le reste
try:
    logging.info("Tentative d'initialisation de la JVM...")
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    initialize_jvm()
    logging.info("JVM initialisée avec succès.")
except Exception as e:
    logging.error(f"ÉCHEC CRITIQUE de l'initialisation de la JVM: {e}")
    # On ne quitte pas, pour voir si pytest peut quand même s'exécuter
    # pour les tests non-JVM.

# Étape 2: Lancer pytest avec les arguments passés au script
try:
    logging.info(f"Lancement de pytest.main avec les arguments: {sys.argv[1:]}")
    exit_code = pytest.main(sys.argv[1:])
    logging.info(f"pytest.main a terminé avec le code de sortie: {exit_code}")
    sys.exit(exit_code)
except Exception as e:
    logging.error(f"Échec de l'exécution de pytest.main: {e}")
    sys.exit(1)
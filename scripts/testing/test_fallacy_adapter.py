# ===== ONE-LINER AUTO-ACTIVATEUR =====
import scripts.core.auto_env  # Auto-activation environnement intelligent
# =====================================

import sys
from pathlib import Path
import logging

# Configuration du logging pour le test
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("TestFallacyAdapter")

# S'assurer que la racine du projet est dans sys.path pour que bootstrap fonctionne correctement
try:
    current_script_path = Path(__file__).resolve()
    # Correction: Remonter de trois niveaux pour atteindre la racine du projet
    # scripts/testing/test_fallacy_adapter.py -> scripts/testing -> scripts -> project_root
    project_root_for_test = current_script_path.parent.parent.parent
    if str(project_root_for_test) not in sys.path:
        sys.path.insert(0, str(project_root_for_test))
        logger.info(f"Ajout de {project_root_for_test} à sys.path pour le test.")
except NameError:
    logger.error("__file__ non défini. Assurez-vous que le script est exécuté en tant que fichier.")
    project_root_for_test = Path.cwd().parent # Tentative de fallback améliorée, mais __file__ est préférable

try:
    from argumentation_analysis.core.bootstrap import initialize_project_environment, ProjectContext
except ImportError as e:
    logger.error(f"Impossible d'importer depuis project_core.bootstrap: {e}")
    logger.error("Assurez-vous que la racine du projet est correctement ajoutée à sys.path.")
    sys.exit(1)

def run_minimal_test():
    logger.info("Début du test minimal de l'adaptateur ContextualFallacyDetector...")

    # Déterminer le chemin du fichier .env.example ou .env
    env_file_path = project_root_for_test / "argumentation_analysis" / ".env.example"
    if not env_file_path.exists():
        env_file_path = project_root_for_test / "argumentation_analysis" / ".env"
    
    if not env_file_path.exists():
        logger.warning(f"Fichier .env non trouvé ({project_root_for_test / 'argumentation_analysis / .env[.example]'}), le test pourrait être limité.")
        env_file_path = None
    else:
        logger.info(f"Utilisation du fichier .env: {env_file_path}")

    # Initialiser l'environnement
    logger.info("Initialisation de l'environnement du projet...")
    initialized_context: ProjectContext = initialize_project_environment(
        env_path_str=str(env_file_path) if env_file_path else None,
        root_path_str=str(project_root_for_test)
    )

    if not initialized_context:
        logger.error("Échec de l'initialisation du contexte du projet.")
        return

    informal_agent = initialized_context.informal_agent
    if not informal_agent:
        logger.error("L'agent informel n'a pas été initialisé dans le contexte.")
        if not initialized_context.llm_service:
            logger.error("  Cause possible: LLMService non initialisé.")
        if not initialized_context.fallacy_detector:
            logger.error("  Cause possible: FallacyDetector (ou son adaptateur) non initialisé.")
        return

    logger.info(f"Agent informel récupéré: {type(informal_agent)}")
    if hasattr(informal_agent, 'tools') and "fallacy_detector" in informal_agent.tools:
        logger.info(f"Détecteur de sophismes dans l'agent: {type(informal_agent.tools['fallacy_detector'])}")
    else:
        logger.warning("L'agent informel ne semble pas avoir de détecteur de sophismes configuré.")

    test_text = "Les experts disent que c'est vrai, donc ça doit l'être. Tout le monde le pense."
    logger.info(f"Appel de analyze_fallacies avec le texte: '{test_text}'")

    try:
        fallacies = informal_agent.analyze_fallacies(test_text)
        logger.info(f"Résultat de analyze_fallacies (nombre de sophismes: {len(fallacies)}):")
        for i, fallacy in enumerate(fallacies):
            logger.info(f"  Sophisme {i+1}: {fallacy.get('fallacy_type', 'N/A')} - {fallacy.get('marker', 'N/A')}")
        
        if not fallacies:
            logger.info("Aucun sophisme détecté, ce qui peut être normal pour ce texte simple et ce détecteur.")

    except AttributeError as ae:
        logger.error(f"ERREUR AttributeError lors de l'appel à analyze_fallacies: {ae}", exc_info=True)
        logger.error("Cela signifie que l'interface n'est toujours pas correcte.")
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue lors de l'appel à analyze_fallacies: {e}", exc_info=True)

    logger.info("Fin du test minimal.")

if __name__ == "__main__":
    run_minimal_test()
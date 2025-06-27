import logging
import sys
import traceback
from pathlib import Path

# Ajouter la racine du projet au PYTHONPATH pour que les imports fonctionnent
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration du logging pour voir les messages des composants
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("DebugScript")

try:
    logger.info("Début du script de débogage...")
    
    logger.info("Importation de Kernel...")
    from semantic_kernel import Kernel
    
    logger.info("Importation de PropositionalLogicAgent...")
    from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
    
    logger.info("Création d'une instance de Kernel...")
    kernel = Kernel()
    
    logger.info("Tentative d'instanciation de PropositionalLogicAgent...")
    agent = PropositionalLogicAgent(kernel=kernel)
    
    logger.info("Instanciation de l'agent réussie !")
    logger.info(f"Agent créé: {agent.name}")
    
except Exception as e:
    logger.error("Échec de l'instanciation de l'agent.")
    logger.error(f"Exception: {e}")
    logger.error("Traceback complet:")
    traceback.print_exc()
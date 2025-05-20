"""
Script pour vérifier que toutes les importations fonctionnent correctement.
"""

import importlib
import sys
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Ajouter le répertoire parent au PYTHONPATH
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
    logging.info(f"Répertoire parent ajouté au PYTHONPATH: {parent_dir}")

# Liste des modules à vérifier
modules_to_check = [
    # Modules principaux
    "argumentation_analysis",
    "argumentation_analysis.core",
    "argumentation_analysis.agents",
    "argumentation_analysis.orchestration",
    "argumentation_analysis.paths",
    
    # Sous-modules
    "argumentation_analysis.core.llm_service",
    "argumentation_analysis.core.jvm_setup",
    "argumentation_analysis.core.shared_state",
    
    # Modules avec redirection
    "argumentation_analysis.agents.core.extract",
    "argumentation_analysis.agents.extract",  # Devrait être redirigé vers agents.core.extract
    
    # Classes et fonctions spécifiques
    "argumentation_analysis.core.llm_service.create_llm_service",
    "argumentation_analysis.agents.core.extract.extract_agent.ExtractAgent",
    "argumentation_analysis.agents.extract.ExtractAgent",  # Devrait fonctionner via la redirection
]

# Vérifier chaque module
success_count = 0
failure_count = 0

for module_name in modules_to_check:
    try:
        if "." in module_name and module_name.split(".")[-2] != module_name.split(".")[-1]:
            # Pour les attributs spécifiques (comme create_llm_service)
            parent_module_name = ".".join(module_name.split(".")[:-1])
            attr_name = module_name.split(".")[-1]
            
            parent_module = importlib.import_module(parent_module_name)
            getattr(parent_module, attr_name)  # Vérifie si l'attribut existe
            
            logging.info(f"✅ Attribut '{attr_name}' du module '{parent_module_name}' importé avec succès.")
        else:
            # Pour les modules
            module = importlib.import_module(module_name)
            logging.info(f"✅ Module '{module_name}' importé avec succès.")
        
        success_count += 1
    except ImportError as e:
        logging.error(f"❌ Erreur lors de l'importation du module '{module_name}': {e}")
        failure_count += 1
    except AttributeError as e:
        logging.error(f"❌ Attribut non trouvé dans '{module_name}': {e}")
        failure_count += 1

# Afficher le résultat
logging.info(f"\nRésultat: {success_count}/{len(modules_to_check)} modules importés avec succès.")
if failure_count > 0:
    logging.warning(f"⚠️ {failure_count} modules n'ont pas pu être importés.")
    sys.exit(1)
else:
    logging.info("✅ Toutes les importations fonctionnent correctement.")
    sys.exit(0)
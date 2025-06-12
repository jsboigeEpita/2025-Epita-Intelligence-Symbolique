"""
Script pour vérifier que toutes les importations fonctionnent correctement.
"""

import project_core.core_from_scripts.auto_env
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
parent_dir = Path(__file__).resolve().parent.parent.parent # MODIFIÉ: Remonter à la racine du projet
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
    logging.info(f"Répertoire racine du projet ajouté au PYTHONPATH: {parent_dir}")

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
        # Vérifier si on tente d'importer un attribut spécifique d'un module
        # Heuristique: si le dernier composant n'est pas égal à l'avant-dernier (ex: core.llm_service.create_llm_service)
        # et qu'il y a plus d'un composant.
        parts = module_name.split('.')
        is_attribute_import = len(parts) > 1 and parts[-1][0].islower() # Souvent les fonctions/attributs commencent par minuscule

        if is_attribute_import:
            # Logique existante pour les attributs spécifiques
            parent_module_name = ".".join(parts[:-1])
            attr_name = parts[-1]
            
            # On importe d'abord le module parent
            parent_success, parent_message = test_module_import_by_name(parent_module_name)
            if parent_success:
                parent_module = importlib.import_module(parent_module_name)
                getattr(parent_module, attr_name)  # Vérifie si l'attribut existe
                logging.info(f"✅ Attribut '{attr_name}' du module '{parent_module_name}' accessible avec succès.")
                success_count += 1
            else:
                logging.error(f"❌ Échec de l'import du module parent '{parent_module_name}' pour l'attribut '{attr_name}': {parent_message}")
                failure_count += 1
        else:
            # Pour les modules simples, utiliser la fonction utilitaire
            success, message = test_module_import_by_name(module_name)
            # Le message de l'utilitaire est déjà formaté, mais on peut le préfixer si besoin
            # ou utiliser le logger de l'utilitaire directement.
            # Pour l'instant, on logue le message retourné.
            if success:
                logging.info(message)
                success_count += 1
            else:
                logging.error(message)
                failure_count += 1
                
    except ImportError as e: # Devrait être attrapé par test_module_import_by_name pour les modules
        logging.error(f"❌ Erreur lors de l'importation (ImportError) pour '{module_name}': {e}")
        failure_count += 1
    except AttributeError as e: # Spécifique à la logique getattr
        logging.error(f"❌ Attribut non trouvé (AttributeError) pour '{module_name}': {e}")
        failure_count += 1
    except Exception as e_unexpected: # Attraper d'autres erreurs inattendues
        logging.error(f"❌ Erreur inattendue pour '{module_name}': {e_unexpected}", exc_info=True)
        failure_count +=1

# Afficher le résultat
logging.info(f"\nRésultat: {success_count}/{len(modules_to_check)} modules importés avec succès.")
if failure_count > 0:
    logging.warning(f"⚠️ {failure_count} modules n'ont pas pu être importés.")
    sys.exit(1)
else:
    logging.info("✅ Toutes les importations fonctionnent correctement.")
    sys.exit(0)
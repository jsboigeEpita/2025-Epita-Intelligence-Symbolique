#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester que toutes les importations fonctionnent correctement.

Ce script vérifie que les importations directes et les redirections
fonctionnent correctement, ce qui est essentiel pour s'assurer que
les modifications de structure n'ont pas cassé le code existant.
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

def test_import(module_name, attr_name=None):
    """
    Teste l'importation d'un module ou d'un attribut d'un module.
    
    Args:
        module_name (str): Nom du module à importer
        attr_name (str, optional): Nom de l'attribut à vérifier
    
    Returns:
        bool: True si l'importation a réussi, False sinon
    """
    try:
        module = importlib.import_module(module_name)
        if attr_name:
            getattr(module, attr_name)
            logging.info(f"✅ Attribut '{attr_name}' du module '{module_name}' importé avec succès.")
        else:
            logging.info(f"✅ Module '{module_name}' importé avec succès.")
        return True
    except ImportError as e:
        logging.error(f"❌ Erreur lors de l'importation du module '{module_name}': {e}")
        return False
    except AttributeError as e:
        logging.error(f"❌ Attribut '{attr_name}' non trouvé dans le module '{module_name}': {e}")
        return False

def main():
    # Liste des modules à tester
    modules_to_test = [
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
    ]
    
    # Liste des attributs à tester
    attributes_to_test = [
        # Fonctions et classes exposées
        ("argumentation_analysis.core.llm_service", "create_llm_service"),
        ("argumentation_analysis.core.jvm_setup", "initialize_jvm"),
        ("argumentation_analysis.core.jvm_setup", "download_tweety_jars"),
        
        # Classes et fonctions via redirection
        ("argumentation_analysis.agents.extract", "extract_agent"),
        ("argumentation_analysis.agents.core.extract", "extract_agent"),
    ]
    
    # Tester les modules
    success_count = 0
    total_count = len(modules_to_test) + len(attributes_to_test)
    
    logging.info("=== Test des importations de modules ===")
    for module_name in modules_to_test:
        if test_import(module_name):
            success_count += 1
    
    logging.info("\n=== Test des importations d'attributs ===")
    for module_name, attr_name in attributes_to_test:
        if test_import(module_name, attr_name):
            success_count += 1
    
    # Afficher le résultat
    logging.info(f"\nRésultat: {success_count}/{total_count} importations réussies.")
    if success_count == total_count:
        logging.info("✅ Toutes les importations fonctionnent correctement.")
        return 0
    else:
        logging.warning(f"⚠️ {total_count - success_count} importations ont échoué.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
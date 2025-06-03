# -*- coding: utf-8 -*-
"""
Script de test pour vérifier l'importation des modules principaux
du projet Intelligence Symbolique.
"""

import sys
import os
import importlib
from pathlib import Path

def test_import(module_name):
    """Teste l'importation d'un module et retourne le résultat."""
    try:
        module = importlib.import_module(module_name)
        return True, f"✓ Module '{module_name}' importé avec succès"
    except ImportError as e:
        return False, f"✗ Erreur lors de l'importation du module '{module_name}': {str(e)}"
    except Exception as e:
        return False, f"✗ Erreur inattendue lors de l'importation du module '{module_name}': {str(e)}"

def main():
    """Fonction principale pour tester les importations."""
    print("Test d'importation des modules principaux du projet Intelligence Symbolique")
    print("=" * 80)
    
    # Ajouter le répertoire du projet au chemin de recherche Python
    project_root = Path(__file__).resolve().parent.parent.parent # MODIFIÉ: Remonter à la racine du projet
    sys.path.insert(0, str(project_root))
    
    # Liste des modules à tester (basée sur la structure réelle du projet)
    modules_to_test = [
        "argumentation_analysis",
        "argumentation_analysis.services.cache_service",
        "argumentation_analysis.services.crypto_service",
        "argumentation_analysis.services.definition_service",
        "argumentation_analysis.services.extract_service",
        "argumentation_analysis.services.fetch_service",
        "argumentation_analysis.utils.system_utils",
        "argumentation_analysis.utils.taxonomy_loader"
    ]
    
    # Tester chaque module
    success_count = 0
    total_count = len(modules_to_test)
    
    for module_name in modules_to_test:
        success, message = test_module_import_by_name(module_name) # Utilisation de la fonction importée
        print(message)
        if success:
            success_count += 1
    
    # Afficher le résumé
    print("\nRésumé:")
    print(f"Modules importés avec succès: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\nTous les modules ont été importés avec succès!")
    else:
        print("\nCertains modules n'ont pas pu être importés. Vérifiez les erreurs ci-dessus.")

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
import sys
import os
import importlib.util

def test_module_import(module_path):
    """Teste l'importation d'un module Python."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec is None:
            return False, f"Impossible de charger le module: {module_path}"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, f"Module importé avec succès: {module_path}"
    except Exception as e:
        return False, f"Erreur lors de l'importation de {module_path}: {str(e)}"

def run_tests():
    """Exécute les tests d'importation sur les modules Python réorganisés."""
    modules_to_test = [
        "scripts/testing/simulation_agent_informel.py",
        "scripts/testing/test_agent_informel.py",
        "scripts/utils/test_imports_utils.py"
    ]
    
    print("Test des importations après réorganisation:")
    all_passed = True
    
    for module_path in modules_to_test:
        if not os.path.exists(module_path):
            print(f"{module_path} : ✗ (Fichier non trouvé)")
            all_passed = False
            continue
            
        # Utiliser la fonction importée, qui attend un objet Path
        success, message = test_module_import_by_path(Path(module_path))
        # L'utilitaire formate déjà bien le message, mais on peut garder le préfixe du chemin pour ce script.
        print(f"{module_path} : {message}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\nTous les modules peuvent être importés correctement!")
    else:
        print("\nCertains modules présentent des problèmes d'importation.")
        print("Note: Ces problèmes peuvent être liés à des dépendances manquantes et non à la réorganisation des fichiers.")

if __name__ == "__main__":
    run_tests()
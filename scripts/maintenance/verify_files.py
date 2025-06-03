import os
import sys

def verify_files():
    """Vérifie l'existence des fichiers réorganisés."""
    files_to_check = [
        'docs/analysis/comparaison_sophismes.md',
        'docs/analysis/conclusion_test_agent_informel.md',
        'docs/documentation_sophismes.md',
        'results/analysis/rapport_analyse_sophismes.json',
        'docs/analysis/synthese_test_agent_informel.md',
        'docs/reports/rapport_workflow_collaboratif/rapport_analyse_workflow_collaboratif.md',
        'scripts/testing/simulation_agent_informel.py',
        'scripts/testing/test_agent_informel.py',
        'scripts/utils/test_imports_utils.py',
        'examples/test_data/test_sophismes_complexes.txt'
    ]
    
    print("Vérification des fichiers réorganisés:")
    all_exist = True
    
    # Utiliser la fonction centralisée
    # Convertir les chaînes en objets Path pour la fonction utilitaire
    paths_to_check_objects = [Path(fp) for fp in files_to_check]
    existing_files, missing_files = check_files_existence(paths_to_check_objects)
    
    for p in paths_to_check_objects: # Itérer sur la liste originale pour garder l'ordre et le formatage
        if p in existing_files:
            print(f"{str(p)} : ✓")
        else:
            print(f"{str(p)} : ✗ (Non trouvé ou n'est pas un fichier)")
            
    if not missing_files:
        print("\nTous les fichiers ont été correctement réorganisés et existent!")
    else:
        print(f"\n{len(missing_files)} fichier(s) n'ont pas été trouvé(s) ou ne sont pas des fichiers aux emplacements attendus.")

if __name__ == "__main__":
    verify_files()
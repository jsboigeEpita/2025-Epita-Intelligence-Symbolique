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
    
    for file_path in files_to_check:
        exists = os.path.exists(file_path)
        print(f"{file_path} : {'✓' if exists else '✗'}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\nTous les fichiers ont été correctement réorganisés!")
    else:
        print("\nCertains fichiers n'ont pas été trouvés aux emplacements attendus.")

if __name__ == "__main__":
    verify_files()
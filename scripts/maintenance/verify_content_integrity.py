import os
import json
import sys

def check_markdown_file(file_path):
    """Vérifie qu'un fichier Markdown est lisible et contient du contenu."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not content.strip():
            return False, "Le fichier est vide"
            
        # Vérification basique de la structure Markdown (présence de titres)
        if not any(line.startswith('#') for line in content.split('\n')):
            return False, "Aucun titre Markdown détecté"
            
        return True, f"Fichier Markdown valide ({len(content)} caractères)"
    except Exception as e:
        return False, f"Erreur lors de la lecture: {str(e)}"

def check_json_file(file_path):
    """Vérifie qu'un fichier JSON est valide et peut être parsé."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return True, f"JSON valide ({len(str(data))} caractères)"
    except json.JSONDecodeError as e:
        return False, f"JSON invalide: {str(e)}"
    except Exception as e:
        return False, f"Erreur lors de la lecture: {str(e)}"

def check_text_file(file_path):
    """Vérifie qu'un fichier texte est lisible."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not content.strip():
            return False, "Le fichier est vide"
            
        return True, f"Fichier texte valide ({len(content)} caractères)"
    except Exception as e:
        return False, f"Erreur lors de la lecture: {str(e)}"

def verify_content():
    """Vérifie l'intégrité du contenu des fichiers réorganisés."""
    files_to_check = [
        ('docs/analysis/comparaison_sophismes.md', check_markdown_file),
        ('docs/analysis/conclusion_test_agent_informel.md', check_markdown_file),
        ('docs/documentation_sophismes.md', check_markdown_file),
        ('results/analysis/rapport_analyse_sophismes.json', check_json_file),
        ('docs/analysis/synthese_test_agent_informel.md', check_markdown_file),
        ('docs/reports/rapport_workflow_collaboratif/rapport_analyse_workflow_collaboratif.md', check_markdown_file),
        ('examples/test_data/test_sophismes_complexes.txt', check_text_file)
    ]
    
    print("Vérification de l'intégrité du contenu des fichiers:")
    all_valid = True
    
    for file_path, check_func in files_to_check:
        # La vérification d'existence est maintenant dans les fonctions utilitaires
        # if not os.path.exists(file_path):
        #     print(f"{file_path} : ✗ (Fichier non trouvé)")
        #     all_valid = False
        #     continue
            
        success, message = check_func(Path(file_path)) # Passer un objet Path
        # Le message de l'utilitaire inclut déjà le chemin du fichier.
        print(f"{'✓' if success else '✗'} - {message}")
        if not success:
            all_valid = False
    
    if all_valid:
        print("\nTous les fichiers ont un contenu valide et lisible!")
    else:
        print("\nCertains fichiers présentent des problèmes de contenu.")

if __name__ == "__main__":
    verify_content()
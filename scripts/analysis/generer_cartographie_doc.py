import json
from datetime import datetime
import os

# Définition des chemins des fichiers
# Supposons que le script est à la racine du projet.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_JSON_PATH = os.path.join(BASE_DIR, "docs", "audit", "extracted_summaries_consolidated_20250604_153239.json")
OUTPUT_MD_PATH = os.path.join(BASE_DIR, "docs", "audit", "cartographie_documentation_2025-06-03.md")

def generer_cartographie():
    """
    Génère un fichier Markdown de cartographie de la documentation
    à partir d'un fichier JSON de résumés.
    """
    try:
        # Lire le fichier JSON d'entrée
        with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f_in:
            donnees_json = json.load(f_in)

        # Obtenir la date actuelle
        date_generation = datetime.now().strftime("%Y-%m-%d")

        # Construire la chaîne Markdown
        markdown_output_lines = []
        markdown_output_lines.append("# Cartographie de la Documentation du Projet")
        markdown_output_lines.append(f"Date de génération: {date_generation}")
        markdown_output_lines.append("\n## Fichiers et Résumés")

        # Vérifier si donnees_json est bien une liste
        if not isinstance(donnees_json, list):
            # Gérer le cas où le JSON est un dictionnaire contenant la liste
            if isinstance(donnees_json, dict) and len(donnees_json) == 1:
                potential_list_key = list(donnees_json.keys())[0]
                if isinstance(donnees_json[potential_list_key], list):
                    donnees_json = donnees_json[potential_list_key]
                else:
                    print(f"Erreur: Le contenu JSON sous la clé '{potential_list_key}' n'est pas une liste.")
                    markdown_output_lines.append(f"\nErreur: Le format JSON sous la clé '{potential_list_key}' n'est pas une liste d'objets attendue.")
                    donnees_json = [] 
            else:
                print("Erreur: Le contenu JSON n'est pas une liste comme attendu.")
                markdown_output_lines.append("\nErreur: Le format JSON n'est pas une liste d'objets attendue.")
                donnees_json = [] 


        for item in donnees_json:
            markdown_output_lines.append("\n---")
            
            file_path = item.get("path", "Chemin non disponible")
            summary = item.get("summary", "Résumé non disponible")

            markdown_output_lines.append(f"**Fichier:** `{file_path}`")
            markdown_output_lines.append("**Résumé:**")
            markdown_output_lines.append(summary)

        markdown_output_lines.append("\n---") # Séparateur final

        # Écrire la chaîne Markdown dans le fichier de sortie
        final_markdown_string = "\n".join(markdown_output_lines)
        with open(OUTPUT_MD_PATH, 'w', encoding='utf-8') as f_out:
            f_out.write(final_markdown_string)

        print(f"Cartographie générée avec succès dans {OUTPUT_MD_PATH}")

    except FileNotFoundError:
        print(f"Erreur : Le fichier d'entrée '{INPUT_JSON_PATH}' n'a pas été trouvé.")
    except json.JSONDecodeError:
        print(f"Erreur : Impossible de décoder le fichier JSON '{INPUT_JSON_PATH}'. Vérifiez son format.")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    generer_cartographie()
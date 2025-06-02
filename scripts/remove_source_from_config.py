import json
from pathlib import Path

# Définir les chemins des fichiers
input_config_path = Path("_temp/config_fr_corrected.json")
output_config_path = Path("_temp/config_lemonde_deleted.json")
source_name_to_remove = "article_lemonde_elections_europeennes_2024"

# S'assurer que le répertoire de sortie existe
output_config_path.parent.mkdir(parents=True, exist_ok=True)

# Charger les données depuis le fichier d'entrée
try:
    with open(input_config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Erreur : Le fichier d'entrée '{input_config_path}' n'a pas été trouvé.")
    exit(1)
except json.JSONDecodeError:
    print(f"Erreur : Impossible de décoder le JSON du fichier '{input_config_path}'.")
    exit(1)

# S'assurer que les données sont une liste (ou une structure contenant une liste de sources)
# Ceci est une hypothèse basée sur la tâche. Si la structure est différente,
# la logique de filtrage devra être adaptée.
# Pour cet exemple, nous supposons que le fichier JSON racine est une liste de sources.
if isinstance(data, list):
    # Filtrer la liste des sources
    filtered_sources = [
        source for source in data
        if not (isinstance(source, dict) and source.get("source_name") == source_name_to_remove)
    ]
elif isinstance(data, dict) and "sources" in data and isinstance(data["sources"], list):
    # Cas où les sources sont sous une clé "sources"
    filtered_sources_list = [
        source for source in data["sources"]
        if not (isinstance(source, dict) and source.get("source_name") == source_name_to_remove)
    ]
    data["sources"] = filtered_sources_list
    filtered_sources = data # Conserver la structure d'origine si c'est un dictionnaire
else:
    print(f"Erreur : La structure des données dans '{input_config_path}' n'est pas une liste de sources attendue ou un dictionnaire avec une clé 'sources'.")
    # Si le fichier ne contient pas la source à supprimer, on peut soit sortir,
    # soit écrire le contenu original dans le fichier de sortie.
    # Pour cette tâche, nous allons écrire le contenu original.
    filtered_sources = data


# Sauvegarder la liste filtrée dans le fichier de sortie
try:
    with open(output_config_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_sources, f, indent=2, ensure_ascii=False)
    print(f"La source '{source_name_to_remove}' a été supprimée (si elle existait).")
    print(f"La configuration mise à jour a été sauvegardée dans : '{output_config_path}'")
except IOError:
    print(f"Erreur : Impossible d'écrire dans le fichier de sortie '{output_config_path}'.")
    exit(1)
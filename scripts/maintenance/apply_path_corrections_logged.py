import json
from pathlib import Path

# Définition des chemins des fichiers d'entrée et de sortie
input_config_path = Path("_temp/config_lemonde_deleted.json")
output_config_path = Path("_temp/config_paths_corrected_v3.json")

# S'assurer que le répertoire de sortie existe
output_config_path.parent.mkdir(parents=True, exist_ok=True)

print(f"INFO: Lecture du fichier de configuration : {input_config_path}")

# Charger les données depuis le fichier d'entrée
try:
    with open(input_config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"ERREUR: Le fichier d'entrée {input_config_path} n'a pas été trouvé.")
    data = []
except json.JSONDecodeError:
    print(f"ERREUR: Erreur de décodage JSON dans le fichier {input_config_path}.")
    data = []

modified_data = []

for source in data:
    source_id = source.get("id", "ID inconnu")
    source_name = source.get("source_name", "Nom inconnu")
    print(f"INFO: Traitement de la source - ID: {source_id}, Nom: {source_name}")

    path_modifie = False
    ancien_path = source.get("path")

    if source_id == "assemblee_nationale_2024_pg_attal":
        source["path"] = "discours_attal_20240130.txt"
        path_modifie = True
    elif source_id == "rapport_ia_commission_2024":
        source["path"] = "rapport_ia_2024.txt"
        path_modifie = True
    elif source_id == "Source_Ibsen_Vildanden":
        source["path"] = "https://www.gutenberg.org/files/1657/1657-0.txt"
        path_modifie = True

    if path_modifie:
        print(f"INFO: -> Chemin modifié. Ancien: {ancien_path}, Nouveau: {source['path']}")
    else:
        print(f"INFO: -> Aucun chemin modifié pour cette source.")
    
    modified_data.append(source)

# Sauvegarder les données modifiées dans le fichier de sortie
try:
    with open(output_config_path, 'w', encoding='utf-8') as f:
        json.dump(modified_data, f, indent=2, ensure_ascii=False)
    print(f"INFO: Configuration mise à jour sauvegardée dans : {output_config_path}")
except IOError:
    print(f"ERREUR: Impossible d'écrire dans le fichier de sortie {output_config_path}.")
import argumentation_analysis.core.environment
import json

input_file_path = "_temp/decrypted_sources_with_vildanden.json"
output_file_path = "_temp/config_fr_corrected.json"

try:
    with open(input_file_path, 'r', encoding='utf-8') as f:
        sources_data = json.load(f)
except FileNotFoundError:
    print(f"Erreur : Le fichier d'entrée '{input_file_path}' n'a pas été trouvé.")
    exit()
except json.JSONDecodeError:
    print(f"Erreur : Impossible de décoder le JSON du fichier d'entrée '{input_file_path}'.")
    exit()

for source in sources_data:
    if source.get("id") == "assemblee_nationale_2024_pg_attal":
        source["fetch_method"] = "file"
        source["path"] = "discours_attal_20240130.txt"
    elif source.get("id") == "rapport_ia_commission_2024":
        source["fetch_method"] = "file"
        source["path"] = "rapport_ia_2024.txt"

try:
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(sources_data, f, indent=2, ensure_ascii=False)
    print(f"L'opération est terminée. Le fichier de sortie est : {output_file_path}")
except IOError:
    print(f"Erreur : Impossible d'écrire dans le fichier de sortie '{output_file_path}'.")
    exit()
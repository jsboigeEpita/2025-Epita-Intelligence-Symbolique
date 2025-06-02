import json

input_config_path = "_temp/config_paths_corrected_v3.json"
ids_to_inspect = ["assemblee_nationale_2024_pg_attal", "rapport_ia_commission_2024", "Source_Ibsen_Vildanden"]

found_ids = set()

try:
    with open(input_config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Erreur: Le fichier {input_config_path} n'a pas été trouvé.")
    exit()
except json.JSONDecodeError:
    print(f"Erreur: Impossible de décoder le JSON du fichier {input_config_path}.")
    exit()

print(f"Inspection du fichier : {input_config_path}")
print("=" * 30)

if isinstance(data, list): # Cas où le JSON est une liste d'objets sources
    for source in data:
        source_id = source.get("id")
        if source_id in ids_to_inspect:
            print(f"--- Entrée pour Source ID: {source_id} ---")
            print(json.dumps(source, indent=2, ensure_ascii=False))
            print("--------------------------------------------------")
            found_ids.add(source_id)
elif isinstance(data, dict): # Cas où le JSON est un dictionnaire avec une clé principale (ex: "sources")
    # Tentative de trouver une clé commune pour la liste des sources
    possible_keys = ["sources", "items", "data", "records"] # Ajoutez d'autres clés possibles si nécessaire
    sources_list = None
    for key in possible_keys:
        if key in data and isinstance(data[key], list):
            sources_list = data[key]
            break
    
    if sources_list:
        for source in sources_list:
            source_id = source.get("id")
            if source_id in ids_to_inspect:
                print(f"--- Entrée pour Source ID: {source_id} ---")
                print(json.dumps(source, indent=2, ensure_ascii=False))
                print("--------------------------------------------------")
                found_ids.add(source_id)
    else: # Si la structure est un dictionnaire mais pas une liste de sources directement
        source_id = data.get("id")
        if source_id in ids_to_inspect :
            print(f"--- Entrée pour Source ID: {source_id} ---")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("--------------------------------------------------")
            found_ids.add(source_id)
        # Si l'ID est une clé du dictionnaire principal
        elif any(key_id in data for key_id in ids_to_inspect):
             for key_id_to_check in ids_to_inspect:
                if key_id_to_check in data:
                    source_data = data[key_id_to_check]
                    print(f"--- Entrée pour Source ID: {key_id_to_check} ---")
                    print(json.dumps(source_data, indent=2, ensure_ascii=False))
                    print("--------------------------------------------------")
                    found_ids.add(key_id_to_check)
        else:
            print(f"La structure du JSON ({type(data)}) n'est pas une liste de sources ou un dictionnaire avec une clé de sources connue, et l'ID n'est pas directement accessible.")

else:
    print(f"Le contenu du fichier JSON n'est ni une liste, ni un dictionnaire attendu. Type trouvé: {type(data)}")


print("=" * 30)
for an_id in ids_to_inspect:
    if an_id not in found_ids:
        print(f"L'ID source '{an_id}' n'a pas été trouvé dans le fichier.")
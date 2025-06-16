import project_core.core_from_scripts.auto_env
import json

input_config_path = "_temp/config_paths_corrected_v3.json"
ids_to_inspect = ["assemblee_nationale_2024_pg_attal", "rapport_ia_commission_2024", "Source_Ibsen_Vildanden"]

found_ids = set()

try:
    config_file = Path(input_config_path)
    if not config_file.exists():
        print(f"Erreur: Le fichier {input_config_path} n'a pas été trouvé.")
        exit()
    with open(config_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
except json.JSONDecodeError:
    print(f"Erreur: Impossible de décoder le JSON du fichier {input_config_path}.")
    exit()
except Exception as e:
    print(f"Erreur inattendue lors de la lecture du fichier {input_config_path}: {e}")
    exit()

print(f"Inspection du fichier : {input_config_path}")
print("=" * 30)

# Utiliser la fonction centralisée
found_sources, found_ids_from_util = find_sources_in_config_by_ids(data, ids_to_inspect)

if found_sources:
    for source_config in found_sources:
        source_id_display = source_config.get("id", "ID Manquant")
        print(f"--- Entrée pour Source ID: {source_id_display} ---")
        print(json.dumps(source_config, indent=2, ensure_ascii=False))
        print("--------------------------------------------------")
        # found_ids est déjà mis à jour par find_sources_in_config_by_ids,
        # mais on le met à jour ici pour la vérification finale.
        if source_id_display != "ID Manquant":
            found_ids.add(source_id_display)
else:
    print("Aucune source correspondante trouvée par la fonction utilitaire.")


print("=" * 30)
for an_id in ids_to_inspect:
    if an_id not in found_ids:
        print(f"L'ID source '{an_id}' n'a pas été trouvé dans le fichier.")
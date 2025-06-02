import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Définir le chemin du fichier d'entrée
input_config_path = Path("_temp/config_lemonde_deleted.json")
# Définir le chemin du fichier de sortie
output_config_path = Path("_temp/config_paths_corrected_v2.json")

logging.info(f"Lecture du fichier d'entrée : {input_config_path}")
# Charger les données depuis input_config_path
try:
    with open(input_config_path, 'r', encoding='utf-8') as f:
        sources_data = json.load(f)
except FileNotFoundError:
    logging.error(f"Le fichier d'entrée {input_config_path} n'a pas été trouvé.")
    exit()
except json.JSONDecodeError:
    logging.error(f"Le fichier d'entrée {input_config_path} n'est pas un JSON valide.")
    exit()

# Itérer sur chaque source dans les données chargées
for source in sources_data:
    source_name = source.get("source_name")
    source_id = source.get("source_id")
    logging.info(f"Traitement de la source ID: {source_id}, Nom: {source_name}")

    modified = False
    old_path = source.get("path", "N/A")

    if source_name == "assemblee_nationale_2024_pg_attal":
        new_path = "discours_attal_20240130.txt"
        if source.get("path") != new_path:
            logging.info(f"Modification de la source ID: {source_id}, Nom: {source_name}")
            logging.info(f"  Ancien chemin: {old_path}")
            logging.info(f"  Nouveau chemin: {new_path}")
            source["path"] = new_path
            modified = True
    elif source_name == "rapport_ia_commission_2024":
        new_path = "rapport_ia_2024.txt"
        if source.get("path") != new_path:
            logging.info(f"Modification de la source ID: {source_id}, Nom: {source_name}")
            logging.info(f"  Ancien chemin: {old_path}")
            logging.info(f"  Nouveau chemin: {new_path}")
            source["path"] = new_path
            modified = True
    elif source_id == "Source_Ibsen_Vildanden":
        new_path = "https://www.gutenberg.org/files/1657/1657-0.txt"
        if source.get("path") != new_path:
            logging.info(f"Modification de la source ID: {source_id}, Nom: {source_name}")
            logging.info(f"  Ancien chemin: {old_path}")
            logging.info(f"  Nouveau chemin: {new_path}")
            source["path"] = new_path
            modified = True
    
    if not modified:
        logging.info(f"Aucune modification pour la source ID: {source_id}, Nom: {source_name}")

# Sauvegarder la liste mise à jour des sources dans output_config_path
try:
    with open(output_config_path, 'w', encoding='utf-8') as f:
        json.dump(sources_data, f, indent=2, ensure_ascii=False)
    logging.info(f"Modifications sauvegardées avec succès dans {output_config_path}")
except IOError:
    logging.error(f"Impossible d'écrire dans le fichier de sortie {output_config_path}.")
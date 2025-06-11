import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define file paths
INPUT_CONFIG_PATH = os.path.join('_temp', 'config_with_full_texts.json')
OUTPUT_CONFIG_PATH = os.path.join('_temp', 'config_with_segments.json')
LOG_FILE_PATH = os.path.join('_temp', 'populate_extract_segments.log')

# Setup file handler for logging
file_handler = logging.FileHandler(LOG_FILE_PATH, mode='w')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

def populate_segments():
    """
    Loads configuration with full texts, extracts segments based on markers,
    and saves the updated configuration.
    """
    logging.info(f"Début du script populate_extract_segments.py")
    logging.info(f"Chargement de la configuration depuis {INPUT_CONFIG_PATH}")

    if not os.path.exists(INPUT_CONFIG_PATH):
        logging.error(f"Le fichier d'entrée {INPUT_CONFIG_PATH} n'a pas été trouvé. Assurez-vous que le script populate_full_texts.py a été exécuté.")
        return

    try:
        with open(INPUT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            sources_config = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Erreur lors du décodage du JSON depuis {INPUT_CONFIG_PATH}: {e}")
        return
    except Exception as e:
        logging.error(f"Une erreur inattendue est survenue lors de la lecture de {INPUT_CONFIG_PATH}: {e}")
        return

    logging.info(f"{len(sources_config)} sources chargées.")

    for source_obj in sources_config:
        source_id = source_obj.get('id', 'ID_INCONNU')
        logging.info(f"Traitement de la source: {source_id}")

        source_full_text = source_obj.get('full_text')

        if not source_full_text:
            logging.warning(f"Full_text vide ou non disponible pour la source {source_id}. Passage aux extraits de la source suivante.")
            # Initialiser full_text_segment à None ou vide pour tous les extraits de cette source
            for extract_obj in source_obj.get('extracts', []):
                 extract_obj['full_text_segment'] = None # ou "" selon la préférence
            continue

        extracts = source_obj.get('extracts', [])
        logging.info(f"Traitement de {len(extracts)} extraits pour la source {source_id}")

        for extract_obj in extracts:
            extract_name = extract_obj.get('id', 'NOM_EXTRAIT_INCONNU') # ou 'name' si c'est le champ utilisé
            start_marker = extract_obj.get('start_marker')
            end_marker = extract_obj.get('end_marker')

            extract_obj['full_text_segment'] = None # Initialiser par défaut

            if not start_marker or not end_marker:
                logging.warning(f"Marqueurs de début ou de fin manquants pour l'extrait {extract_name} de la source {source_id}. Segment non peuplé.")
                continue

            try:
                start_index = source_full_text.find(start_marker)
                if start_index != -1:
                    # Chercher end_marker après le start_marker
                    # Ajouter len(start_marker) pour commencer la recherche après le marqueur de début complet
                    search_start_for_end_marker = start_index + len(start_marker)
                    end_index_relative = source_full_text[search_start_for_end_marker:].find(end_marker)

                    if end_index_relative != -1:
                        # end_index est relatif à la sous-chaîne, il faut le ramener à l'index absolu
                        end_index_absolute = search_start_for_end_marker + end_index_relative
                        
                        # Le segment inclut le start_marker et le end_marker
                        segment = source_full_text[start_index : end_index_absolute + len(end_marker)]
                        extract_obj['full_text_segment'] = segment
                        logging.info(f"Segment pour l'extrait '{extract_name}' de la source '{source_id}' peuplé (longueur: {len(segment)}).")
                    else:
                        logging.error(f"Marqueur de fin '{end_marker}' pour l'extrait '{extract_name}' non trouvé après le début dans la source '{source_id}'.")
                else:
                    logging.error(f"Marqueur de début '{start_marker}' pour l'extrait '{extract_name}' non trouvé dans la source '{source_id}'.")
            except Exception as e:
                logging.error(f"Erreur inattendue lors du traitement de l'extrait '{extract_name}' de la source '{source_id}': {e}")


    logging.info(f"Sauvegarde de la configuration mise à jour dans {OUTPUT_CONFIG_PATH}")
    try:
        # S'assurer que le répertoire _temp existe
        os.makedirs(os.path.dirname(OUTPUT_CONFIG_PATH), exist_ok=True)
        with open(OUTPUT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(sources_config, f, ensure_ascii=False, indent=2)
        logging.info("Configuration sauvegardée avec succès.")
    except Exception as e: # Ajout de la clause except
        logging.error(f"Erreur lors de la sauvegarde de la configuration dans {OUTPUT_CONFIG_PATH}: {e}")

    logging.info("Fin du script populate_extract_segments.py")

if __name__ == '__main__':
    populate_segments()
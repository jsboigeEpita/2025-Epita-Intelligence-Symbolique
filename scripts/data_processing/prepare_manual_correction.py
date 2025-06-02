import json
import pathlib
import argparse

def prepare_manual_correction(config_file_path_str, target_source_id, target_extract_name, output_debug_file_str):
    config_file_path = pathlib.Path(config_file_path_str)
    output_debug_file = pathlib.Path(output_debug_file_str)

    print(f"INFO: Chargement de la configuration depuis : {config_file_path}")
    if not config_file_path.exists():
        print(f"ERREUR: Le fichier de configuration '{config_file_path}' n'existe pas.")
        return

    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            sources_data = json.load(f)
    except Exception as e:
        print(f"ERREUR: Impossible de charger ou parser le fichier JSON '{config_file_path}': {e}")
        return

    if not isinstance(sources_data, list):
        print(f"ERREUR: La structure racine du JSON dans '{config_file_path}' n'est pas une liste.")
        return

    found_source = None
    for source in sources_data:
        if isinstance(source, dict) and source.get("id") == target_source_id:
            found_source = source
            break
    
    if not found_source:
        print(f"ERREUR: Source ID '{target_source_id}' non trouvée.")
        available_ids = [s.get('id') for s in sources_data if isinstance(s, dict)]
        print(f"INFO: IDs de source disponibles: {available_ids}")
        return

    found_extract = None
    extracts_list = found_source.get("extracts", [])
    if not isinstance(extracts_list, list):
        print(f"ERREUR: Le champ 'extracts' pour la source ID '{target_source_id}' n'est pas une liste.")
        return

    for extract in extracts_list:
        if isinstance(extract, dict) and extract.get("extract_name") == target_extract_name:
            found_extract = extract
            break

    if not found_extract:
        print(f"ERREUR: Extrait nom '{target_extract_name}' non trouvé dans la source ID '{target_source_id}'.")
        available_extract_names = [e.get('extract_name') for e in extracts_list if isinstance(e, dict)]
        print(f"INFO: Noms d'extraits disponibles pour la source '{target_source_id}': {available_extract_names}")
        return

    source_name = found_source.get("source_name", "Nom de source inconnu")
    current_start_marker = found_extract.get("start_marker", "N/A")
    current_end_marker = found_extract.get("end_marker", "N/A")
    source_full_text = found_source.get("full_text")

    debug_info = []
    debug_info.append(f"--- Informations pour Correction Manuelle ---")
    debug_info.append(f"Source ID         : {target_source_id}")
    debug_info.append(f"Nom de la Source  : {source_name}")
    debug_info.append(f"Nom de l'Extrait  : {target_extract_name}")
    debug_info.append(f"Marqueur Début Actuel : {repr(current_start_marker)}")
    debug_info.append(f"Marqueur Fin Actuel   : {repr(current_end_marker)}")
    
    if source_full_text:
        debug_info.append(f"Full_text de la source (longueur: {len(source_full_text)} caractères) :\n--- DEBUT FULL TEXT ---")
        debug_info.append(source_full_text)
        debug_info.append("--- FIN FULL TEXT ---")
    else:
        debug_info.append("ATTENTION: Full_text de la source est ABSENT ou VIDE.")

    try:
        with open(output_debug_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(debug_info))
        print(f"INFO: Les informations de débogage ont été écrites dans : {output_debug_file}")
        print(f"INFO: Marqueur Début Actuel : {repr(current_start_marker)}")
        print(f"INFO: Marqueur Fin Actuel   : {repr(current_end_marker)}")
        if not source_full_text:
             print(f"ATTENTION: Le full_text pour la source {target_source_id} est manquant. La correction manuelle des marqueurs sera difficile.")
    except Exception as e:
        print(f"ERREUR: Impossible d'écrire le fichier de débogage '{output_debug_file}': {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prépare les informations pour la correction manuelle d'un extrait.")
    parser.add_argument("config_file", help="Chemin vers le fichier de configuration JSON des sources.")
    parser.add_argument("source_id", help="ID de la source à traiter.")
    parser.add_argument("extract_name", help="Nom de l'extrait à traiter.")
    parser.add_argument("output_file", help="Chemin vers le fichier de sortie pour les informations de débogage.")
    
    args = parser.parse_args()
    
    prepare_manual_correction(args.config_file, args.source_id, args.extract_name, args.output_file)
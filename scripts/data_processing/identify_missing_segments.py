import argumentation_analysis.core.environment
import json
import pathlib

def identify_missing_segments(config_file_path_str):
    config_file_path = pathlib.Path(config_file_path_str)
    print(f"INFO: Analyse du fichier de configuration : {config_file_path}")

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

    missing_segments_count = 0
    total_extracts_count = 0

    print("\n--- Rapport des Segments d'Extraits Manquants ou Vides ---")
    for i, source in enumerate(sources_data):
        source_id = source.get("id", f"Source Inconnue #{i+1}")
        source_name = source.get("source_name", "Nom de source inconnu")
        extracts = source.get("extracts", [])

        if not isinstance(extracts, list):
            print(f"ATTENTION: La source '{source_name}' (ID: {source_id}) a un champ 'extracts' qui n'est pas une liste.")
            continue

        for j, extract in enumerate(extracts):
            total_extracts_count += 1
            extract_name = extract.get("extract_name", f"Extrait Inconnu #{j+1}")
            segment = extract.get("full_text_segment")
            
            # Vérifier si le segment est manquant (None) ou vide (chaîne vide)
            if segment is None or segment == "":
                missing_segments_count += 1
                print(f"  - Source: '{source_name}' (ID: {source_id})")
                print(f"    Extrait: '{extract_name}' - SEGMENT MANQUANT/VIDE")
                # Afficher les marqueurs pour aider au diagnostic
                start_marker = extract.get("start_marker", "N/A")
                end_marker = extract.get("end_marker", "N/A")
                print(f"      Marqueur Début: {repr(start_marker)}")
                print(f"      Marqueur Fin: {repr(end_marker)}")
                # Indiquer si le full_text de la source est présent
                has_full_text = "PRÉSENT" if source.get("full_text") else "ABSENT"
                print(f"      Full_text de la source: {has_full_text}")


    print("\n--- Résumé ---")
    if missing_segments_count == 0:
        print("Tous les extraits ont un segment 'full_text_segment' renseigné.")
    else:
        print(f"Nombre total d'extraits avec segment manquant ou vide : {missing_segments_count}")
        print(f"Nombre total d'extraits analysés : {total_extracts_count}")
        # La fonction est maintenant importée et retourne les valeurs.
        # Le script appelant peut choisir de les utiliser ou non.
    
    if __name__ == "__main__":
        # ASSUREZ-VOUS QUE CE CHEMIN EST CORRECT
        config_file_to_analyze_str = "_temp/config_final_pre_encryption.json"
        config_file_path_obj = pathlib.Path(config_file_to_analyze_str)
        
        # Appeler la fonction importée
        # La fonction logge déjà les détails, donc ici on peut juste afficher un résumé si besoin.
        missing_count, total_count, _ = identify_missing_full_text_segments(config_file_path_obj)
        
        print(f"\n--- Résultat final de l'appel à la fonction utilitaire ---")
        if missing_count == 0 and total_count > 0:
            print(f"Analyse terminée. Tous les {total_count} extraits ont un segment 'full_text_segment' renseigné.")
        elif total_count == 0:
            print("Analyse terminée. Aucun extrait n'a été trouvé ou analysé.")
        else:
            print(f"Analyse terminée. {missing_count} extraits sur {total_count} ont un segment manquant ou vide.")
import json
import pathlib
import copy

# Définition des chemins des fichiers d'entrée et de sortie
input_config_path = "_temp/config_paths_corrected_v3.json"
output_config_path = "_temp/config_segments_populated.json"

print(f"INFO: Lecture du fichier de configuration : {input_config_path}")

try:
    with open(input_config_path, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
except FileNotFoundError:
    print(f"ERREUR: Fichier de configuration d'entrée {input_config_path} non trouvé.")
    exit()
except json.JSONDecodeError as e:
    print(f"ERREUR: Décodage JSON du fichier {input_config_path} échoué: {e}")
    exit()
except Exception as e:
    print(f"ERREUR: Lecture du fichier {input_config_path} échouée: {e}")
    exit()

# Création d'une copie profonde pour travailler dessus
new_data = copy.deepcopy(loaded_data)

for source in new_data:
    source_id = source.get("id", "ID inconnu")
    source_name = source.get("source_name", "Nom inconnu")
    print(f"INFO: Traitement de la source - ID: {source_id}, Nom: {source_name}")

    source_full_text = source.get("full_text", "")

    if source.get("fetch_method") == "file" and not source_full_text:
        file_path_str = source.get("path")
        if file_path_str:
            file_to_read = pathlib.Path(file_path_str)
            if file_to_read.exists():
                try:
                    with open(file_to_read, 'r', encoding='utf-8') as f:
                        source_full_text = f.read()
                    source["full_text"] = source_full_text  # Mettre à jour new_data
                    print(f"INFO: -> Full_text lu depuis le fichier: {file_to_read}")
                except Exception as e:
                    print(f" ERREUR: Lecture du fichier {file_to_read} pour source {source_id} échouée: {e}")
            else:
                print(f" ATTENTION: Fichier {file_to_read} pour source {source_id} non trouvé.")
        else:
            print(f" ATTENTION: Chemin de fichier non spécifié pour source {source_id} (type file).")
    elif not source_full_text and source.get("fetch_method") != "file":
        print(f" INFO: Full_text non disponible ou non récupérable localement pour source {source_id} (type: {source.get('fetch_method')}). Segments non générés.")
        continue # Passe à la source suivante

    if source_full_text:
        print(f"INFO: -> Full_text de la source disponible (longueur: {len(source_full_text)}). Tentative de génération des segments d'extraits.")
        for extract in source.get("extracts", []):
            extract_name = extract.get("extract_name", "Nom d'extrait inconnu")
            start_marker = extract.get("start_marker")
            end_marker = extract.get("end_marker")

            if start_marker and end_marker:
                try:
                    start_index = source_full_text.find(start_marker)
                    # Chercher end_marker après le début de start_marker
                    end_index = source_full_text.find(end_marker, start_index + len(start_marker))

                    if start_index != -1 and end_index != -1:
                        # S'assurer que end_index est bien après start_index
                        if end_index > start_index:
                            segment = source_full_text[start_index : end_index + len(end_marker)]
                            extract["full_text_segment"] = segment
                            print(f"INFO: ---> Segment pour extrait '{extract_name}' généré (longueur: {len(segment)}).")
                        else:
                            # Cas où end_marker est trouvé avant la fin de start_marker (ou chevauchement)
                            # Tenter de trouver end_marker APRES la fin de start_marker
                            search_after_start_marker_end = start_index + len(start_marker)
                            end_index_strict = source_full_text.find(end_marker, search_after_start_marker_end)
                            if end_index_strict != -1:
                                segment = source_full_text[start_index : end_index_strict + len(end_marker)]
                                extract["full_text_segment"] = segment
                                print(f"INFO: ---> Segment pour extrait '{extract_name}' généré (longueur: {len(segment)}) (recherche stricte).")
                            else:
                                print(f" ATTENTION: Marqueur de fin '{end_marker}' pour extrait '{extract_name}' (source {source_id}) non trouvé après le marqueur de début '{start_marker}'.")
                    else:
                        missing_markers_msg = []
                        if start_index == -1:
                            missing_markers_msg.append(f"marqueur de début '{start_marker}'")
                        if end_index == -1 : #and start_index != -1 (implicite si on arrive ici et start_index != -1)
                             missing_markers_msg.append(f"marqueur de fin '{end_marker}' après '{start_marker}'")
                        elif end_index == -1 and start_index == -1: # si les deux sont manquants, le message précédent est suffisant
                            pass


                        print(f" ATTENTION: Marqueurs pour extrait '{extract_name}' (source {source_id}) non trouvés: {', '.join(missing_markers_msg)} dans le full_text.")

                except Exception as e:
                    print(f" ERREUR: Génération du segment pour extrait '{extract_name}' (source {source_id}) échouée: {e}")
            else:
                missing_info = []
                if not start_marker:
                    missing_info.append("marqueur de début")
                if not end_marker:
                    missing_info.append("marqueur de fin")
                print(f" ATTENTION: {', '.join(missing_info).capitalize()} manquants pour extrait '{extract_name}' (source {source_id}).")
    else:
        print(f" INFO: Full_text non disponible pour source {source_id}. Segments non générés.")

try:
    with open(output_config_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print(f"INFO: Configuration avec segments potentiellement peuplés sauvegardée dans : {output_config_path}")
except Exception as e:
    print(f"ERREUR: Sauvegarde du fichier {output_config_path} échouée: {e}")
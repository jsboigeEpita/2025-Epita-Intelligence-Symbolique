import json
import pathlib
import copy
import re

def get_significant_substrings(marker_text, length=30):
    """
    Extrait des sous-chaînes significatives (préfixe et suffixe) d'un marqueur.
    Retire les espaces de début/fin, puis prend les `length` premiers et derniers caractères.
    """
    if not marker_text or not isinstance(marker_text, str):
        return None, None
    
    cleaned_marker = marker_text.strip()
    if not cleaned_marker:
        return None, None

    prefix = cleaned_marker[:length]
    suffix = cleaned_marker[-length:]
    return prefix, suffix

def find_segment_with_markers(full_text, start_marker, end_marker):
    """
    Tente de trouver un segment basé sur les marqueurs de début et de fin.
    Retourne (start_index, end_index_of_end_marker, segment_text) ou (None, None, None).
    """
    if not all([full_text, start_marker, end_marker]):
        return None, None, None

    try:
        start_idx = full_text.find(start_marker)
        if start_idx == -1:
            return None, None, None

        # Recherche end_marker APRES start_marker
        # end_idx est l'index de début de end_marker
        end_idx = full_text.find(end_marker, start_idx + len(start_marker))
        if end_idx == -1:
            return None, None, None
            
        # L'index de fin pour le slicing doit inclure le end_marker
        # segment_end_idx = end_idx + len(end_marker)
        
        # Assurer que le segment n'est pas vide et que les marqueurs ne se chevauchent pas mal
        if end_idx <= start_idx : # end_marker doit commencer après le début de start_marker
             return None, None, None

        # Le segment extrait inclut les marqueurs
        # Le segment est de start_idx (début de start_marker) à end_idx + len(end_marker) (fin de end_marker)
        new_segment = full_text[start_idx : end_idx + len(end_marker)]
        return start_idx, end_idx + len(end_marker), new_segment
    except Exception as e:
        print(f"DEBUG: Erreur dans find_segment_with_markers: {e} avec start='{start_marker}', end='{end_marker}'")
        return None, None, None

def main():
    input_config_path = pathlib.Path("_temp/config_segments_populated.json")
    output_config_path = pathlib.Path("_temp/config_markers_autocorrected.json")
    output_config_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"INFO: Lecture du fichier de configuration : {input_config_path}")
    try:
        with open(input_config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERREUR: Fichier d'entrée non trouvé: {input_config_path}")
        return
    except json.JSONDecodeError:
        print(f"ERREUR: Impossible de décoder le JSON depuis: {input_config_path}")
        return

    corrected_data = copy.deepcopy(data)
    corrected_extracts_count = 0

    # corrected_data est une liste de sources, donc on itère directement dessus.
    for source in corrected_data:
        source_id = source.get("source_id")
        source_name = source.get("source_name")
        source_full_text = source.get("full_text")

        if source.get("fetch_method") == "file" and not source_full_text:
            file_path_str = source.get("file_path")
            if file_path_str:
                file_path = pathlib.Path(file_path_str)
                if file_path.exists():
                    try:
                        source_full_text = file_path.read_text(encoding='utf-8')
                        source["full_text"] = source_full_text # Mettre à jour pour la sauvegarde potentielle
                        print(f"INFO: Texte complet chargé depuis le fichier {file_path} pour la source {source_id}")
                    except Exception as e:
                        print(f"ERREUR: Impossible de lire le fichier source {file_path} pour {source_id}: {e}")
                        source_full_text = None
                else:
                    print(f"AVERTISSEMENT: Fichier source {file_path} non trouvé pour {source_id}.")
                    source_full_text = None
            else:
                print(f"AVERTISSEMENT: file_path manquant pour la source {source_id} avec fetch_method='file'.")
                source_full_text = None
        
        if not source_full_text:
            print(f"AVERTISSEMENT: Texte complet non disponible pour la source : {source_name} ({source_id}). Passage à la source suivante.")
            continue

        for extract in source.get("extracts", []):
            if not extract.get("full_text_segment"): # Cible les extraits sans segment
                extract_name = extract.get("extract_name", "N/A")
                print(f"\nINFO: Tentative de correction pour Extrait: {extract_name} (Source: {source_id} - {source_name})")

                current_start_marker = extract.get("start_marker")
                current_end_marker = extract.get("end_marker")
                print(f"  Marqueurs actuels: START='{current_start_marker}' END='{current_end_marker}'")

                found_new_markers = False

                # Priorité 1: Recherche exacte des marqueurs actuels
                if current_start_marker and current_end_marker:
                    _, _, segment = find_segment_with_markers(source_full_text, current_start_marker, current_end_marker)
                    if segment:
                        extract["start_marker"] = current_start_marker
                        extract["end_marker"] = current_end_marker
                        extract["full_text_segment"] = segment
                        corrected_extracts_count += 1
                        print(f"  SUCCESS (P1): Marqueurs actuels validés et segment extrait pour {extract_name}.")
                        found_new_markers = True
                    else:
                        print(f"  INFO (P1): Échec de la validation des marqueurs actuels pour {extract_name}.")

                # Priorité 2: Recherche de sous-chaînes significatives
                if not found_new_markers:
                    print(f"  INFO (P2): Tentative avec des sous-chaînes significatives pour {extract_name}.")
                    start_prefix, start_suffix = get_significant_substrings(current_start_marker)
                    end_prefix, end_suffix = get_significant_substrings(current_end_marker)
                    
                    potential_new_markers = []
                    if start_prefix:
                        if end_suffix: potential_new_markers.append((start_prefix, end_suffix, "start_prefix, end_suffix"))
                        if end_prefix: potential_new_markers.append((start_prefix, end_prefix, "start_prefix, end_prefix"))
                    if start_suffix:
                        if end_suffix: potential_new_markers.append((start_suffix, end_suffix, "start_suffix, end_suffix"))
                        if end_prefix: potential_new_markers.append((start_suffix, end_prefix, "start_suffix, end_prefix"))
                    
                    # Si les marqueurs originaux sont courts, ils pourraient être identiques à leurs préfixes/suffixes
                    # Ajouter les marqueurs originaux nettoyés s'ils sont différents des combinaisons déjà testées
                    # et si les préfixes/suffixes sont égaux aux marqueurs nettoyés eux-mêmes.
                    cleaned_start = current_start_marker.strip() if current_start_marker else None
                    cleaned_end = current_end_marker.strip() if current_end_marker else None

                    if cleaned_start and cleaned_end:
                        if cleaned_start == start_prefix and cleaned_start == start_suffix and \
                           cleaned_end == end_prefix and cleaned_end == end_suffix:
                           # Ce cas est déjà couvert par la P1 si les marqueurs originaux étaient juste nettoyés
                           pass
                        else: # Essayer avec les marqueurs nettoyés si P1 a échoué (peut-être à cause d'espaces)
                            if not any(nm[0] == cleaned_start and nm[1] == cleaned_end for nm in potential_new_markers):
                                potential_new_markers.append((cleaned_start, cleaned_end, "cleaned_original_markers"))


                    for new_start, new_end, strategy_name in potential_new_markers:
                        if not new_start or not new_end: continue
                        print(f"    Tentative (P2 - {strategy_name}): START='{new_start}' END='{new_end}'")
                        _, _, segment = find_segment_with_markers(source_full_text, new_start, new_end)
                        if segment:
                            extract["start_marker"] = new_start
                            extract["end_marker"] = new_end
                            extract["full_text_segment"] = segment
                            corrected_extracts_count += 1
                            print(f"    SUCCESS (P2 - {strategy_name}): Nouveaux marqueurs trouvés et segment extrait pour {extract_name}.")
                            found_new_markers = True
                            break 
                    if not found_new_markers:
                         print(f"    FAILURE (P2): Aucune sous-chaîne significative n'a fonctionné pour {extract_name}.")


                # Priorité 3: Recherche floue (non implémentée)
                if not found_new_markers:
                    print(f"  INFO (P3): La recherche floue n'est pas implémentée dans cette version.")
                    # Logique pour la recherche floue ici si disponible

                if not found_new_markers:
                    print(f"  FAILURE: Correction automatique ÉCHOUÉE pour {extract_name}. Aucun nouveau marqueur fonctionnel trouvé.")
                else:
                    print(f"  SUCCESS: Correction automatique RÉUSSIE pour {extract_name}.")
            else:
                # Segment déjà présent, on ne fait rien
                pass


    print(f"\nINFO: Sauvegarde de la configuration avec marqueurs potentiellement auto-corrigés dans : {output_config_path}")
    try:
        with open(output_config_path, 'w', encoding='utf-8') as f:
            json.dump(corrected_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"ERREUR: Impossible d'écrire le fichier de sortie {output_config_path}: {e}")

    print(f"\n--- Résumé de la correction ---")
    # data est une liste de sources
    total_extracts_to_check = sum(1 for src in data for ext in src.get('extracts', []) if not ext.get('full_text_segment'))
    print(f"Nombre total d'extraits pour lesquels une correction a été tentée (ceux sans full_text_segment initial): {total_extracts_to_check}")
    print(f"Nombre d'extraits corrigés avec succès : {corrected_extracts_count}")
    print(f"Fichier de sortie généré : {output_config_path.resolve()}")

if __name__ == "__main__":
    main()
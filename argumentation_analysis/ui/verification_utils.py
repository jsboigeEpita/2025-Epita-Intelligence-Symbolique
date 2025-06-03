"""
Utilitaires de vérification des définitions d'extraits pour l'interface utilisateur.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# Importation de la configuration UI et des utilitaires nécessaires
from . import config as ui_config
from .cache_utils import load_from_cache 
# get_full_text_for_source est la fonction principale à utiliser ici
from .fetch_utils import get_full_text_for_source 

verification_logger = logging.getLogger("App.UI.VerificationUtils")
if not verification_logger.handlers and not verification_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    verification_logger.addHandler(handler)
    verification_logger.setLevel(logging.INFO)

# Placeholder pour reconstruct_url en attendant la refonte de utils.py
# Cette fonction est nécessaire pour verify_extract_definitions (indirectement via get_full_text_for_source si non fourni dans source_info)
# et directement si on reconstruit l'URL pour le cache_key dans verify_extract_definitions.
# La version dans fetch_utils.py est suffisante comme placeholder commun.
# Pour éviter la duplication, on pourrait l'importer depuis fetch_utils ou un common_utils.
# Pour l'instant, on assume qu'elle est disponible via get_full_text_for_source ou que
# source_info contient déjà une 'url' complète.
# La version HEAD de verify_extract_definitions reconstruit l'URL pour le cache_key.

# La fonction reconstruct_url est maintenant importée depuis .utils
from .utils import reconstruct_url

def verify_extract_definitions(definitions_list: List[Dict[str, Any]], app_config: Optional[Dict[str, Any]] = None) -> str:
    """Vérifie la présence des marqueurs de début et de fin pour chaque extrait défini. (Version HEAD)"""
    verification_logger.info("\n🔬 Lancement de la vérification des marqueurs d'extraits...")
    results = []
    total_checks = 0
    total_errors = 0

    if not definitions_list or definitions_list == ui_config.DEFAULT_EXTRACT_SOURCES:
        return "Aucune définition valide à vérifier."

    for source_idx, source_info in enumerate(definitions_list):
        source_name = source_info.get("source_name", f"Source Inconnue #{source_idx+1}")
        verification_logger.info(f"\n--- Vérification Source: '{source_name}' ---")
        
        # Utiliser get_full_text_for_source pour obtenir le texte
        # Elle gère le cache, la reconstruction d'URL, et les différentes méthodes de fetch.
        texte_brut_source = get_full_text_for_source(source_info, app_config=app_config)
        
        # La logique de reconstruction d'URL pour le cache_key est maintenant dans get_full_text_for_source
        # et la logique de fetch aussi.

        if texte_brut_source is not None:
            verification_logger.info(f"   -> Texte complet récupéré (longueur: {len(texte_brut_source)}). Vérification des extraits...")
            extracts = source_info.get("extracts", [])
            if not extracts: verification_logger.info("      -> Aucun extrait défini.")

            for extract_idx, extract_info in enumerate(extracts):
                extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx+1}")
                start_marker = extract_info.get("start_marker")
                end_marker = extract_info.get("end_marker")

                is_target_extract = source_name == "Source_1" and extract_name == "1. DAcbat Complet (Ottawa, 1858)"

                if is_target_extract:
                    verification_logger.info(f"[LOGGING DIAGNOSTIC POUR {source_name} -> {extract_name}]")
                    verification_logger.info(f"  extract_name: {extract_name}")
                    verification_logger.info(f"  start_marker (reçu): '{start_marker}'")
                    verification_logger.info(f"  end_marker (reçu): '{end_marker}'")

                current_start_index = -1
                current_end_index = -1

                if start_marker: # texte_brut_source est déjà vérifié non None
                    actual_start_marker_log = start_marker
                    if is_target_extract:
                        verification_logger.info(f"  AVANT RECHERCHE start_marker:")
                        verification_logger.info(f"    actual_start_marker: '{actual_start_marker_log}'")
                        approx_start_pos = texte_brut_source.find(actual_start_marker_log)
                        if approx_start_pos != -1:
                            context_window = 200
                            start_slice = max(0, approx_start_pos - context_window)
                            end_slice = approx_start_pos + len(actual_start_marker_log) + context_window
                            context_text_start = texte_brut_source[start_slice:end_slice]
                            verification_logger.info(f"    contexte source_text (autour de pos {approx_start_pos}, fenetre +/-{context_window}):\n'''{context_text_start}'''")
                        else:
                            verification_logger.info(f"    start_marker non trouvé (estimation), contexte source_text (début):\n'''{texte_brut_source[:500]}'''")
                    try:
                        found_pos = texte_brut_source.index(actual_start_marker_log)
                        current_start_index = found_pos
                        if is_target_extract:
                            verification_logger.info(f"  start_index TROUVÉ: {current_start_index}")
                    except ValueError:
                        if is_target_extract:
                            verification_logger.info(f"  start_index NON TROUVÉ pour '{actual_start_marker_log}'")
                        current_start_index = -1
                
                if end_marker and current_start_index != -1:
                    actual_end_marker_log = end_marker
                    search_area_start_for_end_marker = current_start_index + len(start_marker)
                    if is_target_extract:
                        verification_logger.info(f"  AVANT RECHERCHE end_marker (recherche à partir de position {search_area_start_for_end_marker}):")
                        verification_logger.info(f"    actual_end_marker: '{actual_end_marker_log}'")
                        approx_end_pos_in_search_area = texte_brut_source[search_area_start_for_end_marker:].find(actual_end_marker_log)
                        if approx_end_pos_in_search_area != -1:
                            approx_end_pos_global = search_area_start_for_end_marker + approx_end_pos_in_search_area
                            context_window = 200
                            start_slice = max(0, approx_end_pos_global - context_window)
                            end_slice = approx_end_pos_global + len(actual_end_marker_log) + context_window
                            context_text_end = texte_brut_source[start_slice:end_slice]
                            verification_logger.info(f"    contexte source_text (autour de pos globale {approx_end_pos_global}, fenetre +/-{context_window}):\n'''{context_text_end}'''")
                        else:
                            verification_logger.info(f"    end_marker non trouvé (estimation) dans la zone, contexte source_text (zone de recherche concernée):\n'''{texte_brut_source[search_area_start_for_end_marker : search_area_start_for_end_marker + 500]}'''")
                    try:
                        found_pos_end = texte_brut_source.find(actual_end_marker_log, search_area_start_for_end_marker)
                        if found_pos_end != -1:
                            current_end_index = found_pos_end + len(actual_end_marker_log)
                            if is_target_extract:
                                verification_logger.info(f"  end_index TROUVÉ (marqueur trouvé à {found_pos_end}, fin du segment à {current_end_index})")
                        else:
                            if is_target_extract:
                                verification_logger.info(f"  end_index NON TROUVÉ pour '{actual_end_marker_log}' après start_marker.")
                            current_end_index = -1
                    except Exception as e_find_end:
                        if is_target_extract:
                            verification_logger.error(f"  Erreur inattendue recherche end_marker: {e_find_end}")
                        current_end_index = -1
                
                if is_target_extract:
                    verification_logger.info(f"  Valeurs finales pour {extract_name}: current_start_index = {current_start_index}, current_end_index = {current_end_index}")

                total_checks += 1
                marker_errors = []

                if not start_marker or not end_marker:
                    marker_errors.append("Marqueur(s) Manquant(s)")
                else:
                    # La logique de current_start_index et current_end_index remplace les simples 'in'
                    start_found = current_start_index != -1
                    end_found_after_start = current_end_index != -1 and (current_start_index + len(start_marker) <= current_end_index - len(end_marker) if start_marker and end_marker else False)


                    if not start_found: marker_errors.append("Début NON TROUVÉ")
                    # Vérifier si end_marker a été trouvé *après* start_marker.
                    # current_end_index est la position *après* le marqueur de fin.
                    # current_start_index est la position *de début* du marqueur de début.
                    # Il faut que le début du marqueur de fin soit après la fin du marqueur de début.
                    # Position de début du marqueur de fin = current_end_index - len(end_marker)
                    # Position de fin du marqueur de début = current_start_index + len(start_marker)
                    if start_found and not (end_marker and current_end_index != -1 and (current_end_index - len(end_marker)) >= (current_start_index + len(start_marker))):
                         marker_errors.append("Fin NON TROUVÉE (après début)")
                    elif not start_found and end_marker and current_end_index != -1 : # Fin trouvée mais pas début
                         marker_errors.append("Fin TROUVÉE mais Début NON TROUVÉ")


                if marker_errors:
                    verification_logger.warning(f"      -> ❌ Problème Extrait '{extract_name}': {', '.join(marker_errors)}")
                    results.append(f"<li>{source_name} -> {extract_name}: <strong style='color:red;'>{', '.join(marker_errors)}</strong></li>")
                    total_errors += 1
                else:
                    verification_logger.info(f"      -> ✅ OK: Extrait '{extract_name}'")
        else:
            num_extracts = len(source_info.get("extracts",[]))
            # source_type n'est plus directement utilisé ici pour la condition is_plaintext
            # car get_full_text_for_source gère déjà cela.
            # On vérifie juste si texte_brut_source est None.
            # La distinction Tika binaire vs plaintext est gérée dans get_full_text_for_source/fetch_with_tika
            results.append(f"<li>{source_name}: Vérification impossible (texte source non obtenu ou vide)</li>")
            total_errors += num_extracts # Compter tous les extraits comme erreur si la source n'est pas chargée
            total_checks += num_extracts


    summary = f"--- Résultat Vérification ---<br/>{total_checks} extraits vérifiés. <strong style='color: {'red' if total_errors > 0 else 'green'};'>{total_errors} erreur(s) trouvée(s).</strong>"
    if results:
        summary += "<br/>Détails :<ul>" + "".join(results) + "</ul>"
    else:
         if total_checks > 0: summary += "<br/>Tous les marqueurs semblent corrects."
         else: summary += "<br/>Aucun extrait n'a pu être vérifié."

    verification_logger.info("\n" + f"{summary.replace('<br/>', chr(10)).replace('<li>', '- ').replace('</li>', '').replace('<ul>', '').replace('</ul>', '').replace('<strong>', '').replace('</strong>', '')}")
    return summary

verification_logger.info("Utilitaires de vérification UI définis.")
"""
Utilitaires de vérification des définitions d'extraits pour l'interface utilisateur.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# Importation de la configuration UI et des utilitaires nécessaires
from . import config as ui_config
from ..services.fetch_service import FetchService
from .utils import reconstruct_url

verification_logger = logging.getLogger("App.UI.VerificationUtils")
if not verification_logger.handlers and not verification_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
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
# from .utils import reconstruct_url # Commenté pour suspicion de circularité/inutilisé


def verify_extract_definitions(
    definitions_list: List[Dict[str, Any]], fetch_service: FetchService
) -> str:
    """Vérifie la présence des marqueurs de début et de fin pour chaque extrait défini."""
    verification_logger.info(
        "\n🔬 Lancement de la vérification des marqueurs d'extraits..."
    )
    results = []
    total_checks = 0
    total_errors = 0

    if not definitions_list or definitions_list == ui_config.DEFAULT_EXTRACT_SOURCES:
        return "Aucune définition valide à vérifier."

    for source_idx, source_info in enumerate(definitions_list):
        source_name = source_info.get("source_name", f"Source Inconnue #{source_idx+1}")
        verification_logger.info(f"\n--- Vérification Source: '{source_name}' ---")

        texte_brut_source = None
        try:
            reconstructed_url = reconstruct_url(
                source_info.get("schema"),
                source_info.get("host_parts", []),
                source_info.get("path"),
            )
            if not reconstructed_url:
                raise ValueError("URL source invalide.")

            source_type = source_info.get("source_type")
            if source_type == "jina":
                texte_brut_source = fetch_service.fetch_with_jina(reconstructed_url)
            elif source_type == "direct_download":
                texte_brut_source = fetch_service.fetch_direct_text(reconstructed_url)
            elif source_type == "tika":
                texte_brut_source = fetch_service.fetch_with_tika(url=reconstructed_url)
            else:
                raise ValueError(f"Type source inconnu '{source_type}'.")
        except Exception as e:
            verification_logger.error(
                f"   -> ❌ Erreur fetch pendant la vérification pour '{source_name}': {e}"
            )

        if texte_brut_source is not None:
            verification_logger.info(
                f"   -> Texte complet récupéré (longueur: {len(texte_brut_source)}). Vérification des extraits..."
            )
            extracts = source_info.get("extracts", [])
            if not extracts:
                verification_logger.info("      -> Aucun extrait défini.")

            for extract_idx, extract_info in enumerate(extracts):
                extract_name = extract_info.get(
                    "extract_name", f"Extrait #{extract_idx+1}"
                )
                start_marker = extract_info.get("start_marker")
                end_marker = extract_info.get("end_marker")

                current_start_index = -1
                current_end_index = -1

                if start_marker:  # texte_brut_source est déjà vérifié non None
                    actual_start_marker_log = start_marker
                    try:
                        found_pos = texte_brut_source.index(actual_start_marker_log)
                        current_start_index = found_pos
                    except ValueError:
                        current_start_index = -1

                if end_marker and current_start_index != -1:
                    actual_end_marker_log = end_marker
                    search_area_start_for_end_marker = current_start_index + len(
                        start_marker
                    )
                    try:
                        found_pos_end = texte_brut_source.find(
                            actual_end_marker_log, search_area_start_for_end_marker
                        )
                        if found_pos_end != -1:
                            current_end_index = found_pos_end + len(
                                actual_end_marker_log
                            )
                        else:
                            current_end_index = -1
                    except Exception:
                        current_end_index = -1

                total_checks += 1
                marker_errors = []

                if not start_marker or not end_marker:
                    marker_errors.append("Marqueur(s) Manquant(s)")
                else:
                    # La logique de current_start_index et current_end_index remplace les simples 'in'
                    start_found = current_start_index != -1
                    end_found_after_start = current_end_index != -1 and (
                        current_start_index + len(start_marker)
                        <= current_end_index - len(end_marker)
                        if start_marker and end_marker
                        else False
                    )

                    if not start_found:
                        marker_errors.append("Début NON TROUVÉ")
                    # Vérifier si end_marker a été trouvé *après* start_marker.
                    # current_end_index est la position *après* le marqueur de fin.
                    # current_start_index est la position *de début* du marqueur de début.
                    # Il faut que le début du marqueur de fin soit après la fin du marqueur de début.
                    # Position de début du marqueur de fin = current_end_index - len(end_marker)
                    # Position de fin du marqueur de début = current_start_index + len(start_marker)
                    if start_found and not (
                        end_marker
                        and current_end_index != -1
                        and (current_end_index - len(end_marker))
                        >= (current_start_index + len(start_marker))
                    ):
                        marker_errors.append("Fin NON TROUVÉE (après début)")
                    elif (
                        not start_found and end_marker and current_end_index != -1
                    ):  # Fin trouvée mais pas début
                        marker_errors.append("Fin TROUVÉE mais Début NON TROUVÉ")

                if marker_errors:
                    verification_logger.warning(
                        f"      -> ❌ Problème Extrait '{extract_name}': {', '.join(marker_errors)}"
                    )
                    results.append(
                        f"<li>{source_name} -> {extract_name}: <strong style='color:red;'>{', '.join(marker_errors)}</strong></li>"
                    )
                    total_errors += 1
                else:
                    verification_logger.info(
                        f"      -> [OK] OK: Extrait '{extract_name}'"
                    )
        else:
            num_extracts = len(source_info.get("extracts", []))
            # source_type n'est plus directement utilisé ici pour la condition is_plaintext
            # car get_full_text_for_source gère déjà cela.
            # On vérifie juste si texte_brut_source est None.
            # La distinction Tika binaire vs plaintext est gérée dans get_full_text_for_source/fetch_with_tika
            results.append(
                f"<li>{source_name}: Vérification impossible (texte source non obtenu ou vide)</li>"
            )
            total_errors += num_extracts  # Compter tous les extraits comme erreur si la source n'est pas chargée
            total_checks += num_extracts

    summary = f"--- Résultat Vérification ---<br/>{total_checks} extraits vérifiés. <strong style='color: {'red' if total_errors > 0 else 'green'};'>{total_errors} erreur(s) trouvée(s).</strong>"
    if results:
        summary += "<br/>Détails :<ul>" + "".join(results) + "</ul>"
    else:
        if total_checks > 0:
            summary += "<br/>Tous les marqueurs semblent corrects."
        else:
            summary += "<br/>Aucun extrait n'a pu être vérifié."

    verification_logger.info(
        "\n"
        + f"{summary.replace('<br/>', chr(10)).replace('<li>', '- ').replace('</li>', '').replace('<ul>', '').replace('</ul>', '').replace('<strong>', '').replace('</strong>', '')}"
    )
    return summary


verification_logger.info("Utilitaires de vérification UI définis.")

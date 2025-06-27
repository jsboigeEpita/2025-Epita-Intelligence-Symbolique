# -*- coding: utf-8 -*-
"""
Utilitaires pour la vérification des extraits.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple # Ajout de Tuple

# Imports nécessaires pour la logique du pipeline et des fonctions déplacées
# from project_core.service_setup.core_services import initialize_core_services # Remplacé par initialisation manuelle
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract # Pour typer les objets DefinitionService
# Imports pour les fonctions déplacées depuis marker_verification_logic.py
from argumentation_analysis.ui.extract_utils import load_source_text, extract_text_with_markers

# Imports pour l'initialisation manuelle des services
from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.crypto_service import CryptoService
from argumentation_analysis.services.definition_service import DefinitionService
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.ui.config import (
    ENCRYPTION_KEY as DEFAULT_ENCRYPTION_KEY,
    CONFIG_FILE as DEFAULT_CONFIG_FILE_PATH,
    CONFIG_FILE_JSON as DEFAULT_CONFIG_FILE_JSON_PATH
)


logger = logging.getLogger(__name__)

# --- Fonctions déplacées depuis argumentation_analysis/utils/extract_repair/marker_verification_logic.py ---

def verify_extract(source_info: Dict[str, Any], extract_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vérifie qu'un extrait est correctement défini et peut être extrait du texte source.
    
    Args:
        source_info: Informations sur la source (doit contenir au moins 'source_name', et des infos pour load_source_text)
        extract_info: Informations sur l'extrait (doit contenir 'extract_name', 'start_marker', 'end_marker', 'template_start')
        
    Returns:
        Dict[str, Any]: Résultat de la vérification
    """
    source_name = source_info.get("source_name", "Source inconnue")
    extract_name = extract_info.get("extract_name", "Extrait inconnu")
    start_marker = extract_info.get("start_marker", "")
    end_marker = extract_info.get("end_marker", "")
    template_start = extract_info.get("template_start", "")
    
    logger.info(f"Vérification de l'extrait '{extract_name}' de la source '{source_name}'...")
    
    # Convertir le dictionnaire en objet SourceDefinition pour utiliser get_url()
    # et assurer la cohérence des types.
    source_definition_obj = SourceDefinition.from_dict(source_info)
    
    source_text, url = load_source_text(source_definition_obj)
    if not source_text:
        logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
        return {
            "source_name": source_name, "extract_name": extract_name, "status": "error",
            "message": f"Impossible de charger le texte source: {url}",
            "start_found": False, "end_found": False
        }
    
    extracted_text, status, start_found, end_found = extract_text_with_markers(
        source_text, start_marker, end_marker, template_start
    )
    
    result_details: Dict[str, Any] = {
        "source_name": source_name, "extract_name": extract_name,
        "start_found": start_found, "end_found": end_found,
        "messages": [] # Initialiser une liste pour les messages
    }

    if start_found and end_found:
        current_status = "valid" # Statut initial si les marqueurs sont trouvés
        
        result_details["extracted_length"] = len(extracted_text)
        
        # Condition 1: Texte court
        if len(extracted_text) < 10:
            logger.warning(f"Extrait '{extract_name}' valide mais très court ({len(extracted_text)} caractères).")
            current_status = "warning"
            result_details["messages"].append(f"Extrait valide mais très court ({len(extracted_text)} caractères).")
            result_details["too_short"] = True # Pour le rapport

        # Condition 2: Problème de template (marqueur de début ne correspond pas au template attendu)
        template_prefix = template_start.replace("{0}", "")
        if template_prefix and start_marker and not start_marker.startswith(template_prefix):
            warning_message = f"Avertissement: Le marqueur de début '{start_marker}' ne commence pas par le template attendu '{template_prefix}'."
            logger.warning(f"Extrait '{extract_name}': {warning_message}")
            current_status = "warning"
            if warning_message not in result_details["messages"]:
                result_details["messages"].append(warning_message)
            result_details["template_issue"] = True
        # La logique précédente pour la première lettre manquante était trop spécifique.
        # Cette condition plus générale devrait couvrir le cas du test.

        # Condition 3: Caractères spéciaux / Problèmes d'encodage
        special_chars_to_check = ["\\u", "\\x"]
        has_encoding_issues = any(char_seq in extracted_text for char_seq in special_chars_to_check if char_seq)
        if has_encoding_issues:
            warning_message = "Extrait valide mais contient des caractères spéciaux potentiellement mal encodés."
            logger.warning(f"Extrait '{extract_name}': {warning_message}")
            current_status = "warning"
            if warning_message not in result_details["messages"]: # Éviter les doublons
                result_details["messages"].append(warning_message)
            result_details["encoding_issues"] = True

        result_details["status"] = current_status
        if not result_details["messages"] and current_status == "valid":
            result_details["messages"].append("Extrait valide. Les deux marqueurs ont été trouvés.")
        elif not result_details["messages"] and current_status == "warning": # Fallback si un warning a été mis sans message
            result_details["messages"].append("Extrait valide avec avertissement(s).")
            
        # Concaténer les messages pour le champ "message" principal
        result_details["message"] = " | ".join(result_details["messages"])

    else: # Cas où start_found ou end_found (ou les deux) sont faux
        result_details["status"] = "invalid"
        if not start_found and not end_found: result_details["message"] = "Extrait invalide. Les deux marqueurs sont introuvables."
        elif not start_found: result_details["message"] = "Extrait invalide. Le marqueur de début est introuvable."
        else: result_details["message"] = "Extrait invalide. Le marqueur de fin est introuvable."
        logger.error(f"Extrait '{extract_name}' invalide. {result_details['message']}")
        
    return result_details

def verify_all_extracts(
    extract_definitions_list: List[Dict[str, Any]], # Attend une liste de dictionnaires (sources)
    # fetch_service et extract_service ne sont pas directement utilisés par cette version de la logique
    # car verify_extract appelle load_source_text et extract_text_with_markers qui sont supposés
    # gérer leur propre logique de fetch/extraction ou être des utilitaires purs.
    # Si FetchService et ExtractService étaient nécessaires ici, ils devraient être passés.
    # Pour l'instant, on les retire des arguments de cette fonction de haut niveau.
) -> List[Dict[str, Any]]:
    """
    Vérifie tous les extraits dans la liste de définitions fournie.
    (Anciennement verify_extracts, renommée pour clarté et adaptée)
    """
    logger.info("Vérification de tous les extraits (dans verification_utils)...")
    results = []
    for source_idx, source_data_dict in enumerate(extract_definitions_list):
        source_name = source_data_dict.get("source_name", f"Source #{source_idx}")
        logger.info(f"Vérification de la source '{source_name}'...")
        
        extracts_data_list = source_data_dict.get("extracts", [])
        for extract_data_dict in extracts_data_list:
            # verify_extract attend des dictionnaires pour source_info et extract_info
            # source_data_dict est déjà le dict pour la source.
            result = verify_extract(source_data_dict, extract_data_dict)
            results.append(result)
    return results

def generate_verification_report(results: List[Dict[str, Any]], output_file_str: str) -> None:
    """
    Génère un rapport HTML des résultats de la vérification.
    (Anciennement generate_report, renommée pour clarté)
    """
    logger.info(f"Génération du rapport de vérification dans '{output_file_str}'...")
    
    status_counts = {"valid": 0, "warning": 0, "invalid": 0, "error": 0}
    issue_types = {
        "start_marker_missing": 0, "end_marker_missing": 0, "both_markers_missing": 0,
        "template_issue": 0, "encoding_issue": 0, "too_short": 0, "source_loading_error": 0
    }

    for result in results:
        status = result.get("status", "error")
        if status in status_counts: status_counts[status] += 1
        
        if status == "invalid":
            if not result.get("start_found") and not result.get("end_found"): issue_types["both_markers_missing"] += 1
            elif not result.get("start_found"): issue_types["start_marker_missing"] += 1
            elif not result.get("end_found"): issue_types["end_marker_missing"] += 1
        elif status == "warning":
            if result.get("template_issue"): issue_types["template_issue"] += 1
            if result.get("encoding_issues"): issue_types["encoding_issue"] += 1
            # La clé "extracted_length" peut ne pas être présente si le statut n'est pas "valid" ou "warning" avec longueur.
            if result.get("extracted_length", 100) < 10 : issue_types["too_short"] +=1
        elif status == "error":
            issue_types["source_loading_error"] += 1

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport de vérification des extraits</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .valid {{ color: green; }} .warning {{ color: orange; }}
            .invalid {{ color: red; }} .error {{ color: darkred; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .details {{ margin-top: 5px; font-size: 0.9em; color: #666; }}
            .issue-types {{ margin-top: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Rapport de vérification des extraits</h1>
        <div class="summary">
            <h2>Résumé</h2>
            <p>Total des extraits vérifiés: <strong>{len(results)}</strong></p>
            <p>Extraits valides: <strong class="valid">{status_counts["valid"]}</strong></p>
            <p>Extraits avec avertissements: <strong class="warning">{status_counts["warning"]}</strong></p>
            <p>Extraits invalides: <strong class="invalid">{status_counts["invalid"]}</strong></p>
            <p>Erreurs: <strong class="error">{status_counts["error"]}</strong></p>
            <div class="issue-types">
                <h3>Types de problèmes</h3>
                <p>Marqueur de début manquant: <strong>{issue_types["start_marker_missing"]}</strong></p>
                <p>Marqueur de fin manquant: <strong>{issue_types["end_marker_missing"]}</strong></p>
                <p>Les deux marqueurs manquants: <strong>{issue_types["both_markers_missing"]}</strong></p>
                <p>Problème de template: <strong>{issue_types["template_issue"]}</strong></p>
                <p>Problème d'encodage: <strong>{issue_types["encoding_issue"]}</strong></p>
                <p>Extrait trop court: <strong>{issue_types["too_short"]}</strong></p>
                <p>Erreur de chargement de la source: <strong>{issue_types["source_loading_error"]}</strong></p>
            </div>
        </div>
        <h2>Détails des vérifications</h2>
        <table>
            <tr><th>Source</th><th>Extrait</th><th>Statut</th><th>Détails</th></tr>
    """
    for result in results:
        source_name = result.get("source_name", "Source inconnue")
        extract_name = result.get("extract_name", "Extrait inconnu")
        status = result.get("status", "error")
        message = result.get("message", "Aucun message")
        details_html = ""
        if status == "valid":
            details_html = f"<div class='details'><p><strong>Longueur de l'extrait:</strong> {result.get('extracted_length', 'N/A')} caractères</p></div>"
        elif status == "warning":
            details_html = f"""
            <div class="details">
                <p><strong>Début trouvé:</strong> {result.get('start_found')}</p> <p><strong>Fin trouvée:</strong> {result.get('end_found')}</p>
                <p><strong>Problème template:</strong> {result.get('template_issue', False)}</p> <p><strong>Problème encodage:</strong> {result.get('encoding_issues', False)}</p>
                <p><strong>Longueur:</strong> {result.get('extracted_length', 'N/A')}</p>
            </div>"""
        elif status == "invalid":
            details_html = f"<div class='details'><p><strong>Début trouvé:</strong> {result.get('start_found')}</p><p><strong>Fin trouvée:</strong> {result.get('end_found')}</p></div>"
        
        html_content += f"""
        <tr class="{status}"><td>{source_name}</td><td>{extract_name}</td><td>{status}</td><td>{message}{details_html}</td></tr>
        """
    html_content += "</table></body></html>"
    
    output_file = Path(output_file_str)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"Rapport de vérification généré dans '{output_file}'.")


# --- Pipeline (précédemment défini ici) ---

def run_extract_verification_pipeline(
    project_root_dir: Path,
    output_report_path_str: str,
    custom_input_path_str: Optional[str],
    hitler_only: bool
):
    """
    Exécute le pipeline de vérification des extraits.
    """
    logger.info("Démarrage du pipeline de vérification des extraits...")
    logger.info(f"Racine du projet utilisée pour le pipeline: {project_root_dir}")

    try:
        config_file_to_use = Path(custom_input_path_str) if custom_input_path_str else None
        
        # Remplacement de initialize_core_services
        logger.info("Initialisation manuelle des services pour verification_utils...")
        base_path = project_root_dir if project_root_dir else Path.cwd()

        current_encryption_key = DEFAULT_ENCRYPTION_KEY # TODO: Permettre la surcharge via config si nécessaire
        
        current_config_file = config_file_to_use if config_file_to_use else base_path / DEFAULT_CONFIG_FILE_PATH
        if not current_config_file.is_absolute():
            current_config_file = base_path / current_config_file
        
        current_fallback_file = base_path / DEFAULT_CONFIG_FILE_JSON_PATH # TODO: Permettre la surcharge
        if not current_fallback_file.is_absolute():
            current_fallback_file = base_path / current_fallback_file
        if not current_fallback_file.exists():
            logger.warning(f"Fichier de fallback JSON {current_fallback_file.resolve()} non trouvé.")
            current_fallback_file = None

        crypto_service = CryptoService(current_encryption_key)
        
        cache_dir = base_path / "argumentation_analysis" / "text_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_service = CacheService(cache_dir=cache_dir)
        
        extract_service = ExtractService()
        
        temp_download_dir = base_path / "argumentation_analysis" / "temp_downloads"
        temp_download_dir.mkdir(parents=True, exist_ok=True)
        fetch_service = FetchService(cache_service=cache_service, temp_download_dir=temp_download_dir)
        
        definition_service = DefinitionService(
            crypto_service=crypto_service,
            config_file=current_config_file,
            fallback_file=current_fallback_file
        )
        logger.info("Services initialisés manuellement pour verification_utils.")

        # extract_service, fetch_service, definition_service sont maintenant disponibles localement
        
        extract_definitions_obj, error_message = definition_service.load_definitions() # C'est un objet ExtractDefinitions
        if error_message:
            logger.warning(f"Avertissement lors du chargement des définitions (pipeline): {error_message}")

        if not extract_definitions_obj or not extract_definitions_obj.sources:
            logger.error("Aucune définition d'extrait chargée ou sources vides. Arrêt du pipeline.")
            return
            
        logger.info(f"{len(extract_definitions_obj.sources)} sources chargées dans le pipeline.")
        
        # Convertir ExtractDefinitions en List[Dict[str, Any]] pour verify_all_extracts
        definitions_as_list_of_dicts: List[Dict[str, Any]] = []
        if hasattr(extract_definitions_obj, 'sources'):
            for source_def_obj in extract_definitions_obj.sources:
                if hasattr(source_def_obj, 'to_dict'): # Vérifier si la méthode existe
                    definitions_as_list_of_dicts.append(source_def_obj.to_dict())
                else: # Fallback si to_dict n'existe pas (ne devrait pas arriver avec les modèles Pydantic)
                    logger.warning(f"Source {source_def_obj.source_name} n'a pas de méthode to_dict().")
                    # Créer un dict manuellement si nécessaire, ou ignorer.
                    # Pour l'instant, on l'ignore pour éviter une erreur si la structure est inattendue.

        if hitler_only:
            original_count = len(definitions_as_list_of_dicts)
            definitions_as_list_of_dicts = [
                source_dict for source_dict in definitions_as_list_of_dicts
                if "hitler" in source_dict.get("source_name", "").lower()
            ]
            logger.info(f"Filtrage des sources (pipeline): {len(definitions_as_list_of_dicts)}/{original_count} sources retenues.")

        if not definitions_as_list_of_dicts:
            logger.warning("Aucune source restante après filtrage. Arrêt du pipeline de vérification.")
            return

        logger.info("Démarrage de la vérification des extraits (pipeline)...")
        # verify_all_extracts attend List[Dict], et les services ne sont plus passés directement
        results = verify_all_extracts(definitions_as_list_of_dicts)
        logger.info(f"Vérification terminée (pipeline). {len(results)} résultats obtenus.")
        
        output_report_file = Path(output_report_path_str)
        output_report_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Génération du rapport dans {output_report_file} (pipeline)...")
        generate_verification_report(results, str(output_report_file)) # Renommé
        logger.info(f"Rapport généré dans {output_report_file} (pipeline)")
        
    except Exception as e:
        logger.error(f"Exception non gérée dans le pipeline de vérification: {e}", exc_info=True)
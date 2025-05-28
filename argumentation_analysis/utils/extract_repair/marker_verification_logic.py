#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logique métier pour la vérification des extraits.

Contient les fonctions pour vérifier un ou tous les extraits,
et pour générer un rapport de vérification.
"""

import os
import json
import logging
from pathlib import Path # Ajouté pour Path si nécessaire
from typing import List, Dict, Any, Tuple, Optional

# Configuration du logging pour ce module
logger = logging.getLogger("MarkerVerificationLogic")
# La configuration de base (handlers, level) est généralement faite au niveau de l'application.

# Imports nécessaires pour les fonctions de logique métier
# Ces imports doivent pointer vers les modules réels du projet
# et non les mocks ou fallbacks qui étaient dans le script original.
# Assurez-vous que ces chemins sont corrects par rapport à la structure du projet.
from argumentation_analysis.ui.utils import load_from_cache, reconstruct_url # Exemple, à ajuster
from argumentation_analysis.ui.extract_utils import load_source_text, extract_text_with_markers # Exemple, à ajuster
# Si ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON sont nécessaires ici,
# ils devraient être passés en argument ou importés depuis un module de configuration central.


def verify_extract(source_info: Dict[str, Any], extract_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vérifie qu'un extrait est correctement défini et peut être extrait du texte source.
    
    Args:
        source_info: Informations sur la source
        extract_info: Informations sur l'extrait
        
    Returns:
        Dict[str, Any]: Résultat de la vérification
    """
    source_name = source_info.get("source_name", "Source inconnue")
    extract_name = extract_info.get("extract_name", "Extrait inconnu")
    start_marker = extract_info.get("start_marker", "")
    end_marker = extract_info.get("end_marker", "")
    template_start = extract_info.get("template_start", "")
    
    logger.info(f"Vérification de l'extrait '{extract_name}' de la source '{source_name}'...")
    
    # Chargement du texte source
    # La fonction load_source_text doit être disponible et correctement importée
    source_text, url = load_source_text(source_info)
    if not source_text:
        logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "error",
            "message": f"Impossible de charger le texte source: {url}",
            "start_found": False,
            "end_found": False
        }
    
    # Extraction du texte avec les marqueurs
    # La fonction extract_text_with_markers doit être disponible et correctement importée
    extracted_text, status, start_found, end_found = extract_text_with_markers(
        source_text, start_marker, end_marker, template_start
    )
    
    if start_found and end_found:
        logger.info(f"Extrait '{extract_name}' valide. Les deux marqueurs ont été trouvés.")
        
        if len(extracted_text) < 10:
            logger.warning(f"Extrait '{extract_name}' valide mais très court ({len(extracted_text)} caractères).")
            return {
                "source_name": source_name,
                "extract_name": extract_name,
                "status": "warning",
                "message": f"Extrait valide mais très court ({len(extracted_text)} caractères).",
                "start_found": True,
                "end_found": True,
                "extracted_length": len(extracted_text)
            }
        
        if template_start and "{0}" in template_start:
            first_letter = template_start.replace("{0}", "")
            if start_marker and not start_marker.startswith(first_letter):
                logger.warning(f"Extrait '{extract_name}' valide mais avec un marqueur de début potentiellement corrompu (première lettre manquante).")
                return {
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "warning",
                    "message": f"Extrait valide mais avec un marqueur de début potentiellement corrompu (première lettre manquante).",
                    "start_found": True,
                    "end_found": True,
                    "template_issue": True
                }
        
        # Vérification des caractères spéciaux (simplifiée)
        # La définition de special_chars peut nécessiter un ajustement
        special_chars_to_check = ["\\u", "\\x"] # Exemple, à affiner
        has_encoding_issues = any(char_seq in extracted_text for char_seq in special_chars_to_check if char_seq) # Ignorer ""
        if has_encoding_issues:
            logger.warning(f"Extrait '{extract_name}' valide mais contient des caractères spéciaux potentiellement mal encodés.")
            return {
                "source_name": source_name,
                "extract_name": extract_name,
                "status": "warning",
                "message": f"Extrait valide mais contient des caractères spéciaux potentiellement mal encodés.",
                "start_found": True,
                "end_found": True,
                "encoding_issues": True
            }
        
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "valid",
            "message": "Extrait valide. Les deux marqueurs ont été trouvés.",
            "start_found": True,
            "end_found": True,
            "extracted_length": len(extracted_text)
        }
    
    if not start_found and not end_found:
        message = "Extrait invalide. Les deux marqueurs sont introuvables."
    elif not start_found:
        message = "Extrait invalide. Le marqueur de début est introuvable."
    else:  # not end_found
        message = "Extrait invalide. Le marqueur de fin est introuvable."
        
    logger.error(f"Extrait '{extract_name}' invalide. {message}")
    return {
        "source_name": source_name,
        "extract_name": extract_name,
        "status": "invalid",
        "message": message,
        "start_found": start_found,
        "end_found": end_found
    }

def verify_all_extracts(extract_definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Vérifie tous les extraits dans le fichier de configuration.
    
    Args:
        extract_definitions: Liste des définitions d'extraits (dictionnaires)
        
    Returns:
        List[Dict[str, Any]]: Résultats de la vérification
    """
    logger.info("Vérification de tous les extraits...")
    results = []
    for source_idx, source_info in enumerate(extract_definitions):
        source_name = source_info.get("source_name", f"Source #{source_idx}")
        logger.info(f"Vérification de la source '{source_name}'...")
        
        extracts = source_info.get("extracts", [])
        for extract_idx, extract_info in enumerate(extracts):
            result = verify_extract(source_info, extract_info)
            results.append(result)
    return results

def generate_verification_report(results: List[Dict[str, Any]], output_file: str = "verify_extracts_report.html") -> None:
    """
    Génère un rapport HTML des résultats de la vérification.
    (Renommée pour éviter conflit avec d'autres generate_report)
    """
    logger.info(f"Génération du rapport de vérification dans '{output_file}'...")
    
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
            if result.get("extracted_length", 0) < 10: issue_types["too_short"] += 1
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
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"Rapport de vérification généré dans '{output_file}'.")
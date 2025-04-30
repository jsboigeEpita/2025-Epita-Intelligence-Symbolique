#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de vérification des extraits dans le fichier de configuration

Ce script vérifie que tous les extraits définis dans extract_sources_updated.json
sont correctement définis et peuvent être extraits du texte source.

Il génère un rapport détaillé des résultats de la vérification.
"""

import os
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("VerifyExtracts")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("verify_extracts.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)

# Imports depuis les modules du projet
import sys

# Ajouter le répertoire parent au chemin d'importation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    # Import relatif depuis le package utils
    logger.info("Tentative d'import relatif...")
    from ...ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
    from ...ui.utils import load_from_cache, reconstruct_url
    from ...ui.extract_utils import (
        load_source_text, extract_text_with_markers, find_similar_text,
        load_extract_definitions_safely, save_extract_definitions_safely
    )
    logger.info("Import relatif réussi.")
except ImportError as e:
    logger.warning(f"Import relatif échoué: {e}")
    try:
        # Fallback pour les imports absolus
        logger.info("Tentative d'import absolu...")
        from argumentiation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        from argumentiation_analysis.ui.utils import load_from_cache, reconstruct_url
        from argumentiation_analysis.ui.extract_utils import (
            load_source_text, extract_text_with_markers, find_similar_text,
            load_extract_definitions_safely, save_extract_definitions_safely
        )
        logger.info("Import absolu réussi.")
    except ImportError as e:
        logger.error(f"Import absolu échoué: {e}")
        
        # Définir des fonctions de remplacement simples pour les tests
        logger.warning("Utilisation de fonctions de remplacement pour les tests...")
        
        # Constantes de configuration
        ENCRYPTION_KEY = "test_key"
        CONFIG_FILE = "C:/dev/2025-Epita-Intelligence-Symbolique/argumentiation_analysis/data/extract_sources.json"
        CONFIG_FILE_JSON = "C:/dev/2025-Epita-Intelligence-Symbolique/argumentiation_analysis/data/extract_sources.json"
        
        def load_from_cache(url, encryption_key=None):
            logger.info(f"Simulation de chargement depuis le cache pour {url}")
            return None, f"Erreur simulée: Impossible de charger {url}"
        
        def reconstruct_url(source_info):
            schema = source_info.get("schema", "https:")
            host_parts = source_info.get("host_parts", [])
            path = source_info.get("path", "")
            host = ".".join(host_parts) if host_parts else ""
            return f"{schema}//{host}{path}"
        
        def load_source_text(source_info):
            """Charge le texte source d'une définition."""
            logger.info(f"Chargement du texte source pour {source_info.get('source_name', 'Source inconnue')}")
            
            # Reconstruire l'URL
            url = reconstruct_url(source_info)
            
            # Simuler le chargement depuis le cache
            with open("extract_repair/docs/extract_sources_updated.json", 'r', encoding='utf-8') as f:
                extract_definitions = json.load(f)
            
            # Trouver la source correspondante
            for source in extract_definitions:
                if source.get("source_name") == source_info.get("source_name"):
                    # Simuler un texte source
                    source_text = f"Texte source simulé pour {source_info.get('source_name')}"
                    return source_text, url
            
            return None, f"Erreur: Source {source_info.get('source_name')} non trouvée"
        
        def extract_text_with_markers(source_text, start_marker, end_marker, template_start=None):
            """Extrait le texte avec les marqueurs."""
            logger.info(f"Extraction de texte avec les marqueurs: '{start_marker}' et '{end_marker}'")
            
            # Appliquer le template si présent
            if template_start and "{0}" in template_start:
                first_letter = template_start.replace("{0}", "")
                if start_marker and not start_marker.startswith(first_letter):
                    start_marker = first_letter + start_marker
                    logger.info(f"Marqueur de début corrigé avec template: '{start_marker}'")
            
            # Vérifier si les marqueurs sont présents
            start_found = start_marker in source_text
            end_found = end_marker in source_text
            
            if start_found and end_found:
                start_pos = source_text.find(start_marker)
                end_pos = source_text.find(end_marker, start_pos + len(start_marker))
                
                if start_pos >= 0 and end_pos > start_pos:
                    extracted = source_text[start_pos:end_pos + len(end_marker)]
                    return extracted, "success", True, True
            
            return "", "error", start_found, end_found
        
        def find_similar_text(text, pattern, context_size=50, max_results=5):
            logger.info(f"Recherche de texte similaire à '{pattern}'")
            return []
        
        def load_extract_definitions_safely(config_file, encryption_key=None, fallback_file=None):
            logger.info(f"Chargement des définitions d'extraits depuis {config_file}")
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    extract_definitions = json.load(f)
                return extract_definitions, None
            except Exception as e:
                error_msg = f"Erreur lors du chargement des définitions d'extraits: {str(e)}"
                logger.error(error_msg)
                return [], error_msg
        
        def save_extract_definitions_safely(extract_definitions, config_file, encryption_key=None, fallback_file=None):
            logger.info(f"Sauvegarde des définitions d'extraits dans {config_file}")
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(extract_definitions, f, indent=4, ensure_ascii=False)
                return True, None
            except Exception as e:
                error_msg = f"Erreur lors de la sauvegarde des définitions d'extraits: {str(e)}"
                logger.error(error_msg)
                return False, error_msg

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
    extracted_text, status, start_found, end_found = extract_text_with_markers(
        source_text, start_marker, end_marker, template_start
    )
    
    # Vérifier si les deux marqueurs sont trouvés
    if start_found and end_found:
        logger.info(f"Extrait '{extract_name}' valide. Les deux marqueurs ont été trouvés.")
        
        # Vérifier si l'extrait est vide ou trop court
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
        
        # Vérifier si le template est utilisé et si le marqueur de début est potentiellement corrompu
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
        
        # Vérifier si l'extrait contient des caractères spéciaux mal encodés
        special_chars = ["", "\\u", "\\x"]
        has_encoding_issues = any(char in extracted_text for char in special_chars)
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
    
    # Si au moins un marqueur est manquant
    if not start_found and not end_found:
        logger.error(f"Extrait '{extract_name}' invalide. Les deux marqueurs sont introuvables.")
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "invalid",
            "message": "Extrait invalide. Les deux marqueurs sont introuvables.",
            "start_found": False,
            "end_found": False
        }
    elif not start_found:
        logger.error(f"Extrait '{extract_name}' invalide. Le marqueur de début est introuvable.")
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "invalid",
            "message": "Extrait invalide. Le marqueur de début est introuvable.",
            "start_found": False,
            "end_found": True
        }
    else:  # not end_found
        logger.error(f"Extrait '{extract_name}' invalide. Le marqueur de fin est introuvable.")
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "invalid",
            "message": "Extrait invalide. Le marqueur de fin est introuvable.",
            "start_found": True,
            "end_found": False
        }

def verify_all_extracts(extract_definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Vérifie tous les extraits dans le fichier de configuration.
    
    Args:
        extract_definitions: Liste des définitions d'extraits
        
    Returns:
        List[Dict[str, Any]]: Résultats de la vérification
    """
    logger.info("Vérification de tous les extraits...")
    
    # Liste pour stocker les résultats
    results = []
    
    # Parcourir toutes les sources et leurs extraits
    for source_idx, source_info in enumerate(extract_definitions):
        source_name = source_info.get("source_name", f"Source #{source_idx}")
        logger.info(f"Vérification de la source '{source_name}'...")
        
        extracts = source_info.get("extracts", [])
        for extract_idx, extract_info in enumerate(extracts):
            extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")
            
            # Vérifier l'extrait
            result = verify_extract(source_info, extract_info)
            results.append(result)
    
    return results

def generate_report(results: List[Dict[str, Any]], output_file: str = "verify_extracts_report.html") -> None:
    """
    Génère un rapport HTML des résultats de la vérification.
    
    Args:
        results: Résultats de la vérification
        output_file: Chemin du fichier de sortie
    """
    logger.info(f"Génération du rapport dans '{output_file}'...")
    
    # Compter les différents statuts
    status_counts = {
        "valid": 0,
        "warning": 0,
        "invalid": 0,
        "error": 0
    }
    
    # Compter les types de problèmes
    issue_types = {
        "start_marker_missing": 0,
        "end_marker_missing": 0,
        "both_markers_missing": 0,
        "template_issue": 0,
        "encoding_issue": 0,
        "too_short": 0,
        "source_loading_error": 0
    }
    
    for result in results:
        status = result.get("status", "error")
        if status in status_counts:
            status_counts[status] += 1
        
        # Analyser les types de problèmes
        if status == "invalid":
            if not result.get("start_found") and not result.get("end_found"):
                issue_types["both_markers_missing"] += 1
            elif not result.get("start_found"):
                issue_types["start_marker_missing"] += 1
            elif not result.get("end_found"):
                issue_types["end_marker_missing"] += 1
        elif status == "warning":
            if result.get("template_issue"):
                issue_types["template_issue"] += 1
            if result.get("encoding_issues"):
                issue_types["encoding_issue"] += 1
            if result.get("extracted_length", 0) < 10:
                issue_types["too_short"] += 1
        elif status == "error":
            issue_types["source_loading_error"] += 1
    
    # Générer le contenu HTML
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
            .valid {{ color: green; }}
            .warning {{ color: orange; }}
            .invalid {{ color: red; }}
            .error {{ color: darkred; }}
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
            <tr>
                <th>Source</th>
                <th>Extrait</th>
                <th>Statut</th>
                <th>Détails</th>
            </tr>
    """
    
    # Ajouter une ligne pour chaque résultat
    for result in results:
        source_name = result.get("source_name", "Source inconnue")
        extract_name = result.get("extract_name", "Extrait inconnu")
        status = result.get("status", "error")
        message = result.get("message", "Aucun message")
        
        details = ""
        if status == "valid":
            details += f"""
            <div class="details">
                <p><strong>Longueur de l'extrait:</strong> {result.get('extracted_length', 'Non disponible')} caractères</p>
            </div>
            """
        elif status == "warning":
            details += f"""
            <div class="details">
                <p><strong>Marqueur de début trouvé:</strong> {"Oui" if result.get('start_found') else "Non"}</p>
                <p><strong>Marqueur de fin trouvé:</strong> {"Oui" if result.get('end_found') else "Non"}</p>
                <p><strong>Problème de template:</strong> {"Oui" if result.get('template_issue') else "Non"}</p>
                <p><strong>Problème d'encodage:</strong> {"Oui" if result.get('encoding_issues') else "Non"}</p>
                <p><strong>Longueur de l'extrait:</strong> {result.get('extracted_length', 'Non disponible')} caractères</p>
            </div>
            """
        elif status == "invalid":
            details += f"""
            <div class="details">
                <p><strong>Marqueur de début trouvé:</strong> {"Oui" if result.get('start_found') else "Non"}</p>
                <p><strong>Marqueur de fin trouvé:</strong> {"Oui" if result.get('end_found') else "Non"}</p>
            </div>
            """
        
        html_content += f"""
        <tr class="{status}">
            <td>{source_name}</td>
            <td>{extract_name}</td>
            <td>{status}</td>
            <td>{message}{details}</td>
        </tr>
        """
    
    html_content += """
        </table>
    </body>
    </html>
    """
    
    # Écrire le rapport dans un fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Rapport généré dans '{output_file}'.")

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Vérification des extraits dans le fichier de configuration")
    parser.add_argument("--input", "-i", default="extract_repair/docs/extract_sources_updated.json",
                        help="Fichier d'entrée (extract_sources_updated.json)")
    parser.add_argument("--output", "-o", default="extract_repair/docs/verify_extracts_report.html",
                        help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Activer le mode verbeux")
    
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de vérification des extraits...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    logger.info(f"Chemin du script: {os.path.abspath(__file__)}")
    
    # Vérifier que le fichier d'entrée existe
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Le fichier {args.input} n'existe pas.")
        return
    
    # Charger les définitions d'extraits
    logger.info(f"Chargement des définitions d'extraits depuis {args.input}...")
    try:
        extract_definitions, error_message = load_extract_definitions_safely(args.input)
        if error_message:
            logger.error(f"Erreur lors du chargement des définitions d'extraits: {error_message}")
            return
        
        logger.info(f"{len(extract_definitions)} sources chargées.")
        
        # Afficher les premières sources pour vérification
        for i, source in enumerate(extract_definitions[:2]):
            logger.info(f"Source {i}: {source.get('source_name', 'Sans nom')}")
            logger.info(f"  Type: {source.get('source_type', 'Non spécifié')}")
            logger.info(f"  Extraits: {len(source.get('extracts', []))}")
    except Exception as e:
        logger.error(f"Exception lors du chargement des définitions d'extraits: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return
    
    # Vérifier tous les extraits
    logger.info("Vérification de tous les extraits...")
    try:
        results = verify_all_extracts(extract_definitions)
        logger.info(f"Vérification terminée. {len(results)} résultats obtenus.")
    except Exception as e:
        logger.error(f"Exception lors de la vérification des extraits: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return
    
    # Générer le rapport
    logger.info(f"Génération du rapport dans {args.output}...")
    try:
        generate_report(results, args.output)
        logger.info(f"Rapport généré dans {args.output}")
    except Exception as e:
        logger.error(f"Exception lors de la génération du rapport: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Afficher un résumé des résultats
    valid_count = sum(1 for result in results if result.get("status") == "valid")
    warning_count = sum(1 for result in results if result.get("status") == "warning")
    invalid_count = sum(1 for result in results if result.get("status") == "invalid")
    error_count = sum(1 for result in results if result.get("status") == "error")
    
    logger.info("Résumé des résultats:")
    logger.info(f"  - Extraits vérifiés: {len(results)}")
    logger.info(f"  - Extraits valides: {valid_count}")
    logger.info(f"  - Extraits avec avertissements: {warning_count}")
    logger.info(f"  - Extraits invalides: {invalid_count}")
    logger.info(f"  - Erreurs: {error_count}")
    
    # Afficher les extraits invalides
    if invalid_count > 0:
        logger.info("Extraits invalides:")
        for result in results:
            if result.get("status") == "invalid":
                logger.info(f"  - {result.get('source_name')} - {result.get('extract_name')}: {result.get('message')}")

if __name__ == "__main__":
    main()
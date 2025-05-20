#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de vérification des extraits

Ce script vérifie la validité des extraits définis dans extract_sources.json
en s'assurant que les marqueurs de début et de fin sont présents dans les textes sources.

Fonctionnalités:
- Vérification de la présence des marqueurs dans les textes sources
- Génération d'un rapport détaillé des problèmes détectés
- Prise en charge des templates pour les marqueurs de début
- Vérification spécifique pour le corpus de discours d'Hitler
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
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("VerifyExtracts")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("verify_extracts.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)

# Imports des services et modèles
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.crypto_service import CryptoService
from argumentation_analysis.services.definition_service import DefinitionService
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON


def verify_extracts(
    extract_definitions: ExtractDefinitions,
    fetch_service: FetchService,
    extract_service: ExtractService
) -> List[Dict[str, Any]]:
    """
    Vérifie la validité des extraits.
    
    Args:
        extract_definitions: Définitions d'extraits
        fetch_service: Service de récupération
        extract_service: Service d'extraction
        
    Returns:
        Liste des résultats de vérification
    """
    logger.info("Vérification des extraits...")
    
    # Liste pour stocker les résultats
    results = []
    
    # Compteurs pour le résumé
    total_extracts = 0
    valid_extracts = 0
    invalid_extracts = 0
    
    # Parcourir toutes les sources et leurs extraits
    for source_idx, source_info in enumerate(extract_definitions.sources):
        source_name = source_info.source_name
        logger.info(f"Vérification de la source '{source_name}'...")
        
        # Récupérer le texte source
        source_dict = source_info.to_dict()
        source_text, url = fetch_service.fetch_text(source_dict)
        
        if not source_text:
            logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
            
            # Ajouter un résultat d'erreur pour chaque extrait de cette source
            for extract_idx, extract_info in enumerate(source_info.extracts):
                extract_name = extract_info.extract_name
                total_extracts += 1
                invalid_extracts += 1
                
                results.append({
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "error",
                    "message": f"Impossible de charger le texte source: {url}"
                })
            
            continue
        
        # Vérifier chaque extrait
        for extract_idx, extract_info in enumerate(source_info.extracts):
            extract_name = extract_info.extract_name
            start_marker = extract_info.start_marker
            end_marker = extract_info.end_marker
            template_start = extract_info.template_start
            
            logger.info(f"Vérification de l'extrait '{extract_name}'...")
            total_extracts += 1
            
            # Extraction du texte avec les marqueurs
            extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
                source_text, start_marker, end_marker, template_start
            )
            
            # Vérifier si l'extraction a réussi
            if start_found and end_found:
                logger.info(f"Extrait '{extract_name}' valide.")
                valid_extracts += 1
                
                results.append({
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "valid",
                    "message": "Extrait valide."
                })
            else:
                logger.warning(f"Extrait '{extract_name}' invalide: {status}")
                invalid_extracts += 1
                
                # Déterminer le problème spécifique
                if not start_found and not end_found:
                    message = "Marqueurs de début et de fin non trouvés."
                elif not start_found:
                    message = "Marqueur de début non trouvé."
                elif not end_found:
                    message = "Marqueur de fin non trouvé."
                else:
                    message = "Problème inconnu."
                
                results.append({
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "invalid",
                    "message": message
                })
    
    # Afficher le résumé
    logger.info(f"Vérification terminée. {total_extracts} extraits vérifiés.")
    logger.info(f"Extraits valides: {valid_extracts}")
    logger.info(f"Extraits invalides: {invalid_extracts}")
    
    return results


def generate_report(results: List[Dict[str, Any]], output_file: str = "verify_report.html"):
    """
    Génère un rapport HTML des résultats de vérification.
    
    Args:
        results: Résultats de vérification
        output_file: Fichier de sortie pour le rapport HTML
    """
    logger.info(f"Génération du rapport dans '{output_file}'...")
    
    # Compter les différents statuts
    status_counts = {
        "valid": 0,
        "invalid": 0,
        "error": 0
    }
    
    for result in results:
        status = result.get("status", "error")
        if status in status_counts:
            status_counts[status] += 1
    
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
            .invalid {{ color: orange; }}
            .error {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>Rapport de vérification des extraits</h1>
        
        <div class="summary">
            <h2>Résumé</h2>
            <p>Total des extraits vérifiés: <strong>{len(results)}</strong></p>
            <p>Extraits valides: <strong class="valid">{status_counts["valid"]}</strong></p>
            <p>Extraits invalides: <strong class="invalid">{status_counts["invalid"]}</strong></p>
            <p>Erreurs: <strong class="error">{status_counts["error"]}</strong></p>
        </div>
        
        <h2>Détails des vérifications</h2>
        <table>
            <tr>
                <th>Source</th>
                <th>Extrait</th>
                <th>Statut</th>
                <th>Message</th>
            </tr>
    """
    
    # Ajouter une ligne pour chaque résultat
    for result in results:
        source_name = result.get("source_name", "Source inconnue")
        extract_name = result.get("extract_name", "Extrait inconnu")
        status = result.get("status", "error")
        message = result.get("message", "Aucun message")
        
        html_content += f"""
        <tr class="{status}">
            <td>{source_name}</td>
            <td>{extract_name}</td>
            <td>{status}</td>
            <td>{message}</td>
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
    parser = argparse.ArgumentParser(description="Vérification des extraits")
    parser.add_argument("--output", "-o", default="verify_report.html", help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None, help="Fichier d'entrée personnalisé")
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
    
    # Initialiser les services
    try:
        # Créer le service de cache
        cache_dir = Path("./text_cache")
        cache_service = CacheService(cache_dir)
        
        # Créer le service de chiffrement
        crypto_service = CryptoService(ENCRYPTION_KEY)
        
        # Créer le service d'extraction
        extract_service = ExtractService()
        
        # Créer le service de récupération
        temp_download_dir = Path("./temp_downloads")
        fetch_service = FetchService(
            cache_service=cache_service,
            temp_download_dir=temp_download_dir
        )
        
        # Créer le service de définition
        input_file = Path(args.input) if args.input else Path(CONFIG_FILE)
        fallback_file = Path(CONFIG_FILE_JSON) if Path(CONFIG_FILE_JSON).exists() else None
        definition_service = DefinitionService(
            crypto_service=crypto_service,
            config_file=input_file,
            fallback_file=fallback_file
        )
        
        # Charger les définitions d'extraits
        extract_definitions, error_message = definition_service.load_definitions()
        if error_message:
            logger.warning(f"Avertissement lors du chargement des définitions: {error_message}")
        
        logger.info(f"{len(extract_definitions.sources)} sources chargées.")
        
        # Vérifier les extraits
        results = verify_extracts(extract_definitions, fetch_service, extract_service)
        
        # Générer le rapport
        generate_report(results, args.output)
        
    except Exception as e:
        logger.error(f"Exception non gérée: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
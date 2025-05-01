#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution pour la vérification des extraits

Ce script est un point d'entrée simplifié pour exécuter le script de vérification
des extraits. Il utilise les services refactorisés et les modèles centralisés.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RunVerifyExtracts")

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importer le script de vérification
from argumentiation_analysis.scripts.verify_extracts import (
    verify_extracts, generate_report
)

# Importer les services nécessaires
from argumentiation_analysis.services.cache_service import CacheService
from argumentiation_analysis.services.crypto_service import CryptoService
from argumentiation_analysis.services.definition_service import DefinitionService
from argumentiation_analysis.services.extract_service import ExtractService
from argumentiation_analysis.services.fetch_service import FetchService
from argumentiation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Vérification des extraits")
    parser.add_argument("--output", "-o", default="verify_report.html", help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None, help="Fichier d'entrée personnalisé")
    parser.add_argument("--hitler-only", action="store_true", help="Traiter uniquement le corpus de discours d'Hitler")
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de vérification des extraits...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    
    try:
        # Créer le service de cache
        cache_dir = Path("./argumentiation_analysis/text_cache")
        cache_service = CacheService(cache_dir)
        
        # Créer le service de chiffrement
        crypto_service = CryptoService(ENCRYPTION_KEY)
        
        # Créer le service d'extraction
        extract_service = ExtractService()
        
        # Créer le service de récupération
        temp_download_dir = Path("./argumentiation_analysis/temp_downloads")
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
        
        # Filtrer les sources si l'option --hitler-only est activée
        if args.hitler_only:
            original_count = len(extract_definitions.sources)
            extract_definitions.sources = [
                source for source in extract_definitions.sources
                if "hitler" in source.source_name.lower()
            ]
            logger.info(f"Filtrage des sources: {len(extract_definitions.sources)}/{original_count} sources retenues (corpus Hitler).")
        
        # Vérifier les extraits
        results = verify_extracts(extract_definitions, fetch_service, extract_service)
        
        # Générer le rapport
        generate_report(results, args.output)
        logger.info(f"Rapport généré dans {args.output}")
        
    except Exception as e:
        logger.error(f"Exception non gérée: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
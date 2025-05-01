#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution pour la réparation des extraits

Ce script est un point d'entrée simplifié pour exécuter le script de réparation
des bornes défectueuses dans les extraits. Il utilise les services refactorisés
et les modèles centralisés.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RunExtractRepair")

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importer le script de réparation
from argumentiation_analysis.scripts.repair_extract_markers import (
    repair_extract_markers, generate_report, setup_agents
)

# Importer les services nécessaires
from argumentiation_analysis.services.cache_service import CacheService
from argumentiation_analysis.services.crypto_service import CryptoService
from argumentiation_analysis.services.definition_service import DefinitionService
from argumentiation_analysis.services.extract_service import ExtractService
from argumentiation_analysis.services.fetch_service import FetchService
from argumentiation_analysis.core.llm_service import create_llm_service
from argumentiation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON


async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Réparation des bornes défectueuses dans les extraits")
    parser.add_argument("--output", "-o", default="repair_report.html", help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--save", "-s", action="store_true", help="Sauvegarder les modifications")
    parser.add_argument("--hitler-only", action="store_true", help="Traiter uniquement le corpus de discours d'Hitler")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None, help="Fichier d'entrée personnalisé")
    parser.add_argument("--output-json", default="extract_sources_updated.json", help="Fichier de sortie JSON pour vérification")
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de réparation des bornes défectueuses...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    
    try:
        # Créer le service LLM
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM.")
            return
        
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
        
        # Réparer les bornes défectueuses
        logger.info("Démarrage de la réparation des bornes défectueuses...")
        updated_definitions, results = await repair_extract_markers(
            extract_definitions, llm_service, fetch_service, extract_service
        )
        logger.info(f"Réparation terminée. {len(results)} résultats obtenus.")
        
        # Générer le rapport
        logger.info(f"Génération du rapport dans {args.output}...")
        generate_report(results, args.output)
        logger.info(f"Rapport généré dans {args.output}")
        
        # Sauvegarder les modifications si demandé
        if args.save:
            logger.info(f"Sauvegarde des modifications...")
            success, error_message = definition_service.save_definitions(updated_definitions)
            if success:
                logger.info("✅ Modifications sauvegardées avec succès.")
            else:
                logger.error(f"❌ Erreur lors de la sauvegarde: {error_message}")
        
        # Exporter les définitions mises à jour au format JSON pour vérification
        if args.output_json:
            logger.info(f"Exportation des définitions mises à jour dans {args.output_json}...")
            success, message = definition_service.export_definitions_to_json(
                updated_definitions, Path(args.output_json)
            )
            logger.info(message)
    
    except Exception as e:
        logger.error(f"Exception non gérée: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())
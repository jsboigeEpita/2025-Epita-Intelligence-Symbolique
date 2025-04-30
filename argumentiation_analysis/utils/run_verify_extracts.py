#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer la vérification des extraits

Ce script permet de vérifier l'état des extraits sans appliquer de corrections.
Il génère un rapport HTML détaillé des résultats de la vérification.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Ajouter le répertoire parent au chemin d'importation
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

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

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Vérification des extraits dans le fichier de configuration")
    parser.add_argument("--output", "-o", default="verify_extracts_report.html",
                        help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--hitler-only", action="store_true",
                        help="Traiter uniquement le corpus de discours d'Hitler")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None,
                        help="Fichier d'entrée personnalisé")
    
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
    
    # Importer les modules nécessaires
    try:
        # Import direct depuis le répertoire courant
        logger.info("Tentative d'import direct...")
        from extract_repair.verify_extracts import verify_all_extracts, generate_report
        
        # Import depuis le répertoire parent
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from argumentiation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        from argumentiation_analysis.ui.extract_utils import load_extract_definitions_safely
        logger.info("Import direct réussi.")
    except ImportError as e:
        logger.error(f"Erreur d'importation: {e}")
        logger.error("Vérifiez que les modules nécessaires sont présents dans le projet.")
        print(f"\n❌ Erreur lors de l'importation des modules: {e}")
        print("Vérifiez que les modules nécessaires sont présents dans le projet.")
        return
    
    # Charger les définitions d'extraits
    input_file = args.input if args.input else CONFIG_FILE
    logger.info(f"Chargement des définitions d'extraits depuis {input_file}...")
    extract_definitions, error_message = load_extract_definitions_safely(input_file, ENCRYPTION_KEY, CONFIG_FILE_JSON)
    
    if error_message:
        logger.error(f"Erreur lors du chargement des définitions d'extraits: {error_message}")
        return
    
    logger.info(f"{len(extract_definitions)} sources chargées.")
    
    # Afficher les premières sources pour vérification
    for i, source in enumerate(extract_definitions[:2]):
        logger.info(f"Source {i}: {source.get('source_name', 'Sans nom')}")
        logger.info(f"  Type: {source.get('source_type', 'Non spécifié')}")
        logger.info(f"  Extraits: {len(source.get('extracts', []))}")
    
    # Filtrer les sources si l'option --hitler-only est activée
    if args.hitler_only:
        original_count = len(extract_definitions)
        extract_definitions = [
            source for source in extract_definitions
            if "hitler" in source.get("source_name", "").lower()
        ]
        logger.info(f"Filtrage des sources: {len(extract_definitions)}/{original_count} sources retenues (corpus Hitler).")
    
    # Vérifier tous les extraits
    logger.info("Vérification de tous les extraits...")
    results = verify_all_extracts(extract_definitions)
    logger.info(f"Vérification terminée. {len(results)} résultats obtenus.")
    
    # Générer le rapport
    output_file = args.output
    logger.info(f"Génération du rapport dans {output_file}...")
    generate_report(results, output_file)
    logger.info(f"Rapport généré dans {output_file}")
    
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
    
    # Afficher un message de succès
    print(f"\n✅ Vérification des extraits terminée avec succès. Rapport généré dans {output_file}")
    print(f"Résumé: {valid_count} valides, {warning_count} avec avertissements, {invalid_count} invalides, {error_count} erreurs")

if __name__ == "__main__":
    main()
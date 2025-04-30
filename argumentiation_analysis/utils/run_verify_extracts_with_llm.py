#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer la vérification des extraits avec un LLM

Ce script permet de vérifier la qualité des extraits en utilisant un LLM
pour évaluer leur cohérence, pertinence et intégrité.
Il génère un rapport HTML détaillé des résultats de la vérification.
"""

import os
import sys
import argparse
import logging
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au chemin d'importation
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("VerifyExtractsLLM")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("verify_extracts_llm.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)

async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Vérification de la qualité des extraits avec un LLM")
    parser.add_argument("--output", "-o", default="verify_extracts_llm_report.html",
                        help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--hitler-only", action="store_true",
                        help="Traiter uniquement le corpus de discours d'Hitler")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None,
                        help="Fichier d'entrée personnalisé")
    parser.add_argument("--limit", "-l", type=int, default=None,
                        help="Limiter le nombre d'extraits à traiter")
    
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de vérification des extraits avec LLM...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    logger.info(f"Chemin du script: {os.path.abspath(__file__)}")
    
    # Importer les modules nécessaires
    try:
        # Import direct depuis le répertoire courant
        logger.info("Tentative d'import direct...")
        from extract_repair.verify_extracts_with_llm import verify_extracts_with_llm, generate_report
        
        # Import depuis le répertoire parent
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from argumentiation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        from argumentiation_analysis.ui.extract_utils import load_extract_definitions_safely
        from argumentiation_analysis.core.llm_service import create_llm_service
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
    
    # Limiter le nombre d'extraits si l'option --limit est spécifiée
    if args.limit is not None and args.limit > 0:
        # Compter le nombre total d'extraits
        total_extracts = sum(len(source.get("extracts", [])) for source in extract_definitions)
        logger.info(f"Limitation du nombre d'extraits: {args.limit}/{total_extracts} extraits maximum.")
        
        # Limiter le nombre d'extraits par source
        limited_definitions = []
        extracts_count = 0
        
        for source in extract_definitions:
            extracts = source.get("extracts", [])
            if extracts_count + len(extracts) <= args.limit:
                # Ajouter toute la source
                limited_definitions.append(source)
                extracts_count += len(extracts)
            else:
                # Ajouter seulement une partie des extraits
                remaining = args.limit - extracts_count
                if remaining > 0:
                    limited_source = source.copy()
                    limited_source["extracts"] = extracts[:remaining]
                    limited_definitions.append(limited_source)
                    extracts_count += remaining
                break
        
        extract_definitions = limited_definitions
        logger.info(f"Nombre d'extraits limité à {extracts_count}.")
    
    # Créer le service LLM
    logger.info("Création du service LLM...")
    llm_service = create_llm_service()
    if not llm_service:
        logger.error("Impossible de créer le service LLM.")
        return
    logger.info(f"Service LLM créé: {type(llm_service).__name__}")
    
    # Vérifier tous les extraits avec le LLM
    logger.info("Vérification de tous les extraits avec le LLM...")
    results = await verify_extracts_with_llm(extract_definitions, llm_service)
    logger.info(f"Vérification terminée. {len(results)} résultats obtenus.")
    
    # Générer le rapport
    output_file = args.output
    logger.info(f"Génération du rapport dans {output_file}...")
    generate_report(results, output_file)
    logger.info(f"Rapport généré dans {output_file}")
    
    # Afficher un résumé des résultats
    valid_count = sum(1 for result in results if result.get("status") == "valid")
    invalid_count = sum(1 for result in results if result.get("status") == "invalid")
    error_count = sum(1 for result in results if result.get("status") == "error")
    
    # Calculer les scores moyens
    total_coherence = 0
    total_relevance = 0
    total_integrity = 0
    valid_count_for_avg = 0
    
    for result in results:
        if result.get("status") != "error":
            total_coherence += result.get("coherence", 0)
            total_relevance += result.get("relevance", 0)
            total_integrity += result.get("integrity", 0)
            valid_count_for_avg += 1
    
    avg_coherence = total_coherence / valid_count_for_avg if valid_count_for_avg > 0 else 0
    avg_relevance = total_relevance / valid_count_for_avg if valid_count_for_avg > 0 else 0
    avg_integrity = total_integrity / valid_count_for_avg if valid_count_for_avg > 0 else 0
    
    logger.info("Résumé des résultats:")
    logger.info(f"  - Extraits vérifiés: {len(results)}")
    logger.info(f"  - Extraits valides: {valid_count}")
    logger.info(f"  - Extraits invalides: {invalid_count}")
    logger.info(f"  - Erreurs: {error_count}")
    logger.info(f"  - Score moyen de cohérence: {avg_coherence:.2f}/5")
    logger.info(f"  - Score moyen de pertinence: {avg_relevance:.2f}/5")
    logger.info(f"  - Score moyen d'intégrité: {avg_integrity:.2f}/5")
    
    # Afficher un message de succès
    print(f"\n✅ Vérification des extraits terminée avec succès. Rapport généré dans {output_file}")
    print(f"Résumé: {valid_count} valides, {invalid_count} invalides, {error_count} erreurs")
    print(f"Scores moyens: Cohérence {avg_coherence:.2f}/5, Pertinence {avg_relevance:.2f}/5, Intégrité {avg_integrity:.2f}/5")

if __name__ == "__main__":
    asyncio.run(main())
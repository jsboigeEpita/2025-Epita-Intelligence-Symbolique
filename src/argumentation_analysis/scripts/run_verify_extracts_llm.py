#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution pour la vérification de la qualité des extraits avec un LLM.

Ce script utilise la logique de `argumentation_analysis.utils.extract_repair.verify_extracts_with_llm`
pour évaluer les extraits et générer un rapport.
"""

import argparse
import asyncio
import logging
from pathlib import Path
import os
import sys

# Ajouter le répertoire parent au chemin d'importation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from argumentation_analysis.utils.extract_repair.verify_extracts_with_llm import (
    verify_extracts_with_llm,
    generate_report as generate_llm_report, # Renommer pour éviter conflit si d'autres reports sont générés
    logger as verify_llm_logger
)
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON # Nécessaire pour load_extract_definitions_safely
from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely # Import direct
from argumentation_analysis.core.llm_service import create_llm_service # Import direct

# Configuration du logging pour ce script
logger = logging.getLogger("RunVerifyExtractsLLM")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
# Création d'un handler pour écrire les logs dans un fichier spécifique au script d'exécution
run_file_handler = logging.FileHandler("run_verify_extracts_llm.log")
run_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(run_file_handler)


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
                        help="Fichier d'entrée personnalisé (chemin complet vers extract_sources.json ou similaire)")
    parser.add_argument("--limit", "-l", type=int, default=None,
                        help="Limiter le nombre d'extraits à traiter")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        verify_llm_logger.setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers: # Mettre à jour tous les handlers
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")

    logger.info("Démarrage du script de vérification des extraits avec LLM...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    logger.info(f"Chemin du script: {os.path.abspath(__file__)}")

    # Utiliser le fichier d'entrée personnalisé si spécifié, sinon la configuration par défaut
    input_file_path_str = args.input if args.input else CONFIG_FILE
    logger.info(f"Fichier d'entrée: {input_file_path_str}")
    
    input_file_path = Path(input_file_path_str)
    fallback_file_path = Path(CONFIG_FILE_JSON) if Path(CONFIG_FILE_JSON).exists() else None


    # Vérifier que le fichier d'entrée existe
    if not input_file_path.exists() and not (fallback_file_path and fallback_file_path.exists()):
        logger.error(f"Le fichier d'entrée {input_file_path_str} (et son fallback {CONFIG_FILE_JSON} si applicable) n'existe pas.")
        return

    # Charger les définitions d'extraits
    logger.info(f"Chargement des définitions d'extraits depuis {input_file_path_str}...")
    try:
        # Utiliser le chemin du fichier d'entrée fourni ou le fichier de configuration par défaut
        extract_definitions_data, error_message = load_extract_definitions_safely(
            str(input_file_path), # S'assurer que c'est une string
            ENCRYPTION_KEY, 
            str(fallback_file_path) if fallback_file_path else None # S'assurer que c'est une string
        )
        if error_message:
            logger.error(f"Erreur lors du chargement des définitions d'extraits: {error_message}")
            return

        logger.info(f"{len(extract_definitions_data)} sources chargées.")

        # Afficher les premières sources pour vérification
        for i, source in enumerate(extract_definitions_data[:2]):
            logger.info(f"Source {i}: {source.get('source_name', 'Sans nom')}")
            logger.info(f"  Type: {source.get('source_type', 'Non spécifié')}")
            logger.info(f"  Extraits: {len(source.get('extracts', []))}")
    except Exception as e:
        logger.error(f"Exception lors du chargement des définitions d'extraits: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return

    # Filtrer les sources si l'option --hitler-only est activée
    if args.hitler_only:
        original_count = len(extract_definitions_data)
        extract_definitions_data = [
            source for source in extract_definitions_data
            if "hitler" in source.get("source_name", "").lower()
        ]
        logger.info(f"Filtrage des sources: {len(extract_definitions_data)}/{original_count} sources retenues (corpus Hitler).")

    # Limiter le nombre d'extraits si l'option --limit est spécifiée
    if args.limit is not None and args.limit > 0:
        total_extracts_count = sum(len(source.get("extracts", [])) for source in extract_definitions_data)
        logger.info(f"Limitation du nombre d'extraits: {args.limit}/{total_extracts_count} extraits maximum.")

        limited_definitions_list = []
        current_extracts_count = 0
        for source_item in extract_definitions_data:
            extracts_list = source_item.get("extracts", [])
            if current_extracts_count + len(extracts_list) <= args.limit:
                limited_definitions_list.append(source_item)
                current_extracts_count += len(extracts_list)
            else:
                remaining_slots = args.limit - current_extracts_count
                if remaining_slots > 0:
                    limited_source_item = source_item.copy()
                    limited_source_item["extracts"] = extracts_list[:remaining_slots]
                    limited_definitions_list.append(limited_source_item)
                    current_extracts_count += remaining_slots
                break
        extract_definitions_data = limited_definitions_list
        logger.info(f"Nombre d'extraits limité à {current_extracts_count}.")

    # Créer le service LLM
    logger.info("Création du service LLM...")
    try:
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM.")
            return
        logger.info(f"Service LLM créé: {type(llm_service).__name__}")
    except Exception as e:
        logger.error(f"Exception lors de la création du service LLM: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return

    # Vérifier tous les extraits avec le LLM
    logger.info("Vérification de tous les extraits avec le LLM...")
    try:
        results = await verify_extracts_with_llm(extract_definitions_data, llm_service)
        logger.info(f"Vérification terminée. {len(results)} résultats obtenus.")
    except Exception as e:
        logger.error(f"Exception lors de la vérification des extraits: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return

    # Générer le rapport
    report_output_file = args.output
    # S'assurer que le rapport est écrit dans le répertoire du script ou un sous-répertoire
    script_dir = Path(__file__).parent
    # report_path = script_dir / "reports" / report_output_file # Exemple avec sous-dossier
    report_path = script_dir / report_output_file # Dans le même dossier que le script
    
    logger.info(f"Génération du rapport dans {report_path.resolve()}...")
    try:
        generate_llm_report(results, str(report_path)) # S'assurer que c'est une string
        logger.info(f"Rapport généré dans {report_path.resolve()}")
    except Exception as e:
        logger.error(f"Exception lors de la génération du rapport: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return

    # Afficher un résumé des résultats
    final_valid_count = sum(1 for result in results if result.get("status") == "valid")
    final_invalid_count = sum(1 for result in results if result.get("status") == "invalid")
    final_error_count = sum(1 for result in results if result.get("status") == "error")

    final_total_coherence = 0
    final_total_relevance = 0
    final_total_integrity = 0
    final_valid_count_for_avg = 0

    for result in results:
        if result.get("status") != "error":
            final_total_coherence += result.get("coherence", 0)
            final_total_relevance += result.get("relevance", 0)
            final_total_integrity += result.get("integrity", 0)
            final_valid_count_for_avg += 1

    final_avg_coherence = final_total_coherence / final_valid_count_for_avg if final_valid_count_for_avg > 0 else 0
    final_avg_relevance = final_total_relevance / final_valid_count_for_avg if final_valid_count_for_avg > 0 else 0
    final_avg_integrity = final_total_integrity / final_valid_count_for_avg if final_valid_count_for_avg > 0 else 0

    logger.info("Résumé des résultats:")
    logger.info(f"  - Extraits vérifiés: {len(results)}")
    logger.info(f"  - Extraits valides: {final_valid_count}")
    logger.info(f"  - Extraits invalides: {final_invalid_count}")
    logger.info(f"  - Erreurs: {final_error_count}")
    logger.info(f"  - Score moyen de cohérence: {final_avg_coherence:.2f}/5")
    logger.info(f"  - Score moyen de pertinence: {final_avg_relevance:.2f}/5")
    logger.info(f"  - Score moyen d'intégrité: {final_avg_integrity:.2f}/5")

    if final_invalid_count > 0:
        logger.info("Extraits invalides:")
        for result in results:
            if result.get("status") == "invalid":
                logger.info(f"  - {result.get('source_name')} - {result.get('extract_name')}: {result.get('comments')}")

    print(f"\n✅ Vérification des extraits terminée avec succès. Rapport généré dans {report_path.resolve()}")
    print(f"Résumé: {final_valid_count} valides, {final_invalid_count} invalides, {final_error_count} erreurs")
    print(f"Scores moyens: Cohérence {final_avg_coherence:.2f}/5, Pertinence {final_avg_relevance:.2f}/5, Intégrité {final_avg_integrity:.2f}/5")

if __name__ == "__main__":
    asyncio.run(main())
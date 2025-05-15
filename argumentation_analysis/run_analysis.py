#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer l'analyse argumentative

Ce script permet de lancer facilement l'analyse argumentative depuis la racine du projet.
Il offre plusieurs options pour fournir le texte à analyser (fichier, texte direct, etc.)
et configure automatiquement l'environnement nécessaire.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

def setup_logging():
    """Configuration du logging pour l'analyse"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Réduire la verbosité de certaines bibliothèques
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("semantic_kernel.connectors.ai").setLevel(logging.WARNING)
    
    # Garder INFO pour l'orchestration et les agents
    logging.getLogger("Orchestration").setLevel(logging.INFO)
    logging.getLogger("semantic_kernel.agents").setLevel(logging.INFO)
    
    logging.info("Logging configuré pour l'analyse argumentative.")

async def run_analysis(text_content):
    """Exécute l'analyse argumentative sur le texte fourni"""
    # 1. Chargement de l'environnement (.env)
    from dotenv import load_dotenv, find_dotenv
    loaded = load_dotenv(find_dotenv(), override=True)
    print(f".env chargé: {loaded}")

    # 2. Initialisation de la JVM
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    logging.info("Initialisation de la JVM...")
    jvm_ready_status = initialize_jvm(lib_dir_path=LIBS_DIR)
    
    if not jvm_ready_status:
        logging.warning("⚠️ JVM n'a pas pu être initialisée. L'agent PropositionalLogicAgent ne fonctionnera pas.")

    # 3. Création du Service LLM
    from argumentation_analysis.core.llm_service import create_llm_service
    logging.info("Création du service LLM...")
    try:
        llm_service = create_llm_service()
        logging.info(f"✅ Service LLM créé avec succès (ID: {llm_service.service_id}).")
    except Exception as e:
        logging.critical(f"❌ Échec de la création du service LLM: {e}", exc_info=True)
        print(f"❌ ERREUR: Impossible de créer le service LLM. Vérifiez la configuration .env.")
        return

    # 4. Exécution de l'analyse
    if text_content and llm_service:
        logging.info(f"Lancement de l'analyse sur un texte de {len(text_content)} caractères...")
        try:
            from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
            await run_analysis_conversation(
                texte_a_analyser=text_content,
                llm_service=llm_service
            )
            logging.info("🏁 Analyse terminée avec succès.")
        except Exception as e:
            logging.error(f"❌ Erreur lors de l'analyse: {e}", exc_info=True)
    else:
        logging.error("Analyse impossible: texte vide ou service LLM non disponible.")

async def main():
    """Fonction principale du script"""
    parser = argparse.ArgumentParser(description="Analyse argumentative de texte")
    
    # Groupe mutuellement exclusif pour les sources de texte
    text_source = parser.add_mutually_exclusive_group(required=True)
    text_source.add_argument("--file", "-f", type=str, help="Chemin vers un fichier texte à analyser")
    text_source.add_argument("--text", "-t", type=str, help="Texte à analyser (directement en argument)")
    text_source.add_argument("--ui", "-u", action="store_true", help="Utiliser l'interface utilisateur pour sélectionner le texte")
    
    # Options supplémentaires
    parser.add_argument("--verbose", "-v", action="store_true", help="Afficher les logs détaillés")
    
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Récupération du texte selon la source choisie
    text_content = None
    
    if args.file:
        try:
            file_path = Path(args.file)
            if not file_path.exists():
                logging.error(f"Le fichier {file_path} n'existe pas.")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            logging.info(f"Texte chargé depuis {file_path} ({len(text_content)} caractères)")
        except Exception as e:
            logging.error(f"Erreur lors de la lecture du fichier: {e}")
            return
    
    elif args.text:
        text_content = args.text
        logging.info(f"Utilisation du texte fourni en argument ({len(text_content)} caractères)")
    
    elif args.ui:
        # Importer les dépendances nécessaires
        from argumentation_analysis.ui.app import configure_analysis_task
        from argumentation_analysis.paths import LIBS_DIR
        
        try:
            logging.info("Lancement de l'interface utilisateur...")
            text_content = configure_analysis_task()
            if not text_content:
                logging.warning("Aucun texte n'a été sélectionné via l'interface.")
                return
            logging.info(f"Texte sélectionné via l'interface ({len(text_content)} caractères)")
        except Exception as e:
            logging.error(f"Erreur lors de l'utilisation de l'interface: {e}", exc_info=True)
            return
    
    # Exécution de l'analyse
    await run_analysis(text_content)

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer l'orchestration des agents d'analyse argumentative

Ce script permet de lancer facilement l'orchestration des agents d'analyse argumentative
depuis la racine du projet. Il offre plusieurs options pour configurer l'orchestration
et permet d'exécuter l'analyse de manière indépendante.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Any, Optional, List

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

def setup_logging(verbose: bool = False) -> None:
    """Configuration du logging pour l'orchestration.

    :param verbose: Si True, configure le logging au niveau DEBUG.
                    Sinon, configure au niveau INFO.
    :type verbose: bool
    :return: None
    :rtype: None
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
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
    logging.getLogger("Orchestration").setLevel(level)
    # logging.getLogger("semantic_kernel.agents").setLevel(level) # Module inexistant
    
    logging.info("Logging configuré pour l'orchestration.")

async def setup_environment() -> Any:
    """Initialise l'environnement nécessaire pour l'orchestration.

    Charge les variables d'environnement, initialise la JVM et crée le service LLM.

    :return: L'instance du service LLM si la création est réussie, sinon None.
    :rtype: Any
    """
    # 1. Chargement de l'environnement (.env) est maintenant géré automatiquement
    # par l'import du module `settings`. L'import de `jvm_setup` ou `llm_service`
    # déclenchera le chargement de la configuration.
    logging.info("Initialisation de l'environnement (chargement des settings implicite)...")

    # 2. Initialisation de la JVM
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.paths import LIBS_DIR
    logging.info("Initialisation de la JVM...")
    jvm_ready_status = initialize_jvm(lib_dir_path=LIBS_DIR)
    
    if not jvm_ready_status:
        logging.warning("⚠️ JVM n'a pas pu être initialisée. L'agent PropositionalLogicAgent ne fonctionnera pas.")

    # 3. Création du Service LLM
    from argumentation_analysis.core.llm_service import create_llm_service
    logging.info("Création du service LLM...")
    try:
        llm_service = create_llm_service()
        logging.info(f"[OK] Service LLM créé avec succès (ID: {llm_service.service_id}).")
        return llm_service
    except Exception as e:
        logging.critical(f"❌ Échec de la création du service LLM: {e}", exc_info=True)
        print(f"❌ ERREUR: Impossible de créer le service LLM. Vérifiez la configuration .env.")
        return None

async def run_orchestration(text_content: str, llm_service: Any, agents: Optional[List[str]] = None, verbose: bool = False) -> None:
    """Exécute l'orchestration des agents sur le texte fourni.

    :param text_content: Le contenu textuel à analyser.
    :type text_content: str
    :param llm_service: L'instance du service LLM initialisée.
    :type llm_service: Any
    :param agents: Liste optionnelle des noms des agents à utiliser.
                   Actuellement non utilisé directement par `run_analysis_conversation`.
    :type agents: Optional[List[str]]
    :param verbose: Indicateur de verbosité (non utilisé directement ici, mais pourrait l'être).
    :type verbose: bool
    :return: None
    :rtype: None
    """
    if not text_content or not llm_service:
        logging.error("Orchestration impossible: texte vide ou service LLM non disponible.")
        return
    
    logging.info(f"Lancement de l'orchestration sur un texte de {len(text_content)} caractères...")
    
    try:
        from argumentation_analysis.orchestration.analysis_runner import run_analysis
        
        # Note: La fonction run_analysis gère l'orchestration complète.
        
        # Exécution de l'analyse
        await run_analysis(
            text_content=text_content,
            llm_service=llm_service
        )
        
        logging.info("✅ Orchestration terminée avec succès.")
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'orchestration: {e}", exc_info=True)

async def main():
    """Fonction principale du script"""
    parser = argparse.ArgumentParser(description="Orchestration des agents d'analyse argumentative")
    
    # Groupe mutuellement exclusif pour les sources de texte
    text_source = parser.add_mutually_exclusive_group(required=True)
    text_source.add_argument("--file", "-f", type=str, help="Chemin vers un fichier texte à analyser")
    text_source.add_argument("--text", "-t", type=str, help="Texte à analyser (directement en argument)")
    text_source.add_argument("--ui", "-u", action="store_true", help="Utiliser l'interface utilisateur pour sélectionner le texte")
    
    # Options pour les agents
    parser.add_argument("--agents", "-a", type=str, nargs="+", 
                        choices=["pm", "informal", "pl", "extract"],
                        help="Liste des agents à utiliser (par défaut: tous)")
    
    # Options supplémentaires
    parser.add_argument("--verbose", "-v", action="store_true", help="Afficher les logs détaillés")
    
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging(args.verbose)
    
    # Initialisation de l'environnement
    llm_service = await setup_environment()
    if not llm_service:
        return
    
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
    
    # Exécution de l'orchestration
    await run_orchestration(text_content, llm_service, args.agents, args.verbose)

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT D'EXÉCUTION SIMPLIFIÉ POUR LA DÉMONSTRATION SHERLOCK-WATSON (CLUEDO)
=========================================================================

Ce script sert de point d'entrée unique et simplifié pour lancer 
une démonstration du système d'enquête Cluedo.

Il utilise CluedoExtendedOrchestrator pour gérer la logique de l'enquête.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Assurer que la racine du projet est dans sys.path pour les imports absolus
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Import de l'orchestrateur principal
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from semantic_kernel import Kernel # Nécessaire pour l'initialisation de l'orchestrateur

# Configuration du logging simple pour la démo
def setup_demo_logging():
    """Configure un logging basique pour la sortie console."""
    # S'assure de ne configurer qu'une fois
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    # Appliquer le niveau à tous les handlers existants
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.INFO)
    return logging.getLogger("DemoCluedo")

logger = setup_demo_logging()

async def run_demo():
    """
    Lance une session de démonstration du jeu Cluedo.
    """
    logger.info("🎲 Initialisation de la démonstration Cluedo...")

    # Initialisation minimale du Kernel Semantic Kernel (peut nécessiter des variables d'environnement)
    # Pour une démo, on pourrait utiliser un mock ou une configuration minimale.
    # Ici, on suppose une initialisation basique.
    try:
        kernel = Kernel()
        # Potentiellement, ajouter un service LLM si l'orchestrateur en dépend directement
        # pour son initialisation ou son fonctionnement de base non couvert par les mocks.
        # Exemple (à adapter selon les besoins réels de CluedoExtendedOrchestrator):
        # from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        # api_key = os.getenv("OPENAI_API_KEY")
        # model_id = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")
        # if api_key and model_id:
        #     kernel.add_service(OpenAIChatCompletion(service_id="chat_completion", api_key=api_key, ai_model_id=model_id))
        # else:
        #     logger.warning("Variables d'environnement OPENAI_API_KEY ou OPENAI_CHAT_MODEL_ID non définies.")
        #     logger.warning("L'orchestrateur pourrait ne pas fonctionner comme attendu sans service LLM configuré.")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation du Kernel Semantic Kernel: {e}")
        logger.error("Veuillez vérifier votre configuration et vos variables d'environnement.")
        return

    try:
        # Instanciation de l'orchestrateur
        # Le constructeur de CluedoExtendedOrchestrator pourrait nécessiter le kernel
        # ou d'autres configurations. Adaptez selon sa définition.
        orchestrator = CluedoExtendedOrchestrator(kernel=kernel) # ou CluedoExtendedOrchestrator() si kernel n'est pas requis au init

        logger.info("🕵️‍♂️ Lancement de l'enquête Cluedo...")
        
        # L'appel à la méthode principale de l'orchestrateur.
        # Remplacez 'start_investigation' par la méthode réelle.
        # Elle pourrait prendre des paramètres (ex: description du cas).
        # result = await orchestrator.start_investigation("Un meurtre a été commis au manoir Tudor.")
        
        # Placeholder pour la logique d'appel - à remplacer par l'appel réel
        # à la méthode de CluedoExtendedOrchestrator qui lance le jeu/l'enquête.
        # Par exemple, si CluedoExtendedOrchestrator a une méthode `async def play_game()`:
        game_summary = await orchestrator.run_full_game_simulation_and_report(
            human_player_name="Joueur Humain Démo",
            human_player_persona="Un détective amateur perspicace",
            log_level="INFO" # ou "DEBUG" pour plus de détails
        )

        logger.info("\n🏁 Enquête Terminée !")
        logger.info("Résumé de la partie :")
        
        # Affichage structuré du résultat (à adapter selon le retour de l'orchestrateur)
        if game_summary:
            logger.info(f"  Statut: {game_summary.get('status', 'N/A')}")
            solution_found = game_summary.get('solution_found', False)
            logger.info(f"  Solution trouvée: {'Oui' if solution_found else 'Non'}")
            if solution_found:
                logger.info(f"  Coupable: {game_summary.get('final_solution', {}).get('suspect', 'N/A')}")
                logger.info(f"  Arme: {game_summary.get('final_solution', {}).get('weapon', 'N/A')}")
                logger.info(f"  Lieu: {game_summary.get('final_solution', {}).get('room', 'N/A')}")
            logger.info(f"  Nombre de tours: {game_summary.get('total_turns', 'N/A')}")
            if game_summary.get('error_message'):
                logger.error(f"  Erreur: {game_summary.get('error_message')}")
        else:
            logger.warning("Aucun résumé de partie n'a été retourné par l'orchestrateur.")

    except Exception as e:
        logger.error(f"❌ Une erreur est survenue durant l'exécution de la démo: {e}", exc_info=True)

async def main():
    await run_demo()

if __name__ == "__main__":
    # Activation de l'environnement
    try:
        from project_core.core_from_scripts.auto_env import ensure_env
        logger.info("Activation de l'environnement...")
        if not ensure_env(silent=False): # Mettre silent=True pour moins de verbosité
            logger.error("ERREUR: Impossible d'activer l'environnement. Le script pourrait échouer.")
            # Décommenter pour sortir si l'environnement est critique
            # sys.exit(1)
    except ImportError:
        logger.error("ERREUR: Impossible d'importer 'ensure_env' depuis 'project_core.core_from_scripts.auto_env'.")
        logger.error("Veuillez vérifier que le PYTHONPATH est correctement configuré ou que le script est lancé depuis la racine du projet.")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Exécution de la démo interrompue par l'utilisateur.")
    except Exception as general_error:
        logger.critical(f"❌ Une erreur non gérée et critique est survenue: {general_error}", exc_info=True)
        sys.exit(1)
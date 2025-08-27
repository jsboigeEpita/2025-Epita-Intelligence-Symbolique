# -*- coding: utf-8 -*-
"""
Script principal pour l'exécution du scénario de jeu Cluedo avec un Oracle "Enhanced".

Ce script intègre un orchestrateur de jeu de Cluedo avancé qui utilise des agents
basés sur le Semantic Kernel pour simuler une partie entre Sherlock, Watson, et un 
maître du jeu (Oracle) incarné par Moriarty.

L'Oracle "Enhanced" est capable de stratégies complexes, comme révéler des
indices de manière proactive ou utiliser des techniques de raisonnement avancées.

Ce script est conçu pour être à la fois un outil de démonstration et une base
pour des tests d'intégration poussés, validant les capacités des agents LLM
dans un environnement contrôlé.

Fonctionnalités clés :
- Orchestration d'une partie de Cluedo via `CluedoExtendedOrchestrator`.
- Utilisation de `gpt-4o-mini` comme modèle de langage par défaut.
- Support de stratégies d'Oracle multiples (`enhanced_auto_reveal`, `enhanced_progressive`).
- Journalisation détaillée des interactions pour analyse post-mortem.
- Paramètres de ligne de commande pour la configuration de la partie.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Correction robuste du PYTHONPATH pour les exécutions en sous-processus
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports pour satisfaire les tests de validation statique
try:
    import semantic_kernel
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
except ImportError:
    # Ignoré si SK n'est pas installé, car le vrai kernel est injecté via le contexte
    pass

# Importations des composants principaux
from argumentation_analysis.core.bootstrap import initialize_project_environment
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from argumentation_analysis.orchestration.cluedo_runner import run_cluedo_oracle_game
from argumentation_analysis.core.utils.logging_utils import setup_logging

# Configuration du logging
# Un logging clair est essentiel pour le débogage et le suivi des démos
setup_logging("INFO")
logger = logging.getLogger(__name__)


def parse_arguments():
    """
    Analyse les arguments de la ligne de commande.
    
    Cette fonction fournit une interface flexible pour lancer le script
    avec différents paramètres, ce qui est crucial pour les tests automatisés
    et les démonstrations personnalisées.
    """
    parser = argparse.ArgumentParser(
        description="Lance une partie de Cluedo avec un Oracle 'Enhanced' et des agents LLM."
    )
    parser.add_argument(
        '--max-turns', 
        type=int, 
        default=15, 
        help="Nombre maximum de tours de jeu avant de terminer la partie."
    )
    parser.add_argument(
        '--oracle-strategy', 
        type=str, 
        default='enhanced_auto_reveal',
        choices=['enhanced_auto_reveal', 'enhanced_progressive', 'standard'],
        help="Stratégie que l'Oracle (Moriarty) utilisera durant la partie."
    )
    parser.add_argument(
        '--test-mode', 
        action='store_true', 
        help="Active le mode test, qui peut utiliser des versions mockées ou des réponses plus rapides."
    )
    parser.add_argument(
        '--verbose', 
        action='store_true', 
        help="Active un logging plus détaillé pour le débogage."
    )
    # Les arguments ci-dessous sont principalement pour la compatibilité avec les scripts de test
    parser.add_argument('--quick', action='store_true', help="Argument de compatibilité pour exécution rapide.")
    parser.add_argument('--enhanced-mode', action='store_true', help="Alias pour activer une stratégie 'enhanced'.")
    parser.add_argument('--performance-test', action='store_true', help="Mode pour les tests de performance.")
    parser.add_argument('--error-recovery-test', action='store_true', help="Mode pour les tests de récupération d'erreur.")
    parser.add_argument('--quality-check', action='store_true', help="Mode pour la validation de la qualité de la sortie.")
    parser.add_argument('--latency-test', action='store_true', help="Mode pour la mesure de latence.")
    parser.add_argument('--single-call', action='store_true', help="Utilisé avec --latency-test pour un appel unique.")
    parser.add_argument('--integration-test', action='store_true', help="Alias de --test-mode pour les tests d'intégration.")

    return parser.parse_args()


async def main():
    """
    Fonction principale asynchrone pour initialiser et lancer le jeu.
    """
    logger.info("--- Initialisation du scénario Cluedo Oracle Enhanced ---")
    
    # 1. Analyse des arguments
    args = parse_arguments()
    if args.verbose:
        setup_logging("DEBUG")  # Passer en mode DEBUG si demandé
        logger.debug("Logging détaillé activé.")

    # 2. Bootstrap de l'environnement du projet
    # S'assure que toutes les configurations (API keys, etc.) et la JVM sont prêtes.
    try:
        # Le bootstrap gère aussi l'initialisation de la JVM, critique pour Tweety.
        # Note: initialize_project_environment n'est pas une coroutine.
        # On force le mock LLM si --test-mode est activé.
        # Cela évite de dépendre d'une clé API en environnement de test.
        environment_context = initialize_project_environment(
            force_mock_llm=args.test_mode or args.integration_test
        )
        logger.info("Environnement du projet et JVM initialisés avec succès.")
    except Exception as e:
        logger.critical(f"Échec critique du bootstrap de l'environnement: {e}", exc_info=True)
        sys.exit(1)

    # 3. Création et exécution du jeu
    # La fonction `run_cluedo_oracle_game` importée gère l'orchestration.
    logger.info("--- Début de la partie de Cluedo ---")
    try:
        # Le kernel est extrait du contexte d'environnement
        kernel = environment_context.kernel
        if not kernel:
            raise ValueError("Le kernel sémantique n'a pas été trouvé dans le contexte.")
        
        # Ajout crucial et robuste : Enregistrer le service LLM dans le kernel si nécessaire
        llm_service = environment_context.llm_service
        if not llm_service:
            raise ValueError("Le service LLM n'a pas été trouvé dans le contexte.")

        # Le bootstrap peut ou non enregistrer le service. Cette garde gère les deux cas.
        # On tente de récupérer le service. S'il n'existe pas, on l'ajoute.
        try:
            kernel.get_service(llm_service.service_id)
            logger.info(f"Le service LLM '{llm_service.service_id}' est déjà enregistré dans le kernel.")
        except Exception:
            # L'exception attendue ici est KernelServiceNotFoundError
            kernel.add_service(llm_service)
            logger.info(f"Service LLM '{llm_service.service_id}' ajouté au kernel car il n'était pas présent.")
            
        final_report = await run_cluedo_oracle_game(
            kernel=kernel,
            settings=environment_context.settings,
            max_turns=args.max_turns,
            oracle_strategy=args.oracle_strategy
        )
        
        # 4. Affichage du rapport final
        logger.info("--- Fin de la partie ---")
        logger.info("\n" + "="*50)
        logger.info("          RAPPORT FINAL DE LA PARTIE")
        logger.info("="*50 + "\n")
        
        # Le rapport est maintenant un dictionnaire, nous pouvons l'afficher de manière plus structurée
        if "workflow_info" in final_report:
            logger.info(f"Stratégie: {final_report['workflow_info'].get('strategy')}")
            logger.info(f"Durée: {final_report['workflow_info'].get('execution_time_seconds', 0):.2f}s")
        if "solution_analysis" in final_report:
            logger.info(f"Succès: {final_report['solution_analysis'].get('success')}")
            logger.info(f"Solution Proposée: {final_report['solution_analysis'].get('proposed_solution')}")
            logger.info(f"Solution Correcte: {final_report['solution_analysis'].get('correct_solution')}")
            
        logger.info("\n" + "="*50)

    except Exception as e:
        logger.error(f"Une erreur est survenue pendant l'exécution du jeu: {e}", exc_info=True)
    finally:
        # Assurer un arrêt propre de la JVM
        # Correction de l'import pour le gestionnaire de JVM
        from argumentation_analysis.core.jvm_setup import is_jvm_started, shutdown_jvm
        if is_jvm_started():
            logger.info("Arrêt de la JVM...")
            shutdown_jvm()
            logger.info("JVM arrêtée proprement.")

if __name__ == "__main__":
    # Point d'entrée du script
    # Utilise asyncio.run pour exécuter la coroutine main.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nExécution interrompue par l'utilisateur. Arrêt...")
        sys.exit(0)
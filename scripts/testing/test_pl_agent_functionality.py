#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test dédié pour PropositionalLogicAgent.
"""
import asyncio
import logging
import os
import sys

# Ajout du répertoire racine au chemin Python
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from semantic_kernel import Kernel
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.paths import LIBS_DIR
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.core.llm_service import create_llm_service # Assumant que cette fonction existe et est configurée

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestPLAgentFunctionality")

async def main():
    logger.info("--- Début du test de PropositionalLogicAgent ---")

    # 1. Initialiser la JVM
    logger.info("=== Étape 1: Initialisation de la JVM ===")
    jvm_ready = False
    try:
        jvm_ready = initialize_jvm(lib_dir_path=str(LIBS_DIR))
        if not jvm_ready:
            logger.error("Échec de initialize_jvm. La fonction a retourné False.")
        else:
            logger.info("initialize_jvm a retourné True. Vérification de l'état de la JVM avec JPype...")
            import jpype
            if jpype.isJVMStarted():
                logger.info(f"JPype confirme: JVM démarrée. Version: {jpype.getJVMVersion()}")
                # Essayer de charger une classe simple pour confirmer le classpath
                try:
                    PlBeliefSet_class = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
                    logger.info(f"Classe Tweety (PlBeliefSet) chargée avec succès: {PlBeliefSet_class}")
                    logger.info("JVM et Classpath semblent OK.")
                except Exception as e_load_class:
                    logger.error(f"Erreur lors du chargement d'une classe Tweety (problème de classpath probable): {e_load_class}", exc_info=True)
                    jvm_ready = False # Marquer comme non prêt si le classpath est mauvais
            else:
                logger.error("JPype confirme: JVM NON démarrée, même après initialize_jvm.")
                jvm_ready = False
    except Exception as e_jvm_init:
        logger.error(f"Exception majeure lors de l'initialisation de la JVM: {e_jvm_init}", exc_info=True)
        jvm_ready = False

    if not jvm_ready:
        logger.critical("Arrêt du test car la JVM n'a pas pu être initialisée correctement.")
        return
    logger.info("=== JVM initialisée avec succès. ===")

    # 2. Créer une instance de llm_service
    logger.info("=== Étape 2: Création du service LLM ===")
    llm_service = None
    try:
        # Assurez-vous que les variables d'environnement pour le service LLM sont configurées
        # (par exemple, OPENAI_API_KEY, OPENAI_ORG_ID ou Azure équivalents)
        llm_service = create_llm_service()
        if llm_service is None or not hasattr(llm_service, 'service_id'):
            logger.error("Impossible de créer le service LLM. create_llm_service() a retourné None ou un objet invalide. Vérifiez la configuration et les variables d'environnement.")
            return
        logger.info(f"Service LLM créé avec ID: {llm_service.service_id}")
    except Exception as e_llm_service:
        logger.error(f"Erreur lors de la création du service LLM: {e_llm_service}", exc_info=True)
        return
    logger.info("=== Service LLM créé avec succès. ===")

    # 3. Créer une instance de Kernel
    logger.info("=== Étape 3: Création du Kernel Semantic Kernel ===")
    kernel = Kernel()
    try:
        kernel.add_service(llm_service)
        logger.info("Service LLM ajouté au Kernel.")
    except Exception as e_kernel_add_service:
        logger.error(f"Erreur lors de l'ajout du service LLM au Kernel: {e_kernel_add_service}", exc_info=True)
        return
    logger.info("=== Kernel Semantic Kernel créé et configuré. ===")

    # 4. Instancier PropositionalLogicAgent
    logger.info("=== Étape 4: Instanciation et configuration de PropositionalLogicAgent ===")
    pl_agent = None
    try:
        pl_agent = PropositionalLogicAgent(kernel=kernel)
        pl_agent.setup_agent_components(llm_service_id=llm_service.service_id)
        logger.info(f"Agent {pl_agent.name} instancié et configuré.")
    except Exception as e_pl_agent_setup:
        logger.error(f"Erreur lors de l'instanciation ou de la configuration de PropositionalLogicAgent: {e_pl_agent_setup}", exc_info=True)
        return

    if not pl_agent or not pl_agent._tweety_bridge or not pl_agent._tweety_bridge.is_jvm_ready():
        logger.error(f"La JVM n'est pas prête pour TweetyBridge dans {pl_agent.name if pl_agent else 'N/A'} après setup. Vérifiez les logs de TweetyBridge et l'initialisation JVM.")
        return
    logger.info("=== PropositionalLogicAgent instancié et TweetyBridge prêt. ===")

    # Texte d'exemple pour l'analyse
    sample_text = "If it is raining, then the ground is wet. It is raining. Therefore, the ground is wet."
    logger.info(f"Texte d'exemple pour l'analyse : '{sample_text}'")

    # 5. Tester text_to_belief_set
    logger.info("=== Étape 5: Test de text_to_belief_set ===")
    belief_set_obj = None
    status_msg = ""
    try:
        belief_set_obj, status_msg = await pl_agent.text_to_belief_set(sample_text)
    except Exception as e_text_to_bs:
        logger.error(f"Exception lors de l'appel à pl_agent.text_to_belief_set: {e_text_to_bs}", exc_info=True)
        status_msg = f"Exception: {e_text_to_bs}"

    if belief_set_obj:
        logger.info(f"Conversion en BeliefSet réussie: {status_msg}")
        logger.info(f"Contenu du BeliefSet:\n{belief_set_obj.content}")

        # 6. Tester execute_query
        logger.info("=== Étape 6: Test de execute_query ===")
        # Tweety syntax: ! (not), || (or), && (and), => (implies), <=> (iff)
        query1 = "raining => wet_ground" # Devrait être accepté
        query2 = "wet_ground => raining" # Ne devrait pas être accepté
        query3 = "dry_ground"          # Devrait être rejeté
        query4 = "raining"             # Devrait être accepté

        queries_to_test = [query1, query2, query3, query4]
        results_summary = []

        for q_idx, q_str in enumerate(queries_to_test):
            logger.info(f"  Exécution de la requête {q_idx + 1}: '{q_str}'")
            parsed_result_bool = None
            raw_output_str = "Erreur non capturée"
            try:
                parsed_result_bool, raw_output_str = pl_agent.execute_query(belief_set=belief_set_obj, query=q_str)
                logger.info(f"    Résultat pour '{q_str}': {parsed_result_bool} (Output brut de Tweety: '{raw_output_str}')")
                results_summary.append(f"Query: '{q_str}', Result: {parsed_result_bool}, Raw: '{raw_output_str}'")
            except Exception as e_exec_query:
                logger.error(f"    Exception lors de l'exécution de la requête '{q_str}': {e_exec_query}", exc_info=True)
                results_summary.append(f"Query: '{q_str}', Result: EXCEPTION, Raw: '{e_exec_query}'")
        
        logger.info("Résumé des résultats des requêtes:")
        for summary_line in results_summary:
            logger.info(f"  - {summary_line}")
        logger.info("=== Tests de requêtes terminés. ===")
        
        # Optionnel: Tester interpret_results
        # logger.info("Test de interpret_results...")
        # interpretation = await pl_agent.interpret_results(sample_text, belief_set_obj, queries_to_test, results_summary) # Adapter 'results'
        # logger.info(f"Interprétation des résultats:\n{interpretation}")

    else:
        logger.error(f"Échec de la conversion en BeliefSet: {status_msg}")
    logger.info("=== Fin du test de PropositionalLogicAgent ---")

if __name__ == "__main__":
    # Log de démarrage immédiat pour vérifier si le script est atteint
    logging.getLogger("TestPLAgentFunctionality_Startup").info("Script test_pl_agent_functionality.py démarré (dans __main__)")
    asyncio.run(main())
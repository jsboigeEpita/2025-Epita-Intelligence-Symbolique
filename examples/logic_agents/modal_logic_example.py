#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation de l'agent de logique modale.

Cet exemple montre comment:
1. Initialiser un agent de logique modale
2. Convertir un texte en ensemble de croyances
3. Générer des requêtes pertinentes
4. Exécuter des requêtes sur l'ensemble de croyances
5. Interpréter les résultats

Prérequis:
- Semantic Kernel installé
- TweetyProject configuré
- JPype initialisé
"""

import logging
import sys
from typing import List, Tuple, Optional

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet, ModalBeliefSet

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ModalLogicExample")

def initialize_kernel() -> Tuple[Kernel, any]:
    """
    Initialise le kernel Semantic Kernel et le service LLM.
    
    Returns:
        Tuple contenant le kernel et le service LLM
    """
    logger.info("Initialisation du kernel et du service LLM...")
    
    # Créer un kernel Semantic Kernel
    kernel = Kernel()
    
    # Configurer le service LLM (OpenAI dans cet exemple)
    # Remplacez par vos propres clés API
    api_key = "votre_clé_api_openai"
    org_id = "votre_org_id_openai"
    
    # Ajouter le service LLM au kernel
    llm_service = kernel.add_service(
        OpenAIChatCompletion(
            service_id="gpt-4",
            ai_model_id="gpt-4",
            api_key=api_key,
            org_id=org_id
        )
    )
    
    logger.info("Kernel et service LLM initialisés avec succès")
    return kernel, llm_service

def create_modal_logic_agent(kernel: Kernel, llm_service: any) -> ModalLogicAgent:
    """
    Crée un agent de logique modale.
    
    Args:
        kernel: Le kernel Semantic Kernel
        llm_service: Le service LLM
        
    Returns:
        Un agent de logique modale
    """
    logger.info("Création de l'agent de logique modale...")
    
    # Utiliser la factory pour créer l'agent
    agent = LogicAgentFactory.create_agent("modal", kernel, llm_service)
    
    if agent is None:
        raise RuntimeError("Échec de la création de l'agent de logique modale")
    
    logger.info("Agent de logique modale créé avec succès")
    return agent

def process_necessity_possibility_example(agent: ModalLogicAgent) -> None:
    """
    Traite un exemple de nécessité et possibilité.
    
    Args:
        agent: L'agent de logique modale
    """
    logger.info("Exemple de nécessité et possibilité")
    
    # Texte à analyser
    text = """
    Si une proposition est nécessairement vraie, alors elle est vraie.
    Si une proposition est vraie, alors elle est possiblement vraie.
    La somme des angles d'un triangle est nécessairement égale à 180 degrés.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "<>(somme_angles_triangle_180)"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
    
    # Exécuter une autre requête
    query2 = "somme_angles_triangle_180"
    result2, result_msg2 = agent.execute_query(belief_set, query2)
    logger.info(f"Requête: {query2} -> Résultat: {result2} ({result_msg2})")
    
    # Générer des requêtes pertinentes
    queries = agent.generate_queries(text, belief_set)
    logger.info(f"Requêtes générées: {queries}")
    
    # Exécuter les requêtes générées
    results = []
    for query in queries:
        result, result_msg = agent.execute_query(belief_set, query)
        logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
        results.append(result_msg)
    
    # Interpréter les résultats
    interpretation = agent.interpret_results(text, belief_set, queries, results)
    logger.info(f"Interprétation: {interpretation}")

def process_epistemic_example(agent: ModalLogicAgent) -> None:
    """
    Traite un exemple de raisonnement épistémique.
    
    Args:
        agent: L'agent de logique modale
    """
    logger.info("Exemple de raisonnement épistémique")
    
    # Texte à analyser
    text = """
    Alice sait que si elle réussit son examen, elle obtiendra son diplôme.
    Alice sait qu'elle a réussi son examen.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "K(alice, obtention_diplome)"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")

def process_deontic_example(agent: ModalLogicAgent) -> None:
    """
    Traite un exemple de raisonnement déontique.
    
    Args:
        agent: L'agent de logique modale
    """
    logger.info("Exemple de raisonnement déontique")
    
    # Texte à analyser
    text = """
    Il est obligatoire de respecter la loi.
    Si on respecte la loi, alors il est permis de circuler librement.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "!circuler_librement => !respecter_loi"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
    
    # Exécuter une autre requête
    query2 = "O(respecter_loi) => P(circuler_librement)"
    result2, result_msg2 = agent.execute_query(belief_set, query2)
    logger.info(f"Requête: {query2} -> Résultat: {result2} ({result_msg2})")

def process_complex_example(agent: ModalLogicAgent) -> None:
    """
    Traite un exemple plus complexe avec plusieurs modalités.
    
    Args:
        agent: L'agent de logique modale
    """
    logger.info("Exemple complexe avec plusieurs modalités")
    
    # Texte à analyser
    text = """
    Si une action est obligatoire, alors il est nécessaire qu'elle soit permise.
    Il est possible que sauver une vie soit obligatoire.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "<>([](P(sauver_vie)))"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
    
    # Exécuter une autre requête
    query2 = "O(sauver_vie) => [](P(sauver_vie))"
    result2, result_msg2 = agent.execute_query(belief_set, query2)
    logger.info(f"Requête: {query2} -> Résultat: {result2} ({result_msg2})")
    
    # Générer des requêtes pertinentes
    queries = agent.generate_queries(text, belief_set)
    logger.info(f"Requêtes générées: {queries}")
    
    # Exécuter les requêtes générées
    results = []
    for query in queries:
        result, result_msg = agent.execute_query(belief_set, query)
        logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
        results.append(result_msg)
    
    # Interpréter les résultats
    interpretation = agent.interpret_results(text, belief_set, queries, results)
    logger.info(f"Interprétation: {interpretation}")

def main():
    """
    Fonction principale.
    """
    try:
        # Initialiser le kernel et le service LLM
        kernel, llm_service = initialize_kernel()
        
        # Créer l'agent de logique modale
        agent = create_modal_logic_agent(kernel, llm_service)
        
        # Traiter les exemples
        process_necessity_possibility_example(agent)
        process_epistemic_example(agent)
        process_deontic_example(agent)
        process_complex_example(agent)
        
        logger.info("Traitement terminé avec succès")
    
    except Exception as e:
        logger.error(f"Une erreur est survenue: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
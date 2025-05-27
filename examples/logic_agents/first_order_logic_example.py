#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation de l'agent de logique du premier ordre.

Cet exemple montre comment:
1. Initialiser un agent de logique du premier ordre
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
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet, FirstOrderBeliefSet

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FirstOrderLogicExample")

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

def create_first_order_logic_agent(kernel: Kernel, llm_service: any) -> FirstOrderLogicAgent:
    """
    Crée un agent de logique du premier ordre.
    
    Args:
        kernel: Le kernel Semantic Kernel
        llm_service: Le service LLM
        
    Returns:
        Un agent de logique du premier ordre
    """
    logger.info("Création de l'agent de logique du premier ordre...")
    
    # Utiliser la factory pour créer l'agent
    agent = LogicAgentFactory.create_agent("first_order", kernel, llm_service)
    
    if agent is None:
        raise RuntimeError("Échec de la création de l'agent de logique du premier ordre")
    
    logger.info("Agent de logique du premier ordre créé avec succès")
    return agent

def process_syllogism_example(agent: FirstOrderLogicAgent) -> None:
    """
    Traite un exemple de syllogisme catégorique.
    
    Args:
        agent: L'agent de logique du premier ordre
    """
    logger.info("Exemple de syllogisme catégorique")
    
    # Texte à analyser
    text = """
    Tous les hommes sont mortels.
    Socrate est un homme.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "Mortel(socrate)"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
    
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

def process_quantifiers_example(agent: FirstOrderLogicAgent) -> None:
    """
    Traite un exemple avec quantificateurs mixtes.
    
    Args:
        agent: L'agent de logique du premier ordre
    """
    logger.info("Exemple avec quantificateurs mixtes")
    
    # Texte à analyser
    text = """
    Tous les étudiants suivent au moins un cours.
    Aucun cours n'est facile.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "forall x: (Etudiant(x) => exists y: (Cours(y) && Suit(x,y) && !Facile(y)))"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")

def process_relations_example(agent: FirstOrderLogicAgent) -> None:
    """
    Traite un exemple avec des relations entre objets.
    
    Args:
        agent: L'agent de logique du premier ordre
    """
    logger.info("Exemple avec relations")
    
    # Texte à analyser
    text = """
    Tous les parents aiment leurs enfants.
    Marie est la mère de Jean.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "Aime(marie,jean)"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")

def process_complex_example(agent: FirstOrderLogicAgent) -> None:
    """
    Traite un exemple plus complexe.
    
    Args:
        agent: L'agent de logique du premier ordre
    """
    logger.info("Exemple complexe")
    
    # Texte à analyser
    text = """
    Tous les mammifères sont des vertébrés.
    Tous les chats sont des mammifères.
    Tous les vertébrés ont un cœur.
    Félix est un chat.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "ACœur(felix)"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
    
    # Exécuter une autre requête
    query2 = "Vertebre(felix)"
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
        
        # Créer l'agent de logique du premier ordre
        agent = create_first_order_logic_agent(kernel, llm_service)
        
        # Traiter les exemples
        process_syllogism_example(agent)
        process_quantifiers_example(agent)
        process_relations_example(agent)
        process_complex_example(agent)
        
        logger.info("Traitement terminé avec succès")
    
    except Exception as e:
        logger.error(f"Une erreur est survenue: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation de l'agent de logique propositionnelle.

Cet exemple montre comment:
1. Initialiser un agent de logique propositionnelle
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
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet, PropositionalBeliefSet

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PropositionalLogicExample")

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

def create_propositional_logic_agent(kernel: Kernel, llm_service: any) -> PropositionalLogicAgent:
    """
    Crée un agent de logique propositionnelle.
    
    Args:
        kernel: Le kernel Semantic Kernel
        llm_service: Le service LLM
        
    Returns:
        Un agent de logique propositionnelle
    """
    logger.info("Création de l'agent de logique propositionnelle...")
    
    # Utiliser la factory pour créer l'agent
    agent = LogicAgentFactory.create_agent("propositional", kernel, llm_service)
    
    if agent is None:
        raise RuntimeError("Échec de la création de l'agent de logique propositionnelle")
    
    logger.info("Agent de logique propositionnelle créé avec succès")
    return agent

def process_modus_ponens_example(agent: PropositionalLogicAgent) -> None:
    """
    Traite un exemple de Modus Ponens.
    
    Args:
        agent: L'agent de logique propositionnelle
    """
    logger.info("Exemple de Modus Ponens")
    
    # Texte à analyser
    text = """
    Si le ciel est nuageux, alors il va pleuvoir.
    Le ciel est nuageux.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Générer des requêtes pertinentes
    queries = agent.generate_queries(text, belief_set)
    logger.info(f"Requêtes générées: {queries}")
    
    # Exécuter les requêtes
    results = []
    for query in queries:
        result, result_msg = agent.execute_query(belief_set, query)
        logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
        results.append(result_msg)
    
    # Interpréter les résultats
    interpretation = agent.interpret_results(text, belief_set, queries, results)
    logger.info(f"Interprétation: {interpretation}")

def process_modus_tollens_example(agent: PropositionalLogicAgent) -> None:
    """
    Traite un exemple de Modus Tollens.
    
    Args:
        agent: L'agent de logique propositionnelle
    """
    logger.info("Exemple de Modus Tollens")
    
    # Texte à analyser
    text = """
    Si un animal est un mammifère, alors il a des poils.
    Ce reptile n'a pas de poils.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "!mammifere"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
    
    # Exécuter une autre requête
    query2 = "mammifere"
    result2, result_msg2 = agent.execute_query(belief_set, query2)
    logger.info(f"Requête: {query2} -> Résultat: {result2} ({result_msg2})")

def process_complex_example(agent: PropositionalLogicAgent) -> None:
    """
    Traite un exemple plus complexe.
    
    Args:
        agent: L'agent de logique propositionnelle
    """
    logger.info("Exemple complexe")
    
    # Texte à analyser
    text = """
    Si le projet est rentable et techniquement faisable, alors nous l'approuverons.
    Le projet est rentable.
    Si nous approuvons le projet, alors nous devrons embaucher plus de personnel.
    Nous n'embaucherons pas plus de personnel sauf si nous obtenons un financement supplémentaire.
    Nous n'obtiendrons pas de financement supplémentaire.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Exécuter une requête spécifique
    query = "!faisable"
    result, result_msg = agent.execute_query(belief_set, query)
    logger.info(f"Requête: {query} -> Résultat: {result} ({result_msg})")
    
    # Exécuter une autre requête
    query2 = "faisable"
    result2, result_msg2 = agent.execute_query(belief_set, query2)
    logger.info(f"Requête: {query2} -> Résultat: {result2} ({result_msg2})")
    
    # Exécuter une requête pour vérifier la cohérence
    query3 = "faisable && !faisable"
    result3, result_msg3 = agent.execute_query(belief_set, query3)
    logger.info(f"Requête: {query3} -> Résultat: {result3} ({result_msg3})")

def process_contradiction_example(agent: PropositionalLogicAgent) -> None:
    """
    Traite un exemple avec contradiction.
    
    Args:
        agent: L'agent de logique propositionnelle
    """
    logger.info("Exemple avec contradiction")
    
    # Texte à analyser
    text = """
    Tous les étudiants qui étudient régulièrement réussissent leurs examens.
    Alice est une étudiante qui étudie régulièrement.
    Alice n'a pas réussi son examen.
    """
    
    logger.info(f"Texte à analyser: {text}")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        logger.error(f"Échec de la conversion: {status_msg}")
        return
    
    logger.info(f"Ensemble de croyances créé: {belief_set.content}")
    
    # Vérifier si alice_reussite est dérivable
    query1 = "alice_reussite"
    result1, result_msg1 = agent.execute_query(belief_set, query1)
    logger.info(f"Requête: {query1} -> Résultat: {result1} ({result_msg1})")
    
    # Vérifier si !alice_reussite est dérivable
    query2 = "!alice_reussite"
    result2, result_msg2 = agent.execute_query(belief_set, query2)
    logger.info(f"Requête: {query2} -> Résultat: {result2} ({result_msg2})")
    
    # Vérifier s'il y a une contradiction
    query3 = "alice_reussite && !alice_reussite"
    result3, result_msg3 = agent.execute_query(belief_set, query3)
    logger.info(f"Requête: {query3} -> Résultat: {result3} ({result_msg3})")
    
    # Générer une interprétation
    interpretation = agent.interpret_results(
        text, 
        belief_set, 
        [query1, query2, query3], 
        [result_msg1, result_msg2, result_msg3]
    )
    logger.info(f"Interprétation: {interpretation}")

def main():
    """
    Fonction principale.
    """
    try:
        # Initialiser le kernel et le service LLM
        kernel, llm_service = initialize_kernel()
        
        # Créer l'agent de logique propositionnelle
        agent = create_propositional_logic_agent(kernel, llm_service)
        
        # Traiter les exemples
        process_modus_ponens_example(agent)
        process_modus_tollens_example(agent)
        process_complex_example(agent)
        process_contradiction_example(agent)
        
        logger.info("Traitement terminé avec succès")
    
    except Exception as e:
        logger.error(f"Une erreur est survenue: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
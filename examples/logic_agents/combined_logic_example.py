#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation combinée des différents agents logiques.

Cet exemple montre comment:
1. Initialiser différents agents logiques
2. Analyser un texte avec plusieurs types de logiques
3. Comparer les résultats des différentes approches
4. Combiner les analyses pour une interprétation plus riche

Prérequis:
- Semantic Kernel installé
- TweetyProject configuré
- JPype initialisé
"""

import logging
import sys
import time
from typing import Dict, List, Tuple, Optional, Any

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CombinedLogicExample")

class LogicAnalysisResult:
    """
    Classe pour stocker les résultats d'une analyse logique.
    """
    
    def __init__(self, logic_type: str, belief_set: BeliefSet, queries: List[str], results: List[Tuple[Optional[bool], str]], interpretation: str):
        """
        Initialise un résultat d'analyse logique.
        
        Args:
            logic_type: Type de logique utilisé
            belief_set: Ensemble de croyances
            queries: Requêtes exécutées
            results: Résultats des requêtes
            interpretation: Interprétation des résultats
        """
        self.logic_type = logic_type
        self.belief_set = belief_set
        self.queries = queries
        self.results = results
        self.interpretation = interpretation
    
    def __str__(self) -> str:
        """
        Représentation textuelle du résultat.
        
        Returns:
            Représentation textuelle
        """
        return f"Analyse {self.logic_type}:\n" \
               f"Ensemble de croyances: {self.belief_set.content}\n" \
               f"Requêtes: {self.queries}\n" \
               f"Interprétation: {self.interpretation}"

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

def create_logic_agents(kernel: Kernel, llm_service: any) -> Dict[str, Any]:
    """
    Crée les différents agents logiques.
    
    Args:
        kernel: Le kernel Semantic Kernel
        llm_service: Le service LLM
        
    Returns:
        Dictionnaire contenant les agents logiques
    """
    logger.info("Création des agents logiques...")
    
    agents = {}
    
    # Créer les agents pour chaque type de logique
    for logic_type in ["propositional", "first_order", "modal"]:
        agent = LogicAgentFactory.create_agent(logic_type, kernel, llm_service)
        
        if agent is None:
            logger.warning(f"Échec de la création de l'agent de logique {logic_type}")
            continue
        
        agents[logic_type] = agent
        logger.info(f"Agent de logique {logic_type} créé avec succès")
    
    return agents

def analyze_with_propositional_logic(agent: PropositionalLogicAgent, text: str) -> LogicAnalysisResult:
    """
    Analyse un texte avec la logique propositionnelle.
    
    Args:
        agent: L'agent de logique propositionnelle
        text: Le texte à analyser
        
    Returns:
        Résultat de l'analyse
    """
    logger.info("Analyse avec la logique propositionnelle...")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        raise RuntimeError(f"Échec de la conversion en ensemble de croyances propositionnelles: {status_msg}")
    
    logger.info(f"Ensemble de croyances propositionnelles créé: {belief_set.content}")
    
    # Générer des requêtes pertinentes
    queries = agent.generate_queries(text, belief_set)
    logger.info(f"Requêtes propositionnelles générées: {queries}")
    
    # Exécuter les requêtes
    results = []
    result_msgs = []
    for query in queries:
        result, result_msg = agent.execute_query(belief_set, query)
        logger.info(f"Requête propositionnelle: {query} -> Résultat: {result} ({result_msg})")
        results.append((result, result_msg))
        result_msgs.append(result_msg)
    
    # Interpréter les résultats
    interpretation = agent.interpret_results(text, belief_set, queries, result_msgs)
    logger.info(f"Interprétation propositionnelle: {interpretation}")
    
    return LogicAnalysisResult("propositional", belief_set, queries, results, interpretation)

def analyze_with_first_order_logic(agent: FirstOrderLogicAgent, text: str) -> LogicAnalysisResult:
    """
    Analyse un texte avec la logique du premier ordre.
    
    Args:
        agent: L'agent de logique du premier ordre
        text: Le texte à analyser
        
    Returns:
        Résultat de l'analyse
    """
    logger.info("Analyse avec la logique du premier ordre...")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        raise RuntimeError(f"Échec de la conversion en ensemble de croyances du premier ordre: {status_msg}")
    
    logger.info(f"Ensemble de croyances du premier ordre créé: {belief_set.content}")
    
    # Générer des requêtes pertinentes
    queries = agent.generate_queries(text, belief_set)
    logger.info(f"Requêtes du premier ordre générées: {queries}")
    
    # Exécuter les requêtes
    results = []
    result_msgs = []
    for query in queries:
        result, result_msg = agent.execute_query(belief_set, query)
        logger.info(f"Requête du premier ordre: {query} -> Résultat: {result} ({result_msg})")
        results.append((result, result_msg))
        result_msgs.append(result_msg)
    
    # Interpréter les résultats
    interpretation = agent.interpret_results(text, belief_set, queries, result_msgs)
    logger.info(f"Interprétation du premier ordre: {interpretation}")
    
    return LogicAnalysisResult("first_order", belief_set, queries, results, interpretation)

def analyze_with_modal_logic(agent: ModalLogicAgent, text: str) -> LogicAnalysisResult:
    """
    Analyse un texte avec la logique modale.
    
    Args:
        agent: L'agent de logique modale
        text: Le texte à analyser
        
    Returns:
        Résultat de l'analyse
    """
    logger.info("Analyse avec la logique modale...")
    
    # Convertir le texte en ensemble de croyances
    belief_set, status_msg = agent.text_to_belief_set(text)
    
    if belief_set is None:
        raise RuntimeError(f"Échec de la conversion en ensemble de croyances modales: {status_msg}")
    
    logger.info(f"Ensemble de croyances modales créé: {belief_set.content}")
    
    # Générer des requêtes pertinentes
    queries = agent.generate_queries(text, belief_set)
    logger.info(f"Requêtes modales générées: {queries}")
    
    # Exécuter les requêtes
    results = []
    result_msgs = []
    for query in queries:
        result, result_msg = agent.execute_query(belief_set, query)
        logger.info(f"Requête modale: {query} -> Résultat: {result} ({result_msg})")
        results.append((result, result_msg))
        result_msgs.append(result_msg)
    
    # Interpréter les résultats
    interpretation = agent.interpret_results(text, belief_set, queries, result_msgs)
    logger.info(f"Interprétation modale: {interpretation}")
    
    return LogicAnalysisResult("modal", belief_set, queries, results, interpretation)

def combine_analyses(text: str, results: Dict[str, LogicAnalysisResult]) -> str:
    """
    Combine les résultats des différentes analyses logiques.
    
    Args:
        text: Le texte analysé
        results: Les résultats des analyses
        
    Returns:
        Une interprétation combinée
    """
    logger.info("Combinaison des analyses...")
    
    combined = f"Analyse logique combinée du texte:\n\n{text}\n\n"
    
    # Ajouter les ensembles de croyances
    combined += "Ensembles de croyances:\n"
    for logic_type, result in results.items():
        combined += f"- {logic_type.capitalize()}: {result.belief_set.content}\n"
    
    combined += "\nInterprétations:\n"
    
    # Ajouter les interprétations
    for logic_type, result in results.items():
        combined += f"- {logic_type.capitalize()}: {result.interpretation}\n\n"
    
    # Ajouter une synthèse
    combined += "\nSynthèse:\n"
    
    if "propositional" in results and "first_order" in results:
        combined += "La logique propositionnelle permet une analyse simple des implications directes, "
        combined += "tandis que la logique du premier ordre offre une représentation plus riche avec des quantificateurs et des relations. "
    
    if "modal" in results:
        combined += "La logique modale ajoute une dimension supplémentaire en permettant d'exprimer des notions de nécessité, "
        combined += "possibilité, connaissance ou obligation. "
    
    combined += "\n\nCette analyse multi-perspective permet une compréhension plus complète et nuancée du raisonnement présenté dans le texte."
    
    logger.info("Combinaison des analyses terminée")
    return combined

def process_example(agents: Dict[str, Any], text: str) -> None:
    """
    Traite un exemple avec les différents agents logiques.
    
    Args:
        agents: Les agents logiques
        text: Le texte à analyser
    """
    logger.info(f"Traitement de l'exemple: {text}")
    
    results = {}
    
    # Analyser avec la logique propositionnelle
    if "propositional" in agents:
        try:
            results["propositional"] = analyze_with_propositional_logic(agents["propositional"], text)
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse propositionnelle: {str(e)}", exc_info=True)
    
    # Analyser avec la logique du premier ordre
    if "first_order" in agents:
        try:
            results["first_order"] = analyze_with_first_order_logic(agents["first_order"], text)
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du premier ordre: {str(e)}", exc_info=True)
    
    # Analyser avec la logique modale
    if "modal" in agents:
        try:
            results["modal"] = analyze_with_modal_logic(agents["modal"], text)
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse modale: {str(e)}", exc_info=True)
    
    # Combiner les analyses
    if results:
        combined = combine_analyses(text, results)
        logger.info(f"Résultat combiné:\n{combined}")
    else:
        logger.warning("Aucune analyse n'a pu être effectuée")

def main():
    """
    Fonction principale.
    """
    try:
        # Initialiser le kernel et le service LLM
        kernel, llm_service = initialize_kernel()
        
        # Créer les agents logiques
        agents = create_logic_agents(kernel, llm_service)
        
        # Exemple 1: Raisonnement simple
        text1 = """
        Si le ciel est nuageux, alors il va pleuvoir.
        Le ciel est nuageux.
        Donc, il va pleuvoir.
        """
        process_example(agents, text1)
        
        # Exemple 2: Raisonnement avec quantificateurs
        text2 = """
        Tous les hommes sont mortels.
        Socrate est un homme.
        Donc, Socrate est mortel.
        """
        process_example(agents, text2)
        
        # Exemple 3: Raisonnement avec modalités
        text3 = """
        Si une proposition est nécessairement vraie, alors elle est vraie.
        Si une proposition est vraie, alors elle est possiblement vraie.
        La somme des angles d'un triangle est nécessairement égale à 180 degrés.
        Donc, la somme des angles d'un triangle est possiblement égale à 180 degrés.
        """
        process_example(agents, text3)
        
        logger.info("Traitement terminé avec succès")
    
    except Exception as e:
        logger.error(f"Une erreur est survenue: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
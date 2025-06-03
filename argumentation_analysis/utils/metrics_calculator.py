# -*- coding: utf-8 -*-
"""
Utilitaires pour calculer diverses métriques à partir des résultats d'analyse d'argumentation.
"""

import logging
from typing import List, Dict, Any, Optional, Union # Ajout de Union
import numpy as np # Pour la moyenne des scores de confiance

logger = logging.getLogger(__name__)

def count_fallacies(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Compte le nombre total de sophismes détectés et par type/agent.

    :param results: Une liste de dictionnaires, où chaque dictionnaire représente
                    le résultat d'analyse pour un extrait ou par un agent.
                    Chaque résultat doit contenir une clé 'fallacies' (une liste de sophismes)
                    ou une structure similaire permettant d'identifier les sophismes.
                    On s'attend aussi à une clé 'agent_name' ou 'source_name' pour regrouper.
    :type results: List[Dict[str, Any]]
    :return: Un dictionnaire comptant les sophismes.
             Exemple: {'total_fallacies': 10, 'Ad Hominem': 3, 'AgentA_total': 5}
    :rtype: Dict[str, int]
    """
    logger.debug(f"Comptage des sophismes pour {len(results)} résultats.")
    fallacy_counts: Dict[str, int] = {"total_fallacies": 0}

    for result_item in results:
        agent_name = result_item.get("agent_name", result_item.get("source_name", "unknown_agent"))
        agent_total_key = f"{agent_name}_total_fallacies"
        
        fallacies_list = result_item.get("fallacies", [])
        if not isinstance(fallacies_list, list):
            # Gérer le cas où 'fallacies' pourrait être dans une sous-structure comme 'analysis'
            analysis_data = result_item.get("analysis", {})
            if isinstance(analysis_data, dict):
                fallacies_list = analysis_data.get("fallacies", [])
            if not isinstance(fallacies_list, list): # Vérifier à nouveau
                logger.warning(f"La clé 'fallacies' n'est pas une liste ou est absente pour l'item agent/source: {agent_name}. Item: {str(result_item)[:200]}")
                continue

        fallacy_counts["total_fallacies"] += len(fallacies_list)
        fallacy_counts.setdefault(agent_total_key, 0)
        fallacy_counts[agent_total_key] += len(fallacies_list)

        for fallacy in fallacies_list:
            if isinstance(fallacy, dict):
                fallacy_type = fallacy.get("fallacy_type", fallacy.get("type", "unknown_fallacy_type"))
                fallacy_counts.setdefault(fallacy_type, 0)
                fallacy_counts[fallacy_type] += 1
            else:
                logger.warning(f"Sophisme non-dictionnaire rencontré dans les résultats de {agent_name}: {str(fallacy)[:100]}")
                
    logger.info(f"Comptes de sophismes: {fallacy_counts}")
    return fallacy_counts

def extract_confidence_scores(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extrait et moyenne les scores de confiance des analyses.

    :param results: Une liste de résultats d'analyse. Chaque résultat peut contenir
                    un score de confiance global ou des scores par composant.
                    Exemple de structure attendue par résultat:
                    {'agent_name': 'AgentA', 'confidence_score': 0.85} ou
                    {'agent_name': 'AgentB', 'analysis': {'overall_confidence': 0.9}}
    :type results: List[Dict[str, Any]]
    :return: Un dictionnaire des scores de confiance moyens par agent/source.
             Exemple: {'AgentA_avg_confidence': 0.85, 'AgentB_avg_confidence': 0.9}
    :rtype: Dict[str, float]
    """
    logger.debug(f"Extraction des scores de confiance pour {len(results)} résultats.")
    confidence_scores_by_agent: Dict[str, List[float]] = {}

    for result_item in results:
        agent_name = result_item.get("agent_name", result_item.get("source_name", "unknown_agent"))
        
        score = None
        if "confidence_score" in result_item:
            score = result_item["confidence_score"]
        elif "analysis" in result_item and isinstance(result_item["analysis"], dict) and \
             "confidence_score" in result_item["analysis"]:
            score = result_item["analysis"]["confidence_score"]
        elif "analysis" in result_item and isinstance(result_item["analysis"], dict) and \
             "overall_confidence" in result_item["analysis"]: # Autre clé possible
            score = result_item["analysis"]["overall_confidence"]
        
        if isinstance(score, (float, int)):
            confidence_scores_by_agent.setdefault(agent_name, []).append(float(score))
        else:
            logger.debug(f"Score de confiance non trouvé ou invalide pour {agent_name} dans l'item: {str(result_item)[:200]}")

    avg_confidence_scores: Dict[str, float] = {}
    for agent, scores in confidence_scores_by_agent.items():
        if scores:
            avg_confidence_scores[f"{agent}_avg_confidence"] = float(np.mean(scores))
        else:
            avg_confidence_scores[f"{agent}_avg_confidence"] = 0.0
            
    logger.info(f"Scores de confiance moyens: {avg_confidence_scores}")
    return avg_confidence_scores

def analyze_contextual_richness(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Analyse la richesse contextuelle des résultats d'analyse.

    La richesse contextuelle peut être basée sur la longueur du contexte fourni,
    le nombre de points de données contextuels, la présence de citations, etc.
    Cette implémentation est une maquette et pourrait être affinée.
    Pour l'instant, on simule un score basé sur la longueur du 'context_text'
    dans les sophismes, ou la longueur d'un champ 'summary' ou 'detailed_analysis'.

    :param results: Une liste de résultats d'analyse.
    :type results: List[Dict[str, Any]]
    :return: Un dictionnaire des scores de richesse contextuelle moyens par agent/source.
    :rtype: Dict[str, float]
    """
    logger.debug(f"Analyse de la richesse contextuelle pour {len(results)} résultats.")
    richness_scores_by_agent: Dict[str, List[float]] = {}

    for result_item in results:
        agent_name = result_item.get("agent_name", result_item.get("source_name", "unknown_agent"))
        current_richness_score = 0.0
        
        analysis_part = result_item.get("analysis", result_item) # Si 'analysis' n'existe pas, on prend l'item entier

        if isinstance(analysis_part, dict):
            # Option 1: Basé sur la longueur du contexte des sophismes
            fallacies = analysis_part.get("fallacies", [])
            if isinstance(fallacies, list) and fallacies:
                total_context_length = 0
                num_contexts = 0
                for fallacy in fallacies:
                    if isinstance(fallacy, dict) and "context_text" in fallacy and isinstance(fallacy["context_text"], str):
                        total_context_length += len(fallacy["context_text"])
                        num_contexts += 1
                if num_contexts > 0:
                    current_richness_score = total_context_length / (num_contexts * 100.0) # Score normalisé (arbitraire)
            
            # Option 2: Basé sur la longueur d'un résumé ou d'une analyse détaillée
            summary = analysis_part.get("summary", "")
            detailed_analysis = analysis_part.get("detailed_analysis", "")
            
            if isinstance(summary, str) and len(summary) > current_richness_score * 50: # Donner plus de poids si c'est un résumé
                 current_richness_score = max(current_richness_score, len(summary) / 200.0) # Normalisation arbitraire
            if isinstance(detailed_analysis, str) and len(detailed_analysis) > current_richness_score * 50:
                 current_richness_score = max(current_richness_score, len(detailed_analysis) / 500.0) # Normalisation arbitraire

        # S'assurer que le score est entre 0 et 1 (par exemple)
        current_richness_score = min(max(current_richness_score, 0.0), 1.0) 
        richness_scores_by_agent.setdefault(agent_name, []).append(current_richness_score)

    avg_richness_scores: Dict[str, float] = {}
    for agent, scores in richness_scores_by_agent.items():
        if scores:
            avg_richness_scores[f"{agent}_avg_richness"] = float(np.mean(scores))
        else:
            avg_richness_scores[f"{agent}_avg_richness"] = 0.0
            
    logger.info(f"Scores de richesse contextuelle moyens: {avg_richness_scores}")
    return avg_richness_scores
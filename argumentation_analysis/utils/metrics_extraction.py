#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaires pour l'extraction de métriques spécifiques à partir des résultats d'analyse.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def extract_execution_time_from_results(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Extrait les temps d'exécution à partir des timestamps dans les résultats d'analyse.
    Les temps sont calculés par rapport au timestamp principal de l'extrait.

    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse, chaque résultat
                                         devant avoir une clé "timestamp" et une clé "analyses"
                                         contenant des sous-dictionnaires avec "analysis_timestamp".

    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des temps d'exécution.
                                     Clé externe: nom de l'extrait.
                                     Clé interne: type d'analyse.
                                     Valeur: temps d'exécution en secondes.
    """
    execution_times: Dict[str, Dict[str, float]] = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu_" + str(datetime.now().timestamp())) # Assurer un nom unique si manquant
        main_timestamp_str = result.get("timestamp")
        
        if not main_timestamp_str:
            logger.debug(f"Timestamp principal manquant pour l'extrait '{extract_name}'. Temps d'exécution non calculables.")
            continue
            
        try:
            main_dt = datetime.fromisoformat(main_timestamp_str)
        except (ValueError, TypeError) as e:
            logger.warning(f"Format de timestamp principal invalide pour '{extract_name}': {main_timestamp_str}. Erreur: {e}")
            continue
            
        analyses_data = result.get("analyses")
        if not isinstance(analyses_data, dict):
            logger.debug(f"Aucune donnée d'analyse (ou format incorrect) pour '{extract_name}'.")
            continue

        current_extract_times: Dict[str, float] = {}
        for analysis_type, analysis_details in analyses_data.items():
            if not isinstance(analysis_details, dict):
                logger.debug(f"Détails d'analyse pour '{analysis_type}' dans '{extract_name}' n'est pas un dictionnaire.")
                continue

            analysis_timestamp_str = analysis_details.get("analysis_timestamp")
            if not analysis_timestamp_str:
                logger.debug(f"Timestamp d'analyse manquant pour '{analysis_type}' dans '{extract_name}'.")
                continue
                
            try:
                analysis_dt = datetime.fromisoformat(analysis_timestamp_str)
                time_diff_seconds = (analysis_dt - main_dt).total_seconds()
                current_extract_times[analysis_type] = time_diff_seconds
            except (ValueError, TypeError) as e:
                logger.warning(f"Format de timestamp d'analyse invalide pour '{analysis_type}' dans '{extract_name}': {analysis_timestamp_str}. Erreur: {e}")
        
        if current_extract_times:
            execution_times[extract_name] = current_extract_times
            
    logger.info(f"{len(execution_times)} extraits avec des temps d'exécution extraits.")
    return execution_times

def count_fallacies_in_results(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """
    Compte le nombre de sophismes détectés par différents agents/types d'analyse
    à partir des résultats structurés.

    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse. Chaque résultat
                                         doit contenir une clé "analyses" avec les détails.

    Returns:
        Dict[str, Dict[str, int]]: Dictionnaire du nombre de sophismes.
                                     Clé externe: nom de l'extrait.
                                     Clé interne: type d'agent/analyse (ex: "base_contextual", "advanced_complex").
                                     Valeur: nombre de sophismes.
    """
    fallacy_counts: Dict[str, Dict[str, int]] = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu_" + str(datetime.now().timestamp()))
        # Initialiser avec toutes les clés attendues pour assurer une structure cohérente
        current_extract_counts: Dict[str, int] = {
            "base_contextual": 0,
            "advanced_complex": 0,
            "advanced_contextual": 0
        }
        
        analyses_data = result.get("analyses", {})
        if not isinstance(analyses_data, dict):
            logger.debug(f"Aucune donnée d'analyse (ou format incorrect) pour '{extract_name}' lors du comptage des sophismes. Utilisation des valeurs par défaut (0).")
            fallacy_counts[extract_name] = current_extract_counts # Contient maintenant les clés avec 0
            continue

        # Analyse de base - sophismes contextuels
        base_contextual_analysis = analyses_data.get("contextual_fallacies", {})
        if isinstance(base_contextual_analysis, dict):
            argument_results = base_contextual_analysis.get("argument_results", [])
            base_contextual_count = 0
            if isinstance(argument_results, list):
                for arg_result in argument_results:
                    if isinstance(arg_result, dict):
                        base_contextual_count += len(arg_result.get("detected_fallacies", []))
            current_extract_counts["base_contextual"] = base_contextual_count
        else:
            current_extract_counts["base_contextual"] = 0
        
        # Analyse avancée - sophismes complexes
        complex_fallacies_analysis = analyses_data.get("complex_fallacies", {})
        adv_complex_total = 0
        if isinstance(complex_fallacies_analysis, dict):
            adv_complex_total += complex_fallacies_analysis.get("individual_fallacies_count", 0)
            adv_complex_total += len(complex_fallacies_analysis.get("basic_combinations", []))
            adv_complex_total += len(complex_fallacies_analysis.get("advanced_combinations", []))
            adv_complex_total += len(complex_fallacies_analysis.get("fallacy_patterns", []))
        current_extract_counts["advanced_complex"] = adv_complex_total
        
        # Analyse avancée - sophismes contextuels
        advanced_contextual_data = analyses_data.get("contextual_fallacies", {})
        if isinstance(advanced_contextual_data, dict):
             current_extract_counts["advanced_contextual"] = advanced_contextual_data.get("contextual_fallacies_count", 0)
        else:
            current_extract_counts["advanced_contextual"] = 0
        
        fallacy_counts[extract_name] = current_extract_counts
            
    logger.info(f"Comptage des sophismes terminé pour {len(fallacy_counts)} extraits.")
    return fallacy_counts

def extract_confidence_scores_from_results(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Extrait les scores de confiance des différentes analyses.

    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse.

    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de confiance.
                                     Clé externe: nom de l'extrait.
                                     Clé interne: type d'analyse/score (ex: "base_coherence", "advanced_rhetorical").
                                     Valeur: score de confiance.
    """
    confidence_scores: Dict[str, Dict[str, float]] = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu_" + str(datetime.now().timestamp()))
        current_extract_scores: Dict[str, float] = {}
        analyses_data = result.get("analyses") # Peut être None

        if analyses_data is None or not isinstance(analyses_data, dict):
            logger.debug(f"Clé 'analyses' absente ou format incorrect pour '{extract_name}' lors de l'extraction des scores de confiance. Retour d'un dict vide.")
            confidence_scores[extract_name] = {}
            continue

        # Analyse de base - cohérence argumentative
        base_coherence_analysis = analyses_data.get("argument_coherence", {})
        if isinstance(base_coherence_analysis, dict):
            overall_coherence_data = base_coherence_analysis.get("overall_coherence", {})
            if isinstance(overall_coherence_data, dict):
                current_extract_scores["base_coherence"] = overall_coherence_data.get("score", 0.0)
            else:
                current_extract_scores["base_coherence"] = 0.0
        else:
            current_extract_scores["base_coherence"] = 0.0
        
        # Analyse avancée - analyse rhétorique globale
        rhetorical_results_analysis = analyses_data.get("rhetorical_results", {})
        if isinstance(rhetorical_results_analysis, dict):
            overall_rhetorical_analysis = rhetorical_results_analysis.get("overall_analysis", {})
            if isinstance(overall_rhetorical_analysis, dict):
                current_extract_scores["advanced_rhetorical"] = overall_rhetorical_analysis.get("rhetorical_quality", 0.0)
            else:
                current_extract_scores["advanced_rhetorical"] = 0.0

            # Analyse avancée - cohérence (depuis rhetorical_results)
            coherence_sub_analysis = rhetorical_results_analysis.get("coherence_analysis", {})
            if isinstance(coherence_sub_analysis, dict):
                current_extract_scores["advanced_coherence"] = coherence_sub_analysis.get("overall_coherence", 0.0)
            else:
                current_extract_scores["advanced_coherence"] = 0.0
        else:
            current_extract_scores["advanced_rhetorical"] = 0.0
            current_extract_scores["advanced_coherence"] = 0.0

        # Analyse avancée - gravité des sophismes
        fallacy_severity_analysis = analyses_data.get("fallacy_severity", {})
        if isinstance(fallacy_severity_analysis, dict):
            current_extract_scores["advanced_severity"] = fallacy_severity_analysis.get("overall_severity", 0.0)
        else:
            current_extract_scores["advanced_severity"] = 0.0
            
        confidence_scores[extract_name] = current_extract_scores
            
    logger.info(f"Extraction des scores de confiance terminée pour {len(confidence_scores)} extraits.")
    return confidence_scores

def analyze_contextual_richness_from_results(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Analyse la richesse contextuelle des résultats d'analyse.

    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse.

    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de richesse contextuelle.
                                     Clé externe: nom de l'extrait.
                                     Clé interne: type d'analyse/agent (ex: "base_contextual", "advanced_rhetorical").
                                     Valeur: score de richesse.
    """
    richness_scores: Dict[str, Dict[str, float]] = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu_" + str(datetime.now().timestamp()))
        current_extract_scores: Dict[str, float] = {}
        analyses_data = result.get("analyses")

        if analyses_data is None or not isinstance(analyses_data, dict):
            logger.debug(f"Clé 'analyses' absente ou format incorrect pour '{extract_name}' lors de l'analyse de richesse contextuelle. Retour d'un dict vide.")
            richness_scores[extract_name] = {}
            continue

        # Analyse de base - facteurs contextuels
        base_contextual_data = analyses_data.get("contextual_fallacies", {})
        base_richness = 0
        if isinstance(base_contextual_data, dict):
            contextual_factors = base_contextual_data.get("contextual_factors", {})
            if isinstance(contextual_factors, dict):
                base_richness = len(contextual_factors)
        current_extract_scores["base_contextual"] = float(base_richness)
        
        # Analyse avancée - analyse contextuelle (depuis "contextual_fallacies" des résultats avancés)
        advanced_contextual_data = analyses_data.get("contextual_fallacies", {})
        adv_contextual_richness = 0
        if isinstance(advanced_contextual_data, dict):
            context_analysis = advanced_contextual_data.get("context_analysis", {})
            if isinstance(context_analysis, dict):
                if context_analysis.get("context_type"): adv_contextual_richness += 1
                adv_contextual_richness += len(context_analysis.get("context_subtypes", []))
                adv_contextual_richness += len(context_analysis.get("audience_characteristics", []))
                if context_analysis.get("formality_level"): adv_contextual_richness += 1
        current_extract_scores["advanced_contextual"] = float(adv_contextual_richness)
        
        # Analyse avancée - analyse rhétorique globale (depuis "rhetorical_results")
        rhetorical_results_data = analyses_data.get("rhetorical_results", {})
        adv_rhetorical_richness = 0
        if isinstance(rhetorical_results_data, dict):
            overall_analysis_data = rhetorical_results_data.get("overall_analysis", {})
            if isinstance(overall_analysis_data, dict):
                adv_rhetorical_richness += len(overall_analysis_data.get("main_strengths", []))
                adv_rhetorical_richness += len(overall_analysis_data.get("main_weaknesses", []))
                if overall_analysis_data.get("context_relevance"): adv_rhetorical_richness += 1
        current_extract_scores["advanced_rhetorical"] = float(adv_rhetorical_richness)
            
        richness_scores[extract_name] = current_extract_scores
            
    logger.info(f"Analyse de la richesse contextuelle terminée pour {len(richness_scores)} extraits.")
    return richness_scores

def evaluate_coherence_relevance_from_results(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Évalue la pertinence des évaluations de cohérence à partir des résultats d'analyse.
    Le score est basé sur la présence et le nombre d'éléments d'évaluation et de recommandations.

    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse.

    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de pertinence.
                                     Clé externe: nom de l'extrait.
                                     Clé interne: type d'analyse/agent (ex: "base_coherence", "advanced_coherence").
                                     Valeur: score de pertinence.
    """
    relevance_scores: Dict[str, Dict[str, float]] = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu_" + str(datetime.now().timestamp()))
        current_extract_scores: Dict[str, float] = {} # Nom original était current_extract_relevance
        analyses_data = result.get("analyses")

        if analyses_data is None or not isinstance(analyses_data, dict):
            logger.debug(f"Clé 'analyses' absente ou format incorrect pour '{extract_name}' lors de l'évaluation de pertinence/cohérence. Retour d'un dict vide.")
            relevance_scores[extract_name] = {}
            continue

        # Analyse de base - cohérence argumentative
        base_coherence_data = analyses_data.get("argument_coherence", {})
        base_relevance = 0
        if isinstance(base_coherence_data, dict):
            base_relevance += len(base_coherence_data.get("recommendations", []))
            coherence_evals = base_coherence_data.get("coherence_evaluations", {})
            if isinstance(coherence_evals, dict):
                 base_relevance += len(coherence_evals)
        current_extract_scores["base_coherence"] = float(base_relevance)
        
        # Analyse avancée - analyse de cohérence (depuis "rhetorical_results")
        rhetorical_results_data = analyses_data.get("rhetorical_results", {})
        adv_coherence_relevance = 0
        adv_recommendations_relevance = 0
        if isinstance(rhetorical_results_data, dict):
            coherence_analysis_data = rhetorical_results_data.get("coherence_analysis", {})
            if isinstance(coherence_analysis_data, dict):
                if coherence_analysis_data.get("overall_coherence"): adv_coherence_relevance += 1
                if coherence_analysis_data.get("coherence_level"): adv_coherence_relevance += 1
                if coherence_analysis_data.get("thematic_coherence"): adv_coherence_relevance += 1
                if coherence_analysis_data.get("logical_coherence"): adv_coherence_relevance += 1
            
            recommendations_data = rhetorical_results_data.get("recommendations", {})
            if isinstance(recommendations_data, dict):
                coherence_recommendations_list = recommendations_data.get("coherence_recommendations", [])
                adv_recommendations_relevance = len(coherence_recommendations_list)

        current_extract_scores["advanced_coherence"] = float(adv_coherence_relevance)
        current_extract_scores["advanced_recommendations"] = float(adv_recommendations_relevance)
            
        relevance_scores[extract_name] = current_extract_scores
            
    logger.info(f"Évaluation de la pertinence de cohérence terminée pour {len(relevance_scores)} extraits.")
    return relevance_scores

def _calculate_obj_complexity(obj: Any, depth: int = 0) -> float:
    """
    Fonction d'assistance récursive pour calculer la complexité d'un objet (dict, list, autres).
    La complexité est une mesure simple basée sur la profondeur et la largeur.
    """
    if isinstance(obj, dict):
        if not obj: return float(depth)
        return depth + sum(_calculate_obj_complexity(v, depth + 1) for v in obj.values()) / len(obj)
    elif isinstance(obj, list):
        if not obj: return float(depth)
        return depth + sum(_calculate_obj_complexity(v, depth + 1) for v in obj) / len(obj)
    else:
        return float(depth)

def analyze_result_complexity_from_results(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Analyse la complexité des résultats produits par chaque agent/type d'analyse.
    La complexité est une métrique simple basée sur la profondeur et la largeur des structures de données.

    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse.

    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de complexité.
                                     Clé externe: nom de l'extrait.
                                     Clé interne: type d'analyse/agent.
                                     Valeur: score de complexité.
    """
    complexity_scores: Dict[str, Dict[str, float]] = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu_" + str(datetime.now().timestamp()))
        current_extract_scores: Dict[str, float] = {}
        analyses_data = result.get("analyses", {})

        if not isinstance(analyses_data, dict):
            logger.debug(f"Aucune donnée d'analyse pour '{extract_name}' lors de l'analyse de complexité.")
            complexity_scores[extract_name] = current_extract_scores
            continue
            
        for analysis_type, analysis_content in analyses_data.items():
            if isinstance(analysis_content, dict) or isinstance(analysis_content, list):
                current_extract_scores[analysis_type] = _calculate_obj_complexity(analysis_content)
            else:
                current_extract_scores[analysis_type] = 0.0
        
        complexity_scores[extract_name] = current_extract_scores
            
    logger.info(f"Analyse de la complexité des résultats terminée pour {len(complexity_scores)} extraits.")
    return complexity_scores
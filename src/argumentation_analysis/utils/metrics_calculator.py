# -*- coding: utf-8 -*-
"""Utilitaires pour le calcul de métriques d'analyse d'argumentation."""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def count_fallacies(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compte le nombre de sophismes détectés par chaque agent à partir des résultats."""
    fallacy_counts = {
        "base_contextual": 0,
        "advanced_contextual": 0,
        "advanced_complex": 0
    }
    
    for result in results:
        # Analyse de base - sophismes contextuels
        # La structure exacte peut varier, adapter les get si besoin
        base_analysis_part = result.get("analyses", result) # Pour compatibilité avec différentes structures de résultats

        contextual_fallacies = base_analysis_part.get("contextual_fallacies", {})
        argument_results = contextual_fallacies.get("argument_results", [])
        
        for arg_result in argument_results:
            fallacy_counts["base_contextual"] += len(arg_result.get("detected_fallacies", []))
        
        # Analyse avancée - sophismes complexes
        complex_fallacies = base_analysis_part.get("complex_fallacies", {})
        
        fallacy_counts["advanced_complex"] += complex_fallacies.get("individual_fallacies_count", 0)
        fallacy_counts["advanced_complex"] += len(complex_fallacies.get("basic_combinations", []))
        fallacy_counts["advanced_complex"] += len(complex_fallacies.get("advanced_combinations", []))
        fallacy_counts["advanced_complex"] += len(complex_fallacies.get("fallacy_patterns", []))
        
        # Analyse avancée - sophismes contextuels (si présents dans la même structure de résultat)
        # Si les résultats avancés ont une section "contextual_fallacies" distincte, il faudra ajuster
        advanced_contextual_data = base_analysis_part.get("contextual_fallacies", {}) # Peut être redondant si déjà lu
        fallacy_counts["advanced_contextual"] += advanced_contextual_data.get("contextual_fallacies_count", 0)
            
    logger.debug(f"Comptes de sophismes calculés: {fallacy_counts}")
    return fallacy_counts

def extract_confidence_scores(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Extrait et moyenne les scores de confiance des analyses."""
    confidence_scores_lists: Dict[str, List[float]] = {
        "base_coherence": [],
        "advanced_rhetorical": [],
        "advanced_coherence": [],
        "advanced_severity": []
    }
    
    for result in results:
        analyses_data = result.get("analyses", result)

        # Analyse de base - cohérence argumentative
        base_coherence = analyses_data.get("argument_coherence", {})
        base_coherence_score = base_coherence.get("overall_coherence", {}).get("score", 0.0)
        confidence_scores_lists["base_coherence"].append(float(base_coherence_score))
        
        # Analyse avancée - analyse rhétorique globale
        rhetorical_results = analyses_data.get("rhetorical_results", {})
        overall_analysis = rhetorical_results.get("overall_analysis", {})
        rhetorical_quality = overall_analysis.get("rhetorical_quality", 0.0)
        confidence_scores_lists["advanced_rhetorical"].append(float(rhetorical_quality))
        
        # Analyse avancée - cohérence
        coherence_analysis = rhetorical_results.get("coherence_analysis", {})
        overall_coherence = coherence_analysis.get("overall_coherence", 0.0)
        confidence_scores_lists["advanced_coherence"].append(float(overall_coherence))
        
        # Analyse avancée - gravité des sophismes
        fallacy_severity = analyses_data.get("fallacy_severity", {})
        overall_severity = fallacy_severity.get("overall_severity", 0.0)
        confidence_scores_lists["advanced_severity"].append(float(overall_severity))
    
    avg_scores: Dict[str, float] = {}
    for agent, scores in confidence_scores_lists.items():
        if scores:
            avg_scores[agent] = sum(scores) / len(scores)
        else:
            avg_scores[agent] = 0.0
            
    logger.debug(f"Scores de confiance moyens calculés: {avg_scores}")
    return avg_scores

def analyze_contextual_richness(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Analyse la richesse contextuelle des résultats et retourne des scores moyens."""
    richness_scores_lists: Dict[str, List[float]] = {
        "base_contextual": [],
        "advanced_contextual": [],
        "advanced_rhetorical": []
    }
    
    for result in results:
        analyses_data = result.get("analyses", result)

        # Analyse de base - facteurs contextuels
        base_contextual = analyses_data.get("contextual_fallacies", {})
        contextual_factors = base_contextual.get("contextual_factors", {})
        base_richness = float(len(contextual_factors))
        richness_scores_lists["base_contextual"].append(base_richness)
        
        # Analyse avancée - analyse contextuelle
        # La structure peut varier, s'assurer que 'contextual_fallacies' est le bon chemin
        advanced_contextual_data = analyses_data.get("contextual_fallacies", {}) 
        context_analysis = advanced_contextual_data.get("context_analysis", {})
        
        advanced_richness_score = 0.0
        if context_analysis.get("context_type"):
            advanced_richness_score += 1
        advanced_richness_score += len(context_analysis.get("context_subtypes", []))
        advanced_richness_score += len(context_analysis.get("audience_characteristics", []))
        if context_analysis.get("formality_level"):
            advanced_richness_score += 1
        richness_scores_lists["advanced_contextual"].append(advanced_richness_score)
        
        # Analyse avancée - analyse rhétorique globale
        rhetorical_results = analyses_data.get("rhetorical_results", {})
        overall_analysis = rhetorical_results.get("overall_analysis", {})
        
        rhetorical_richness_score = 0.0
        rhetorical_richness_score += len(overall_analysis.get("main_strengths", []))
        rhetorical_richness_score += len(overall_analysis.get("main_weaknesses", []))
        if overall_analysis.get("context_relevance"): # Souvent un score ou un booléen
            relevance_value = overall_analysis.get("context_relevance")
            if isinstance(relevance_value, (int, float)) and relevance_value > 0:
                 rhetorical_richness_score += relevance_value # ou 1 si c'est un booléen/score normalisé
            elif isinstance(relevance_value, bool) and relevance_value:
                 rhetorical_richness_score += 1

        richness_scores_lists["advanced_rhetorical"].append(rhetorical_richness_score)
    
    avg_scores: Dict[str, float] = {}
    for agent, scores in richness_scores_lists.items():
        if scores:
            avg_scores[agent] = sum(scores) / len(scores)
        else:
            avg_scores[agent] = 0.0
            
    logger.debug(f"Scores de richesse contextuelle moyens calculés: {avg_scores}")
    return avg_scores
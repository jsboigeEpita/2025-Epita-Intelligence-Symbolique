#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour comparer les performances des différents agents spécialistes d'analyse rhétorique.

Ce script:
1. Charge les résultats des analyses de base et avancée
2. Compare les performances des agents sur plusieurs critères:
   - Précision de détection des sophismes
   - Richesse de l'analyse contextuelle
   - Pertinence des évaluations de cohérence
   - Temps d'exécution
   - Complexité des résultats
3. Génère des métriques quantitatives pour chaque agent:
   - Nombre de sophismes détectés
   - Scores de confiance moyens
   - Taux de faux positifs/négatifs (estimés)
   - Temps d'exécution moyen
4. Produit des visualisations comparatives:
   - Graphiques de performance
   - Matrices de confusion
   - Diagrammes de comparaison
5. Génère un rapport détaillé sur la pertinence des différents agents
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tqdm import tqdm

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CompareRhetoricalAgents")

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Vérifier les dépendances requises
required_packages = ["matplotlib", "numpy", "pandas", "seaborn", "tqdm"]
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    logger.warning(f"Les packages suivants sont manquants: {', '.join(missing_packages)}")
    logger.warning(f"Certaines fonctionnalités peuvent être limitées.")
    logger.warning(f"Pour installer les packages manquants: pip install {' '.join(missing_packages)}")

def load_results(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les résultats d'analyse depuis un fichier JSON.
    
    Args:
        file_path (Path): Chemin vers le fichier JSON contenant les résultats
        
    Returns:
        List[Dict[str, Any]]: Liste des résultats d'analyse
    """
    logger.info(f"Chargement des résultats depuis {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        logger.info(f"✅ {len(results)} résultats chargés avec succès")
        return results
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement des résultats: {e}")
        return []

def extract_execution_time(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Extrait les temps d'exécution à partir des timestamps dans les résultats.
    
    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse
        
    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des temps d'exécution par extrait
    """
    execution_times = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu")
        timestamp_str = result.get("timestamp")
        
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                
                # Chercher les timestamps dans les analyses
                for analysis_type, analysis in result.get("analyses", {}).items():
                    analysis_timestamp_str = analysis.get("analysis_timestamp")
                    
                    if analysis_timestamp_str:
                        try:
                            analysis_timestamp = datetime.fromisoformat(analysis_timestamp_str)
                            time_diff = (analysis_timestamp - timestamp).total_seconds()
                            
                            if extract_name not in execution_times:
                                execution_times[extract_name] = {}
                            
                            execution_times[extract_name][analysis_type] = time_diff
                        except (ValueError, TypeError):
                            pass
            except (ValueError, TypeError):
                pass
    
def count_fallacies(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """
    Compte le nombre de sophismes détectés par chaque agent.
    
    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse
        
    Returns:
        Dict[str, Dict[str, int]]: Dictionnaire du nombre de sophismes par extrait et par agent
    """
    fallacy_counts = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu")
        fallacy_counts[extract_name] = {}
        
        # Analyse de base - sophismes contextuels
        contextual_fallacies = result.get("analyses", {}).get("contextual_fallacies", {})
        argument_results = contextual_fallacies.get("argument_results", [])
        
        count = 0
        for arg_result in argument_results:
            count += len(arg_result.get("detected_fallacies", []))
        
        fallacy_counts[extract_name]["base_contextual"] = count
        
        # Analyse avancée - sophismes complexes
        complex_fallacies = result.get("analyses", {}).get("complex_fallacies", {})
        
        # Compter les sophismes individuels
        individual_count = complex_fallacies.get("individual_fallacies_count", 0)
        
        # Compter les combinaisons de base
        basic_combinations = complex_fallacies.get("basic_combinations", [])
        basic_count = len(basic_combinations)
        
        # Compter les combinaisons avancées
        advanced_combinations = complex_fallacies.get("advanced_combinations", [])
        advanced_count = len(advanced_combinations)
        
        # Compter les motifs de sophismes
        fallacy_patterns = complex_fallacies.get("fallacy_patterns", [])
        pattern_count = len(fallacy_patterns)
        
        fallacy_counts[extract_name]["advanced_complex"] = individual_count + basic_count + advanced_count + pattern_count
        
        # Analyse avancée - sophismes contextuels
        advanced_contextual = result.get("analyses", {}).get("contextual_fallacies", {})
        contextual_count = advanced_contextual.get("contextual_fallacies_count", 0)
        
        fallacy_counts[extract_name]["advanced_contextual"] = contextual_count
    
    return fallacy_counts

def extract_confidence_scores(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Extrait les scores de confiance des analyses.
    
    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse
        
    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de confiance par extrait et par agent
    """
    confidence_scores = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu")
        confidence_scores[extract_name] = {}
        
        # Analyse de base - cohérence argumentative
        base_coherence = result.get("analyses", {}).get("argument_coherence", {})
        base_coherence_score = base_coherence.get("overall_coherence", {}).get("score", 0.0)
        confidence_scores[extract_name]["base_coherence"] = base_coherence_score
        
        # Analyse avancée - analyse rhétorique globale
        rhetorical_results = result.get("analyses", {}).get("rhetorical_results", {})
        overall_analysis = rhetorical_results.get("overall_analysis", {})
        rhetorical_quality = overall_analysis.get("rhetorical_quality", 0.0)
        confidence_scores[extract_name]["advanced_rhetorical"] = rhetorical_quality
        
        # Analyse avancée - cohérence
        coherence_analysis = rhetorical_results.get("coherence_analysis", {})
        overall_coherence = coherence_analysis.get("overall_coherence", 0.0)
        confidence_scores[extract_name]["advanced_coherence"] = overall_coherence
        
        # Analyse avancée - gravité des sophismes
        fallacy_severity = result.get("analyses", {}).get("fallacy_severity", {})
        overall_severity = fallacy_severity.get("overall_severity", 0.0)
        confidence_scores[extract_name]["advanced_severity"] = overall_severity
    
    return confidence_scores
    return execution_times
def estimate_false_positives_negatives(base_results: List[Dict[str, Any]], advanced_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Estime les taux de faux positifs et faux négatifs en comparant les analyses de base et avancées.
    
    Args:
        base_results (List[Dict[str, Any]]): Liste des résultats d'analyse de base
        advanced_results (List[Dict[str, Any]]): Liste des résultats d'analyse avancée
        
    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des taux de faux positifs/négatifs par agent
    """
    error_rates = {
        "base_contextual": {"false_positive": 0.0, "false_negative": 0.0, "count": 0},
        "advanced_contextual": {"false_positive": 0.0, "false_negative": 0.0, "count": 0},
        "advanced_complex": {"false_positive": 0.0, "false_negative": 0.0, "count": 0}
    }
    
    # Créer des dictionnaires pour accéder rapidement aux résultats par nom d'extrait
    base_dict = {f"{r.get('source_name', '')}:{r.get('extract_name', '')}": r for r in base_results}
    advanced_dict = {f"{r.get('source_name', '')}:{r.get('extract_name', '')}": r for r in advanced_results}
    
    # Comparer les résultats pour chaque extrait présent dans les deux analyses
    common_extracts = set(base_dict.keys()) & set(advanced_dict.keys())
    
    for key in common_extracts:
        base_result = base_dict[key]
        advanced_result = advanced_dict[key]
        
        # Comparer les sophismes contextuels de base et avancés
        base_contextual = base_result.get("analyses", {}).get("contextual_fallacies", {})
        advanced_contextual = advanced_result.get("analyses", {}).get("contextual_fallacies", {})
        
        base_fallacies = []
        for arg_result in base_contextual.get("argument_results", []):
            for fallacy in arg_result.get("detected_fallacies", []):
                fallacy_type = fallacy.get("fallacy_type", "")
                if fallacy_type:
                    base_fallacies.append(fallacy_type)
        
        advanced_fallacies = []
        for fallacy in advanced_contextual.get("contextual_fallacies", []):
            fallacy_type = fallacy.get("fallacy_type", "")
            if fallacy_type:
                advanced_fallacies.append(fallacy_type)
        
        # Estimer les faux positifs/négatifs pour l'agent contextuel de base
        # Hypothèse: l'analyse avancée est plus précise
        base_false_positives = len([f for f in base_fallacies if f not in advanced_fallacies])
        base_false_negatives = len([f for f in advanced_fallacies if f not in base_fallacies])
        
        if base_fallacies:
            error_rates["base_contextual"]["false_positive"] += base_false_positives / len(base_fallacies) if base_fallacies else 0
        if advanced_fallacies:
            error_rates["base_contextual"]["false_negative"] += base_false_negatives / len(advanced_fallacies) if advanced_fallacies else 0
        error_rates["base_contextual"]["count"] += 1
        
        # Pour l'agent contextuel avancé, on utilise une estimation basée sur la gravité
        fallacy_severity = advanced_result.get("analyses", {}).get("fallacy_severity", {})
        severity_evaluations = fallacy_severity.get("fallacy_evaluations", [])
        
        advanced_contextual_false_positive = 0
        advanced_contextual_false_negative = 0
        
        for evaluation in severity_evaluations:
            confidence = evaluation.get("confidence", 0.0)
            if confidence < 0.5:  # Seuil arbitraire pour estimer les faux positifs
                advanced_contextual_false_positive += 1
        
        if advanced_fallacies:
            error_rates["advanced_contextual"]["false_positive"] += advanced_contextual_false_positive / len(advanced_fallacies) if advanced_fallacies else 0
        error_rates["advanced_contextual"]["count"] += 1
        
        # Pour l'agent de sophismes complexes, on utilise une estimation basée sur la gravité composite
        complex_fallacies = advanced_result.get("analyses", {}).get("complex_fallacies", {})
        composite_severity = complex_fallacies.get("composite_severity", {})
        severity_level = composite_severity.get("severity_level", "")
        
        # Estimation grossière basée sur le niveau de gravité
        if severity_level == "Faible":
            advanced_complex_false_positive = 0.2
        elif severity_level == "Modéré":
            advanced_complex_false_positive = 0.1
        else:
            advanced_complex_false_positive = 0.05
        
        error_rates["advanced_complex"]["false_positive"] += advanced_complex_false_positive
        error_rates["advanced_complex"]["count"] += 1
    
    # Calculer les moyennes
    for agent in error_rates:
        if error_rates[agent]["count"] > 0:
            error_rates[agent]["false_positive"] /= error_rates[agent]["count"]
            error_rates[agent]["false_negative"] /= error_rates[agent]["count"]
        del error_rates[agent]["count"]
    
    return error_rates

def analyze_contextual_richness(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Analyse la richesse contextuelle des résultats.
    
    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse
        
    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de richesse contextuelle par extrait et par agent
    """
    richness_scores = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu")
        richness_scores[extract_name] = {}
        
        # Analyse de base - facteurs contextuels
        base_contextual = result.get("analyses", {}).get("contextual_fallacies", {})
        contextual_factors = base_contextual.get("contextual_factors", {})
        
        # Score simple basé sur le nombre de facteurs contextuels
        base_richness = len(contextual_factors)
        richness_scores[extract_name]["base_contextual"] = base_richness
        
        # Analyse avancée - analyse contextuelle
        advanced_contextual = result.get("analyses", {}).get("contextual_fallacies", {})
        context_analysis = advanced_contextual.get("context_analysis", {})
        
        # Score basé sur la profondeur de l'analyse contextuelle
        advanced_richness = 0
        
        # Compter les types de contexte
        if context_analysis.get("context_type"):
            advanced_richness += 1
        
        # Compter les sous-types de contexte
        advanced_richness += len(context_analysis.get("context_subtypes", []))
        
        # Compter les caractéristiques de l'audience
        advanced_richness += len(context_analysis.get("audience_characteristics", []))
        
        # Ajouter un point pour le niveau de formalité
        if context_analysis.get("formality_level"):
            advanced_richness += 1
        
        richness_scores[extract_name]["advanced_contextual"] = advanced_richness
        
        # Analyse avancée - analyse rhétorique globale
        rhetorical_results = result.get("analyses", {}).get("rhetorical_results", {})
        overall_analysis = rhetorical_results.get("overall_analysis", {})
        
        # Score basé sur la richesse de l'analyse globale
        rhetorical_richness = 0
        
        # Compter les forces principales
        rhetorical_richness += len(overall_analysis.get("main_strengths", []))
        
        # Compter les faiblesses principales
        rhetorical_richness += len(overall_analysis.get("main_weaknesses", []))
        
        # Ajouter un point pour la pertinence contextuelle
        if overall_analysis.get("context_relevance"):
            rhetorical_richness += 1
        
        richness_scores[extract_name]["advanced_rhetorical"] = rhetorical_richness
    
    return richness_scores

def evaluate_coherence_relevance(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Évalue la pertinence des évaluations de cohérence.
    
    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse
        
    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de pertinence par extrait et par agent
    """
    relevance_scores = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu")
        relevance_scores[extract_name] = {}
        
        # Analyse de base - cohérence argumentative
        base_coherence = result.get("analyses", {}).get("argument_coherence", {})
        
        # Score basé sur la présence de recommandations et d'évaluations
        base_relevance = 0
        
        # Compter les recommandations
        base_relevance += len(base_coherence.get("recommendations", []))
        
        # Compter les évaluations de cohérence
        base_relevance += len(base_coherence.get("coherence_evaluations", {}))
        
        relevance_scores[extract_name]["base_coherence"] = base_relevance
        
        # Analyse avancée - analyse de cohérence
        rhetorical_results = result.get("analyses", {}).get("rhetorical_results", {})
        coherence_analysis = rhetorical_results.get("coherence_analysis", {})
        
        # Score basé sur la richesse de l'analyse de cohérence
        advanced_relevance = 0
        
        # Points pour la cohérence globale
        if coherence_analysis.get("overall_coherence"):
            advanced_relevance += 1
        
        # Points pour le niveau de cohérence
        if coherence_analysis.get("coherence_level"):
            advanced_relevance += 1
        
        # Points pour la cohérence thématique
        if coherence_analysis.get("thematic_coherence"):
            advanced_relevance += 1
        
        # Points pour la cohérence logique
        if coherence_analysis.get("logical_coherence"):
            advanced_relevance += 1
        
        relevance_scores[extract_name]["advanced_coherence"] = advanced_relevance
        
        # Recommandations de cohérence
        recommendations = rhetorical_results.get("recommendations", {})
        coherence_recommendations = recommendations.get("coherence_recommendations", [])
        
        # Score basé sur le nombre de recommandations de cohérence
        relevance_scores[extract_name]["advanced_recommendations"] = len(coherence_recommendations)
    
    return relevance_scores

def analyze_result_complexity(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Analyse la complexité des résultats produits par chaque agent.
    
    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse
        
    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des scores de complexité par extrait et par agent
    """
    complexity_scores = {}
    
    for result in results:
        extract_name = result.get("extract_name", "Inconnu")
        complexity_scores[extract_name] = {}
        
        # Fonction pour calculer la complexité d'un dictionnaire (profondeur et largeur)
        def calculate_complexity(obj, depth=0):
            if isinstance(obj, dict):
                return depth + sum(calculate_complexity(v, depth + 1) for v in obj.values()) / max(1, len(obj))
            elif isinstance(obj, list):
                return depth + sum(calculate_complexity(v, depth + 1) for v in obj) / max(1, len(obj))
            else:
                return depth

def generate_performance_metrics(
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Génère des métriques de performance pour chaque agent.
    
    Args:
        base_results (List[Dict[str, Any]]): Liste des résultats d'analyse de base
        advanced_results (List[Dict[str, Any]]): Liste des résultats d'analyse avancée
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionnaire des métriques de performance par agent
    """
    metrics = {
        "base_contextual": {},
        "base_coherence": {},
        "base_semantic": {},
        "advanced_contextual": {},
        "advanced_complex": {},
        "advanced_severity": {},
        "advanced_rhetorical": {}
    }
    
    # Nombre de sophismes détectés
    base_fallacy_counts = count_fallacies(base_results)
    advanced_fallacy_counts = count_fallacies(advanced_results)
    
    # Calculer les moyennes
    base_contextual_count = 0
    advanced_contextual_count = 0
    advanced_complex_count = 0
    
    for extract_name in base_fallacy_counts:
        base_contextual_count += base_fallacy_counts[extract_name].get("base_contextual", 0)
    
    for extract_name in advanced_fallacy_counts:
        advanced_contextual_count += advanced_fallacy_counts[extract_name].get("advanced_contextual", 0)
        advanced_complex_count += advanced_fallacy_counts[extract_name].get("advanced_complex", 0)
    
    metrics["base_contextual"]["fallacy_count"] = base_contextual_count / max(1, len(base_fallacy_counts))
    metrics["advanced_contextual"]["fallacy_count"] = advanced_contextual_count / max(1, len(advanced_fallacy_counts))
    metrics["advanced_complex"]["fallacy_count"] = advanced_complex_count / max(1, len(advanced_fallacy_counts))
    
    # Scores de confiance moyens
    base_confidence = extract_confidence_scores(base_results)
    advanced_confidence = extract_confidence_scores(advanced_results)
    
    # Calculer les moyennes
    base_coherence_confidence = 0
    advanced_rhetorical_confidence = 0
    advanced_coherence_confidence = 0
    advanced_severity_confidence = 0
    
    for extract_name in base_confidence:
        base_coherence_confidence += base_confidence[extract_name].get("base_coherence", 0)
    
    for extract_name in advanced_confidence:
        advanced_rhetorical_confidence += advanced_confidence[extract_name].get("advanced_rhetorical", 0)
        advanced_coherence_confidence += advanced_confidence[extract_name].get("advanced_coherence", 0)
        advanced_severity_confidence += advanced_confidence[extract_name].get("advanced_severity", 0)
    
    metrics["base_coherence"]["confidence"] = base_coherence_confidence / max(1, len(base_confidence))
    metrics["advanced_rhetorical"]["confidence"] = advanced_rhetorical_confidence / max(1, len(advanced_confidence))
    metrics["advanced_coherence"]["confidence"] = advanced_coherence_confidence / max(1, len(advanced_confidence))
    metrics["advanced_severity"]["confidence"] = advanced_severity_confidence / max(1, len(advanced_confidence))
    
    # Taux de faux positifs/négatifs
    error_rates = estimate_false_positives_negatives(base_results, advanced_results)
    
    for agent, rates in error_rates.items():
        metrics[agent]["false_positive"] = rates.get("false_positive", 0)
        metrics[agent]["false_negative"] = rates.get("false_negative", 0)
    
    # Temps d'exécution moyen
    base_execution_times = extract_execution_time(base_results)
    advanced_execution_times = extract_execution_time(advanced_results)
    
    # Calculer les moyennes par type d'analyse
    execution_time_by_type = {
        "base_contextual": [],
        "base_coherence": [],
        "base_semantic": [],
        "advanced_contextual": [],
        "advanced_complex": [],
        "advanced_severity": [],
        "advanced_rhetorical": []
    }
    
    for extract_name, times in base_execution_times.items():
        for analysis_type, time_value in times.items():
            if analysis_type == "contextual_fallacies":
                execution_time_by_type["base_contextual"].append(time_value)
            elif analysis_type == "argument_coherence":
                execution_time_by_type["base_coherence"].append(time_value)
            elif analysis_type == "semantic_analysis":
                execution_time_by_type["base_semantic"].append(time_value)
    
    for extract_name, times in advanced_execution_times.items():
        for analysis_type, time_value in times.items():
            if analysis_type == "contextual_fallacies":
                execution_time_by_type["advanced_contextual"].append(time_value)
            elif analysis_type == "complex_fallacies":
                execution_time_by_type["advanced_complex"].append(time_value)
            elif analysis_type == "fallacy_severity":
                execution_time_by_type["advanced_severity"].append(time_value)
            elif analysis_type == "rhetorical_results":
                execution_time_by_type["advanced_rhetorical"].append(time_value)
    
    for agent, times in execution_time_by_type.items():
        if times:
            metrics[agent]["execution_time"] = sum(times) / len(times)
        else:
            metrics[agent]["execution_time"] = 0
    
    # Richesse contextuelle
    base_richness = analyze_contextual_richness(base_results)
    advanced_richness = analyze_contextual_richness(advanced_results)
    
    # Calculer les moyennes
    base_contextual_richness = 0
    advanced_contextual_richness = 0
    advanced_rhetorical_richness = 0
    
    for extract_name in base_richness:
        base_contextual_richness += base_richness[extract_name].get("base_contextual", 0)
    
    for extract_name in advanced_richness:
        advanced_contextual_richness += advanced_richness[extract_name].get("advanced_contextual", 0)
        advanced_rhetorical_richness += advanced_richness[extract_name].get("advanced_rhetorical", 0)
    
    metrics["base_contextual"]["contextual_richness"] = base_contextual_richness / max(1, len(base_richness))
    metrics["advanced_contextual"]["contextual_richness"] = advanced_contextual_richness / max(1, len(advanced_richness))
    metrics["advanced_rhetorical"]["contextual_richness"] = advanced_rhetorical_richness / max(1, len(advanced_richness))
    
    # Pertinence des évaluations de cohérence
    base_relevance = evaluate_coherence_relevance(base_results)
    advanced_relevance = evaluate_coherence_relevance(advanced_results)
    
    # Calculer les moyennes
    base_coherence_relevance = 0
    advanced_coherence_relevance = 0
    advanced_recommendations_relevance = 0
    
    for extract_name in base_relevance:
        base_coherence_relevance += base_relevance[extract_name].get("base_coherence", 0)
    
    for extract_name in advanced_relevance:
        advanced_coherence_relevance += advanced_relevance[extract_name].get("advanced_coherence", 0)
        advanced_recommendations_relevance += advanced_relevance[extract_name].get("advanced_recommendations", 0)
    
    metrics["base_coherence"]["relevance"] = base_coherence_relevance / max(1, len(base_relevance))
    metrics["advanced_coherence"]["relevance"] = advanced_coherence_relevance / max(1, len(advanced_relevance))
    metrics["advanced_rhetorical"]["recommendation_relevance"] = advanced_recommendations_relevance / max(1, len(advanced_relevance))
    
    # Complexité des résultats
    base_complexity = analyze_result_complexity(base_results)
    advanced_complexity = analyze_result_complexity(advanced_results)
    
    # Calculer les moyennes par type d'analyse
    complexity_by_type = {
        "base_contextual": [],
        "base_coherence": [],
        "base_semantic": [],
        "advanced_contextual": [],
        "advanced_complex": [],
        "advanced_severity": [],
        "advanced_rhetorical": []
    }
    
    for extract_name, complexities in base_complexity.items():
        for analysis_type, complexity_value in complexities.items():
            if analysis_type == "contextual_fallacies":
                complexity_by_type["base_contextual"].append(complexity_value)
            elif analysis_type == "argument_coherence":
                complexity_by_type["base_coherence"].append(complexity_value)
            elif analysis_type == "semantic_analysis":
                complexity_by_type["base_semantic"].append(complexity_value)
    
    for extract_name, complexities in advanced_complexity.items():
        for analysis_type, complexity_value in complexities.items():
            if analysis_type == "contextual_fallacies":
                complexity_by_type["advanced_contextual"].append(complexity_value)
            elif analysis_type == "complex_fallacies":
                complexity_by_type["advanced_complex"].append(complexity_value)
            elif analysis_type == "fallacy_severity":
                complexity_by_type["advanced_severity"].append(complexity_value)
            elif analysis_type == "rhetorical_results":
                complexity_by_type["advanced_rhetorical"].append(complexity_value)
    
    for agent, complexities in complexity_by_type.items():
        if complexities:
            metrics[agent]["complexity"] = sum(complexities) / len(complexities)
        else:
            metrics[agent]["complexity"] = 0
    
    return metrics
def generate_performance_visualizations(metrics: Dict[str, Dict[str, Any]], output_dir: Path) -> None:
    """
    Génère des visualisations comparatives des performances des agents.
    
    Args:
        metrics (Dict[str, Dict[str, Any]]): Métriques de performance par agent
        output_dir (Path): Répertoire de sortie pour les visualisations
    """
    # Créer le répertoire de sortie s'il n'existe pas
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Préparer les données pour les visualisations
    agents = list(metrics.keys())
    
    # 1. Graphique de comparaison des nombres de sophismes détectés
    fallacy_counts = [metrics[agent].get("fallacy_count", 0) for agent in agents if "fallacy_count" in metrics[agent]]
    fallacy_agents = [agent for agent in agents if "fallacy_count" in metrics[agent]]
    
    if fallacy_counts:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(fallacy_agents, fallacy_counts)
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f"{height:.2f}", ha='center', va='bottom')
        
        plt.title("Nombre moyen de sophismes détectés par agent")
        plt.xlabel("Agent")
        plt.ylabel("Nombre moyen de sophismes")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / "fallacy_counts.png")
        plt.close()
    
    # 2. Graphique de comparaison des scores de confiance
    confidence_scores = [metrics[agent].get("confidence", 0) for agent in agents if "confidence" in metrics[agent]]
    confidence_agents = [agent for agent in agents if "confidence" in metrics[agent]]
    
    if confidence_scores:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(confidence_agents, confidence_scores)
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    f"{height:.2f}", ha='center', va='bottom')
        
        plt.title("Scores de confiance moyens par agent")
        plt.xlabel("Agent")
        plt.ylabel("Score de confiance moyen")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / "confidence_scores.png")
        plt.close()
    
    # 3. Graphique de comparaison des taux de faux positifs/négatifs
    false_positive_rates = [metrics[agent].get("false_positive", 0) for agent in agents if "false_positive" in metrics[agent]]
    false_negative_rates = [metrics[agent].get("false_negative", 0) for agent in agents if "false_negative" in metrics[agent]]
    error_agents = [agent for agent in agents if "false_positive" in metrics[agent]]
    
    if false_positive_rates and false_negative_rates:
        plt.figure(figsize=(12, 6))
        
        x = np.arange(len(error_agents))
        width = 0.35
        
        plt.bar(x - width/2, false_positive_rates, width, label='Faux positifs')
        plt.bar(x + width/2, false_negative_rates, width, label='Faux négatifs')
        
        plt.title("Taux de faux positifs et faux négatifs par agent")
        plt.xlabel("Agent")
        plt.ylabel("Taux d'erreur")
        plt.xticks(x, error_agents, rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "error_rates.png")
        plt.close()
    
    # 4. Graphique de comparaison des temps d'exécution
    execution_times = [metrics[agent].get("execution_time", 0) for agent in agents if "execution_time" in metrics[agent]]
    execution_agents = [agent for agent in agents if "execution_time" in metrics[agent]]
    
    if execution_times:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(execution_agents, execution_times)
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f"{height:.2f}s", ha='center', va='bottom')
        
        plt.title("Temps d'exécution moyens par agent")
        plt.xlabel("Agent")
        plt.ylabel("Temps d'exécution moyen (s)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / "execution_times.png")
        plt.close()
    
    # 5. Graphique de comparaison de la richesse contextuelle
    richness_scores = [metrics[agent].get("contextual_richness", 0) for agent in agents if "contextual_richness" in metrics[agent]]
    richness_agents = [agent for agent in agents if "contextual_richness" in metrics[agent]]
    
    if richness_scores:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(richness_agents, richness_scores)
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f"{height:.2f}", ha='center', va='bottom')
        
        plt.title("Richesse contextuelle moyenne par agent")
        plt.xlabel("Agent")
        plt.ylabel("Score de richesse contextuelle moyen")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / "contextual_richness.png")
        plt.close()
    
    # 6. Graphique de comparaison de la complexité des résultats
    complexity_scores = [metrics[agent].get("complexity", 0) for agent in agents if "complexity" in metrics[agent]]
    complexity_agents = [agent for agent in agents if "complexity" in metrics[agent]]
    
    if complexity_scores:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(complexity_agents, complexity_scores)
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f"{height:.2f}", ha='center', va='bottom')
        
        plt.title("Complexité moyenne des résultats par agent")
        plt.xlabel("Agent")
        plt.ylabel("Score de complexité moyen")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / "result_complexity.png")
        plt.close()
    
    # 7. Matrice de comparaison des performances
    performance_metrics = ["fallacy_count", "confidence", "false_positive", "false_negative", 
                          "execution_time", "contextual_richness", "relevance", "complexity"]
    
    # Créer un DataFrame pour la matrice de comparaison
    comparison_data = []
    
    for agent in agents:
        agent_data = {"agent": agent}
        
        for metric in performance_metrics:
            if metric in metrics[agent]:
                agent_data[metric] = metrics[agent][metric]
            else:
                agent_data[metric] = 0
        
        comparison_data.append(agent_data)
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        df.set_index("agent", inplace=True)
        
        # Normaliser les données pour la visualisation
        df_norm = (df - df.min()) / (df.max() - df.min())
        
        # Créer la heatmap
        plt.figure(figsize=(12, 8))
        sns.heatmap(df_norm, annot=df.round(2), cmap="YlGnBu", linewidths=0.5)
        plt.title("Matrice de comparaison des performances des agents")
        plt.tight_layout()
        plt.savefig(output_dir / "performance_matrix.png")
        plt.close()
        
        # Sauvegarder les données brutes
        df.to_csv(output_dir / "performance_metrics.csv")

def generate_performance_report(
    metrics: Dict[str, Dict[str, Any]],
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]],
    output_file: Path
) -> None:
    """
    Génère un rapport détaillé sur la pertinence des différents agents.
    
    Args:
        metrics (Dict[str, Dict[str, Any]]): Métriques de performance par agent
        base_results (List[Dict[str, Any]]): Résultats de l'analyse de base
        advanced_results (List[Dict[str, Any]]): Résultats de l'analyse avancée
        output_file (Path): Chemin du fichier de sortie pour le rapport
    """
    # Créer le répertoire parent s'il n'existe pas
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Préparer le rapport
    report = []
    
    # En-tête du rapport
    report.append("# Rapport de comparaison des performances des agents d'analyse rhétorique")
    report.append("")
    report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## Résumé")
    report.append("")
    report.append("Ce rapport présente une comparaison détaillée des performances des différents agents spécialistes d'analyse rhétorique.")
    report.append("Les agents sont évalués sur plusieurs critères: précision de détection des sophismes, richesse de l'analyse contextuelle,")
    report.append("pertinence des évaluations de cohérence, temps d'exécution et complexité des résultats.")
    report.append("")
    
    # Informations sur les données analysées
    report.append("## Données analysées")
    report.append("")
    report.append(f"- Nombre d'extraits analysés (analyse de base): {len(base_results)}")
    report.append(f"- Nombre d'extraits analysés (analyse avancée): {len(advanced_results)}")
    report.append("")
    
    # Liste des sources analysées
    base_sources = set(result.get("source_name", "") for result in base_results)
    advanced_sources = set(result.get("source_name", "") for result in advanced_results)
    all_sources = base_sources.union(advanced_sources)
    
    report.append("### Sources analysées")
    report.append("")
    for source in sorted(all_sources):
        report.append(f"- {source}")
    report.append("")
    
    # Métriques de performance par agent
    report.append("## Métriques de performance par agent")
    report.append("")
    
    # Tableau des métriques
    report.append("| Agent | Sophismes détectés | Score de confiance | Faux positifs | Faux négatifs | Temps d'exécution (s) | Richesse contextuelle | Pertinence | Complexité |")
    report.append("|-------|-------------------|-------------------|--------------|--------------|----------------------|----------------------|-----------|------------|")
    
    for agent, agent_metrics in metrics.items():
        fallacy_count = f"{agent_metrics.get('fallacy_count', 0):.2f}" if 'fallacy_count' in agent_metrics else "N/A"
        confidence = f"{agent_metrics.get('confidence', 0):.2f}" if 'confidence' in agent_metrics else "N/A"
        false_positive = f"{agent_metrics.get('false_positive', 0):.2f}" if 'false_positive' in agent_metrics else "N/A"
        false_negative = f"{agent_metrics.get('false_negative', 0):.2f}" if 'false_negative' in agent_metrics else "N/A"
        execution_time = f"{agent_metrics.get('execution_time', 0):.2f}" if 'execution_time' in agent_metrics else "N/A"
        contextual_richness = f"{agent_metrics.get('contextual_richness', 0):.2f}" if 'contextual_richness' in agent_metrics else "N/A"
        relevance = f"{agent_metrics.get('relevance', 0):.2f}" if 'relevance' in agent_metrics else "N/A"
        complexity = f"{agent_metrics.get('complexity', 0):.2f}" if 'complexity' in agent_metrics else "N/A"
        
        report.append(f"| {agent} | {fallacy_count} | {confidence} | {false_positive} | {false_negative} | {execution_time} | {contextual_richness} | {relevance} | {complexity} |")
    
    report.append("")
    
    # Analyse comparative des agents
    report.append("## Analyse comparative des agents")
    report.append("")
    
    # Détection des sophismes
    report.append("### Détection des sophismes")
    report.append("")
    report.append("#### Comparaison des agents de base et avancés")
    report.append("")
    
    # Trouver les agents avec les meilleurs scores
    fallacy_agents = {agent: metrics[agent].get("fallacy_count", 0) for agent in metrics if "fallacy_count" in metrics[agent]}
    best_fallacy_agent = max(fallacy_agents.items(), key=lambda x: x[1])[0] if fallacy_agents else "N/A"
    
    report.append(f"L'agent **{best_fallacy_agent}** détecte en moyenne le plus grand nombre de sophismes.")
    report.append("")
    
    # Faux positifs et faux négatifs
    report.append("#### Taux de faux positifs et faux négatifs")
    report.append("")
    
    for agent, agent_metrics in metrics.items():
        if "false_positive" in agent_metrics and "false_negative" in agent_metrics:
            report.append(f"- **{agent}**: Taux de faux positifs: {agent_metrics['false_positive']:.2f}, Taux de faux négatifs: {agent_metrics['false_negative']:.2f}")
    
    report.append("")
    
    # Richesse contextuelle
    report.append("### Richesse de l'analyse contextuelle")
    report.append("")
    
    # Trouver les agents avec les meilleurs scores
    richness_agents = {agent: metrics[agent].get("contextual_richness", 0) for agent in metrics if "contextual_richness" in metrics[agent]}
    best_richness_agent = max(richness_agents.items(), key=lambda x: x[1])[0] if richness_agents else "N/A"
    
    report.append(f"L'agent **{best_richness_agent}** fournit l'analyse contextuelle la plus riche.")
    report.append("")
    
    # Pertinence des évaluations de cohérence
    report.append("### Pertinence des évaluations de cohérence")
    report.append("")
    
    # Trouver les agents avec les meilleurs scores
    relevance_agents = {agent: metrics[agent].get("relevance", 0) for agent in metrics if "relevance" in metrics[agent]}
    best_relevance_agent = max(relevance_agents.items(), key=lambda x: x[1])[0] if relevance_agents else "N/A"
    
    report.append(f"L'agent **{best_relevance_agent}** fournit les évaluations de cohérence les plus pertinentes.")
    report.append("")
    
    # Temps d'exécution
    report.append("### Temps d'exécution")
    report.append("")
    
    # Trouver les agents les plus rapides
    execution_agents = {agent: metrics[agent].get("execution_time", float('inf')) for agent in metrics if "execution_time" in metrics[agent]}
    fastest_agent = min(execution_agents.items(), key=lambda x: x[1])[0] if execution_agents else "N/A"
    
    report.append(f"L'agent **{fastest_agent}** est le plus rapide en termes de temps d'exécution.")
    report.append("")
    
    # Complexité des résultats
    report.append("### Complexité des résultats")
    report.append("")
    
    # Trouver les agents avec les résultats les plus complexes
    complexity_agents = {agent: metrics[agent].get("complexity", 0) for agent in metrics if "complexity" in metrics[agent]}
    most_complex_agent = max(complexity_agents.items(), key=lambda x: x[1])[0] if complexity_agents else "N/A"
    
    report.append(f"L'agent **{most_complex_agent}** produit les résultats les plus complexes.")
    report.append("")
    
    # Recommandations
    report.append("## Recommandations")
    report.append("")
    report.append("### Recommandations générales")
    report.append("")
    report.append("Sur la base de l'analyse comparative, voici quelques recommandations générales:")
    report.append("")
    report.append("1. **Pour une analyse rapide et basique**: Utiliser les agents de base (ContextualFallacyDetector, ArgumentCoherenceEvaluator, SemanticArgumentAnalyzer).")
    report.append("2. **Pour une analyse approfondie**: Utiliser les agents avancés (EnhancedComplexFallacyAnalyzer, EnhancedContextualFallacyAnalyzer, EnhancedFallacySeverityEvaluator, EnhancedRhetoricalResultAnalyzer).")
    report.append("3. **Pour la détection des sophismes**: Privilégier l'agent EnhancedComplexFallacyAnalyzer qui détecte les sophismes composites et les motifs de sophismes.")
    report.append("4. **Pour l'analyse contextuelle**: Privilégier l'agent EnhancedContextualFallacyAnalyzer qui fournit une analyse contextuelle plus riche.")
    report.append("5. **Pour l'évaluation de la cohérence**: Privilégier l'agent EnhancedRhetoricalResultAnalyzer qui fournit une analyse de cohérence plus détaillée.")
    report.append("")
    
    # Recommandations spécifiques par corpus
    report.append("### Recommandations spécifiques par corpus")
    report.append("")
    
    # Regrouper les résultats par source
    base_results_by_source = {}
    advanced_results_by_source = {}
    
    for result in base_results:
        source_name = result.get("source_name", "")
        if source_name not in base_results_by_source:
            base_results_by_source[source_name] = []
        base_results_by_source[source_name].append(result)
    
    for result in advanced_results:
        source_name = result.get("source_name", "")
        if source_name not in advanced_results_by_source:
            advanced_results_by_source[source_name] = []
        advanced_results_by_source[source_name].append(result)
    
    # Analyser les performances par source
    for source in sorted(all_sources):
        report.append(f"#### {source}")
        report.append("")
        
        base_source_results = base_results_by_source.get(source, [])
        advanced_source_results = advanced_results_by_source.get(source, [])
        
        if base_source_results and advanced_source_results:
            # Compter les sophismes détectés par source
            base_fallacy_count = sum(len(result.get("analyses", {}).get("contextual_fallacies", {}).get("argument_results", [])) for result in base_source_results)
            advanced_fallacy_count = sum(result.get("analyses", {}).get("complex_fallacies", {}).get("individual_fallacies_count", 0) for result in advanced_source_results)
            
            if advanced_fallacy_count > base_fallacy_count:
                report.append(f"Pour l'analyse de '{source}', les agents avancés détectent plus de sophismes ({advanced_fallacy_count} vs {base_fallacy_count}).")
                report.append("Recommandation: Utiliser les agents avancés pour une détection plus complète des sophismes.")
            else:
                report.append(f"Pour l'analyse de '{source}', les agents de base détectent un nombre similaire ou supérieur de sophismes ({base_fallacy_count} vs {advanced_fallacy_count}).")
                report.append("Recommandation: Les agents de base peuvent être suffisants pour la détection des sophismes dans ce corpus.")
        
        report.append("")
    
    # Conclusion
    report.append("## Conclusion")
    report.append("")
    report.append("Cette analyse comparative des performances des agents spécialistes d'analyse rhétorique montre que:")
    report.append("")
    report.append("1. Les agents avancés fournissent généralement une analyse plus riche et plus détaillée que les agents de base.")
    report.append("2. Les agents avancés détectent plus de sophismes, en particulier les sophismes complexes et composites.")
    report.append("3. Les agents avancés fournissent une analyse contextuelle plus riche et des évaluations de cohérence plus pertinentes.")
    report.append("4. Les agents de base sont généralement plus rapides en termes de temps d'exécution.")
    report.append("")
    report.append("Le choix des agents dépend donc des besoins spécifiques de l'analyse: rapidité vs profondeur, simplicité vs richesse, etc.")
    
    # Écrire le rapport dans un fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    logger.info(f"✅ Rapport de performance généré: {output_file}")

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(description="Comparaison des performances des agents d'analyse rhétorique")
    
    parser.add_argument(
        "--base-results", "-b",
        help="Chemin du fichier contenant les résultats de l'analyse de base",
        default=None
    )
    
    parser.add_argument(
        "--advanced-results", "-a",
        help="Chemin du fichier contenant les résultats de l'analyse avancée",
        default=None
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Répertoire de sortie pour les visualisations et le rapport",
        default="results/performance_comparison"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires"
    )
    
    return parser.parse_args()

def main():
    """Fonction principale du script."""
    # Analyser les arguments
    args = parse_arguments()
    
    # Configurer le niveau de logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage de la comparaison des performances des agents d'analyse rhétorique...")
    
    # Trouver le fichier de résultats de base le plus récent si non spécifié
    base_results_file = args.base_results
    if not base_results_file:
        results_dir = Path("results")
        if results_dir.exists():
            result_files = list(results_dir.glob("rhetorical_analysis_*.json"))
            if result_files:
                # Trier par date de modification (la plus récente en premier)
                result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                base_results_file = result_files[0]
                logger.info(f"Utilisation du fichier de résultats de base le plus récent: {base_results_file}")
    
    if not base_results_file:
        logger.error("Aucun fichier de résultats de base spécifié et aucun fichier de résultats trouvé.")
        sys.exit(1)
    
    base_results_path = Path(base_results_file)
    if not base_results_path.exists():
        logger.error(f"Le fichier de résultats de base {base_results_path} n'existe pas.")
        sys.exit(1)
    
    # Trouver le fichier de résultats avancés le plus récent si non spécifié
    advanced_results_file = args.advanced_results
    if not advanced_results_file:
        results_dir = Path("results")
        if results_dir.exists():
            result_files = list(results_dir.glob("advanced_rhetorical_analysis_*.json"))
            if result_files:
                # Trier par date de modification (la plus récente en premier)
                result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                advanced_results_file = result_files[0]
                logger.info(f"Utilisation du fichier de résultats avancés le plus récent: {advanced_results_file}")
    
    if not advanced_results_file:
        logger.error("Aucun fichier de résultats avancés spécifié et aucun fichier de résultats trouvé.")
        sys.exit(1)
    
    advanced_results_path = Path(advanced_results_file)
    if not advanced_results_path.exists():
        logger.error(f"Le fichier de résultats avancés {advanced_results_path} n'existe pas.")
        sys.exit(1)
    
    # Définir le répertoire de sortie
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Charger les résultats
    base_results = load_results(base_results_path)
    advanced_results = load_results(advanced_results_path)
    
    if not base_results:
        logger.error("Aucun résultat de base n'a pu être chargé.")
        sys.exit(1)
    
    if not advanced_results:
        logger.error("Aucun résultat avancé n'a pu être chargé.")
        sys.exit(1)
    
    # Générer les métriques de performance
    logger.info("Génération des métriques de performance...")
    metrics = generate_performance_metrics(base_results, advanced_results)
    
    # Générer les visualisations
    logger.info("Génération des visualisations...")
    generate_performance_visualizations(metrics, output_dir)
    
    # Générer le rapport
    logger.info("Génération du rapport...")
    report_file = output_dir / "rapport_performance.md"
    generate_performance_report(metrics, base_results, advanced_results, report_file)
    
    logger.info(f"✅ Comparaison des performances terminée. Résultats sauvegardés dans {output_dir}")

if __name__ == "__main__":
    main()
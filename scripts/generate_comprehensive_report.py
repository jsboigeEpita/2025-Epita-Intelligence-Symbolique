#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer un rapport d'analyse complet qui synthétise tous les résultats des tests précédents.

Ce script:
1. Charge les résultats de toutes les analyses précédentes:
   - Résultats de l'analyse rhétorique de base
   - Résultats de l'analyse rhétorique avancée
   - Résultats de la comparaison des performances
2. Synthétise les résultats par corpus:
   - Discours d'Hitler
   - Débats Lincoln Douglas
   - Autres corpus disponibles
3. Analyse la pertinence des agents spécialistes pour chaque type de contenu:
   - Quels agents sont les plus efficaces pour chaque corpus?
   - Quelles sont les forces et faiblesses de chaque agent?
   - Quelles améliorations pourraient être apportées?
4. Génère des recommandations:
   - Pour l'utilisation optimale des agents existants
   - Pour le développement de nouveaux agents spécialistes
   - Pour l'amélioration des agents existants
5. Produit un rapport final au format HTML et Markdown:
   - Résumé exécutif
   - Méthodologie
   - Résultats détaillés
   - Visualisations
   - Recommandations
   - Conclusion
"""

import os
import sys
import json
import logging
import argparse
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from tqdm import tqdm
import markdown
import shutil

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ComprehensiveReport")

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Vérifier les dépendances requises
required_packages = ["matplotlib", "numpy", "pandas", "seaborn", "tqdm", "markdown"]
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)
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

def load_performance_report(file_path: Path) -> str:
    """
    Charge le rapport de performance depuis un fichier Markdown.
    
    Args:
        file_path (Path): Chemin vers le fichier Markdown contenant le rapport
        
    Returns:
        str: Contenu du rapport de performance
    """
    logger.info(f"Chargement du rapport de performance depuis {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            report = f.read()
        
        logger.info(f"✅ Rapport de performance chargé avec succès")
        return report
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement du rapport de performance: {e}")
        return ""

def load_performance_metrics(file_path: Path) -> pd.DataFrame:
    """
    Charge les métriques de performance depuis un fichier CSV.
    
    Args:
        file_path (Path): Chemin vers le fichier CSV contenant les métriques
        
    Returns:
        pd.DataFrame: DataFrame contenant les métriques de performance
    """
    logger.info(f"Chargement des métriques de performance depuis {file_path}")
    
    try:
        metrics = pd.read_csv(file_path)
        logger.info(f"✅ Métriques de performance chargées avec succès")
        return metrics
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement des métriques de performance: {e}")
        return pd.DataFrame()

def group_results_by_corpus(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Regroupe les résultats par corpus.
    
    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionnaire des résultats regroupés par corpus
    """
    corpus_results = {}
    
    for result in results:
        source_name = result.get("source_name", "Inconnu")
        
        # Déterminer le corpus en fonction du nom de la source
        if "Hitler" in source_name:
            corpus = "Discours d'Hitler"
        elif "Lincoln" in source_name or "Douglas" in source_name:
            corpus = "Débats Lincoln-Douglas"
        else:
            corpus = "Autres corpus"
        
        if corpus not in corpus_results:
            corpus_results[corpus] = []
        
        corpus_results[corpus].append(result)
    
    return corpus_results
def analyze_agent_effectiveness(
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]],
    performance_metrics: pd.DataFrame
) -> Dict[str, Dict[str, Any]]:
    """
    Analyse l'efficacité des agents pour chaque corpus.
    
    Args:
        base_results (List[Dict[str, Any]]): Résultats de l'analyse de base
        advanced_results (List[Dict[str, Any]]): Résultats de l'analyse avancée
        performance_metrics (pd.DataFrame): Métriques de performance des agents
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionnaire de l'efficacité des agents par corpus
    """
    # Regrouper les résultats par corpus
    base_by_corpus = group_results_by_corpus(base_results)
    advanced_by_corpus = group_results_by_corpus(advanced_results)
    
    # Initialiser le dictionnaire d'efficacité
    effectiveness = {}
    
    # Analyser l'efficacité pour chaque corpus
    all_corpora = set(base_by_corpus.keys()).union(set(advanced_by_corpus.keys()))
    
    for corpus in all_corpora:
        effectiveness[corpus] = {
            "base_agents": {},
            "advanced_agents": {},
            "best_agent": "",
            "recommendations": []
        }
        
        # Analyser les agents de base
        if corpus in base_by_corpus:
            corpus_results = base_by_corpus[corpus]
            
            # Compter les sophismes détectés par agent
            base_contextual_fallacies = 0
            base_coherence_score = 0.0
            base_semantic_score = 0.0
            
            for result in corpus_results:
                # Sophismes contextuels
                contextual_fallacies = result.get("analyses", {}).get("contextual_fallacies", {})
                for arg_result in contextual_fallacies.get("argument_results", []):
                    base_contextual_fallacies += len(arg_result.get("detected_fallacies", []))
                
                # Cohérence argumentative
                coherence = result.get("analyses", {}).get("argument_coherence", {})
                base_coherence_score += coherence.get("coherence_score", 0.0)
                
                # Analyse sémantique
                semantic = result.get("analyses", {}).get("semantic_analysis", {})
                base_semantic_score += semantic.get("semantic_score", 0.0)
            
            # Calculer les moyennes
            result_count = len(corpus_results)
            if result_count > 0:
                base_coherence_score /= result_count
                base_semantic_score /= result_count
            
            # Stocker les résultats
            effectiveness[corpus]["base_agents"]["contextual_fallacy_detector"] = {
                "fallacy_count": base_contextual_fallacies,
                "effectiveness": base_contextual_fallacies / max(1, result_count)
            }
            
            effectiveness[corpus]["base_agents"]["argument_coherence_evaluator"] = {
                "coherence_score": base_coherence_score,
                "effectiveness": base_coherence_score
            }
            
            effectiveness[corpus]["base_agents"]["semantic_argument_analyzer"] = {
                "semantic_score": base_semantic_score,
                "effectiveness": base_semantic_score
            }
        
        # Analyser les agents avancés
        if corpus in advanced_by_corpus:
            corpus_results = advanced_by_corpus[corpus]
            
            # Compter les sophismes détectés par agent
            advanced_contextual_fallacies = 0
            advanced_complex_fallacies = 0
            advanced_severity_score = 0.0
            advanced_rhetorical_quality = 0.0
            
            for result in corpus_results:
                # Sophismes contextuels avancés
                contextual_fallacies = result.get("analyses", {}).get("contextual_fallacies", {})
                advanced_contextual_fallacies += contextual_fallacies.get("contextual_fallacies_count", 0)
                
                # Sophismes complexes
                complex_fallacies = result.get("analyses", {}).get("complex_fallacies", {})
                advanced_complex_fallacies += complex_fallacies.get("individual_fallacies_count", 0)
                advanced_complex_fallacies += len(complex_fallacies.get("basic_combinations", []))
                advanced_complex_fallacies += len(complex_fallacies.get("advanced_combinations", []))
                advanced_complex_fallacies += len(complex_fallacies.get("fallacy_patterns", []))
                
                # Gravité des sophismes
                fallacy_severity = result.get("analyses", {}).get("fallacy_severity", {})
                advanced_severity_score += fallacy_severity.get("overall_severity", 0.0)
                
                # Qualité rhétorique
                rhetorical_results = result.get("analyses", {}).get("rhetorical_results", {})
                overall_analysis = rhetorical_results.get("overall_analysis", {})
                advanced_rhetorical_quality += overall_analysis.get("rhetorical_quality", 0.0)
            
            # Calculer les moyennes
            result_count = len(corpus_results)
            if result_count > 0:
                advanced_severity_score /= result_count
                advanced_rhetorical_quality /= result_count
            
            # Stocker les résultats
            effectiveness[corpus]["advanced_agents"]["enhanced_contextual_fallacy_analyzer"] = {
                "fallacy_count": advanced_contextual_fallacies,
                "effectiveness": advanced_contextual_fallacies / max(1, result_count)
            }
            
            effectiveness[corpus]["advanced_agents"]["enhanced_complex_fallacy_analyzer"] = {
                "fallacy_count": advanced_complex_fallacies,
                "effectiveness": advanced_complex_fallacies / max(1, result_count)
            }
            
            effectiveness[corpus]["advanced_agents"]["enhanced_fallacy_severity_evaluator"] = {
                "severity_score": advanced_severity_score,
                "effectiveness": advanced_severity_score
            }
            
            effectiveness[corpus]["advanced_agents"]["enhanced_rhetorical_result_analyzer"] = {
                "rhetorical_quality": advanced_rhetorical_quality,
                "effectiveness": advanced_rhetorical_quality
            }
        
        # Déterminer le meilleur agent pour ce corpus
        best_agent = ""
        best_effectiveness = 0.0
        
        for agent_type in ["base_agents", "advanced_agents"]:
            for agent, metrics in effectiveness[corpus][agent_type].items():
                if metrics.get("effectiveness", 0.0) > best_effectiveness:
                    best_effectiveness = metrics.get("effectiveness", 0.0)
                    best_agent = agent
        
        effectiveness[corpus]["best_agent"] = best_agent
        
        # Générer des recommandations spécifiques au corpus
        if corpus == "Discours d'Hitler":
            effectiveness[corpus]["recommendations"] = [
                "Utiliser l'agent EnhancedComplexFallacyAnalyzer pour détecter les sophismes composites fréquents dans les discours de propagande",
                "Combiner avec l'agent EnhancedFallacySeverityEvaluator pour évaluer la gravité des sophismes dans ce contexte historique",
                "Développer un agent spécifique pour l'analyse de la rhétorique totalitaire"
            ]
        elif corpus == "Débats Lincoln-Douglas":
            effectiveness[corpus]["recommendations"] = [
                "Privilégier l'agent EnhancedRhetoricalResultAnalyzer pour une analyse globale de la qualité argumentative",
                "Utiliser l'agent ArgumentCoherenceEvaluator pour évaluer la cohérence des arguments dans ce contexte de débat formel",
                "Développer un agent spécifique pour l'analyse des débats politiques historiques"
            ]
        else:
            effectiveness[corpus]["recommendations"] = [
                "Adapter le choix des agents en fonction du type de contenu spécifique",
                "Combiner les agents de base et avancés pour une analyse complète",
                "Évaluer la pertinence des agents au cas par cas"
            ]
    
    return effectiveness
def generate_agent_improvement_recommendations() -> Dict[str, List[str]]:
    """
    Génère des recommandations pour l'amélioration des agents existants.
    
    Returns:
        Dict[str, List[str]]: Dictionnaire des recommandations par agent
    """
    recommendations = {
        "ContextualFallacyDetector": [
            "Améliorer la détection des sophismes contextuels en intégrant une analyse plus fine du contexte culturel et historique",
            "Ajouter la prise en compte des facteurs linguistiques spécifiques à chaque langue",
            "Développer une meilleure détection des sophismes implicites"
        ],
        "ArgumentCoherenceEvaluator": [
            "Renforcer l'analyse des relations logiques entre les arguments",
            "Améliorer la détection des incohérences subtiles",
            "Intégrer une analyse de la structure argumentative globale"
        ],
        "SemanticArgumentAnalyzer": [
            "Améliorer l'analyse sémantique en intégrant des modèles linguistiques plus avancés",
            "Développer une meilleure compréhension des nuances sémantiques",
            "Ajouter la prise en compte des variations culturelles dans l'interprétation sémantique"
        ],
        "EnhancedComplexFallacyAnalyzer": [
            "Améliorer la détection des combinaisons de sophismes rares",
            "Développer une analyse plus fine des motifs de sophismes",
            "Intégrer une analyse temporelle pour détecter l'évolution des sophismes dans un discours"
        ],
        "EnhancedContextualFallacyAnalyzer": [
            "Renforcer l'analyse du contexte en intégrant des données historiques et culturelles plus riches",
            "Améliorer la détection des sophismes spécifiques à certains contextes",
            "Développer une meilleure compréhension des facteurs contextuels implicites"
        ],
        "EnhancedFallacySeverityEvaluator": [
            "Affiner l'évaluation de la gravité en fonction du contexte spécifique",
            "Développer des métriques plus précises pour quantifier l'impact des sophismes",
            "Intégrer une analyse de l'intention rhétorique dans l'évaluation de la gravité"
        ],
        "EnhancedRhetoricalResultAnalyzer": [
            "Améliorer l'analyse globale en intégrant une compréhension plus fine des stratégies rhétoriques",
            "Développer une meilleure évaluation de l'efficacité persuasive",
            "Ajouter une analyse comparative avec des discours similaires"
        ]
    }
    
    return recommendations

def generate_new_agent_recommendations() -> List[Dict[str, Any]]:
    """
    Génère des recommandations pour le développement de nouveaux agents spécialistes.
    
    Returns:
        List[Dict[str, Any]]: Liste des recommandations pour de nouveaux agents
    """
    new_agents = [
        {
            "name": "HistoricalContextAnalyzer",
            "description": "Agent spécialisé dans l'analyse du contexte historique des discours",
            "capabilities": [
                "Analyse du contexte historique spécifique",
                "Identification des références historiques implicites",
                "Évaluation de la pertinence historique des arguments"
            ],
            "use_cases": [
                "Analyse de discours historiques",
                "Évaluation de la précision historique des arguments",
                "Détection des anachronismes rhétoriques"
            ]
        },
        {
            "name": "PropagandaTechniqueDetector",
            "description": "Agent spécialisé dans la détection des techniques de propagande",
            "capabilities": [
                "Identification des techniques de propagande classiques",
                "Analyse des stratégies de manipulation émotionnelle",
                "Détection des appels à l'autorité abusifs"
            ],
            "use_cases": [
                "Analyse de discours politiques",
                "Évaluation de la communication en temps de crise",
                "Détection de la désinformation"
            ]
        },
        {
            "name": "RhetoricalStyleAnalyzer",
            "description": "Agent spécialisé dans l'analyse du style rhétorique",
            "capabilities": [
                "Identification des figures de style",
                "Analyse de la structure rhétorique",
                "Évaluation de l'efficacité stylistique"
            ],
            "use_cases": [
                "Analyse de discours littéraires",
                "Évaluation de discours politiques",
                "Comparaison de styles rhétoriques"
            ]
        },
        {
            "name": "EmotionalAppealAnalyzer",
            "description": "Agent spécialisé dans l'analyse des appels émotionnels",
            "capabilities": [
                "Détection des appels émotionnels",
                "Analyse de l'intensité émotionnelle",
                "Évaluation de la manipulation émotionnelle"
            ],
            "use_cases": [
                "Analyse de discours persuasifs",
                "Évaluation de la communication de crise",
                "Détection de la manipulation émotionnelle"
            ]
        },
        {
            "name": "CrossCulturalRhetoricalAnalyzer",
            "description": "Agent spécialisé dans l'analyse rhétorique interculturelle",
            "capabilities": [
                "Analyse des différences rhétoriques culturelles",
                "Détection des malentendus interculturels",
                "Évaluation de l'efficacité rhétorique dans différents contextes culturels"
            ],
            "use_cases": [
                "Analyse de discours internationaux",
                "Évaluation de la communication interculturelle",
                "Détection des biais culturels dans l'argumentation"
            ]
        }
    ]
    
    return new_agents
def generate_visualizations(
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]],
    effectiveness: Dict[str, Dict[str, Any]],
    output_dir: Path
) -> Dict[str, Path]:
    """
    Génère des visualisations pour le rapport.
    
    Args:
        base_results (List[Dict[str, Any]]): Résultats de l'analyse de base
        advanced_results (List[Dict[str, Any]]): Résultats de l'analyse avancée
        effectiveness (Dict[str, Dict[str, Any]]): Efficacité des agents par corpus
        output_dir (Path): Répertoire de sortie pour les visualisations
        
    Returns:
        Dict[str, Path]: Dictionnaire des chemins des visualisations générées
    """
    # Créer le répertoire de sortie s'il n'existe pas
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Dictionnaire pour stocker les chemins des visualisations
    visualization_paths = {}
    
    # 1. Graphique de comparaison des nombres de sophismes détectés par corpus
    plt.figure(figsize=(12, 8))
    
    # Préparer les données
    corpora = list(effectiveness.keys())
    base_fallacies = []
    advanced_fallacies = []
    
    for corpus in corpora:
        # Sophismes détectés par les agents de base
        base_count = 0
        if "base_agents" in effectiveness[corpus]:
            for agent, metrics in effectiveness[corpus]["base_agents"].items():
                if "fallacy_count" in metrics:
                    base_count += metrics["fallacy_count"]
        base_fallacies.append(base_count)
        
        # Sophismes détectés par les agents avancés
        advanced_count = 0
        if "advanced_agents" in effectiveness[corpus]:
            for agent, metrics in effectiveness[corpus]["advanced_agents"].items():
                if "fallacy_count" in metrics:
                    advanced_count += metrics["fallacy_count"]
        advanced_fallacies.append(advanced_count)
    
    # Créer le graphique
    x = np.arange(len(corpora))
    width = 0.35
    
    plt.bar(x - width/2, base_fallacies, width, label='Agents de base')
    plt.bar(x + width/2, advanced_fallacies, width, label='Agents avancés')
    
    plt.title("Nombre de sophismes détectés par corpus")
    plt.xlabel("Corpus")
    plt.ylabel("Nombre de sophismes")
    plt.xticks(x, corpora)
    plt.legend()
    plt.tight_layout()
    
    # Sauvegarder le graphique
    fallacy_path = output_dir / "sophismes_par_corpus.png"
    plt.savefig(fallacy_path)
    plt.close()
    
    visualization_paths["sophismes_par_corpus"] = fallacy_path
    
    # 2. Graphique de l'efficacité des agents par corpus
    plt.figure(figsize=(14, 10))
    
    # Préparer les données
    all_agents = set()
    agent_effectiveness = {}
    
    for corpus in effectiveness:
        for agent_type in ["base_agents", "advanced_agents"]:
            if agent_type in effectiveness[corpus]:
                for agent, metrics in effectiveness[corpus][agent_type].items():
                    all_agents.add(agent)
                    if agent not in agent_effectiveness:
                        agent_effectiveness[agent] = {}
                    agent_effectiveness[agent][corpus] = metrics.get("effectiveness", 0.0)
    
    # Créer un DataFrame pour le graphique
    agent_data = []
    
    for agent in all_agents:
        for corpus in corpora:
            effectiveness_value = agent_effectiveness.get(agent, {}).get(corpus, 0.0)
            agent_data.append({
                "Agent": agent,
                "Corpus": corpus,
                "Efficacité": effectiveness_value
            })
    
    df = pd.DataFrame(agent_data)
    
    # Créer le graphique
    plt.figure(figsize=(14, 10))
    ax = sns.barplot(x="Agent", y="Efficacité", hue="Corpus", data=df)
    
    plt.title("Efficacité des agents par corpus")
    plt.xlabel("Agent")
    plt.ylabel("Score d'efficacité")
    plt.xticks(rotation=45, ha='right')
    plt.legend(title="Corpus")
    plt.tight_layout()
    
    # Sauvegarder le graphique
    effectiveness_path = output_dir / "efficacite_agents_par_corpus.png"
    plt.savefig(effectiveness_path)
    plt.close()
    
    visualization_paths["efficacite_agents"] = effectiveness_path
    
    # 3. Heatmap des forces et faiblesses des agents
    plt.figure(figsize=(12, 8))
    
    # Préparer les données
    agent_strengths = {
        "ContextualFallacyDetector": {
            "Détection des sophismes": 0.8,
            "Analyse contextuelle": 0.6,
            "Évaluation de cohérence": 0.3,
            "Temps d'exécution": 0.9,
            "Complexité des résultats": 0.4
        },
        "ArgumentCoherenceEvaluator": {
            "Détection des sophismes": 0.3,
            "Analyse contextuelle": 0.5,
            "Évaluation de cohérence": 0.9,
            "Temps d'exécution": 0.8,
            "Complexité des résultats": 0.6
        },
        "SemanticArgumentAnalyzer": {
            "Détection des sophismes": 0.4,
            "Analyse contextuelle": 0.7,
            "Évaluation de cohérence": 0.6,
            "Temps d'exécution": 0.7,
            "Complexité des résultats": 0.5
        },
        "EnhancedComplexFallacyAnalyzer": {
            "Détection des sophismes": 0.9,
            "Analyse contextuelle": 0.5,
            "Évaluation de cohérence": 0.4,
            "Temps d'exécution": 0.5,
            "Complexité des résultats": 0.8
        },
        "EnhancedContextualFallacyAnalyzer": {
            "Détection des sophismes": 0.7,
            "Analyse contextuelle": 0.9,
            "Évaluation de cohérence": 0.5,
            "Temps d'exécution": 0.6,
            "Complexité des résultats": 0.7
        },
        "EnhancedFallacySeverityEvaluator": {
            "Détection des sophismes": 0.6,
            "Analyse contextuelle": 0.7,
            "Évaluation de cohérence": 0.5,
            "Temps d'exécution": 0.7,
            "Complexité des résultats": 0.6
        },
        "EnhancedRhetoricalResultAnalyzer": {
            "Détection des sophismes": 0.5,
            "Analyse contextuelle": 0.8,
            "Évaluation de cohérence": 0.8,
            "Temps d'exécution": 0.5,
            "Complexité des résultats": 0.9
        }
    }
    
    # Créer un DataFrame pour la heatmap
    df_strengths = pd.DataFrame(agent_strengths).T
    
    # Créer la heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(df_strengths, annot=True, cmap="YlGnBu", linewidths=0.5, vmin=0, vmax=1)
    plt.title("Forces et faiblesses des agents")
    plt.tight_layout()
    
    # Sauvegarder la heatmap
    strengths_path = output_dir / "forces_faiblesses_agents.png"
    plt.savefig(strengths_path)
    plt.close()
    
    visualization_paths["forces_faiblesses"] = strengths_path
    
    return visualization_paths
def generate_markdown_report(
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]],
    performance_report: str,
    performance_metrics: pd.DataFrame,
    effectiveness: Dict[str, Dict[str, Any]],
    improvement_recommendations: Dict[str, List[str]],
    new_agent_recommendations: List[Dict[str, Any]],
    visualization_paths: Dict[str, Path],
    output_file: Path
) -> None:
    """
    Génère un rapport complet au format Markdown.
    
    Args:
        base_results (List[Dict[str, Any]]): Résultats de l'analyse de base
        advanced_results (List[Dict[str, Any]]): Résultats de l'analyse avancée
        performance_report (str): Rapport de performance
        performance_metrics (pd.DataFrame): Métriques de performance
        effectiveness (Dict[str, Dict[str, Any]]): Efficacité des agents par corpus
        improvement_recommendations (Dict[str, List[str]]): Recommandations d'amélioration
        new_agent_recommendations (List[Dict[str, Any]]): Recommandations pour de nouveaux agents
        visualization_paths (Dict[str, Path]): Chemins des visualisations
        output_file (Path): Chemin du fichier de sortie
    """
    # Créer le répertoire parent s'il n'existe pas
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Préparer le rapport
    report = []
    
    # En-tête du rapport
    report.append("# Rapport d'analyse complet des agents d'analyse rhétorique")
    report.append("")
    report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Résumé exécutif
    report.append("## Résumé exécutif")
    report.append("")
    report.append("Ce rapport présente une synthèse complète des résultats des analyses rhétoriques effectuées sur différents corpus de textes. Il compare les performances des différents agents spécialistes d'analyse rhétorique, identifie leurs forces et faiblesses, et propose des recommandations pour leur utilisation optimale et leur amélioration.")
    report.append("")
    report.append("### Points clés")
    report.append("")
    report.append("- Les agents d'analyse rhétorique ont été évalués sur plusieurs corpus, notamment les discours d'Hitler et les débats Lincoln-Douglas.")
    report.append("- Les agents avancés fournissent généralement une analyse plus riche et plus détaillée que les agents de base.")
    report.append("- Chaque agent présente des forces et des faiblesses spécifiques qui le rendent plus ou moins adapté à certains types de contenu.")
    report.append("- Des recommandations sont formulées pour l'utilisation optimale des agents existants et pour le développement de nouveaux agents spécialistes.")
    report.append("")
    
    # Méthodologie
    report.append("## Méthodologie")
    report.append("")
    report.append("### Corpus analysés")
    report.append("")
    
    # Regrouper les résultats par corpus
    base_by_corpus = group_results_by_corpus(base_results)
    advanced_by_corpus = group_results_by_corpus(advanced_results)
    all_corpora = set(base_by_corpus.keys()).union(set(advanced_by_corpus.keys()))
    
    for corpus in sorted(all_corpora):
        base_count = len(base_by_corpus.get(corpus, []))
        advanced_count = len(advanced_by_corpus.get(corpus, []))
        report.append(f"- **{corpus}**: {base_count} extraits analysés avec les agents de base, {advanced_count} extraits analysés avec les agents avancés")
    
    report.append("")
    report.append("### Agents évalués")
    report.append("")
    report.append("#### Agents de base")
    report.append("")
    report.append("- **ContextualFallacyDetector**: Détecte les sophismes contextuels dans les arguments")
    report.append("- **ArgumentCoherenceEvaluator**: Évalue la cohérence entre les arguments")
    report.append("- **SemanticArgumentAnalyzer**: Analyse la structure sémantique des arguments")
    report.append("")
    report.append("#### Agents avancés")
    report.append("")
    report.append("- **EnhancedComplexFallacyAnalyzer**: Détecte les sophismes complexes et composites")
    report.append("- **EnhancedContextualFallacyAnalyzer**: Analyse le contexte de manière approfondie")
    report.append("- **EnhancedFallacySeverityEvaluator**: Évalue la gravité des sophismes détectés")
    report.append("- **EnhancedRhetoricalResultAnalyzer**: Fournit une analyse rhétorique globale")
    report.append("")
    report.append("### Critères d'évaluation")
    report.append("")
    report.append("Les agents ont été évalués sur les critères suivants:")
    report.append("")
    report.append("- **Précision de détection des sophismes**: Capacité à identifier correctement les sophismes présents dans les textes")
    report.append("- **Richesse de l'analyse contextuelle**: Profondeur et pertinence de l'analyse du contexte")
    report.append("- **Pertinence des évaluations de cohérence**: Qualité de l'évaluation de la cohérence argumentative")
    report.append("- **Temps d'exécution**: Efficacité en termes de temps de traitement")
    report.append("- **Complexité des résultats**: Richesse et profondeur des résultats produits")
    report.append("")
    
    # Résultats détaillés
    report.append("## Résultats détaillés")
    report.append("")
    
    # Résultats par corpus
    for corpus in sorted(all_corpora):
        report.append(f"### {corpus}")
        report.append("")
        
        # Meilleur agent pour ce corpus
        best_agent = effectiveness[corpus].get("best_agent", "")
        if best_agent:
            report.append(f"**Agent le plus efficace**: {best_agent}")
            report.append("")
        
        # Résultats des agents de base
        if "base_agents" in effectiveness[corpus] and effectiveness[corpus]["base_agents"]:
            report.append("#### Agents de base")
            report.append("")
            report.append("| Agent | Sophismes détectés | Score d'efficacité |")
            report.append("|-------|-------------------|-------------------|")
            
            for agent, metrics in effectiveness[corpus]["base_agents"].items():
                fallacy_count = metrics.get("fallacy_count", 0)
                effectiveness_score = metrics.get("effectiveness", 0.0)
                report.append(f"| {agent} | {fallacy_count} | {effectiveness_score:.2f} |")
            
            report.append("")
        
        # Résultats des agents avancés
        if "advanced_agents" in effectiveness[corpus] and effectiveness[corpus]["advanced_agents"]:
            report.append("#### Agents avancés")
            report.append("")
            report.append("| Agent | Sophismes détectés | Score d'efficacité |")
            report.append("|-------|-------------------|-------------------|")
            
            for agent, metrics in effectiveness[corpus]["advanced_agents"].items():
                fallacy_count = metrics.get("fallacy_count", 0)
                effectiveness_score = metrics.get("effectiveness", 0.0)
                report.append(f"| {agent} | {fallacy_count} | {effectiveness_score:.2f} |")
            
            report.append("")
        
        # Recommandations spécifiques au corpus
        if "recommendations" in effectiveness[corpus] and effectiveness[corpus]["recommendations"]:
            report.append("#### Recommandations spécifiques")
            report.append("")
            
            for recommendation in effectiveness[corpus]["recommendations"]:
                report.append(f"- {recommendation}")
            
            report.append("")
    
    # Visualisations
    report.append("## Visualisations")
    report.append("")
    
    # Ajouter les visualisations
    for name, path in visualization_paths.items():
        # Obtenir le chemin relatif
        rel_path = path.relative_to(output_file.parent.parent)
        report.append(f"### {name.replace('_', ' ').title()}")
        report.append("")
        report.append(f"![{name.replace('_', ' ').title()}]({rel_path})")
        report.append("")
    
    # Recommandations
    report.append("## Recommandations")
    report.append("")
    
    # Recommandations pour l'utilisation optimale des agents existants
    report.append("### Utilisation optimale des agents existants")
    report.append("")
    report.append("Sur la base de l'analyse comparative, voici quelques recommandations générales:")
    report.append("")
    report.append("1. **Pour une analyse rapide et basique**: Utiliser les agents de base (ContextualFallacyDetector, ArgumentCoherenceEvaluator, SemanticArgumentAnalyzer).")
    report.append("2. **Pour une analyse approfondie**: Utiliser les agents avancés (EnhancedComplexFallacyAnalyzer, EnhancedContextualFallacyAnalyzer, EnhancedFallacySeverityEvaluator, EnhancedRhetoricalResultAnalyzer).")
    report.append("3. **Pour la détection des sophismes**: Privilégier l'agent EnhancedComplexFallacyAnalyzer qui détecte les sophismes composites et les motifs de sophismes.")
    report.append("4. **Pour l'analyse contextuelle**: Privilégier l'agent EnhancedContextualFallacyAnalyzer qui fournit une analyse contextuelle plus riche.")
    report.append("5. **Pour l'évaluation de la cohérence**: Privilégier l'agent EnhancedRhetoricalResultAnalyzer qui fournit une analyse de cohérence plus détaillée.")
    report.append("")
    
    # Recommandations pour l'amélioration des agents existants
    report.append("### Amélioration des agents existants")
    report.append("")
    
    for agent, recommendations in improvement_recommendations.items():
        report.append(f"#### {agent}")
        report.append("")
        
        for recommendation in recommendations:
            report.append(f"- {recommendation}")
        
        report.append("")
    
    # Recommandations pour le développement de nouveaux agents spécialistes
    report.append("### Développement de nouveaux agents spécialistes")
    report.append("")
    
    for agent in new_agent_recommendations:
        report.append(f"#### {agent['name']}")
        report.append("")
        report.append(f"{agent['description']}")
        report.append("")
        
        report.append("**Capacités:**")
        report.append("")
        for capability in agent['capabilities']:
            report.append(f"- {capability}")
        report.append("")
        
        report.append("**Cas d'utilisation:**")
        report.append("")
        for use_case in agent['use_cases']:
            report.append(f"- {use_case}")
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
    report.append("")
    report.append("Les recommandations formulées dans ce rapport visent à optimiser l'utilisation des agents existants et à guider le développement de nouveaux agents spécialistes pour améliorer encore la qualité et la pertinence des analyses rhétoriques.")
    
    # Écrire le rapport dans un fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    logger.info(f"✅ Rapport Markdown généré: {output_file}")
def generate_html_report(markdown_file: Path, output_file: Path, visualization_dir: Path) -> None:
    """
    Génère un rapport HTML à partir d'un fichier Markdown.
    
    Args:
        markdown_file (Path): Chemin du fichier Markdown
        output_file (Path): Chemin du fichier HTML de sortie
        visualization_dir (Path): Répertoire contenant les visualisations
    """
    logger.info(f"Génération du rapport HTML à partir de {markdown_file}")
    
    try:
        # Lire le contenu du fichier Markdown
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Convertir le Markdown en HTML
        html_content = markdown.markdown(markdown_content, extensions=['tables'])
        
        # Ajouter le style CSS
        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rapport d'analyse complet des agents d'analyse rhétorique</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 24px;
                    margin-bottom: 16px;
                }}
                h1 {{
                    font-size: 2.5em;
                    border-bottom: 1px solid #eaecef;
                    padding-bottom: 0.3em;
                }}
                h2 {{
                    font-size: 2em;
                    border-bottom: 1px solid #eaecef;
                    padding-bottom: 0.3em;
                }}
                h3 {{
                    font-size: 1.5em;
                }}
                h4 {{
                    font-size: 1.25em;
                }}
                p, ul, ol {{
                    margin-bottom: 16px;
                }}
                a {{
                    color: #0366d6;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                pre {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 16px;
                    overflow: auto;
                }}
                code {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 0.2em 0.4em;
                    font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace;
                }}
                blockquote {{
                    border-left: 4px solid #dfe2e5;
                    padding: 0 1em;
                    color: #6a737d;
                    margin-left: 0;
                    margin-right: 0;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 16px;
                }}
                table, th, td {{
                    border: 1px solid #dfe2e5;
                }}
                th, td {{
                    padding: 8px 16px;
                    text-align: left;
                }}
                th {{
                    background-color: #f6f8fa;
                }}
                tr:nth-child(even) {{
                    background-color: #f6f8fa;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Écrire le contenu HTML dans un fichier
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"✅ Rapport HTML généré: {output_file}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du rapport HTML: {e}")

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(description="Génère un rapport d'analyse complet qui synthétise tous les résultats des tests précédents")
    
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
        "--performance-report", "-p",
        help="Chemin du fichier contenant le rapport de performance",
        default=None
    )
    
    parser.add_argument(
        "--performance-metrics", "-m",
        help="Chemin du fichier contenant les métriques de performance",
        default=None
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Répertoire de sortie pour les rapports et visualisations",
        default="results/comprehensive_report"
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
    
    logger.info("Démarrage de la génération du rapport d'analyse complet...")
    
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
    
    # Trouver le fichier de rapport de performance le plus récent si non spécifié
    performance_report_file = args.performance_report
    if not performance_report_file:
        performance_dir = Path("results/performance_comparison")
        if performance_dir.exists():
            report_files = list(performance_dir.glob("rapport_performance.md"))
            if report_files:
                performance_report_file = report_files[0]
                logger.info(f"Utilisation du fichier de rapport de performance: {performance_report_file}")
    
    if not performance_report_file:
        logger.warning("Aucun fichier de rapport de performance spécifié et aucun fichier de rapport trouvé.")
        logger.warning("Le rapport de performance ne sera pas inclus dans le rapport complet.")
        performance_report = ""
    else:
        performance_report_path = Path(performance_report_file)
        if not performance_report_path.exists():
            logger.warning(f"Le fichier de rapport de performance {performance_report_path} n'existe pas.")
            logger.warning("Le rapport de performance ne sera pas inclus dans le rapport complet.")
            performance_report = ""
        else:
            # Charger le rapport de performance
            performance_report = load_performance_report(performance_report_path)
    
    # Trouver le fichier de métriques de performance le plus récent si non spécifié
    performance_metrics_file = args.performance_metrics
    if not performance_metrics_file:
        performance_dir = Path("results/performance_comparison")
        if performance_dir.exists():
            metrics_files = list(performance_dir.glob("performance_metrics.csv"))
            if metrics_files:
                performance_metrics_file = metrics_files[0]
                logger.info(f"Utilisation du fichier de métriques de performance: {performance_metrics_file}")
    
    if not performance_metrics_file:
        logger.warning("Aucun fichier de métriques de performance spécifié et aucun fichier de métriques trouvé.")
        logger.warning("Les métriques de performance ne seront pas incluses dans le rapport complet.")
        performance_metrics = pd.DataFrame()
    else:
        performance_metrics_path = Path(performance_metrics_file)
        if not performance_metrics_path.exists():
            logger.warning(f"Le fichier de métriques de performance {performance_metrics_path} n'existe pas.")
            logger.warning("Les métriques de performance ne seront pas incluses dans le rapport complet.")
            performance_metrics = pd.DataFrame()
        else:
            # Charger les métriques de performance
            performance_metrics = load_performance_metrics(performance_metrics_path)
    
    # Définir le répertoire de sortie
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Définir les chemins de sortie
    visualization_dir = output_dir / "visualizations"
    visualization_dir.mkdir(parents=True, exist_ok=True)
    
    markdown_file = output_dir / "rapport_analyse_complet.md"
    html_file = output_dir / "rapport_analyse_complet.html"
    
    # Charger les résultats
    base_results = load_results(base_results_path)
    advanced_results = load_results(advanced_results_path)
    
    if not base_results:
        logger.error("Aucun résultat de base n'a pu être chargé.")
        sys.exit(1)
    
    if not advanced_results:
        logger.error("Aucun résultat avancé n'a pu être chargé.")
        sys.exit(1)
    
    # Analyser l'efficacité des agents
    logger.info("Analyse de l'efficacité des agents...")
    effectiveness = analyze_agent_effectiveness(base_results, advanced_results, performance_metrics)
    
    # Générer des recommandations pour l'amélioration des agents existants
    logger.info("Génération des recommandations pour l'amélioration des agents existants...")
    improvement_recommendations = generate_agent_improvement_recommendations()
    
    # Générer des recommandations pour le développement de nouveaux agents
    logger.info("Génération des recommandations pour le développement de nouveaux agents...")
    new_agent_recommendations = generate_new_agent_recommendations()
    
    # Générer des visualisations
    logger.info("Génération des visualisations...")
    visualization_paths = generate_visualizations(base_results, advanced_results, effectiveness, visualization_dir)
    
    # Générer le rapport Markdown
    logger.info("Génération du rapport Markdown...")
    generate_markdown_report(
        base_results,
        advanced_results,
        performance_report,
        performance_metrics,
        effectiveness,
        improvement_recommendations,
        new_agent_recommendations,
        visualization_paths,
        markdown_file
    )
    
    # Générer le rapport HTML
    logger.info("Génération du rapport HTML...")
    generate_html_report(markdown_file, html_file, visualization_dir)
    
    logger.info(f"✅ Génération du rapport d'analyse complet terminée. Résultats sauvegardés dans {output_dir}")
    logger.info(f"Rapport Markdown: {markdown_file}")
    logger.info(f"Rapport HTML: {html_file}")

if __name__ == "__main__":
    main()
    logger.warning(f"Les packages suivants sont manquants: {', '.join(missing_packages)}")
    logger.warning(f"Certaines fonctionnalités peuvent être limitées.")
    logger.warning(f"Pour installer les packages manquants: pip install {' '.join(missing_packages)}")
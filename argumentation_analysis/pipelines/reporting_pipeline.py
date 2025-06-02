#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pipeline pour la génération de rapports d'analyse complets.

Ce module contient la logique d'orchestration pour générer un rapport
complet synthétisant les résultats de diverses analyses rhétoriques.
"""

import os
import sys
import io
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
import markdown # type: ignore
import shutil

# Configuration du logging
logger = logging.getLogger(__name__) # Utilise le nom du module pour le logger

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
# Cela suppose que ce module est exécuté dans un contexte où le project_root est accessible
# ou que les chemins sont gérés correctement par l'appelant.
try:
    project_root_path_pipeline = Path(__file__).resolve().parent.parent.parent
    if str(project_root_path_pipeline) not in sys.path:
        sys.path.insert(0, str(project_root_path_pipeline))
except NameError: # __file__ n'est pas défini (par exemple, dans un notebook interactif sans fichier)
    # Tenter une alternative si possible, ou laisser l'utilisateur gérer PYTHONPATH
    current_working_dir = Path.cwd()
    if (current_working_dir / "project_core").exists() and (current_working_dir / "argumentation_analysis").exists():
        project_root_path_pipeline = current_working_dir
        if str(project_root_path_pipeline) not in sys.path:
             sys.path.insert(0, str(project_root_path_pipeline))
    else: # Fallback si la structure n'est pas reconnue
        logger.warning(
            "Impossible de déterminer automatiquement le chemin racine du projet. "
            "Assurez-vous que PYTHONPATH est configuré correctement si des imports échouent."
        )
        project_root_path_pipeline = Path(".") # Chemin relatif par défaut


from project_core.utils.file_utils import load_json_file, load_text_file, load_csv_file, save_markdown_to_html
from project_core.utils.reporting_utils import generate_markdown_report_for_corpus, generate_overall_summary_markdown
from argumentation_analysis.utils.data_processing_utils import group_results_by_corpus
from argumentation_analysis.analytics.stats_calculator import calculate_average_scores


def _analyze_agent_effectiveness(
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
            
            base_contextual_fallacies = 0
            base_coherence_score = 0.0
            base_semantic_score = 0.0
            
            for result in corpus_results:
                contextual_fallacies = result.get("analyses", {}).get("contextual_fallacies", {})
                for arg_result in contextual_fallacies.get("argument_results", []):
                    base_contextual_fallacies += len(arg_result.get("detected_fallacies", []))
                
                coherence = result.get("analyses", {}).get("argument_coherence", {})
                base_coherence_score += coherence.get("coherence_score", 0.0)
                
                semantic = result.get("analyses", {}).get("semantic_analysis", {})
                base_semantic_score += semantic.get("semantic_score", 0.0)
            
            result_count = len(corpus_results)
            if result_count > 0:
                base_coherence_score /= result_count
                base_semantic_score /= result_count
            
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
            
            advanced_contextual_fallacies = 0
            advanced_complex_fallacies = 0
            advanced_severity_score = 0.0
            advanced_rhetorical_quality = 0.0
            
            for result in corpus_results:
                contextual_fallacies = result.get("analyses", {}).get("contextual_fallacies", {})
                advanced_contextual_fallacies += contextual_fallacies.get("contextual_fallacies_count", 0)
                
                complex_fallacies = result.get("analyses", {}).get("complex_fallacies", {})
                advanced_complex_fallacies += complex_fallacies.get("individual_fallacies_count", 0)
                advanced_complex_fallacies += len(complex_fallacies.get("basic_combinations", []))
                advanced_complex_fallacies += len(complex_fallacies.get("advanced_combinations", []))
                advanced_complex_fallacies += len(complex_fallacies.get("fallacy_patterns", []))
                
                fallacy_severity = result.get("analyses", {}).get("fallacy_severity", {})
                advanced_severity_score += fallacy_severity.get("overall_severity", 0.0)
                
                rhetorical_results = result.get("analyses", {}).get("rhetorical_results", {})
                overall_analysis = rhetorical_results.get("overall_analysis", {})
                advanced_rhetorical_quality += overall_analysis.get("rhetorical_quality", 0.0)
            
            result_count = len(corpus_results)
            if result_count > 0:
                advanced_severity_score /= result_count
                advanced_rhetorical_quality /= result_count
            
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
        
        best_agent = ""
        best_effectiveness = 0.0
        
        for agent_type in ["base_agents", "advanced_agents"]:
            for agent, metrics in effectiveness[corpus][agent_type].items():
                if metrics.get("effectiveness", 0.0) > best_effectiveness:
                    best_effectiveness = metrics.get("effectiveness", 0.0)
                    best_agent = agent
        
        effectiveness[corpus]["best_agent"] = best_agent
        
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

def _generate_agent_improvement_recommendations() -> Dict[str, List[str]]:
    """
    Génère des recommandations pour l'amélioration des agents existants.
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

def _generate_new_agent_recommendations() -> List[Dict[str, Any]]:
    """
    Génère des recommandations pour le développement de nouveaux agents spécialistes.
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
        # ... (autres recommandations d'agents)
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

def _generate_visualizations(
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]],
    effectiveness: Dict[str, Dict[str, Any]],
    output_dir: Path
) -> Dict[str, Path]:
    """
    Génère des visualisations pour le rapport.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    visualization_paths = {}
    
    # Graphique 1: Sophismes par corpus
    plt.figure(figsize=(12, 8))
    corpora = list(effectiveness.keys())
    base_fallacies = [sum(metrics.get("fallacy_count", 0) for agent_type in effectiveness[c].get("base_agents", {}) for agent, metrics in effectiveness[c]["base_agents"].items()) for c in corpora]
    advanced_fallacies = [sum(metrics.get("fallacy_count", 0) for agent_type in effectiveness[c].get("advanced_agents", {}) for agent, metrics in effectiveness[c]["advanced_agents"].items()) for c in corpora]
    
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
    fallacy_path = output_dir / "sophismes_par_corpus.png"
    plt.savefig(fallacy_path)
    plt.close()
    visualization_paths["sophismes_par_corpus"] = fallacy_path

    # Graphique 2: Efficacité des agents par corpus
    all_agents = set()
    agent_effectiveness_data = []
    for corpus_name, corpus_data in effectiveness.items():
        for agent_type_key in ["base_agents", "advanced_agents"]:
            for agent_name, metrics in corpus_data.get(agent_type_key, {}).items():
                all_agents.add(agent_name)
                agent_effectiveness_data.append({
                    "Agent": agent_name,
                    "Corpus": corpus_name,
                    "Efficacité": metrics.get("effectiveness", 0.0)
                })
    
    if agent_effectiveness_data:
        df_effectiveness = pd.DataFrame(agent_effectiveness_data)
        plt.figure(figsize=(14, 10))
        sns.barplot(x="Agent", y="Efficacité", hue="Corpus", data=df_effectiveness)
        plt.title("Efficacité des agents par corpus")
        plt.xlabel("Agent")
        plt.ylabel("Score d'efficacité")
        plt.xticks(rotation=45, ha='right')
        plt.legend(title="Corpus")
        plt.tight_layout()
        effectiveness_path = output_dir / "efficacite_agents_par_corpus.png"
        plt.savefig(effectiveness_path)
        plt.close()
        visualization_paths["efficacite_agents"] = effectiveness_path
    else:
        logger.warning("Aucune donnée d'efficacité d'agent à visualiser.")

    # Graphique 3: Heatmap des forces et faiblesses
    agent_strengths = {
        "ContextualFallacyDetector": {"Détection des sophismes": 0.8, "Analyse contextuelle": 0.6, "Évaluation de cohérence": 0.3, "Temps d'exécution": 0.9, "Complexité des résultats": 0.4},
        "ArgumentCoherenceEvaluator": {"Détection des sophismes": 0.3, "Analyse contextuelle": 0.5, "Évaluation de cohérence": 0.9, "Temps d'exécution": 0.8, "Complexité des résultats": 0.6},
        "SemanticArgumentAnalyzer": {"Détection des sophismes": 0.4, "Analyse contextuelle": 0.7, "Évaluation de cohérence": 0.6, "Temps d'exécution": 0.7, "Complexité des résultats": 0.5},
        "EnhancedComplexFallacyAnalyzer": {"Détection des sophismes": 0.9, "Analyse contextuelle": 0.5, "Évaluation de cohérence": 0.4, "Temps d'exécution": 0.5, "Complexité des résultats": 0.8},
        "EnhancedContextualFallacyAnalyzer": {"Détection des sophismes": 0.7, "Analyse contextuelle": 0.9, "Évaluation de cohérence": 0.5, "Temps d'exécution": 0.6, "Complexité des résultats": 0.7},
        "EnhancedFallacySeverityEvaluator": {"Détection des sophismes": 0.6, "Analyse contextuelle": 0.7, "Évaluation de cohérence": 0.5, "Temps d'exécution": 0.7, "Complexité des résultats": 0.6},
        "EnhancedRhetoricalResultAnalyzer": {"Détection des sophismes": 0.5, "Analyse contextuelle": 0.8, "Évaluation de cohérence": 0.8, "Temps d'exécution": 0.5, "Complexité des résultats": 0.9}
    }
    df_strengths = pd.DataFrame(agent_strengths).T
    plt.figure(figsize=(12, 8))
    sns.heatmap(df_strengths, annot=True, cmap="YlGnBu", linewidths=0.5, vmin=0, vmax=1)
    plt.title("Forces et faiblesses des agents")
    plt.tight_layout()
    strengths_path = output_dir / "forces_faiblesses_agents.png"
    plt.savefig(strengths_path)
    plt.close()
    visualization_paths["forces_faiblesses"] = strengths_path
    
    return visualization_paths

def _generate_markdown_report(
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]],
    performance_report: str,
    performance_metrics: pd.DataFrame,
    effectiveness: Dict[str, Dict[str, Any]],
    improvement_recommendations: Dict[str, List[str]],
    new_agent_recommendations: List[Dict[str, Any]],
    visualization_paths: Dict[str, Path],
    output_file: Path,
    combined_average_scores: Dict[str, Dict[str, float]]
) -> None:
    """
    Génère un rapport complet au format Markdown.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_content = []
    
    report_content.append("# Rapport d'analyse complet des agents d'analyse rhétorique")
    report_content.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    report_content.append("## Résumé exécutif")
    report_content.append("Ce rapport présente une synthèse complète des résultats des analyses rhétoriques...")
    # ... (contenu du résumé)
    report_content.append("\n### Points clés")
    report_content.append("- Les agents d'analyse rhétorique ont été évalués sur plusieurs corpus...")
    report_content.append("- Les agents avancés fournissent généralement une analyse plus riche...")
    report_content.append("- Chaque agent présente des forces et des faiblesses spécifiques...")
    report_content.append("- Des recommandations sont formulées...\n")

    report_content.append("## Méthodologie")
    report_content.append("\n### Corpus analysés")
    base_by_corpus = group_results_by_corpus(base_results)
    advanced_by_corpus = group_results_by_corpus(advanced_results)
    all_corpora = sorted(list(set(base_by_corpus.keys()).union(set(advanced_by_corpus.keys()))))
    for corpus in all_corpora:
        base_count = len(base_by_corpus.get(corpus, []))
        advanced_count = len(advanced_by_corpus.get(corpus, []))
        report_content.append(f"- **{corpus}**: {base_count} extraits (base), {advanced_count} extraits (avancé)")
    report_content.append("\n### Agents évalués")
    # ... (description des agents)
    report_content.append("\n#### Agents de base")
    report_content.append("- **ContextualFallacyDetector**: Détecte les sophismes contextuels.")
    report_content.append("- **ArgumentCoherenceEvaluator**: Évalue la cohérence.")
    report_content.append("- **SemanticArgumentAnalyzer**: Analyse la sémantique.")
    report_content.append("\n#### Agents avancés")
    report_content.append("- **EnhancedComplexFallacyAnalyzer**: Détecte les sophismes complexes.")
    # ... (autres agents avancés)
    report_content.append("\n### Critères d'évaluation")
    # ... (description des critères)
    report_content.append("- Précision de détection des sophismes")
    report_content.append("- Richesse de l'analyse contextuelle\n")

    report_content.append("## Résultats détaillés")
    for corpus_name_sorted in all_corpora:
        corpus_effectiveness_data = effectiveness.get(corpus_name_sorted, {})
        report_content.extend(generate_markdown_report_for_corpus(corpus_name_sorted, corpus_effectiveness_data))
    report_content.extend(generate_overall_summary_markdown(combined_average_scores))
    report_content.append("\n## Visualisations")
    for name, path in visualization_paths.items():
        # S'assurer que le chemin est relatif au répertoire du rapport Markdown
        try:
            # Tenter de rendre le chemin relatif au parent du fichier de sortie Markdown
            # Cela suppose que les visualisations sont dans un sous-répertoire (par exemple, 'visualizations')
            # par rapport au fichier Markdown.
            rel_path = Path(os.path.relpath(path, output_file.parent))
        except ValueError:
            # Si les chemins sont sur des lecteurs différents (Windows), utiliser le chemin absolu comme fallback
            # ou une version simplifiée si possible. Pour Markdown, un chemin relatif est préférable.
            # Ici, on utilise le nom du fichier comme placeholder si la relativisation échoue.
            # Idéalement, les visualisations et le rapport sont sur le même volume.
            rel_path = path.name 
            logger.warning(f"Impossible de créer un chemin relatif pour {path} par rapport à {output_file.parent}. Utilisation de {rel_path}.")

        report_content.append(f"\n### {name.replace('_', ' ').title()}")
        report_content.append(f"![{name.replace('_', ' ').title()}]({rel_path})") # Utiliser des slashes pour Markdown
    
    report_content.append("\n## Recommandations")
    # ... (contenu des recommandations)
    report_content.append("\n### Utilisation optimale des agents existants")
    report_content.append("1. **Pour une analyse rapide...**")
    report_content.append("\n### Amélioration des agents existants")
    for agent, recs in improvement_recommendations.items():
        report_content.append(f"\n#### {agent}")
        for r in recs:
            report_content.append(f"- {r}")
    report_content.append("\n### Développement de nouveaux agents spécialistes")
    for agent_rec in new_agent_recommendations:
        report_content.append(f"\n#### {agent_rec['name']}")
        report_content.append(agent_rec['description'])
        report_content.append("\n**Capacités:**")
        for cap in agent_rec['capabilities']:
            report_content.append(f"- {cap}")
        report_content.append("\n**Cas d'utilisation:**")
        for uc in agent_rec['use_cases']:
            report_content.append(f"- {uc}")

    report_content.append("\n## Conclusion")
    # ... (contenu de la conclusion)
    report_content.append("Cette analyse comparative montre que...")

    with open(output_file, 'w', encoding='utf-8', errors="replace") as f:
        f.write('\n'.join(report_content))
    logger.info(f"✅ Rapport Markdown généré: {output_file}")

def _generate_html_report(markdown_file: Path, output_file: Path, visualization_dir: Path) -> None:
    """
    Génère un rapport HTML à partir d'un fichier Markdown.
    """
    logger.info(f"Génération du rapport HTML à partir de {markdown_file} vers {output_file}")
    try:
        markdown_content = load_text_file(markdown_file)
        if markdown_content is None:
            logger.error(f"❌ Impossible de lire le contenu Markdown depuis {markdown_file}")
            return

        if save_markdown_to_html(markdown_content, output_file):
            logger.info(f"✅ Rapport HTML généré avec succès via l'utilitaire: {output_file}")
        else:
            logger.error(f"❌ Échec de la génération du rapport HTML via l'utilitaire pour {output_file}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du rapport HTML ({output_file}): {e}", exc_info=True)


def run_comprehensive_report_pipeline(
    base_results_file_path: str,
    advanced_results_file_path: str,
    performance_report_file_path: Optional[str],
    performance_metrics_file_path: Optional[str],
    output_dir_str: str,
    verbose: bool = False
) -> bool:
    """
    Exécute le pipeline de génération de rapport complet.

    Args:
        base_results_file_path (str): Chemin du fichier des résultats de base.
        advanced_results_file_path (str): Chemin du fichier des résultats avancés.
        performance_report_file_path (Optional[str]): Chemin du fichier du rapport de performance.
        performance_metrics_file_path (Optional[str]): Chemin du fichier des métriques de performance.
        output_dir_str (str): Répertoire de sortie pour les rapports et visualisations.
        verbose (bool): Active le logging détaillé.

    Returns:
        bool: True si le pipeline s'est exécuté avec succès, False sinon.
    """
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        logger.setLevel(logging.DEBUG) # Assurez-vous que le logger de ce module est aussi en DEBUG
        logger.debug("Mode verbeux activé pour le pipeline.")
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        logger.setLevel(logging.INFO)


    logger.info("Démarrage de la génération du rapport d'analyse complet via le pipeline...")

    base_results_path = Path(base_results_file_path)
    advanced_results_path = Path(advanced_results_file_path)
    output_dir = Path(output_dir_str)

    if not base_results_path.exists():
        logger.error(f"Le fichier de résultats de base {base_results_path} n'existe pas.")
        return False
    if not advanced_results_path.exists():
        logger.error(f"Le fichier de résultats avancés {advanced_results_path} n'existe pas.")
        return False

    performance_report = ""
    if performance_report_file_path:
        perf_report_path = Path(performance_report_file_path)
        if perf_report_path.exists():
            content = load_text_file(perf_report_path)
            performance_report = content if content is not None else ""
        else:
            logger.warning(f"Fichier de rapport de performance {perf_report_path} non trouvé.")
    else:
        logger.info("Aucun fichier de rapport de performance fourni.")

    performance_metrics = pd.DataFrame()
    if performance_metrics_file_path:
        perf_metrics_path = Path(performance_metrics_file_path)
        if perf_metrics_path.exists():
            df_metrics = load_csv_file(perf_metrics_path)
            performance_metrics = df_metrics if df_metrics is not None else pd.DataFrame()
        else:
            logger.warning(f"Fichier de métriques de performance {perf_metrics_path} non trouvé.")
    else:
        logger.info("Aucun fichier de métriques de performance fourni.")
        
    output_dir.mkdir(parents=True, exist_ok=True)
    visualization_dir = output_dir / "visualizations"
    visualization_dir.mkdir(parents=True, exist_ok=True)
    
    markdown_file = output_dir / "rapport_analyse_complet.md"
    html_file = output_dir / "rapport_analyse_complet.html"
    
    base_results_data = load_json_file(base_results_path)
    advanced_results_data = load_json_file(advanced_results_path)

    base_results = []
    if isinstance(base_results_data, list):
        base_results = base_results_data
    elif base_results_data is not None:
        logger.warning(f"Les résultats de base chargés depuis {base_results_path} ne sont pas une liste. Type: {type(base_results_data)}. Traitement comme liste vide.")

    advanced_results = []
    if isinstance(advanced_results_data, list):
        advanced_results = advanced_results_data
    elif advanced_results_data is not None:
        logger.warning(f"Les résultats avancés chargés depuis {advanced_results_path} ne sont pas une liste. Type: {type(advanced_results_data)}. Traitement comme liste vide.")

    if not base_results:
        logger.error("Aucun résultat de base n'a pu être chargé.")
        return False
    if not advanced_results:
        logger.error("Aucun résultat avancé n'a pu être chargé.")
        return False

    logger.info("Regroupement des résultats par corpus...")
    base_results_grouped = group_results_by_corpus(base_results)
    advanced_results_grouped = group_results_by_corpus(advanced_results)

    logger.info("Calcul des scores moyens...")
    average_scores_base = calculate_average_scores(base_results_grouped)
    average_scores_advanced = calculate_average_scores(advanced_results_grouped)
    
    combined_average_scores: Dict[str, Dict[str, float]] = {}
    all_corpora_for_scores = set(average_scores_base.keys()) | set(average_scores_advanced.keys())
    for corpus_name in all_corpora_for_scores:
        combined_average_scores[corpus_name] = {}
        base_corpus_scores = average_scores_base.get(corpus_name, {})
        advanced_corpus_scores = average_scores_advanced.get(corpus_name, {})
        all_metrics_for_corpus = set(base_corpus_scores.keys()) | set(advanced_corpus_scores.keys())
        for metric_name in all_metrics_for_corpus:
            if metric_name in advanced_corpus_scores:
                combined_average_scores[corpus_name][metric_name] = advanced_corpus_scores[metric_name]
            elif metric_name in base_corpus_scores:
                 combined_average_scores[corpus_name][metric_name] = base_corpus_scores[metric_name]
    
    logger.info("Analyse de l'efficacité des agents...")
    effectiveness = _analyze_agent_effectiveness(base_results, advanced_results, performance_metrics)
    
    logger.info("Génération des recommandations pour l'amélioration des agents...")
    improvement_recommendations = _generate_agent_improvement_recommendations()
    
    logger.info("Génération des recommandations pour de nouveaux agents...")
    new_agent_recommendations = _generate_new_agent_recommendations()
    
    logger.info("Génération des visualisations...")
    visualization_paths = _generate_visualizations(base_results, advanced_results, effectiveness, visualization_dir)
    
    logger.info("Génération du rapport Markdown...")
    _generate_markdown_report(
        base_results, advanced_results, performance_report, performance_metrics,
        effectiveness, improvement_recommendations, new_agent_recommendations,
        visualization_paths, markdown_file, combined_average_scores
    )
    
    logger.info("Génération du rapport HTML...")
    _generate_html_report(markdown_file, html_file, visualization_dir)
    
    logger.info(f"✅ Pipeline de génération du rapport complet terminé. Résultats dans {output_dir}")
    logger.info(f"Rapport Markdown: {markdown_file}")
    logger.info(f"Rapport HTML: {html_file}")
    return True

if __name__ == '__main__':
    # Exemple d'utilisation (pourrait être appelé par un script de plus haut niveau)
    # Ceci est juste pour des tests directs du module, pas pour l'exécution principale.
    parser = argparse.ArgumentParser(description="Exécute le pipeline de génération de rapport complet.")
    parser.add_argument("--base-results", required=True, help="Chemin des résultats de base (JSON).")
    parser.add_argument("--advanced-results", required=True, help="Chemin des résultats avancés (JSON).")
    parser.add_argument("--performance-report", help="Chemin du rapport de performance (Markdown).")
    parser.add_argument("--performance-metrics", help="Chemin des métriques de performance (CSV).")
    parser.add_argument("--output-dir", default="results/comprehensive_report_pipeline_test", help="Répertoire de sortie.")
    parser.add_argument("--verbose", action="store_true", help="Logging détaillé.")
    
    args = parser.parse_args()

    # Configuration initiale du logger pour le bloc __main__
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    # S'assurer que le logger du module est aussi au bon niveau si verbose est activé
    # au moment de l'appel de run_comprehensive_report_pipeline
    
    success = run_comprehensive_report_pipeline(
        base_results_file_path=args.base_results,
        advanced_results_file_path=args.advanced_results,
        performance_report_file_path=args.performance_report,
        performance_metrics_file_path=args.performance_metrics,
        output_dir_str=args.output_dir,
        verbose=args.verbose
    )

    if success:
        logger.info("Exécution de test du pipeline terminée avec succès.")
    else:
        logger.error("Exécution de test du pipeline a échoué.")
        sys.exit(1)
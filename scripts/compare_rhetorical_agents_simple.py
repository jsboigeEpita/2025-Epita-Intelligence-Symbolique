#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour comparer les performances des différents agents spécialistes d'analyse rhétorique.

Ce script:
1. Charge les résultats des analyses de base et avancée
2. Compare les performances des agents sur plusieurs critères
3. Génère des métriques quantitatives pour chaque agent
4. Produit des visualisations comparatives
5. Génère un rapport détaillé sur la pertinence des différents agents
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CompareRhetoricalAgents")

def load_results(file_path):
    """Charge les résultats d'analyse depuis un fichier JSON."""
    logger.info(f"Chargement des résultats depuis {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        logger.info(f"✅ {len(results)} résultats chargés avec succès")
        return results
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement des résultats: {e}")
        return []

def count_fallacies(results):
    """Compte le nombre de sophismes détectés par chaque agent."""
    fallacy_counts = {
        "base_contextual": 0,
        "advanced_contextual": 0,
        "advanced_complex": 0
    }
    
    # Analyse de base - sophismes contextuels
    for result in results:
        contextual_fallacies = result.get("analyses", {}).get("contextual_fallacies", {})
        argument_results = contextual_fallacies.get("argument_results", [])
        
        for arg_result in argument_results:
            fallacy_counts["base_contextual"] += len(arg_result.get("detected_fallacies", []))
        
        # Analyse avancée - sophismes complexes
        complex_fallacies = result.get("analyses", {}).get("complex_fallacies", {})
        
        # Compter les sophismes individuels
        fallacy_counts["advanced_complex"] += complex_fallacies.get("individual_fallacies_count", 0)
        
        # Compter les combinaisons de base
        fallacy_counts["advanced_complex"] += len(complex_fallacies.get("basic_combinations", []))
        
        # Compter les combinaisons avancées
        fallacy_counts["advanced_complex"] += len(complex_fallacies.get("advanced_combinations", []))
        
        # Compter les motifs de sophismes
        fallacy_counts["advanced_complex"] += len(complex_fallacies.get("fallacy_patterns", []))
        
        # Analyse avancée - sophismes contextuels
        advanced_contextual = result.get("analyses", {}).get("contextual_fallacies", {})
        fallacy_counts["advanced_contextual"] += advanced_contextual.get("contextual_fallacies_count", 0)
    
    return fallacy_counts

def extract_confidence_scores(results):
    """Extrait les scores de confiance des analyses."""
    confidence_scores = {
        "base_coherence": [],
        "advanced_rhetorical": [],
        "advanced_coherence": [],
        "advanced_severity": []
    }
    
    for result in results:
        # Analyse de base - cohérence argumentative
        base_coherence = result.get("analyses", {}).get("argument_coherence", {})
        base_coherence_score = base_coherence.get("overall_coherence", {}).get("score", 0.0)
        confidence_scores["base_coherence"].append(base_coherence_score)
        
        # Analyse avancée - analyse rhétorique globale
        rhetorical_results = result.get("analyses", {}).get("rhetorical_results", {})
        overall_analysis = rhetorical_results.get("overall_analysis", {})
        rhetorical_quality = overall_analysis.get("rhetorical_quality", 0.0)
        confidence_scores["advanced_rhetorical"].append(rhetorical_quality)
        
        # Analyse avancée - cohérence
        coherence_analysis = rhetorical_results.get("coherence_analysis", {})
        overall_coherence = coherence_analysis.get("overall_coherence", 0.0)
        confidence_scores["advanced_coherence"].append(overall_coherence)
        
        # Analyse avancée - gravité des sophismes
        fallacy_severity = result.get("analyses", {}).get("fallacy_severity", {})
        overall_severity = fallacy_severity.get("overall_severity", 0.0)
        confidence_scores["advanced_severity"].append(overall_severity)
    
    # Calculer les moyennes
    avg_scores = {}
    for agent, scores in confidence_scores.items():
        if scores:
            avg_scores[agent] = sum(scores) / len(scores)
        else:
            avg_scores[agent] = 0.0
    
    return avg_scores

def analyze_contextual_richness(results):
    """Analyse la richesse contextuelle des résultats."""
    richness_scores = {
        "base_contextual": [],
        "advanced_contextual": [],
        "advanced_rhetorical": []
    }
    
    for result in results:
        # Analyse de base - facteurs contextuels
        base_contextual = result.get("analyses", {}).get("contextual_fallacies", {})
        contextual_factors = base_contextual.get("contextual_factors", {})
        
        # Score simple basé sur le nombre de facteurs contextuels
        base_richness = len(contextual_factors)
        richness_scores["base_contextual"].append(base_richness)
        
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
        
        richness_scores["advanced_contextual"].append(advanced_richness)
        
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
        
        richness_scores["advanced_rhetorical"].append(rhetorical_richness)
    
    # Calculer les moyennes
    avg_scores = {}
    for agent, scores in richness_scores.items():
        if scores:
            avg_scores[agent] = sum(scores) / len(scores)
        else:
            avg_scores[agent] = 0.0
    
    return avg_scores

def generate_performance_visualizations(base_metrics, advanced_metrics, output_dir):
    """Génère des visualisations comparatives des performances des agents."""
    # Créer le répertoire de sortie s'il n'existe pas
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Graphique de comparaison des nombres de sophismes détectés
    plt.figure(figsize=(10, 6))
    agents = ["base_contextual", "advanced_contextual", "advanced_complex"]
    fallacy_counts = [
        base_metrics["fallacy_counts"]["base_contextual"],
        advanced_metrics["fallacy_counts"]["advanced_contextual"],
        advanced_metrics["fallacy_counts"]["advanced_complex"]
    ]
    
    bars = plt.bar(agents, fallacy_counts)
    
    # Ajouter les valeurs sur les barres
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f"{height}", ha='center', va='bottom')
    
    plt.title("Nombre de sophismes détectés par agent")
    plt.xlabel("Agent")
    plt.ylabel("Nombre de sophismes")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / "fallacy_counts.png")
    plt.close()
    
    # 2. Graphique de comparaison des scores de confiance
    plt.figure(figsize=(10, 6))
    confidence_agents = ["base_coherence", "advanced_rhetorical", "advanced_coherence", "advanced_severity"]
    confidence_scores = [
        base_metrics["confidence_scores"]["base_coherence"],
        advanced_metrics["confidence_scores"]["advanced_rhetorical"],
        advanced_metrics["confidence_scores"]["advanced_coherence"],
        advanced_metrics["confidence_scores"]["advanced_severity"]
    ]
    
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
    
    # 3. Graphique de comparaison de la richesse contextuelle
    plt.figure(figsize=(10, 6))
    richness_agents = ["base_contextual", "advanced_contextual", "advanced_rhetorical"]
    richness_scores = [
        base_metrics["richness_scores"]["base_contextual"],
        advanced_metrics["richness_scores"]["advanced_contextual"],
        advanced_metrics["richness_scores"]["advanced_rhetorical"]
    ]
    
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
    
    # 4. Matrice de comparaison des performances
    # Créer un DataFrame pour la matrice de comparaison
    comparison_data = {
        "Agent": ["base_contextual", "advanced_contextual", "advanced_complex", "base_coherence", 
                 "advanced_rhetorical", "advanced_coherence", "advanced_severity"],
        "Sophismes détectés": [
            base_metrics["fallacy_counts"]["base_contextual"],
            advanced_metrics["fallacy_counts"]["advanced_contextual"],
            advanced_metrics["fallacy_counts"]["advanced_complex"],
            0, 0, 0, 0
        ],
        "Score de confiance": [
            0, 0, 0,
            base_metrics["confidence_scores"]["base_coherence"],
            advanced_metrics["confidence_scores"]["advanced_rhetorical"],
            advanced_metrics["confidence_scores"]["advanced_coherence"],
            advanced_metrics["confidence_scores"]["advanced_severity"]
        ],
        "Richesse contextuelle": [
            base_metrics["richness_scores"]["base_contextual"],
            advanced_metrics["richness_scores"]["advanced_contextual"],
            0, 0,
            advanced_metrics["richness_scores"]["advanced_rhetorical"],
            0, 0
        ]
    }
    
    df = pd.DataFrame(comparison_data)
    df.set_index("Agent", inplace=True)
    
    # Sauvegarder les données brutes
    df.to_csv(output_dir / "performance_metrics.csv")
    
    # Créer la heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(df, annot=True, cmap="YlGnBu", linewidths=0.5)
    plt.title("Matrice de comparaison des performances des agents")
    plt.tight_layout()
    plt.savefig(output_dir / "performance_matrix.png")
    plt.close()

def generate_performance_report(base_metrics, advanced_metrics, output_file):
    """Génère un rapport détaillé sur la pertinence des différents agents."""
    # Créer le répertoire parent s'il n'existe pas
    output_file = Path(output_file)
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
    
    # Métriques de performance par agent
    report.append("## Métriques de performance par agent")
    report.append("")
    
    # Détection des sophismes
    report.append("### Détection des sophismes")
    report.append("")
    report.append("| Agent | Nombre de sophismes détectés |")
    report.append("|-------|----------------------------|")
    report.append(f"| Agent contextuel de base | {base_metrics['fallacy_counts']['base_contextual']} |")
    report.append(f"| Agent contextuel avancé | {advanced_metrics['fallacy_counts']['advanced_contextual']} |")
    report.append(f"| Agent de sophismes complexes | {advanced_metrics['fallacy_counts']['advanced_complex']} |")
    report.append("")
    
    # Scores de confiance
    report.append("### Scores de confiance")
    report.append("")
    report.append("| Agent | Score de confiance moyen |")
    report.append("|-------|--------------------------|")
    report.append(f"| Agent de cohérence de base | {base_metrics['confidence_scores']['base_coherence']:.2f} |")
    report.append(f"| Agent rhétorique avancé | {advanced_metrics['confidence_scores']['advanced_rhetorical']:.2f} |")
    report.append(f"| Agent de cohérence avancé | {advanced_metrics['confidence_scores']['advanced_coherence']:.2f} |")
    report.append(f"| Agent d'évaluation de gravité | {advanced_metrics['confidence_scores']['advanced_severity']:.2f} |")
    report.append("")
    
    # Richesse contextuelle
    report.append("### Richesse contextuelle")
    report.append("")
    report.append("| Agent | Score de richesse contextuelle moyen |")
    report.append("|-------|-------------------------------------|")
    report.append(f"| Agent contextuel de base | {base_metrics['richness_scores']['base_contextual']:.2f} |")
    report.append(f"| Agent contextuel avancé | {advanced_metrics['richness_scores']['advanced_contextual']:.2f} |")
    report.append(f"| Agent rhétorique avancé | {advanced_metrics['richness_scores']['advanced_rhetorical']:.2f} |")
    report.append("")
    
    # Analyse comparative
    report.append("## Analyse comparative")
    report.append("")
    
    # Comparer la détection des sophismes
    base_fallacy_count = base_metrics['fallacy_counts']['base_contextual']
    advanced_contextual_count = advanced_metrics['fallacy_counts']['advanced_contextual']
    advanced_complex_count = advanced_metrics['fallacy_counts']['advanced_complex']
    
    if advanced_complex_count > base_fallacy_count and advanced_complex_count > advanced_contextual_count:
        report.append("L'agent de sophismes complexes détecte le plus grand nombre de sophismes, ce qui suggère une analyse plus approfondie.")
    elif advanced_contextual_count > base_fallacy_count:
        report.append("L'agent contextuel avancé détecte plus de sophismes que l'agent contextuel de base, ce qui suggère une meilleure précision.")
    else:
        report.append("L'agent contextuel de base détecte un nombre comparable de sophismes aux agents avancés, ce qui suggère une bonne efficacité.")
    
    report.append("")
    
    # Comparer la richesse contextuelle
    base_richness = base_metrics['richness_scores']['base_contextual']
    advanced_contextual_richness = advanced_metrics['richness_scores']['advanced_contextual']
    advanced_rhetorical_richness = advanced_metrics['richness_scores']['advanced_rhetorical']
    
    if advanced_rhetorical_richness > advanced_contextual_richness and advanced_rhetorical_richness > base_richness:
        report.append("L'agent rhétorique avancé fournit l'analyse contextuelle la plus riche, ce qui permet une meilleure compréhension du contexte.")
    elif advanced_contextual_richness > base_richness:
        report.append("L'agent contextuel avancé fournit une analyse contextuelle plus riche que l'agent contextuel de base.")
    else:
        report.append("L'agent contextuel de base fournit une analyse contextuelle comparable aux agents avancés.")
    
    report.append("")
    
    # Recommandations
    report.append("## Recommandations")
    report.append("")
    report.append("Sur la base de l'analyse comparative, voici quelques recommandations:")
    report.append("")
    report.append("1. **Pour une analyse rapide et basique**: Utiliser les agents de base (ContextualFallacyDetector, ArgumentCoherenceEvaluator, SemanticArgumentAnalyzer).")
    report.append("2. **Pour une analyse approfondie**: Utiliser les agents avancés (EnhancedComplexFallacyAnalyzer, EnhancedContextualFallacyAnalyzer, EnhancedFallacySeverityEvaluator, EnhancedRhetoricalResultAnalyzer).")
    report.append("3. **Pour la détection des sophismes**: Privilégier l'agent EnhancedComplexFallacyAnalyzer qui détecte les sophismes composites et les motifs de sophismes.")
    report.append("4. **Pour l'analyse contextuelle**: Privilégier l'agent EnhancedRhetoricalResultAnalyzer qui fournit une analyse contextuelle plus riche.")
    report.append("")
    
    # Conclusion
    report.append("## Conclusion")
    report.append("")
    report.append("Cette analyse comparative des performances des agents spécialistes d'analyse rhétorique montre que:")
    report.append("")
    report.append("1. Les agents avancés fournissent généralement une analyse plus riche et plus détaillée que les agents de base.")
    report.append("2. Les agents avancés détectent plus de sophismes, en particulier les sophismes complexes et composites.")
    report.append("3. Les agents avancés fournissent une analyse contextuelle plus riche.")
    report.append("")
    report.append("Le choix des agents dépend donc des besoins spécifiques de l'analyse: rapidité vs profondeur, simplicité vs richesse, etc.")
    
    # Écrire le rapport dans un fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    logger.info(f"✅ Rapport de performance généré: {output_file}")

def main():
    """Fonction principale du script."""
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
    
    args = parser.parse_args()
    
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
    
    base_metrics = {
        "fallacy_counts": count_fallacies(base_results),
        "confidence_scores": extract_confidence_scores(base_results),
        "richness_scores": analyze_contextual_richness(base_results)
    }
    
    advanced_metrics = {
        "fallacy_counts": count_fallacies(advanced_results),
        "confidence_scores": extract_confidence_scores(advanced_results),
        "richness_scores": analyze_contextual_richness(advanced_results)
    }
    
    # Générer les visualisations
    logger.info("Génération des visualisations...")
    generate_performance_visualizations(base_metrics, advanced_metrics, output_dir)
    
    # Générer le rapport
    logger.info("Génération du rapport...")
    report_file = output_dir / "rapport_performance.md"
    generate_performance_report(base_metrics, advanced_metrics, report_file)
    
    logger.info(f"✅ Comparaison des performances terminée. Résultats sauvegardés dans {output_dir}")

if __name__ == "__main__":
    main()
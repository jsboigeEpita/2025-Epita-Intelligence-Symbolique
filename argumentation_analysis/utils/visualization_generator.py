#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaire pour la génération de visualisations des performances des agents.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any

# Dépendances optionnelles pour la visualisation
try:
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns
    VISUALIZATION_LIBS_AVAILABLE = True
except ImportError:
    VISUALIZATION_LIBS_AVAILABLE = False
    # Initialiser les variables pour que le code ne plante pas si les libs sont absentes
    # mais les fonctions utilisant ces variables ne seront pas appelées grâce au flag.
    plt = None 
    np = None
    pd = None
    sns = None


logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def generate_performance_visualizations(
    metrics: Dict[str, Dict[str, Any]],
    output_dir: Path
) -> List[str]:
    """
    Génère des visualisations comparatives des performances des agents.
    Nécessite matplotlib, numpy, pandas, seaborn.

    Args:
        metrics (Dict[str, Dict[str, Any]]): Métriques de performance par agent.
        output_dir (Path): Répertoire de sortie pour les visualisations.

    Returns:
        List[str]: Liste des chemins des fichiers de visualisation générés.
    """
    if not VISUALIZATION_LIBS_AVAILABLE:
        logger.warning("Bibliothèques de visualisation (matplotlib, numpy, pandas, seaborn) non disponibles. Saut de la génération des graphiques.")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: List[str] = []
    
    agents = list(metrics.keys())
    if not agents:
        logger.info("Aucune métrique d'agent fournie, aucune visualisation ne sera générée.")
        return []
    
    # Graphique de comparaison des nombres de sophismes détectés
    fallacy_counts = [metrics[agent].get("fallacy_count", 0) for agent in agents if metrics[agent].get("fallacy_count") is not None]
    fallacy_agents = [agent for agent in agents if metrics[agent].get("fallacy_count") is not None]
    if fallacy_counts and fallacy_agents:
        plt.figure(figsize=(10, 7))
        bars = plt.bar(fallacy_agents, fallacy_counts, color=sns.color_palette("viridis", len(fallacy_agents)))
        for bar in bars:
            plt.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05 * max(fallacy_counts, default=1),
                     f"{bar.get_height():.2f}", ha='center', va='bottom')
        plt.title("Nombre moyen de sophismes détectés par agent")
        plt.xlabel("Agent")
        plt.ylabel("Nombre moyen de sophismes")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        file_path = output_dir / "fallacy_counts_comparison.png"
        plt.savefig(file_path)
        plt.close()
        generated_files.append(str(file_path))
        logger.info(f"Visualisation 'fallacy_counts_comparison.png' générée.")

    # Graphique de comparaison des scores de confiance
    confidence_scores = [metrics[agent].get("confidence", 0) for agent in agents if metrics[agent].get("confidence") is not None]
    confidence_agents = [agent for agent in agents if metrics[agent].get("confidence") is not None]
    if confidence_scores and confidence_agents:
        plt.figure(figsize=(10, 7))
        bars = plt.bar(confidence_agents, confidence_scores, color=sns.color_palette("magma", len(confidence_agents)))
        for bar in bars:
            plt.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                     f"{bar.get_height():.2f}", ha='center', va='bottom')
        plt.title("Scores de confiance moyens par agent")
        plt.xlabel("Agent")
        plt.ylabel("Score de confiance moyen")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        file_path = output_dir / "confidence_scores_comparison.png"
        plt.savefig(file_path)
        plt.close()
        generated_files.append(str(file_path))
        logger.info(f"Visualisation 'confidence_scores_comparison.png' générée.")

    # Graphique des taux de faux positifs/négatifs
    fp_rates_filtered = [metrics[agent].get("false_positive_rate", 0.0) for agent in agents if metrics[agent].get("false_positive_rate") is not None]
    fn_rates_filtered = [metrics[agent].get("false_negative_rate", 0.0) for agent in agents if metrics[agent].get("false_negative_rate") is not None]
    error_agents = [agent for agent in agents if metrics[agent].get("false_positive_rate") is not None and metrics[agent].get("false_negative_rate") is not None]
    
    # Filtrer à nouveau fp_rates et fn_rates pour correspondre à error_agents
    fp_rates_for_plot = [metrics[agent]["false_positive_rate"] for agent in error_agents]
    fn_rates_for_plot = [metrics[agent]["false_negative_rate"] for agent in error_agents]

    if error_agents and fp_rates_for_plot and fn_rates_for_plot:
        x = np.arange(len(error_agents))
        width = 0.35
        plt.figure(figsize=(12, 7))
        plt.bar(x - width/2, fp_rates_for_plot, width, label='Taux Faux Positifs', color=sns.color_palette("coolwarm")[0])
        plt.bar(x + width/2, fn_rates_for_plot, width, label='Taux Faux Négatifs', color=sns.color_palette("coolwarm")[3])
        plt.title("Taux de faux positifs et faux négatifs estimés par agent")
        plt.xlabel("Agent")
        plt.ylabel("Taux d'erreur estimé")
        plt.xticks(x, error_agents, rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()
        file_path = output_dir / "error_rates_comparison.png"
        plt.savefig(file_path)
        plt.close()
        generated_files.append(str(file_path))
        logger.info(f"Visualisation 'error_rates_comparison.png' générée.")

    # Graphique des temps d'exécution
    exec_times = [metrics[agent].get("execution_time", 0) for agent in agents if metrics[agent].get("execution_time") is not None]
    exec_agents = [agent for agent in agents if metrics[agent].get("execution_time") is not None]
    if exec_times and exec_agents:
        plt.figure(figsize=(10, 7))
        bars = plt.bar(exec_agents, exec_times, color=sns.color_palette("plasma", len(exec_agents)))
        for bar in bars:
            plt.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.02 * max(exec_times, default=1),
                     f"{bar.get_height():.2f}s", ha='center', va='bottom')
        plt.title("Temps d'exécution moyens par agent")
        plt.xlabel("Agent")
        plt.ylabel("Temps d'exécution moyen (s)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        file_path = output_dir / "execution_times_comparison.png"
        plt.savefig(file_path)
        plt.close()
        generated_files.append(str(file_path))
        logger.info(f"Visualisation 'execution_times_comparison.png' générée.")

    # Matrice de comparaison des performances (Heatmap)
    heatmap_metrics = ["fallacy_count", "confidence", "false_positive_rate", "false_negative_rate",
                       "execution_time", "contextual_richness", "relevance", "complexity", "recommendation_relevance"]
    
    df_data = []
    for agent_name in agents:
        row = {"agent": agent_name}
        for metric_name in heatmap_metrics:
            row[metric_name] = metrics[agent_name].get(metric_name) 
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    df = df.set_index("agent")
    df = df.dropna(axis=1, how='all') 
    df = df.fillna(0) 

    if not df.empty:
        df_normalized = (df - df.min()) / (df.max() - df.min())
        df_normalized = df_normalized.fillna(0) 

        plt.figure(figsize=(14, 10))
        sns.heatmap(df_normalized, annot=df.round(2), cmap="viridis_r", linewidths=.5, fmt=".2f")
        plt.title("Matrice de comparaison normalisée des performances des agents")
        plt.xticks(rotation=45, ha="right")
        plt.yticks(rotation=0)
        plt.tight_layout()
        file_path = output_dir / "performance_matrix_heatmap.png"
        plt.savefig(file_path)
        plt.close()
        generated_files.append(str(file_path))
        logger.info(f"Visualisation 'performance_matrix_heatmap.png' générée.")
        
        csv_file_path = output_dir / "performance_metrics_summary.csv"
        df.to_csv(csv_file_path)
        generated_files.append(str(csv_file_path))
        logger.info(f"Données des métriques sauvegardées dans '{csv_file_path}'.")

    return generated_files
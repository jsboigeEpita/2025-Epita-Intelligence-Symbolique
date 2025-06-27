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
    import matplotlib
    matplotlib.use('Agg')
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

def _prepare_data_for_bar_chart(metrics: Dict, metric_name: str) -> (List[str], List[float]):
    """Extrait les données pour un graphique à barres simple."""
    agents_with_metric = [agent for agent in metrics.keys() if metrics[agent].get(metric_name) is not None]
    values = [metrics[agent][metric_name] for agent in agents_with_metric]
    return agents_with_metric, values

def _plot_bar_chart(ax, data_agents: List[str], data_values: List[float], title: str, ylabel: str, palette: str, text_suffix: str = ""):
    """Génère un graphique à barres sur un axe donné."""
    bars = ax.bar(data_agents, data_values, color=sns.color_palette(palette, len(data_agents)))
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05 * max(data_values, default=1),
                 f"{bar.get_height():.2f}{text_suffix}", ha='center', va='bottom')
    ax.set_title(title)
    ax.set_xlabel("Agent")
    ax.set_ylabel(ylabel)
    ax.tick_params(axis='x', rotation=45)

def _plot_error_rates(ax, metrics: Dict, agents: List[str]):
    """Génère le graphique des taux d'erreur."""
    error_agents = [agent for agent in agents if metrics[agent].get("false_positive_rate") is not None and metrics[agent].get("false_negative_rate") is not None]
    if not error_agents:
        return
    fp_rates = [metrics[agent]["false_positive_rate"] for agent in error_agents]
    fn_rates = [metrics[agent]["false_negative_rate"] for agent in error_agents]
    
    x = np.arange(len(error_agents))
    width = 0.35
    palette = sns.color_palette("coolwarm", n_colors=4)
    ax.bar(x - width/2, fp_rates, width, label='Taux Faux Positifs', color=palette[0])
    ax.bar(x + width/2, fn_rates, width, label='Taux Faux Négatifs', color=palette[3])
    ax.set_title("Taux de faux positifs et faux négatifs estimés par agent")
    ax.set_xlabel("Agent")
    ax.set_ylabel("Taux d'erreur estimé")
    ax.set_xticks(x)
    ax.set_xticklabels(error_agents, rotation=45, ha="right")
    ax.legend()

def _prepare_heatmap_data(metrics: Dict, agents: List[str]) -> pd.DataFrame:
    """Prépare et normalise les données pour le heatmap."""
    heatmap_metrics = ["fallacy_count", "confidence", "false_positive_rate", "false_negative_rate", "execution_time", "contextual_richness", "relevance", "complexity", "recommendation_relevance"]
    
    df = pd.DataFrame(index=pd.Index(agents, name="agent"))
    for metric_name in heatmap_metrics:
        metric_values = [metrics.get(agent, {}).get(metric_name) for agent in agents]
        df[metric_name] = pd.to_numeric(pd.Series(metric_values, index=df.index), errors='coerce')

    df.dropna(axis=1, how='all', inplace=True)
    if df.empty:
        return pd.DataFrame()
        
    df.fillna(0, inplace=True)
    return df

def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise un DataFrame."""
    if df.empty:
        return pd.DataFrame()
    df_min = df.min()
    df_max = df.max()
    range_val = df_max - df_min
    range_val_safe = range_val.replace(0, 1)
    df_normalized = (df - df_min) / range_val_safe
    return df_normalized.fillna(0)

def _plot_heatmap(ax, df_normalized: pd.DataFrame, df_original: pd.DataFrame):
    """Génère le heatmap sur un axe donné."""
    sns.heatmap(df_normalized, annot=df_original.round(2), cmap="viridis_r", linewidths=.5, fmt=".2f", ax=ax)
    ax.set_title("Matrice de comparaison normalisée des performances des agents")
    ax.tick_params(axis='x', rotation=45)
    ax.tick_params(axis='y', rotation=0)

def generate_performance_visualizations(
    metrics: Dict[str, Dict[str, Any]],
    output_dir: Path
) -> List[str]:
    """
    Génère des visualisations comparatives des performances des agents.
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
    fallacy_agents, fallacy_counts = _prepare_data_for_bar_chart(metrics, "fallacy_count")
    if fallacy_agents:
        fig, ax = plt.subplots(figsize=(10, 7))
        _plot_bar_chart(ax, fallacy_agents, fallacy_counts, "Nombre moyen de sophismes détectés par agent", "Nombre moyen de sophismes", "viridis")
        fig.tight_layout()
        file_path = output_dir / "fallacy_counts_comparison.png"
        fig.savefig(file_path)
        plt.close(fig)
        generated_files.append(str(file_path))
        logger.info(f"Visualisation '{file_path.name}' générée.")

    # Graphique de comparaison des scores de confiance
    confidence_agents, confidence_scores = _prepare_data_for_bar_chart(metrics, "confidence")
    if confidence_agents:
        fig, ax = plt.subplots(figsize=(10, 7))
        _plot_bar_chart(ax, confidence_agents, confidence_scores, "Scores de confiance moyens par agent", "Score de confiance moyen", "magma")
        fig.tight_layout()
        file_path = output_dir / "confidence_scores_comparison.png"
        fig.savefig(file_path)
        plt.close(fig)
        generated_files.append(str(file_path))
        logger.info(f"Visualisation '{file_path.name}' générée.")

    # Graphique des taux de faux positifs/négatifs
    fig, ax = plt.subplots(figsize=(12, 7))
    _plot_error_rates(ax, metrics, agents)
    if ax.has_data():
        fig.tight_layout()
        file_path = output_dir / "error_rates_comparison.png"
        fig.savefig(file_path)
        generated_files.append(str(file_path))
        logger.info(f"Visualisation '{file_path.name}' générée.")
    plt.close(fig)

    # Graphique des temps d'exécution
    exec_agents, exec_times = _prepare_data_for_bar_chart(metrics, "execution_time")
    if exec_agents:
        fig, ax = plt.subplots(figsize=(10, 7))
        _plot_bar_chart(ax, exec_agents, exec_times, "Temps d'exécution moyens par agent", "Temps d'exécution moyen (s)", "plasma", text_suffix="s")
        fig.tight_layout()
        file_path = output_dir / "execution_times_comparison.png"
        fig.savefig(file_path)
        plt.close(fig)
        generated_files.append(str(file_path))
        logger.info(f"Visualisation '{file_path.name}' générée.")

    # Matrice de comparaison des performances (Heatmap)
    df_heatmap = _prepare_heatmap_data(metrics, agents)
    if not df_heatmap.empty:
        df_normalized = _normalize_dataframe(df_heatmap)
        fig, ax = plt.subplots(figsize=(14, 10))
        _plot_heatmap(ax, df_normalized, df_heatmap)
        fig.tight_layout()
        file_path = output_dir / "performance_matrix_heatmap.png"
        fig.savefig(file_path)
        plt.close(fig)
        generated_files.append(str(file_path))
        logger.info(f"Visualisation '{file_path.name}' générée.")
        
        csv_file_path = output_dir / "performance_metrics_summary.csv"
        df_heatmap.to_csv(csv_file_path)
        generated_files.append(str(csv_file_path))
        logger.info(f"Données des métriques sauvegardées dans '{csv_file_path}'.")

    return generated_files
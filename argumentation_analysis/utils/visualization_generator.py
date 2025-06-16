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
        palette = sns.color_palette("coolwarm", n_colors=4) # Demander explicitement 4 couleurs
        plt.bar(x - width/2, fp_rates_for_plot, width, label='Taux Faux Positifs', color=palette[0])
        plt.bar(x + width/2, fn_rates_for_plot, width, label='Taux Faux Négatifs', color=palette[3])
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
    
    # Initialiser un DataFrame avec l'index des agents
    if agents:
        df = pd.DataFrame(index=pd.Index(agents, name="agent"))
    else:
        df = pd.DataFrame()

    # Remplir le DataFrame colonne par colonne pour les métriques
    for metric_name in heatmap_metrics:
        metric_values = [metrics.get(agent_name, {}).get(metric_name) for agent_name in agents]
        # Créer la Series avec dtype=float pour convertir None en NaN
        # et s'assurer que les valeurs numériques sont bien des floats.
        # Si metric_values ne contient que des None, la Series sera de type float64 avec des NaN.
        try:
            s = pd.Series(metric_values, index=df.index, dtype=float)
            # Si la série n'est pas vide après conversion (c-à-d, elle ne contenait pas QUE des None ou des erreurs de conversion)
            # ou si elle est vide mais que la colonne n'existe pas encore (pour la créer)
            if not s.isnull().all() or metric_name not in df.columns:
                 df[metric_name] = s
            elif metric_name in df.columns: # La colonne existe mais la nouvelle série est vide/NaN
                 df[metric_name] = pd.Series(np.nan, index=df.index, dtype=float) # Remplacer par des NaN explicites
        except Exception as e:
            logger.warning(f"Impossible de créer/convertir la Series pour la métrique '{metric_name}' avec dtype=float: {e}. Tentative avec pd.to_numeric.")
            try:
                # Tentative sans forcer dtype, puis conversion
                temp_series = pd.Series(metric_values, index=df.index)
                s_numeric = pd.to_numeric(temp_series, errors='coerce')
                if not s_numeric.isnull().all() or metric_name not in df.columns:
                    df[metric_name] = s_numeric
                elif metric_name in df.columns:
                    df[metric_name] = pd.Series(np.nan, index=df.index, dtype=float)

            except Exception as e_inner:
                logger.error(f"Échec final de la création/conversion de la Series pour la métrique '{metric_name}': {e_inner}. Cette métrique sera remplie de NaN.")
                # Assurer que la colonne existe avec des NaN si elle a été partiellement créée ou référencée
                df[metric_name] = pd.Series(np.nan, index=df.index, dtype=float)


    # Supprimer les colonnes qui seraient entièrement NaN (si une métrique n'existe pour aucun agent ou n'a pu être convertie)
    df = df.dropna(axis=1, how='all')
    
    if not df.empty:
        # Tenter de convertir toutes les colonnes en numérique.
        for col in list(df.columns): # Utiliser list() pour itérer sur une copie si on modifie df.columns
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Ne garder que les colonnes qui sont effectivement devenues numériques.
        # Si aucune colonne n'est numérique, df deviendra un DataFrame vide (avec index s'il existait).
        # Au lieu de slicer avec df[numeric_cols], supprimons les colonnes non numériques pour éviter le bug potentiel.
        numeric_cols_present = df.select_dtypes(include=np.number).columns
        cols_to_drop = [col for col in df.columns if col not in numeric_cols_present]
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
        
        # Maintenant, df ne contient que des colonnes numériques (ou est vide si toutes ont été droppées ou si df était vide initialement).
        # On peut appliquer fillna(0) sans risque si df n'est pas vide.
        if not df.empty:
           # Forcer la conversion en float pour une meilleure gestion des NaN avant fillna,
           # surtout si une colonne initialement int est devenue float à cause des NaN.
           # Ou si une colonne est restée 'object' mais contient des nombres.
           for col_name in df.columns: # S'assurer que chaque colonne est bien numérique
               if df[col_name].dtype == 'object':
                   df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
           # Après to_numeric, les colonnes avec des non-numériques auront des NaN.
           # Celles qui étaient full-NaN ont été droppées. Celles qui sont devenues full-NaN ici seront gérées par fillna.
           df = df.astype(float).fillna(0)
        # Si df est devenu vide après la sélection des colonnes numériques, il le reste.
    # else: df était déjà vide ou est devenu vide après dropna.
    # À ce stade, df est soit vide, soit contient uniquement des colonnes numériques avec les NaN remplacés par 0.
    if not df.empty:
        # df ne contient maintenant que des colonnes numériques avec les NaN remplacés par 0.
        df_min = df.min()
        df_max = df.max()
        range_val = df_max - df_min
        
        range_val_safe = range_val.replace(0, 1)

        df_normalized = (df - df_min) / range_val_safe
        df_normalized = df_normalized.fillna(0)
    else:
        # S'assurer que df_normalized est un DataFrame vide avec les colonnes attendues si df est vide
        # Cela évite des erreurs si heatmap est appelée avec un DataFrame vide.
        # Les colonnes de heatmap_metrics qui existent réellement dans les données après dropna.
        # Cependant, si df est vide, df.columns sera vide.
        # Il est plus sûr de créer un DataFrame vide sans colonnes spécifiques ici.
        df_normalized = pd.DataFrame(index=pd.Index(agents, name="agent") if agents else None)

    if not df_normalized.empty:
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
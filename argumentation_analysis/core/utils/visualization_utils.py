# -*- coding: utf-8 -*-
"""Utilitaires pour la génération de visualisations."""

import logging
from pathlib import Path
from typing import Dict, Any
import matplotlib.pyplot as plt
import pandas as pd

# import seaborn as sns

logger = logging.getLogger(__name__)


def generate_performance_visualizations(
    base_metrics: Dict[str, Any], advanced_metrics: Dict[str, Any], output_dir: Path
) -> None:
    """
    Génère des visualisations comparatives des performances des agents.
    Les métriques attendues sont des dictionnaires contenant eux-mêmes des dictionnaires
    pour 'fallacy_counts', 'confidence_scores', 'richness_scores'.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Début de la génération des visualisations dans {output_dir}")

    # 1. Graphique de comparaison des nombres de sophismes détectés
    try:
        plt.figure(figsize=(10, 6))
        agents_fallacy = ["base_contextual", "advanced_contextual", "advanced_complex"]
        fallacy_counts_values = [
            base_metrics.get("fallacy_counts", {}).get("base_contextual", 0),
            advanced_metrics.get("fallacy_counts", {}).get("advanced_contextual", 0),
            advanced_metrics.get("fallacy_counts", {}).get("advanced_complex", 0),
        ]

        bars_fallacy = plt.bar(agents_fallacy, fallacy_counts_values)
        for bar in bars_fallacy:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.1,
                f"{height}",
                ha="center",
                va="bottom",
            )

        plt.title("Nombre de sophismes détectés par agent")
        plt.xlabel("Agent")
        plt.ylabel("Nombre de sophismes")
        plt.xticks(rotation=45)
        plt.tight_layout()
        fallacy_chart_path = output_dir / "fallacy_counts.png"
        plt.savefig(fallacy_chart_path)
        plt.close()
        logger.debug(f"Graphique des sophismes sauvegardé : {fallacy_chart_path}")
    except Exception as e:
        logger.error(
            f"Erreur lors de la génération du graphique des sophismes: {e}",
            exc_info=True,
        )

    # 2. Graphique de comparaison des scores de confiance
    try:
        plt.figure(figsize=(10, 6))
        agents_confidence = [
            "base_coherence",
            "advanced_rhetorical",
            "advanced_coherence",
            "advanced_severity",
        ]
        confidence_scores_values = [
            base_metrics.get("confidence_scores", {}).get("base_coherence", 0.0),
            advanced_metrics.get("confidence_scores", {}).get(
                "advanced_rhetorical", 0.0
            ),
            advanced_metrics.get("confidence_scores", {}).get(
                "advanced_coherence", 0.0
            ),
            advanced_metrics.get("confidence_scores", {}).get("advanced_severity", 0.0),
        ]

        bars_confidence = plt.bar(agents_confidence, confidence_scores_values)
        for bar in bars_confidence:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.02,
                f"{height:.2f}",
                ha="center",
                va="bottom",
            )

        plt.title("Scores de confiance moyens par agent")
        plt.xlabel("Agent")
        plt.ylabel("Score de confiance moyen")
        plt.xticks(rotation=45)
        plt.tight_layout()
        confidence_chart_path = output_dir / "confidence_scores.png"
        plt.savefig(confidence_chart_path)
        plt.close()
        logger.debug(
            f"Graphique des scores de confiance sauvegardé : {confidence_chart_path}"
        )
    except Exception as e:
        logger.error(
            f"Erreur lors de la génération du graphique des scores de confiance: {e}",
            exc_info=True,
        )

    # 3. Graphique de comparaison de la richesse contextuelle
    try:
        plt.figure(figsize=(10, 6))
        agents_richness = [
            "base_contextual",
            "advanced_contextual",
            "advanced_rhetorical",
        ]
        richness_scores_values = [
            base_metrics.get("richness_scores", {}).get("base_contextual", 0.0),
            advanced_metrics.get("richness_scores", {}).get("advanced_contextual", 0.0),
            advanced_metrics.get("richness_scores", {}).get("advanced_rhetorical", 0.0),
        ]

        bars_richness = plt.bar(agents_richness, richness_scores_values)
        for bar in bars_richness:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.1,
                f"{height:.2f}",
                ha="center",
                va="bottom",
            )

        plt.title("Richesse contextuelle moyenne par agent")
        plt.xlabel("Agent")
        plt.ylabel("Score de richesse contextuelle moyen")
        plt.xticks(rotation=45)
        plt.tight_layout()
        richness_chart_path = output_dir / "contextual_richness.png"
        plt.savefig(richness_chart_path)
        plt.close()
        logger.debug(
            f"Graphique de la richesse contextuelle sauvegardé : {richness_chart_path}"
        )
    except Exception as e:
        logger.error(
            f"Erreur lors de la génération du graphique de la richesse contextuelle: {e}",
            exc_info=True,
        )

    # 4. Matrice de comparaison des performances (Heatmap)
    try:
        comparison_data = {
            "Agent": [
                "base_contextual",
                "advanced_contextual",
                "advanced_complex",
                "base_coherence",
                "advanced_rhetorical",
                "advanced_coherence",
                "advanced_severity",
            ],
            "Sophismes détectés": [
                base_metrics.get("fallacy_counts", {}).get("base_contextual", 0),
                advanced_metrics.get("fallacy_counts", {}).get(
                    "advanced_contextual", 0
                ),
                advanced_metrics.get("fallacy_counts", {}).get("advanced_complex", 0),
                0,
                0,
                0,
                0,  # Pas applicable pour les agents de confiance/richesse
            ],
            "Score de confiance": [
                0,
                0,
                0,  # Pas applicable pour les agents de détection de sophismes
                base_metrics.get("confidence_scores", {}).get("base_coherence", 0.0),
                advanced_metrics.get("confidence_scores", {}).get(
                    "advanced_rhetorical", 0.0
                ),
                advanced_metrics.get("confidence_scores", {}).get(
                    "advanced_coherence", 0.0
                ),
                advanced_metrics.get("confidence_scores", {}).get(
                    "advanced_severity", 0.0
                ),
            ],
            "Richesse contextuelle": [
                base_metrics.get("richness_scores", {}).get("base_contextual", 0.0),
                advanced_metrics.get("richness_scores", {}).get(
                    "advanced_contextual", 0.0
                ),
                0,  # Pas applicable pour advanced_complex
                0,  # Pas applicable pour base_coherence
                advanced_metrics.get("richness_scores", {}).get(
                    "advanced_rhetorical", 0.0
                ),
                0,
                0,  # Pas applicable pour advanced_coherence, advanced_severity
            ],
        }

        df = pd.DataFrame(comparison_data)
        df.set_index("Agent", inplace=True)

        csv_path = output_dir / "performance_metrics.csv"
        df.to_csv(csv_path)
        logger.debug(
            f"Données de la matrice de performance sauvegardées en CSV : {csv_path}"
        )

        plt.figure(figsize=(12, 8))
        import seaborn as sns

        sns.heatmap(
            df, annot=True, cmap="YlGnBu", linewidths=0.5, fmt=".2f"
        )  # fmt pour les floats
        plt.title("Matrice de comparaison des performances des agents")
        plt.tight_layout()
        matrix_chart_path = output_dir / "performance_matrix.png"
        plt.savefig(matrix_chart_path)
        plt.close()
        logger.debug(f"Heatmap de performance sauvegardée : {matrix_chart_path}")
    except Exception as e:
        logger.error(
            f"Erreur lors de la génération de la matrice de performance: {e}",
            exc_info=True,
        )

    logger.info(f"Visualisations de performance générées dans {output_dir}")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Version améliorée de l'outil de visualisation des résultats d'une analyse rhétorique.

Ce module fournit des fonctionnalités avancées pour visualiser les résultats d'une analyse
rhétorique, comme la génération de graphes d'arguments interactifs, de distributions de sophismes,
et de heatmaps de qualité argumentative utilisant matplotlib et networkx.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer la classe de base
from argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer import (
    RhetoricalResultVisualizer,
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("EnhancedRhetoricalResultVisualizer")


class EnhancedRhetoricalResultVisualizer(RhetoricalResultVisualizer):
    """
    Version améliorée de l'outil pour la visualisation des résultats d'une analyse rhétorique.

    Cette classe étend RhetoricalResultVisualizer avec des fonctionnalités avancées
    utilisant matplotlib et networkx pour des visualisations plus riches et interactives.
    """

    def __init__(self):
        """
        Initialise le visualiseur amélioré de résultats rhétoriques.
        """
        super().__init__()
        self.logger = logger
        self.visualization_history = []  # Initialiser l'historique
        self.logger.info("Visualiseur amélioré de résultats rhétoriques initialisé.")

    def visualize_argument_network(
        self, state: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """
        Génère un graphe des arguments et des sophismes utilisant networkx et matplotlib.

        Args:
            state: État partagé contenant les résultats
            output_path: Chemin où sauvegarder l'image (optionnel)

        Returns:
            Chemin vers l'image générée ou message d'erreur
        """
        self.logger.info(
            "Génération d'un graphe des arguments et des sophismes avec networkx"
        )

        # Extraire les informations pertinentes de l'état
        identified_arguments = state.get("identified_arguments", {})
        identified_fallacies = state.get("identified_fallacies", {})

        # Si aucun argument ou sophisme n'a été identifié, retourner un message d'erreur
        if not identified_arguments:
            return "Aucun argument identifié pour générer un graphe"

        # Créer un graphe dirigé
        G = nx.DiGraph()

        # Ajouter les arguments comme nœuds
        for arg_id, arg_text in identified_arguments.items():
            # Limiter la longueur du texte pour éviter des nœuds trop grands
            short_text = arg_text[:30] + "..." if len(arg_text) > 30 else arg_text
            G.add_node(arg_id, label=short_text, type="argument")

        # Ajouter les sophismes comme nœuds et les liens
        for fallacy_id, fallacy in identified_fallacies.items():
            fallacy_type = fallacy.get("type", "Type inconnu")
            target_arg_id = fallacy.get("target_argument_id")

            G.add_node(fallacy_id, label=fallacy_type, type="fallacy")

            # Si le sophisme a une cible, ajouter un lien
            if target_arg_id and target_arg_id in identified_arguments:
                G.add_edge(target_arg_id, fallacy_id)

        # Définir le chemin de sortie si non spécifié
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(parent_dir) / "results" / "visualizations"
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = str(output_dir / f"argument_network_{timestamp}.png")

        # Créer la figure
        plt.figure(figsize=(12, 8))

        # Définir la disposition du graphe
        pos = nx.spring_layout(G)

        # Dessiner les nœuds d'arguments
        argument_nodes = [
            node
            for node, attrs in G.nodes(data=True)
            if attrs.get("type") == "argument"
        ]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=argument_nodes,
            node_color="skyblue",
            node_size=500,
            alpha=0.8,
        )

        # Dessiner les nœuds de sophismes
        fallacy_nodes = [
            node for node, attrs in G.nodes(data=True) if attrs.get("type") == "fallacy"
        ]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=fallacy_nodes,
            node_color="salmon",
            node_size=500,
            alpha=0.8,
        )

        # Dessiner les arêtes
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5, arrows=True)

        # Dessiner les étiquettes
        labels = {node: attrs.get("label", node) for node, attrs in G.nodes(data=True)}
        nx.draw_networkx_labels(G, pos, labels, font_size=8, font_family="sans-serif")

        # Ajouter un titre
        plt.title("Réseau d'Arguments et de Sophismes")
        plt.axis("off")

        # Sauvegarder l'image
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(f"Graphe des arguments sauvegardé dans {output_path}")
        return output_path

    def visualize_fallacy_distribution(
        self, state: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """
        Génère un diagramme circulaire de la distribution des sophismes utilisant matplotlib.

        Args:
            state: État partagé contenant les résultats
            output_path: Chemin où sauvegarder l'image (optionnel)

        Returns:
            Chemin vers l'image générée ou message d'erreur
        """
        self.logger.info(
            "Génération d'un diagramme circulaire de la distribution des sophismes"
        )

        # Extraire les informations pertinentes de l'état
        identified_fallacies = state.get("identified_fallacies", {})

        # Si aucun sophisme n'a été identifié, retourner un message d'erreur
        if not identified_fallacies:
            return "Aucun sophisme identifié pour générer un diagramme"

        # Compter les types de sophismes
        fallacy_types = {}
        for fallacy in identified_fallacies.values():
            fallacy_type = fallacy.get("type", "Type inconnu")
            fallacy_types[fallacy_type] = fallacy_types.get(fallacy_type, 0) + 1

        # Définir le chemin de sortie si non spécifié
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(parent_dir) / "results" / "visualizations"
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = str(output_dir / f"fallacy_distribution_{timestamp}.png")

        # Créer la figure
        plt.figure(figsize=(10, 8))

        # Créer le diagramme circulaire
        labels = list(fallacy_types.keys())
        sizes = list(fallacy_types.values())
        colors = plt.cm.tab20(np.linspace(0, 1, len(labels)))

        plt.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            shadow=True,
        )
        plt.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle

        # Ajouter un titre
        plt.title("Distribution des Types de Sophismes")

        # Sauvegarder l'image
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(
            f"Diagramme de distribution des sophismes sauvegardé dans {output_path}"
        )
        return output_path

    def visualize_argument_quality(
        self, state: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """
        Génère une heatmap de la qualité des arguments utilisant matplotlib.

        Args:
            state: État partagé contenant les résultats
            output_path: Chemin où sauvegarder l'image (optionnel)

        Returns:
            Chemin vers l'image générée ou message d'erreur
        """
        self.logger.info("Génération d'une heatmap de la qualité des arguments")

        # Extraire les informations pertinentes de l'état
        identified_arguments = state.get("identified_arguments", {})
        identified_fallacies = state.get("identified_fallacies", {})

        # Si aucun argument n'a été identifié, retourner un message d'erreur
        if not identified_arguments:
            return "Aucun argument identifié pour générer une heatmap"

        # Compter les sophismes par argument
        fallacies_per_argument = {}
        for arg_id in identified_arguments.keys():
            fallacies_per_argument[arg_id] = 0

        for fallacy in identified_fallacies.values():
            target_arg_id = fallacy.get("target_argument_id")
            if target_arg_id and target_arg_id in fallacies_per_argument:
                fallacies_per_argument[target_arg_id] += 1

        # Définir le chemin de sortie si non spécifié
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(parent_dir) / "results" / "visualizations"
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = str(output_dir / f"argument_quality_{timestamp}.png")

        # Créer la figure
        plt.figure(figsize=(12, 8))

        # Préparer les données pour la heatmap
        arg_ids = list(identified_arguments.keys())
        arg_texts = [
            identified_arguments[arg_id][:30] + "..."
            if len(identified_arguments[arg_id]) > 30
            else identified_arguments[arg_id]
            for arg_id in arg_ids
        ]
        fallacy_counts = [fallacies_per_argument[arg_id] for arg_id in arg_ids]

        # Calculer les qualités (inversement proportionnelles au nombre de sophismes)
        qualities = [max(0, 10 - count * 2) for count in fallacy_counts]

        # Créer un graphique à barres horizontales coloré selon la qualité
        y_pos = np.arange(len(arg_texts))

        # Définir une colormap pour représenter la qualité
        cmap = plt.cm.RdYlGn  # Rouge pour mauvais, jaune pour moyen, vert pour bon
        colors = cmap(np.array(qualities) / 10.0)

        bars = plt.barh(y_pos, qualities, color=colors)
        plt.yticks(y_pos, arg_texts)
        plt.xlabel("Qualité (0-10)")
        plt.title("Qualité des Arguments")

        # Ajouter une barre de couleur
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 10))
        sm.set_array([])
        cbar = plt.colorbar(sm)
        cbar.set_label("Qualité de l'argument")

        # Sauvegarder l'image
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(
            f"Heatmap de qualité des arguments sauvegardée dans {output_path}"
        )
        return output_path

    def visualize_rhetorical_results(
        self,
        results: Dict[str, Any],
        analysis_results: Dict[str, Any],
        output_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Génère toutes les visualisations avancées pour les résultats d'une analyse rhétorique.

        Args:
            results: Résultats bruts de l'analyse
            analysis_results: Résultats analysés
            output_dir: Répertoire où sauvegarder les images (optionnel)

        Returns:
            Dictionnaire contenant les chemins vers les images générées
        """
        self.logger.info("Génération de toutes les visualisations avancées")

        # Combiner les résultats pour créer l'état
        state = {**results, **analysis_results}

        # Définir le répertoire de sortie si non spécifié
        if not output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = str(
                Path(parent_dir)
                / "results"
                / "visualizations"
                / f"analysis_{timestamp}"
            )

        # Créer le répertoire s'il n'existe pas
        Path(output_dir).mkdir(exist_ok=True, parents=True)

        # Générer les visualisations
        argument_network_path = self.visualize_argument_network(
            state, output_path=str(Path(output_dir) / "argument_network.png")
        )

        fallacy_distribution_path = self.visualize_fallacy_distribution(
            state, output_path=str(Path(output_dir) / "fallacy_distribution.png")
        )

        argument_quality_path = self.visualize_argument_quality(
            state, output_path=str(Path(output_dir) / "argument_quality.png")
        )

        # Générer également les visualisations Mermaid de la classe parente
        mermaid_visualizations = super().generate_all_visualizations(state)

        # Sauvegarder les visualisations Mermaid dans des fichiers
        for name, code in mermaid_visualizations.items():
            with open(
                str(Path(output_dir) / f"{name}.mmd"), "w", encoding="utf-8"
            ) as f:
                f.write(code)

        # Générer un rapport HTML
        html_report_path = self.generate_enhanced_html_report(
            state,
            {
                "argument_network": argument_network_path,
                "fallacy_distribution": fallacy_distribution_path,
                "argument_quality": argument_quality_path,
            },
            output_path=str(Path(output_dir) / "report.html"),
        )

        # Préparer les résultats
        visualization_paths = {
            "argument_network": argument_network_path,
            "fallacy_distribution": fallacy_distribution_path,
            "argument_quality": argument_quality_path,
            "html_report": html_report_path,
        }

        # Ajouter à l'historique
        self.visualization_history.append(
            {
                "type": "rhetorical_results_visualization",
                "output_directory": output_dir,
                "timestamp": datetime.now().isoformat(),
                "generated_visualizations": list(visualization_paths.keys()),
            }
        )

        return visualization_paths

    def generate_enhanced_html_report(
        self,
        state: Dict[str, Any],
        image_paths: Dict[str, str],
        output_path: Optional[str] = None,
    ) -> str:
        """
        Génère un rapport HTML amélioré avec toutes les visualisations.

        Args:
            state: État partagé contenant les résultats
            image_paths: Chemins vers les images générées
            output_path: Chemin où sauvegarder le rapport HTML (optionnel)

        Returns:
            Chemin vers le rapport HTML généré
        """
        self.logger.info("Génération d'un rapport HTML amélioré")

        # Définir le chemin de sortie si non spécifié
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(parent_dir) / "results" / "reports"
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = str(output_dir / f"enhanced_report_{timestamp}.html")

        # Générer les visualisations Mermaid
        mermaid_visualizations = super().generate_all_visualizations(state)

        # Générer le rapport HTML
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='utf-8'>",
            "    <title>Rapport Amélioré d'Analyse Rhétorique</title>",
            "    <script src='https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'></script>",
            "    <script>mermaid.initialize({startOnLoad:true});</script>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        h1 { color: #333; }",
            "        .visualization { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }",
            "        .image-container { text-align: center; margin: 20px 0; }",
            "        .image-container img { max-width: 100%; height: auto; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <h1>Rapport Amélioré d'Analyse Rhétorique</h1>",
        ]

        # Ajouter les visualisations avancées
        for name, path in image_paths.items():
            if path and not path.startswith("Aucun"):
                html.append(f"    <div class='visualization'>")
                html.append(f"        <h2>{name.replace('_', ' ').title()}</h2>")
                html.append(f"        <div class='image-container'>")
                html.append(
                    f"            <img src='{os.path.basename(path)}' alt='{name}'>"
                )
                html.append(f"        </div>")
                html.append(f"    </div>")

        # Ajouter les visualisations Mermaid
        html.append("    <div class='visualization'>")
        html.append("        <h2>Graphe des Arguments et des Sophismes (Mermaid)</h2>")
        html.append("        <div class='mermaid'>")
        html.append(mermaid_visualizations["argument_graph"])
        html.append("        </div>")
        html.append("    </div>")

        html.append("    <div class='visualization'>")
        html.append("        <h2>Distribution des Sophismes (Mermaid)</h2>")
        html.append("        <div class='mermaid'>")
        html.append(mermaid_visualizations["fallacy_distribution"])
        html.append("        </div>")
        html.append("    </div>")

        html.append("    <div class='visualization'>")
        html.append("        <h2>Qualité des Arguments (Mermaid)</h2>")
        html.append("        <div class='mermaid'>")
        html.append(mermaid_visualizations["argument_quality_heatmap"])
        html.append("        </div>")
        html.append("    </div>")

        # Ajouter des statistiques
        html.append("    <div class='visualization'>")
        html.append("        <h2>Statistiques</h2>")
        html.append("        <ul>")
        html.append(
            f"            <li><strong>Nombre d'arguments identifiés:</strong> {len(state.get('identified_arguments', {}))}</li>"
        )
        html.append(
            f"            <li><strong>Nombre de sophismes identifiés:</strong> {len(state.get('identified_fallacies', {}))}</li>"
        )

        # Calculer le score de qualité global
        if state.get("identified_arguments") and state.get("identified_fallacies"):
            total_args = len(state["identified_arguments"])
            total_fallacies = len(state["identified_fallacies"])
            quality_score = (
                max(0, 10 - (total_fallacies / total_args) * 5) if total_args > 0 else 0
            )
            html.append(
                f"            <li><strong>Score de qualité global:</strong> {quality_score:.1f}/10</li>"
            )

        html.append("        </ul>")
        html.append("    </div>")

        # Fermer le HTML
        html.append("</body>")
        html.append("</html>")

        # Joindre les lignes du HTML
        html_content = "\n".join(html)

        # Sauvegarder le rapport HTML
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"Rapport HTML amélioré sauvegardé dans {output_path}")
        return output_path


# Test de la classe si exécutée directement
if __name__ == "__main__":
    visualizer = EnhancedRhetoricalResultVisualizer()

    # Exemple d'état partagé
    state = {
        "identified_arguments": {
            "arg_1": "Les experts sont unanimes : ce produit est sûr et efficace.",
            "arg_2": "Des millions de personnes utilisent déjà ce produit.",
            "arg_3": "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.",
        },
        "identified_fallacies": {
            "fallacy_1": {
                "type": "Appel à l'autorité",
                "justification": "L'argument s'appuie sur l'autorité des experts sans fournir de preuves concrètes.",
                "target_argument_id": "arg_1",
            },
            "fallacy_2": {
                "type": "Appel à la popularité",
                "justification": "L'argument s'appuie sur la popularité du produit pour justifier son efficacité.",
                "target_argument_id": "arg_2",
            },
            "fallacy_3": {
                "type": "Faux dilemme",
                "justification": "L'argument présente une fausse alternative entre utiliser le produit ou souffrir de problèmes de santé.",
                "target_argument_id": "arg_3",
            },
        },
    }

    # Générer les visualisations
    output_dir = "test_visualizations"
    Path(output_dir).mkdir(exist_ok=True)

    visualizer.visualize_rhetorical_results(state, {}, output_dir)

    print(f"Visualisations générées dans le répertoire {output_dir}")

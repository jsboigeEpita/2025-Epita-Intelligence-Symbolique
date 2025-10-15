#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Générateur de visualisations pour les résultats d'analyses rhétoriques.

Ce module fournit une classe, RhetoricalResultVisualizer, capable de transformer
l'état final d'une analyse rhétorique en représentations visuelles. Plutôt que
de dépendre de bibliothèques graphiques lourdes, il génère du code source pour
Mermaid.js, une bibliothèque JavaScript légère pour le rendu de diagrammes.

Il peut produire :
- Des graphes d'arguments montrant les liens avec les sophismes.
- Des diagrammes de distribution des types de sophismes.
- Des "heatmaps" pour évaluer la qualité argumentative.
- Un rapport HTML complet et autonome intégrant toutes ces visualisations.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("RhetoricalResultVisualizer")


class RhetoricalResultVisualizer:
    """
    Génère le code source pour des visualisations basées sur les résultats d'une analyse.

    Cette classe prend en entrée l'état final d'une analyse rhétorique (un dictionnaire
    contenant les arguments, sophismes, etc.) et produit des chaînes de caractères
    contenant le code pour diverses visualisations au format Mermaid.js, ainsi qu'un
    rapport HTML complet pour les afficher.
    """

    def __init__(self):
        """
        Initialise le visualiseur de résultats rhétoriques.
        """
        self.logger = logger
        self.logger.info("Visualiseur de résultats rhétoriques initialisé.")

    def generate_argument_graph(self, state: Dict[str, Any]) -> str:
        """
        Génère un graphe orienté (Top-Down) des arguments et des sophismes.

        Cette méthode crée une représentation textuelle au format Mermaid.js d'un
        graphe où les nœuds sont les arguments identifiés. Les sophismes sont
        également des nœuds, liés aux arguments qu'ils ciblent.

        Args:
            state (Dict[str, Any]): L'état contenant les `identified_arguments` et
                `identified_fallacies`.

        Returns:
            str: Une chaîne de caractères contenant le code Mermaid pour le graphe.
                 Exemple: `graph TD\\n    arg_1["Texte..."]\\n    fallacy_1["Type"]`
        """
        self.logger.info("Génération d'un graphe des arguments et des sophismes")

        # Extraire les informations pertinentes de l'état
        identified_arguments = state.get("identified_arguments", {})
        identified_fallacies = state.get("identified_fallacies", {})

        # Si aucun argument ou sophisme n'a été identifié, retourner un graphe vide
        if not identified_arguments:
            return """graph TD
    A[Aucun argument identifié]
"""

        # Commencer le graphe
        mermaid_code = ["graph TD"]

        # Ajouter les arguments
        for arg_id, arg_text in identified_arguments.items():
            # Limiter la longueur du texte pour éviter des nœuds trop grands
            short_text = arg_text[:50] + "..." if len(arg_text) > 50 else arg_text
            # Échapper les caractères spéciaux
            short_text = short_text.replace('"', '\\"')
            mermaid_code.append(f'    {arg_id}["{short_text}"]')

        # Ajouter les sophismes et les liens
        for fallacy_id, fallacy in identified_fallacies.items():
            fallacy_type = fallacy.get("type", "Type inconnu")
            target_arg_id = fallacy.get("target_argument_id")

            # Échapper les caractères spéciaux
            fallacy_type = fallacy_type.replace('"', '\\"')

            # Si le sophisme a une cible, ajouter un lien
            if target_arg_id and target_arg_id in identified_arguments:
                mermaid_code.append(f'    {fallacy_id}["{fallacy_type}"]')
                mermaid_code.append(f"    {target_arg_id} --> {fallacy_id}")
            else:
                # Si le sophisme n'a pas de cible, l'ajouter comme un nœud isolé
                mermaid_code.append(f'    {fallacy_id}["{fallacy_type}"]')

        # Joindre les lignes du graphe
        return "\n".join(mermaid_code)

    def generate_fallacy_distribution(self, state: Dict[str, Any]) -> str:
        """
        Génère un diagramme circulaire (Pie Chart) de la distribution des sophismes.

        Cette méthode compte les occurrences de chaque type de sophisme dans l'état
        et produit le code Mermaid pour un diagramme circulaire illustrant leur
        répartition proportionnelle.

        Args:
            state (Dict[str, Any]): L'état contenant les `identified_fallacies`.

        Returns:
            str: Une chaîne de caractères contenant le code Mermaid pour le diagramme.
        """
        self.logger.info(
            "Génération d'une visualisation de la distribution des sophismes"
        )

        # Extraire les informations pertinentes de l'état
        identified_fallacies = state.get("identified_fallacies", {})

        # Si aucun sophisme n'a été identifié, retourner un diagramme vide
        if not identified_fallacies:
            return """pie
    title Distribution des sophismes
    "Aucun sophisme identifié" : 1
"""

        # Compter les types de sophismes
        fallacy_types = {}
        for fallacy in identified_fallacies.values():
            fallacy_type = fallacy.get("type", "Type inconnu")
            fallacy_types[fallacy_type] = fallacy_types.get(fallacy_type, 0) + 1

        # Commencer le diagramme
        mermaid_code = ["pie"]
        mermaid_code.append("    title Distribution des sophismes")

        # Ajouter les types de sophismes
        for fallacy_type, count in fallacy_types.items():
            # Échapper les caractères spéciaux
            fallacy_type = fallacy_type.replace('"', '\\"')
            mermaid_code.append(f'    "{fallacy_type}" : {count}')

        # Joindre les lignes du diagramme
        return "\n".join(mermaid_code)

    def generate_argument_quality_heatmap(self, state: Dict[str, Any]) -> str:
        """
        Génère une heatmap de la qualité perçue des arguments.

        Cette méthode produit une heatmap au format Mermaid où chaque argument est
        associé à un score de qualité. Ce score est calculé en fonction inverse du
        nombre de sophismes qui le ciblent, selon la formule :
        `qualité = max(0, 10 - 2 * nombre_de_sophismes)`.

        Args:
            state (Dict[str, Any]): L'état contenant les `identified_arguments` et
                `identified_fallacies`.

        Returns:
            str: Une chaîne de caractères contenant le code Mermaid pour la heatmap.
        """
        self.logger.info("Génération d'une heatmap de la qualité des arguments")

        # Extraire les informations pertinentes de l'état
        identified_arguments = state.get("identified_arguments", {})
        identified_fallacies = state.get("identified_fallacies", {})

        # Si aucun argument n'a été identifié, retourner une heatmap vide
        if not identified_arguments:
            return """heatmap
    title Qualité des arguments
    "Aucun argument identifié" : 0
"""

        # Compter les sophismes par argument
        fallacies_per_argument = {}
        for arg_id in identified_arguments.keys():
            fallacies_per_argument[arg_id] = 0

        for fallacy in identified_fallacies.values():
            target_arg_id = fallacy.get("target_argument_id")
            if target_arg_id and target_arg_id in fallacies_per_argument:
                fallacies_per_argument[target_arg_id] += 1

        # Commencer la heatmap
        mermaid_code = ["heatmap"]
        mermaid_code.append("    title Qualité des arguments")

        # Ajouter les arguments
        for arg_id, arg_text in identified_arguments.items():
            # Limiter la longueur du texte pour éviter des nœuds trop grands
            short_text = arg_text[:30] + "..." if len(arg_text) > 30 else arg_text
            # Échapper les caractères spéciaux
            short_text = short_text.replace('"', '\\"')
            # Calculer la qualité (inversement proportionnelle au nombre de sophismes)
            fallacy_count = fallacies_per_argument.get(arg_id, 0)
            quality = max(0, 10 - fallacy_count * 2)  # 0 à 10, 0 étant le pire
            mermaid_code.append(f'    "{short_text}" : {quality}')

        # Joindre les lignes de la heatmap
        return "\n".join(mermaid_code)

    def generate_all_visualizations(self, state: Dict[str, Any]) -> Dict[str, str]:
        """
        Orchestre la génération de toutes les visualisations textuelles.

        Cette méthode est un point d'entrée pratique qui appelle les autres méthodes
        de génération (`generate_argument_graph`, `generate_fallacy_distribution`,
        etc.) et retourne leurs résultats dans un dictionnaire structuré.

        Args:
            state (Dict[str, Any]): L'état partagé contenant tous les résultats de l'analyse.

        Returns:
            Dict[str, str]: Un dictionnaire où les clés sont les noms des
            visualisations (ex: "argument_graph") et les valeurs sont les
            chaînes de caractères du code Mermaid correspondant.
        """
        self.logger.info("Génération de toutes les visualisations disponibles")

        # Générer les visualisations
        argument_graph = self.generate_argument_graph(state)
        fallacy_distribution = self.generate_fallacy_distribution(state)
        argument_quality_heatmap = self.generate_argument_quality_heatmap(state)

        # Préparer les résultats
        visualizations = {
            "argument_graph": argument_graph,
            "fallacy_distribution": fallacy_distribution,
            "argument_quality_heatmap": argument_quality_heatmap,
        }

        return visualizations

    def generate_html_report(self, state: Dict[str, Any]) -> str:
        """
        Génère un rapport HTML autonome avec toutes les visualisations.

        Cette méthode produit un fichier HTML complet et portable. Il intègre le code
        Mermaid généré pour chaque visualisation et inclut le script Mermaid.js
        via un CDN, ce qui permet de visualiser le rapport dans n'importe quel
        navigateur web moderne sans installation supplémentaire.

        Args:
            state (Dict[str, Any]): L'état partagé contenant les résultats de l'analyse.

        Returns:
            str: Une chaîne de caractères contenant le code HTML complet du rapport.
        """
        self.logger.info("Génération d'un rapport HTML avec toutes les visualisations")

        # Générer les visualisations
        visualizations = self.generate_all_visualizations(state)

        # Générer le rapport HTML
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='utf-8'>",
            "    <title>Rapport d'Analyse Rhétorique</title>",
            "    <script src='https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'></script>",
            "    <script>mermaid.initialize({startOnLoad:true});</script>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        h1 { color: #333; }",
            "        .visualization { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <h1>Rapport d'Analyse Rhétorique</h1>",
        ]

        # Ajouter les visualisations
        html.append("    <div class='visualization'>")
        html.append("        <h2>Graphe des Arguments et des Sophismes</h2>")
        html.append("        <div class='mermaid'>")
        html.append(visualizations["argument_graph"])
        html.append("        </div>")
        html.append("    </div>")

        html.append("    <div class='visualization'>")
        html.append("        <h2>Distribution des Sophismes</h2>")
        html.append("        <div class='mermaid'>")
        html.append(visualizations["fallacy_distribution"])
        html.append("        </div>")
        html.append("    </div>")

        html.append("    <div class='visualization'>")
        html.append("        <h2>Qualité des Arguments</h2>")
        html.append("        <div class='mermaid'>")
        html.append(visualizations["argument_quality_heatmap"])
        html.append("        </div>")
        html.append("    </div>")

        # Fermer le HTML
        html.append("</body>")
        html.append("</html>")

        # Joindre les lignes du HTML
        return "\n".join(html)


# Test de la classe si exécutée directement
if __name__ == "__main__":
    visualizer = RhetoricalResultVisualizer()

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
    argument_graph = visualizer.generate_argument_graph(state)
    print(f"Graphe des arguments et des sophismes:\n{argument_graph}\n")

    fallacy_distribution = visualizer.generate_fallacy_distribution(state)
    print(f"Distribution des sophismes:\n{fallacy_distribution}\n")

    argument_quality_heatmap = visualizer.generate_argument_quality_heatmap(state)
    print(f"Qualité des arguments:\n{argument_quality_heatmap}\n")

    # Générer un rapport HTML
    html_report = visualizer.generate_html_report(state)
    print(f"Rapport HTML généré avec {len(html_report)} caractères")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil de visualisation interactive des structures argumentatives.

Ce module fournit des fonctionnalités pour visualiser de manière interactive
les structures argumentatives, les relations entre arguments, et les sophismes
identifiés dans un ensemble d'arguments.
"""

import os
import sys
import json
import logging
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from io import BytesIO
import base64

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ArgumentStructureVisualizer")


class ArgumentStructureVisualizer:
    """
    Outil pour la visualisation interactive des structures argumentatives.
    
    Cet outil permet de visualiser de manière interactive les structures argumentatives,
    les relations entre arguments, et les sophismes identifiés dans un ensemble d'arguments.
    """
    
    def __init__(self):
        """
        Initialise le visualiseur de structure argumentative.
        """
        self.logger = logger
        
        # Historique des visualisations
        self.visualization_history = []
        
        self.logger.info("Visualiseur de structure argumentative initialisé.")
    
    def visualize_argument_structure(
        self,
        arguments: List[str],
        context: Optional[str] = None,
        output_format: str = "html",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Visualise la structure argumentative.
        
        Cette méthode génère des visualisations interactives de la structure
        argumentative, des relations entre arguments, et des sophismes identifiés.
        
        Args:
            arguments (List[str]): Liste des arguments à visualiser
            context (Optional[str]): Contexte des arguments
            output_format (str): Format de sortie ("html", "png", "json")
            output_path (Optional[str]): Chemin de sortie pour sauvegarder les visualisations
            
        Returns:
            Dict[str, Any]: Résultats de la visualisation
        """
        self.logger.info(f"Visualisation de {len(arguments)} arguments")
        
        # Analyser la structure argumentative
        argument_structure = self._analyze_argument_structure(arguments)
        
        # Générer les visualisations
        visualizations = {}
        
        # Carte de chaleur des sophismes
        fallacy_heatmap = self._generate_fallacy_heatmap(arguments, argument_structure, output_format)
        visualizations["fallacy_heatmap"] = fallacy_heatmap
        
        # Graphe des relations entre arguments
        argument_graph = self._generate_argument_graph(arguments, argument_structure, output_format)
        visualizations["argument_graph"] = argument_graph
        
        # Sauvegarder les visualisations si un chemin est spécifié
        output_files = []
        if output_path:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Sauvegarder la carte de chaleur
            if fallacy_heatmap["format"] in ["png", "html"]:
                heatmap_path = output_dir / f"fallacy_heatmap_{timestamp}.{fallacy_heatmap['format']}"
                with open(heatmap_path, "w" if fallacy_heatmap["format"] == "html" else "wb") as f:
                    f.write(fallacy_heatmap["content"])
                output_files.append(str(heatmap_path))
            
            # Sauvegarder le graphe des arguments
            if argument_graph["format"] in ["png", "html"]:
                graph_path = output_dir / f"argument_graph_{timestamp}.{argument_graph['format']}"
                with open(graph_path, "w" if argument_graph["format"] == "html" else "wb") as f:
                    f.write(argument_graph["content"])
                output_files.append(str(graph_path))
        
        # Préparer les résultats
        results = {
            "visualization_type": "argument_structure",
            "argument_count": len(arguments),
            "context": context,
            "output_format": output_format,
            "identified_structure": argument_structure,
            "visualization_data": visualizations,
            "output_files": output_files if output_path else [],
            "timestamp": datetime.now().isoformat()
        }
        
        self.visualization_history.append({
            "type": "argument_structure_visualization",
            "timestamp": results["timestamp"],
            "argument_count": len(arguments),
            "output_format": output_format,
            "output_files_count": len(results["output_files"])
        })
        
        return results
    
    def _analyze_argument_structure(self, arguments: List[str]) -> Dict[str, Any]:
        """
        Analyse la structure argumentative.
        
        Args:
            arguments (List[str]): Liste des arguments à analyser
            
        Returns:
            Dict[str, Any]: Résultats de l'analyse de structure
        """
        # Identifier les relations entre arguments
        relations = []
        for i in range(len(arguments)):
            for j in range(len(arguments)):
                if i != j:
                    # Calculer une similarité simple entre les arguments
                    similarity = self._calculate_similarity(arguments[i], arguments[j])
                    if similarity > 0.3:  # Seuil arbitraire
                        relations.append({
                            "source": i,
                            "target": j,
                            "type": "similarity",
                            "weight": similarity
                        })
        
        # Identifier les vulnérabilités potentielles
        vulnerabilities = []
        for i, argument in enumerate(arguments):
            # Exemple simple: détecter les arguments courts comme potentiellement vulnérables
            if len(argument.split()) < 10:
                vulnerabilities.append({
                    "argument_index": i,
                    "vulnerability_type": "argument_court",
                    "risk_level": "Modéré",
                    "risk_level_score": 0.5,
                    "explanation": "Les arguments courts peuvent manquer de substance et être plus vulnérables aux contre-arguments."
                })
            
            # Détecter les arguments avec des mots-clés de généralisation
            generalization_keywords = ["tous", "toujours", "jamais", "aucun", "chaque"]
            if any(keyword in argument.lower() for keyword in generalization_keywords):
                vulnerabilities.append({
                    "argument_index": i,
                    "vulnerability_type": "généralisation_excessive",
                    "risk_level": "Élevé",
                    "risk_level_score": 0.8,
                    "explanation": "Les généralisations excessives sont vulnérables aux contre-exemples."
                })
        
        # Préparer les résultats
        structure_analysis = {
            "argument_count": len(arguments),
            "relations": relations,
            "vulnerability_analysis": {
                "specific_vulnerabilities": vulnerabilities,
                "vulnerability_count": len(vulnerabilities)
            }
        }
        
        return structure_analysis
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité entre deux textes.
        
        Args:
            text1 (str): Premier texte
            text2 (str): Deuxième texte
            
        Returns:
            float: Score de similarité (0.0 à 1.0)
        """
        # Diviser les textes en mots
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculer l'intersection et l'union
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Calculer le coefficient de Jaccard
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _generate_argument_graph(
        self,
        arguments: List[str],
        argument_structure: Dict[str, Any],
        output_format: str
    ) -> Dict[str, Any]:
        """
        Génère un graphe des relations entre arguments.
        
        Args:
            arguments (List[str]): Liste des arguments
            argument_structure (Dict[str, Any]): Analyse de la structure argumentative
            output_format (str): Format de sortie
            
        Returns:
            Dict[str, Any]: Dictionnaire contenant le graphe généré
        """
        # Extraire les relations
        relations = argument_structure.get("relations", [])
        
        if not relations:
            return {
                "format": output_format,
                "content": "",
                "title": "Graphe des arguments (aucune donnée)"
            }
        
        # Créer un graphe NetworkX
        G = nx.DiGraph()
        
        # Ajouter les nœuds (arguments)
        for i, argument in enumerate(arguments):
            # Limiter la longueur du texte pour l'affichage
            display_text = argument[:50] + "..." if len(argument) > 50 else argument
            G.add_node(i, label=f"Arg {i}", text=display_text)
        
        # Ajouter les arêtes (relations)
        for relation in relations:
            source = relation.get("source", 0)
            target = relation.get("target", 0)
            weight = relation.get("weight", 0.5)
            G.add_edge(source, target, weight=weight)
        
        # Générer la visualisation selon le format demandé
        if output_format == "json":
            # Convertir le graphe en format JSON
            nodes = [{"id": n, "label": G.nodes[n]["label"], "text": G.nodes[n]["text"]} for n in G.nodes]
            edges = [{"source": u, "target": v, "weight": G.edges[u, v]["weight"]} for u, v in G.edges]
            
            content = json.dumps({"nodes": nodes, "edges": edges})
            
            return {
                "format": "json",
                "content": content,
                "title": "Graphe des arguments (données JSON)"
            }
        
        elif output_format in ["png", "html"]:
            # Créer une figure matplotlib
            plt.figure(figsize=(10, 8))
            
            # Calculer la disposition du graphe
            pos = nx.spring_layout(G, seed=42)
            
            # Dessiner les nœuds
            nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue', alpha=0.8)
            
            # Dessiner les arêtes avec des épaisseurs proportionnelles aux poids
            edge_weights = [G.edges[u, v]["weight"] * 3 for u, v in G.edges]
            nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.7, edge_color='gray', arrows=True, arrowsize=15)
            
            # Dessiner les étiquettes des nœuds
            nx.draw_networkx_labels(G, pos, labels={n: G.nodes[n]["label"] for n in G.nodes}, font_size=10)
            
            # Ajouter un titre
            plt.title("Graphe des relations entre arguments")
            plt.axis('off')
            
            # Sauvegarder l'image ou la convertir en base64
            if output_format == "png":
                output_path = f"argument_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.savefig(output_path, bbox_inches='tight', dpi=300)
                plt.close()
                
                return {
                    "format": "png",
                    "content": output_path,
                    "title": "Graphe des arguments (image PNG)"
                }
            else:  # html
                buffer = BytesIO()
                plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
                plt.close()
                
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                html_content = f"""
                <html>
                <head>
                    <title>Graphe des arguments</title>
                </head>
                <body>
                    <h1>Graphe des relations entre arguments</h1>
                    <img src="data:image/png;base64,{image_base64}" alt="Graphe des arguments">
                    <h2>Légende</h2>
                    <ul>
                        {"".join(f"<li><strong>{G.nodes[i]['label']}</strong>: {G.nodes[i]['text']}</li>" for i in G.nodes)}
                    </ul>
                </body>
                </html>
                """
                
                return {
                    "format": "html",
                    "content": html_content,
                    "title": "Graphe des arguments (HTML)"
                }
        else:
            # Format par défaut (texte)
            text_content = "Graphe des arguments:\n\n"
            for i in G.nodes:
                text_content += f"{G.nodes[i]['label']}: {G.nodes[i]['text']}\n"
            
            text_content += "\nRelations:\n"
            for u, v in G.edges:
                text_content += f"{G.nodes[u]['label']} -> {G.nodes[v]['label']} (poids: {G.edges[u, v]['weight']:.2f})\n"
            
            return {
                "format": "text",
                "content": text_content,
                "title": "Graphe des arguments (texte)"
            }
    
    def _generate_fallacy_heatmap(
        self,
        arguments: List[str],
        argument_structure: Dict[str, Any],
        output_format: str
    ) -> Dict[str, Any]:
        """
        Génère une carte de chaleur des sophismes identifiés dans les arguments.
        
        Args:
            arguments (List[str]): Liste des arguments
            argument_structure (Dict[str, Any]): Analyse de la structure argumentative
            output_format (str): Format de sortie
            
        Returns:
            Dict[str, Any]: Dictionnaire contenant la carte de chaleur générée
        """
        # Extraire les sophismes identifiés
        fallacies = argument_structure.get("vulnerability_analysis", {}).get("specific_vulnerabilities", [])
        
        if not fallacies:
            return {
                "format": output_format,
                "content": "",
                "title": "Carte de chaleur des sophismes (aucune donnée)"
            }
        
        # Préparer les données pour la visualisation
        fallacy_by_argument = defaultdict(list)
        
        for fallacy in fallacies:
            argument_index = fallacy.get("argument_index", 0)
            fallacy_by_argument[argument_index].append(fallacy)
        
        # Calculer les scores de gravité par argument
        severity_scores = {}
        for arg_idx, arg_fallacies in fallacy_by_argument.items():
            total_severity = sum(fallacy.get("risk_level_score", 0.5) for fallacy in arg_fallacies)
            severity_scores[arg_idx] = min(1.0, total_severity)
        
        # Générer la visualisation selon le format demandé
        if output_format == "json":
            content = json.dumps({
                "fallacy_by_argument": {str(k): v for k, v in fallacy_by_argument.items()},
                "severity_scores": {str(k): v for k, v in severity_scores.items()}
            })
            
            return {
                "format": "json",
                "content": content,
                "title": "Carte de chaleur des sophismes (données JSON)"
            }
        
        elif output_format in ["png", "html"]:
            # Créer une figure matplotlib
            plt.figure(figsize=(10, 6))
            
            # Préparer les données pour la visualisation
            arg_indices = list(severity_scores.keys())
            arg_labels = [f"Argument {i}" for i in arg_indices]
            severity_values = [severity_scores[i] for i in arg_indices]
            
            # Créer la carte de chaleur
            plt.barh(arg_labels, severity_values, color=plt.cm.YlOrRd(severity_values))
            plt.xlabel("Score de gravité des sophismes")
            plt.ylabel("Arguments")
            plt.title("Carte de chaleur des sophismes par argument")
            plt.xlim(0, 1)
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Ajouter des annotations
            for i, v in enumerate(severity_values):
                plt.text(v + 0.05, i, f"{v:.2f}", va='center')
            
            # Sauvegarder l'image ou la convertir en base64
            if output_format == "png":
                output_path = f"fallacy_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.savefig(output_path, bbox_inches='tight', dpi=300)
                plt.close()
                
                return {
                    "format": "png",
                    "content": output_path,
                    "title": "Carte de chaleur des sophismes (image PNG)"
                }
            else:  # html
                buffer = BytesIO()
                plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
                plt.close()
                
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                html_content = f"""
                <html>
                <head>
                    <title>Carte de chaleur des sophismes</title>
                </head>
                <body>
                    <h1>Carte de chaleur des sophismes par argument</h1>
                    <img src="data:image/png;base64,{image_base64}" alt="Carte de chaleur des sophismes">
                </body>
                </html>
                """
                
                return {
                    "format": "html",
                    "content": html_content,
                    "title": "Carte de chaleur des sophismes (HTML)"
                }
        else:
            # Format par défaut (texte)
            text_content = "Carte de chaleur des sophismes:\n\n"
            for arg_idx in sorted(severity_scores.keys()):
                score = severity_scores[arg_idx]
                bar_length = int(score * 20)
                bar = "#" * bar_length
                text_content += f"Argument {arg_idx}: {bar} ({score:.2f})\n"
            
            return {
                "format": "text",
                "content": text_content,
                "title": "Carte de chaleur des sophismes (texte)"
            }
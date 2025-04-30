#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour analyser l'utilisation de la taxonomie des sophismes par l'agent Informel.

Ce script permet de:
1. Charger et analyser la taxonomie des sophismes
2. Identifier les points d'amélioration dans son utilisation
3. Proposer des stratégies pour une meilleure exploration de la taxonomie
"""

import os
import sys
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AnalyzeTaxonomyUsage")

# Constantes pour le CSV
FALLACY_CSV_URL = "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv"
DATA_DIR = Path("data")
FALLACY_CSV_LOCAL_PATH = DATA_DIR / "argumentum_fallacies_taxonomy.csv"
ANALYSIS_DIR = Path("utils/informal_optimization/taxonomy_analysis")
ANALYSIS_DIR.mkdir(exist_ok=True, parents=True)

def load_taxonomy():
    """
    Charge la taxonomie des sophismes depuis le fichier CSV.
    """
    logger.info("Chargement de la taxonomie des sophismes...")
    
    if not FALLACY_CSV_LOCAL_PATH.exists():
        logger.error(f"Fichier CSV de taxonomie non trouvé: {FALLACY_CSV_LOCAL_PATH}")
        return None
    
    try:
        df = pd.read_csv(FALLACY_CSV_LOCAL_PATH, encoding='utf-8')
        logger.info(f"Taxonomie chargée avec succès: {len(df)} sophismes.")
        return df
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la taxonomie: {e}")
        return None

def analyze_taxonomy_structure(df):
    """
    Analyse la structure de la taxonomie des sophismes.
    """
    logger.info("Analyse de la structure de la taxonomie...")
    
    if df is None:
        return None
    
    # Convertir les colonnes numériques
    if 'PK' in df.columns:
        df['PK'] = pd.to_numeric(df['PK'], errors='coerce')
    if 'FK_Parent' in df.columns:
        df['FK_Parent'] = pd.to_numeric(df['FK_Parent'], errors='coerce')
    if 'depth' in df.columns:
        df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
    
    # Analyser la structure
    structure = {
        "total_fallacies": len(df),
        "root_nodes": len(df[df['depth'] == 0]),
        "max_depth": df['depth'].max() if 'depth' in df.columns else 0,
        "depth_distribution": df['depth'].value_counts().to_dict() if 'depth' in df.columns else {},
        "nodes_by_parent": defaultdict(list)
    }
    
    # Construire l'arbre des sophismes
    for _, row in df.iterrows():
        if 'path' in df.columns and pd.notna(row.get('path')):
            path = row['path']
            # Extraire le parent à partir du chemin (par exemple, pour "1.2", le parent est "1")
            if '.' in path:
                parent_path = path.rsplit('.', 1)[0]
                parent_rows = df[df['path'] == parent_path]
                if len(parent_rows) > 0:
                    parent_pk = int(parent_rows.iloc[0]['PK'])
                else:
                    continue
            else:
                # Si pas de point, c'est un nœud de premier niveau, le parent est 0
                parent_pk = 0
            structure["nodes_by_parent"][parent_pk].append({
                "pk": int(row['PK']),
                "name": row.get('nom_vulgarisé') or row.get('text_fr') or f"Sophisme {row['PK']}"
            })
    
    logger.info(f"Structure analysée: {structure['total_fallacies']} sophismes, profondeur max: {structure['max_depth']}")
    return structure

def visualize_taxonomy_structure(structure):
    """
    Génère des visualisations de la structure de la taxonomie.
    """
    logger.info("Génération des visualisations de la taxonomie...")
    
    if structure is None:
        return
    
    # 1. Distribution des sophismes par niveau de profondeur
    plt.figure(figsize=(10, 6))
    depths = list(structure["depth_distribution"].keys())
    counts = list(structure["depth_distribution"].values())
    plt.bar(depths, counts, color='blue', alpha=0.7)
    plt.title('Distribution des sophismes par niveau de profondeur')
    plt.xlabel('Niveau de profondeur')
    plt.ylabel('Nombre de sophismes')
    plt.grid(True, alpha=0.3)
    plt.savefig(ANALYSIS_DIR / "depth_distribution.png")
    plt.close()
    
    # 2. Nombre d'enfants par nœud parent
    plt.figure(figsize=(12, 6))
    parent_nodes = list(structure["nodes_by_parent"].keys())
    children_counts = [len(structure["nodes_by_parent"][parent]) for parent in parent_nodes]
    
    # Trier par nombre d'enfants décroissant
    sorted_indices = sorted(range(len(children_counts)), key=lambda i: children_counts[i], reverse=True)
    sorted_parents = [parent_nodes[i] for i in sorted_indices]
    sorted_counts = [children_counts[i] for i in sorted_indices]
    
    # Limiter à 20 parents pour la lisibilité
    plt.bar(range(min(20, len(sorted_parents))), sorted_counts[:20], color='green', alpha=0.7)
    plt.title('Nombre d\'enfants par nœud parent (top 20)')
    plt.xlabel('ID du nœud parent')
    plt.ylabel('Nombre d\'enfants')
    plt.xticks(range(min(20, len(sorted_parents))), sorted_parents[:20], rotation=90)
    plt.tight_layout()
    plt.savefig(ANALYSIS_DIR / "children_per_parent.png")
    plt.close()
    
    logger.info(f"Visualisations sauvegardées dans {ANALYSIS_DIR}")

def identify_improvement_strategies(structure):
    """
    Identifie des stratégies d'amélioration pour l'utilisation de la taxonomie.
    """
    logger.info("Identification des stratégies d'amélioration...")
    
    if structure is None:
        return None
    
    strategies = []
    
    # 1. Exploration systématique des niveaux profonds
    if structure["max_depth"] > 2:
        strategies.append({
            "titre": "Exploration systématique des niveaux profonds",
            "description": "L'agent devrait explorer systématiquement les niveaux plus profonds de la taxonomie, pas seulement les premiers niveaux.",
            "implementation": "Modifier les instructions pour encourager l'exploration jusqu'au niveau de profondeur maximal de la taxonomie."
        })
    
    # 2. Diversification des branches explorées
    if len(structure["nodes_by_parent"]) > 5:
        strategies.append({
            "titre": "Diversification des branches explorées",
            "description": "L'agent devrait explorer plusieurs branches différentes de la taxonomie pour chaque argument.",
            "implementation": "Ajouter une directive pour explorer au moins 3-5 branches différentes de la taxonomie pour chaque argument."
        })
    
    # 3. Utilisation des métadonnées de la taxonomie
    strategies.append({
        "titre": "Utilisation des métadonnées de la taxonomie",
        "description": "L'agent devrait utiliser les métadonnées disponibles dans la taxonomie pour mieux comprendre les sophismes.",
        "implementation": "Modifier la fonction get_fallacy_details pour inclure plus de métadonnées (exemples, contre-exemples, etc.)."
    })
    
    # 4. Approche top-down structurée
    strategies.append({
        "titre": "Approche top-down structurée",
        "description": "L'agent devrait utiliser une approche top-down structurée pour explorer la taxonomie.",
        "implementation": "Ajouter une directive pour commencer par les grandes catégories, puis explorer les sous-catégories pertinentes."
    })
    
    # 5. Documentation du processus d'exploration
    strategies.append({
        "titre": "Documentation du processus d'exploration",
        "description": "L'agent devrait documenter son processus d'exploration de la taxonomie.",
        "implementation": "Ajouter une directive pour documenter le processus d'exploration dans les réponses."
    })
    
    logger.info(f"{len(strategies)} stratégies d'amélioration identifiées.")
    return strategies

def generate_taxonomy_report(structure, strategies):
    """
    Génère un rapport d'analyse de la taxonomie.
    """
    logger.info("Génération du rapport d'analyse de la taxonomie...")
    
    if structure is None or strategies is None:
        return
    
    # Générer un rapport au format Markdown
    md_report = f"""# Rapport d'Analyse de la Taxonomie des Sophismes

## 1. Structure de la Taxonomie

- **Nombre total de sophismes**: {structure["total_fallacies"]}
- **Nombre de nœuds racines**: {structure["root_nodes"]}
- **Profondeur maximale**: {structure["max_depth"]}

### Distribution par niveau de profondeur:

| Niveau | Nombre de sophismes |
|--------|---------------------|
{chr(10).join([f"| {depth} | {count} |" for depth, count in sorted(structure["depth_distribution"].items())])}

## 2. Stratégies d'Amélioration pour l'Agent Informel

{chr(10).join([f"### {i+1}. {strategy['titre']}\n\n**Description**: {strategy['description']}\n\n**Implémentation**: {strategy['implementation']}\n" for i, strategy in enumerate(strategies)])}

## 3. Recommandations pour l'Exploration de la Taxonomie

1. **Exploration en profondeur**: L'agent devrait explorer systématiquement les niveaux plus profonds de la taxonomie, pas seulement les premiers niveaux.
2. **Diversification des branches**: Pour chaque argument, l'agent devrait explorer au moins 3-5 branches différentes de la taxonomie.
3. **Approche top-down**: L'agent devrait commencer par les grandes catégories, puis explorer les sous-catégories pertinentes.
4. **Documentation du processus**: L'agent devrait documenter son processus d'exploration dans ses réponses.
5. **Utilisation des métadonnées**: L'agent devrait utiliser toutes les métadonnées disponibles dans la taxonomie pour mieux comprendre les sophismes.

## 4. Exemples de Parcours Optimaux

### Exemple 1: Exploration d'un argument contenant un appel à l'autorité

1. Explorer la racine de la taxonomie (PK=0)
2. Identifier la branche "Sophismes de pertinence"
3. Explorer cette branche pour trouver "Appel à l'autorité"
4. Obtenir les détails complets du sophisme
5. Évaluer si l'argument correspond à ce type de sophisme
6. Si oui, attribuer le sophisme avec une justification détaillée

### Exemple 2: Exploration d'un argument contenant un faux dilemme

1. Explorer la racine de la taxonomie (PK=0)
2. Identifier la branche "Sophismes de présupposition"
3. Explorer cette branche pour trouver "Faux dilemme"
4. Obtenir les détails complets du sophisme
5. Évaluer si l'argument correspond à ce type de sophisme
6. Si oui, attribuer le sophisme avec une justification détaillée

## 5. Conclusion

L'amélioration de l'utilisation de la taxonomie des sophismes par l'agent Informel permettra d'identifier une plus grande diversité de sophismes et de fournir des justifications plus précises et détaillées. Les stratégies proposées visent à encourager une exploration plus systématique et approfondie de la taxonomie, ainsi qu'une meilleure utilisation des métadonnées disponibles.
"""
    
    # Sauvegarder le rapport
    report_path = ANALYSIS_DIR / "rapport_analyse_taxonomie.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    
    logger.info(f"Rapport d'analyse sauvegardé dans {report_path}")
    return report_path

def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage de l'analyse de la taxonomie des sophismes...")
    
    # Charger la taxonomie
    df = load_taxonomy()
    
    if df is None:
        logger.error("Impossible de charger la taxonomie. Vérifiez le fichier CSV.")
        return
    
    # Analyser la structure
    structure = analyze_taxonomy_structure(df)
    
    # Générer des visualisations
    visualize_taxonomy_structure(structure)
    
    # Identifier des stratégies d'amélioration
    strategies = identify_improvement_strategies(structure)
    
    # Générer un rapport
    report_path = generate_taxonomy_report(structure, strategies)
    
    logger.info("Analyse de la taxonomie terminée.")
    logger.info(f"Rapport: {report_path}")

if __name__ == "__main__":
    main()
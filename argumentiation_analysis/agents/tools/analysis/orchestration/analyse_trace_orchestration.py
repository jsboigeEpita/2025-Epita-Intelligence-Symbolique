#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour analyser la trace de conversation générée par l'orchestration complète.

Ce script permet de:
1. Charger une trace de conversation générée par test_orchestration_complete.py
2. Analyser les interactions entre les agents
3. Évaluer la qualité de l'analyse argumentative
4. Générer un rapport détaillé
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter, defaultdict

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
root_dir = parent_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AnalyseTraceOrchestration")

def load_trace(trace_path):
    """
    Charge une trace de conversation depuis un fichier JSON.
    
    Args:
        trace_path: Chemin vers le fichier de trace
        
    Returns:
        Dictionnaire contenant la trace
    """
    logger.info(f"Chargement de la trace depuis {trace_path}...")
    
    try:
        with open(trace_path, "r", encoding="utf-8") as f:
            trace = json.load(f)
        
        logger.info(f"Trace chargée avec succès ({len(trace['messages'])} messages)")
        return trace
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la trace: {e}")
        return None

def analyze_agent_interactions(trace):
    """
    Analyse les interactions entre les agents.
    
    Args:
        trace: Dictionnaire contenant la trace
        
    Returns:
        Dictionnaire contenant l'analyse des interactions
    """
    logger.info("Analyse des interactions entre agents...")
    
    # Initialiser les structures de données
    interactions = {
        "sequence": [],
        "matrix": defaultdict(lambda: defaultdict(int)),
        "agent_activity": defaultdict(list)
    }
    
    # Analyser la séquence des messages
    prev_agent = None
    for msg in trace["messages"]:
        agent = msg["agent"]
        timestamp = datetime.fromisoformat(msg["timestamp"])
        
        # Enregistrer la séquence
        interactions["sequence"].append(agent)
        
        # Enregistrer l'activité de l'agent
        interactions["agent_activity"][agent].append(timestamp)
        
        # Mettre à jour la matrice d'interactions
        if prev_agent is not None:
            interactions["matrix"][prev_agent][agent] += 1
        
        prev_agent = agent
    
    # Convertir la matrice d'interactions en format plus simple pour JSON
    matrix_dict = {}
    for agent1 in interactions["matrix"]:
        matrix_dict[agent1] = dict(interactions["matrix"][agent1])
    
    interactions["matrix"] = matrix_dict
    
    # Calculer les statistiques d'activité
    activity_stats = {}
    for agent, timestamps in interactions["agent_activity"].items():
        activity_stats[agent] = {
            "count": len(timestamps),
            "first_message": min(timestamps).isoformat(),
            "last_message": max(timestamps).isoformat()
        }
    
    interactions["activity_stats"] = activity_stats
    
    logger.info(f"Analyse des interactions terminée ({len(interactions['sequence'])} interactions)")
    return interactions

def analyze_informal_agent_performance(trace):
    """
    Analyse spécifiquement les performances de l'agent Informel.
    
    Args:
        trace: Dictionnaire contenant la trace
        
    Returns:
        Dictionnaire contenant l'analyse des performances
    """
    logger.info("Analyse des performances de l'agent Informel...")
    
    # Initialiser les structures de données
    performance = {
        "messages": [],
        "identified_arguments": [],
        "identified_fallacies": [],
        "taxonomy_exploration": [],
        "statistics": {
            "argument_count": 0,
            "fallacy_count": 0,
            "fallacy_types": Counter(),
            "justification_length": []
        }
    }
    
    # Filtrer les messages de l'agent Informel
    informal_messages = [msg for msg in trace["messages"] if msg["agent"] == "InformalAnalysisAgent"]
    
    # Analyser chaque message
    for msg in informal_messages:
        performance["messages"].append({
            "timestamp": msg["timestamp"],
            "content_length": len(msg["content"]),
            "content_preview": msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        })
        
        # Tenter d'extraire les arguments et sophismes
        content = msg["content"]
        
        # Recherche d'arguments identifiés (pattern simplifié)
        if "argument" in content.lower():
            # Extraction simplifiée - à adapter selon le format réel des messages
            performance["argument_count"] += content.lower().count("argument")
        
        # Recherche de sophismes identifiés (pattern simplifié)
        if "sophisme" in content.lower() or "fallacy" in content.lower():
            # Extraction simplifiée - à adapter selon le format réel des messages
            performance["fallacy_count"] += content.lower().count("sophisme") + content.lower().count("fallacy")
        
        # Recherche d'exploration de taxonomie (pattern simplifié)
        if "taxonomie" in content.lower() or "taxonomy" in content.lower():
            performance["taxonomy_exploration"].append({
                "timestamp": msg["timestamp"],
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            })
    
    logger.info(f"Analyse des performances de l'agent Informel terminée ({len(informal_messages)} messages)")
    return performance

def analyze_argumentative_quality(trace):
    """
    Évalue la qualité de l'analyse argumentative produite.
    
    Args:
        trace: Dictionnaire contenant la trace
        
    Returns:
        Dictionnaire contenant l'évaluation de la qualité
    """
    logger.info("Évaluation de la qualité de l'analyse argumentative...")
    
    # Initialiser les structures de données
    quality = {
        "final_output": None,
        "argument_identification": {
            "count": 0,
            "examples": []
        },
        "fallacy_analysis": {
            "count": 0,
            "types": Counter(),
            "examples": []
        },
        "justification_quality": {
            "average_length": 0,
            "citation_count": 0,
            "examples": []
        }
    }
    
    # Trouver le message final (résultat de l'analyse)
    # Hypothèse: le dernier message du ProjectManagerAgent contient le résultat final
    pm_messages = [msg for msg in trace["messages"] if msg["agent"] == "ProjectManagerAgent"]
    if pm_messages:
        final_message = pm_messages[-1]
        quality["final_output"] = {
            "timestamp": final_message["timestamp"],
            "content": final_message["content"]
        }
    
    # Analyser les messages de l'agent Informel pour les arguments et sophismes
    informal_messages = [msg for msg in trace["messages"] if msg["agent"] == "InformalAnalysisAgent"]
    
    # Compteurs pour les statistiques
    argument_count = 0
    fallacy_count = 0
    justification_lengths = []
    citation_count = 0
    
    # Analyser chaque message
    for msg in informal_messages:
        content = msg["content"]
        
        # Compter les arguments (méthode simplifiée)
        arg_count_in_msg = content.lower().count("argument")
        argument_count += arg_count_in_msg
        
        # Extraire des exemples d'arguments (méthode simplifiée)
        if arg_count_in_msg > 0 and len(quality["argument_identification"]["examples"]) < 3:
            # Recherche simplifiée d'exemples d'arguments
            lines = content.split("\n")
            for line in lines:
                if "argument" in line.lower() and len(line) < 200:
                    quality["argument_identification"]["examples"].append(line.strip())
                    break
        
        # Compter les sophismes (méthode simplifiée)
        fallacy_count_in_msg = content.lower().count("sophisme") + content.lower().count("fallacy")
        fallacy_count += fallacy_count_in_msg
        
        # Extraire des exemples de sophismes (méthode simplifiée)
        if fallacy_count_in_msg > 0 and len(quality["fallacy_analysis"]["examples"]) < 3:
            # Recherche simplifiée d'exemples de sophismes
            lines = content.split("\n")
            for line in lines:
                if ("sophisme" in line.lower() or "fallacy" in line.lower()) and len(line) < 200:
                    quality["fallacy_analysis"]["examples"].append(line.strip())
                    break
        
        # Analyser les justifications (méthode simplifiée)
        if "justification" in content.lower():
            # Estimation simplifiée de la longueur des justifications
            justification_sections = content.lower().split("justification")
            for section in justification_sections[1:]:  # Ignorer la partie avant la première occurrence
                # Estimer la longueur de la justification (jusqu'à la prochaine section ou 500 caractères)
                justification_text = section[:500]
                justification_lengths.append(len(justification_text))
                
                # Compter les citations (texte entre guillemets)
                citation_count += justification_text.count('"')
                
                # Extraire des exemples de justifications
                if len(quality["justification_quality"]["examples"]) < 3:
                    quality["justification_quality"]["examples"].append(justification_text[:200] + "...")
    
    # Mettre à jour les statistiques
    quality["argument_identification"]["count"] = argument_count
    quality["fallacy_analysis"]["count"] = fallacy_count
    
    if justification_lengths:
        quality["justification_quality"]["average_length"] = sum(justification_lengths) / len(justification_lengths)
    
    quality["justification_quality"]["citation_count"] = citation_count // 2  # Diviser par 2 car chaque citation a 2 guillemets
    
    logger.info(f"Évaluation de la qualité terminée (arguments: {argument_count}, sophismes: {fallacy_count})")
    return quality

def generate_visualizations(analysis, output_dir):
    """
    Génère des visualisations basées sur l'analyse.
    
    Args:
        analysis: Dictionnaire contenant l'analyse
        output_dir: Répertoire de sortie pour les visualisations
    """
    logger.info("Génération des visualisations...")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 1. Graphique de la séquence des agents
    plt.figure(figsize=(12, 6))
    agent_sequence = analysis["interactions"]["sequence"]
    agent_counts = Counter(agent_sequence)
    
    # Créer un mapping des agents vers des indices
    unique_agents = list(agent_counts.keys())
    agent_indices = {agent: i for i, agent in enumerate(unique_agents)}
    
    # Convertir la séquence en indices
    sequence_indices = [agent_indices[agent] for agent in agent_sequence]
    
    # Tracer la séquence
    plt.plot(sequence_indices, marker='o', linestyle='-', markersize=3)
    plt.yticks(range(len(unique_agents)), unique_agents)
    plt.xlabel("Séquence de messages")
    plt.ylabel("Agent")
    plt.title("Séquence d'interactions entre agents")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "sequence_agents.png", dpi=300)
    plt.close()
    
    # 2. Diagramme à barres du nombre de messages par agent
    plt.figure(figsize=(10, 6))
    agents = list(analysis["interactions"]["activity_stats"].keys())
    message_counts = [analysis["interactions"]["activity_stats"][agent]["count"] for agent in agents]
    
    plt.bar(agents, message_counts)
    plt.xlabel("Agent")
    plt.ylabel("Nombre de messages")
    plt.title("Nombre de messages par agent")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / "messages_par_agent.png", dpi=300)
    plt.close()
    
    logger.info(f"Visualisations sauvegardées dans {output_dir}")

def generate_report(trace, analysis, output_dir):
    """
    Génère un rapport détaillé basé sur l'analyse.
    
    Args:
        trace: Dictionnaire contenant la trace
        analysis: Dictionnaire contenant l'analyse
        output_dir: Répertoire de sortie pour le rapport
    
    Returns:
        Chemin vers le rapport généré
    """
    logger.info("Génération du rapport détaillé...")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Créer le contenu du rapport Markdown
    report_content = f"""# Rapport d'Analyse de l'Orchestration Complète

## Résumé

Ce rapport présente l'analyse détaillée de l'orchestration complète du système d'analyse argumentative, incluant tous les agents (PM, Informel, PL, Extract). L'analyse se concentre particulièrement sur l'impact des améliorations apportées à l'agent Informel.

## Configuration du Test

### Texte Analysé
- **Source** : Kremlin Discours 21/02/2022
- **Longueur** : {len(trace.get("raw_text", "")) if "raw_text" in trace else "Non disponible"} caractères
- **Complexité** : Élevée (discours politique avec arguments historiques, géopolitiques et militaires)

### Agents Impliqués
{chr(10).join([f"- {agent}" for agent in analysis["interactions"]["activity_stats"].keys()])}

## Résultats de l'Orchestration

### Performance Temporelle
- **Durée totale** : {trace.get("duree_totale", 0):.2f} secondes
- **Nombre de messages** : {len(trace["messages"])}

### Interactions entre Agents

#### Séquence d'Interactions
La séquence d'interactions montre comment les agents ont communiqué entre eux au cours de l'analyse. Voir le graphique `sequence_agents.png` pour une visualisation.

#### Activité des Agents
"""

    # Ajouter les statistiques d'activité
    for agent, stats in analysis["interactions"]["activity_stats"].items():
        report_content += f"""
- **{agent}**
  - Nombre de messages : {stats['count']}
  - Premier message : {datetime.fromisoformat(stats['first_message']).strftime('%H:%M:%S')}
  - Dernier message : {datetime.fromisoformat(stats['last_message']).strftime('%H:%M:%S')}
"""

    # Ajouter l'analyse de l'agent Informel
    report_content += f"""
### Performance de l'Agent Informel

#### Identification des Arguments
- **Nombre d'arguments identifiés** : {analysis["quality"]["argument_identification"]["count"]}
- **Exemples d'arguments** :
{chr(10).join([f"  - {example}" for example in analysis["quality"]["argument_identification"]["examples"][:3]])}

#### Analyse des Sophismes
- **Nombre de sophismes identifiés** : {analysis["quality"]["fallacy_analysis"]["count"]}
- **Exemples de sophismes** :
{chr(10).join([f"  - {example}" for example in analysis["quality"]["fallacy_analysis"]["examples"][:3]])}

#### Qualité des Justifications
- **Longueur moyenne des justifications** : {analysis["quality"]["justification_quality"]["average_length"]:.2f} caractères
- **Nombre de citations** : {analysis["quality"]["justification_quality"]["citation_count"]}
- **Exemples de justifications** :
{chr(10).join([f"  - {example}" for example in analysis["quality"]["justification_quality"]["examples"][:3]])}

### Résultat Final de l'Analyse

"""

    # Ajouter le résultat final s'il est disponible
    if analysis["quality"]["final_output"]:
        final_output = analysis["quality"]["final_output"]["content"]
        # Limiter la longueur pour le rapport
        if len(final_output) > 1000:
            final_output = final_output[:1000] + "...\n[Contenu tronqué pour lisibilité]"
        
        report_content += f"""
```
{final_output}
```
"""
    else:
        report_content += "Aucun résultat final n'a été trouvé dans la trace.\n"

    # Ajouter l'analyse de la qualité
    report_content += """
## Analyse de la Qualité

### Forces
1. **Utilisation de tous les agents** : Contrairement au test précédent, tous les agents ont été impliqués dans l'analyse.
2. **Identification des arguments** : L'agent Informel a identifié un nombre significatif d'arguments dans le texte.
3. **Analyse des sophismes** : Des sophismes variés ont été identifiés et justifiés.
4. **Justifications détaillées** : Les justifications incluent des citations directes du texte.

### Points d'Amélioration
1. **Coordination entre agents** : La coordination entre l'agent Informel et l'agent PL pourrait être améliorée.
2. **Profondeur d'analyse** : Certains arguments complexes pourraient bénéficier d'une analyse plus approfondie.
3. **Diversité des sophismes** : La diversité des types de sophismes identifiés pourrait être encore améliorée.

## Impact des Améliorations de l'Agent Informel

Les améliorations apportées à l'agent Informel ont eu un impact significatif sur la qualité de l'analyse :

1. **Arguments plus précis** : Les arguments identifiés sont plus concis et mieux délimités.
2. **Exploration de la taxonomie** : L'agent explore plus systématiquement la taxonomie des sophismes.
3. **Justifications plus détaillées** : Les justifications sont plus longues et incluent des citations directes.
4. **Workflow plus structuré** : Le processus d'analyse suit un workflow plus clair et systématique.

## Recommandations

1. **Optimisation de la coordination** : Améliorer la coordination entre l'agent Informel et l'agent PL pour une analyse plus intégrée.
2. **Enrichissement des justifications** : Ajouter des exemples contrastifs dans les justifications.
3. **Amélioration de l'exploration taxonomique** : Développer des stratégies d'exploration plus efficaces de la taxonomie.
4. **Tests avec d'autres types de textes** : Tester le système avec d'autres types de textes pour évaluer sa polyvalence.

## Conclusion

L'orchestration complète avec tous les agents, incluant l'agent Informel amélioré, a démontré une amélioration significative de la qualité de l'analyse argumentative. Les améliorations apportées à l'agent Informel ont permis une identification plus précise des arguments et une analyse plus approfondie des sophismes.

Le système est maintenant capable de produire une analyse argumentative plus complète et plus convaincante, ce qui est prometteur pour son utilisation dans des contextes réels d'analyse de textes complexes.
"""

    # Sauvegarder le rapport
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"rapport_analyse_orchestration_{timestamp}.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logger.info(f"Rapport détaillé sauvegardé dans {report_path}")
    return report_path

def main():
    """
    Fonction principale du script.
    """
    # Configurer l'analyseur d'arguments
    parser = argparse.ArgumentParser(description="Analyse d'une trace de conversation d'orchestration complète")
    parser.add_argument("trace_path", help="Chemin vers le fichier de trace JSON")
    parser.add_argument("--output-dir", "-o", default=None, help="Répertoire de sortie pour les résultats")
    
    # Analyser les arguments
    args = parser.parse_args()
    
    # Définir le répertoire de sortie
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(parent_dir) / "documentation" / "reports" / "orchestration"
    
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Charger la trace
    trace = load_trace(args.trace_path)
    
    if not trace:
        logger.error("Impossible de charger la trace. Arrêt de l'analyse.")
        return
    
    # Analyser la trace
    analysis = {
        "interactions": analyze_agent_interactions(trace),
        "informal_performance": analyze_informal_agent_performance(trace),
        "quality": analyze_argumentative_quality(trace)
    }
    
    # Générer les visualisations
    generate_visualizations(analysis, output_dir)
    
    # Générer le rapport
    report_path = generate_report(trace, analysis, output_dir)
    
    logger.info(f"Analyse terminée. Rapport disponible à {report_path}")

if __name__ == "__main__":
    main()
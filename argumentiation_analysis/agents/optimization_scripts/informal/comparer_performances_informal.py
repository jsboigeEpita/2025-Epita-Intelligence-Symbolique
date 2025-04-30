#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour comparer les performances de l'agent Informel avant et après les améliorations.

Ce script permet de:
1. Charger les traces de conversation avant et après les améliorations
2. Comparer les performances sur différents critères
3. Générer un rapport comparatif
"""

import os
import sys
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ComparerPerformancesInformal")

# Répertoire des traces
TRACES_DIR = Path("traces_informal_agent")
COMPARISON_DIR = Path("utils/informal_optimization/comparison")
COMPARISON_DIR.mkdir(exist_ok=True, parents=True)

def load_traces(before_timestamp, after_timestamp):
    """
    Charge les traces de conversation avant et après les améliorations.
    
    Args:
        before_timestamp: Timestamp pour séparer les traces avant/après
        after_timestamp: Timestamp pour séparer les traces après/avant
    """
    logger.info("Chargement des traces de conversation...")
    
    traces_before = []
    traces_after = []
    
    if not TRACES_DIR.exists():
        logger.error(f"Répertoire des traces non trouvé: {TRACES_DIR}")
        return traces_before, traces_after
    
    for trace_file in TRACES_DIR.glob("*.json"):
        try:
            file_timestamp = trace_file.stem.split('_')[-1]
            
            with open(trace_file, "r", encoding="utf-8") as f:
                trace_data = json.load(f)
                trace_info = {
                    "file": trace_file.name,
                    "data": trace_data
                }
                
                # Déterminer si la trace est avant ou après les améliorations
                if file_timestamp < before_timestamp:
                    traces_before.append(trace_info)
                    logger.info(f"Trace avant améliorations: {trace_file.name}")
                elif file_timestamp > after_timestamp:
                    traces_after.append(trace_info)
                    logger.info(f"Trace après améliorations: {trace_file.name}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la trace {trace_file.name}: {e}")
    
    logger.info(f"{len(traces_before)} traces avant améliorations, {len(traces_after)} traces après améliorations.")
    return traces_before, traces_after

def compare_argument_identification(traces_before, traces_after):
    """
    Compare la qualité de l'identification des arguments avant et après les améliorations.
    """
    logger.info("Comparaison de l'identification des arguments...")
    
    results = {
        "before": {
            "total_arguments": 0,
            "argument_lengths": [],
            "avg_argument_length": 0,
            "arguments_per_extrait": defaultdict(int)
        },
        "after": {
            "total_arguments": 0,
            "argument_lengths": [],
            "avg_argument_length": 0,
            "arguments_per_extrait": defaultdict(int)
        }
    }
    
    # Analyser les traces avant améliorations
    for trace in traces_before:
        trace_data = trace["data"]
        extrait_id = trace_data.get("extrait", {}).get("id", "inconnu")
        
        for resultat in trace_data.get("resultats_par_extrait", []):
            if resultat.get("id") == extrait_id:
                num_args = resultat.get("nombre_arguments", 0)
                results["before"]["arguments_per_extrait"][extrait_id] = num_args
                results["before"]["total_arguments"] += num_args
        
        # Analyser les arguments identifiés
        arguments = []
        for arg in trace_data.get("resultats", {}).get("arguments", []):
            description = arg.get("description", "")
            if description:
                arguments.append(description)
                results["before"]["argument_lengths"].append(len(description.split()))
    
    # Analyser les traces après améliorations
    for trace in traces_after:
        trace_data = trace["data"]
        extrait_id = trace_data.get("extrait", {}).get("id", "inconnu")
        
        for resultat in trace_data.get("resultats_par_extrait", []):
            if resultat.get("id") == extrait_id:
                num_args = resultat.get("nombre_arguments", 0)
                results["after"]["arguments_per_extrait"][extrait_id] = num_args
                results["after"]["total_arguments"] += num_args
        
        # Analyser les arguments identifiés
        arguments = []
        for arg in trace_data.get("resultats", {}).get("arguments", []):
            description = arg.get("description", "")
            if description:
                arguments.append(description)
                results["after"]["argument_lengths"].append(len(description.split()))
    
    # Calculer les moyennes
    if results["before"]["argument_lengths"]:
        results["before"]["avg_argument_length"] = sum(results["before"]["argument_lengths"]) / len(results["before"]["argument_lengths"])
    
    if results["after"]["argument_lengths"]:
        results["after"]["avg_argument_length"] = sum(results["after"]["argument_lengths"]) / len(results["after"]["argument_lengths"])
    
    logger.info(f"Avant: {results['before']['total_arguments']} arguments, longueur moyenne: {results['before']['avg_argument_length']:.2f} mots")
    logger.info(f"Après: {results['after']['total_arguments']} arguments, longueur moyenne: {results['after']['avg_argument_length']:.2f} mots")
    
    return results

def compare_fallacy_attribution(traces_before, traces_after):
    """
    Compare la qualité de l'attribution des sophismes avant et après les améliorations.
    """
    logger.info("Comparaison de l'attribution des sophismes...")
    
    results = {
        "before": {
            "total_fallacies": 0,
            "fallacy_types": Counter(),
            "justification_lengths": [],
            "avg_justification_length": 0,
            "fallacies_per_argument": defaultdict(int),
            "fallacies_per_extrait": defaultdict(int)
        },
        "after": {
            "total_fallacies": 0,
            "fallacy_types": Counter(),
            "justification_lengths": [],
            "avg_justification_length": 0,
            "fallacies_per_argument": defaultdict(int),
            "fallacies_per_extrait": defaultdict(int)
        }
    }
    
    # Analyser les traces avant améliorations
    for trace in traces_before:
        trace_data = trace["data"]
        extrait_id = trace_data.get("extrait", {}).get("id", "inconnu")
        
        for resultat in trace_data.get("resultats_par_extrait", []):
            if resultat.get("id") == extrait_id:
                num_fallacies = resultat.get("nombre_sophismes", 0)
                results["before"]["fallacies_per_extrait"][extrait_id] = num_fallacies
                results["before"]["total_fallacies"] += num_fallacies
        
        # Analyser les sophismes identifiés
        fallacies = []
        for fallacy in trace_data.get("resultats", {}).get("sophismes", []):
            fallacy_type = fallacy.get("fallacy_type", "")
            justification = fallacy.get("justification", "")
            target_arg_id = fallacy.get("target_argument_id", "")
            
            if fallacy_type:
                fallacies.append({
                    "type": fallacy_type,
                    "justification": justification,
                    "target_arg_id": target_arg_id
                })
                
                results["before"]["fallacy_types"][fallacy_type] += 1
                results["before"]["justification_lengths"].append(len(justification.split()))
                results["before"]["fallacies_per_argument"][target_arg_id] += 1
    
    # Analyser les traces après améliorations
    for trace in traces_after:
        trace_data = trace["data"]
        extrait_id = trace_data.get("extrait", {}).get("id", "inconnu")
        
        for resultat in trace_data.get("resultats_par_extrait", []):
            if resultat.get("id") == extrait_id:
                num_fallacies = resultat.get("nombre_sophismes", 0)
                results["after"]["fallacies_per_extrait"][extrait_id] = num_fallacies
                results["after"]["total_fallacies"] += num_fallacies
        
        # Analyser les sophismes identifiés
        fallacies = []
        for fallacy in trace_data.get("resultats", {}).get("sophismes", []):
            fallacy_type = fallacy.get("fallacy_type", "")
            justification = fallacy.get("justification", "")
            target_arg_id = fallacy.get("target_argument_id", "")
            
            if fallacy_type:
                fallacies.append({
                    "type": fallacy_type,
                    "justification": justification,
                    "target_arg_id": target_arg_id
                })
                
                results["after"]["fallacy_types"][fallacy_type] += 1
                results["after"]["justification_lengths"].append(len(justification.split()))
                results["after"]["fallacies_per_argument"][target_arg_id] += 1
    
    # Calculer les moyennes
    if results["before"]["justification_lengths"]:
        results["before"]["avg_justification_length"] = sum(results["before"]["justification_lengths"]) / len(results["before"]["justification_lengths"])
    
    if results["after"]["justification_lengths"]:
        results["after"]["avg_justification_length"] = sum(results["after"]["justification_lengths"]) / len(results["after"]["justification_lengths"])
    
    logger.info(f"Avant: {results['before']['total_fallacies']} sophismes, {len(results['before']['fallacy_types'])} types uniques, longueur moyenne des justifications: {results['before']['avg_justification_length']:.2f} mots")
    logger.info(f"Après: {results['after']['total_fallacies']} sophismes, {len(results['after']['fallacy_types'])} types uniques, longueur moyenne des justifications: {results['after']['avg_justification_length']:.2f} mots")
    
    return results

def generate_comparison_visualizations(arg_results, fallacy_results):
    """
    Génère des visualisations comparatives.
    """
    logger.info("Génération des visualisations comparatives...")
    
    # 1. Longueur moyenne des arguments
    plt.figure(figsize=(10, 6))
    avg_lengths = [
        arg_results["before"]["avg_argument_length"],
        arg_results["after"]["avg_argument_length"]
    ]
    plt.bar(["Avant", "Après"], avg_lengths, color=['blue', 'green'])
    plt.title('Longueur moyenne des arguments (en mots)')
    plt.ylabel('Nombre de mots')
    plt.grid(True, alpha=0.3)
    plt.savefig(COMPARISON_DIR / "argument_length_comparison.png")
    plt.close()
    
    # 2. Nombre d'arguments identifiés
    plt.figure(figsize=(10, 6))
    arg_counts = [
        arg_results["before"]["total_arguments"],
        arg_results["after"]["total_arguments"]
    ]
    plt.bar(["Avant", "Après"], arg_counts, color=['blue', 'green'])
    plt.title('Nombre d\'arguments identifiés')
    plt.ylabel('Nombre d\'arguments')
    plt.grid(True, alpha=0.3)
    plt.savefig(COMPARISON_DIR / "argument_count_comparison.png")
    plt.close()
    
    # 3. Nombre de sophismes identifiés
    plt.figure(figsize=(10, 6))
    fallacy_counts = [
        fallacy_results["before"]["total_fallacies"],
        fallacy_results["after"]["total_fallacies"]
    ]
    plt.bar(["Avant", "Après"], fallacy_counts, color=['blue', 'green'])
    plt.title('Nombre de sophismes identifiés')
    plt.ylabel('Nombre de sophismes')
    plt.grid(True, alpha=0.3)
    plt.savefig(COMPARISON_DIR / "fallacy_count_comparison.png")
    plt.close()
    
    # 4. Diversité des types de sophismes
    plt.figure(figsize=(10, 6))
    fallacy_type_counts = [
        len(fallacy_results["before"]["fallacy_types"]),
        len(fallacy_results["after"]["fallacy_types"])
    ]
    plt.bar(["Avant", "Après"], fallacy_type_counts, color=['blue', 'green'])
    plt.title('Diversité des types de sophismes')
    plt.ylabel('Nombre de types uniques')
    plt.grid(True, alpha=0.3)
    plt.savefig(COMPARISON_DIR / "fallacy_diversity_comparison.png")
    plt.close()
    
    # 5. Longueur moyenne des justifications
    plt.figure(figsize=(10, 6))
    justification_lengths = [
        fallacy_results["before"]["avg_justification_length"],
        fallacy_results["after"]["avg_justification_length"]
    ]
    plt.bar(["Avant", "Après"], justification_lengths, color=['blue', 'green'])
    plt.title('Longueur moyenne des justifications (en mots)')
    plt.ylabel('Nombre de mots')
    plt.grid(True, alpha=0.3)
    plt.savefig(COMPARISON_DIR / "justification_length_comparison.png")
    plt.close()
    
    logger.info(f"Visualisations sauvegardées dans {COMPARISON_DIR}")

def generate_comparison_report(arg_results, fallacy_results):
    """
    Génère un rapport comparatif des performances avant et après les améliorations.
    """
    logger.info("Génération du rapport comparatif...")
    
    # Calculer les pourcentages d'amélioration
    arg_length_improvement = ((arg_results["before"]["avg_argument_length"] - arg_results["after"]["avg_argument_length"]) / arg_results["before"]["avg_argument_length"]) * 100 if arg_results["before"]["avg_argument_length"] > 0 else 0
    arg_count_improvement = ((arg_results["after"]["total_arguments"] - arg_results["before"]["total_arguments"]) / arg_results["before"]["total_arguments"]) * 100 if arg_results["before"]["total_arguments"] > 0 else 0
    
    fallacy_count_improvement = ((fallacy_results["after"]["total_fallacies"] - fallacy_results["before"]["total_fallacies"]) / fallacy_results["before"]["total_fallacies"]) * 100 if fallacy_results["before"]["total_fallacies"] > 0 else 0
    fallacy_diversity_improvement = ((len(fallacy_results["after"]["fallacy_types"]) - len(fallacy_results["before"]["fallacy_types"])) / len(fallacy_results["before"]["fallacy_types"])) * 100 if len(fallacy_results["before"]["fallacy_types"]) > 0 else 0
    justification_length_improvement = ((fallacy_results["after"]["avg_justification_length"] - fallacy_results["before"]["avg_justification_length"]) / fallacy_results["before"]["avg_justification_length"]) * 100 if fallacy_results["before"]["avg_justification_length"] > 0 else 0
    
    report = f"""# Rapport Comparatif des Performances de l'Agent Informel

## 1. Résumé

Ce rapport présente une comparaison des performances de l'agent Informel avant et après les améliorations apportées. L'analyse porte sur l'identification des arguments et l'attribution des sophismes.

## 2. Identification des Arguments

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Nombre total d'arguments | {arg_results["before"]["total_arguments"]} | {arg_results["after"]["total_arguments"]} | {arg_count_improvement:.2f}% |
| Longueur moyenne des arguments | {arg_results["before"]["avg_argument_length"]:.2f} mots | {arg_results["after"]["avg_argument_length"]:.2f} mots | {arg_length_improvement:.2f}% |

### Analyse

{
"L'agent identifie désormais des arguments plus concis et précis." if arg_length_improvement > 0 else 
"La longueur des arguments n'a pas été significativement réduite."
}

{
f"Le nombre d'arguments identifiés a augmenté de {arg_count_improvement:.2f}%, ce qui suggère une meilleure capacité à identifier les arguments distincts." if arg_count_improvement > 0 else 
"Le nombre d'arguments identifiés n'a pas significativement changé."
}

## 3. Attribution des Sophismes

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Nombre total de sophismes | {fallacy_results["before"]["total_fallacies"]} | {fallacy_results["after"]["total_fallacies"]} | {fallacy_count_improvement:.2f}% |
| Diversité des types de sophismes | {len(fallacy_results["before"]["fallacy_types"])} | {len(fallacy_results["after"]["fallacy_types"])} | {fallacy_diversity_improvement:.2f}% |
| Longueur moyenne des justifications | {fallacy_results["before"]["avg_justification_length"]:.2f} mots | {fallacy_results["after"]["avg_justification_length"]:.2f} mots | {justification_length_improvement:.2f}% |

### Types de sophismes les plus fréquents

#### Avant les améliorations:
{chr(10).join([f"- {fallacy_type}: {count} occurrences" for fallacy_type, count in fallacy_results["before"]["fallacy_types"].most_common(5)])}

#### Après les améliorations:
{chr(10).join([f"- {fallacy_type}: {count} occurrences" for fallacy_type, count in fallacy_results["after"]["fallacy_types"].most_common(5)])}

### Analyse

{
f"L'agent identifie désormais {fallacy_count_improvement:.2f}% plus de sophismes qu'avant." if fallacy_count_improvement > 0 else 
"Le nombre de sophismes identifiés n'a pas significativement changé."
}

{
f"La diversité des types de sophismes utilisés a augmenté de {fallacy_diversity_improvement:.2f}%, ce qui suggère une meilleure exploration de la taxonomie." if fallacy_diversity_improvement > 0 else 
"La diversité des types de sophismes n'a pas significativement changé."
}

{
f"Les justifications sont désormais {justification_length_improvement:.2f}% plus détaillées qu'avant." if justification_length_improvement > 0 else 
"La longueur des justifications n'a pas significativement changé."
}

## 4. Conclusion

{
"Les améliorations apportées à l'agent Informel ont eu un impact positif sur ses performances. L'agent identifie désormais des arguments plus précis et concis, utilise une plus grande diversité de sophismes et fournit des justifications plus détaillées." 
if arg_length_improvement > 0 or arg_count_improvement > 0 or fallacy_count_improvement > 0 or fallacy_diversity_improvement > 0 or justification_length_improvement > 0 else
"Les améliorations apportées à l'agent Informel n'ont pas eu d'impact significatif sur ses performances. Des ajustements supplémentaires pourraient être nécessaires."
}

### Recommandations pour des améliorations futures

1. {
"Continuer à améliorer la concision des arguments identifiés." if arg_length_improvement < 10 else
"Maintenir la qualité actuelle de l'identification des arguments."
}

2. {
"Encourager davantage l'exploration de la taxonomie pour augmenter la diversité des sophismes identifiés." if fallacy_diversity_improvement < 20 else
"Maintenir la diversité actuelle des sophismes identifiés."
}

3. {
"Renforcer les exigences pour les justifications afin de les rendre encore plus détaillées et convaincantes." if justification_length_improvement < 20 else
"Maintenir la qualité actuelle des justifications."
}

4. Intégrer des mécanismes d'auto-évaluation pour que l'agent puisse juger de la qualité de ses propres analyses.

5. Développer des métriques plus précises pour évaluer la pertinence des sophismes identifiés, au-delà de leur simple nombre et diversité.

Date de l'analyse: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    # Sauvegarder le rapport
    report_path = COMPARISON_DIR / f"rapport_comparatif_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"Rapport comparatif sauvegardé dans {report_path}")
    return report_path

def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage de la comparaison des performances de l'agent Informel...")
    
    # Définir les timestamps pour séparer les traces avant/après
    before_timestamp = "20250430_033000"  # Traces avant cette date sont considérées "avant améliorations"
    after_timestamp = "20250430_034000"   # Traces après cette date sont considérées "après améliorations"
    
    # Charger les traces
    traces_before, traces_after = load_traces(before_timestamp, after_timestamp)
    
    if not traces_before or not traces_after:
        logger.error("Impossible de comparer les performances: pas assez de traces.")
        return
    
    # Comparer l'identification des arguments
    arg_results = compare_argument_identification(traces_before, traces_after)
    
    # Comparer l'attribution des sophismes
    fallacy_results = compare_fallacy_attribution(traces_before, traces_after)
    
    # Générer des visualisations comparatives
    generate_comparison_visualizations(arg_results, fallacy_results)
    
    # Générer le rapport comparatif
    report_path = generate_comparison_report(arg_results, fallacy_results)
    
    logger.info("Comparaison des performances terminée.")
    logger.info(f"Rapport: {report_path}")

if __name__ == "__main__":
    main()
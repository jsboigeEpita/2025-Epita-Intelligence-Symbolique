#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaire pour la génération de rapports Markdown sur les performances des agents.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def generate_markdown_performance_report(
    metrics: Dict[str, Dict[str, Any]],
    base_results_summary: Dict[str, Any], 
    advanced_results_summary: Dict[str, Any],
    output_file: Path
) -> None:
    """
    Génère un rapport Markdown détaillé sur la pertinence des différents agents.

    Args:
        metrics (Dict[str, Dict[str, Any]]): Métriques de performance par agent.
        base_results_summary (Dict[str, Any]): Résumé des données de base 
                                               (ex: {"count": len(base_results), "sources": list_of_sources}).
        advanced_results_summary (Dict[str, Any]): Résumé des données avancées.
        output_file (Path): Chemin du fichier de sortie pour le rapport Markdown.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_content: List[str] = []

    report_content.append("# Rapport de Comparaison des Performances des Agents d'Analyse Rhétorique")
    report_content.append(f"\n*Date de génération: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    report_content.append("## 1. Résumé Exécutif")
    report_content.append("Ce rapport détaille et compare les performances de différents agents (ou configurations d'agents) d'analyse rhétorique. L'évaluation se base sur plusieurs critères incluant la détection de sophismes, la richesse contextuelle, la pertinence des évaluations de cohérence, le temps d'exécution, et la complexité des résultats générés.")
    
    report_content.append("\n## 2. Données Analysées")
    report_content.append(f"- Nombre d'extraits pour l'analyse de base: {base_results_summary.get('count', 'N/A')}")
    sources_base = base_results_summary.get('sources', [])
    report_content.append(f"- Sources pour l'analyse de base: {', '.join(sources_base) if sources_base else 'N/A'}")
    report_content.append(f"- Nombre d'extraits pour l'analyse avancée: {advanced_results_summary.get('count', 'N/A')}")
    sources_advanced = advanced_results_summary.get('sources', [])
    report_content.append(f"- Sources pour l'analyse avancée: {', '.join(sources_advanced) if sources_advanced else 'N/A'}")

    report_content.append("\n## 3. Métriques de Performance Agrégées par Agent/Type d'Analyse")
    header = "| Agent/Type | Sophismes (moy.) | Confiance (moy.) | Taux FP (est.) | Taux FN (est.) | Exécution (s/moy.) | Richesse Context. (moy.) | Pertinence Cohér. (moy.) | Complexité Résultat (moy.) | Recommandations Cohér. (moy.) |"
    separator = "|---|---|---|---|---|---|---|---|---|---|"
    report_content.append(header)
    report_content.append(separator)

    if metrics:
        for agent_name, agent_metrics_dict in metrics.items():
            row_values = [
                agent_name,
                f"{agent_metrics_dict.get('fallacy_count', 0.0):.2f}",
                f"{agent_metrics_dict.get('confidence', 0.0):.2f}",
                f"{agent_metrics_dict.get('false_positive_rate', 0.0):.2f}",
                f"{agent_metrics_dict.get('false_negative_rate', 0.0):.2f}",
                f"{agent_metrics_dict.get('execution_time', 0.0):.2f}",
                f"{agent_metrics_dict.get('contextual_richness', 0.0):.2f}",
                f"{agent_metrics_dict.get('relevance', 0.0):.2f}", 
                f"{agent_metrics_dict.get('complexity', 0.0):.2f}",
                f"{agent_metrics_dict.get('recommendation_relevance', 0.0):.2f}"
            ]
            report_content.append(f"| {' | '.join(row_values)} |")
    else:
        report_content.append("| N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |")


    report_content.append("\n## 4. Analyse Détaillée et Recommandations (Exemples)")
    
    if metrics:
        try:
            best_fallacy_detector = max(metrics.items(), key=lambda item: item[1].get('fallacy_count', -1.0))[0]
            report_content.append(f"\n### Détection de Sophismes")
            report_content.append(f"- **Meilleure détection (nombre moyen) :** {best_fallacy_detector} ({metrics.get(best_fallacy_detector, {}).get('fallacy_count', 0.0):.2f})")
        except (ValueError, TypeError): 
            report_content.append("\n### Détection de Sophismes")
            report_content.append("- Données insuffisantes ou format incorrect pour déterminer le meilleur agent pour la détection de sophismes.")

        try:
            richest_context_agent = max(metrics.items(), key=lambda item: item[1].get('contextual_richness', -1.0))[0]
            report_content.append(f"\n### Richesse Contextuelle")
            report_content.append(f"- **Analyse la plus riche (score moyen) :** {richest_context_agent} ({metrics.get(richest_context_agent, {}).get('contextual_richness', 0.0):.2f})")
        except (ValueError, TypeError):
            report_content.append("\n### Richesse Contextuelle")
            report_content.append("- Données insuffisantes ou format incorrect pour déterminer l'agent avec la meilleure richesse contextuelle.")
        
        report_content.append("\n*Note: Les 'meilleurs' agents sont identifiés sur la base des métriques individuelles. Une évaluation globale peut nécessiter une pondération de ces métriques en fonction des priorités du projet.*")
    else:
        report_content.append("\n- Aucune métrique disponible pour l'analyse détaillée.")

    report_content.append("\n## 5. Conclusion")
    report_content.append("Le choix de l'agent optimal dépendra des priorités spécifiques de l'analyse (précision, rapidité, profondeur, etc.). Ce rapport fournit une base quantitative pour guider cette sélection.")
    report_content.append("\nPour des visualisations graphiques de ces métriques, veuillez consulter les fichiers PNG générés dans le même répertoire que ce rapport (si les bibliothèques de visualisation sont installées).")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_content))
        logger.info(f"Rapport de performance Markdown généré avec succès : {output_file}")
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture du rapport Markdown {output_file}: {e}", exc_info=True)
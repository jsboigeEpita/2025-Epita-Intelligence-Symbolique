# -*- coding: utf-8 -*-
"""Utilitaires pour la génération de rapports."""

import json
from pathlib import Path
from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

def save_json_report(data: Union[List[Dict[str, Any]], Dict[str, Any]], output_file: Path) -> bool:
    """
    Sauvegarde des données (liste ou dictionnaire) dans un fichier JSON.

    Args:
        data: Les données à sauvegarder.
        output_file: Chemin du fichier de sortie JSON.

    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
    logger.info(f"Sauvegarde des données JSON vers {output_file}...")
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Données JSON sauvegardées avec succès : {output_file.resolve()}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des données JSON vers {output_file}: {e}", exc_info=True)
        return False

def generate_json_report(analysis_results: List[Dict[str, Any]], output_file: Path) -> None:
    """
    Génère un rapport JSON à partir des résultats d'analyse.
    (Utilise save_json_report en interne pour la sauvegarde)
    """
    logger.info(f"Génération du rapport JSON (via save_json_report) vers {output_file}...")
    if not save_json_report(analysis_results, output_file):
        # save_json_report logue déjà l'erreur spécifique.
        # On pourrait ajouter un log ici si on veut un message de plus haut niveau.
        logger.error(f"Échec final de la génération du rapport JSON pour {output_file}")
    # La fonction originale ne retournait rien.
def save_text_report(report_content: str, output_file: Path) -> bool:
    """
    Sauvegarde un contenu textuel (par exemple, un rapport Markdown) dans un fichier.

    Args:
        report_content (str): Le contenu textuel du rapport.
        output_file: Chemin du fichier de sortie.

    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
    logger.info(f"Sauvegarde du rapport textuel vers {output_file}...")
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.info(f"Rapport textuel sauvegardé avec succès : {output_file.resolve()}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du rapport textuel vers {output_file}: {e}", exc_info=True)
        return False

def generate_specific_rhetorical_markdown_report(analysis_results: List[Dict[str, Any]], output_file: Path) -> None:
    """
    Génère un rapport Markdown spécifique à l'analyse rhétorique Python
    à partir des résultats d'analyse.
    """
    logger.info(f"Génération du rapport Markdown rhétorique spécifique vers {output_file}...")
    report_content_parts = ["# Rapport d'Analyse Rhétorique Python\n"]

    for result_item in analysis_results:
        source_name = result_item.get("source_name", "Source Inconnue")
        analysis = result_item.get("analysis", {})
        error = result_item.get("error")

        report_content_parts.append(f"## Analyse de : {source_name}\n")

        if error:
            report_content_parts.append(f"**Erreur lors de l'analyse :** `{error}`\n")
            report_content_parts.append("\n---\n")
            continue
        
        if not analysis:
            report_content_parts.append("Aucune analyse disponible pour cette source (données d'analyse vides).\n")
            report_content_parts.append("\n---\n")
            continue

        original_text = analysis.get("text", "Texte original non disponible.")
        report_content_parts.append("### Texte Analysé (extrait)\n")
        report_content_parts.append(f"```\n{original_text[:500]}{'...' if len(original_text) > 500 else ''}\n```\n")

        fallacies = analysis.get("fallacies", [])
        report_content_parts.append(f"### Sophismes Détectés ({len(fallacies)})\n")
        if fallacies:
            for i, fallacy in enumerate(fallacies):
                fallacy_type = fallacy.get("fallacy_type", "Type inconnu").replace("_", " ").title()
                description = fallacy.get("description", "Pas de description.")
                severity = fallacy.get("severity", "Non spécifiée")
                confidence = fallacy.get("confidence", 0.0)
                context_text = fallacy.get("context_text", "Pas de contexte.")
                
                report_content_parts.append(f"**Sophisme {i+1}: {fallacy_type}**\n")
                report_content_parts.append(f"- Description : {description}\n")
                report_content_parts.append(f"- Sévérité : {severity}\n")
                report_content_parts.append(f"- Confiance : {confidence:.2f}\n")
                report_content_parts.append(f"- Contexte : `{context_text[:200]}{'...' if len(context_text) > 200 else ''}`\n")
        else:
            report_content_parts.append("Aucun sophisme détecté pour ce texte.\n")
        
        categories = analysis.get("categories", {})
        report_content_parts.append(f"\n### Catégorisation des Sophismes\n")
        if categories:
            has_content = False
            for category, types in categories.items():
                if types: # S'assurer que la liste des types n'est pas vide
                    report_content_parts.append(f"- **{category.replace('_', ' ').title()}**: {', '.join(types)}\n")
                    has_content = True
            if not has_content:
                 report_content_parts.append("Aucune catégorie de sophisme identifiée.\n")
        else:
            report_content_parts.append("Aucune catégorie de sophisme disponible.\n")

        report_content_parts.append("\n---\n")

    final_report_content = "\n".join(report_content_parts)
    if not save_text_report(final_report_content, output_file):
        logger.error(f"Échec de la sauvegarde du rapport Markdown rhétorique spécifique vers {output_file}")
    # save_text_report logue déjà le succès ou l'erreur spécifique.

def generate_performance_comparison_markdown_report(
    base_metrics: Dict[str, Any],
    advanced_metrics: Dict[str, Any],
    output_file: Path
) -> None:
    """
    Génère un rapport Markdown détaillé comparant les performances des agents
    d'analyse rhétorique basé sur les métriques fournies.
    """
    logger.info(f"Génération du rapport de comparaison de performance Markdown vers {output_file}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    report_parts = []
    
    # En-tête du rapport
    from datetime import datetime # Import local pour éviter dépendance au niveau module si non utilisée ailleurs
    report_parts.append("# Rapport de comparaison des performances des agents d'analyse rhétorique")
    report_parts.append("")
    report_parts.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_parts.append("")
    report_parts.append("## Résumé")
    report_parts.append("")
    report_parts.append("Ce rapport présente une comparaison détaillée des performances des différents agents spécialistes d'analyse rhétorique.")
    report_parts.append("Les agents sont évalués sur plusieurs critères: précision de détection des sophismes, richesse de l'analyse contextuelle,")
    report_parts.append("pertinence des évaluations de cohérence, temps d'exécution et complexité des résultats.")
    report_parts.append("")
    
    # Métriques de performance par agent
    report_parts.append("## Métriques de performance par agent")
    report_parts.append("")
    
    # Détection des sophismes
    report_parts.append("### Détection des sophismes")
    report_parts.append("")
    report_parts.append("| Agent | Nombre de sophismes détectés |")
    report_parts.append("|-------|----------------------------|")
    report_parts.append(f"| Agent contextuel de base | {base_metrics.get('fallacy_counts', {}).get('base_contextual', 0)} |")
    report_parts.append(f"| Agent contextuel avancé | {advanced_metrics.get('fallacy_counts', {}).get('advanced_contextual', 0)} |")
    report_parts.append(f"| Agent de sophismes complexes | {advanced_metrics.get('fallacy_counts', {}).get('advanced_complex', 0)} |")
    report_parts.append("")
    
    # Scores de confiance
    report_parts.append("### Scores de confiance")
    report_parts.append("")
    report_parts.append("| Agent | Score de confiance moyen |")
    report_parts.append("|-------|--------------------------|")
    report_parts.append(f"| Agent de cohérence de base | {base_metrics.get('confidence_scores', {}).get('base_coherence', 0.0):.2f} |")
    report_parts.append(f"| Agent rhétorique avancé | {advanced_metrics.get('confidence_scores', {}).get('advanced_rhetorical', 0.0):.2f} |")
    report_parts.append(f"| Agent de cohérence avancé | {advanced_metrics.get('confidence_scores', {}).get('advanced_coherence', 0.0):.2f} |")
    report_parts.append(f"| Agent d'évaluation de gravité | {advanced_metrics.get('confidence_scores', {}).get('advanced_severity', 0.0):.2f} |")
    report_parts.append("")
    
    # Richesse contextuelle
    report_parts.append("### Richesse contextuelle")
    report_parts.append("")
    report_parts.append("| Agent | Score de richesse contextuelle moyen |")
    report_parts.append("|-------|-------------------------------------|")
    report_parts.append(f"| Agent contextuel de base | {base_metrics.get('richness_scores', {}).get('base_contextual', 0.0):.2f} |")
    report_parts.append(f"| Agent contextuel avancé | {advanced_metrics.get('richness_scores', {}).get('advanced_contextual', 0.0):.2f} |")
    report_parts.append(f"| Agent rhétorique avancé | {advanced_metrics.get('richness_scores', {}).get('advanced_rhetorical', 0.0):.2f} |")
    report_parts.append("")
    
    # Analyse comparative
    report_parts.append("## Analyse comparative")
    report_parts.append("")
    
    base_fallacy_count = base_metrics.get('fallacy_counts', {}).get('base_contextual', 0)
    advanced_contextual_fallacy_count = advanced_metrics.get('fallacy_counts', {}).get('advanced_contextual', 0)
    advanced_complex_fallacy_count = advanced_metrics.get('fallacy_counts', {}).get('advanced_complex', 0)
    
    if advanced_complex_fallacy_count > base_fallacy_count and advanced_complex_fallacy_count > advanced_contextual_fallacy_count:
        report_parts.append("L'agent de sophismes complexes détecte le plus grand nombre de sophismes, suggérant une analyse plus approfondie.")
    elif advanced_contextual_fallacy_count > base_fallacy_count:
        report_parts.append("L'agent contextuel avancé détecte plus de sophismes que l'agent contextuel de base, suggérant une meilleure précision.")
    else:
        report_parts.append("L'agent contextuel de base détecte un nombre comparable de sophismes aux agents avancés, suggérant une bonne efficacité pour sa catégorie.")
    report_parts.append("")
    
    base_richness = base_metrics.get('richness_scores', {}).get('base_contextual', 0.0)
    advanced_contextual_richness = advanced_metrics.get('richness_scores', {}).get('advanced_contextual', 0.0)
    advanced_rhetorical_richness = advanced_metrics.get('richness_scores', {}).get('advanced_rhetorical', 0.0)
    
    if advanced_rhetorical_richness > advanced_contextual_richness and advanced_rhetorical_richness > base_richness:
        report_parts.append("L'agent rhétorique avancé fournit l'analyse contextuelle la plus riche.")
    elif advanced_contextual_richness > base_richness:
        report_parts.append("L'agent contextuel avancé fournit une analyse contextuelle plus riche que l'agent contextuel de base.")
    else:
        report_parts.append("L'agent contextuel de base fournit une analyse contextuelle comparable aux agents avancés pour sa catégorie.")
    report_parts.append("")
    
    # Recommandations
    report_parts.append("## Recommandations")
    report_parts.append("")
    report_parts.append("Sur la base de cette analyse comparative:")
    report_parts.append("- **Analyse rapide et basique**: Agents de base (ContextualFallacyDetector, etc.).")
    report_parts.append("- **Analyse approfondie**: Agents avancés (EnhancedComplexFallacyAnalyzer, etc.).")
    report_parts.append("- **Détection de sophismes**: EnhancedComplexFallacyAnalyzer pour sophismes composites.")
    report_parts.append("- **Analyse contextuelle**: EnhancedRhetoricalResultAnalyzer pour richesse contextuelle.")
    report_parts.append("")
    
    # Conclusion
    report_parts.append("## Conclusion")
    report_parts.append("")
    report_parts.append("Les agents avancés offrent généralement une analyse plus détaillée et riche. Le choix dépend des besoins spécifiques de l'analyse (rapidité vs profondeur).")
    
    final_report_content = "\n".join(report_parts)
    if not save_text_report(final_report_content, output_file):
        logger.error(f"Échec de la sauvegarde du rapport de comparaison de performance vers {output_file}")
    # save_text_report logue déjà le succès ou l'erreur spécifique.
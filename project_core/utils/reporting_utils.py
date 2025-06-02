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
def generate_markdown_report_for_corpus(corpus_name: str, corpus_effectiveness_data: Dict[str, Any]) -> List[str]:
    """
    Génère une section de rapport au format Markdown pour un corpus donné.

    Cette section inclut les résultats d'analyse détaillés pour ce corpus,
    y compris l'efficacité des agents et les recommandations spécifiques.

    Args:
        corpus_name (str): Le nom du corpus.
        corpus_effectiveness_data (Dict[str, Any]): Un dictionnaire contenant les données
            d'efficacité des agents pour ce corpus. Doit contenir les clés
            'best_agent' (str, optionnel), 'base_agents' (Dict, optionnel),
            'advanced_agents' (Dict, optionnel), et 'recommendations' (List[str], optionnel).
            Les dictionnaires 'base_agents' et 'advanced_agents' doivent mapper les noms
            d'agents à des dictionnaires contenant 'fallacy_count' (int) et
            'effectiveness' (float).

    Returns:
        List[str]: Une liste de chaînes de caractères, représentant les lignes
                   de la section du rapport Markdown pour le corpus.
    """
    report_section_lines = []
    report_section_lines.append(f"### {corpus_name}")
    report_section_lines.append("")

    # Meilleur agent pour ce corpus
    best_agent = corpus_effectiveness_data.get("best_agent", "")
    if best_agent:
        report_section_lines.append(f"**Agent le plus efficace**: {best_agent}")
        report_section_lines.append("")

    # Résultats des agents de base
    base_agents_data = corpus_effectiveness_data.get("base_agents", {})
    if base_agents_data:
        report_section_lines.append("#### Agents de base")
        report_section_lines.append("")
        report_section_lines.append("| Agent | Sophismes détectés | Score d'efficacité |")
        report_section_lines.append("|-------|-------------------|-------------------|")
        
        for agent, metrics in base_agents_data.items():
            fallacy_count = metrics.get("fallacy_count", 0)
            effectiveness_score = metrics.get("effectiveness", 0.0)
            report_section_lines.append(f"| {agent} | {fallacy_count} | {effectiveness_score:.2f} |")
        
        report_section_lines.append("")

    # Résultats des agents avancés
    advanced_agents_data = corpus_effectiveness_data.get("advanced_agents", {})
    if advanced_agents_data:
        report_section_lines.append("#### Agents avancés")
        report_section_lines.append("")
        report_section_lines.append("| Agent | Sophismes détectés | Score d'efficacité |")
        report_section_lines.append("|-------|-------------------|-------------------|")
        
        for agent, metrics in advanced_agents_data.items():
            fallacy_count = metrics.get("fallacy_count", 0)
            effectiveness_score = metrics.get("effectiveness", 0.0)
            report_section_lines.append(f"| {agent} | {fallacy_count} | {effectiveness_score:.2f} |")
        
        report_section_lines.append("")

    # Recommandations spécifiques au corpus
    recommendations = corpus_effectiveness_data.get("recommendations", [])
    if recommendations:
        report_section_lines.append("#### Recommandations spécifiques")
        report_section_lines.append("")
        
        for recommendation in recommendations:
            report_section_lines.append(f"- {recommendation}")
        
        report_section_lines.append("")
    
    return report_section_lines
def generate_overall_summary_markdown(all_average_scores: Dict[str, Dict[str, float]]) -> List[str]:
    """
    Crée une section de résumé global au format Markdown.

    Cette fonction agrège et présente les scores moyens obtenus sur tous les corpus
    (par exemple, moyenne des scores de confiance par corpus, moyenne de la richesse
    contextuelle par corpus, etc.).

    Args:
        all_average_scores (Dict[str, Dict[str, float]]): Un dictionnaire où les clés externes
            sont les noms des corpus. Chaque corpus a un dictionnaire interne où les clés
            sont les noms des métriques (par exemple, 'confidence_score', 'contextual_richness')
            et les valeurs sont les scores moyens flottants.
            Exemple:
            {
                "Corpus A": {"confidence_score": 0.85, "contextual_richness": 0.75},
                "Corpus B": {"confidence_score": 0.90, "contextual_richness": 0.80}
            }

    Returns:
        List[str]: Une liste de chaînes de caractères, représentant les lignes
                   de la section du résumé global au format Markdown.
    """
    report_lines = []
    report_lines.append("## Résumé Global des Scores Moyens par Corpus")
    report_lines.append("")

    if not all_average_scores:
        report_lines.append("Aucune donnée de score moyen disponible pour générer le résumé global.")
        report_lines.append("")
        return report_lines

    # Collecter tous les noms de métriques uniques pour l'en-tête du tableau
    metric_names = set()
    for corpus_scores in all_average_scores.values():
        metric_names.update(corpus_scores.keys())
    
    sorted_metric_names = sorted(list(metric_names))

    # Créer l'en-tête du tableau
    header = "| Corpus | " + " | ".join([name.replace('_', ' ').title() for name in sorted_metric_names]) + " |"
    separator = "|--------|-" + "-|-".join(["-" * len(name.replace('_', ' ').title()) for name in sorted_metric_names]) + "-|"
    report_lines.append(header)
    report_lines.append(separator)

    # Remplir le tableau avec les données
    for corpus_name, scores in sorted(all_average_scores.items()):
        row_values = [corpus_name]
        for metric_name in sorted_metric_names:
            score = scores.get(metric_name, 0.0) # Mettre 0.0 si la métrique manque pour un corpus
            row_values.append(f"{score:.2f}")
        report_lines.append("| " + " | ".join(row_values) + " |")

    report_lines.append("")
    return report_lines
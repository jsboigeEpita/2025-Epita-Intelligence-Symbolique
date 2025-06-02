# -*- coding: utf-8 -*-
"""
Module pour la génération de synthèses d'analyses rhétoriques.
"""

import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Imports des utilitaires du projet qui étaient utilisés dans le script original
# et qui sont nécessaires pour les fonctions déplacées.
from argumentation_analysis.utils.text_processing import split_text_into_arguments
from argumentation_analysis.utils.data_generation import generate_sample_text

logger = logging.getLogger(__name__)

# --- Fonctions de génération de données simulées (déplacées depuis le script) ---

def generate_fallacy_detection(argument: str, common_fallacies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Génère une détection de sophismes simulée pour un argument.

    :param argument: Argument à analyser.
    :type argument: str
    :param common_fallacies: Liste des sophismes courants à utiliser.
                             Chaque sophisme est un dictionnaire avec "name", "description", "severity".
    :type common_fallacies: List[Dict[str, Any]]
    :return: Liste des sophismes détectés pour l'argument. Chaque sophisme détecté
             est un dictionnaire avec "fallacy_type", "description", "severity",
             "context_text", et "confidence". Retourne une liste vide si aucun
             sophisme n'est détecté ou si `common_fallacies` est vide.
    :rtype: List[Dict[str, Any]]
    """
    if not common_fallacies: # Au cas où la liste serait vide
        return []
    if random.random() < 0.5: # Probabilité de détecter un sophisme (50%)
        return []
    
    fallacy = random.choice(common_fallacies)
    
    return [{
        "fallacy_type": fallacy["name"].lower().replace(" ", "_"),
        "description": fallacy["description"],
        "severity": fallacy["severity"],
        "context_text": argument[:50] + "...", # Contexte tronqué
        "confidence": round(random.uniform(0.6, 0.95), 2)
    }]

def generate_coherence_evaluation() -> Dict[str, Any]:
    """
    Génère une évaluation de cohérence simulée.

    :return: Un dictionnaire contenant l'évaluation de cohérence simulée,
             incluant "overall_coherence", "thematic_coherence",
             "logical_coherence", et "recommendations".
    :rtype: Dict[str, Any]
    """
    coherence_score = round(random.uniform(0.4, 0.9), 2)
    coherence_level = "Faible"
    if coherence_score >= 0.7:
        coherence_level = "Élevé"
    elif coherence_score >= 0.5:
        coherence_level = "Modéré"
    
    recommendations = [
        "Améliorer la transition entre les arguments",
        "Renforcer la cohérence thématique",
        "Clarifier les liens logiques entre les idées",
        "Éviter les digressions qui affaiblissent l'argumentation"
    ]
    selected_recommendations = random.sample(recommendations, k=random.randint(1, 3))
    
    return {
        "overall_coherence": {"score": coherence_score, "level": coherence_level},
        "thematic_coherence": round(random.uniform(0.4, 0.9), 2),
        "logical_coherence": round(random.uniform(0.4, 0.9), 2),
        "recommendations": selected_recommendations
    }

# --- Fonctions de génération d'analyse et de rapports (déplacées) ---

def generate_rhetorical_analysis_for_extract(
    extract_definition: Dict[str, Any], 
    source_name: str, 
    agent_config: Dict[str, Any],
    common_fallacies_for_simulation: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Génère une analyse rhétorique simulée pour un seul extrait.

    Cette fonction simule divers aspects d'une analyse rhétorique, y compris
    la détection de sophismes, l'évaluation de la cohérence, et le calcul
    de métriques de qualité.

    :param extract_definition: Dictionnaire contenant la définition de l'extrait,
                               notamment "extract_name" et optionnellement "type".
    :type extract_definition: Dict[str, Any]
    :param source_name: Nom de la source de l'extrait.
    :type source_name: str
    :param agent_config: Configuration de l'agent d'analyse (utilisé pour "name").
    :type agent_config: Dict[str, Any]
    :param common_fallacies_for_simulation: Liste des sophismes courants à utiliser
                                            pour la simulation de détection.
    :type common_fallacies_for_simulation: List[Dict[str, Any]]
    :return: Un dictionnaire contenant les résultats de l'analyse rhétorique simulée
             pour l'extrait.
    :rtype: Dict[str, Any]
    """
    extract_name = extract_definition["extract_name"]
    extract_type = extract_definition.get("type", "general")
    
    extract_text = generate_sample_text(extract_name=extract_name, source_name=source_name)
    arguments = split_text_into_arguments(extract_text)
    
    results: Dict[str, Any] = {
        "extract_name": extract_name,
        "source_name": source_name,
        "agent_name": agent_config["name"],
        "argument_count": len(arguments),
        "timestamp": datetime.now().isoformat(),
        "extract_text": extract_text,
        "analyses": {}
    }
    
    fallacy_analysis_results = {
        "argument_count": len(arguments),
        "context_description": f"Extrait '{extract_name}' de la source '{source_name}'",
        "contextual_factors": {
            "domain": "politique" if "politique" in extract_type else "général",
            "audience": "public" if "discours" in extract_type else "spécialistes",
            "medium": "oral" if "discours" in extract_type else "écrit",
            "purpose": "persuader" if "politique" in extract_type else "informer"
        },
        "argument_results": []
    }
    
    total_fallacies = 0
    for i, argument_text in enumerate(arguments):
        detected_fallacies = generate_fallacy_detection(argument_text, common_fallacies_for_simulation)
        total_fallacies += len(detected_fallacies)
        fallacy_analysis_results["argument_results"].append({
            "argument_index": i,
            "argument": argument_text,
            "detected_fallacies": detected_fallacies
        })
    
    results["analyses"]["fallacy_detection"] = fallacy_analysis_results
    results["analyses"]["fallacy_count"] = total_fallacies
    results["analyses"]["coherence_evaluation"] = generate_coherence_evaluation()
    results["analyses"]["metrics"] = {
        "fallacy_density": round(total_fallacies / len(arguments), 2) if arguments else 0,
        "persuasiveness_score": round(random.uniform(0.3, 0.9), 2),
        "clarity_score": round(random.uniform(0.4, 0.9), 2),
        "overall_quality": round(random.uniform(0.4, 0.9), 2)
    }
    results["analyses"]["recommendations"] = random.sample([
        "Réduire l'utilisation des sophismes identifiés",
        "Améliorer la cohérence entre les arguments",
        "Renforcer les preuves factuelles",
        "Clarifier les liens logiques entre les idées"
    ], k=random.randint(1,3))
    
    return results

def generate_markdown_summary_for_analysis(analysis_result: Dict[str, Any], output_dir: Path) -> Path:
    """
    Génère une synthèse au format Markdown pour un résultat d'analyse.

    Crée un fichier Markdown contenant un résumé formaté des résultats
    d'une analyse rhétorique spécifique.

    :param analysis_result: Dictionnaire contenant les résultats de l'analyse
                            pour un extrait.
    :type analysis_result: Dict[str, Any]
    :param output_dir: Répertoire (objet Path) où le fichier Markdown de synthèse
                       sera sauvegardé.
    :type output_dir: Path
    :return: Le chemin (objet Path) du fichier Markdown de synthèse généré.
    :rtype: Path
    """
    extract_name = analysis_result["extract_name"]
    source_name = analysis_result["source_name"]
    agent_name = analysis_result["agent_name"]
    
    filename = f"{source_name.replace(' ', '_')}_{extract_name.replace(' ', '_')}_{agent_name.replace(' ', '_')}.md"
    output_path = output_dir / filename
    
    extract_text = analysis_result["extract_text"]
    argument_count = analysis_result["argument_count"]
    fallacy_count = analysis_result["analyses"]["fallacy_count"]
    coherence_evaluation = analysis_result["analyses"]["coherence_evaluation"]
    metrics = analysis_result["analyses"]["metrics"]
    
    content = f"# Analyse rhétorique: {extract_name}\n\n"
    content += f"## Informations générales\n\n"
    content += f"- **Source**: {source_name}\n"
    content += f"- **Extrait**: {extract_name}\n"
    content += f"- **Agent d'analyse**: {agent_name}\n"
    content += f"- **Date d'analyse**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    content += f"## Résumé de l'analyse\n\n"
    content += f"L'analyse rhétorique de cet extrait a identifié **{fallacy_count} sophismes** sur un total de **{argument_count} arguments**. "
    content += f"La cohérence argumentative globale est évaluée comme **{coherence_evaluation['overall_coherence']['level']}** "
    content += f"(score: {coherence_evaluation['overall_coherence']['score']}).\n\n"
    content += f"## Extrait analysé\n\n```\n{extract_text}\n```\n\n"
    content += f"## Sophismes détectés\n\n"
    
    fallacy_results = analysis_result["analyses"]["fallacy_detection"]["argument_results"]
    fallacies_found_in_extract = any(arg_res["detected_fallacies"] for arg_res in fallacy_results)
    
    if fallacies_found_in_extract:
        for arg_result in fallacy_results:
            if arg_result["detected_fallacies"]:
                argument = arg_result["argument"]
                for fallacy in arg_result["detected_fallacies"]:
                    fallacy_type = fallacy["fallacy_type"].replace("_", " ").title()
                    content += f"### {fallacy_type}\n\n"
                    content += f"- **Description**: {fallacy['description']}\n"
                    content += f"- **Sévérité**: {fallacy.get('severity', 'Non spécifiée')}\n"
                    content += f"- **Confiance**: {fallacy.get('confidence', 0.0):.2f}\n"
                    content += f"- **Contexte**:\n  > {argument}\n\n"
    else:
        content += "Aucun sophisme n'a été détecté dans cet extrait.\n\n"
    
    content += "## Métriques d'analyse\n\n"
    content += "| Métrique | Valeur | Interprétation |\n|----------|--------|----------------|\n"
    metric_interpretations = {
        "fallacy_density": lambda v: "Faible" if v < 0.2 else ("Modérée" if v < 0.5 else "Forte") + " présence de sophismes",
        "persuasiveness_score": lambda v: "Peu" if v < 0.4 else ("Modérément" if v < 0.7 else "Très") + " persuasif",
        "clarity_score": lambda v: "Peu" if v < 0.4 else ("Modérément" if v < 0.7 else "Très") + " clair",
        "overall_quality": lambda v: "Faible" if v < 0.4 else ("Moyenne" if v < 0.7 else "Élevée") + " qualité"
    }
    for name, value in metrics.items():
        interp_func = metric_interpretations.get(name, lambda v: "Non spécifiée")
        interpretation = interp_func(value)
        formatted_name = name.replace("_", " ").title()
        content += f"| {formatted_name} | {value:.2f} | {interpretation} |\n"
        
    content += "\n## Recommandations\n\n"
    for rec in analysis_result["analyses"]["recommendations"]:
        content += f"- {rec}\n"
        
    content += f"\n## Analyses détaillées (liens fictifs)\n\n"
    content += f"- [Analyse JSON complète](../rhetorical_analyses_{analysis_result['timestamp']}.json)\n" # Placeholder
    
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.debug(f"Synthèse Markdown générée: {output_path}")
    return output_path

def generate_global_summary_report(all_analyses: List[Dict[str, Any]], output_dir: Path, rhetorical_agents_config: List[Dict[str, Any]]) -> Path:
    """
    Génère un rapport de synthèse global comparant les différents agents.

    Ce rapport agrège les résultats de multiples analyses effectuées par différents
    agents sur diverses sources, fournissant une vue comparative.

    :param all_analyses: Liste de tous les résultats d'analyse individuels.
    :type all_analyses: List[Dict[str, Any]]
    :param output_dir: Répertoire (objet Path) où le rapport global sera sauvegardé.
    :type output_dir: Path
    :param rhetorical_agents_config: Liste des configurations des agents rhétoriques,
                                     utilisée pour extraire des informations comme
                                     les forces et faiblesses.
    :type rhetorical_agents_config: List[Dict[str, Any]]
    :return: Le chemin (objet Path) du rapport de synthèse global généré.
    :rtype: Path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"rapport_synthese_global_{timestamp}.md"
    
    analyses_by_agent: Dict[str, Dict[str, List[Dict[str,Any]]]] = {}
    sources_set = set()
    
    for analysis in all_analyses:
        agent_name = analysis["agent_name"]
        source_name = analysis["source_name"]
        analyses_by_agent.setdefault(agent_name, {}).setdefault(source_name, []).append(analysis)
        sources_set.add(source_name)
        
    content = f"# Rapport de synthèse global des analyses rhétoriques\n\n"
    content += f"## Informations générales\n\n"
    content += f"- **Date de génération**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
    content += f"- **Nombre d'agents**: {len(analyses_by_agent)}\n"
    content += f"- **Nombre de sources**: {len(sources_set)}\n"
    content += f"- **Nombre total d'analyses**: {len(all_analyses)}\n\n"
    content += f"## Comparaison des agents\n\n"
    content += "| Agent | Analyses | Sophismes | Cohérence Moy. | Forces (extrait) | Faiblesses (extrait) |\n"
    content += "|-------|----------|-----------|----------------|------------------|----------------------|\n"

    for agent_name_key, agent_data in analyses_by_agent.items():
        num_analyses = sum(len(src_analyses) for src_analyses in agent_data.values())
        total_fallacies_agent = sum(an["analyses"]["fallacy_count"] for src_analyses in agent_data.values() for an in src_analyses)
        
        all_coherence_scores = [
            an["analyses"]["coherence_evaluation"]["overall_coherence"]["score"] 
            for src_analyses in agent_data.values() for an in src_analyses
        ]
        avg_coherence_agent = sum(all_coherence_scores) / len(all_coherence_scores) if all_coherence_scores else 0
        
        agent_info_cfg = next((agent for agent in rhetorical_agents_config if agent["name"] == agent_name_key), None)
        strengths = ", ".join(agent_info_cfg["strengths"][:2]) if agent_info_cfg else "N/A"
        weaknesses = ", ".join(agent_info_cfg["weaknesses"][:2]) if agent_info_cfg else "N/A"
        
        content += f"| {agent_name_key} | {num_analyses} | {total_fallacies_agent} | {avg_coherence_agent:.2f} | {strengths} | {weaknesses} |\n"

    content += "\n## Analyse par source\n\n"
    for source_name_key in sorted(list(sources_set)):
        content += f"### {source_name_key}\n\n"
        content += "| Agent | Extraits | Sophismes | Cohérence Moy. | Qualité Glob. Moy. |\n"
        content += "|-------|----------|-----------|----------------|--------------------|\n"
        for agent_name_key, agent_data_for_source in analyses_by_agent.items():
            if source_name_key in agent_data_for_source:
                source_specific_analyses = agent_data_for_source[source_name_key]
                num_extracts_src = len(source_specific_analyses)
                total_fallacies_src = sum(an["analyses"]["fallacy_count"] for an in source_specific_analyses)
                
                coherence_scores_src = [an["analyses"]["coherence_evaluation"]["overall_coherence"]["score"] for an in source_specific_analyses]
                avg_coherence_src = sum(coherence_scores_src) / len(coherence_scores_src) if coherence_scores_src else 0
                
                quality_scores_src = [an["analyses"]["metrics"]["overall_quality"] for an in source_specific_analyses]
                avg_quality_src = sum(quality_scores_src) / len(quality_scores_src) if quality_scores_src else 0
                
                content += f"| {agent_name_key} | {num_extracts_src} | {total_fallacies_src} | {avg_coherence_src:.2f} | {avg_quality_src:.2f} |\n"
        content += "\n"
        
    # ... (Le reste de la génération du rapport global peut être ajouté ici, comme les exemples de sophismes notables, etc.)

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"Rapport de synthèse global généré: {output_path}")
    return output_path


# --- Fonction Pipeline Principale ---

def run_summary_generation_pipeline(
    simulated_sources_data: List[Dict[str, Any]], 
    rhetorical_agents_data: List[Dict[str, Any]], 
    common_fallacies_data: List[Dict[str, Any]],
    output_reports_dir: Path
) -> None:
    """
    Orchestre la génération des analyses simulées et des rapports de synthèse.

    Ce pipeline principal itère sur les agents et les sources de données simulées,
    génère des analyses rhétoriques pour chaque extrait, crée des synthèses
    individuelles en Markdown, et produit un rapport de synthèse global.

    :param simulated_sources_data: Liste des données des sources simulées,
                                   chaque source contenant des extraits.
    :type simulated_sources_data: List[Dict[str, Any]]
    :param rhetorical_agents_data: Liste des configurations des agents rhétoriques.
    :type rhetorical_agents_data: List[Dict[str, Any]]
    :param common_fallacies_data: Liste des définitions des sophismes courants
                                  utilisés pour la simulation.
    :type common_fallacies_data: List[Dict[str, Any]]
    :param output_reports_dir: Répertoire (objet Path) de base où tous les rapports
                               et synthèses seront sauvegardés.
    :type output_reports_dir: Path
    :return: None
    :rtype: None
    """
    logger.info("Démarrage du pipeline de génération de synthèses d'analyses rhétoriques...")
    
    summaries_subdir = output_reports_dir / "summaries"
    summaries_subdir.mkdir(parents=True, exist_ok=True)
    
    all_generated_analyses: List[Dict[str, Any]] = []
    
    for agent_config_item in rhetorical_agents_data:
        logger.info(f"Pipeline: Traitement avec l'agent '{agent_config_item['name']}'...")
        for source_item in simulated_sources_data:
            source_name_item = source_item["source_name"]
            extracts_list = source_item["extracts"]
            for extract_def_item in extracts_list:
                analysis_result_item = generate_rhetorical_analysis_for_extract(
                    extract_def_item, 
                    source_name_item, 
                    agent_config_item,
                    common_fallacies_data # Passer les définitions de sophismes
                )
                all_generated_analyses.append(analysis_result_item)
                generate_markdown_summary_for_analysis(analysis_result_item, summaries_subdir)
    
    global_summary_file_path = generate_global_summary_report(
        all_generated_analyses, 
        output_reports_dir,
        rhetorical_agents_data # Passer la config des agents pour le rapport global
    )
    
    json_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_json_output_path = output_reports_dir / f"all_rhetorical_analyses_simulated_{json_timestamp}.json"
    
    try:
        with open(full_json_output_path, 'w', encoding='utf-8') as f_json:
            json.dump(all_generated_analyses, f_json, ensure_ascii=False, indent=2)
        logger.info(f"Toutes les analyses simulées sauvegardées en JSON: {full_json_output_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du JSON global des analyses: {e}", exc_info=True)

    logger.info(f"Pipeline de génération de synthèses terminé. Rapport global: {global_summary_file_path}")
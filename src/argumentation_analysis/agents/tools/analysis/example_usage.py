#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation des outils d'analyse rhétorique.

Ce script montre comment utiliser les outils d'analyse rhétorique pour analyser
un texte argumentatif, évaluer la gravité des sophismes, analyser les sophismes
complexes, et visualiser les résultats.
"""

import os
import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer les outils d'analyse rhétorique
from argumentation_analysis.agents.tools.analysis import (
    ContextualFallacyAnalyzer,
    FallacySeverityEvaluator,
    ComplexFallacyAnalyzer,
    RhetoricalResultAnalyzer,
    RhetoricalResultVisualizer
)


def main():
    """Fonction principale."""
    print("Exemple d'utilisation des outils d'analyse rhétorique")
    print("====================================================")
    
    # Texte argumentatif à analyser
    text = """
    Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà, 
    donc vous devriez l'essayer aussi. Si vous n'utilisez pas ce produit, vous risquez de souffrir de 
    problèmes de santé graves. Notre produit est le meilleur sur le marché, car il est nouveau et utilise 
    une technologie révolutionnaire. Tous nos concurrents vendent des produits dangereux et inefficaces.
    """
    
    print(f"\nTexte à analyser:\n{text}")
    
    # Créer un état partagé simulé
    state = {
        "raw_text": text,
        "identified_arguments": {
            "arg_1": "Les experts sont unanimes : ce produit est sûr et efficace.",
            "arg_2": "Des millions de personnes utilisent déjà ce produit.",
            "arg_3": "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.",
            "arg_4": "Notre produit est le meilleur sur le marché, car il est nouveau et utilise une technologie révolutionnaire.",
            "arg_5": "Tous nos concurrents vendent des produits dangereux et inefficaces."
        },
        "identified_fallacies": {
            "fallacy_1": {
                "type": "Appel à l'autorité",
                "justification": "L'argument s'appuie sur l'autorité des experts sans fournir de preuves concrètes.",
                "target_argument_id": "arg_1"
            },
            "fallacy_2": {
                "type": "Appel à la popularité",
                "justification": "L'argument s'appuie sur la popularité du produit pour justifier son efficacité.",
                "target_argument_id": "arg_2"
            },
            "fallacy_3": {
                "type": "Faux dilemme",
                "justification": "L'argument présente une fausse alternative entre utiliser le produit ou souffrir de problèmes de santé.",
                "target_argument_id": "arg_3"
            },
            "fallacy_4": {
                "type": "Appel à la nouveauté",
                "justification": "L'argument suggère que le produit est meilleur simplement parce qu'il est nouveau.",
                "target_argument_id": "arg_4"
            },
            "fallacy_5": {
                "type": "Généralisation hâtive",
                "justification": "L'argument généralise à tous les concurrents sans preuves suffisantes.",
                "target_argument_id": "arg_5"
            }
        },
        "belief_sets": {
            "bs_1": {
                "logic_type": "Propositional",
                "content": "A: Le produit est sûr et efficace\nB: Des millions de personnes utilisent le produit\nC: Vous devriez utiliser le produit\nD: Vous souffrirez de problèmes de santé graves\n\nA → C\nB → C\n¬C → D"
            }
        },
        "answers": {
            "task_1": {
                "author_agent": "InformalAnalysisAgent",
                "answer_text": "J'ai identifié cinq sophismes dans le texte : un appel à l'autorité, un appel à la popularité, un faux dilemme, un appel à la nouveauté et une généralisation hâtive.",
                "source_ids": ["fallacy_1", "fallacy_2", "fallacy_3", "fallacy_4", "fallacy_5"]
            },
            "task_2": {
                "author_agent": "PropositionalLogicAgent",
                "answer_text": "J'ai formalisé les arguments en logique propositionnelle et identifié une structure de raisonnement fallacieuse.",
                "source_ids": ["bs_1"]
            }
        },
        "final_conclusion": "Le texte contient plusieurs sophismes qui affaiblissent significativement sa validité argumentative."
    }
    
    # 1. Analyse contextuelle des sophismes
    print("\n1. Analyse contextuelle des sophismes")
    print("------------------------------------")
    contextual_analyzer = ContextualFallacyAnalyzer()
    
    # Analyser le contexte
    context = "Discours commercial pour un produit controversé"
    contextual_results = contextual_analyzer.analyze_context(text, context)
    print(f"Résultats de l'analyse contextuelle: {len(contextual_results['contextual_fallacies'])} sophismes identifiés")
    
    # Identifier les sophismes contextuels
    contextual_fallacies = contextual_analyzer.identify_contextual_fallacies(text, context)
    print(f"Sophismes contextuels identifiés: {len(contextual_fallacies)}")
    for i, fallacy in enumerate(contextual_fallacies):
        print(f"  {i+1}. {fallacy['fallacy_type']} (confiance: {fallacy['confidence']:.2f})")
    
    # 2. Évaluation de la gravité des sophismes
    print("\n2. Évaluation de la gravité des sophismes")
    print("----------------------------------------")
    severity_evaluator = FallacySeverityEvaluator()
    
    # Évaluer la gravité des sophismes
    for fallacy_id, fallacy in state["identified_fallacies"].items():
        fallacy_type = fallacy["type"]
        target_arg_id = fallacy.get("target_argument_id")
        if target_arg_id and target_arg_id in state["identified_arguments"]:
            argument = state["identified_arguments"][target_arg_id]
            severity_results = severity_evaluator.evaluate_severity(fallacy_type, argument, context)
            print(f"  {fallacy_id} ({fallacy_type}): Score de gravité = {severity_results['final_score']:.2f} ({severity_results['severity_level']})")
    
    # Classer les sophismes par gravité
    fallacies_to_rank = []
    for fallacy_id, fallacy in state["identified_fallacies"].items():
        fallacy_type = fallacy["type"]
        target_arg_id = fallacy.get("target_argument_id")
        if target_arg_id and target_arg_id in state["identified_arguments"]:
            argument = state["identified_arguments"][target_arg_id]
            fallacies_to_rank.append({
                "fallacy_type": fallacy_type,
                "argument": argument,
                "context": context
            })
    
    ranked_fallacies = severity_evaluator.rank_fallacies(fallacies_to_rank)
    print("\nSophismes classés par gravité:")
    for i, fallacy in enumerate(ranked_fallacies):
        print(f"  {i+1}. {fallacy['fallacy_type']} (gravité: {fallacy['severity']:.2f}, niveau: {fallacy['severity_level']})")
    
    # 3. Analyse des sophismes complexes
    print("\n3. Analyse des sophismes complexes")
    print("--------------------------------")
    complex_analyzer = ComplexFallacyAnalyzer()
    
    # Identifier les combinaisons de sophismes
    combined_fallacies = complex_analyzer.identify_combined_fallacies(text)
    print(f"Combinaisons de sophismes identifiées: {len(combined_fallacies)}")
    for i, fallacy in enumerate(combined_fallacies):
        print(f"  {i+1}. {fallacy['combination_name']} (composants: {', '.join(fallacy['components'])})")
    
    # Analyser les sophismes structurels
    arguments = list(state["identified_arguments"].values())
    structural_fallacies = complex_analyzer.analyze_structural_fallacies(arguments)
    print(f"Sophismes structurels identifiés: {len(structural_fallacies)}")
    for i, fallacy in enumerate(structural_fallacies):
        print(f"  {i+1}. {fallacy['structural_fallacy_type']}")
    
    # Identifier les motifs de sophismes
    patterns = complex_analyzer.identify_fallacy_patterns(text)
    print(f"Motifs de sophismes identifiés: {len(patterns)}")
    for i, pattern in enumerate(patterns):
        print(f"  {i+1}. {pattern['pattern_type']}: {pattern['description']}")
    
    # 4. Analyse des résultats
    print("\n4. Analyse des résultats")
    print("----------------------")
    result_analyzer = RhetoricalResultAnalyzer()
    
    # Analyser les résultats
    analysis_results = result_analyzer.analyze_results(state)
    print(f"Métriques de base:")
    print(f"  Arguments: {analysis_results['metrics']['argument_count']}")
    print(f"  Sophismes: {analysis_results['metrics']['fallacy_count']}")
    print(f"  Ratio sophismes/arguments: {analysis_results['metrics']['fallacy_per_argument']:.2f}")
    
    print(f"\nÉvaluation de la qualité:")
    print(f"  Score de complétude: {analysis_results['quality_evaluation']['completeness_score']:.2f}")
    print(f"  Score de profondeur: {analysis_results['quality_evaluation']['depth_score']:.2f}")
    print(f"  Score de cohérence: {analysis_results['quality_evaluation']['coherence_score']:.2f}")
    print(f"  Score global: {analysis_results['quality_evaluation']['overall_score']:.2f}")
    print(f"  Niveau de qualité: {analysis_results['quality_evaluation']['quality_level']}")
    
    # Extraire des insights
    insights = result_analyzer.extract_insights(state)
    print(f"\nInsights extraits: {len(insights)}")
    for i, insight in enumerate(insights):
        print(f"  {i+1}. {insight['title']} (importance: {insight['importance']})")
    
    # Générer un résumé
    summary = result_analyzer.generate_summary(state)
    print(f"\nRésumé généré: {len(summary)} caractères")
    
    # 5. Visualisation des résultats
    print("\n5. Visualisation des résultats")
    print("----------------------------")
    result_visualizer = RhetoricalResultVisualizer()
    
    # Générer les visualisations
    visualizations = result_visualizer.generate_all_visualizations(state)
    print(f"Visualisations générées:")
    for viz_name, viz_code in visualizations.items():
        print(f"  {viz_name}: {len(viz_code)} caractères")
    
    # Générer un rapport HTML
    html_report = result_visualizer.generate_html_report(state)
    print(f"\nRapport HTML généré: {len(html_report)} caractères")
    
    # Sauvegarder le rapport HTML
    report_path = Path("rapport_analyse_rhetorique.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    print(f"Rapport HTML sauvegardé dans {report_path.absolute()}")


if __name__ == "__main__":
    main()
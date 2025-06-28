#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fournit un outil pour l'analyse méta des résultats d'une analyse rhétorique.

Ce module définit `RhetoricalResultAnalyzer`, un outil qui n'analyse pas le
texte brut, mais plutôt l'état (`state`) résultant d'une analyse rhétorique
préalable. Son but est de calculer des métriques, d'évaluer la qualité globale
de l'analyse, d'extraire des insights de haut niveau et de générer des résumés.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import Counter

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RhetoricalResultAnalyzer")


class RhetoricalResultAnalyzer:
    """
    Analyse un état contenant les résultats d'une analyse rhétorique.

    Cette classe prend en entrée un dictionnaire (`state`) qui représente
    l'ensemble des données collectées lors d'une analyse (arguments identifiés,
    sophismes, etc.) et produit une analyse de second niveau sur ces données.
    """

    def __init__(self):
        """Initialise l'analyseur de résultats rhétoriques."""
        self.logger = logger
        self.logger.info("Analyseur de résultats rhétoriques initialisé.")
    
    def analyze_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Point d'entrée principal pour analyser l'état des résultats.

        Cette méthode prend l'état complet d'une analyse et orchestre une série
        de sous-analyses pour calculer des métriques, évaluer la qualité et
        structurer les résultats.

        Args:
            state (Dict[str, Any]): L'état partagé contenant les résultats bruts
                de l'analyse rhétorique (arguments, sophismes, etc.).

        Returns:
            Dict[str, Any]: Un dictionnaire structuré contenant les résultats de
            cette méta-analyse, incluant des métriques, des analyses de
            sophismes, d'arguments, et une évaluation de la qualité.
        """
        self.logger.info("Analyse des résultats d'une analyse rhétorique")
        
        # Extraire les informations pertinentes de l'état
        raw_text = state.get("raw_text", "")
        identified_arguments = state.get("identified_arguments", {})
        identified_fallacies = state.get("identified_fallacies", {})
        belief_sets = state.get("belief_sets", {})
        answers = state.get("answers", {})
        final_conclusion = state.get("final_conclusion", None)
        
        # Calculer les métriques de base
        metrics = self._calculate_basic_metrics(
            raw_text, identified_arguments, identified_fallacies, belief_sets, answers
        )
        
        # Analyser les sophismes
        fallacy_analysis = self._analyze_fallacies(identified_fallacies, identified_arguments)
        
        # Analyser les arguments
        argument_analysis = self._analyze_arguments(identified_arguments, identified_fallacies)
        
        # Analyser les réponses
        answer_analysis = self._analyze_answers(answers)
        
        # Évaluer la qualité globale de l'analyse
        quality_evaluation = self._evaluate_analysis_quality(
            metrics, fallacy_analysis, argument_analysis, answer_analysis
        )
        
        # Préparer les résultats
        results = {
            "metrics": metrics,
            "fallacy_analysis": fallacy_analysis,
            "argument_analysis": argument_analysis,
            "answer_analysis": answer_analysis,
            "quality_evaluation": quality_evaluation,
            "has_conclusion": final_conclusion is not None
        }
    def _calculate_basic_metrics(
        self,
        raw_text: str,
        identified_arguments: Dict[str, str],
        identified_fallacies: Dict[str, Dict[str, Any]],
        belief_sets: Dict[str, Dict[str, Any]],
        answers: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calcule les métriques de base de l'analyse.
        
        Args:
            raw_text: Texte brut analysé
            identified_arguments: Arguments identifiés
            identified_fallacies: Sophismes identifiés
            belief_sets: Ensembles de croyances
            answers: Réponses aux tâches
            
        Returns:
            Dictionnaire contenant les métriques de base
        """
        # Calculer les métriques de base
        text_length = len(raw_text)
        word_count = len(raw_text.split())
        argument_count = len(identified_arguments)
        fallacy_count = len(identified_fallacies)
        belief_set_count = len(belief_sets)
        answer_count = len(answers)
        
        # Calculer les ratios
        fallacy_per_argument = fallacy_count / argument_count if argument_count > 0 else 0
        argument_per_100_words = (argument_count * 100) / word_count if word_count > 0 else 0
        fallacy_per_100_words = (fallacy_count * 100) / word_count if word_count > 0 else 0
        
        # Préparer les métriques
        metrics = {
            "text_length": text_length,
            "word_count": word_count,
            "argument_count": argument_count,
            "fallacy_count": fallacy_count,
            "belief_set_count": belief_set_count,
            "answer_count": answer_count,
            "fallacy_per_argument": fallacy_per_argument,
            "argument_per_100_words": argument_per_100_words,
            "fallacy_per_100_words": fallacy_per_100_words
        }
        
        return metrics
    
    def _analyze_fallacies(
        self,
        identified_fallacies: Dict[str, Dict[str, Any]],
        identified_arguments: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analyse les sophismes identifiés.
        
        Args:
            identified_fallacies: Sophismes identifiés
            identified_arguments: Arguments identifiés
            
        Returns:
            Dictionnaire contenant l'analyse des sophismes
        """
        # Si aucun sophisme n'a été identifié, retourner une analyse vide
        if not identified_fallacies:
            return {
                "fallacy_types": {},
                "most_common_fallacy": None,
                "fallacies_with_targets": 0,
                "fallacies_without_targets": 0,
                "targeted_arguments": set(),
                "untargeted_arguments": set()
            }
        
        # Compter les types de sophismes
        fallacy_types = Counter()
        fallacies_with_targets = 0
        fallacies_without_targets = 0
        targeted_arguments = set()
        untargeted_arguments = set(identified_arguments.keys())
        
        for fallacy_id, fallacy in identified_fallacies.items():
            fallacy_type = fallacy.get("type", "Type inconnu")
            fallacy_types[fallacy_type] += 1
            
            target_arg_id = fallacy.get("target_argument_id")
            if target_arg_id:
                fallacies_with_targets += 1
                targeted_arguments.add(target_arg_id)
                if target_arg_id in untargeted_arguments:
                    untargeted_arguments.remove(target_arg_id)
            else:
                fallacies_without_targets += 1
        
        # Déterminer le type de sophisme le plus courant
        most_common_fallacy = fallacy_types.most_common(1)[0] if fallacy_types else None
        
        # Préparer l'analyse
        fallacy_analysis = {
            "fallacy_types": dict(fallacy_types),
            "most_common_fallacy": most_common_fallacy,
            "fallacies_with_targets": fallacies_with_targets,
            "fallacies_without_targets": fallacies_without_targets,
            "targeted_arguments": list(targeted_arguments),
            "untargeted_arguments": list(untargeted_arguments)
        }
        
        return fallacy_analysis
    
    def _analyze_arguments(
        self,
        identified_arguments: Dict[str, str],
        identified_fallacies: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyse les arguments identifiés.
        
        Args:
            identified_arguments: Arguments identifiés
            identified_fallacies: Sophismes identifiés
            
        Returns:
            Dictionnaire contenant l'analyse des arguments
        """
        # Si aucun argument n'a été identifié, retourner une analyse vide
        if not identified_arguments:
            return {
                "average_argument_length": 0,
                "arguments_with_fallacies": 0,
                "arguments_without_fallacies": 0,
                "fallacies_per_argument": {}
            }
        
        # Calculer la longueur moyenne des arguments
        argument_lengths = [len(arg) for arg in identified_arguments.values()]
        average_argument_length = sum(argument_lengths) / len(argument_lengths)
        
        # Compter les arguments avec et sans sophismes
        arguments_with_fallacies = set()
        fallacies_per_argument = {}
        
        for fallacy_id, fallacy in identified_fallacies.items():
            target_arg_id = fallacy.get("target_argument_id")
            if target_arg_id:
                arguments_with_fallacies.add(target_arg_id)
                fallacies_per_argument[target_arg_id] = fallacies_per_argument.get(target_arg_id, 0) + 1
        
        arguments_without_fallacies = len(identified_arguments) - len(arguments_with_fallacies)
        
        # Préparer l'analyse
        argument_analysis = {
            "average_argument_length": average_argument_length,
            "arguments_with_fallacies": len(arguments_with_fallacies),
            "arguments_without_fallacies": arguments_without_fallacies,
            "fallacies_per_argument": fallacies_per_argument
        }
        
        return argument_analysis
    
    def _analyze_answers(self, answers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyse les réponses aux tâches.
        
        Args:
            answers: Réponses aux tâches
            
        Returns:
            Dictionnaire contenant l'analyse des réponses
        """
        # Si aucune réponse n'a été fournie, retourner une analyse vide
        if not answers:
            return {
                "answer_count": 0,
                "answers_by_agent": {},
                "answers_with_sources": 0,
                "answers_without_sources": 0
            }
        
        # Compter les réponses par agent
        answers_by_agent = Counter()
        answers_with_sources = 0
        answers_without_sources = 0
        
        for task_id, answer in answers.items():
            author_agent = answer.get("author_agent", "Agent inconnu")
            answers_by_agent[author_agent] += 1
            
            source_ids = answer.get("source_ids", [])
            if source_ids:
                answers_with_sources += 1
            else:
                answers_without_sources += 1
        
        # Préparer l'analyse
        answer_analysis = {
            "answer_count": len(answers),
            "answers_by_agent": dict(answers_by_agent),
            "answers_with_sources": answers_with_sources,
            "answers_without_sources": answers_without_sources
        }
        
        return answer_analysis
    
    def _evaluate_analysis_quality(
        self,
        metrics: Dict[str, Any],
        fallacy_analysis: Dict[str, Any],
        argument_analysis: Dict[str, Any],
        answer_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Évalue la qualité globale de l'analyse.
        
        Args:
            metrics: Métriques de base
            fallacy_analysis: Analyse des sophismes
            argument_analysis: Analyse des arguments
            answer_analysis: Analyse des réponses
            
        Returns:
            Dictionnaire contenant l'évaluation de la qualité
        """
        # Calculer les scores de qualité
        completeness_score = self._calculate_completeness_score(metrics, answer_analysis)
        depth_score = self._calculate_depth_score(metrics, fallacy_analysis, argument_analysis)
        coherence_score = self._calculate_coherence_score(fallacy_analysis, argument_analysis, answer_analysis)
        
        # Calculer le score global
        overall_score = (completeness_score + depth_score + coherence_score) / 3
        
        # Déterminer le niveau de qualité
        quality_level = self._determine_quality_level(overall_score)
        
        # Générer des recommandations
        recommendations = self._generate_recommendations(
            metrics, fallacy_analysis, argument_analysis, answer_analysis,
            completeness_score, depth_score, coherence_score
        )
        
        # Préparer l'évaluation
        quality_evaluation = {
            "completeness_score": completeness_score,
            "depth_score": depth_score,
            "coherence_score": coherence_score,
            "overall_score": overall_score,
            "quality_level": quality_level,
            "recommendations": recommendations
        }
        
        return quality_evaluation
    
    def _calculate_completeness_score(
        self,
        metrics: Dict[str, Any],
        answer_analysis: Dict[str, Any]
    ) -> float:
        """
        Calcule le score de complétude de l'analyse.
        
        Args:
            metrics: Métriques de base
            answer_analysis: Analyse des réponses
            
        Returns:
            Score de complétude (0.0 à 1.0)
        """
        # Facteurs de complétude
        has_arguments = metrics["argument_count"] > 0
        has_fallacies = metrics["fallacy_count"] > 0
        has_belief_sets = metrics["belief_set_count"] > 0
        has_answers = metrics["answer_count"] > 0
        
        # Calculer le score
        completeness_factors = [has_arguments, has_fallacies, has_belief_sets, has_answers]
        completeness_score = sum(1 for factor in completeness_factors if factor) / len(completeness_factors)
        
        return completeness_score
    
    def _calculate_depth_score(
        self,
        metrics: Dict[str, Any],
        fallacy_analysis: Dict[str, Any],
        argument_analysis: Dict[str, Any]
    ) -> float:
        """
        Calcule le score de profondeur de l'analyse.
        
        Args:
            metrics: Métriques de base
            fallacy_analysis: Analyse des sophismes
            argument_analysis: Analyse des arguments
            
        Returns:
            Score de profondeur (0.0 à 1.0)
        """
        # Facteurs de profondeur
        fallacy_per_argument_score = min(1.0, metrics["fallacy_per_argument"] / 2)
        argument_per_100_words_score = min(1.0, metrics["argument_per_100_words"] / 5)
        
        # Calculer le score
        depth_score = (fallacy_per_argument_score + argument_per_100_words_score) / 2
        
        return depth_score
    def _calculate_coherence_score(
        self,
        fallacy_analysis: Dict[str, Any],
        argument_analysis: Dict[str, Any],
        answer_analysis: Dict[str, Any]
    ) -> float:
        """
        Calcule le score de cohérence de l'analyse.
        
        Args:
            fallacy_analysis: Analyse des sophismes
            argument_analysis: Analyse des arguments
            answer_analysis: Analyse des réponses
            
        Returns:
            Score de cohérence (0.0 à 1.0)
        """
        # Facteurs de cohérence
        fallacies_with_targets_ratio = fallacy_analysis["fallacies_with_targets"] / (fallacy_analysis["fallacies_with_targets"] + fallacy_analysis["fallacies_without_targets"]) if (fallacy_analysis["fallacies_with_targets"] + fallacy_analysis["fallacies_without_targets"]) > 0 else 0
        answers_with_sources_ratio = answer_analysis["answers_with_sources"] / answer_analysis["answer_count"] if answer_analysis["answer_count"] > 0 else 0
        
        # Calculer le score
        coherence_score = (fallacies_with_targets_ratio + answers_with_sources_ratio) / 2
        
        return coherence_score
    
    def _determine_quality_level(self, overall_score: float) -> str:
        """
        Détermine le niveau de qualité en fonction du score global.
        
        Args:
            overall_score: Score global
            
        Returns:
            Niveau de qualité (Insuffisant, Basique, Bon, Excellent)
        """
        if overall_score < 0.3:
            return "Insuffisant"
        elif overall_score < 0.6:
            return "Basique"
        elif overall_score < 0.8:
            return "Bon"
        else:
            return "Excellent"
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, Any],
        fallacy_analysis: Dict[str, Any],
        argument_analysis: Dict[str, Any],
        answer_analysis: Dict[str, Any],
        completeness_score: float,
        depth_score: float,
        coherence_score: float
    ) -> List[str]:
        """
        Génère des recommandations pour améliorer l'analyse.
        
        Args:
            metrics: Métriques de base
            fallacy_analysis: Analyse des sophismes
            argument_analysis: Analyse des arguments
            answer_analysis: Analyse des réponses
            completeness_score: Score de complétude
            depth_score: Score de profondeur
            coherence_score: Score de cohérence
            
        Returns:
            Liste de recommandations
        """
        recommendations = []
        
        # Recommandations basées sur la complétude
        if completeness_score < 0.5:
            if metrics["argument_count"] == 0:
                recommendations.append("Identifier les arguments dans le texte.")
            if metrics["fallacy_count"] == 0:
                recommendations.append("Identifier les sophismes dans les arguments.")
            if metrics["belief_set_count"] == 0:
                recommendations.append("Créer des ensembles de croyances pour l'analyse formelle.")
            if metrics["answer_count"] == 0:
                recommendations.append("Fournir des réponses aux tâches d'analyse.")
        
        # Recommandations basées sur la profondeur
        if depth_score < 0.5:
            if metrics["fallacy_per_argument"] < 0.5:
                recommendations.append("Approfondir l'analyse des sophismes dans les arguments.")
            if metrics["argument_per_100_words"] < 2:
                recommendations.append("Identifier plus d'arguments dans le texte.")
        
        # Recommandations basées sur la cohérence
        if coherence_score < 0.5:
            if fallacy_analysis["fallacies_without_targets"] > fallacy_analysis["fallacies_with_targets"]:
                recommendations.append("Associer les sophismes identifiés à des arguments spécifiques.")
            if answer_analysis["answers_without_sources"] > answer_analysis["answers_with_sources"]:
                recommendations.append("Citer les sources utilisées dans les réponses.")
        
        return recommendations
    
    def extract_insights(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrait des insights des résultats d'une analyse rhétorique.
        
        Cette méthode analyse l'état partagé contenant les résultats d'une analyse
        rhétorique pour en extraire des insights pertinents.
        
        Args:
            state: État partagé contenant les résultats
            
        Returns:
            Liste des insights extraits
        """
        self.logger.info("Extraction d'insights des résultats d'une analyse rhétorique")
        
        # Analyser les résultats
        analysis_results = self.analyze_results(state)
        
        # Extraire les insights
        insights = []
        
        # Insight sur le type de sophisme le plus courant
        most_common_fallacy = analysis_results["fallacy_analysis"].get("most_common_fallacy")
        if most_common_fallacy:
            fallacy_type, count = most_common_fallacy
            insights.append({
                "type": "most_common_fallacy",
                "title": f"Le sophisme le plus courant est '{fallacy_type}'",
                "description": f"Ce sophisme apparaît {count} fois dans le texte, ce qui suggère une tendance argumentative spécifique.",
                "importance": "Élevée"
            })
        
        # Insight sur les arguments avec le plus de sophismes
        fallacies_per_argument = analysis_results["argument_analysis"].get("fallacies_per_argument", {})
        if fallacies_per_argument:
            max_fallacies_arg_id = max(fallacies_per_argument, key=fallacies_per_argument.get)
            max_fallacies_count = fallacies_per_argument[max_fallacies_arg_id]
            insights.append({
                "type": "argument_with_most_fallacies",
                "title": f"L'argument {max_fallacies_arg_id} contient le plus de sophismes",
                "description": f"Cet argument contient {max_fallacies_count} sophismes, ce qui suggère une faiblesse argumentative significative.",
                "importance": "Élevée"
            })
        
        # Insight sur la qualité globale de l'analyse
        quality_level = analysis_results["quality_evaluation"].get("quality_level")
        if quality_level:
            insights.append({
                "type": "analysis_quality",
                "title": f"La qualité globale de l'analyse est '{quality_level}'",
                "description": f"Cette évaluation est basée sur la complétude, la profondeur et la cohérence de l'analyse.",
                "importance": "Moyenne"
            })
        
        # Insight sur les recommandations
        recommendations = analysis_results["quality_evaluation"].get("recommendations", [])
        if recommendations:
            insights.append({
                "type": "recommendations",
                "title": f"{len(recommendations)} recommandations pour améliorer l'analyse",
                "description": "Ces recommandations visent à améliorer la qualité de l'analyse rhétorique.",
                "recommendations": recommendations,
                "importance": "Moyenne"
            })
        
        # Insight sur la distribution des réponses par agent
        answers_by_agent = analysis_results["answer_analysis"].get("answers_by_agent", {})
        if answers_by_agent:
            most_active_agent = max(answers_by_agent, key=answers_by_agent.get)
            insights.append({
                "type": "agent_participation",
                "title": f"L'agent '{most_active_agent}' a fourni le plus de réponses",
                "description": f"Cet agent a fourni {answers_by_agent[most_active_agent]} réponses sur un total de {analysis_results['answer_analysis']['answer_count']}.",
                "importance": "Faible"
            })
        
        return insights
    def generate_summary(self, state: Dict[str, Any]) -> str:
        """
        Génère un résumé des résultats d'une analyse rhétorique.
        
        Cette méthode analyse l'état partagé contenant les résultats d'une analyse
        rhétorique pour en générer un résumé textuel.
        
        Args:
            state: État partagé contenant les résultats
            
        Returns:
            Résumé des résultats
        """
        self.logger.info("Génération d'un résumé des résultats d'une analyse rhétorique")
        
        # Analyser les résultats
        analysis_results = self.analyze_results(state)
        
        # Extraire les insights
        insights = self.extract_insights(state)
        
        # Générer le résumé
        summary = []
        
        # Introduction
        summary.append("# Résumé de l'Analyse Rhétorique")
        summary.append("")
        
        # Métriques de base
        metrics = analysis_results["metrics"]
        summary.append("## Métriques de Base")
        summary.append(f"- **Texte analysé:** {metrics['word_count']} mots ({metrics['text_length']} caractères)")
        summary.append(f"- **Arguments identifiés:** {metrics['argument_count']}")
        summary.append(f"- **Sophismes identifiés:** {metrics['fallacy_count']}")
        summary.append(f"- **Ratio sophismes/arguments:** {metrics['fallacy_per_argument']:.2f}")
        summary.append("")
        
        # Analyse des sophismes
        fallacy_analysis = analysis_results["fallacy_analysis"]
        summary.append("## Analyse des Sophismes")
        
        if fallacy_analysis["most_common_fallacy"]:
            fallacy_type, count = fallacy_analysis["most_common_fallacy"]
            summary.append(f"- **Sophisme le plus courant:** {fallacy_type} ({count} occurrences)")
        
        summary.append(f"- **Sophismes avec cible:** {fallacy_analysis['fallacies_with_targets']}")
        summary.append(f"- **Sophismes sans cible:** {fallacy_analysis['fallacies_without_targets']}")
        
        # Distribution des types de sophismes
        if fallacy_analysis["fallacy_types"]:
            summary.append("- **Distribution des types de sophismes:**")
            for fallacy_type, count in fallacy_analysis["fallacy_types"].items():
                summary.append(f"  - {fallacy_type}: {count}")
        
        summary.append("")
        
        # Analyse des arguments
        argument_analysis = analysis_results["argument_analysis"]
        summary.append("## Analyse des Arguments")
        summary.append(f"- **Longueur moyenne des arguments:** {argument_analysis['average_argument_length']:.2f} caractères")
        summary.append(f"- **Arguments avec sophismes:** {argument_analysis['arguments_with_fallacies']}")
        summary.append(f"- **Arguments sans sophismes:** {argument_analysis['arguments_without_fallacies']}")
        
        # Arguments avec le plus de sophismes
        if argument_analysis["fallacies_per_argument"]:
            max_fallacies_arg_id = max(argument_analysis["fallacies_per_argument"], key=argument_analysis["fallacies_per_argument"].get)
            max_fallacies_count = argument_analysis["fallacies_per_argument"][max_fallacies_arg_id]
            summary.append(f"- **Argument avec le plus de sophismes:** {max_fallacies_arg_id} ({max_fallacies_count} sophismes)")
        
        summary.append("")
        
        # Évaluation de la qualité
        quality_evaluation = analysis_results["quality_evaluation"]
        summary.append("## Évaluation de la Qualité")
        summary.append(f"- **Score de complétude:** {quality_evaluation['completeness_score']:.2f}")
        summary.append(f"- **Score de profondeur:** {quality_evaluation['depth_score']:.2f}")
        summary.append(f"- **Score de cohérence:** {quality_evaluation['coherence_score']:.2f}")
        summary.append(f"- **Score global:** {quality_evaluation['overall_score']:.2f}")
        summary.append(f"- **Niveau de qualité:** {quality_evaluation['quality_level']}")
        
        # Recommandations
        if quality_evaluation["recommendations"]:
            summary.append("- **Recommandations:**")
            for recommendation in quality_evaluation["recommendations"]:
                summary.append(f"  - {recommendation}")
        
        summary.append("")
        
        # Insights principaux
        if insights:
            summary.append("## Insights Principaux")
            for insight in insights:
                if insight["importance"] == "Élevée":
                    summary.append(f"- **{insight['title']}:** {insight['description']}")
            
            summary.append("")
        
        # Conclusion
        summary.append("## Conclusion")
        summary.append(f"Cette analyse rhétorique a identifié {metrics['argument_count']} arguments et {metrics['fallacy_count']} sophismes dans le texte. ")
        
        if quality_evaluation["quality_level"] in ["Bon", "Excellent"]:
            summary.append(f"La qualité globale de l'analyse est {quality_evaluation['quality_level'].lower()}, avec une bonne couverture des aspects rhétoriques du texte.")
        else:
            summary.append(f"La qualité globale de l'analyse est {quality_evaluation['quality_level'].lower()}, ce qui suggère des opportunités d'amélioration.")
        
        # Joindre les lignes du résumé
        return "\n".join(summary)


# Test de la classe si exécutée directement
if __name__ == "__main__":
    analyzer = RhetoricalResultAnalyzer()
    
    # Exemple d'état partagé
    state = {
        "raw_text": "Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà, donc vous devriez l'essayer aussi. Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.",
        "identified_arguments": {
            "arg_1": "Les experts sont unanimes : ce produit est sûr et efficace.",
            "arg_2": "Des millions de personnes utilisent déjà ce produit.",
            "arg_3": "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
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
                "answer_text": "J'ai identifié trois sophismes dans le texte : un appel à l'autorité, un appel à la popularité et un faux dilemme.",
                "source_ids": ["fallacy_1", "fallacy_2", "fallacy_3"]
            },
            "task_2": {
                "author_agent": "PropositionalLogicAgent",
                "answer_text": "J'ai formalisé les arguments en logique propositionnelle et identifié une structure de raisonnement fallacieuse.",
                "source_ids": ["bs_1"]
            }
        },
        "final_conclusion": "Le texte contient plusieurs sophismes qui affaiblissent significativement sa validité argumentative."
    }
    
    # Analyser les résultats
    results = analyzer.analyze_results(state)
    print(f"Résultats de l'analyse: {json.dumps(results, indent=2, ensure_ascii=False)}")
    
    # Extraire des insights
    insights = analyzer.extract_insights(state)
    print(f"Insights extraits: {json.dumps(insights, indent=2, ensure_ascii=False)}")
    
    # Générer un résumé
    summary = analyzer.generate_summary(state)
    print(f"Résumé généré:\n{summary}")
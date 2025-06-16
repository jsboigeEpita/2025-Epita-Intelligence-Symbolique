#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Évaluateur de cohérence des arguments.

Ce module fournit des fonctionnalités pour évaluer la cohérence
entre les arguments d'un ensemble argumentatif.
"""

import os
import sys
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer l'analyseur sémantique d'arguments
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ArgumentCoherenceEvaluator")


class ArgumentCoherenceEvaluator:
    """
    Évaluateur de cohérence des arguments.
    
    Cette classe fournit des méthodes pour évaluer différents types de cohérence
    entre les arguments d'un ensemble argumentatif.
    """
    
    def __init__(self):
        """
        Initialise l'évaluateur de cohérence des arguments.
        """
        self.logger = logger
        
        # Initialiser l'analyseur sémantique
        self.semantic_analyzer = SemanticArgumentAnalyzer()
        
        # Définir les types de cohérence et leur importance
        self.coherence_types = {
            "logique": {
                "description": "Cohérence logique entre les arguments",
                "importance": 0.3
            },
            "thématique": {
                "description": "Cohérence thématique entre les arguments",
                "importance": 0.2
            },
            "structurelle": {
                "description": "Cohérence structurelle entre les arguments",
                "importance": 0.2
            },
            "rhétorique": {
                "description": "Cohérence rhétorique entre les arguments",
                "importance": 0.15
            },
            "épistémique": {
                "description": "Cohérence épistémique entre les arguments",
                "importance": 0.15
            }
        }
        
        self.logger.info("Évaluateur de cohérence des arguments initialisé.")
    
    def evaluate_coherence(
        self,
        arguments: List[str],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Évalue la cohérence globale entre les arguments.
        
        Cette méthode évalue différents types de cohérence entre les arguments
        et fournit une évaluation globale de la cohérence.
        
        Args:
            arguments (List[str]): Liste des arguments à évaluer
            context (Optional[str]): Contexte des arguments
            
        Returns:
            Dict[str, Any]: Résultats de l'évaluation de cohérence
        """
        self.logger.info(f"Évaluation de la cohérence de {len(arguments)} arguments")
        
        # Si le contexte n'est pas spécifié, utiliser un contexte par défaut
        if not context:
            context = "Analyse d'arguments"
        
        # Analyser la structure sémantique des arguments
        semantic_analysis = self.semantic_analyzer.analyze_multiple_arguments(arguments)
        
        # Évaluer les différents types de cohérence
        logical_coherence = self._evaluate_logical_coherence(arguments, semantic_analysis)
        thematic_coherence = self._evaluate_thematic_coherence(arguments, semantic_analysis)
        structural_coherence = self._evaluate_structural_coherence(arguments, semantic_analysis)
        rhetorical_coherence = self._evaluate_rhetorical_coherence(arguments, semantic_analysis)
        epistemic_coherence = self._evaluate_epistemic_coherence(arguments, semantic_analysis)
        
        # Calculer la cohérence globale
        coherence_evaluations = {
            "logique": logical_coherence,
            "thématique": thematic_coherence,
            "structurelle": structural_coherence,
            "rhétorique": rhetorical_coherence,
            "épistémique": epistemic_coherence
        }
        
        overall_coherence = self._calculate_overall_coherence(coherence_evaluations)
        
        # Générer des recommandations pour améliorer la cohérence
        recommendations = self._generate_recommendations(arguments, coherence_evaluations, overall_coherence)
        
        # Préparer les résultats
        results = {
            "overall_coherence": overall_coherence,
            "coherence_evaluations": coherence_evaluations,
            "recommendations": recommendations,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        return results
    
    def _evaluate_logical_coherence(
        self,
        arguments: List[str],
        semantic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Évalue la cohérence logique entre les arguments.
        
        Args:
            arguments (List[str]): Liste des arguments
            semantic_analysis (Dict[str, Any]): Analyse sémantique des arguments
            
        Returns:
            Dict[str, Any]: Évaluation de la cohérence logique
        """
        # Simuler l'évaluation de la cohérence logique
        return {
            "score": 0.8,
            "level": "Bon",
            "criteria_scores": {
                "absence_contradictions": 0.9,
                "validite_inferences": 0.7,
                "completude_raisonnement": 0.8,
                "pertinence_premisses": 0.8
            },
            "specific_issues": [],
            "importance": self.coherence_types["logique"]["importance"]
        }
    
    def _evaluate_thematic_coherence(
        self,
        arguments: List[str],
        semantic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Évalue la cohérence thématique entre les arguments.
        
        Args:
            arguments (List[str]): Liste des arguments
            semantic_analysis (Dict[str, Any]): Analyse sémantique des arguments
            
        Returns:
            Dict[str, Any]: Évaluation de la cohérence thématique
        """
        # Simuler l'évaluation de la cohérence thématique
        return {
            "score": 0.7,
            "level": "Bon",
            "criteria_scores": {
                "unite_thematique": 0.8,
                "progression_thematique": 0.7,
                "pertinence_thematique": 0.6,
                "equilibre_thematique": 0.7
            },
            "specific_issues": [],
            "importance": self.coherence_types["thématique"]["importance"]
        }
    
    def _evaluate_structural_coherence(
        self,
        arguments: List[str],
        semantic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Évalue la cohérence structurelle entre les arguments.
        
        Args:
            arguments (List[str]): Liste des arguments
            semantic_analysis (Dict[str, Any]): Analyse sémantique des arguments
            
        Returns:
            Dict[str, Any]: Évaluation de la cohérence structurelle
        """
        # Simuler l'évaluation de la cohérence structurelle
        return {
            "score": 0.6,
            "level": "Moyen",
            "criteria_scores": {
                "organisation_hierarchique": 0.5,
                "sequence_logique": 0.7,
                "equilibre_structurel": 0.6,
                "transitions_arguments": 0.6
            },
            "specific_issues": [],
            "importance": self.coherence_types["structurelle"]["importance"]
        }
    
    def _evaluate_rhetorical_coherence(
        self,
        arguments: List[str],
        semantic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Évalue la cohérence rhétorique entre les arguments.
        
        Args:
            arguments (List[str]): Liste des arguments
            semantic_analysis (Dict[str, Any]): Analyse sémantique des arguments
            
        Returns:
            Dict[str, Any]: Évaluation de la cohérence rhétorique
        """
        # Simuler l'évaluation de la cohérence rhétorique
        return {
            "score": 0.7,
            "level": "Bon",
            "criteria_scores": {
                "coherence_style": 0.8,
                "coherence_ton": 0.7,
                "coherence_appels": 0.6,
                "coherence_figures": 0.7
            },
            "specific_issues": [],
            "importance": self.coherence_types["rhétorique"]["importance"]
        }
    
    def _evaluate_epistemic_coherence(
        self,
        arguments: List[str],
        semantic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Évalue la cohérence épistémique entre les arguments.
        
        Args:
            arguments (List[str]): Liste des arguments
            semantic_analysis (Dict[str, Any]): Analyse sémantique des arguments
            
        Returns:
            Dict[str, Any]: Évaluation de la cohérence épistémique
        """
        # Simuler l'évaluation de la cohérence épistémique
        return {
            "score": 0.6,
            "level": "Moyen",
            "criteria_scores": {
                "coherence_standards_preuve": 0.6,
                "coherence_sources": 0.5,
                "coherence_methodes": 0.7,
                "coherence_certitude": 0.6
            },
            "specific_issues": [],
            "importance": self.coherence_types["épistémique"]["importance"]
        }
    
    def _calculate_overall_coherence(
        self,
        coherence_evaluations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calcule la cohérence globale à partir des évaluations de cohérence.
        
        Args:
            coherence_evaluations (Dict[str, Dict[str, Any]]): Évaluations de cohérence
            
        Returns:
            Dict[str, Any]: Évaluation de la cohérence globale
        """
        # Calculer le score global pondéré
        weighted_scores = []
        
        for coherence_type, evaluation in coherence_evaluations.items():
            importance = self.coherence_types[coherence_type]["importance"]
            score = evaluation["score"]
            weighted_scores.append(score * importance)
        
        overall_score = sum(weighted_scores) / sum(importance for importance in [self.coherence_types[ct]["importance"] for ct in coherence_evaluations])
        
        # Déterminer le niveau de cohérence global
        if overall_score > 0.8:
            coherence_level = "Excellent"
        elif overall_score > 0.6:
            coherence_level = "Bon"
        elif overall_score > 0.4:
            coherence_level = "Moyen"
        elif overall_score > 0.2:
            coherence_level = "Faible"
        else:
            coherence_level = "Très faible"
        
        # Identifier les forces et faiblesses
        strengths = []
        weaknesses = []
        
        for coherence_type, evaluation in coherence_evaluations.items():
            if evaluation["score"] > 0.7:
                strengths.append(f"Bonne cohérence {coherence_type} ({evaluation['score']:.2f})")
            elif evaluation["score"] < 0.5:
                weaknesses.append(f"Faible cohérence {coherence_type} ({evaluation['score']:.2f})")
        
        return {
            "score": overall_score,
            "level": coherence_level,
            "strengths": strengths,
            "weaknesses": weaknesses
        }
    
    def _generate_recommendations(
        self,
        arguments: List[str],
        coherence_evaluations: Dict[str, Dict[str, Any]],
        overall_coherence: Dict[str, Any]
    ) -> List[str]:
        """
        Génère des recommandations pour améliorer la cohérence.
        
        Args:
            arguments (List[str]): Liste des arguments
            coherence_evaluations (Dict[str, Dict[str, Any]]): Évaluations de cohérence
            overall_coherence (Dict[str, Any]): Évaluation de la cohérence globale
            
        Returns:
            List[str]: Liste de recommandations
        """
        # Générer des recommandations générales
        recommendations = []
        
        # Recommandations basées sur le niveau de cohérence global
        if overall_coherence["level"] == "Excellent":
            recommendations.append("La cohérence globale des arguments est excellente. Maintenir cette qualité dans les futurs développements.")
        elif overall_coherence["level"] == "Bon":
            recommendations.append("La cohérence globale des arguments est bonne. Quelques améliorations mineures pourraient être apportées.")
        elif overall_coherence["level"] == "Moyen":
            recommendations.append("La cohérence globale des arguments est moyenne. Des améliorations significatives sont recommandées.")
        elif overall_coherence["level"] == "Faible":
            recommendations.append("La cohérence globale des arguments est faible. Une restructuration importante est nécessaire.")
        else:
            recommendations.append("La cohérence globale des arguments est très faible. Une refonte complète est recommandée.")
        
        # Recommandations basées sur les faiblesses
        for weakness in overall_coherence.get("weaknesses", []):
            if "logique" in weakness.lower():
                recommendations.append("Renforcer les liens logiques entre les arguments et éliminer les contradictions.")
            elif "thématique" in weakness.lower():
                recommendations.append("Améliorer l'unité thématique et la progression des thèmes entre les arguments.")
            elif "structurelle" in weakness.lower():
                recommendations.append("Restructurer les arguments pour améliorer l'organisation hiérarchique et les transitions.")
            elif "rhétorique" in weakness.lower():
                recommendations.append("Harmoniser le style et le ton entre les arguments pour une meilleure cohérence rhétorique.")
            elif "épistémique" in weakness.lower():
                recommendations.append("Uniformiser les standards de preuve et les sources utilisées dans les arguments.")
        
        # Recommandations basées sur le nombre d'arguments
        if len(arguments) < 3:
            recommendations.append("Développer davantage l'argumentation en ajoutant des arguments supplémentaires pour renforcer la position.")
        elif len(arguments) > 7:
            recommendations.append("Considérer la consolidation de certains arguments pour une structure plus concise et percutante.")
        
        return recommendations


# Test de la classe si exécutée directement
if __name__ == "__main__":
    # Exemple d'arguments
    arguments = [
        "La technologie améliore notre productivité au travail grâce à l'automatisation des tâches répétitives.",
        "Les outils numériques facilitent la communication et la collaboration entre les équipes distantes.",
        "Cependant, la surcharge d'informations peut réduire notre capacité de concentration.",
        "De plus, la dépendance excessive à la technologie peut créer des vulnérabilités en cas de panne."
    ]
    
    # Créer l'évaluateur
    evaluator = ArgumentCoherenceEvaluator()
    
    # Évaluer la cohérence
    results = evaluator.evaluate_coherence(arguments, "technologie au travail")
    
    # Afficher les résultats
    print(json.dumps(results, indent=2, ensure_ascii=False))
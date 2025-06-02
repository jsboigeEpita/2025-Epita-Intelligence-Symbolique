#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil d'analyse des résultats d'une analyse rhétorique amélioré.

Ce module fournit des fonctionnalités avancées pour analyser les résultats d'une analyse
rhétorique, extraire des insights plus profonds et générer des résumés plus détaillés.
"""

import os
import sys
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer l'analyseur de résultats rhétoriques de base
from argumentation_analysis.agents.tools.analysis.rhetorical_result_analyzer import RhetoricalResultAnalyzer as BaseAnalyzer

# Importer les analyseurs améliorés
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("EnhancedRhetoricalResultAnalyzer")


class EnhancedRhetoricalResultAnalyzer(BaseAnalyzer):
    """
    Outil amélioré pour l'analyse des résultats d'une analyse rhétorique.
    
    Cette version améliorée intègre l'analyse de persuasion, l'évaluation de la qualité
    argumentative, et l'analyse des stratégies rhétoriques pour une analyse plus
    complète et nuancée des résultats rhétoriques.
    """
    
    def __init__(self):
        """
        Initialise l'analyseur de résultats rhétoriques amélioré.
        """
        super().__init__()
        self.logger = logger
        
        # Initialiser les analyseurs améliorés
        self.complex_fallacy_analyzer = EnhancedComplexFallacyAnalyzer()
        self.severity_evaluator = EnhancedFallacySeverityEvaluator()
        
        # Historique des analyses pour l'apprentissage continu
        self.analysis_history = []
        
        self.logger.info("Analyseur de résultats rhétoriques amélioré initialisé.")
    
    def analyze_rhetorical_results(self, results: Dict[str, Any], context: str = "général") -> Dict[str, Any]:
        """
        Analyse les résultats d'une analyse rhétorique de manière avancée.
        
        Cette méthode améliorée analyse les résultats d'une analyse rhétorique pour
        en extraire des insights plus profonds, évaluer la qualité argumentative,
        et analyser les stratégies rhétoriques utilisées.
        
        Args:
            results: Résultats de l'analyse rhétorique
            context: Contexte de l'analyse (optionnel)
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse avancée
        """
        self.logger.info(f"Analyse avancée des résultats rhétoriques dans le contexte: {context}")
        
        # Analyser la distribution des sophismes
        fallacy_analysis = self._analyze_fallacy_distribution(results)
        
        # Analyser la qualité de la cohérence
        coherence_analysis = self._analyze_coherence_quality(results)
        
        # Analyser l'efficacité persuasive
        persuasion_analysis = self._analyze_persuasion_effectiveness(results, context)
        
        # Calculer la qualité rhétorique globale
        rhetorical_quality, rhetorical_quality_level = self._calculate_overall_rhetorical_quality(
            fallacy_analysis, coherence_analysis, persuasion_analysis
        )
        
        # Identifier les forces et les faiblesses
        strengths, weaknesses = self._identify_strengths_and_weaknesses(
            fallacy_analysis, coherence_analysis, persuasion_analysis
        )
        
        # Générer des recommandations
        recommendations = self._generate_recommendations(
            fallacy_analysis, coherence_analysis, persuasion_analysis, context
        )
        
        # Préparer les résultats
        analysis_results = {
            "overall_analysis": {
                "rhetorical_quality": rhetorical_quality,
                "rhetorical_quality_level": rhetorical_quality_level,
                "main_strengths": strengths,
                "main_weaknesses": weaknesses,
                "context_relevance": self._evaluate_context_relevance(results, context)
            },
            "fallacy_analysis": fallacy_analysis,
            "coherence_analysis": coherence_analysis,
            "persuasion_analysis": persuasion_analysis,
            "recommendations": recommendations,
            "context": context,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Ajouter l'analyse à l'historique
        self.analysis_history.append({
            "type": "rhetorical_results_analysis",
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        return analysis_results
    
    def _analyze_fallacy_distribution(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse la distribution des sophismes dans les résultats.
        
        Args:
            results: Résultats de l'analyse rhétorique
            
        Returns:
            Dictionnaire contenant l'analyse de la distribution des sophismes
        """
        # Extraire les informations pertinentes
        complex_fallacy_analysis = results.get("complex_fallacy_analysis", {})
        contextual_fallacy_analysis = results.get("contextual_fallacy_analysis", {})
        
        individual_fallacies_count = complex_fallacy_analysis.get("individual_fallacies_count", 0)
        basic_combinations = complex_fallacy_analysis.get("basic_combinations", [])
        advanced_combinations = complex_fallacy_analysis.get("advanced_combinations", [])
        
        contextual_fallacies = contextual_fallacy_analysis.get("contextual_fallacies", [])
        
        # Calculer le nombre total de sophismes
        total_fallacies = individual_fallacies_count + len(basic_combinations) + len(advanced_combinations)
        
        # Identifier les types de sophismes et leur distribution
        fallacy_types = Counter()
        for fallacy in contextual_fallacies:
            fallacy_type = fallacy.get("fallacy_type", "Type inconnu")
            fallacy_types[fallacy_type] += 1
        
        # Identifier les sophismes les plus courants
        most_common_fallacies = [fallacy_type for fallacy_type, _ in fallacy_types.most_common(3)]
        
        # Identifier les sophismes les plus graves
        fallacies_by_severity = sorted(
            contextual_fallacies,
            key=lambda f: f.get("confidence", 0.5),
            reverse=True
        )
        most_severe_fallacies = [
            fallacy.get("fallacy_type", "Type inconnu")
            for fallacy in fallacies_by_severity[:3]
        ]
        
        # Calculer la gravité globale
        composite_severity = complex_fallacy_analysis.get("composite_severity", {})
        overall_severity = composite_severity.get("adjusted_severity", 0.5)
        severity_level = composite_severity.get("severity_level", "Modéré")
        
        # Préparer l'analyse
        fallacy_analysis = {
            "total_fallacies": total_fallacies,
            "fallacy_types_distribution": dict(fallacy_types),
            "most_common_fallacies": most_common_fallacies,
            "most_severe_fallacies": most_severe_fallacies,
            "composite_fallacies": len(basic_combinations) + len(advanced_combinations),
            "overall_severity": overall_severity,
            "severity_level": severity_level
        }
        
        return fallacy_analysis
    
    def _analyze_coherence_quality(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse la qualité de la cohérence argumentative.
        
        Args:
            results: Résultats de l'analyse rhétorique
            
        Returns:
            Dictionnaire contenant l'analyse de la qualité de la cohérence
        """
        # Extraire les informations pertinentes
        argument_coherence_evaluation = results.get("argument_coherence_evaluation", {})
        
        # Extraire les scores de cohérence
        overall_coherence = argument_coherence_evaluation.get("coherence_score", 0.5)
        coherence_level = argument_coherence_evaluation.get("coherence_level", "Modéré")
        
        # Extraire les clusters thématiques
        thematic_clusters = argument_coherence_evaluation.get("thematic_clusters", [])
        thematic_coherence = 0.7 if len(thematic_clusters) <= 2 else 0.5  # Estimation simplifiée
        
        # Extraire les flux logiques
        logical_flows = argument_coherence_evaluation.get("logical_flows", [])
        logical_coherence = 0.6 if logical_flows else 0.3  # Estimation simplifiée
        
        # Évaluer la qualité de la structure
        structure_quality = (thematic_coherence + logical_coherence) / 2
        
        # Identifier les principaux problèmes de cohérence
        main_coherence_issues = []
        
        if thematic_coherence < 0.6:
            main_coherence_issues.append("Thematic shifts")
        
        if logical_coherence < 0.6:
            main_coherence_issues.append("Logical gaps")
        
        if len(thematic_clusters) > 2:
            main_coherence_issues.append("Multiple unrelated themes")
        
        # Préparer l'analyse
        coherence_analysis = {
            "overall_coherence": overall_coherence,
            "coherence_level": coherence_level,
            "thematic_coherence": thematic_coherence,
            "logical_coherence": logical_coherence,
            "structure_quality": structure_quality,
            "main_coherence_issues": main_coherence_issues
        }
        
        return coherence_analysis
    
    def _analyze_persuasion_effectiveness(self, results: Dict[str, Any], context: str) -> Dict[str, Any]:
        """
        Analyse l'efficacité persuasive des arguments.
        
        Args:
            results: Résultats de l'analyse rhétorique
            context: Contexte de l'analyse
            
        Returns:
            Dictionnaire contenant l'analyse de l'efficacité persuasive
        """
        # Extraire les informations pertinentes
        contextual_fallacy_analysis = results.get("contextual_fallacy_analysis", {})
        contextual_fallacies = contextual_fallacy_analysis.get("contextual_fallacies", [])
        context_analysis = contextual_fallacy_analysis.get("context_analysis", {})
        
        # Identifier les appels rhétoriques (ethos, pathos, logos)
        rhetorical_appeals = self._identify_rhetorical_appeals(contextual_fallacy_analysis)
        
        # Calculer les scores d'appel
        emotional_appeal = rhetorical_appeals.get("pathos", 0.0)
        logical_appeal = rhetorical_appeals.get("logos", 0.0)
        credibility_appeal = rhetorical_appeals.get("ethos", 0.0)
        
        # Évaluer l'adéquation au contexte
        context_type = context_analysis.get("context_type", "général")
        context_appropriateness = self._evaluate_context_appropriateness(
            rhetorical_appeals, context_type
        )
        
        # Évaluer l'alignement avec l'audience
        audience_characteristics = context_analysis.get("audience_characteristics", ["généraliste"])
        audience_alignment = self._evaluate_audience_alignment(
            rhetorical_appeals, audience_characteristics
        )
        
        # Calculer le score de persuasion global
        persuasion_score = (
            emotional_appeal * 0.3 +
            logical_appeal * 0.3 +
            credibility_appeal * 0.2 +
            context_appropriateness * 0.1 +
            audience_alignment * 0.1
        )
        
        # Déterminer le niveau de persuasion
        if persuasion_score > 0.8:
            persuasion_level = "Excellent"
        elif persuasion_score > 0.6:
            persuasion_level = "Élevé"
        elif persuasion_score > 0.4:
            persuasion_level = "Modéré"
        elif persuasion_score > 0.2:
            persuasion_level = "Faible"
        else:
            persuasion_level = "Très faible"
        
        # Préparer l'analyse
        persuasion_analysis = {
            "persuasion_score": persuasion_score,
            "persuasion_level": persuasion_level,
            "emotional_appeal": emotional_appeal,
            "logical_appeal": logical_appeal,
            "credibility_appeal": credibility_appeal,
            "context_appropriateness": context_appropriateness,
            "audience_alignment": audience_alignment
        }
        
        return persuasion_analysis
    
    def _evaluate_context_appropriateness(
        self,
        rhetorical_appeals: Dict[str, float],
        context_type: str
    ) -> float:
        """
        Évalue l'adéquation des appels rhétoriques au contexte.
        
        Args:
            rhetorical_appeals: Appels rhétoriques identifiés
            context_type: Type de contexte
            
        Returns:
            Score d'adéquation au contexte (0.0 à 1.0)
        """
        # Définir les appels rhétoriques appropriés selon le contexte
        context_appeal_weights = {
            "politique": {"ethos": 0.3, "pathos": 0.4, "logos": 0.3},
            "scientifique": {"ethos": 0.3, "pathos": 0.1, "logos": 0.6},
            "commercial": {"ethos": 0.3, "pathos": 0.5, "logos": 0.2},
            "juridique": {"ethos": 0.4, "pathos": 0.2, "logos": 0.4},
            "académique": {"ethos": 0.3, "pathos": 0.1, "logos": 0.6},
            "général": {"ethos": 0.33, "pathos": 0.33, "logos": 0.34}
        }
        
        # Utiliser les poids appropriés ou les poids par défaut
        weights = context_appeal_weights.get(context_type, context_appeal_weights["général"])
        
        # Calculer le score d'adéquation
        appropriateness_score = sum(
            appeal_score * weights.get(appeal, 0.33)
            for appeal, appeal_score in rhetorical_appeals.items()
        )
        
        return min(1.0, appropriateness_score)
    
    def _evaluate_audience_alignment(
        self,
        rhetorical_appeals: Dict[str, float],
        audience_characteristics: List[str]
    ) -> float:
        """
        Évalue l'alignement des appels rhétoriques avec l'audience.
        
        Args:
            rhetorical_appeals: Appels rhétoriques identifiés
            audience_characteristics: Caractéristiques de l'audience
            
        Returns:
            Score d'alignement avec l'audience (0.0 à 1.0)
        """
        # Définir les appels rhétoriques appropriés selon l'audience
        audience_appeal_weights = {
            "généraliste": {"ethos": 0.3, "pathos": 0.4, "logos": 0.3},
            "expert": {"ethos": 0.3, "pathos": 0.1, "logos": 0.6},
            "académique": {"ethos": 0.3, "pathos": 0.1, "logos": 0.6},
            "professionnel": {"ethos": 0.4, "pathos": 0.2, "logos": 0.4},
            "jeune": {"ethos": 0.2, "pathos": 0.5, "logos": 0.3},
            "senior": {"ethos": 0.4, "pathos": 0.3, "logos": 0.3}
        }
        
        # Calculer les poids moyens pour l'audience
        weights = {"ethos": 0.33, "pathos": 0.33, "logos": 0.34}  # Valeurs par défaut
        
        if audience_characteristics:
            for characteristic in audience_characteristics:
                if characteristic in audience_appeal_weights:
                    for appeal, weight in audience_appeal_weights[characteristic].items():
                        weights[appeal] = (weights[appeal] + weight) / 2
        
        # Calculer le score d'alignement
        alignment_score = sum(
            appeal_score * weights.get(appeal, 0.33)
            for appeal, appeal_score in rhetorical_appeals.items()
        )
        
        return min(1.0, alignment_score)
    
    def _calculate_overall_rhetorical_quality(
        self,
        fallacy_analysis: Dict[str, Any],
        coherence_analysis: Dict[str, Any],
        persuasion_analysis: Dict[str, Any]
    ) -> Tuple[float, str]:
        """
        Calcule la qualité rhétorique globale.
        
        Args:
            fallacy_analysis: Analyse des sophismes
            coherence_analysis: Analyse de la cohérence
            persuasion_analysis: Analyse de la persuasion
            
        Returns:
            Tuple contenant le score de qualité rhétorique et le niveau de qualité
        """
        # Extraire les scores pertinents
        fallacy_severity = fallacy_analysis.get("overall_severity", 0.5)
        coherence_score = coherence_analysis.get("overall_coherence", 0.5)
        persuasion_score = persuasion_analysis.get("persuasion_score", 0.5)
        
        # Inverser le score de gravité des sophismes (plus la gravité est élevée, moins la qualité est bonne)
        fallacy_quality = 1.0 - fallacy_severity
        
        # Calculer le score de qualité rhétorique global
        rhetorical_quality = (fallacy_quality * 0.3) + (coherence_score * 0.3) + (persuasion_score * 0.4)
        
        # Déterminer le niveau de qualité
        if rhetorical_quality > 0.8:
            quality_level = "Excellent"
        elif rhetorical_quality > 0.6:
            quality_level = "Bon"
        elif rhetorical_quality > 0.4:
            quality_level = "Modéré"
        elif rhetorical_quality > 0.2:
            quality_level = "Faible"
        else:
            quality_level = "Très faible"
        
        return rhetorical_quality, quality_level
    
    def _identify_strengths_and_weaknesses(
        self,
        fallacy_analysis: Dict[str, Any],
        coherence_analysis: Dict[str, Any],
        persuasion_analysis: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """
        Identifie les forces et les faiblesses de l'argumentation.
        
        Args:
            fallacy_analysis: Analyse des sophismes
            coherence_analysis: Analyse de la cohérence
            persuasion_analysis: Analyse de la persuasion
            
        Returns:
            Tuple contenant les listes des forces et des faiblesses
        """
        strengths = []
        weaknesses = []
        
        # Forces et faiblesses basées sur les sophismes
        if fallacy_analysis.get("total_fallacies", 0) == 0:
            strengths.append("Absence de sophismes détectés")
        elif fallacy_analysis.get("overall_severity", 0.5) < 0.4:
            strengths.append("Utilisation modérée de sophismes")
        elif fallacy_analysis.get("overall_severity", 0.5) > 0.7:
            weaknesses.append("Utilisation excessive de sophismes graves")
        
        # Forces et faiblesses basées sur la cohérence
        if coherence_analysis.get("overall_coherence", 0.5) > 0.7:
            strengths.append("Forte cohérence argumentative")
        elif coherence_analysis.get("overall_coherence", 0.5) < 0.4:
            weaknesses.append("Faible cohérence argumentative")
        
        if coherence_analysis.get("thematic_coherence", 0.5) > 0.7:
            strengths.append("Forte cohérence thématique")
        elif coherence_analysis.get("thematic_coherence", 0.5) < 0.4:
            weaknesses.append("Faible cohérence thématique")
        
        if coherence_analysis.get("logical_coherence", 0.5) > 0.7:
            strengths.append("Forte cohérence logique")
        elif coherence_analysis.get("logical_coherence", 0.5) < 0.4:
            weaknesses.append("Faible cohérence logique")
        
        # Forces et faiblesses basées sur la persuasion
        if persuasion_analysis.get("persuasion_score", 0.5) > 0.7:
            strengths.append("Argumentation persuasive")
        elif persuasion_analysis.get("persuasion_score", 0.5) < 0.4:
            weaknesses.append("Argumentation peu persuasive")
        
        if persuasion_analysis.get("emotional_appeal", 0.5) > 0.7:
            strengths.append("Fort appel émotionnel")
        
        if persuasion_analysis.get("logical_appeal", 0.5) > 0.7:
            strengths.append("Fort appel logique")
        
        if persuasion_analysis.get("credibility_appeal", 0.5) > 0.7:
            strengths.append("Fort appel à la crédibilité")
        
        return strengths, weaknesses
    
    def _evaluate_context_relevance(self, results: Dict[str, Any], context: str) -> float:
        """
        Évalue la pertinence de l'argumentation par rapport au contexte.
        
        Args:
            results: Résultats de l'analyse rhétorique
            context: Contexte de l'analyse
            
        Returns:
            Score de pertinence par rapport au contexte (0.0 à 1.0)
        """
        # Extraire les informations pertinentes
        contextual_fallacy_analysis = results.get("contextual_fallacy_analysis", {})
        context_analysis = contextual_fallacy_analysis.get("context_analysis", {})
        
        # Vérifier si le contexte détecté correspond au contexte attendu
        detected_context = context_analysis.get("context_type", "général")
        context_match = 1.0 if detected_context in context else 0.7
        
        # Calculer la pertinence contextuelle
        contextual_relevance = context_analysis.get("confidence", 0.5) * context_match
        
        return min(1.0, contextual_relevance)
    
    def _analyze_persuasion(self, results: Dict[str, Any], context: str) -> Dict[str, Any]:
        """
        Analyse les stratégies de persuasion utilisées.
        
        Args:
            results: Résultats de l'analyse rhétorique
            context: Contexte de l'analyse
            
        Returns:
            Dictionnaire contenant l'analyse des stratégies de persuasion
        """
        # Extraire les informations pertinentes
        complex_fallacy_analysis = results.get("complex_fallacy_analysis", {})
        contextual_fallacy_analysis = results.get("contextual_fallacy_analysis", {})
        
        # Identifier les stratégies de persuasion
        persuasion_strategies = self._identify_persuasion_strategies(contextual_fallacy_analysis)
        
        # Identifier les appels rhétoriques (ethos, pathos, logos)
        rhetorical_appeals = self._identify_rhetorical_appeals(contextual_fallacy_analysis)
        
        # Préparer l'analyse
        persuasion_analysis = {
            "persuasion_strategies": persuasion_strategies,
            "rhetorical_appeals": rhetorical_appeals,
            "dominant_appeal": max(rhetorical_appeals, key=rhetorical_appeals.get) if rhetorical_appeals else None
        }
        
        return persuasion_analysis
    
    def _identify_persuasion_strategies(self, contextual_fallacy_analysis: Dict[str, Any]) -> Dict[str, float]:
        """
        Identifie les stratégies de persuasion utilisées.
        
        Args:
            contextual_fallacy_analysis: Analyse des sophismes contextuels
            
        Returns:
            Dictionnaire des stratégies de persuasion avec leur score
        """
        # Définir les stratégies de persuasion et les sophismes associés
        strategy_fallacy_mapping = {
            "Appel à l'autorité": ["Appel à l'autorité", "Appel à la tradition", "Appel à la nouveauté"],
            "Appel à l'émotion": ["Appel à la peur", "Appel à la pitié", "Appel à la flatterie"],
            "Fausse dichotomie": ["Faux dilemme", "Pente glissante", "Homme de paille"],
            "Généralisation abusive": ["Généralisation hâtive", "Sophisme du vrai écossais", "Anecdote"],
            "Attaque personnelle": ["Ad hominem", "Tu quoque", "Empoisonner le puits"]
        }
        
        # Extraire les sophismes identifiés
        contextual_fallacies = contextual_fallacy_analysis.get("contextual_fallacies", [])
        
        # Compter les occurrences de chaque stratégie
        strategy_counts = defaultdict(int)
        
        for fallacy in contextual_fallacies:
            fallacy_type = fallacy.get("fallacy_type", "")
            confidence = fallacy.get("confidence", 0.5)
            
            for strategy, fallacy_types in strategy_fallacy_mapping.items():
                if fallacy_type in fallacy_types:
                    strategy_counts[strategy] += confidence
        
        # Normaliser les scores
        total_score = sum(strategy_counts.values())
        if total_score > 0:
            strategies = {strategy: score / total_score for strategy, score in strategy_counts.items()}
        else:
            strategies = {}
        
        return strategies
    
    def _identify_rhetorical_appeals(self, contextual_fallacy_analysis: Dict[str, Any]) -> Dict[str, float]:
        """
        Identifie les appels rhétoriques (ethos, pathos, logos) utilisés.
        
        Args:
            contextual_fallacy_analysis: Analyse des sophismes contextuels
            
        Returns:
            Dictionnaire des appels rhétoriques avec leur score
        """
        # Définir les appels rhétoriques et les sophismes associés
        appeal_fallacy_mapping = {
            "ethos": ["Appel à l'autorité", "Appel à la tradition", "Ad hominem"],
            "pathos": ["Appel à la peur", "Appel à la pitié", "Appel à la flatterie", "Appel à l'émotion"],
            "logos": ["Faux dilemme", "Pente glissante", "Post hoc ergo propter hoc", "Généralisation hâtive"]
        }
        
        # Extraire les sophismes identifiés
        contextual_fallacies = contextual_fallacy_analysis.get("contextual_fallacies", [])
        
        # Initialiser les scores
        appeals = {
            "ethos": 0.0,
            "pathos": 0.0,
            "logos": 0.0
        }
        
        # Compter les occurrences de chaque appel
        for fallacy in contextual_fallacies:
            fallacy_type = fallacy.get("fallacy_type", "")
            confidence = fallacy.get("confidence", 0.5)
            
            for appeal, fallacy_types in appeal_fallacy_mapping.items():
                if fallacy_type in fallacy_types:
                    appeals[appeal] += confidence
        
        # Normaliser les scores
        total_score = sum(appeals.values())
        if total_score > 0:
            appeals = {appeal: score / total_score for appeal, score in appeals.items()}
        
        return appeals
    
    def _determine_quality_level(
        self,
        fallacy_analysis: Dict[str, Any],
        coherence_analysis: Dict[str, Any],
        persuasion_analysis: Dict[str, Any]
    ) -> str:
        """
        Détermine le niveau de qualité de l'analyse rhétorique.
        
        Args:
            fallacy_analysis: Analyse des sophismes
            coherence_analysis: Analyse de la cohérence
            persuasion_analysis: Analyse de la persuasion
            
        Returns:
            Niveau de qualité (Excellent, Bon, Moyen, Faible)
        """
        # Calculer un score global
        coherence_score = coherence_analysis.get("overall_coherence_score", 0.5)
        
        # Calculer un score de sophistication des sophismes
        total_fallacies = fallacy_analysis.get("total_fallacies", 0)
        advanced_combinations_count = fallacy_analysis.get("advanced_combinations_count", 0)
        sophistication_score = advanced_combinations_count / max(1, total_fallacies)
        
        # Calculer un score global
        overall_score = (coherence_score + sophistication_score) / 2
        
        # Déterminer le niveau de qualité
        if overall_score > 0.8:
            return "Excellent"
        elif overall_score > 0.6:
            return "Bon"
        elif overall_score > 0.4:
            return "Moyen"
        else:
            return "Faible"
    
    def _generate_recommendations(
        self,
        fallacy_analysis: Dict[str, Any],
        coherence_analysis: Dict[str, Any],
        persuasion_analysis: Dict[str, Any],
        context: str
    ) -> Dict[str, List[str]]:
        """
        Génère des recommandations pour améliorer l'argumentation.
        
        Args:
            fallacy_analysis: Analyse des sophismes
            coherence_analysis: Analyse de la cohérence
            persuasion_analysis: Analyse de la persuasion
            
        Returns:
            Dictionnaire contenant les recommandations par catégorie
        """
        # Initialiser les listes de recommandations par catégorie
        general_recommendations = []
        fallacy_recommendations = []
        coherence_recommendations = []
        persuasion_recommendations = []
        context_specific_recommendations = []
        
        # Recommandations basées sur les sophismes
        if fallacy_analysis.get("total_fallacies", 0) > 5:
            fallacy_recommendations.append("Réduire le nombre de sophismes utilisés")
        
        if fallacy_analysis.get("overall_severity", 0.5) > 0.7:
            fallacy_recommendations.append("Éviter les sophismes les plus graves")
            
            # Ajouter des recommandations spécifiques pour les sophismes les plus courants
            most_common_fallacies = fallacy_analysis.get("most_common_fallacies", [])
            for fallacy in most_common_fallacies:
                if fallacy == "Appel à l'émotion":
                    fallacy_recommendations.append("Réduire les appels émotionnels excessifs")
                elif fallacy == "Ad hominem":
                    fallacy_recommendations.append("Éviter les attaques personnelles")
                elif fallacy == "Appel à l'autorité":
                    fallacy_recommendations.append("Citer des sources plus crédibles et diversifiées")
        
        if fallacy_analysis.get("contextual_ratio", 0) < 0.3:
            fallacy_recommendations.append("Adapter les sophismes au contexte spécifique de l'argumentation")
        
        # Recommandations basées sur la cohérence
        if coherence_analysis.get("overall_coherence", 0.5) < 0.6:
            coherence_recommendations.append("Améliorer la cohérence globale de l'argumentation")
        
        if coherence_analysis.get("contradiction_count", 0) > 0:
            coherence_recommendations.append(f"Résoudre les {coherence_analysis.get('contradiction_count')} contradictions identifiées")
        
        main_coherence_issues = coherence_analysis.get("main_coherence_issues", [])
        for issue in main_coherence_issues:
            if issue == "Thematic shifts":
                coherence_recommendations.append("Maintenir une cohérence thématique plus forte")
            elif issue == "Logical gaps":
                coherence_recommendations.append("Combler les lacunes logiques entre les arguments")
            elif issue == "Multiple unrelated themes":
                coherence_recommendations.append("Réduire le nombre de thèmes non liés")
        
        # Recommandations basées sur la persuasion
        if persuasion_analysis.get("persuasion_score", 0.5) < 0.6:
            persuasion_recommendations.append("Renforcer l'efficacité persuasive globale")
        
        # Équilibrer les appels rhétoriques
        rhetorical_appeals = persuasion_analysis.get("rhetorical_appeals", {})
        if rhetorical_appeals:
            min_appeal = min(rhetorical_appeals, key=rhetorical_appeals.get)
            if rhetorical_appeals[min_appeal] < 0.4:
                if min_appeal == "ethos":
                    persuasion_recommendations.append("Renforcer l'appel à la crédibilité")
                elif min_appeal == "pathos":
                    persuasion_recommendations.append("Renforcer l'appel émotionnel")
                elif min_appeal == "logos":
                    persuasion_recommendations.append("Renforcer l'appel logique avec des preuves et des raisonnements solides")
        
        # Recommandations spécifiques au contexte
        if context == "politique":
            if persuasion_analysis.get("emotional_appeal", 0.5) > 0.8 and persuasion_analysis.get("logical_appeal", 0.5) < 0.4:
                context_specific_recommendations.append("Équilibrer les appels émotionnels avec des arguments logiques")
        elif context == "scientifique":
            if persuasion_analysis.get("logical_appeal", 0.5) < 0.6:
                context_specific_recommendations.append("Renforcer la rigueur logique et les preuves empiriques")
        elif context == "commercial":
            if persuasion_analysis.get("credibility_appeal", 0.5) < 0.5:
                context_specific_recommendations.append("Renforcer la crédibilité de la marque ou du produit")
        
        # Ajouter des recommandations générales basées sur l'ensemble des analyses
        if fallacy_analysis.get("overall_severity", 0.5) > 0.6 and coherence_analysis.get("overall_coherence", 0.5) < 0.6:
            general_recommendations.append("Restructurer l'argumentation pour réduire les sophismes et améliorer la cohérence")
        elif persuasion_analysis.get("persuasion_score", 0.5) < 0.5:
            general_recommendations.append("Revoir la stratégie persuasive globale")
        
        # Regrouper toutes les recommandations
        recommendations = {
            "general_recommendations": general_recommendations,
            "fallacy_recommendations": fallacy_recommendations,
            "coherence_recommendations": coherence_recommendations,
            "persuasion_recommendations": persuasion_recommendations,
            "context_specific_recommendations": context_specific_recommendations
        }
        
        return recommendations
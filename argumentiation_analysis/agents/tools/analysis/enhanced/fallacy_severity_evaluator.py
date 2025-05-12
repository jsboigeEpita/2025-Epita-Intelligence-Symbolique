#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Évaluateur amélioré de la gravité des sophismes.

Ce module fournit une classe pour évaluer la gravité des sophismes
en tenant compte du contexte, du public cible et du domaine.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("EnhancedFallacySeverityEvaluator")


class EnhancedFallacySeverityEvaluator:
    """
    Évaluateur amélioré de la gravité des sophismes.
    
    Cette classe évalue la gravité des sophismes en tenant compte du contexte,
    du public cible et du domaine.
    """
    
    def __init__(self):
        """Initialise l'évaluateur de gravité des sophismes."""
        self.logger = logger
        self.logger.info("Évaluateur de gravité des sophismes initialisé.")
        
        # Base de gravité pour chaque type de sophisme
        self.fallacy_severity_base = {
            "Appel à l'autorité": 0.6,
            "Appel à la popularité": 0.5,
            "Appel à la tradition": 0.4,
            "Appel à la nouveauté": 0.4,
            "Appel à l'ignorance": 0.7,
            "Appel à la peur": 0.8,
            "Appel à la pitié": 0.6,
            "Appel à la flatterie": 0.5,
            "Faux dilemme": 0.7,
            "Pente glissante": 0.6,
            "Homme de paille": 0.7,
            "Ad hominem": 0.8,
            "Tu quoque": 0.6,
            "Généralisation hâtive": 0.6,
            "Post hoc ergo propter hoc": 0.5
        }
        
        # Modificateurs de gravité en fonction du contexte
        self.context_severity_modifiers = {
            "académique": 0.2,
            "scientifique": 0.3,
            "politique": 0.2,
            "juridique": 0.3,
            "médical": 0.3,
            "commercial": 0.1,
            "journalistique": 0.2,
            "éducatif": 0.2,
            "religieux": 0.1,
            "personnel": -0.1,
            "divertissement": -0.2,
            "général": 0.0
        }
        
        # Modificateurs de gravité en fonction du public cible
        self.audience_severity_modifiers = {
            "experts": 0.2,
            "professionnels": 0.1,
            "étudiants": 0.1,
            "grand public": 0.0,
            "enfants": 0.2,
            "personnes âgées": 0.1,
            "personnes vulnérables": 0.2,
            "général": 0.0
        }
        
        # Modificateurs de gravité en fonction du domaine
        self.domain_severity_modifiers = {
            "santé": 0.2,
            "sécurité": 0.2,
            "finance": 0.1,
            "environnement": 0.1,
            "éducation": 0.1,
            "politique": 0.1,
            "droit": 0.2,
            "technologie": 0.1,
            "sciences": 0.2,
            "général": 0.0
        }
    
    def evaluate_fallacy_severity(self, arguments: List[str], context: str = "général") -> Dict[str, Any]:
        """
        Évalue la gravité des sophismes dans une liste d'arguments.
        
        Args:
            arguments: Liste d'arguments à analyser
            context: Contexte de l'analyse (académique, politique, commercial, etc.)
            
        Returns:
            Dictionnaire contenant les résultats de l'évaluation
        """
        self.logger.info(f"Évaluation de la gravité des sophismes dans {len(arguments)} arguments")
        
        # Analyser l'impact du contexte
        context_analysis = self._analyze_context_impact(context)
        
        # Détecter les sophismes dans les arguments (simulation)
        fallacies = []
        for i, argument in enumerate(arguments):
            # Simuler la détection de sophismes
            if "expert" in argument.lower() or "autorité" in argument.lower():
                fallacies.append({
                    "fallacy_type": "Appel à l'autorité",
                    "context_text": argument,
                    "confidence": 0.7
                })
            elif "million" in argument.lower() or "populaire" in argument.lower() or "tout le monde" in argument.lower():
                fallacies.append({
                    "fallacy_type": "Appel à la popularité",
                    "context_text": argument,
                    "confidence": 0.6
                })
            elif "peur" in argument.lower() or "risque" in argument.lower() or "danger" in argument.lower():
                fallacies.append({
                    "fallacy_type": "Appel à la peur",
                    "context_text": argument,
                    "confidence": 0.8
                })
        
        # Évaluer la gravité de chaque sophisme
        fallacy_evaluations = []
        for fallacy in fallacies:
            severity_evaluation = self._calculate_fallacy_severity(fallacy, context_analysis)
            fallacy_evaluations.append(severity_evaluation)
        
        # Calculer la gravité globale
        overall_severity, severity_level = self._calculate_overall_severity(fallacy_evaluations)
        
        # Préparer le résultat
        result = {
            "overall_severity": overall_severity,
            "severity_level": severity_level,
            "fallacy_evaluations": fallacy_evaluations,
            "context_analysis": context_analysis,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def evaluate_fallacy_list(self, fallacies: List[Dict[str, Any]], context: str = "général") -> Dict[str, Any]:
        """
        Évalue la gravité d'une liste de sophismes.
        
        Args:
            fallacies: Liste de sophismes à évaluer
            context: Contexte de l'analyse (académique, politique, commercial, etc.)
            
        Returns:
            Dictionnaire contenant les résultats de l'évaluation
        """
        self.logger.info(f"Évaluation de la gravité de {len(fallacies)} sophismes")
        
        # Analyser l'impact du contexte
        context_analysis = self._analyze_context_impact(context)
        
        # Évaluer la gravité de chaque sophisme
        fallacy_evaluations = []
        for fallacy in fallacies:
            severity_evaluation = self._calculate_fallacy_severity(fallacy, context_analysis)
            fallacy_evaluations.append(severity_evaluation)
        
        # Calculer la gravité globale
        overall_severity, severity_level = self._calculate_overall_severity(fallacy_evaluations)
        
        # Préparer le résultat
        result = {
            "overall_severity": overall_severity,
            "severity_level": severity_level,
            "fallacy_evaluations": fallacy_evaluations,
            "context_analysis": context_analysis,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _analyze_context_impact(self, context: str) -> Dict[str, Any]:
        """
        Analyse l'impact du contexte sur la gravité des sophismes.
        
        Args:
            context: Contexte de l'analyse (académique, politique, commercial, etc.)
            
        Returns:
            Dictionnaire contenant l'analyse du contexte
        """
        # Déterminer le type de contexte
        context_type = context.lower() if context.lower() in self.context_severity_modifiers else "général"
        
        # Déterminer le type de public cible en fonction du contexte
        audience_map = {
            "académique": "experts",
            "scientifique": "experts",
            "politique": "grand public",
            "juridique": "professionnels",
            "médical": "professionnels",
            "commercial": "grand public",
            "journalistique": "grand public",
            "éducatif": "étudiants",
            "religieux": "grand public",
            "personnel": "général",
            "divertissement": "grand public",
            "général": "général"
        }
        audience_type = audience_map.get(context_type, "général")
        
        # Déterminer le type de domaine en fonction du contexte
        domain_map = {
            "académique": "sciences",
            "scientifique": "sciences",
            "politique": "politique",
            "juridique": "droit",
            "médical": "santé",
            "commercial": "finance",
            "journalistique": "général",
            "éducatif": "éducation",
            "religieux": "général",
            "personnel": "général",
            "divertissement": "général",
            "général": "général"
        }
        domain_type = domain_map.get(context_type, "général")
        
        # Obtenir les modificateurs de gravité
        context_severity_modifier = self.context_severity_modifiers.get(context_type, 0.0)
        audience_severity_modifier = self.audience_severity_modifiers.get(audience_type, 0.0)
        domain_severity_modifier = self.domain_severity_modifiers.get(domain_type, 0.0)
        
        # Préparer le résultat
        context_analysis = {
            "context_type": context_type,
            "audience_type": audience_type,
            "domain_type": domain_type,
            "context_severity_modifier": context_severity_modifier,
            "audience_severity_modifier": audience_severity_modifier,
            "domain_severity_modifier": domain_severity_modifier
        }
        
        return context_analysis
    
    def _calculate_fallacy_severity(self, fallacy: Dict[str, Any], context_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcule la gravité d'un sophisme.
        
        Args:
            fallacy: Sophisme à évaluer
            context_analysis: Analyse du contexte
            
        Returns:
            Dictionnaire contenant l'évaluation de la gravité du sophisme
        """
        # Obtenir le type de sophisme
        fallacy_type = fallacy.get("fallacy_type", "Sophisme inconnu")
        
        # Obtenir la gravité de base du sophisme
        base_severity = self.fallacy_severity_base.get(fallacy_type, 0.5)
        
        # Obtenir les modificateurs de gravité
        context_modifier = context_analysis.get("context_severity_modifier", 0.0)
        audience_modifier = context_analysis.get("audience_severity_modifier", 0.0)
        domain_modifier = context_analysis.get("domain_severity_modifier", 0.0)
        
        # Calculer la gravité finale
        final_severity = base_severity + context_modifier + audience_modifier + domain_modifier
        final_severity = max(0.0, min(1.0, final_severity))  # Limiter entre 0.0 et 1.0
        
        # Déterminer le niveau de gravité
        severity_level = self._determine_severity_level(final_severity)
        
        # Préparer le résultat
        severity_evaluation = {
            "fallacy_type": fallacy_type,
            "context_text": fallacy.get("context_text", ""),
            "base_severity": base_severity,
            "context_modifier": context_modifier,
            "audience_modifier": audience_modifier,
            "domain_modifier": domain_modifier,
            "final_severity": final_severity,
            "severity_level": severity_level
        }
        
        return severity_evaluation
    
    def _determine_severity_level(self, severity: float) -> str:
        """
        Détermine le niveau de gravité en fonction d'une valeur numérique.
        
        Args:
            severity: Valeur de gravité (entre 0.0 et 1.0)
            
        Returns:
            Niveau de gravité (Faible, Modéré, Élevé, Critique)
        """
        if severity < 0.4:
            return "Faible"
        elif severity < 0.7:
            return "Modéré"
        elif severity < 0.9:
            return "Élevé"
        else:
            return "Critique"
    
    def _calculate_overall_severity(self, fallacy_evaluations: List[Dict[str, Any]]) -> Tuple[float, str]:
        """
        Calcule la gravité globale à partir d'une liste d'évaluations de sophismes.
        
        Args:
            fallacy_evaluations: Liste d'évaluations de sophismes
            
        Returns:
            Tuple contenant la gravité globale et le niveau de gravité
        """
        if not fallacy_evaluations:
            return 0.0, "Faible"
        
        # Calculer la moyenne des gravités
        severities = [evaluation.get("final_severity", 0.0) for evaluation in fallacy_evaluations]
        avg_severity = sum(severities) / len(severities)
        
        # Donner plus de poids à la gravité la plus élevée
        max_severity = max(severities)
        overall_severity = (avg_severity * 0.7) + (max_severity * 0.3)
        overall_severity = max(0.0, min(1.0, overall_severity))  # Limiter entre 0.0 et 1.0
        
        # Déterminer le niveau de gravité
        severity_level = self._determine_severity_level(overall_severity)
        
        return overall_severity, severity_level


# Test de la classe si exécutée directement
if __name__ == "__main__":
    evaluator = EnhancedFallacySeverityEvaluator()
    
    # Exemple d'arguments
    arguments = [
        "Les experts affirment que ce produit est sûr.",
        "Ce produit est utilisé par des millions de personnes.",
        "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
        "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
    ]
    
    # Évaluer la gravité des sophismes
    result = evaluator.evaluate_fallacy_severity(arguments, "commercial")
    print(json.dumps(result, indent=2, ensure_ascii=False))
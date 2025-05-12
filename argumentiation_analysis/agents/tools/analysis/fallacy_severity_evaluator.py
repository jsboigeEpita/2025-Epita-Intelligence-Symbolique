#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil d'évaluation de la gravité des sophismes.

Ce module fournit des fonctionnalités pour évaluer la gravité des sophismes
identifiés dans un argument, en tenant compte de différents facteurs comme
le contexte, l'impact sur la validité de l'argument, et la visibilité du sophisme.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

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
logger = logging.getLogger("FallacySeverityEvaluator")


class FallacySeverityEvaluator:
    """
    Outil pour l'évaluation de la gravité des sophismes.
    
    Cet outil permet d'évaluer la gravité des sophismes identifiés dans un argument,
    en tenant compte de différents facteurs comme le contexte, l'impact sur la validité
    de l'argument, et la visibilité du sophisme.
    """
    
    def __init__(self):
        """
        Initialise l'évaluateur de gravité des sophismes.
        """
        self.logger = logger
        self._load_severity_data()
        self.logger.info("Évaluateur de gravité des sophismes initialisé.")
    
    def _load_severity_data(self):
        """
        Charge les données de gravité des sophismes.
        
        Ces données définissent la gravité de base de différents types de sophismes
        dans différents contextes.
        """
        # Gravité de base des sophismes (0.0 à 1.0)
        self.base_severity = {
            "Appel à l'autorité": 0.6,
            "Appel à la popularité": 0.5,
            "Appel à la tradition": 0.4,
            "Appel à la nouveauté": 0.4,
            "Appel à l'émotion": 0.7,
            "Faux dilemme": 0.8,
            "Pente glissante": 0.7,
            "Homme de paille": 0.8,
            "Ad hominem": 0.9,
            "Généralisation hâtive": 0.6,
            "Post hoc ergo propter hoc": 0.5,
            "Argument circulaire": 0.7,
            "Appel à l'ignorance": 0.6,
            "Sophisme du vrai écossais": 0.5,
            "Argument d'incrédulité personnelle": 0.4
        }
        
        # Modificateurs de gravité en fonction du contexte
        self.context_modifiers = {
            "politique": {
                "Appel à l'émotion": 0.3,  # Plus grave dans un contexte politique
                "Ad hominem": 0.2,
                "Homme de paille": 0.2,
                "Faux dilemme": 0.2
            },
            "scientifique": {
                "Appel à la popularité": 0.3,
                "Appel à la tradition": 0.3,
                "Appel à l'autorité": 0.2,
                "Post hoc ergo propter hoc": 0.3
            },
            "commercial": {
                "Appel à la nouveauté": 0.2,
                "Appel à la popularité": 0.2,
                "Faux dilemme": 0.2,
                "Appel à l'émotion": 0.2
            },
            "juridique": {
                "Pente glissante": 0.3,
                "Ad hominem": 0.3,
                "Appel à l'émotion": 0.2,
                "Généralisation hâtive": 0.3
            },
            "académique": {
                "Appel à l'autorité": 0.3,
                "Homme de paille": 0.2,
                "Ad hominem": 0.2,
                "Argument circulaire": 0.3
            }
        }
    
    def evaluate_severity(self, fallacy_type: str, argument: str, context: str) -> Dict[str, Any]:
        """
        Évalue la gravité d'un sophisme dans un argument.
        
        Cette méthode évalue la gravité d'un sophisme dans un argument en tenant compte
        de différents facteurs comme le type de sophisme, le contexte, et l'impact sur
        la validité de l'argument.
        
        Args:
            fallacy_type: Type de sophisme
            argument: Argument contenant le sophisme
            context: Contexte de l'argument
            
        Returns:
            Dictionnaire contenant le score de gravité et les détails de l'évaluation
        """
        self.logger.info(f"Évaluation de la gravité du sophisme '{fallacy_type}' dans le contexte: {context}")
        
        # Déterminer le type de contexte
        context_type = self._determine_context_type(context)
        self.logger.info(f"Type de contexte déterminé: {context_type}")
        
        # Calculer la gravité de base
        base_score = self.base_severity.get(fallacy_type, 0.5)
        self.logger.info(f"Gravité de base du sophisme '{fallacy_type}': {base_score}")
        
        # Appliquer les modificateurs de contexte
        context_modifier = 0.0
        if context_type in self.context_modifiers and fallacy_type in self.context_modifiers[context_type]:
            context_modifier = self.context_modifiers[context_type][fallacy_type]
        self.logger.info(f"Modificateur de contexte: {context_modifier}")
        
        # Calculer la visibilité du sophisme
        visibility_score = self._calculate_visibility(fallacy_type, argument)
        self.logger.info(f"Score de visibilité: {visibility_score}")
        
        # Calculer l'impact sur la validité de l'argument
        impact_score = self._calculate_impact(fallacy_type, argument)
        self.logger.info(f"Score d'impact: {impact_score}")
        
        # Calculer le score final
        final_score = min(1.0, base_score + context_modifier + (visibility_score * 0.1) + (impact_score * 0.2))
        self.logger.info(f"Score final de gravité: {final_score}")
        
        # Déterminer le niveau de gravité
        severity_level = self._determine_severity_level(final_score)
        
        # Préparer les résultats
        results = {
            "fallacy_type": fallacy_type,
            "context_type": context_type,
            "base_score": base_score,
            "context_modifier": context_modifier,
            "visibility_score": visibility_score,
            "impact_score": impact_score,
            "final_score": final_score,
            "severity_level": severity_level,
            "explanation": self._generate_explanation(fallacy_type, context_type, final_score)
        }
        
        return results
    
    def _determine_context_type(self, context: str) -> str:
        """
        Détermine le type de contexte à partir de la description du contexte.
        
        Args:
            context: Description du contexte
            
        Returns:
            Type de contexte (ex: politique, scientifique, etc.)
        """
        context_lower = context.lower()
        
        # Déterminer le type de contexte en fonction de mots-clés
        if any(keyword in context_lower for keyword in ["politique", "élection", "gouvernement", "président"]):
            return "politique"
        elif any(keyword in context_lower for keyword in ["scientifique", "recherche", "étude", "expérience"]):
            return "scientifique"
        elif any(keyword in context_lower for keyword in ["commercial", "publicité", "marketing", "produit"]):
            return "commercial"
        elif any(keyword in context_lower for keyword in ["juridique", "légal", "tribunal", "procès"]):
            return "juridique"
        elif any(keyword in context_lower for keyword in ["académique", "universitaire", "éducation"]):
            return "académique"
        else:
            return "général"
    
    def _calculate_visibility(self, fallacy_type: str, argument: str) -> float:
        """
        Calcule la visibilité d'un sophisme dans un argument.
        
        La visibilité représente à quel point le sophisme est évident ou facile à repérer.
        
        Args:
            fallacy_type: Type de sophisme
            argument: Argument contenant le sophisme
            
        Returns:
            Score de visibilité (0.0 à 1.0)
        """
        # Cette méthode pourrait utiliser des techniques de NLP pour évaluer la visibilité
        # Pour l'instant, nous utilisons une approche simplifiée basée sur des mots-clés
        
        # Mots-clés associés à chaque type de sophisme
        fallacy_keywords = {
            "Appel à l'autorité": ["expert", "autorité", "scientifique", "étude", "recherche", "unanime"],
            "Appel à la popularité": ["tout le monde", "majorité", "populaire", "commun", "consensus"],
            "Appel à la tradition": ["tradition", "toujours", "depuis longtemps", "historiquement", "ancestral"],
            "Appel à la nouveauté": ["nouveau", "moderne", "récent", "innovation", "dernière"],
            "Appel à l'émotion": ["peur", "crainte", "inquiétude", "espoir", "rêve", "cauchemar"],
            "Faux dilemme": ["soit", "ou bien", "alternative", "choix", "uniquement"],
            "Pente glissante": ["mènera à", "conduira à", "finira par", "inévitablement"],
            "Homme de paille": ["prétendre", "caricature", "déformer", "exagérer"],
            "Ad hominem": ["personne", "caractère", "intégrité", "moralité", "crédibilité"]
        }
        
        # Si le type de sophisme n'est pas dans la liste, retourner une visibilité moyenne
        if fallacy_type not in fallacy_keywords:
            return 0.5
        
        # Compter le nombre de mots-clés présents dans l'argument
        argument_lower = argument.lower()
        keyword_count = sum(1 for keyword in fallacy_keywords[fallacy_type] if keyword.lower() in argument_lower)
        
        # Calculer le score de visibilité
        visibility_score = min(1.0, keyword_count / len(fallacy_keywords[fallacy_type]))
        
        return visibility_score
    
    def _calculate_impact(self, fallacy_type: str, argument: str) -> float:
        """
        Calcule l'impact d'un sophisme sur la validité d'un argument.
        
        L'impact représente à quel point le sophisme affecte la validité de l'argument.
        
        Args:
            fallacy_type: Type de sophisme
            argument: Argument contenant le sophisme
            
        Returns:
            Score d'impact (0.0 à 1.0)
        """
        # Cette méthode pourrait utiliser des techniques de NLP pour évaluer l'impact
        # Pour l'instant, nous utilisons une approche simplifiée basée sur la longueur
        # de l'argument et la position du sophisme
        
        # Impact de base en fonction du type de sophisme
        base_impact = {
            "Appel à l'autorité": 0.6,
            "Appel à la popularité": 0.5,
            "Appel à la tradition": 0.4,
            "Appel à la nouveauté": 0.4,
            "Appel à l'émotion": 0.7,
            "Faux dilemme": 0.8,
            "Pente glissante": 0.7,
            "Homme de paille": 0.8,
            "Ad hominem": 0.9,
            "Généralisation hâtive": 0.6,
            "Post hoc ergo propter hoc": 0.5,
            "Argument circulaire": 0.7,
            "Appel à l'ignorance": 0.6,
            "Sophisme du vrai écossais": 0.5,
            "Argument d'incrédulité personnelle": 0.4
        }
        
        # Si le type de sophisme n'est pas dans la liste, retourner un impact moyen
        if fallacy_type not in base_impact:
            return 0.5
        
        # Calculer l'impact en fonction de la longueur de l'argument
        # Plus l'argument est court, plus l'impact du sophisme est important
        length_modifier = max(0.0, min(0.3, 1.0 - (len(argument) / 1000)))
        
        # Calculer le score d'impact
        impact_score = min(1.0, base_impact[fallacy_type] + length_modifier)
        
        return impact_score
    
    def _determine_severity_level(self, score: float) -> str:
        """
        Détermine le niveau de gravité en fonction du score.
        
        Args:
            score: Score de gravité (0.0 à 1.0)
            
        Returns:
            Niveau de gravité (Faible, Modéré, Élevé, Critique)
        """
        if score < 0.3:
            return "Faible"
        elif score < 0.6:
            return "Modéré"
        elif score < 0.8:
            return "Élevé"
        else:
            return "Critique"
    
    def _generate_explanation(self, fallacy_type: str, context_type: str, score: float) -> str:
        """
        Génère une explication de la gravité du sophisme.
        
        Args:
            fallacy_type: Type de sophisme
            context_type: Type de contexte
            score: Score de gravité
            
        Returns:
            Explication de la gravité du sophisme
        """
        severity_level = self._determine_severity_level(score)
        
        explanations = {
            "Faible": f"Le sophisme '{fallacy_type}' a un impact limité dans ce contexte {context_type}. Il n'affecte pas significativement la validité de l'argument.",
            "Modéré": f"Le sophisme '{fallacy_type}' a un impact modéré dans ce contexte {context_type}. Il affecte partiellement la validité de l'argument.",
            "Élevé": f"Le sophisme '{fallacy_type}' a un impact important dans ce contexte {context_type}. Il compromet sérieusement la validité de l'argument.",
            "Critique": f"Le sophisme '{fallacy_type}' a un impact critique dans ce contexte {context_type}. Il invalide complètement l'argument."
        }
        
        return explanations.get(severity_level, "Explication non disponible.")
    
    def rank_fallacies(self, fallacies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classe les sophismes par ordre de gravité.
        
        Args:
            fallacies: Liste des sophismes à classer
            
        Returns:
            Liste des sophismes classés par gravité
        """
        self.logger.info(f"Classement de {len(fallacies)} sophismes par gravité")
        
        # Évaluer la gravité de chaque sophisme
        for fallacy in fallacies:
            if "severity" not in fallacy:
                # Si la gravité n'est pas déjà évaluée, l'évaluer
                if "argument" in fallacy and "context" in fallacy:
                    severity_results = self.evaluate_severity(
                        fallacy["fallacy_type"],
                        fallacy["argument"],
                        fallacy["context"]
                    )
                    fallacy["severity"] = severity_results["final_score"]
                    fallacy["severity_level"] = severity_results["severity_level"]
                else:
                    # Si l'argument ou le contexte n'est pas disponible, utiliser la gravité de base
                    fallacy["severity"] = self.base_severity.get(fallacy["fallacy_type"], 0.5)
                    fallacy["severity_level"] = self._determine_severity_level(fallacy["severity"])
        
        # Trier les sophismes par gravité (du plus grave au moins grave)
        sorted_fallacies = sorted(fallacies, key=lambda x: x.get("severity", 0.0), reverse=True)
        
        self.logger.info(f"Sophismes classés par gravité: {len(sorted_fallacies)}")
        
        return sorted_fallacies
    
    def evaluate_impact(self, fallacy_type: str, argument: str, context: str) -> Dict[str, Any]:
        """
        Évalue l'impact d'un sophisme sur la validité d'un argument.
        
        Args:
            fallacy_type: Type de sophisme
            argument: Argument contenant le sophisme
            context: Contexte de l'argument
            
        Returns:
            Dictionnaire contenant les détails de l'impact
        """
        self.logger.info(f"Évaluation de l'impact du sophisme '{fallacy_type}' sur l'argument")
        
        # Évaluer la gravité du sophisme
        severity_results = self.evaluate_severity(fallacy_type, argument, context)
        
        # Générer des suggestions pour corriger l'argument
        suggestions = self._generate_correction_suggestions(fallacy_type, argument)
        
        # Préparer les résultats
        impact_results = {
            "fallacy_type": fallacy_type,
            "severity": severity_results["final_score"],
            "severity_level": severity_results["severity_level"],
            "explanation": severity_results["explanation"],
            "impact_on_validity": self._calculate_validity_impact(severity_results["final_score"]),
            "correction_suggestions": suggestions
        }
        
        return impact_results
    
    def _calculate_validity_impact(self, severity_score: float) -> str:
        """
        Calcule l'impact sur la validité de l'argument en fonction du score de gravité.
        
        Args:
            severity_score: Score de gravité
            
        Returns:
            Description de l'impact sur la validité
        """
        if severity_score < 0.3:
            return "L'argument reste globalement valide malgré ce sophisme."
        elif severity_score < 0.6:
            return "L'argument est partiellement affaibli par ce sophisme."
        elif severity_score < 0.8:
            return "L'argument est significativement affaibli par ce sophisme."
        else:
            return "L'argument est invalidé par ce sophisme."
    
    def _generate_correction_suggestions(self, fallacy_type: str, argument: str) -> List[str]:
        """
        Génère des suggestions pour corriger un argument contenant un sophisme.
        
        Args:
            fallacy_type: Type de sophisme
            argument: Argument contenant le sophisme
            
        Returns:
            Liste de suggestions pour corriger l'argument
        """
        # Suggestions de correction pour différents types de sophismes
        correction_suggestions = {
            "Appel à l'autorité": [
                "Citer des preuves concrètes plutôt que de s'appuyer uniquement sur l'autorité.",
                "Expliquer pourquoi l'autorité citée est pertinente dans ce contexte spécifique.",
                "Reconnaître les limites de l'expertise de l'autorité citée."
            ],
            "Appel à la popularité": [
                "Fournir des preuves objectives plutôt que de s'appuyer sur l'opinion populaire.",
                "Expliquer pourquoi l'argument est valide indépendamment de sa popularité.",
                "Reconnaître que la popularité n'est pas un gage de vérité."
            ],
            "Appel à la tradition": [
                "Expliquer pourquoi la tradition est pertinente dans ce contexte spécifique.",
                "Fournir des preuves objectives en plus de l'argument traditionnel.",
                "Reconnaître que la tradition n'est pas un gage de validité."
            ],
            "Faux dilemme": [
                "Présenter d'autres alternatives possibles.",
                "Nuancer les options présentées.",
                "Reconnaître la complexité de la situation."
            ],
            "Ad hominem": [
                "Se concentrer sur les arguments plutôt que sur la personne.",
                "Éviter les attaques personnelles.",
                "Répondre aux arguments de manière objective."
            ]
        }
        
        # Si le type de sophisme n'est pas dans la liste, retourner des suggestions génériques
        if fallacy_type not in correction_suggestions:
            return [
                "Fournir des preuves objectives pour soutenir l'argument.",
                "Éviter les raisonnements fallacieux.",
                "Structurer l'argument de manière logique et cohérente."
            ]
        
        return correction_suggestions[fallacy_type]


# Test de la classe si exécutée directement
if __name__ == "__main__":
    evaluator = FallacySeverityEvaluator()
    
    # Exemple d'évaluation de la gravité d'un sophisme
    fallacy_type = "Appel à l'autorité"
    argument = "Les experts sont unanimes : ce produit est sûr et efficace."
    context = "Discours commercial pour un produit controversé"
    
    severity_results = evaluator.evaluate_severity(fallacy_type, argument, context)
    print(f"Résultats de l'évaluation de gravité: {json.dumps(severity_results, indent=2, ensure_ascii=False)}")
    
    # Exemple de classement de sophismes
    fallacies = [
        {
            "fallacy_type": "Appel à l'autorité",
            "argument": "Les experts sont unanimes : ce produit est sûr et efficace.",
            "context": "Discours commercial pour un produit controversé"
        },
        {
            "fallacy_type": "Appel à la popularité",
            "argument": "Des millions de personnes utilisent ce produit, vous devriez l'essayer aussi.",
            "context": "Discours commercial pour un produit controversé"
        },
        {
            "fallacy_type": "Faux dilemme",
            "argument": "Soit vous achetez ce produit, soit vous continuerez à souffrir.",
            "context": "Discours commercial pour un produit controversé"
        }
    ]
    
    ranked_fallacies = evaluator.rank_fallacies(fallacies)
    print(f"Sophismes classés par gravité: {json.dumps(ranked_fallacies, indent=2, ensure_ascii=False)}")
    
    # Exemple d'évaluation de l'impact d'un sophisme
    impact_results = evaluator.evaluate_impact(fallacy_type, argument, context)
    print(f"Résultats de l'évaluation d'impact: {json.dumps(impact_results, indent=2, ensure_ascii=False)}")
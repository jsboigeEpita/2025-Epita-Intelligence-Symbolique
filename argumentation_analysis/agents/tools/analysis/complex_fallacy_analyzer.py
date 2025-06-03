#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil d'analyse des sophismes complexes.

Ce module fournit des fonctionnalités pour analyser des sophismes complexes,
comme les combinaisons de sophismes ou les sophismes qui s'étendent sur plusieurs
arguments.
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

# Importer les autres analyseurs
from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ComplexFallacyAnalyzer")


class ComplexFallacyAnalyzer:
    """
    Outil pour l'analyse des sophismes complexes.
    
    Cet outil permet d'analyser des sophismes complexes, comme les combinaisons
    de sophismes ou les sophismes qui s'étendent sur plusieurs arguments.
    """
    
    def __init__(self):
        """
        Initialise l'analyseur de sophismes complexes.
        """
        self.logger = logger
        self.contextual_analyzer = ContextualFallacyAnalyzer()
        self.severity_evaluator = FallacySeverityEvaluator()
        self._load_fallacy_combinations()
        self.logger.info("Analyseur de sophismes complexes initialisé.")
    
    def _load_fallacy_combinations(self):
        """
        Charge les combinaisons connues de sophismes.
        
        Ces combinaisons définissent des motifs courants de sophismes qui apparaissent
        ensemble et qui peuvent former des sophismes complexes.
        """
        # Combinaisons connues de sophismes
        self.fallacy_combinations = {
            "Double appel": {
                "description": "Combinaison d'un appel à l'autorité et d'un appel à la popularité",
                "components": ["Appel à l'autorité", "Appel à la popularité"],
                "severity_modifier": 0.2  # Augmente la gravité de 0.2
            },
            "Dilemme émotionnel": {
                "description": "Combinaison d'un faux dilemme et d'un appel à l'émotion",
                "components": ["Faux dilemme", "Appel à l'émotion"],
                "severity_modifier": 0.3
            },
            "Attaque personnelle généralisée": {
                "description": "Combinaison d'un ad hominem et d'une généralisation hâtive",
                "components": ["Ad hominem", "Généralisation hâtive"],
                "severity_modifier": 0.3
            },
            "Tradition autoritaire": {
                "description": "Combinaison d'un appel à la tradition et d'un appel à l'autorité",
                "components": ["Appel à la tradition", "Appel à l'autorité"],
                "severity_modifier": 0.2
            },
            "Pente émotionnelle": {
                "description": "Combinaison d'une pente glissante et d'un appel à l'émotion",
                "components": ["Pente glissante", "Appel à l'émotion"],
                "severity_modifier": 0.3
            }
        }
        
        # Sophismes structurels qui s'étendent sur plusieurs arguments
        self.structural_fallacies = {
            "Contradiction cachée": {
                "description": "Contradiction entre deux arguments présentés comme cohérents",
                "detection_pattern": "contradiction",
                "severity_modifier": 0.3
            },
            "Cercle argumentatif": {
                "description": "Série d'arguments qui forment un cercle logique",
                "detection_pattern": "circular",
                "severity_modifier": 0.3
            },
            "Déplacement de fardeau": {
                "description": "Série d'arguments qui déplacent progressivement le fardeau de la preuve",
                "detection_pattern": "burden_shift",
                "severity_modifier": 0.2
            },
            "Escalade d'engagement": {
                "description": "Série d'arguments qui augmentent progressivement l'engagement",
                "detection_pattern": "escalation",
                "severity_modifier": 0.2
            }
        }
    
    def identify_combined_fallacies(self, argument: str) -> List[Dict[str, Any]]:
        """
        Identifie les combinaisons de sophismes dans un argument.
        
        Cette méthode analyse un argument pour identifier des combinaisons connues
        de sophismes qui apparaissent ensemble et qui peuvent former des sophismes
        complexes.
        
        Args:
            argument: Argument à analyser
            
        Returns:
            Liste des combinaisons de sophismes identifiées
        """
        self.logger.info(f"Identification des combinaisons de sophismes dans l'argument (longueur: {len(argument)})")
        
        # Identifier les sophismes individuels dans l'argument
        individual_fallacies = self.contextual_analyzer.identify_contextual_fallacies(
            argument=argument,
            context="général"  # Contexte générique pour l'identification initiale
        )
        
        self.logger.info(f"Sophismes individuels identifiés: {len(individual_fallacies)}")
        
        # Identifier les combinaisons de sophismes
        combined_fallacies = []
        
        # Pour chaque combinaison connue, vérifier si ses composants sont présents
        for combination_name, combination_info in self.fallacy_combinations.items():
            components = combination_info["components"]
            
            # Vérifier si tous les composants sont présents
            components_present = all(
                any(fallacy["fallacy_type"] == component for fallacy in individual_fallacies)
                for component in components
            )
            
            if components_present:
                # Extraire les sophismes individuels qui forment cette combinaison
                component_fallacies = [
                    fallacy for fallacy in individual_fallacies
                    if fallacy["fallacy_type"] in components
                ]
                
                # Calculer la gravité de la combinaison
                base_severity = max(fallacy.get("confidence", 0.5) for fallacy in component_fallacies)
                combined_severity = min(1.0, base_severity + combination_info["severity_modifier"])
                
                # Ajouter la combinaison identifiée
                combined_fallacies.append({
                    "combination_name": combination_name,
                    "description": combination_info["description"],
                    "components": components,
                    "component_fallacies": component_fallacies,
                    "severity": combined_severity,
                    "severity_level": self.severity_evaluator._determine_severity_level(combined_severity),
                    "explanation": f"Cette combinaison de sophismes ({', '.join(components)}) forme un sophisme complexe de type '{combination_name}', qui est particulièrement problématique car il combine plusieurs types de raisonnements fallacieux."
                })
        
        self.logger.info(f"Combinaisons de sophismes identifiées: {len(combined_fallacies)}")
        
        return combined_fallacies
    
    def analyze_structural_fallacies(self, arguments: List[str]) -> List[Dict[str, Any]]:
        """
        Analyse les sophismes structurels qui s'étendent sur plusieurs arguments.
        
        Cette méthode analyse un ensemble d'arguments pour identifier des sophismes
        structurels qui s'étendent sur plusieurs arguments, comme les contradictions
        cachées ou les cercles argumentatifs.
        
        Args:
            arguments: Liste d'arguments à analyser
            
        Returns:
            Liste des sophismes structurels identifiés
        """
        self.logger.info(f"Analyse des sophismes structurels dans {len(arguments)} arguments")
        
        # Identifier les sophismes individuels dans chaque argument
        all_fallacies = []
        for i, argument in enumerate(arguments):
            fallacies = self.contextual_analyzer.identify_contextual_fallacies(
                argument=argument,
                context="général"  # Contexte générique pour l'identification initiale
            )
            
            # Ajouter l'index de l'argument à chaque sophisme
            for fallacy in fallacies:
                fallacy["argument_index"] = i
            
            all_fallacies.extend(fallacies)
        
        self.logger.info(f"Sophismes individuels identifiés dans tous les arguments: {len(all_fallacies)}")
        
        # Identifier les sophismes structurels
        structural_fallacies = []
        
        # Détecter les contradictions cachées
        contradictions = self._detect_contradictions(arguments)
        for contradiction in contradictions:
            structural_fallacies.append({
                "structural_fallacy_type": "Contradiction cachée",
                "description": self.structural_fallacies["Contradiction cachée"]["description"],
                "involved_arguments": contradiction["involved_arguments"],
                "contradiction_details": contradiction["details"],
                "severity": 0.8,  # Gravité élevée par défaut pour les contradictions
                "severity_level": "Élevé",
                "explanation": "Cette contradiction entre arguments affaiblit significativement la cohérence globale du raisonnement."
            })
        
        # Détecter les cercles argumentatifs
        circles = self._detect_circular_arguments(arguments)
        for circle in circles:
            structural_fallacies.append({
                "structural_fallacy_type": "Cercle argumentatif",
                "description": self.structural_fallacies["Cercle argumentatif"]["description"],
                "involved_arguments": circle["involved_arguments"],
                "circle_details": circle["details"],
                "severity": 0.7,  # Gravité élevée par défaut pour les cercles
                "severity_level": "Élevé",
                "explanation": "Ce cercle argumentatif rend le raisonnement global circulaire et donc non valide."
            })
        
        self.logger.info(f"Sophismes structurels identifiés: {len(structural_fallacies)}")
        
        return structural_fallacies
    
    def _detect_contradictions(self, arguments: List[str]) -> List[Dict[str, Any]]:
        """
        Détecte les contradictions entre arguments.
        
        Args:
            arguments: Liste d'arguments à analyser
            
        Returns:
            Liste des contradictions détectées
        """
        # Cette méthode pourrait utiliser des techniques de NLP pour détecter les contradictions
        # Pour l'instant, nous utilisons une approche simplifiée basée sur des mots-clés
        
        contradictions = []
        
        # Mots-clés qui indiquent des affirmations positives et négatives
        positive_keywords = ["est", "sont", "a", "ont", "peut", "peuvent", "doit", "doivent"]
        negative_keywords = ["n'est pas", "ne sont pas", "n'a pas", "n'ont pas", "ne peut pas", "ne peuvent pas", "ne doit pas", "ne doivent pas"]
        
        # Pour chaque paire d'arguments
        for i in range(len(arguments)):
            for j in range(i + 1, len(arguments)):
                arg1 = arguments[i].lower()
                arg2 = arguments[j].lower()
                
                # Vérifier si un argument contient une affirmation positive et l'autre une négation correspondante
                for pos_kw in positive_keywords:
                    for neg_kw in negative_keywords:
                        # Vérifier si le mot-clé positif est dans arg1 et le négatif dans arg2
                        if pos_kw in arg1 and neg_kw in arg2:
                            # Extraire le contexte autour des mots-clés
                            pos_idx = arg1.find(pos_kw)
                            neg_idx = arg2.find(neg_kw)
                            
                            pos_context = arg1[max(0, pos_idx - 20):min(len(arg1), pos_idx + len(pos_kw) + 20)]
                            neg_context = arg2[max(0, neg_idx - 20):min(len(arg2), neg_idx + len(neg_kw) + 20)]
                            
                            contradictions.append({
                                "involved_arguments": [i, j],
                                "details": {
                                    "positive_statement": pos_context,
                                    "negative_statement": neg_context
                                }
                            })
                        
                        # Vérifier si le mot-clé positif est dans arg2 et le négatif dans arg1
                        if pos_kw in arg2 and neg_kw in arg1:
                            # Extraire le contexte autour des mots-clés
                            pos_idx = arg2.find(pos_kw)
                            neg_idx = arg1.find(neg_kw)
                            
                            pos_context = arg2[max(0, pos_idx - 20):min(len(arg2), pos_idx + len(pos_kw) + 20)]
                            neg_context = arg1[max(0, neg_idx - 20):min(len(arg1), neg_idx + len(neg_kw) + 20)]
                            
                            contradictions.append({
                                "involved_arguments": [i, j],
                                "details": {
                                    "positive_statement": pos_context,
                                    "negative_statement": neg_context
                                }
                            })
        
        return contradictions
    
    def _detect_circular_arguments(self, arguments: List[str]) -> List[Dict[str, Any]]:
        """
        Détecte les cercles argumentatifs.
        
        Args:
            arguments: Liste d'arguments à analyser
            
        Returns:
            Liste des cercles argumentatifs détectés
        """
        # Cette méthode pourrait utiliser des techniques de NLP pour détecter les cercles argumentatifs
        # Pour l'instant, nous utilisons une approche simplifiée basée sur des mots-clés
        
        circles = []
        
        # Si nous avons moins de 3 arguments, il ne peut pas y avoir de cercle
        if len(arguments) < 3:
            return circles
        
        # Pour chaque triplet d'arguments
        for i in range(len(arguments)):
            for j in range(len(arguments)):
                if j == i:
                    continue
                for k in range(len(arguments)):
                    if k == i or k == j:
                        continue
                    
                    arg1 = arguments[i].lower()
                    arg2 = arguments[j].lower()
                    arg3 = arguments[k].lower()
                    
                    # Vérifier si arg1 soutient arg2, arg2 soutient arg3, et arg3 soutient arg1
                    # Cette vérification est très simplifiée et pourrait être améliorée
                    if (any(kw in arg1 for kw in ["donc", "ainsi", "par conséquent"]) and
                        any(kw in arg2 for kw in ["donc", "ainsi", "par conséquent"]) and
                        any(kw in arg3 for kw in ["donc", "ainsi", "par conséquent"])):
                        
                        circles.append({
                            "involved_arguments": [i, j, k],
                            "details": {
                                "arg1_supports_arg2": True,
                                "arg2_supports_arg3": True,
                                "arg3_supports_arg1": True
                            }
                        })
        
        return circles
    
    def identify_fallacy_patterns(self, text: str) -> List[Dict[str, Any]]:
        """
        Identifie les motifs de sophismes dans un texte.
        
        Cette méthode analyse un texte pour identifier des motifs récurrents de sophismes,
        comme l'alternance entre appel à l'émotion et appel à l'autorité.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des motifs de sophismes identifiés
        """
        self.logger.info(f"Identification des motifs de sophismes dans le texte (longueur: {len(text)})")
        
        # Diviser le texte en paragraphes
        paragraphs = text.split("\n\n")
        
        # Identifier les sophismes dans chaque paragraphe
        paragraph_fallacies = []
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            fallacies = self.contextual_analyzer.identify_contextual_fallacies(
                argument=paragraph,
                context="général"  # Contexte générique pour l'identification initiale
            )
            
            # Ajouter l'index du paragraphe à chaque sophisme
            for fallacy in fallacies:
                fallacy["paragraph_index"] = i
            
            paragraph_fallacies.append({
                "paragraph_index": i,
                "fallacies": fallacies
            })
        
        self.logger.info(f"Sophismes identifiés dans {len(paragraph_fallacies)} paragraphes")
        
        # Identifier les motifs de sophismes
        patterns = []
        
        # Motif d'alternance
        alternation_patterns = self._detect_alternation_patterns(paragraph_fallacies)
        for pattern in alternation_patterns:
            patterns.append({
                "pattern_type": "Alternance",
                "description": f"Alternance entre {pattern['fallacy_type1']} et {pattern['fallacy_type2']}",
                "involved_paragraphs": pattern["involved_paragraphs"],
                "fallacy_types": [pattern["fallacy_type1"], pattern["fallacy_type2"]],
                "severity": 0.7,
                "severity_level": "Élevé",
                "explanation": f"Ce motif d'alternance entre {pattern['fallacy_type1']} et {pattern['fallacy_type2']} renforce l'effet persuasif des sophismes en combinant leurs effets."
            })
        
        # Motif d'escalade
        escalation_patterns = self._detect_escalation_patterns(paragraph_fallacies)
        for pattern in escalation_patterns:
            patterns.append({
                "pattern_type": "Escalade",
                "description": f"Escalade de {pattern['start_fallacy_type']} vers {pattern['end_fallacy_type']}",
                "involved_paragraphs": pattern["involved_paragraphs"],
                "fallacy_types": pattern["fallacy_sequence"],
                "severity": 0.8,
                "severity_level": "Élevé",
                "explanation": f"Ce motif d'escalade de sophismes augmente progressivement l'intensité de l'argumentation fallacieuse, rendant la manipulation plus difficile à détecter."
            })
        
        self.logger.info(f"Motifs de sophismes identifiés: {len(patterns)}")
        
        return patterns
    
    def _detect_alternation_patterns(self, paragraph_fallacies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Détecte les motifs d'alternance entre deux types de sophismes.
        
        Args:
            paragraph_fallacies: Liste des sophismes identifiés par paragraphe
            
        Returns:
            Liste des motifs d'alternance détectés
        """
        alternation_patterns = []
        
        # Si nous avons moins de 4 paragraphes, il est difficile de détecter un motif d'alternance
        if len(paragraph_fallacies) < 4:
            return alternation_patterns
        
        # Pour chaque paire de types de sophismes
        fallacy_types = set()
        for paragraph in paragraph_fallacies:
            for fallacy in paragraph["fallacies"]:
                fallacy_types.add(fallacy["fallacy_type"])
        
        for type1 in fallacy_types:
            for type2 in fallacy_types:
                if type1 == type2:
                    continue
                
                # Vérifier s'il y a un motif d'alternance
                alternation_count = 0
                involved_paragraphs = []
                
                for i in range(len(paragraph_fallacies) - 1):
                    fallacies1 = [f["fallacy_type"] for f in paragraph_fallacies[i]["fallacies"]]
                    fallacies2 = [f["fallacy_type"] for f in paragraph_fallacies[i + 1]["fallacies"]]
                    
                    if type1 in fallacies1 and type2 in fallacies2:
                        alternation_count += 1
                        involved_paragraphs.extend([paragraph_fallacies[i]["paragraph_index"], paragraph_fallacies[i + 1]["paragraph_index"]])
                    elif type2 in fallacies1 and type1 in fallacies2:
                        alternation_count += 1
                        involved_paragraphs.extend([paragraph_fallacies[i]["paragraph_index"], paragraph_fallacies[i + 1]["paragraph_index"]])
                
                # Si nous avons au moins 2 alternances, c'est un motif
                if alternation_count >= 2:
                    alternation_patterns.append({
                        "fallacy_type1": type1,
                        "fallacy_type2": type2,
                        "alternation_count": alternation_count,
                        "involved_paragraphs": list(set(involved_paragraphs))
                    })
        
        return alternation_patterns
    
    def _detect_escalation_patterns(self, paragraph_fallacies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Détecte les motifs d'escalade de sophismes.
        
        Args:
            paragraph_fallacies: Liste des sophismes identifiés par paragraphe
            
        Returns:
            Liste des motifs d'escalade détectés
        """
        escalation_patterns = []
        
        # Si nous avons moins de 3 paragraphes, il est difficile de détecter un motif d'escalade
        if len(paragraph_fallacies) < 3:
            return escalation_patterns
        
        # Définir l'ordre d'escalade des sophismes (du moins grave au plus grave)
        escalation_order = [
            "Appel à la tradition",
            "Appel à la nouveauté",
            "Appel à la popularité",
            "Appel à l'autorité",
            "Généralisation hâtive",
            "Appel à l'émotion",
            "Pente glissante",
            "Faux dilemme",
            "Homme de paille",
            "Ad hominem"
        ]
        
        # Pour chaque séquence de paragraphes
        for i in range(len(paragraph_fallacies) - 2):
            fallacies1 = [f["fallacy_type"] for f in paragraph_fallacies[i]["fallacies"]]
            fallacies2 = [f["fallacy_type"] for f in paragraph_fallacies[i + 1]["fallacies"]]
            fallacies3 = [f["fallacy_type"] for f in paragraph_fallacies[i + 2]["fallacies"]]
            
            # Vérifier s'il y a une escalade
            escalation_sequence = []
            
            for f1 in fallacies1:
                for f2 in fallacies2:
                    for f3 in fallacies3:
                        if f1 in escalation_order and f2 in escalation_order and f3 in escalation_order:
                            f1_idx = escalation_order.index(f1)
                            f2_idx = escalation_order.index(f2)
                            f3_idx = escalation_order.index(f3)
                            
                            if f1_idx < f2_idx < f3_idx:
                                escalation_sequence = [f1, f2, f3]
                                break
            
            if escalation_sequence:
                escalation_patterns.append({
                    "start_fallacy_type": escalation_sequence[0],
                    "end_fallacy_type": escalation_sequence[-1],
                    "fallacy_sequence": escalation_sequence,
                    "involved_paragraphs": [
                        paragraph_fallacies[i]["paragraph_index"],
                        paragraph_fallacies[i + 1]["paragraph_index"],
                        paragraph_fallacies[i + 2]["paragraph_index"]
                    ]
                })
        
        return escalation_patterns


# Test de la classe si exécutée directement
if __name__ == "__main__":
    analyzer = ComplexFallacyAnalyzer()
    
    # Exemple d'identification de combinaisons de sophismes
    argument = "Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà, donc vous devriez l'essayer aussi."
    
    combined_fallacies = analyzer.identify_combined_fallacies(argument)
    print(f"Combinaisons de sophismes identifiées: {json.dumps(combined_fallacies, indent=2, ensure_ascii=False)}")
    
    # Exemple d'analyse de sophismes structurels
    arguments = [
        "Les experts affirment que ce produit est sûr.",
        "Ce produit est sûr car il est utilisé par des millions de personnes.",
        "Vous devriez faire confiance aux experts et utiliser ce produit."
    ]
    
    structural_fallacies = analyzer.analyze_structural_fallacies(arguments)
    print(f"Sophismes structurels identifiés: {json.dumps(structural_fallacies, indent=2, ensure_ascii=False)}")
    
    # Exemple d'identification de motifs de sophismes
    text = """
    Les experts sont unanimes : ce produit est sûr et efficace.
    
    Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.
    
    Des millions de personnes utilisent déjà ce produit avec satisfaction.
    
    Les critiques de ce produit sont motivés par des intérêts financiers et ne sont pas crédibles.
    
    La science a prouvé l'efficacité de ce produit dans de nombreuses études.
    
    Si vous n'agissez pas maintenant, il sera trop tard pour profiter des bienfaits de ce produit.
    """
    
    patterns = analyzer.identify_fallacy_patterns(text)
    print(f"Motifs de sophismes identifiés: {json.dumps(patterns, indent=2, ensure_ascii=False)}")
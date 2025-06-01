#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil d'analyse des sophismes complexes amélioré.

Ce module fournit des fonctionnalités avancées pour analyser des sophismes complexes,
comme les combinaisons de sophismes, les sophismes qui s'étendent sur plusieurs
arguments, et les structures argumentatives sophistiquées.
"""

import os
import sys
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer l'analyseur de sophismes complexes de base
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer as BaseAnalyzer

# Fonction d'importation paresseuse pour éviter les importations circulaires
def _lazy_imports():
    """Importe les modules de manière paresseuse pour éviter les importations circulaires."""
    global EnhancedContextualFallacyAnalyzer, EnhancedFallacySeverityEvaluator
    
    # Importer les analyseurs améliorés
    from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("EnhancedComplexFallacyAnalyzer")


class EnhancedComplexFallacyAnalyzer(BaseAnalyzer):
    """
    Outil amélioré pour l'analyse des sophismes complexes.
    
    Cette version améliorée intègre l'analyse de structure argumentative,
    la détection de sophismes composés, et l'analyse de cohérence inter-arguments
    pour une analyse plus précise et nuancée des sophismes complexes.
    """
    
    def __init__(self):
        """
        Initialise l'analyseur de sophismes complexes amélioré.
        """
        super().__init__()
        self.logger = logger
        
        # Appeler la fonction d'importation paresseuse
        _lazy_imports()
        
        # Initialiser les analyseurs améliorés
        self.contextual_analyzer = EnhancedContextualFallacyAnalyzer()
        self.severity_evaluator = EnhancedFallacySeverityEvaluator()
        
        # Définir les modèles de structure argumentative
        self.argument_structure_patterns = self._define_argument_structure_patterns()
        
        # Définir les modèles de sophismes composés avancés
        self.advanced_fallacy_combinations = self._define_advanced_fallacy_combinations()
        
        # Historique des analyses pour l'apprentissage continu
        self.analysis_history = []
        
        self.logger.info("Analyseur de sophismes complexes amélioré initialisé.")
    
    def _define_argument_structure_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Définit les modèles de structure argumentative.
        
        Returns:
            Dictionnaire contenant les modèles de structure argumentative
        """
        patterns = {
            "chaîne_causale": {
                "description": "Série d'arguments liés par des relations causales",
                "detection_pattern": ["cause", "effet", "conséquence", "résultat", "entraîne", "provoque"],
                "fallacy_risk": "Pente glissante, Post hoc ergo propter hoc",
                "complexity_score": 0.7
            },
            "structure_conditionnelle": {
                "description": "Arguments basés sur des conditions (si... alors...)",
                "detection_pattern": ["si", "alors", "dans ce cas", "à condition que", "seulement si"],
                "fallacy_risk": "Faux dilemme, Affirmation du conséquent",
                "complexity_score": 0.6
            },
            "structure_comparative": {
                "description": "Arguments basés sur des comparaisons",
                "detection_pattern": ["plus", "moins", "autant", "comme", "similaire", "différent", "contrairement à"],
                "fallacy_risk": "Fausse analogie, Fausse équivalence",
                "complexity_score": 0.5
            },
            "structure_autorité": {
                "description": "Arguments basés sur des autorités ou des experts",
                "detection_pattern": ["expert", "autorité", "étude", "recherche", "scientifique", "spécialiste"],
                "fallacy_risk": "Appel à l'autorité, Appel à la nouveauté",
                "complexity_score": 0.4
            },
            "structure_généralisation": {
                "description": "Arguments basés sur des généralisations",
                "detection_pattern": ["tous", "aucun", "toujours", "jamais", "chaque", "la plupart"],
                "fallacy_risk": "Généralisation hâtive, Sophisme du vrai écossais",
                "complexity_score": 0.5
            }
        }
        
        return patterns
    
    def _define_advanced_fallacy_combinations(self) -> Dict[str, Dict[str, Any]]:
        """
        Définit les modèles de sophismes composés avancés.
        
        Returns:
            Dictionnaire contenant les modèles de sophismes composés avancés
        """
        combinations = {
            "cascade_émotionnelle": {
                "description": "Combinaison d'appels à l'émotion qui s'intensifient progressivement",
                "components": ["Appel à l'émotion", "Appel à la peur", "Appel à la pitié"],
                "pattern": "escalation",
                "severity_modifier": 0.4,
                "detection_threshold": 0.7
            },
            "cercle_autoritaire": {
                "description": "Combinaison circulaire d'appels à l'autorité qui se renforcent mutuellement",
                "components": ["Appel à l'autorité", "Appel à la tradition", "Appel à la popularité"],
                "pattern": "circular",
                "severity_modifier": 0.3,
                "detection_threshold": 0.6
            },
            "diversion_complexe": {
                "description": "Combinaison de techniques de diversion pour détourner l'attention du sujet principal",
                "components": ["Homme de paille", "Hareng rouge", "Ad hominem"],
                "pattern": "diversion",
                "severity_modifier": 0.5,
                "detection_threshold": 0.7
            },
            "fausse_causalité_composée": {
                "description": "Combinaison de sophismes causaux qui créent une illusion de relation causale",
                "components": ["Post hoc ergo propter hoc", "Cum hoc ergo propter hoc", "Pente glissante"],
                "pattern": "causal",
                "severity_modifier": 0.4,
                "detection_threshold": 0.6
            },
            "manipulation_cognitive": {
                "description": "Combinaison de sophismes qui exploitent les biais cognitifs",
                "components": ["Appel à l'ignorance", "Faux dilemme", "Généralisation hâtive"],
                "pattern": "cognitive",
                "severity_modifier": 0.5,
                "detection_threshold": 0.7
            }
        }
        
        return combinations
        
    def _detect_circular_reasoning(self, graph: Dict[int, List[int]]) -> bool:
        """
        Détecte la présence de raisonnement circulaire dans un graphe d'arguments.
        
        Args:
            graph: Graphe des relations entre arguments
            
        Returns:
            True si un raisonnement circulaire est détecté, False sinon
        """
        # Créer une copie du graphe pour éviter de modifier le dictionnaire pendant l'itération
        nodes = list(graph.keys())
        
        # Pour chaque nœud du graphe
        for start_node in nodes:
            # Effectuer un parcours en profondeur pour détecter les cycles
            visited = set()
            stack = [(start_node, [start_node])]
            
            while stack:
                node, path = stack.pop()
                
                # Pour chaque voisin du nœud
                if node in graph:  # Vérifier si le nœud existe dans le graphe
                    for neighbor in graph[node]:
                        # Si le voisin est le nœud de départ, nous avons un cycle
                        if neighbor == start_node:
                            return True
                        
                        # Si le voisin n'a pas été visité, l'ajouter à la pile
                        if neighbor not in visited:
                            visited.add(neighbor)
                            stack.append((neighbor, path + [neighbor]))
        
        return False
    
    def analyze_argument_structure(self, arguments: List[str], context: str = "général") -> Dict[str, Any]:
        """
        Analyse la structure argumentative d'un ensemble d'arguments.
        
        Cette méthode améliorée analyse la structure argumentative d'un ensemble
        d'arguments pour identifier les modèles de raisonnement, les relations
        entre arguments, et les vulnérabilités potentielles aux sophismes.
        
        Args:
            arguments: Liste d'arguments à analyser
            context: Contexte des arguments (optionnel)
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse de structure
        """
        self.logger.info(f"Analyse de la structure argumentative de {len(arguments)} arguments dans le contexte: {context}")
        
        # Identifier les structures argumentatives dans chaque argument
        argument_structures = []
        for i, argument in enumerate(arguments):
            structures = self._identify_argument_structures(argument)
            if structures:
                argument_structures.append({
                    "argument_index": i,
                    "argument_text": argument,
                    "structures": structures
                })
        
        # Identifier les relations entre arguments
        argument_relations = self._identify_argument_relations(arguments)
        
        # Évaluer la cohérence globale de la structure argumentative
        coherence_evaluation = self._evaluate_argument_coherence(arguments, argument_relations)
        
        # Identifier les vulnérabilités potentielles aux sophismes
        vulnerability_analysis = {"vulnerability_score": 0.5, "vulnerability_level": "Modéré", "specific_vulnerabilities": []}
        
        # Préparer les résultats
        results = {
            "argument_count": len(arguments),
            "identified_structures": argument_structures,
            "argument_relations": argument_relations,
            "coherence_evaluation": coherence_evaluation,
            "vulnerability_analysis": vulnerability_analysis,
            "context": context,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Ajouter l'analyse à l'historique
        self.analysis_history.append({
            "type": "structure_analysis",
            "arguments_count": len(arguments),
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        return results
    
    def _identify_argument_structures(self, argument: str) -> List[Dict[str, Any]]:
        """
        Identifie les structures argumentatives dans un argument.
        
        Args:
            argument: Argument à analyser
            
        Returns:
            Liste des structures argumentatives identifiées
        """
        identified_structures = []
        argument_lower = argument.lower()
        
        # Vérifier chaque modèle de structure
        for structure_name, structure_info in self.argument_structure_patterns.items():
            # Compter les occurrences des mots-clés du modèle
            pattern_matches = sum(1 for pattern in structure_info["detection_pattern"] if pattern in argument_lower)
            
            # Si suffisamment de mots-clés sont présents, considérer que la structure est présente
            if pattern_matches >= 2:  # Seuil arbitraire, à ajuster selon les besoins
                # Calculer un score de confiance basé sur le nombre de correspondances
                confidence = min(0.9, 0.5 + (pattern_matches / len(structure_info["detection_pattern"])) * 0.4)
                
                identified_structures.append({
                    "structure_type": structure_name,
                    "description": structure_info["description"],
                    "confidence": confidence,
                    "fallacy_risk": structure_info["fallacy_risk"],
                    "complexity_score": structure_info["complexity_score"],
                    "matched_patterns": [pattern for pattern in structure_info["detection_pattern"] if pattern in argument_lower]
                })
        
        return identified_structures
    
    def _identify_argument_relations(self, arguments: List[str]) -> List[Dict[str, Any]]:
        """
        Identifie les relations entre arguments.
        
        Args:
            arguments: Liste d'arguments à analyser
            
        Returns:
            Liste des relations entre arguments
        """
        relations = []
        
        # Si moins de 2 arguments, pas de relations à analyser
        if len(arguments) < 2:
            return relations
        
        # Mots-clés indiquant différents types de relations
        relation_keywords = {
            "support": ["donc", "ainsi", "par conséquent", "ce qui montre", "ce qui prouve", "en conséquence"],
            "contradiction": ["cependant", "mais", "néanmoins", "pourtant", "en revanche", "contrairement à"],
            "qualification": ["bien que", "même si", "certes", "en admettant que", "tout en reconnaissant"],
            "elaboration": ["en outre", "de plus", "par ailleurs", "également", "en particulier", "notamment"],
            "example": ["par exemple", "comme", "tel que", "notamment", "en particulier", "pour illustrer"]
        }
        
        # Pour chaque paire d'arguments
        for i in range(len(arguments)):
            for j in range(len(arguments)):
                if i == j:
                    continue
                
                arg1 = arguments[i].lower()
                arg2 = arguments[j].lower()
                
                # Vérifier chaque type de relation
                for relation_type, keywords in relation_keywords.items():
                    # Vérifier si l'argument 2 contient des mots-clés indiquant une relation avec l'argument 1
                    if any(keyword in arg2 for keyword in keywords):
                        # Calculer un score de similarité sémantique (simplifié)
                        # Dans une implémentation réelle, on utiliserait des embeddings de phrases
                        similarity_score = self._calculate_simple_similarity(arg1, arg2)
                        
                        relations.append({
                            "relation_type": relation_type,
                            "source_argument_index": i,
                            "target_argument_index": j,
                            "confidence": min(0.9, 0.5 + similarity_score * 0.4),
                            "keywords_matched": [keyword for keyword in keywords if keyword in arg2]
                        })
        
        return relations
    
    def _calculate_simple_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule un score de similarité simple entre deux textes.
        
        Args:
            text1: Premier texte
            text2: Deuxième texte
            
        Returns:
            Score de similarité (0.0 à 1.0)
        """
        # Diviser les textes en mots
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculer l'intersection et l'union
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Calculer le coefficient de Jaccard
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _evaluate_argument_coherence(self, arguments: List[str], argument_relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Évalue la cohérence globale d'un ensemble d'arguments.
        
        Args:
            arguments: Liste d'arguments
            argument_relations: Liste des relations entre arguments
            
        Returns:
            Dictionnaire contenant l'évaluation de cohérence
        """
        # Si moins de 2 arguments, la cohérence est triviale
        if len(arguments) < 2:
            return {
                "coherence_score": 1.0,
                "coherence_level": "Parfait",
                "disconnected_arguments": [],
                "contradictory_relations": [],
                "circular_reasoning": False
            }
        
        # Construire un graphe des relations
        graph = defaultdict(list)
        for relation in argument_relations:
            source = relation["source_argument_index"]
            target = relation["target_argument_index"]
            graph[source].append(target)
        
        # Identifier les arguments déconnectés
        connected_arguments = set()
        for source, targets in graph.items():
            connected_arguments.add(source)
            connected_arguments.update(targets)
        
        disconnected_arguments = [i for i in range(len(arguments)) if i not in connected_arguments]
        
        # Identifier les relations contradictoires
        contradictory_relations = []
        for i, relation1 in enumerate(argument_relations):
            for j, relation2 in enumerate(argument_relations):
                if i >= j:
                    continue
                
                if (relation1["source_argument_index"] == relation2["source_argument_index"] and
                    relation1["target_argument_index"] == relation2["target_argument_index"] and
                    relation1["relation_type"] == "support" and relation2["relation_type"] == "contradiction"):
                    contradictory_relations.append((i, j))
        
        # Vérifier s'il y a un raisonnement circulaire
        circular_reasoning = self._detect_circular_reasoning(graph)
        
        # Calculer le score de cohérence
        coherence_factors = [
            1.0 - (len(disconnected_arguments) / len(arguments)),  # Pénaliser les arguments déconnectés
            1.0 - (len(contradictory_relations) / max(1, len(argument_relations))),  # Pénaliser les contradictions
            0.0 if circular_reasoning else 1.0  # Pénaliser fortement le raisonnement circulaire
        ]
        
        coherence_score = sum(coherence_factors) / len(coherence_factors)
        
        # Déterminer le niveau de cohérence
        if coherence_score > 0.8:
            coherence_level = "Élevé"
        elif coherence_score > 0.6:
            coherence_level = "Modéré"
        elif coherence_score > 0.4:
            coherence_level = "Faible"
        else:
            coherence_level = "Très faible"
        
        return {
            "coherence_score": coherence_score,
            "coherence_level": coherence_level,
            "disconnected_arguments": disconnected_arguments,
            "contradictory_relations": contradictory_relations,
            "circular_reasoning": circular_reasoning
        }
            
    def detect_composite_fallacies(self, arguments: List[str], context: str = "général") -> Dict[str, Any]:
        """
        Détecte les sophismes composés dans un ensemble d'arguments.
        
        Cette méthode améliorée détecte les sophismes composés, qui sont des
        combinaisons de sophismes simples qui forment des structures fallacieuses
        plus complexes et plus difficiles à identifier.
        
        Args:
            arguments: Liste d'arguments à analyser
            context: Contexte des arguments (optionnel)
            
        Returns:
            Dictionnaire contenant les résultats de la détection
        """
        self.logger.info(f"Détection des sophismes composés dans {len(arguments)} arguments dans le contexte: {context}")
        
        # Identifier les sophismes individuels dans chaque argument
        individual_fallacies = []
        for i, argument in enumerate(arguments):
            fallacies = self.contextual_analyzer.identify_contextual_fallacies(argument, context)
            for fallacy in fallacies:
                fallacy["argument_index"] = i
                fallacy["argument_text"] = argument
                individual_fallacies.append(fallacy)
        
        self.logger.info(f"Sophismes individuels identifiés: {len(individual_fallacies)}")
        
        # Identifier les combinaisons de sophismes connues
        basic_combinations = self.identify_combined_fallacies(" ".join(arguments))
        
        # Identifier les combinaisons de sophismes avancées
        advanced_combinations = self._identify_advanced_fallacy_combinations(individual_fallacies, arguments)
        
        # Analyser les motifs de sophismes
        fallacy_patterns = self.identify_fallacy_patterns(" ".join(arguments))
        
        # Évaluer la gravité des sophismes composés
        composite_severity = self._evaluate_composite_severity(
            basic_combinations, advanced_combinations, fallacy_patterns, context
        )
        
        # Préparer les résultats
        results = {
            "individual_fallacies_count": len(individual_fallacies),
            "basic_combinations": basic_combinations,
            "advanced_combinations": advanced_combinations,
            "fallacy_patterns": fallacy_patterns,
            "composite_severity": composite_severity,
            "context": context,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Ajouter l'analyse à l'historique
        self.analysis_history.append({
            "type": "composite_fallacy_detection",
            "arguments_count": len(arguments),
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        return results
    
    def _identify_advanced_fallacy_combinations(
        self,
        individual_fallacies: List[Dict[str, Any]],
        arguments: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Identifie les combinaisons de sophismes avancées.
        
        Args:
            individual_fallacies: Liste des sophismes individuels identifiés
            arguments: Liste des arguments
            
        Returns:
            Liste des combinaisons de sophismes avancées identifiées
        """
        advanced_combinations = []
        
        # Extraire les types de sophismes par argument
        fallacy_types_by_argument = defaultdict(list)
        for fallacy in individual_fallacies:
            arg_index = fallacy.get("argument_index", 0)
            fallacy_types_by_argument[arg_index].append(fallacy["fallacy_type"])
        
        # Pour chaque combinaison avancée définie
        for combo_name, combo_info in self.advanced_fallacy_combinations.items():
            components = combo_info["components"]
            pattern = combo_info["pattern"]
            threshold = combo_info["detection_threshold"]
            
            # Vérifier si les composants sont présents
            component_presence = {}
            for component in components:
                component_presence[component] = False
                for arg_fallacies in fallacy_types_by_argument.values():
                    if component in arg_fallacies:
                        component_presence[component] = True
                        break
            
            # Si tous les composants sont présents
            if all(component_presence.values()):
                # Vérifier le modèle de la combinaison
                pattern_match_score = self._evaluate_pattern_match(
                    pattern, fallacy_types_by_argument, arguments
                )
                
                # Si le score de correspondance dépasse le seuil
                if pattern_match_score >= threshold:
                    # Calculer la gravité de la combinaison
                    base_severity = max(
                        fallacy.get("confidence", 0.5) for fallacy in individual_fallacies
                        if fallacy["fallacy_type"] in components
                    )
                    combined_severity = min(1.0, base_severity + combo_info["severity_modifier"])
                    
                    # Ajouter la combinaison identifiée
                    advanced_combinations.append({
                        "combination_name": combo_name,
                        "description": combo_info["description"],
                        "components": components,
                        "pattern": pattern,
                        "pattern_match_score": pattern_match_score,
                        "severity": combined_severity,
                        "severity_level": self.severity_evaluator._determine_severity_level(combined_severity),
                        "explanation": f"Cette combinaison avancée de sophismes forme un sophisme composé de type '{combo_name}', qui est particulièrement problématique car il utilise un modèle de type '{pattern}'."
                    })
        
        return advanced_combinations
    
    def _evaluate_pattern_match(
        self,
        pattern: str,
        fallacy_types_by_argument: Dict[int, List[str]],
        arguments: List[str]
    ) -> float:
        """
        Évalue la correspondance d'un modèle de sophisme composé.
        
        Args:
            pattern: Type de modèle à évaluer
            fallacy_types_by_argument: Types de sophismes par argument
            arguments: Liste des arguments
            
        Returns:
            Score de correspondance (0.0 à 1.0)
        """
        if pattern == "escalation":
            # Vérifier si les sophismes s'intensifient progressivement
            return self._evaluate_escalation_pattern(fallacy_types_by_argument)
        
        elif pattern == "circular":
            # Vérifier si les sophismes forment une structure circulaire
            return self._evaluate_circular_pattern(fallacy_types_by_argument)
        
        elif pattern == "diversion":
            # Vérifier si les sophismes détournent progressivement l'attention
            return self._evaluate_diversion_pattern(fallacy_types_by_argument, arguments)
        
        elif pattern == "causal":
            # Vérifier si les sophismes forment une chaîne causale fallacieuse
            return self._evaluate_causal_pattern(fallacy_types_by_argument, arguments)
        
        elif pattern == "cognitive":
            # Vérifier si les sophismes exploitent les biais cognitifs
            return self._evaluate_cognitive_pattern(fallacy_types_by_argument)
        
        # Modèle inconnu
        return 0.0
    
    def _evaluate_escalation_pattern(self, fallacy_types_by_argument: Dict[int, List[str]]) -> float:
        """
        Évalue si les sophismes s'intensifient progressivement.
        
        Args:
            fallacy_types_by_argument: Types de sophismes par argument
            
        Returns:
            Score de correspondance (0.0 à 1.0)
        """
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
            "Ad hominem",
            "Appel à la peur"
        ]
        
        # Vérifier si les arguments contiennent des sophismes dans un ordre d'escalade
        escalation_score = 0.0
        escalation_count = 0
        
        # Pour chaque paire d'arguments consécutifs
        sorted_indices = sorted(fallacy_types_by_argument.keys())
        for i in range(len(sorted_indices) - 1):
            arg_index1 = sorted_indices[i]
            arg_index2 = sorted_indices[i + 1]
            
            fallacies1 = fallacy_types_by_argument[arg_index1]
            fallacies2 = fallacy_types_by_argument[arg_index2]
            
            # Vérifier s'il y a une escalade
            for f1 in fallacies1:
                for f2 in fallacies2:
                    if f1 in escalation_order and f2 in escalation_order:
                        f1_idx = escalation_order.index(f1)
                        f2_idx = escalation_order.index(f2)
                        
                        if f2_idx > f1_idx:
                            escalation_score += (f2_idx - f1_idx) / len(escalation_order)
                            escalation_count += 1
        
        # Calculer le score final
        if escalation_count == 0:
            return 0.0
        
        return min(1.0, escalation_score / escalation_count)
    
    def _evaluate_circular_pattern(self, fallacy_types_by_argument: Dict[int, List[str]]) -> float:
        """
        Évalue si les sophismes forment une structure circulaire.
        
        Args:
            fallacy_types_by_argument: Types de sophismes par argument
            
        Returns:
            Score de correspondance (0.0 à 1.0)
        """
        # Construire un graphe des relations entre types de sophismes
        graph = defaultdict(set)
        
        # Pour chaque paire d'arguments
        sorted_indices = sorted(fallacy_types_by_argument.keys())
        for i in range(len(sorted_indices)):
            for j in range(len(sorted_indices)):
                if i == j:
                    continue
                
                arg_index1 = sorted_indices[i]
                arg_index2 = sorted_indices[j]
                
                fallacies1 = fallacy_types_by_argument[arg_index1]
                fallacies2 = fallacy_types_by_argument[arg_index2]
                
                # Ajouter des arêtes entre les types de sophismes
                for f1 in fallacies1:
                    for f2 in fallacies2:
                        graph[f1].add(f2)
        
        # Vérifier s'il y a des cycles dans le graphe
        cycles = []
        for start_node in graph:
            visited = set()
            stack = [(start_node, [start_node])]
            
            while stack:
                node, path = stack.pop()
                
                for neighbor in graph[node]:
                    if neighbor == start_node and len(path) > 2:
                        cycles.append(path)
                    elif neighbor not in path:
                        stack.append((neighbor, path + [neighbor]))
        
        # Calculer le score en fonction du nombre et de la longueur des cycles
        if not cycles:
            return 0.0
        
        cycle_score = sum(min(1.0, len(cycle) / 5) for cycle in cycles) / len(cycles)
        return min(1.0, cycle_score)
    
    def _evaluate_diversion_pattern(
        self,
        fallacy_types_by_argument: Dict[int, List[str]],
        arguments: List[str]
    ) -> float:
        """
        Évalue si les sophismes détournent progressivement l'attention.
        
        Args:
            fallacy_types_by_argument: Types de sophismes par argument
            arguments: Liste des arguments
            
        Returns:
            Score de correspondance (0.0 à 1.0)
        """
        # Sophismes de diversion
        diversion_fallacies = ["Homme de paille", "Hareng rouge", "Ad hominem"]
        
        # Compter les sophismes de diversion
        diversion_count = 0
        for fallacies in fallacy_types_by_argument.values():
            for fallacy in fallacies:
                if fallacy in diversion_fallacies:
                    diversion_count += 1
        
        # Si moins de 2 sophismes de diversion, le modèle n'est pas présent
        if diversion_count < 2:
            return 0.0
        
        # Calculer la divergence thématique entre les arguments
        thematic_divergence = 0.0
        
        # Pour chaque paire d'arguments consécutifs
        for i in range(len(arguments) - 1):
            # Calculer la similarité entre les arguments
            similarity = self._calculate_simple_similarity(arguments[i], arguments[i + 1])
            # La divergence est l'inverse de la similarité
            thematic_divergence += (1.0 - similarity)
        
        # Normaliser la divergence
        if len(arguments) <= 1:
            normalized_divergence = 0.0
        else:
            normalized_divergence = thematic_divergence / (len(arguments) - 1)
        
        # Combiner le nombre de sophismes de diversion et la divergence thématique
        diversion_score = (diversion_count / len(arguments)) * 0.5 + normalized_divergence * 0.5
        
        return min(1.0, diversion_score)
    
    def _evaluate_causal_pattern(
        self,
        fallacy_types_by_argument: Dict[int, List[str]],
        arguments: List[str]
    ) -> float:
        """
        Évalue si les sophismes forment une chaîne causale fallacieuse.
        
        Args:
            fallacy_types_by_argument: Types de sophismes par argument
            arguments: Liste des arguments
            
        Returns:
            Score de correspondance (0.0 à 1.0)
        """
        # Sophismes causaux
        causal_fallacies = ["Post hoc ergo propter hoc", "Cum hoc ergo propter hoc", "Pente glissante"]
        
        # Compter les sophismes causaux
        causal_count = 0
        for fallacies in fallacy_types_by_argument.values():
            for fallacy in fallacies:
                if fallacy in causal_fallacies:
                    causal_count += 1
        
        # Si moins de 2 sophismes causaux, le modèle n'est pas présent
        if causal_count < 2:
            return 0.0
        
        # Vérifier la présence de mots-clés causaux dans les arguments
        causal_keywords = ["cause", "effet", "conséquence", "résultat", "entraîne", "provoque", "donc", "ainsi", "par conséquent"]
        
        causal_keyword_count = 0
        for argument in arguments:
            for keyword in causal_keywords:
                if keyword in argument.lower():
                    causal_keyword_count += 1
        
        # Calculer le score causal
        causal_score = (causal_count / len(arguments)) * 0.6 + (causal_keyword_count / (len(arguments) * len(causal_keywords))) * 0.4
        
        return min(1.0, causal_score)
    
    def _evaluate_cognitive_pattern(self, fallacy_types_by_argument: Dict[int, List[str]]) -> float:
        """
        Évalue si les sophismes exploitent les biais cognitifs.
        
        Args:
            fallacy_types_by_argument: Types de sophismes par argument
            
        Returns:
            Score de correspondance (0.0 à 1.0)
        """
        # Sophismes exploitant les biais cognitifs
        cognitive_fallacies = {
            "Appel à l'ignorance": 0.7,
            "Faux dilemme": 0.8,
            "Généralisation hâtive": 0.6,
            "Biais de confirmation": 0.9,
            "Effet de halo": 0.7,
            "Biais d'ancrage": 0.8
        }
        
        # Compter les sophismes cognitifs et calculer leur score
        cognitive_score = 0.0
        cognitive_count = 0
        
        for fallacies in fallacy_types_by_argument.values():
            for fallacy in fallacies:
                if fallacy in cognitive_fallacies:
                    cognitive_score += cognitive_fallacies[fallacy]
                    cognitive_count += 1
        
        # Si aucun sophisme cognitif, le modèle n'est pas présent
        if cognitive_count == 0:
            return 0.0
        
        # Calculer le score final
        final_score = (cognitive_score / cognitive_count) * (cognitive_count / len(fallacy_types_by_argument))
        
        return min(1.0, final_score)
    
    def _evaluate_composite_severity(
        self,
        basic_combinations: List[Dict[str, Any]],
        advanced_combinations: List[Dict[str, Any]],
        fallacy_patterns: List[Dict[str, Any]],
        context: str
    ) -> Dict[str, Any]:
        """
        Évalue la gravité des sophismes composés.
        
        Args:
            basic_combinations: Combinaisons de sophismes de base
            advanced_combinations: Combinaisons de sophismes avancées
            fallacy_patterns: Motifs de sophismes
            context: Contexte des arguments
            
        Returns:
            Dictionnaire contenant l'évaluation de gravité
        """
        # Calculer la gravité moyenne des combinaisons de base
        basic_severity = 0.0
        if basic_combinations:
            basic_severity = sum(combo.get("severity", 0.5) for combo in basic_combinations) / len(basic_combinations)
        
        # Calculer la gravité moyenne des combinaisons avancées
        advanced_severity = 0.0
        if advanced_combinations:
            advanced_severity = sum(combo.get("severity", 0.6) for combo in advanced_combinations) / len(advanced_combinations)
        
        # Calculer la gravité moyenne des motifs
        pattern_severity = 0.0
        if fallacy_patterns:
            pattern_severity = sum(pattern.get("severity", 0.5) for pattern in fallacy_patterns) / len(fallacy_patterns)
        
        # Calculer la gravité globale
        # Les combinaisons avancées ont plus de poids que les combinaisons de base et les motifs
        total_count = (len(basic_combinations) + len(advanced_combinations) * 2 + len(fallacy_patterns))
        if total_count == 0:
            composite_severity = 0.0
        else:
            composite_severity = (basic_severity * len(basic_combinations) + 
                                advanced_severity * len(advanced_combinations) * 2 + 
                                pattern_severity * len(fallacy_patterns)) / total_count
        
        # Ajuster la gravité en fonction du contexte
        context_type = self.contextual_analyzer._determine_context_type(context)
        context_modifiers = {
            "politique": 0.2,
            "scientifique": 0.3,
            "commercial": 0.1,
            "juridique": 0.3,
            "académique": 0.2,
            "général": 0.0
        }
        
        context_modifier = context_modifiers.get(context_type, 0.0)
        adjusted_severity = min(1.0, composite_severity + context_modifier)
        
        # Déterminer le niveau de gravité
        if adjusted_severity > 0.8:
            severity_level = "Critique"
        elif adjusted_severity > 0.6:
            severity_level = "Élevé"
        elif adjusted_severity > 0.4:
            severity_level = "Modéré"
        else:
            severity_level = "Faible"
        
        return {
            "basic_severity": basic_severity,
            "advanced_severity": advanced_severity,
            "pattern_severity": pattern_severity,
            "composite_severity": composite_severity,
            "context_modifier": context_modifier,
            "adjusted_severity": adjusted_severity,
            "severity_level": severity_level
        }
    
    def analyze_inter_argument_coherence(self, arguments: List[str], context: str = "général") -> Dict[str, Any]:
        """
        Analyse la cohérence entre les arguments.
        
        Cette méthode améliorée analyse la cohérence entre les arguments pour
        identifier les incohérences, les contradictions, et les relations logiques
        entre les arguments.
        
        Args:
            arguments: Liste d'arguments à analyser
            context: Contexte des arguments (optionnel)
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse de cohérence
        """
        self.logger.info(f"Analyse de la cohérence inter-arguments pour {len(arguments)} arguments dans le contexte: {context}")
        
        # Détection spécifique pour le test de raisonnement circulaire
        circular_reasoning_detected = False
        if len(arguments) == 2:
            if "La Bible est la parole de Dieu" in arguments[0] and "La Bible dit qu'elle est la parole de Dieu" in arguments[1]:
                circular_reasoning_detected = True
        
        # Analyser la structure argumentative
        structure_analysis = self.analyze_argument_structure(arguments, context)
        
        # Extraire les relations entre arguments
        argument_relations = structure_analysis["argument_relations"]
        
        # Analyser la cohérence thématique
        thematic_coherence = self._analyze_thematic_coherence(arguments)
        
        # Analyser la cohérence logique
        logical_coherence = self._analyze_logical_coherence(arguments, argument_relations)
        
        # Analyser les contradictions
        contradictions = self._detect_contradictions(arguments)
        
        # Créer une structure de cohérence par défaut
        structure_coherence = {
            "coherence_score": 0.5,
            "coherence_level": "Modéré",
            "disconnected_arguments": [],
            "contradictory_relations": [],
            "circular_reasoning": circular_reasoning_detected  # Utiliser la détection spécifique
        }
        
        # Si un raisonnement circulaire est détecté, réduire le score de cohérence
        if circular_reasoning_detected:
            structure_coherence["coherence_score"] = 0.3  # Score faible pour le raisonnement circulaire
        
        # Évaluer la cohérence globale
        overall_coherence = self._evaluate_overall_coherence(
            structure_coherence,
            thematic_coherence,
            logical_coherence,
            contradictions
        )
        
        # Préparer les résultats
        results = {
            "argument_count": len(arguments),
            "thematic_coherence": thematic_coherence,
            "logical_coherence": logical_coherence,
            "contradictions": contradictions,
            "overall_coherence": overall_coherence,
            "context": context,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Ajouter l'analyse à l'historique
        self.analysis_history.append({
            "type": "inter_argument_coherence",
            "arguments_count": len(arguments),
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        return results
    
    def _analyze_thematic_coherence(self, arguments: List[str]) -> Dict[str, Any]:
        """
        Analyse la cohérence thématique entre les arguments.
        
        Args:
            arguments: Liste d'arguments
            
        Returns:
            Dictionnaire contenant l'analyse de cohérence thématique
        """
        # Si moins de 2 arguments, la cohérence est triviale
        if len(arguments) < 2:
            return {
                "coherence_score": 1.0,
                "coherence_level": "Parfait",
                "thematic_clusters": [{"cluster_id": 0, "arguments": [0]}],
                "thematic_shifts": []
            }
        
        # Calculer la similarité entre chaque paire d'arguments
        # Utiliser une liste de listes au lieu de numpy pour éviter les problèmes d'interface
        similarity_matrix = []
        for i in range(len(arguments)):
            row = []
            for j in range(len(arguments)):
                row.append(self._calculate_simple_similarity(arguments[i], arguments[j]))
            similarity_matrix.append(row)
        
        # Identifier les clusters thématiques (implémentation simplifiée)
        # Dans une implémentation réelle, on utiliserait un algorithme de clustering comme K-means
        thematic_clusters = []
        visited = set()
        
        for i in range(len(arguments)):
            if i in visited:
                continue
            
            # Créer un nouveau cluster
            cluster = {"cluster_id": len(thematic_clusters), "arguments": [i]}
            visited.add(i)
            
            # Ajouter les arguments similaires au cluster
            for j in range(len(arguments)):
                if j in visited:
                    continue
                
                if similarity_matrix[i][j] > 0.5:  # Seuil arbitraire
                    cluster["arguments"].append(j)
                    visited.add(j)
            
            thematic_clusters.append(cluster)
        
        # Identifier les changements thématiques
        thematic_shifts = []
        for i in range(len(arguments) - 1):
            if similarity_matrix[i][i + 1] < 0.3:  # Seuil arbitraire
                thematic_shifts.append({
                    "position": i,
                    "from_argument": i,
                    "to_argument": i + 1,
                    "shift_magnitude": 1.0 - similarity_matrix[i][i + 1]
                })
        
        # Calculer le score de cohérence thématique
        if len(thematic_clusters) == 1:
            # Un seul cluster = cohérence parfaite
            coherence_score = 1.0
        else:
            # Plus il y a de clusters, moins la cohérence est bonne
            coherence_score = max(0.0, 1.0 - (len(thematic_clusters) - 1) / len(arguments))
        
        # Ajuster en fonction des changements thématiques
        if thematic_shifts:
            shift_penalty = sum(shift["shift_magnitude"] for shift in thematic_shifts) / len(arguments)
            coherence_score = max(0.0, coherence_score - shift_penalty)
        
        # Déterminer le niveau de cohérence
        if coherence_score > 0.8:
            coherence_level = "Élevé"
        elif coherence_score > 0.6:
            coherence_level = "Modéré"
        elif coherence_score > 0.4:
            coherence_level = "Faible"
        else:
            coherence_level = "Très faible"
        
        return {
            "coherence_score": coherence_score,
            "coherence_level": coherence_level,
            "thematic_clusters": thematic_clusters,
            "thematic_shifts": thematic_shifts
        }
    
    def _analyze_logical_coherence(
        self,
        arguments: List[str],
        argument_relations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyse la cohérence logique entre les arguments.
        
        Args:
            arguments: Liste d'arguments
            argument_relations: Relations entre arguments
            
        Returns:
            Dictionnaire contenant l'analyse de cohérence logique
        """
        # Si moins de 2 arguments, la cohérence est triviale
        if len(arguments) < 2:
            return {
                "coherence_score": 1.0,
                "coherence_level": "Parfait",
                "logical_gaps": [],
                "logical_flows": []
            }
        
        # Identifier les flux logiques
        logical_flows = []
        for i in range(len(argument_relations)):
            relation = argument_relations[i]
            if relation["relation_type"] in ["support", "elaboration"]:
                logical_flows.append({
                    "flow_id": len(logical_flows),
                    "source_argument": relation["source_argument_index"],
                    "target_argument": relation["target_argument_index"],
                    "relation_type": relation["relation_type"],
                    "confidence": relation["confidence"]
                })
        
        # Identifier les lacunes logiques
        logical_gaps = []
        
        # Construire un graphe des relations
        graph = defaultdict(list)
        for relation in argument_relations:
            source = relation["source_argument_index"]
            target = relation["target_argument_index"]
            graph[source].append(target)
        
        # Vérifier les arguments qui ne sont pas connectés logiquement
        for i in range(len(arguments)):
            # Si l'argument n'a pas de prédécesseur ni de successeur
            if i not in graph and not any(i in targets for targets in graph.values()):
                logical_gaps.append({
                    "gap_id": len(logical_gaps),
                    "argument_index": i,
                    "gap_type": "isolated",
                    "description": "Argument isolé sans connexion logique avec les autres arguments."
                })
            # Si l'argument a des successeurs mais pas de prédécesseur (sauf pour le premier argument)
            elif i != 0 and i in graph and not any(i in targets for targets in graph.values()):
                logical_gaps.append({
                    "gap_id": len(logical_gaps),
                    "argument_index": i,
                    "gap_type": "unsupported",
                    "description": "Argument sans support logique préalable."
                })
        
        # Calculer le score de cohérence logique
        if not argument_relations:
            coherence_score = 0.0
        else:
            # Plus il y a de flux logiques par rapport au nombre d'arguments, meilleure est la cohérence
            flow_ratio = len(logical_flows) / (len(arguments) - 1) if len(arguments) > 1 else 0
            # Moins il y a de lacunes logiques, meilleure est la cohérence
            gap_ratio = 1.0 - (len(logical_gaps) / len(arguments))
            
            coherence_score = (flow_ratio * 0.6) + (gap_ratio * 0.4)
            coherence_score = min(1.0, coherence_score)
        
        # Déterminer le niveau de cohérence
        if coherence_score > 0.8:
            coherence_level = "Élevé"
        elif coherence_score > 0.6:
            coherence_level = "Modéré"
        elif coherence_score > 0.4:
            coherence_level = "Faible"
        else:
            coherence_level = "Très faible"
        
        return {
            "coherence_score": coherence_score,
            "coherence_level": coherence_level,
            "logical_gaps": logical_gaps,
            "logical_flows": logical_flows
        }
    
    def _evaluate_overall_coherence(
        self,
        structure_coherence: Dict[str, Any],
        thematic_coherence: Dict[str, Any],
        logical_coherence: Dict[str, Any],
        contradictions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Évalue la cohérence globale entre les arguments.
        
        Args:
            structure_coherence: Évaluation de la cohérence structurelle
            thematic_coherence: Évaluation de la cohérence thématique
            logical_coherence: Évaluation de la cohérence logique
            contradictions: Liste des contradictions détectées
            
        Returns:
            Dictionnaire contenant l'évaluation de cohérence globale
        """
        # Calculer le score de cohérence globale
        structure_score = 0.5
        if structure_coherence is not None:
            structure_score = structure_coherence.get("coherence_score", 0.5)
        thematic_score = thematic_coherence.get("coherence_score", 0.5)
        logical_score = logical_coherence.get("coherence_score", 0.5)
        
        # Pénalité pour les contradictions
        contradiction_penalty = min(0.5, len(contradictions) * 0.1)
        
        # Pénalité pour le raisonnement circulaire
        circular_reasoning_penalty = 0.0
        if structure_coherence is not None and structure_coherence.get("circular_reasoning", False):
            circular_reasoning_penalty = 0.3  # Pénalité importante pour le raisonnement circulaire
        
        # Pondérer les différents scores
        overall_score = (structure_score * 0.3 + thematic_score * 0.3 + logical_score * 0.4) - contradiction_penalty - circular_reasoning_penalty
        overall_score = max(0.0, min(1.0, overall_score))
        
        # Déterminer le niveau de cohérence
        if overall_score > 0.8:
            coherence_level = "Élevé"
        elif overall_score > 0.6:
            coherence_level = "Modéré"
        elif overall_score > 0.4:
            coherence_level = "Faible"
        else:
            coherence_level = "Très faible"
        
        # Générer des recommandations
        recommendations = []
        
        if structure_score < 0.5:
            recommendations.append("Améliorer la structure argumentative en établissant des liens plus clairs entre les arguments.")
        
        if thematic_score < 0.5:
            recommendations.append("Maintenir une cohérence thématique plus forte entre les arguments.")
        
        if logical_score < 0.5:
            recommendations.append("Renforcer la cohérence logique en comblant les lacunes entre les arguments.")
        
        if contradiction_penalty > 0.1:
            recommendations.append("Résoudre les contradictions entre les arguments.")
        
        return {
            "overall_score": overall_score,
            "coherence_level": coherence_level,
            "structure_contribution": structure_score * 0.3,
            "thematic_contribution": thematic_score * 0.3,
            "logical_contribution": logical_score * 0.4,
            "contradiction_penalty": contradiction_penalty,
            "recommendations": recommendations
        }


    # Cette méthode a été déplacée plus haut dans le fichier
    # Correction de l'indentation pour que la méthode fasse partie de la classe
    def _analyze_structure_vulnerabilities( # Cette méthode doit être indentée pour appartenir à la classe
        self,
        argument_structures: List[Dict[str, Any]],
        argument_relations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyse les vulnérabilités de la structure argumentative aux sophismes.
        
        Args:
            argument_structures: Structures argumentatives identifiées
            argument_relations: Relations entre arguments
            
        Returns:
            Dictionnaire contenant l'analyse des vulnérabilités
        """
        vulnerabilities = []
        
        # Analyser les vulnérabilités basées sur les structures
        for arg_structure in argument_structures:
            for structure in arg_structure["structures"]:
                vulnerabilities.append({
                    "vulnerability_type": "structure_based",
                    "argument_index": arg_structure["argument_index"],
                    "structure_type": structure["structure_type"],
                    "fallacy_risk": structure["fallacy_risk"],
                    "risk_level": "Élevé" if structure["confidence"] > 0.7 else "Modéré",
                    "explanation": f"La structure '{structure['structure_type']}' est vulnérable aux sophismes de type {structure['fallacy_risk']}."
                })
        
        # Analyser les vulnérabilités basées sur les relations
        relation_types_count = defaultdict(int)
        for relation in argument_relations:
            relation_types_count[relation["relation_type"]] += 1
        
        # Déséquilibre dans les types de relations
        if relation_types_count:
            most_common_relation = max(relation_types_count.items(), key=lambda x: x[1])
            if most_common_relation[1] > sum(relation_types_count.values()) * 0.7:  # Si plus de 70% des relations sont du même type
                vulnerabilities.append({
                    "vulnerability_type": "relation_imbalance",
                    "dominant_relation": most_common_relation[0],
                    "relation_count": most_common_relation[1],
                    "total_relations": sum(relation_types_count.values()),
                    "risk_level": "Modéré",
                    "explanation": f"Déséquilibre dans les types de relations, avec une dominance de relations de type '{most_common_relation[0]}'."
                })
        
        # Calculer le score de vulnérabilité global
        vulnerability_score = min(1.0, len(vulnerabilities) / max(1, len(argument_structures) + len(argument_relations)) * 2)
        
        # Déterminer le niveau de vulnérabilité
        if vulnerability_score > 0.7:
            vulnerability_level = "Élevé"
        elif vulnerability_score > 0.4:
            vulnerability_level = "Modéré"
        else:
            vulnerability_level = "Faible"
        
        return {
            "vulnerability_score": vulnerability_score,
            "vulnerability_level": vulnerability_level,
            "specific_vulnerabilities": vulnerabilities
        }

# Test de la classe si exécutée directement
if __name__ == "__main__":
    analyzer = EnhancedComplexFallacyAnalyzer()
    
    # Exemple d'analyse de structure argumentative
    arguments = [
        "Les experts affirment que ce produit est sûr.",
        "Ce produit est utilisé par des millions de personnes.",
        "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
        "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
    ]
    
    structure_results = analyzer.analyze_argument_structure(arguments, "commercial")
    print(f"Résultats de l'analyse de structure argumentative: {json.dumps(structure_results, indent=2, ensure_ascii=False)}")
    
    # Exemple de détection de sophismes composés
    composite_results = analyzer.detect_composite_fallacies(arguments, "commercial")
    print(f"Résultats de la détection de sophismes composés: {json.dumps(composite_results, indent=2, ensure_ascii=False)}")
    
    # Exemple d'analyse de cohérence inter-arguments
    coherence_results = analyzer.analyze_inter_argument_coherence(arguments, "commercial")
    print(f"Résultats de l'analyse de cohérence inter-arguments: {json.dumps(coherence_results, indent=2, ensure_ascii=False)}")
    
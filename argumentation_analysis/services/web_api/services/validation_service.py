#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service de validation d'arguments logiques.
"""

import time
import logging
from typing import Dict, List, Any, Optional

from argumentation_analysis.services.web_api.models.request_models import ValidationRequest
from argumentation_analysis.services.web_api.models.response_models import ValidationResponse, ValidationResult

logger = logging.getLogger("ValidationService")


class ValidationService:
    """
    Service pour la validation logique d'arguments.
    
    Ce service évalue la validité et la solidité des arguments
    en analysant la relation entre prémisses et conclusion.
    """
    
    def __init__(self):
        """Initialise le service de validation."""
        self.logger = logger
        self.is_initialized = True
        
        # Mots-clés logiques pour l'analyse
        self.logical_connectors = {
            'donc', 'par conséquent', 'ainsi', 'c\'est pourquoi', 'en conséquence',
            'il s\'ensuit que', 'on peut conclure', 'cela implique', 'de ce fait'
        }
        
        self.premise_indicators = {
            'car', 'parce que', 'puisque', 'étant donné que', 'vu que',
            'considérant que', 'du fait que', 'en raison de', 'comme'
        }
        
        self.logger.info("Service de validation initialisé")
    
    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service."""
        return self.is_initialized
    
    def validate_argument(self, request: ValidationRequest) -> ValidationResponse:
        """
        Valide un argument logique en analysant ses prémisses, sa conclusion,
        et sa structure logique.

        :param request: L'objet `ValidationRequest` contenant les prémisses,
                        la conclusion, et le type d'argument.
        :type request: ValidationRequest
        :return: Un objet `ValidationResponse` contenant les résultats détaillés
                 de la validation, y compris les scores, les problèmes identifiés
                 et des suggestions d'amélioration.
        :rtype: ValidationResponse
        """
        start_time = time.time()
        
        try:
            # Analyse des prémisses
            premise_analysis = self._analyze_premises(request.premises)
            
            # Analyse de la conclusion
            conclusion_analysis = self._analyze_conclusion(request.conclusion)
            
            # Analyse de la structure logique
            logical_structure = self._analyze_logical_structure(
                request.premises, request.conclusion, request.argument_type
            )
            
            # Calcul des scores
            validity_score = self._calculate_validity_score(
                premise_analysis, conclusion_analysis, logical_structure
            )
            
            soundness_score = self._calculate_soundness_score(
                premise_analysis, validity_score
            )
            
            # Identification des problèmes
            issues = self._identify_issues(
                premise_analysis, conclusion_analysis, logical_structure
            )
            
            # Génération de suggestions
            suggestions = self._generate_suggestions(issues, logical_structure)
            
            # Création du résultat
            result = ValidationResult(
                is_valid=validity_score > 0.6,
                validity_score=validity_score,
                soundness_score=soundness_score,
                premise_analysis=premise_analysis,
                conclusion_analysis=conclusion_analysis,
                logical_structure=logical_structure,
                issues=issues,
                suggestions=suggestions
            )
            
            processing_time = time.time() - start_time
            
            return ValidationResponse(
                success=True,
                premises=request.premises,
                conclusion=request.conclusion,
                argument_type=request.argument_type or "deductive",
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la validation: {e}")
            processing_time = time.time() - start_time
            
            # Réponse d'erreur
            result = ValidationResult(
                is_valid=False,
                validity_score=0.0,
                soundness_score=0.0,
                premise_analysis=[],
                conclusion_analysis={},
                logical_structure={},
                issues=[f"Erreur de validation: {str(e)}"],
                suggestions=["Vérifiez la structure de votre argument"]
            )
            
            return ValidationResponse(
                success=False,
                premises=request.premises,
                conclusion=request.conclusion,
                argument_type=request.argument_type or "unknown",
                result=result,
                processing_time=processing_time
            )
    
    def _analyze_premises(self, premises: List[str]) -> List[Dict[str, Any]]:
        """Analyse individuellement chaque prémisse d'un argument.

        Pour chaque prémisse, évalue la clarté, la spécificité, la crédibilité,
        la présence de qualificateurs, et si c'est une affirmation factuelle.
        Calcule également un score de force pour la prémisse.

        :param premises: Une liste de chaînes de caractères, chaque chaîne étant une prémisse.
        :type premises: List[str]
        :return: Une liste de dictionnaires, chaque dictionnaire contenant l'analyse
                 détaillée d'une prémisse.
        :rtype: List[Dict[str, Any]]
        """
        analysis = []
        
        for i, premise in enumerate(premises):
            premise_data = {
                'index': i,
                'text': premise,
                'length': len(premise),
                'word_count': len(premise.split()),
                'clarity_score': self._assess_clarity(premise),
                'specificity_score': self._assess_specificity(premise),
                'credibility_score': self._assess_credibility(premise),
                'contains_qualifiers': self._contains_qualifiers(premise),
                'is_factual': self._is_factual_claim(premise),
                'strength': 0.0
            }
            
            # Calcul du score de force de la prémisse
            premise_data['strength'] = (
                premise_data['clarity_score'] * 0.3 +
                premise_data['specificity_score'] * 0.3 +
                premise_data['credibility_score'] * 0.4
            )
            
            analysis.append(premise_data)
        
        return analysis
    
    def _analyze_conclusion(self, conclusion: str) -> Dict[str, Any]:
        """Analyse la conclusion d'un argument.

        Évalue la clarté, la spécificité, et la force de la conclusion.
        Initialise des scores pour `follows_logically` et `is_supported` qui
        seront affinés par d'autres méthodes.

        :param conclusion: La chaîne de caractères de la conclusion.
        :type conclusion: str
        :return: Un dictionnaire contenant l'analyse détaillée de la conclusion.
        :rtype: Dict[str, Any]
        """
        return {
            'text': conclusion,
            'length': len(conclusion),
            'word_count': len(conclusion.split()),
            'clarity_score': self._assess_clarity(conclusion),
            'specificity_score': self._assess_specificity(conclusion),
            'follows_logically': 0.5,  # À calculer avec la structure
            'is_supported': 0.5,       # À calculer avec les prémisses
            'strength': self._assess_conclusion_strength(conclusion)
        }
    
    def _analyze_logical_structure(self, premises: List[str], conclusion: str, argument_type: Optional[str]) -> Dict[str, Any]:
        """Analyse la structure logique globale d'un argument.

        Évalue le type d'argument, le nombre de prémisses, la présence de connecteurs
        logiques, la pertinence des prémisses, le flux logique, la complétude,
        la cohérence interne des prémisses, et identifie les lacunes logiques.

        :param premises: La liste des prémisses.
        :type premises: List[str]
        :param conclusion: La conclusion.
        :type conclusion: str
        :param argument_type: Le type d'argument déclaré (par exemple, "deductive").
        :type argument_type: Optional[str]
        :return: Un dictionnaire contenant l'analyse de la structure logique.
        :rtype: Dict[str, Any]
        """
        structure = {
            'argument_type': argument_type,
            'premise_count': len(premises),
            'has_logical_connectors': self._has_logical_connectors(conclusion),
            'premise_relevance': self._assess_premise_relevance(premises, conclusion),
            'logical_flow': self._assess_logical_flow(premises, conclusion),
            'completeness': self._assess_completeness(premises, conclusion),
            'consistency': self._assess_consistency(premises),
            'gap_analysis': self._identify_logical_gaps(premises, conclusion)
        }
        
        return structure
    
    def _calculate_validity_score(self, premise_analysis: List[Dict[str, Any]], conclusion_analysis: Dict[str, Any], structure: Dict[str, Any]) -> float:
        """Calcule un score de validité pour l'argument.

        Combine la force moyenne des prémisses, la force de la conclusion,
        et un score basé sur la structure logique (pertinence, flux, complétude).

        :param premise_analysis: L'analyse des prémisses.
        :type premise_analysis: List[Dict[str, Any]]
        :param conclusion_analysis: L'analyse de la conclusion.
        :type conclusion_analysis: Dict[str, Any]
        :param structure: L'analyse de la structure logique.
        :type structure: Dict[str, Any]
        :return: Un score de validité entre 0.0 et 1.0.
        :rtype: float
        """
        try:
            # Score basé sur la force des prémisses
            premise_strength = sum(p['strength'] for p in premise_analysis) / len(premise_analysis)
            
            # Score basé sur la conclusion
            conclusion_strength = conclusion_analysis['strength']
            
            # Score basé sur la structure logique
            structure_score = (
                structure['premise_relevance'] * 0.3 +
                structure['logical_flow'] * 0.4 +
                structure['completeness'] * 0.3
            )
            
            # Score global de validité
            validity = (
                premise_strength * 0.4 +
                conclusion_strength * 0.2 +
                structure_score * 0.4
            )
            
            return min(1.0, max(0.0, validity))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul validité: {e}")
            return 0.3
    
    def _calculate_soundness_score(self, premise_analysis: List[Dict[str, Any]], validity_score: float) -> float:
        """Calcule un score de solidité pour l'argument.

        La solidité dépend de la validité de l'argument et de la crédibilité
        (vérité perçue) de ses prémisses.

        :param premise_analysis: L'analyse des prémisses, utilisée pour leur crédibilité.
        :type premise_analysis: List[Dict[str, Any]]
        :param validity_score: Le score de validité préalablement calculé.
        :type validity_score: float
        :return: Un score de solidité entre 0.0 et 1.0.
        :rtype: float
        """
        try:
            # La solidité dépend de la validité ET de la vérité des prémisses
            credibility_avg = sum(p['credibility_score'] for p in premise_analysis) / len(premise_analysis)
            
            # Un argument ne peut être solide que s'il est valide
            soundness = validity_score * credibility_avg
            
            return min(1.0, max(0.0, soundness))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul solidité: {e}")
            return 0.3
    
    def _assess_clarity(self, text: str) -> float:
        """Évalue la clarté d'un énoncé textuel basé sur des heuristiques simples.

        Pénalise les phrases très courtes ou très longues.

        :param text: Le texte de l'énoncé.
        :type text: str
        :return: Un score de clarté entre 0.0 et 1.0.
        :rtype: float
        """
        # Heuristiques simples pour la clarté
        word_count = len(text.split())
        
        # Pénalité pour les phrases trop courtes ou trop longues
        if word_count < 3:
            return 0.3
        elif word_count > 30:
            return 0.6
        else:
            return 0.8
    
    def _assess_specificity(self, text: str) -> float:
        """Évalue la spécificité d'un énoncé en recherchant des termes vagues.

        :param text: Le texte de l'énoncé.
        :type text: str
        :return: Un score de spécificité (0.4 si des termes vagues sont trouvés, 0.7 sinon).
        :rtype: float
        """
        # Recherche de termes vagues
        vague_terms = {'quelque', 'certains', 'beaucoup', 'souvent', 'parfois', 'généralement'}
        words = set(text.lower().split())
        
        if words.intersection(vague_terms):
            return 0.4
        else:
            return 0.7
    
    def _assess_credibility(self, text: str) -> float:
        """Évalue la crédibilité perçue d'un énoncé basé sur des indicateurs de source.

        NOTE: Ceci est une heuristique basique et ne remplace pas une vérification factuelle.

        :param text: Le texte de l'énoncé.
        :type text: str
        :return: Un score de crédibilité (0.8 si des indicateurs de source sont trouvés, 0.6 sinon).
        :rtype: float
        """
        # Heuristiques basiques pour la crédibilité
        # Dans un vrai système, cela nécessiterait une vérification factuelle
        
        # Recherche d'indicateurs de sources
        source_indicators = {'selon', 'étude', 'recherche', 'expert', 'données'}
        words = set(text.lower().split())
        
        if words.intersection(source_indicators):
            return 0.8
        else:
            return 0.6  # Score neutre par défaut
    
    def _contains_qualifiers(self, text: str) -> bool:
        """Vérifie si un texte contient des termes qualificateurs (modulateurs de certitude).

        :param text: Le texte à analyser.
        :type text: str
        :return: True si des qualificateurs sont trouvés, False sinon.
        :rtype: bool
        """
        qualifiers = {'peut-être', 'probablement', 'possiblement', 'il semble', 'apparemment'}
        return any(q in text.lower() for q in qualifiers)
    
    def _is_factual_claim(self, text: str) -> bool:
        """Détermine si un énoncé est susceptible d'être une affirmation factuelle.

        Utilise une heuristique simple basée sur l'absence de mots indiquant une opinion
        ou une modalité.

        :param text: Le texte de l'énoncé.
        :type text: str
        :return: True si l'énoncé semble factuel, False sinon.
        :rtype: bool
        """
        # Heuristique simple basée sur la structure
        return not any(word in text.lower() for word in ['devrait', 'pourrait', 'opinion', 'crois'])
    
    def _assess_conclusion_strength(self, conclusion: str) -> float:
        """Évalue la force d'une conclusion comme la moyenne de sa clarté et de sa spécificité.

        :param conclusion: Le texte de la conclusion.
        :type conclusion: str
        :return: Un score de force pour la conclusion.
        :rtype: float
        """
        return (self._assess_clarity(conclusion) + self._assess_specificity(conclusion)) / 2
    
    def _has_logical_connectors(self, text: str) -> bool:
        """Vérifie si un texte contient des connecteurs logiques prédéfinis.

        :param text: Le texte à analyser.
        :type text: str
        :return: True si des connecteurs logiques sont trouvés, False sinon.
        :rtype: bool
        """
        return any(connector in text.lower() for connector in self.logical_connectors)
    
    def _assess_premise_relevance(self, premises: List[str], conclusion: str) -> float:
        """Évalue la pertinence des prémisses par rapport à la conclusion.

        Utilise une heuristique basée sur le chevauchement de mots entre les prémisses
        et la conclusion.

        :param premises: Liste des prémisses.
        :type premises: List[str]
        :param conclusion: La conclusion.
        :type conclusion: str
        :return: Un score moyen de pertinence entre 0.0 et 1.0.
        :rtype: float
        """
        # Analyse basique de la pertinence basée sur les mots-clés communs
        conclusion_words = set(conclusion.lower().split())
        
        relevance_scores = []
        for premise in premises:
            premise_words = set(premise.lower().split())
            common_words = premise_words.intersection(conclusion_words)
            
            # Score basé sur le pourcentage de mots communs
            if len(premise_words) > 0:
                relevance = len(common_words) / len(premise_words)
                relevance_scores.append(min(1.0, relevance * 2))  # Amplifier le score
            else:
                relevance_scores.append(0.0)
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    
    def _assess_logical_flow(self, premises: List[str], conclusion: str) -> float:
        """Évalue le flux logique d'un argument.

        Basé sur la présence de connecteurs logiques dans la conclusion et
        un nombre adéquat de prémisses.

        :param premises: Liste des prémisses.
        :type premises: List[str]
        :param conclusion: La conclusion.
        :type conclusion: str
        :return: Un score de flux logique entre 0.0 et 1.0.
        :rtype: float
        """
        # Score basé sur la présence de connecteurs et la structure
        has_connectors = self._has_logical_connectors(conclusion)
        premise_quality = len(premises) >= 2  # Au moins 2 prémisses pour un bon argument
        
        score = 0.5  # Score de base
        if has_connectors:
            score += 0.3
        if premise_quality:
            score += 0.2
        
        return min(1.0, score)
    
    def _assess_completeness(self, premises: List[str], conclusion: str) -> float:
        """Évalue la complétude d'un argument.

        Considère qu'un argument est plus complet s'il a un nombre suffisant
        de prémisses et une conclusion d'une longueur substantielle.

        :param premises: Liste des prémisses.
        :type premises: List[str]
        :param conclusion: La conclusion.
        :type conclusion: str
        :return: Un score de complétude entre 0.0 et 1.0.
        :rtype: float
        """
        # Un argument complet a suffisamment de prémisses et une conclusion claire
        premise_count_score = min(1.0, len(premises) / 3)  # Optimal autour de 3 prémisses
        conclusion_length_score = min(1.0, len(conclusion.split()) / 10)  # Conclusion substantielle
        
        return (premise_count_score + conclusion_length_score) / 2
    
    def _assess_consistency(self, premises: List[str]) -> float:
        """Évalue la cohérence interne entre les prémisses.

        NOTE: Implémentation actuelle basique, retourne un score neutre.
        Une analyse NLP plus poussée serait nécessaire pour une évaluation réelle.

        :param premises: Liste des prémisses.
        :type premises: List[str]
        :return: Un score de cohérence (actuellement 0.7 par défaut si plus d'une prémisse,
                 1.0 sinon).
        :rtype: float
        """
        # Analyse basique de cohérence (à améliorer avec NLP)
        if len(premises) < 2:
            return 1.0  # Une seule prémisse est cohérente par défaut
        
        # Pour l'instant, score neutre
        return 0.7
    
    def _identify_logical_gaps(self, premises: List[str], conclusion: str) -> List[str]:
        """Identifie les lacunes logiques potentielles dans un argument.

        Vérifie la pertinence des prémisses, le nombre de prémisses, et la présence
        de connecteurs logiques.

        :param premises: Liste des prémisses.
        :type premises: List[str]
        :param conclusion: La conclusion.
        :type conclusion: str
        :return: Une liste de chaînes de caractères décrivant les lacunes identifiées.
        :rtype: List[str]
        """
        gaps = []
        
        # Vérification de la pertinence
        relevance = self._assess_premise_relevance(premises, conclusion)
        if relevance < 0.3:
            gaps.append("Faible pertinence entre prémisses et conclusion")
        
        # Vérification du nombre de prémisses
        if len(premises) < 2:
            gaps.append("Nombre insuffisant de prémisses")
        
        # Vérification des connecteurs logiques
        if not self._has_logical_connectors(conclusion):
            gaps.append("Absence de connecteurs logiques explicites")
        
        return gaps
    
    def _identify_issues(self, premise_analysis: List[Dict[str, Any]], conclusion_analysis: Dict[str, Any], structure: Dict[str, Any]) -> List[str]:
        """Identifie les problèmes potentiels dans un argument basé sur son analyse.

        Regroupe les problèmes liés à la faiblesse des prémisses, à la clarté de la conclusion,
        à la pertinence, au flux logique, et aux lacunes identifiées.

        :param premise_analysis: L'analyse des prémisses.
        :type premise_analysis: List[Dict[str, Any]]
        :param conclusion_analysis: L'analyse de la conclusion.
        :type conclusion_analysis: Dict[str, Any]
        :param structure: L'analyse de la structure logique.
        :type structure: Dict[str, Any]
        :return: Une liste de chaînes de caractères décrivant les problèmes identifiés.
        :rtype: List[str]
        """
        issues = []
        
        # Problèmes avec les prémisses
        weak_premises = [p for p in premise_analysis if p['strength'] < 0.4]
        if weak_premises:
            issues.append(f"{len(weak_premises)} prémisse(s) faible(s) détectée(s)")
        
        # Problèmes avec la conclusion
        if conclusion_analysis['strength'] < 0.4:
            issues.append("Conclusion peu claire ou peu spécifique")
        
        # Problèmes structurels
        if structure['premise_relevance'] < 0.3:
            issues.append("Prémisses peu pertinentes pour la conclusion")
        
        if structure['logical_flow'] < 0.4:
            issues.append("Flux logique déficient")
        
        # Ajout des lacunes identifiées
        issues.extend(structure['gap_analysis'])
        
        return issues
    
    def _generate_suggestions(self, issues: List[str], structure: Dict[str, Any]) -> List[str]:
        """Génère des suggestions d'amélioration basées sur les problèmes identifiés.

        :param issues: Liste des problèmes identifiés dans l'argument.
        :type issues: List[str]
        :param structure: L'analyse de la structure logique (non utilisée directement ici
                          mais pourrait l'être pour des suggestions plus fines).
        :type structure: Dict[str, Any]
        :return: Une liste de chaînes de caractères contenant des suggestions.
        :rtype: List[str]
        """
        suggestions = []
        
        if "prémisse(s) faible(s)" in str(issues):
            suggestions.append("Renforcez vos prémisses avec des données ou des sources fiables")
        
        if "Conclusion peu claire" in str(issues):
            suggestions.append("Reformulez votre conclusion de manière plus précise et spécifique")
        
        if "peu pertinentes" in str(issues):
            suggestions.append("Assurez-vous que vos prémisses sont directement liées à votre conclusion")
        
        if "Flux logique déficient" in str(issues):
            suggestions.append("Utilisez des connecteurs logiques (donc, par conséquent, ainsi...)")
        
        if "Nombre insuffisant de prémisses" in str(issues):
            suggestions.append("Ajoutez des prémisses supplémentaires pour renforcer votre argument")
        
        if not suggestions:
            suggestions.append("Votre argument semble bien structuré")
        
        return suggestions
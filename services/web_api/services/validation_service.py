#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service de validation d'arguments logiques.
"""

import time
import logging
from typing import Dict, List, Any, Optional

from services.web_api.models.request_models import ValidationRequest
from services.web_api.models.response_models import ValidationResponse, ValidationResult

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
        Valide un argument logique.
        
        Args:
            request: Requête de validation
            
        Returns:
            Réponse avec les résultats de validation
        """
        start_time = time.time()
        
        try:
            # Vérification des entrées
            if not request.premises:
                raise ValueError("Aucune prémisse fournie. Un argument valide nécessite au moins une prémisse.")
            
            if not request.conclusion or not request.conclusion.strip():
                raise ValueError("Aucune conclusion fournie. Un argument valide doit avoir une conclusion claire.")
            
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
            
        except ValueError as ve:
            self.logger.error(f"Erreur de validation (Valeur): {ve}")
            processing_time = time.time() - start_time
            
            # Réponse d'erreur avec description détaillée
            result = ValidationResult(
                is_valid=False,
                validity_score=0.0,
                soundness_score=0.0,
                premise_analysis=[],
                conclusion_analysis={},
                logical_structure={},
                issues=[str(ve)],
                suggestions=["Vérifiez que vous avez fourni au moins une prémisse et une conclusion claire."]
            )
            
            return ValidationResponse(
                success=False,
                premises=request.premises,
                conclusion=request.conclusion,
                argument_type=request.argument_type or "unknown",
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la validation: {e}")
            processing_time = time.time() - start_time
            
            # Réponse d'erreur avec description détaillée
            result = ValidationResult(
                is_valid=False,
                validity_score=0.0,
                soundness_score=0.0,
                premise_analysis=[],
                conclusion_analysis={},
                logical_structure={},
                issues=[f"Une erreur s'est produite lors de l'analyse de votre argument : {str(e)}"],
                suggestions=[
                    "Vérifiez que votre argument est bien formaté.",
                    "Assurez-vous que vos prémisses et votre conclusion sont clairement énoncées.",
                    "Vérifiez que vous utilisez des connecteurs logiques appropriés."
                ]
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
        """Analyse chaque prémisse individuellement."""
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
        """Analyse la conclusion."""
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
    
    def _analyze_logical_structure(self, premises: List[str], conclusion: str, argument_type: str) -> Dict[str, Any]:
        """Analyse la structure logique de l'argument."""
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
    
    def _calculate_validity_score(self, premise_analysis: List[Dict], conclusion_analysis: Dict, structure: Dict) -> float:
        """Calcule le score de validité de l'argument."""
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
    
    def _calculate_soundness_score(self, premise_analysis: List[Dict], validity_score: float) -> float:
        """Calcule le score de solidité de l'argument."""
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
        """Évalue la clarté d'un énoncé."""
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
        """Évalue la spécificité d'un énoncé."""
        # Recherche de termes vagues
        vague_terms = {'quelque', 'certains', 'beaucoup', 'souvent', 'parfois', 'généralement'}
        words = set(text.lower().split())
        
        if words.intersection(vague_terms):
            return 0.4
        else:
            return 0.7
    
    def _assess_credibility(self, text: str) -> float:
        """Évalue la crédibilité d'un énoncé."""
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
        """Vérifie si le texte contient des qualificateurs."""
        qualifiers = {'peut-être', 'probablement', 'possiblement', 'il semble', 'apparemment'}
        return any(q in text.lower() for q in qualifiers)
    
    def _is_factual_claim(self, text: str) -> bool:
        """Détermine si l'énoncé est une affirmation factuelle."""
        # Heuristique simple basée sur la structure
        return not any(word in text.lower() for word in ['devrait', 'pourrait', 'opinion', 'crois'])
    
    def _assess_conclusion_strength(self, conclusion: str) -> float:
        """Évalue la force de la conclusion."""
        return (self._assess_clarity(conclusion) + self._assess_specificity(conclusion)) / 2
    
    def _has_logical_connectors(self, text: str) -> bool:
        """Vérifie la présence de connecteurs logiques."""
        return any(connector in text.lower() for connector in self.logical_connectors)
    
    def _assess_premise_relevance(self, premises: List[str], conclusion: str) -> float:
        """Évalue la pertinence des prémisses par rapport à la conclusion."""
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
        """Évalue le flux logique de l'argument."""
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
        """Évalue la complétude de l'argument."""
        # Un argument complet a suffisamment de prémisses et une conclusion claire
        premise_count_score = min(1.0, len(premises) / 3)  # Optimal autour de 3 prémisses
        conclusion_length_score = min(1.0, len(conclusion.split()) / 10)  # Conclusion substantielle
        
        return (premise_count_score + conclusion_length_score) / 2
    
    def _assess_consistency(self, premises: List[str]) -> float:
        """Évalue la cohérence entre les prémisses."""
        # Analyse basique de cohérence (à améliorer avec NLP)
        if len(premises) < 2:
            return 1.0  # Une seule prémisse est cohérente par défaut
        
        # Pour l'instant, score neutre
        return 0.7
    
    def _identify_logical_gaps(self, premises: List[str], conclusion: str) -> List[str]:
        """Identifie les lacunes logiques dans l'argument."""
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
    
    def _identify_issues(self, premise_analysis: List[Dict], conclusion_analysis: Dict, structure: Dict) -> List[str]:
        """Identifie les problèmes dans l'argument."""
        issues = []
        
        # Vérification des prémisses
        if not premise_analysis:
            issues.append("Aucune prémisse fournie. Un argument valide nécessite au moins une prémisse.")
        else:
            # Vérification de la clarté des prémisses
            unclear_premises = [p for p in premise_analysis if p['clarity_score'] < 0.5]
            if unclear_premises:
                issues.append(f"{len(unclear_premises)} prémisse(s) manque(nt) de clarté. Reformulez-les pour les rendre plus explicites.")
            
            # Vérification de la crédibilité
            low_credibility = [p for p in premise_analysis if p['credibility_score'] < 0.4]
            if low_credibility:
                issues.append(f"{len(low_credibility)} prémisse(s) manque(nt) de crédibilité. Ajoutez des sources ou des preuves pour les renforcer.")
        
        # Vérification de la conclusion
        if not conclusion_analysis['text'].strip():
            issues.append("Aucune conclusion fournie. Un argument valide doit avoir une conclusion claire.")
        elif conclusion_analysis['clarity_score'] < 0.5:
            issues.append("La conclusion manque de clarté. Reformulez-la pour la rendre plus explicite.")
        
        # Vérification de la structure logique
        if structure['premise_relevance'] < 0.4:
            issues.append("Les prémisses ne sont pas suffisamment pertinentes pour la conclusion. Assurez-vous que vos prémisses soutiennent directement votre conclusion.")
        
        if structure['logical_flow'] < 0.4:
            issues.append("Le raisonnement manque de fluidité logique. Utilisez des connecteurs logiques appropriés pour lier vos prémisses à votre conclusion.")
        
        if structure['completeness'] < 0.4:
            issues.append("L'argument est incomplet. Ajoutez des prémisses intermédiaires pour renforcer le lien entre vos prémisses et votre conclusion.")
        
        if structure['consistency'] < 0.4:
            issues.append("Les prémisses sont contradictoires entre elles. Assurez-vous que vos prémisses ne se contredisent pas.")
        
        # Vérification des écarts logiques
        gaps = structure['gap_analysis']
        if gaps:
            issues.extend([f"Écart logique détecté : {gap}" for gap in gaps])
        
        return issues
    
    def _generate_suggestions(self, issues: List[str], structure: Dict) -> List[str]:
        """Génère des suggestions pour améliorer l'argument."""
        suggestions = []
        
        # Suggestions générales
        if not issues:
            suggestions.append("Votre argument est bien structuré. Pour le renforcer davantage, vous pourriez ajouter des exemples concrets ou des contre-arguments.")
            return suggestions
        
        # Suggestions basées sur les problèmes identifiés
        for issue in issues:
            if "prémisse" in issue.lower():
                if "clarté" in issue.lower():
                    suggestions.append("Pour améliorer la clarté de vos prémisses : utilisez des phrases courtes et directes, évitez le jargon inutile, et définissez les termes techniques.")
                elif "crédibilité" in issue.lower():
                    suggestions.append("Pour renforcer la crédibilité de vos prémisses : citez des sources fiables, utilisez des statistiques vérifiables, ou appuyez-vous sur des faits établis.")
                elif "pertinence" in issue.lower():
                    suggestions.append("Pour améliorer la pertinence de vos prémisses : assurez-vous que chaque prémisse contribue directement à votre conclusion, et éliminez les informations non essentielles.")
            
            elif "conclusion" in issue.lower():
                if "clarté" in issue.lower():
                    suggestions.append("Pour clarifier votre conclusion : utilisez des termes précis, évitez les ambiguïtés, et assurez-vous qu'elle découle logiquement de vos prémisses.")
                else:
                    suggestions.append("Votre conclusion devrait être clairement liée à vos prémisses. Utilisez des connecteurs logiques comme 'donc', 'par conséquent', ou 'ainsi'.")
            
            elif "logique" in issue.lower():
                if "fluidité" in issue.lower():
                    suggestions.append("Pour améliorer la fluidité logique : utilisez des connecteurs logiques appropriés, structurez vos idées de manière progressive, et assurez-vous que chaque étape découle naturellement de la précédente.")
                elif "incomplet" in issue.lower():
                    suggestions.append("Pour compléter votre argument : ajoutez des prémisses intermédiaires qui renforcent le lien entre vos prémisses principales et votre conclusion.")
                elif "contradictoire" in issue.lower():
                    suggestions.append("Pour résoudre les contradictions : revoyez vos prémisses pour vous assurer qu'elles sont cohérentes entre elles, et reformulez-les si nécessaire.")
        
        # Suggestions spécifiques basées sur le type d'argument
        if structure['argument_type'] == 'deductive':
            suggestions.append("Pour un argument déductif, assurez-vous que vos prémisses sont universellement vraies et que votre conclusion en découle nécessairement.")
        elif structure['argument_type'] == 'inductive':
            suggestions.append("Pour un argument inductif, renforcez vos prémisses avec des exemples variés et représentatifs pour augmenter la probabilité de votre conclusion.")
        
        return suggestions
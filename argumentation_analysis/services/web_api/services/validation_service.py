#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service de validation d'arguments logiques.
"""

import time
import logging
from typing import Dict, List, Any, Optional
import asyncio

# Imports des modèles (style HEAD)
from argumentation_analysis.services.web_api.models.request_models import ValidationRequest
from argumentation_analysis.services.web_api.models.response_models import ValidationResponse, ValidationResult
from .logic_service import LogicService

logger = logging.getLogger("ValidationService")


class ValidationService:
    """
    Service pour la validation logique d'arguments.
    
    Ce service évalue la validité et la solidité des arguments
    en analysant la relation entre prémisses et conclusion.
    """
    
    def __init__(self, logic_service: LogicService):
        """Initialise le service de validation."""
        self.logger = logger
        self.logic_service = logic_service
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
        return self.is_initialized and self.logic_service.is_healthy()

    async def validate_argument(self, request: ValidationRequest) -> ValidationResponse:
        """
        Valide un argument logique.
        
        Args:
            request: Requête de validation
            
        Returns:
            Réponse avec les résultats de validation
        """
        start_time = time.time()
        
        try:
            # Branche 1: Validation formelle via LogicService si logic_type est fourni
            if request.logic_type and request.logic_type != "heuristic":
                is_formally_valid = await self.logic_service.validate_argument_from_components(request)
                
                result = ValidationResult(
                    is_valid=is_formally_valid,
                    validity_score=1.0 if is_formally_valid else 0.0,
                    soundness_score=0.0, # La solidité n'est pas évaluée ici
                    premise_analysis=[],
                    conclusion_analysis={},
                    logical_structure={'argument_type': request.logic_type, 'method': 'formal'},
                    issues=[] if is_formally_valid else ["L'argument n'est pas logiquement valide selon le moteur formel."],
                    suggestions=[]
                )
                
                return ValidationResponse(
                    success=True,
                    premises=request.premises,
                    conclusion=request.conclusion,
                    argument_type=request.argument_type,
                    result=result,
                    processing_time=time.time() - start_time
                )


            # Branche 2: Validation heuristique (comportement existant)
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
            logical_structure['method'] = 'heuristic' # Ajout pour clarté
            
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
            
        except ValueError as ve: # Gestion d'erreur de la branche 0813790
            self.logger.error(f"Erreur de validation (Valeur): {ve}")
            processing_time = time.time() - start_time
            
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
            
        except Exception as e: # Gestion d'erreur de la branche 0813790
            self.logger.error(f"Erreur lors de la validation: {e}")
            processing_time = time.time() - start_time
            
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
            if not premise_analysis: return 0.0 # Eviter division par zéro
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
            if not premise_analysis: return 0.0 # Eviter division par zéro
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
        word_count = len(text.split())
        if word_count < 3: return 0.3
        elif word_count > 30: return 0.6
        else: return 0.8
    
    def _assess_specificity(self, text: str) -> float:
        """Évalue la spécificité d'un énoncé en recherchant des termes vagues.

        :param text: Le texte de l'énoncé.
        :type text: str
        :return: Un score de spécificité (0.4 si des termes vagues sont trouvés, 0.7 sinon).
        :rtype: float
        """
        vague_terms = {'quelque', 'certains', 'beaucoup', 'souvent', 'parfois', 'généralement'}
        words = set(text.lower().split())
        if words.intersection(vague_terms): return 0.4
        else: return 0.7
    
    def _assess_credibility(self, text: str) -> float:
        """Évalue la crédibilité perçue d'un énoncé basé sur des indicateurs de source.

        NOTE: Ceci est une heuristique basique et ne remplace pas une vérification factuelle.

        :param text: Le texte de l'énoncé.
        :type text: str
        :return: Un score de crédibilité (0.8 si des indicateurs de source sont trouvés, 0.6 sinon).
        :rtype: float
        """
        source_indicators = {'selon', 'étude', 'recherche', 'expert', 'données'}
        words = set(text.lower().split())
        if words.intersection(source_indicators): return 0.8
        else: return 0.6
    
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
        conclusion_words = set(conclusion.lower().split())
        relevance_scores = []
        if not premises: return 0.0
        for premise in premises:
            premise_words = set(premise.lower().split())
            common_words = premise_words.intersection(conclusion_words)
            if len(premise_words) > 0:
                relevance = len(common_words) / len(premise_words)
                relevance_scores.append(min(1.0, relevance * 2))
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
        has_connectors = self._has_logical_connectors(conclusion)
        premise_quality = len(premises) >= 2
        score = 0.5
        if has_connectors: score += 0.3
        if premise_quality: score += 0.2
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
        premise_count_score = min(1.0, len(premises) / 3)
        conclusion_length_score = min(1.0, len(conclusion.split()) / 10)
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
        if len(premises) < 2: return 1.0
        return 0.7
    
    def _identify_logical_gaps(self, premises: List[str], conclusion: str) -> List[str]:
        """Identifie les lacunes logiques potentielles dans un argument. (Logique de HEAD)

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
        relevance = self._assess_premise_relevance(premises, conclusion)
        if relevance < 0.3:
            gaps.append("Faible pertinence entre prémisses et conclusion")
        if len(premises) < 2:
            gaps.append("Nombre insuffisant de prémisses")
        if not self._has_logical_connectors(conclusion):
            gaps.append("Absence de connecteurs logiques explicites")
        return gaps

    def _identify_issues(self, premise_analysis: List[Dict[str, Any]], conclusion_analysis: Dict[str, Any], structure: Dict[str, Any]) -> List[str]:
        """Identifie les problèmes dans l'argument. (Logique de la branche 0813790)"""
        issues = []
        
        if not premise_analysis:
            issues.append("Aucune prémisse fournie. Un argument valide nécessite au moins une prémisse.")
        else:
            unclear_premises = [p for p in premise_analysis if p['clarity_score'] < 0.5]
            if unclear_premises:
                issues.append(f"{len(unclear_premises)} prémisse(s) manque(nt) de clarté. Reformulez-les pour les rendre plus explicites.")
            
            low_credibility = [p for p in premise_analysis if p['credibility_score'] < 0.4]
            if low_credibility:
                issues.append(f"{len(low_credibility)} prémisse(s) manque(nt) de crédibilité. Ajoutez des sources ou des preuves pour les renforcer.")
        
        if not conclusion_analysis.get('text', "").strip():
            issues.append("Aucune conclusion fournie. Un argument valide doit avoir une conclusion claire.")
        elif conclusion_analysis.get('clarity_score', 0.0) < 0.5:
            issues.append("La conclusion manque de clarté. Reformulez-la pour la rendre plus explicite.")
        
        if structure.get('premise_relevance', 0.0) < 0.4:
            issues.append("Les prémisses ne sont pas suffisamment pertinentes pour la conclusion. Assurez-vous que vos prémisses soutiennent directement votre conclusion.")
        
        if structure.get('logical_flow', 0.0) < 0.4:
            issues.append("Le raisonnement manque de fluidité logique. Utilisez des connecteurs logiques appropriés pour lier vos prémisses à votre conclusion.")
        
        if structure.get('completeness', 0.0) < 0.4:
            issues.append("L'argument est incomplet. Ajoutez des prémisses intermédiaires pour renforcer le lien entre vos prémisses et votre conclusion.")
        
        if structure.get('consistency', 0.0) < 0.4:
            issues.append("Les prémisses sont contradictoires entre elles. Assurez-vous que vos prémisses ne se contredisent pas.")
        
        gaps = structure.get('gap_analysis', [])
        if gaps:
            issues.extend([f"Écart logique détecté : {gap}" for gap in gaps])
        
        return issues

    def _generate_suggestions(self, issues: List[str], structure: Dict[str, Any]) -> List[str]:
        """Génère des suggestions pour améliorer l'argument. (Logique de la branche 0813790)"""
        suggestions = []
        
        if not issues:
            suggestions.append("Votre argument est bien structuré. Pour le renforcer davantage, vous pourriez ajouter des exemples concrets ou des contre-arguments.")
            return suggestions
        
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
        
        argument_type = structure.get('argument_type')
        if argument_type == 'deductive':
            suggestions.append("Pour un argument déductif, assurez-vous que vos prémisses sont universellement vraies et que votre conclusion en découle nécessairement.")
        elif argument_type == 'inductive':
            suggestions.append("Pour un argument inductif, renforcez vos prémisses avec des exemples variés et représentatifs pour augmenter la probabilité de votre conclusion.")
        
        # S'assurer qu'il y a toujours au moins une suggestion si des problèmes ont été trouvés
        if issues and not suggestions:
            suggestions.append("Examinez les problèmes identifiés pour améliorer la structure et la clarté de votre argument.")
            
        return suggestions
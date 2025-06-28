"""
Agent de génération de contre-arguments.

Ce module implémente l'agent principal pour la génération de contre-arguments.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple

from .definitions import (
    Argument, 
    CounterArgument, 
    CounterArgumentType, 
    ArgumentStrength,
    RhetoricalStrategy,
    Vulnerability,
    EvaluationResult,
    ValidationResult
)
from .parser import ArgumentParser, VulnerabilityAnalyzer, parse_llm_response
from .strategies import RhetoricalStrategies

# Importer les modules que nous avons créés
from ..llm.llm_generator import LLMGenerator
from ..logic.validator import CounterArgumentValidator
from ..evaluation.evaluator import CounterArgumentEvaluator
from ..evaluation.metrics import PerformanceMetrics, MetricsTracker

logger = logging.getLogger(__name__)


class CounterArgumentAgent:
    """
    Agent principal pour la génération de contre-arguments.
    
    Cet agent analyse des arguments, identifie leurs vulnérabilités,
    génère des contre-arguments appropriés et évalue leur qualité.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialise l'agent de génération de contre-arguments.
        
        Args:
            config: Configuration optionnelle pour l'agent
        """
        self.config = config or {}
        self.parser = ArgumentParser()
        self.vulnerability_analyzer = VulnerabilityAnalyzer()
        self.rhetorical_strategies = RhetoricalStrategies()
        
        # Initialiser les composants que nous avons créés
        self.llm_generator = LLMGenerator(
            api_key=self.config.get("openai_api_key"),
            model=self.config.get("model", "gpt-4o")
        )
        self.validator = CounterArgumentValidator(
            tweety_jar_path=self.config.get("tweety_jar_path")
        )
        self.evaluator = CounterArgumentEvaluator()
        
        # Initialiser les métriques
        self.metrics = PerformanceMetrics()
        self.metrics_tracker = MetricsTracker(self.metrics)
        
        logger.info("CounterArgumentAgent initialisé")
    
    def analyze_argument(self, argument_text: str) -> Argument:
        """
        Analyse la structure d'un argument.
        
        Args:
            argument_text: Le texte de l'argument à analyser
            
        Returns:
            Un objet Argument contenant la structure de l'argument
        """
        logger.info(f"Analyse d'un argument: {argument_text[:100]}...")
        return self.parser.parse_argument(argument_text)
    
    def identify_vulnerabilities(self, argument: Argument) -> List[Vulnerability]:
        """
        Identifie les vulnérabilités dans un argument.
        
        Args:
            argument: L'argument à analyser
            
        Returns:
            Une liste de vulnérabilités identifiées
        """
        logger.info(f"Identification des vulnérabilités pour l'argument: {argument.content[:100]}...")
        return self.vulnerability_analyzer.analyze_vulnerabilities(argument)
    
    def generate_counter_argument(
        self,
        argument_text_or_object,
        counter_type: Optional[CounterArgumentType] = None,
        rhetorical_strategy: Optional[RhetoricalStrategy] = None
    ) -> Dict[str, Any]:
        """
        Génère un contre-argument pour un argument donné.
        
        Args:
            argument_text_or_object: Le texte de l'argument ou un objet Argument
            counter_type: Le type de contre-argument à générer (optionnel)
            rhetorical_strategy: Stratégie rhétorique à utiliser (optionnel)
            
        Returns:
            Un dictionnaire contenant l'argument original, le contre-argument,
            l'évaluation et la validation
        """
        # Convertir le texte en objet Argument si nécessaire
        if isinstance(argument_text_or_object, str):
            argument = self.parser.parse_argument(argument_text_or_object)
        else:
            argument = argument_text_or_object
        
        # Identifier les vulnérabilités en utilisant le LLM au lieu de l'analyseur basique
        vulnerabilities_data = self.llm_generator.identify_vulnerabilities(argument)
        
        # Convertir les données du LLM en objets Vulnerability
        vulnerabilities = []
        for vuln_data in vulnerabilities_data:
            try:
                vulnerabilities.append(Vulnerability(
                    type=vuln_data.get("type", "inconnu"),
                    target=vuln_data.get("target", "inconnu"),
                    description=vuln_data.get("description", ""),
                    score=float(vuln_data.get("score", 0.5)),
                    suggested_counter_type=CounterArgumentType(vuln_data.get("suggested_counter_type", "direct_refutation"))
                ))
            except (ValueError, TypeError) as e:
                logger.warning(f"Erreur lors de la conversion d'une vulnérabilité: {e}")
        
        # Sélectionner le type de contre-argument si non spécifié
        if counter_type is None:
            counter_type = self._select_best_counter_type(argument, vulnerabilities)
            logger.info(f"Type de contre-argument sélectionné automatiquement: {counter_type.value}")
        
        # Démarrer le suivi des métriques
        self.metrics_tracker.start_tracking(counter_type)
        
        try:
            # Utiliser le LLM pour générer le contre-argument
            counter_arg_data = self.llm_generator.generate_counter_argument(
                argument, counter_type, vulnerabilities, rhetorical_strategy
            )
            
            # Créer l'objet CounterArgument
            counter_argument = CounterArgument(
                original_argument=argument,
                counter_type=counter_type,
                counter_content=counter_arg_data.get("counter_argument", ""),
                target_component=counter_arg_data.get("target_component", ""),
                strength=ArgumentStrength(counter_arg_data.get("strength", "moderate")),
                confidence=counter_arg_data.get("confidence", 0.8),
                supporting_evidence=counter_arg_data.get("supporting_evidence", []),
                rhetorical_strategy=counter_arg_data.get("rhetorical_strategy", 
                                                        rhetorical_strategy.value if rhetorical_strategy else "")
            )
            
            # Évaluer le contre-argument
            evaluation = self.evaluator.evaluate(argument, counter_argument)
            
            # Valider le contre-argument
            validation = self.validator.validate(argument, counter_argument)
            
            # Arrêter le suivi des métriques
            self.metrics_tracker.stop_tracking(evaluation, success=True)
            
            # Retourner les résultats
            return {
                "original_argument": argument,
                "counter_argument": counter_argument,
                "evaluation": evaluation,
                "validation": validation,
                "vulnerabilities": vulnerabilities  # Ajouter les vulnérabilités à la réponse
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du contre-argument: {e}")
            # Arrêter le suivi des métriques avec échec
            self.metrics_tracker.stop_tracking(
                EvaluationResult(
                    relevance=0.0,
                    logical_strength=0.0,
                    persuasiveness=0.0,
                    originality=0.0,
                    clarity=0.0,
                    overall_score=0.0,
                    recommendations=["Erreur lors de la génération"]
                ),
                success=False
            )
            # Créer un contre-argument par défaut
            return self._create_fallback_response(argument, counter_type, str(e))
    
    def _select_best_counter_type(
        self, 
        argument: Argument, 
        vulnerabilities: List[Vulnerability]
    ) -> CounterArgumentType:
        """
        Sélectionne le meilleur type de contre-argument en fonction des vulnérabilités.
        
        Args:
            argument: L'argument original
            vulnerabilities: Liste des vulnérabilités identifiées
            
        Returns:
            Le type de contre-argument le plus approprié
        """
        if not vulnerabilities:
            # Si aucune vulnérabilité n'est détectée, utiliser la réfutation directe
            return CounterArgumentType.DIRECT_REFUTATION
        
        # Trier les vulnérabilités par score décroissant
        sorted_vulnerabilities = sorted(vulnerabilities, key=lambda v: v.score, reverse=True)
        
        # Utiliser le type suggéré pour la vulnérabilité la plus forte
        return sorted_vulnerabilities[0].suggested_counter_type
    
    def _create_fallback_response(
        self,
        argument: Argument,
        counter_type: CounterArgumentType,
        error_message: str
    ) -> Dict[str, Any]:
        """
        Crée une réponse de secours en cas d'erreur.
        
        Args:
            argument: L'argument original
            counter_type: Le type de contre-argument demandé
            error_message: Le message d'erreur
            
        Returns:
            Un dictionnaire contenant une réponse par défaut
        """
        # Créer un contre-argument par défaut
        counter_argument = CounterArgument(
            original_argument=argument,
            counter_type=counter_type or CounterArgumentType.DIRECT_REFUTATION,
            counter_content=f"Impossible de générer un contre-argument. Erreur: {error_message}",
            target_component="error",
            strength=ArgumentStrength.WEAK,
            confidence=0.1,
            supporting_evidence=[],
            rhetorical_strategy="error"
        )
        
        # Créer une évaluation par défaut
        evaluation = EvaluationResult(
            relevance=0.0,
            logical_strength=0.0,
            persuasiveness=0.0,
            originality=0.0,
            clarity=0.0,
            overall_score=0.0,
            recommendations=["Erreur lors de la génération du contre-argument"]
        )
        
        # Créer une validation par défaut
        validation = ValidationResult(
            is_valid_attack=False,
            original_survives=True,
            counter_succeeds=False,
            logical_consistency=False,
            formal_representation=f"Erreur: {error_message}"
        )
        
        return {
            "original_argument": argument,
            "counter_argument": counter_argument,
            "evaluation": evaluation,
            "validation": validation
        }
    
    def evaluate_counter_argument(
        self, 
        original_argument: Argument, 
        counter_argument: CounterArgument
    ) -> EvaluationResult:
        """
        Évalue la qualité d'un contre-argument.
        
        Args:
            original_argument: L'argument original
            counter_argument: Le contre-argument à évaluer
            
        Returns:
            Un objet EvaluationResult contenant l'évaluation
        """
        logger.info("Évaluation du contre-argument...")
        
        # Dans une implémentation complète, on utiliserait l'évaluateur:
        # return await self.evaluator.evaluate(original_argument, counter_argument)
        
        # Implémentation simplifiée pour cette version
        relevance = self._evaluate_relevance(original_argument, counter_argument)
        logical_strength = self._evaluate_logical_strength(counter_argument)
        persuasiveness = self._evaluate_persuasiveness(counter_argument)
        originality = self._evaluate_originality(counter_argument)
        clarity = self._evaluate_clarity(counter_argument)
        
        overall_score = (
            relevance * 0.25 +
            logical_strength * 0.25 +
            persuasiveness * 0.20 +
            originality * 0.15 +
            clarity * 0.15
        )
        
        recommendations = self._generate_recommendations(
            original_argument, counter_argument, 
            relevance, logical_strength, persuasiveness, originality, clarity
        )
        
        return EvaluationResult(
            relevance=relevance,
            logical_strength=logical_strength,
            persuasiveness=persuasiveness,
            originality=originality,
            clarity=clarity,
            overall_score=overall_score,
            recommendations=recommendations
        )
    
    def validate_counter_argument(
        self, 
        original_argument: Argument, 
        counter_argument: CounterArgument
    ) -> ValidationResult:
        """
        Valide la cohérence logique d'un contre-argument.
        
        Args:
            original_argument: L'argument original
            counter_argument: Le contre-argument à valider
            
        Returns:
            Un objet ValidationResult contenant le résultat de la validation
        """
        logger.info("Validation logique du contre-argument...")
        
        # Dans une implémentation complète, on utiliserait le validateur:
        # return await self.validator.validate(original_argument, counter_argument)
        
        # Implémentation simplifiée pour cette version
        is_valid_attack = True  # Par défaut, considérer comme valide
        original_survives = False  # Par défaut, l'argument original ne survit pas
        counter_succeeds = True  # Par défaut, le contre-argument réussit
        logical_consistency = True  # Par défaut, considérer comme cohérent
        
        if counter_argument.strength in [ArgumentStrength.WEAK, ArgumentStrength.MODERATE]:
            original_survives = True
        
        return ValidationResult(
            is_valid_attack=is_valid_attack,
            original_survives=original_survives,
            counter_succeeds=counter_succeeds,
            logical_consistency=logical_consistency,
            formal_representation=None  # Serait fourni par un validateur basé sur TweetyProject
        )
    
    def _determine_target_component(
        self, 
        counter_type: CounterArgumentType, 
        vulnerabilities: List[Vulnerability]
    ) -> str:
        """Détermine la composante ciblée par le contre-argument."""
        # Mapper les types de contre-arguments aux composantes ciblées
        type_to_target = {
            CounterArgumentType.DIRECT_REFUTATION: "conclusion",
            CounterArgumentType.COUNTER_EXAMPLE: "generalization",
            CounterArgumentType.ALTERNATIVE_EXPLANATION: "explanation",
            CounterArgumentType.PREMISE_CHALLENGE: "premises",
            CounterArgumentType.REDUCTIO_AD_ABSURDUM: "reasoning"
        }
        
        # Utiliser la cible de la première vulnérabilité compatible, si disponible
        for vuln in vulnerabilities:
            if vuln.suggested_counter_type == counter_type:
                return vuln.target
        
        # Sinon, utiliser la cible par défaut pour ce type
        return type_to_target.get(counter_type, "argument")
    
    def _evaluate_strength(
        self, 
        counter_type: CounterArgumentType, 
        vulnerabilities: List[Vulnerability]
    ) -> ArgumentStrength:
        """Évalue la force du contre-argument en fonction du type et des vulnérabilités."""
        # Compter les vulnérabilités compatibles avec ce type de contre-argument
        compatible_vulns = [v for v in vulnerabilities if v.suggested_counter_type == counter_type]
        
        # Calculer le score moyen de ces vulnérabilités
        if compatible_vulns:
            avg_score = sum(v.score for v in compatible_vulns) / len(compatible_vulns)
        else:
            avg_score = 0.5  # Score moyen par défaut
        
        # Déterminer la force en fonction du score
        if avg_score >= 0.8:
            return ArgumentStrength.STRONG
        elif avg_score >= 0.6:
            return ArgumentStrength.MODERATE
        else:
            return ArgumentStrength.WEAK
    
    def _generate_supporting_evidence(
        self, 
        argument: Argument, 
        counter_type: CounterArgumentType
    ) -> List[str]:
        """Génère des preuves à l'appui du contre-argument."""
        # Dans une implémentation complète, ceci serait généré par un LLM
        if counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return ["Plusieurs études contredisent cette conclusion"]
        elif counter_type == CounterArgumentType.COUNTER_EXAMPLE:
            return ["Des cas spécifiques montrent que cette règle n'est pas universelle"]
        elif counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            return ["Les données empiriques ne soutiennent pas cette prémisse"]
        else:
            return []
    
    def _evaluate_relevance(self, original_argument: Argument, counter_argument: CounterArgument) -> float:
        """Évalue la pertinence du contre-argument par rapport à l'argument original."""
        # Implémentation simplifiée pour cette version
        return 0.8
    
    def _evaluate_logical_strength(self, counter_argument: CounterArgument) -> float:
        """Évalue la force logique du contre-argument."""
        # Implémentation simplifiée pour cette version
        strength_scores = {
            ArgumentStrength.WEAK: 0.4,
            ArgumentStrength.MODERATE: 0.6,
            ArgumentStrength.STRONG: 0.8,
            ArgumentStrength.DECISIVE: 0.9
        }
        return strength_scores.get(counter_argument.strength, 0.5)
    
    def _evaluate_persuasiveness(self, counter_argument: CounterArgument) -> float:
        """Évalue le pouvoir de persuasion du contre-argument."""
        # Implémentation simplifiée pour cette version
        return 0.7
    
    def _evaluate_originality(self, counter_argument: CounterArgument) -> float:
        """Évalue l'originalité du contre-argument."""
        # Implémentation simplifiée pour cette version
        return 0.6
    
    def _evaluate_clarity(self, counter_argument: CounterArgument) -> float:
        """Évalue la clarté du contre-argument."""
        # Implémentation simplifiée pour cette version
        return 0.8
    
    def _generate_recommendations(
        self, 
        original_argument: Argument, 
        counter_argument: CounterArgument,
        relevance: float,
        logical_strength: float,
        persuasiveness: float,
        originality: float,
        clarity: float
    ) -> List[str]:
        """Génère des recommandations pour améliorer le contre-argument."""
        recommendations = []
        
        if relevance < 0.6:
            recommendations.append("Améliorer la pertinence par rapport à l'argument original")
        
        if logical_strength < 0.6:
            recommendations.append("Renforcer la structure logique du contre-argument")
        
        if persuasiveness < 0.6:
            recommendations.append("Ajouter des éléments persuasifs comme des exemples concrets")
        
        if originality < 0.6:
            recommendations.append("Développer un angle plus original ou inattendu")
        
        if clarity < 0.6:
            recommendations.append("Clarifier la formulation pour améliorer la compréhension")
        
        if not recommendations:
            recommendations.append("Le contre-argument est de bonne qualité")
        
        return recommendations 
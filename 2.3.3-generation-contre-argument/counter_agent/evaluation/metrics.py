"""
Métriques d'évaluation pour l'agent de génération de contre-arguments.

Ce module fournit des métriques pour évaluer les performances
globales de l'agent de génération de contre-arguments.
"""

import numpy as np
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from ..agent.definitions import (
    Argument, 
    CounterArgument, 
    CounterArgumentType,
    ArgumentStrength,
    EvaluationResult
)

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Classe pour calculer et suivre les métriques de performance
    de l'agent de génération de contre-arguments.
    """
    
    def __init__(self):
        """Initialise le système de métriques."""
        self.metrics_history = {
            'relevance': [],
            'logical_strength': [],
            'persuasiveness': [],
            'originality': [],
            'clarity': [],
            'overall_score': [],
            'generation_time': [],
            'success_rate': []
        }
        
        self.counter_type_metrics = {ct.value: [] for ct in CounterArgumentType}
        self.last_metrics = {}
        
        logger.info("PerformanceMetrics initialisé")
    
    def record_metrics(
        self, 
        evaluation_result: EvaluationResult,
        counter_type: CounterArgumentType,
        generation_time: float,
        success: bool = True
    ) -> None:
        """
        Enregistre les métriques d'une évaluation.
        
        Args:
            evaluation_result: Le résultat de l'évaluation
            counter_type: Le type de contre-argument
            generation_time: Le temps de génération en secondes
            success: Si la génération a réussi
        """
        # Enregistrer les métriques générales
        self.metrics_history['relevance'].append(evaluation_result.relevance)
        self.metrics_history['logical_strength'].append(evaluation_result.logical_strength)
        self.metrics_history['persuasiveness'].append(evaluation_result.persuasiveness)
        self.metrics_history['originality'].append(evaluation_result.originality)
        self.metrics_history['clarity'].append(evaluation_result.clarity)
        self.metrics_history['overall_score'].append(evaluation_result.overall_score)
        self.metrics_history['generation_time'].append(generation_time)
        self.metrics_history['success_rate'].append(1.0 if success else 0.0)
        
        # Enregistrer les métriques par type de contre-argument
        self.counter_type_metrics[counter_type.value].append(evaluation_result.overall_score)
        
        # Mettre à jour les dernières métriques
        self.last_metrics = {
            'relevance': evaluation_result.relevance,
            'logical_strength': evaluation_result.logical_strength,
            'persuasiveness': evaluation_result.persuasiveness,
            'originality': evaluation_result.originality,
            'clarity': evaluation_result.clarity,
            'overall_score': evaluation_result.overall_score,
            'generation_time': generation_time,
            'counter_type': counter_type.value,
            'success': success
        }
        
        logger.debug(f"Métriques enregistrées pour {counter_type.value}, score: {evaluation_result.overall_score:.2f}")
    
    def get_summary_metrics(self) -> Dict[str, Any]:
        """
        Calcule les métriques de synthèse.
        
        Returns:
            Un dictionnaire contenant les métriques de synthèse
        """
        if not self.metrics_history['overall_score']:
            return {
                'average_relevance': 0.0,
                'average_logical_strength': 0.0,
                'average_persuasiveness': 0.0,
                'average_originality': 0.0,
                'average_clarity': 0.0,
                'average_overall_score': 0.0,
                'average_generation_time': 0.0,
                'success_rate': 0.0,
                'sample_count': 0,
                'best_counter_type': None,
                'worst_counter_type': None
            }
        
        # Calculer les moyennes
        average_metrics = {
            'average_relevance': np.mean(self.metrics_history['relevance']),
            'average_logical_strength': np.mean(self.metrics_history['logical_strength']),
            'average_persuasiveness': np.mean(self.metrics_history['persuasiveness']),
            'average_originality': np.mean(self.metrics_history['originality']),
            'average_clarity': np.mean(self.metrics_history['clarity']),
            'average_overall_score': np.mean(self.metrics_history['overall_score']),
            'average_generation_time': np.mean(self.metrics_history['generation_time']),
            'success_rate': np.mean(self.metrics_history['success_rate']),
            'sample_count': len(self.metrics_history['overall_score'])
        }
        
        # Déterminer les types de contre-arguments les plus et les moins performants
        type_performance = {}
        for counter_type, scores in self.counter_type_metrics.items():
            if scores:
                type_performance[counter_type] = np.mean(scores)
        
        if type_performance:
            best_type = max(type_performance.items(), key=lambda x: x[1])
            worst_type = min(type_performance.items(), key=lambda x: x[1])
            
            average_metrics['best_counter_type'] = {
                'type': best_type[0],
                'average_score': best_type[1]
            }
            
            average_metrics['worst_counter_type'] = {
                'type': worst_type[0],
                'average_score': worst_type[1]
            }
        else:
            average_metrics['best_counter_type'] = None
            average_metrics['worst_counter_type'] = None
        
        return average_metrics
    
    def get_performance_trends(self, window_size: int = 10) -> Dict[str, List[float]]:
        """
        Calcule les tendances de performance sur une fenêtre glissante.
        
        Args:
            window_size: La taille de la fenêtre glissante
            
        Returns:
            Un dictionnaire contenant les tendances de performance
        """
        if len(self.metrics_history['overall_score']) < window_size:
            return {
                'relevance_trend': [],
                'logical_strength_trend': [],
                'persuasiveness_trend': [],
                'overall_score_trend': [],
                'generation_time_trend': []
            }
        
        # Calculer les moyennes mobiles
        trends = {}
        for metric in ['relevance', 'logical_strength', 'persuasiveness', 'overall_score', 'generation_time']:
            values = self.metrics_history[metric]
            moving_averages = []
            
            for i in range(len(values) - window_size + 1):
                window = values[i:i+window_size]
                moving_averages.append(np.mean(window))
            
            trends[f'{metric}_trend'] = moving_averages
        
        return trends
    
    def get_counter_type_comparison(self) -> Dict[str, Dict[str, float]]:
        """
        Compare les performances des différents types de contre-arguments.
        
        Returns:
            Un dictionnaire comparant les types de contre-arguments
        """
        comparison = {}
        
        for counter_type, scores in self.counter_type_metrics.items():
            if scores:
                comparison[counter_type] = {
                    'average_score': np.mean(scores),
                    'max_score': np.max(scores),
                    'min_score': np.min(scores),
                    'std_dev': np.std(scores),
                    'count': len(scores)
                }
        
        return comparison
    
    def export_metrics_report(self) -> str:
        """
        Génère un rapport textuel des métriques.
        
        Returns:
            Un rapport textuel formaté
        """
        summary = self.get_summary_metrics()
        comparison = self.get_counter_type_comparison()
        
        report = "Rapport de performances de l'agent de génération de contre-arguments\n"
        report += "================================================================\n\n"
        
        # Métriques globales
        report += "MÉTRIQUES GLOBALES\n"
        report += "------------------\n"
        report += f"Nombre d'échantillons: {summary['sample_count']}\n"
        report += f"Taux de succès: {summary['success_rate']:.2%}\n"
        report += f"Score global moyen: {summary['average_overall_score']:.3f}\n"
        report += f"Temps de génération moyen: {summary['average_generation_time']:.3f} secondes\n\n"
        
        # Métriques détaillées
        report += "MÉTRIQUES DÉTAILLÉES\n"
        report += "--------------------\n"
        report += f"Pertinence moyenne: {summary['average_relevance']:.3f}\n"
        report += f"Force logique moyenne: {summary['average_logical_strength']:.3f}\n"
        report += f"Persuasion moyenne: {summary['average_persuasiveness']:.3f}\n"
        report += f"Originalité moyenne: {summary['average_originality']:.3f}\n"
        report += f"Clarté moyenne: {summary['average_clarity']:.3f}\n\n"
        
        # Comparaison des types de contre-arguments
        report += "COMPARAISON DES TYPES DE CONTRE-ARGUMENTS\n"
        report += "----------------------------------------\n"
        
        if summary['best_counter_type']:
            report += f"Meilleur type: {summary['best_counter_type']['type']} "
            report += f"(score: {summary['best_counter_type']['average_score']:.3f})\n"
        
        if summary['worst_counter_type']:
            report += f"Pire type: {summary['worst_counter_type']['type']} "
            report += f"(score: {summary['worst_counter_type']['average_score']:.3f})\n\n"
        
        # Détails par type
        report += "DÉTAILS PAR TYPE\n"
        report += "---------------\n"
        
        for counter_type, metrics in comparison.items():
            report += f"Type: {counter_type}\n"
            report += f"  Score moyen: {metrics['average_score']:.3f}\n"
            report += f"  Score max: {metrics['max_score']:.3f}\n"
            report += f"  Score min: {metrics['min_score']:.3f}\n"
            report += f"  Écart-type: {metrics['std_dev']:.3f}\n"
            report += f"  Nombre d'échantillons: {metrics['count']}\n\n"
        
        return report


class MetricsTracker:
    """
    Classe utilitaire pour suivre le temps d'exécution
    et d'autres métriques pendant la génération.
    """
    
    def __init__(self, metrics: PerformanceMetrics):
        """
        Initialise le tracker de métriques.
        
        Args:
            metrics: L'instance de PerformanceMetrics à utiliser
        """
        self.metrics = metrics
        self.start_time = None
        self.current_counter_type = None
        
        logger.debug("MetricsTracker initialisé")
    
    def start_tracking(self, counter_type: CounterArgumentType) -> None:
        """
        Commence à suivre le temps pour un type de contre-argument.
        
        Args:
            counter_type: Le type de contre-argument
        """
        self.start_time = time.time()
        self.current_counter_type = counter_type
        
        logger.debug(f"Début du suivi pour {counter_type.value}")
    
    def stop_tracking(self, evaluation_result: EvaluationResult, success: bool = True) -> float:
        """
        Arrête le suivi et enregistre les métriques.
        
        Args:
            evaluation_result: Le résultat de l'évaluation
            success: Si la génération a réussi
            
        Returns:
            Le temps d'exécution en secondes
        """
        if self.start_time is None or self.current_counter_type is None:
            logger.warning("Tentative d'arrêt du suivi sans démarrage préalable")
            return 0.0
        
        execution_time = time.time() - self.start_time
        
        # Enregistrer les métriques
        self.metrics.record_metrics(
            evaluation_result,
            self.current_counter_type,
            execution_time,
            success
        )
        
        logger.debug(f"Fin du suivi pour {self.current_counter_type.value}, temps: {execution_time:.3f}s")
        
        # Réinitialiser
        self.start_time = None
        self.current_counter_type = None
        
        return execution_time 
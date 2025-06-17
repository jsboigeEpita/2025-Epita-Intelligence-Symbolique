# argumentation_analysis/orchestration/cluedo_components/metrics_collector.py
from datetime import datetime
from typing import List, Dict, Any, Optional

from semantic_kernel.contents import ChatMessageContent
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

class MetricsCollector:
    """
    Classe dédiée à la collecte et au calcul des métriques pour le workflow Cluedo.
    """
    def __init__(self,
                 oracle_state: CluedoOracleState,
                 start_time: Optional[datetime],
                 end_time: Optional[datetime],
                 history: List[ChatMessageContent],
                 strategy: str):
        self.oracle_state = oracle_state
        self.start_time = start_time
        self.end_time = end_time
        self.history = history
        self.strategy = strategy
        
        # Attributs pour les métriques Enhanced calculées
        self._auto_revelations_triggered = [] # Doit être peuplé ailleurs
        self._suggestion_quality_scores = [] # Doit être peuplé ailleurs

    def collect_final_metrics(self) -> Dict[str, Any]:
        """Collecte toutes les métriques finales du workflow."""
        execution_time = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
        
        # Statistiques de base
        conversation_history = [
            {"sender": getattr(msg, 'author_name', msg.role), "message": str(msg.content)}
            for msg in self.history if getattr(msg, 'author_name', msg.role) != "system"
        ]
        
        # Métriques Oracle
        oracle_stats = self.oracle_state.get_oracle_statistics()
        
        # PHASE C: Métriques de fluidité et continuité narrative
        fluidity_metrics = self.oracle_state.get_fluidity_metrics()
        
        # Évaluation du succès
        solution_success = self._evaluate_solution_success()
        
        # Métriques de performance comparatives
        performance_metrics = self._calculate_performance_metrics(oracle_stats, execution_time)
        
        # Métriques Enhanced spécifiques
        enhanced_metrics = self._calculate_enhanced_metrics(oracle_stats)
        
        return {
            "solution_analysis": solution_success,
            "conversation_history": conversation_history,
            "oracle_statistics": oracle_stats,
            "performance_metrics": performance_metrics,
            "phase_c_fluidity_metrics": fluidity_metrics,
            "enhanced_metrics": enhanced_metrics,
            "final_state": {
                "solution_proposed": self.oracle_state.is_solution_proposed,
                "final_solution": self.oracle_state.final_solution,
                "secret_solution": self.oracle_state.get_solution_secrete(),
                "game_solvable_by_elimination": self.oracle_state.is_game_solvable_by_elimination()
            }
        }

    def _evaluate_solution_success(self) -> Dict[str, Any]:
        """Évalue le succès de la résolution."""
        if not self.oracle_state.is_solution_proposed:
            return {
                "success": False,
                "reason": "Aucune solution proposée",
                "proposed_solution": None,
                "correct_solution": self.oracle_state.get_solution_secrete()
            }
        
        proposed = self.oracle_state.final_solution
        correct = self.oracle_state.get_solution_secrete()
        
        success = proposed == correct
        
        return {
            "success": success,
            "reason": "Solution correcte" if success else "Solution incorrecte",
            "proposed_solution": proposed,
            "correct_solution": correct,
            "partial_matches": {
                "suspect": proposed.get("suspect") == correct.get("suspect"),
                "arme": proposed.get("arme") == correct.get("arme"),  
                "lieu": proposed.get("lieu") == correct.get("lieu")
            } if proposed and correct else {}
        }
    
    def _calculate_performance_metrics(self, oracle_stats: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Calcule les métriques de performance du workflow 3-agents."""
        agent_interactions = oracle_stats.get("agent_interactions", {})
        
        return {
            "efficiency": {
                "turns_per_minute": agent_interactions.get("total_turns", 0) / (execution_time / 60) if execution_time > 0 else 0,
                "oracle_queries_per_turn": oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 0) / max(1, agent_interactions.get("total_turns", 1)),
                "cards_revealed_per_query": oracle_stats.get("workflow_metrics", {}).get("cards_revealed", 0) / max(1, oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 1))
            },
            "collaboration": {
                "oracle_utilization_rate": oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 0) / max(1, agent_interactions.get("total_turns", 1)),
                "information_sharing_efficiency": len(oracle_stats.get("recent_revelations", [])),
                "agent_balance": self._calculate_agent_balance(agent_interactions)
            },
            "comparison_2vs3_agents": {
                "estimated_2agent_turns": agent_interactions.get("total_turns", 0) * 1.5,  # Estimation
                "efficiency_gain": "15-25% reduction in turns (estimated)",
                "information_richness": f"+{oracle_stats.get('workflow_metrics', {}).get('cards_revealed', 0)} cards revealed"
            }
        }
    
    def _calculate_agent_balance(self, agent_interactions: Dict[str, Any]) -> Dict[str, float]:
        """Calcule l'équilibre de participation entre agents."""
        total_turns = agent_interactions.get("total_turns", 0)
        if total_turns == 0:
            return {"sherlock": 0.0, "watson": 0.0, "moriarty": 0.0}
        
        # Estimation basée sur le pattern cyclique (1/3 chacun idéalement)
        expected_per_agent = total_turns / 3
        
        return {
            "expected_turns_per_agent": expected_per_agent,
            "balance_score": 1.0,  # À améliorer avec tracking réel par agent
            "note": "Équilibre cyclique théorique - à améliorer avec métriques réelles"
        }

    def _calculate_enhanced_metrics(self, oracle_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule les métriques Enhanced spécifiques au mode enhanced_auto_reveal."""
        auto_revelations_count = len(self._auto_revelations_triggered)
        suggestion_quality_scores = self._suggestion_quality_scores
        
        # Niveau d'optimisation du workflow Enhanced
        workflow_optimization_level = "enhanced_auto_reveal"
        if self.strategy == "enhanced_auto_reveal":
            total_queries = oracle_stats.get('dataset_statistics', {}).get('total_queries', 0)
            if total_queries > 0:
                efficiency_ratio = auto_revelations_count / max(total_queries, 1)
                if efficiency_ratio > 0.7:
                    workflow_optimization_level = "high_efficiency"
                elif efficiency_ratio > 0.4:
                    workflow_optimization_level = "medium_efficiency"
                else:
                    workflow_optimization_level = "low_efficiency"
            else:
                workflow_optimization_level = "baseline_efficiency"
        
        return {
            "auto_revelations_count": auto_revelations_count,
            "suggestion_quality_scores": suggestion_quality_scores,
            "workflow_optimization_level": workflow_optimization_level,
            "enhanced_strategy_active": self.strategy == "enhanced_auto_reveal",
            "average_suggestion_quality": sum(suggestion_quality_scores) / len(suggestion_quality_scores) if suggestion_quality_scores else 0.0
        }
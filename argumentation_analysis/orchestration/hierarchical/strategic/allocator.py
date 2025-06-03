"""
Module définissant l'Allocateur de Ressources de l'architecture hiérarchique.

L'Allocateur de Ressources est responsable de la gestion de l'allocation des ressources
computationnelles et cognitives, de la détermination des agents à activer, et de
l'établissement des priorités entre les différentes tâches d'analyse.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState


class ResourceAllocator:
    """
    Classe représentant l'Allocateur de Ressources de l'architecture hiérarchique.
    
    L'Allocateur de Ressources est responsable de:
    - Gérer l'allocation des ressources computationnelles et cognitives
    - Déterminer quels agents opérationnels doivent être activés
    - Établir les priorités entre les différentes tâches d'analyse
    - Optimiser l'utilisation des capacités des agents
    - Ajuster l'allocation en fonction des besoins émergents
    """
    
    def __init__(self, strategic_state: Optional[StrategicState] = None):
        """
        Initialise un nouvel Allocateur de Ressources.
        
        Args:
            strategic_state: L'état stratégique à utiliser. Si None, un nouvel état est créé.
        """
        self.state = strategic_state if strategic_state else StrategicState()
        self.logger = logging.getLogger(__name__)
        
        # Définir les capacités des agents disponibles
        self.agent_capabilities = {
            "informal_analyzer": {
                "specialties": ["argument_identification", "fallacy_detection", "rhetorical_analysis"],
                "efficiency": 0.8,
                "max_load": 1.0
            },
            "logic_analyzer": {
                "specialties": ["formal_logic", "validity_checking", "consistency_analysis"],
                "efficiency": 0.9,
                "max_load": 0.8
            },
            "extract_processor": {
                "specialties": ["text_extraction", "preprocessing", "reference_management"],
                "efficiency": 0.7,
                "max_load": 1.2
            },
            "visualizer": {
                "specialties": ["argument_visualization", "result_presentation", "summary_generation"],
                "efficiency": 0.6,
                "max_load": 0.5
            },
            "data_extractor": {
                "specialties": ["entity_extraction", "relation_detection", "metadata_analysis"],
                "efficiency": 0.75,
                "max_load": 0.9
            }
        }
    
    def allocate_initial_resources(self, strategic_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alloue les ressources initiales en fonction du plan stratégique.
        
        Args:
            strategic_plan: Le plan stratégique défini
            
        Returns:
            L'allocation des ressources
        """
        self.logger.info("Allocation initiale des ressources")
        
        # Extraire les phases et leurs priorités du plan stratégique
        phases = strategic_plan.get("phases", [])
        priorities = strategic_plan.get("priorities", {})
        
        # Analyser les besoins en ressources pour chaque phase
        phase_resource_needs = self._analyze_resource_needs(phases)
        
        # Déterminer les assignations d'agents
        agent_assignments = self._determine_agent_assignments(phases, phase_resource_needs)
        
        # Définir les niveaux de priorité des agents
        priority_levels = self._define_agent_priorities(agent_assignments, priorities)
        
        # Allouer le budget computationnel
        computational_budget = self._allocate_computational_budget(agent_assignments, priority_levels)
        
        # Mettre à jour l'état stratégique avec la nouvelle allocation
        allocation_update = {
            "agent_assignments": agent_assignments,
            "priority_levels": priority_levels,
            "computational_budget": computational_budget
        }
        
        self.state.update_resource_allocation(allocation_update)
        
        return self.state.resource_allocation
    
    def _analyze_resource_needs(self, phases: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Analyse les besoins en ressources pour chaque phase.
        
        Args:
            phases: Liste des phases du plan stratégique
            
        Returns:
            Dictionnaire des besoins en ressources par phase et par spécialité
        """
        phase_resource_needs = {}
        
        for phase in phases:
            phase_id = phase["id"]
            phase_resource_needs[phase_id] = {}
            
            # Analyser la description et les objectifs pour déterminer les besoins
            description = phase["description"].lower()
            
            # Initialiser les besoins pour toutes les spécialités
            all_specialties = set()
            for agent_info in self.agent_capabilities.values():
                all_specialties.update(agent_info["specialties"])
            
            for specialty in all_specialties:
                phase_resource_needs[phase_id][specialty] = 0.0
            
            # Ajuster les besoins en fonction de la description
            if "identification" in description or "éléments clés" in description:
                phase_resource_needs[phase_id]["argument_identification"] = 0.8
                phase_resource_needs[phase_id]["text_extraction"] = 0.7
                phase_resource_needs[phase_id]["entity_extraction"] = 0.6
            
            if "sophisme" in description or "analyse logique" in description:
                phase_resource_needs[phase_id]["fallacy_detection"] = 0.9
                phase_resource_needs[phase_id]["formal_logic"] = 0.8
                phase_resource_needs[phase_id]["validity_checking"] = 0.7
            
            if "synthèse" in description or "évaluation" in description:
                phase_resource_needs[phase_id]["consistency_analysis"] = 0.8
                phase_resource_needs[phase_id]["argument_visualization"] = 0.7
                phase_resource_needs[phase_id]["summary_generation"] = 0.9
            
            # Ajuster en fonction de la durée estimée
            duration_factor = {
                "short": 0.7,
                "medium": 1.0,
                "long": 1.3
            }.get(phase.get("estimated_duration", "medium"), 1.0)
            
            for specialty in phase_resource_needs[phase_id]:
                phase_resource_needs[phase_id][specialty] *= duration_factor
        
        return phase_resource_needs
    
    def _determine_agent_assignments(self, phases: List[Dict[str, Any]], 
                                   phase_resource_needs: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
        """
        Détermine quels agents doivent être assignés à quelles phases.
        
        Args:
            phases: Liste des phases du plan stratégique
            phase_resource_needs: Besoins en ressources par phase et par spécialité
            
        Returns:
            Dictionnaire des assignations d'agents par phase
        """
        agent_assignments = {}
        
        # Pour chaque agent, déterminer les phases auxquelles il devrait être assigné
        for agent_id, capabilities in self.agent_capabilities.items():
            agent_assignments[agent_id] = []
            agent_specialties = capabilities["specialties"]
            
            for phase in phases:
                phase_id = phase["id"]
                phase_needs = phase_resource_needs[phase_id]
                
                # Calculer la pertinence de l'agent pour cette phase
                relevance_score = 0.0
                for specialty in agent_specialties:
                    if specialty in phase_needs:
                        relevance_score += phase_needs[specialty]
                
                # Si l'agent est suffisamment pertinent, l'assigner à cette phase
                if relevance_score > 0.5:
                    agent_assignments[agent_id].append(phase_id)
        
        return agent_assignments
    
    def _define_agent_priorities(self, agent_assignments: Dict[str, List[str]], 
                               phase_priorities: Dict[str, str]) -> Dict[str, str]:
        """
        Définit les niveaux de priorité pour chaque agent.
        
        Args:
            agent_assignments: Assignations d'agents par phase
            phase_priorities: Priorités des phases
            
        Returns:
            Dictionnaire des niveaux de priorité par agent
        """
        priority_levels = {}
        
        for agent_id, assigned_phases in agent_assignments.items():
            if not assigned_phases:
                priority_levels[agent_id] = "low"
                continue
            
            # Déterminer la priorité en fonction des phases assignées
            priority_scores = {"high": 0, "medium": 0, "low": 0}
            
            for phase_id in assigned_phases:
                phase_priority = phase_priorities.get(phase_id, "medium")
                priority_scores[phase_priority] += 1
            
            # Attribuer la priorité en fonction des scores
            if priority_scores["high"] > 0:
                priority_levels[agent_id] = "high"
            elif priority_scores["medium"] > 0:
                priority_levels[agent_id] = "medium"
            else:
                priority_levels[agent_id] = "low"
        
        return priority_levels
    
    def _allocate_computational_budget(self, agent_assignments: Dict[str, List[str]], 
                                     priority_levels: Dict[str, str]) -> Dict[str, float]:
        """
        Alloue le budget computationnel à chaque agent.
        
        Args:
            agent_assignments: Assignations d'agents par phase
            priority_levels: Niveaux de priorité par agent
            
        Returns:
            Dictionnaire du budget computationnel par agent
        """
        computational_budget = {}
        
        # Facteurs de priorité pour l'allocation du budget
        priority_factors = {
            "high": 1.5,
            "medium": 1.0,
            "low": 0.5
        }
        
        # Calculer les scores de base pour chaque agent
        base_scores = {}
        total_score = 0.0
        
        for agent_id, assigned_phases in agent_assignments.items():
            # Le score de base dépend du nombre de phases assignées et de la priorité
            priority_factor = priority_factors.get(priority_levels.get(agent_id, "medium"), 1.0)
            phase_count_factor = min(len(assigned_phases), 3) / 3.0 if assigned_phases else 0.1
            
            base_scores[agent_id] = priority_factor * phase_count_factor
            total_score += base_scores[agent_id]
        
        # Normaliser les budgets pour qu'ils totalisent 1.0
        if total_score > 0:
            for agent_id, score in base_scores.items():
                computational_budget[agent_id] = score / total_score
        else:
            # Allocation par défaut si aucun score n'est calculé
            active_agents = [agent_id for agent_id, phases in agent_assignments.items() if phases]
            if active_agents:
                equal_share = 1.0 / len(active_agents)
                for agent_id in active_agents:
                    computational_budget[agent_id] = equal_share
        
        return computational_budget
    
    def adjust_allocation(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajuste l'allocation des ressources en fonction du feedback reçu.
        
        Args:
            feedback: Feedback sur l'utilisation des ressources
            
        Returns:
            L'allocation des ressources ajustée
        """
        self.logger.info("Ajustement de l'allocation des ressources")
        
        # Extraire les informations pertinentes du feedback
        resource_usage = feedback.get("resource_usage", {})
        bottlenecks = feedback.get("bottlenecks", [])
        idle_resources = feedback.get("idle_resources", [])
        
        # Préparer les ajustements
        allocation_adjustments = {
            "agent_assignments": {},
            "priority_levels": {},
            "computational_budget": {}
        }
        
        # Ajuster les priorités et le budget en fonction des bottlenecks
        for bottleneck in bottlenecks:
            agent_id = bottleneck.get("agent_id")
            severity = bottleneck.get("severity", "medium")
            
            if agent_id and agent_id in self.state.resource_allocation["priority_levels"]:
                # Augmenter la priorité
                allocation_adjustments["priority_levels"][agent_id] = "high"
                
                # Augmenter le budget computationnel
                current_budget = self.state.resource_allocation["computational_budget"].get(agent_id, 0.0)
                increase_factor = 1.5 if severity == "high" else 1.2
                allocation_adjustments["computational_budget"][agent_id] = min(current_budget * increase_factor, 0.5)
        
        # Réduire le budget des ressources inactives
        for idle_resource in idle_resources:
            agent_id = idle_resource.get("agent_id")
            idle_level = idle_resource.get("idle_level", "medium")
            
            if agent_id and agent_id in self.state.resource_allocation["computational_budget"]:
                # Réduire le budget computationnel
                current_budget = self.state.resource_allocation["computational_budget"].get(agent_id, 0.0)
                reduction_factor = 0.5 if idle_level == "high" else 0.8
                allocation_adjustments["computational_budget"][agent_id] = current_budget * reduction_factor
        
        # Normaliser le budget computationnel ajusté
        if allocation_adjustments["computational_budget"]:
            # Copier le budget actuel
            adjusted_budget = dict(self.state.resource_allocation["computational_budget"])
            
            # Appliquer les ajustements
            for agent_id, new_budget in allocation_adjustments["computational_budget"].items():
                adjusted_budget[agent_id] = new_budget
            
            # Calculer le total
            total_budget = sum(adjusted_budget.values())
            
            # Normaliser si nécessaire
            if total_budget > 1.0:
                for agent_id in adjusted_budget:
                    adjusted_budget[agent_id] /= total_budget
                
                # Mettre à jour les ajustements
                allocation_adjustments["computational_budget"] = adjusted_budget
        
        # Mettre à jour l'état stratégique avec les ajustements
        self.state.update_resource_allocation(allocation_adjustments)
        
        return self.state.resource_allocation
    
    def optimize_resource_utilization(self, performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimise l'utilisation des ressources en fonction des métriques de performance.
        
        Args:
            performance_metrics: Métriques de performance des agents
            
        Returns:
            L'allocation des ressources optimisée
        """
        self.logger.info("Optimisation de l'utilisation des ressources")
        
        # Extraire les métriques pertinentes
        agent_efficiency = performance_metrics.get("agent_efficiency", {})
        task_completion_rates = performance_metrics.get("task_completion_rates", {})
        
        # Calculer les scores d'efficacité pour chaque agent
        efficiency_scores = {}
        
        for agent_id, metrics in agent_efficiency.items():
            if agent_id not in self.state.resource_allocation["computational_budget"]:
                continue
            
            # Calculer un score d'efficacité basé sur plusieurs métriques
            processing_speed = metrics.get("processing_speed", 0.5)
            accuracy = metrics.get("accuracy", 0.5)
            resource_usage = metrics.get("resource_usage", 0.5)
            
            # Formule d'efficacité: combinaison pondérée de vitesse, précision et utilisation des ressources
            efficiency_scores[agent_id] = (0.4 * processing_speed + 0.4 * accuracy + 0.2 * (1.0 - resource_usage))
        
        # Ajuster le budget computationnel en fonction des scores d'efficacité
        budget_adjustments = {}
        
        if efficiency_scores:
            # Calculer le score total pour la normalisation
            total_score = sum(efficiency_scores.values())
            
            if total_score > 0:
                # Calculer le budget idéal basé sur l'efficacité
                for agent_id, score in efficiency_scores.items():
                    ideal_budget = score / total_score
                    current_budget = self.state.resource_allocation["computational_budget"].get(agent_id, 0.0)
                    
                    # Ajuster progressivement vers le budget idéal (50% du chemin)
                    budget_adjustments[agent_id] = current_budget + 0.5 * (ideal_budget - current_budget)
        
        # Mettre à jour l'état stratégique avec les ajustements
        if budget_adjustments:
            self.state.update_resource_allocation({
                "computational_budget": budget_adjustments
            })
        
        return self.state.resource_allocation
    
    def get_resource_allocation_snapshot(self) -> Dict[str, Any]:
        """
        Retourne un instantané de l'allocation actuelle des ressources.
        
        Returns:
            Un dictionnaire représentant l'allocation actuelle des ressources
        """
        return {
            "agent_assignments": self.state.resource_allocation["agent_assignments"],
            "priority_levels": self.state.resource_allocation["priority_levels"],
            "computational_budget": self.state.resource_allocation["computational_budget"]
        }
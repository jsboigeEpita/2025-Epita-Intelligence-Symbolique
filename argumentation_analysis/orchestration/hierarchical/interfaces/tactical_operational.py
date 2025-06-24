"""
Définit le contrat de communication entre les couches Tactique et Opérationnelle.

Ce module contient la classe `TacticalOperationalInterface`, qui sert de pont
entre la coordination des tâches (tactique) et leur exécution concrète par les
agents (opérationnelle).

Fonctions principales :
- Traduire les tâches tactiques (le "Comment") en commandes opérationnelles
  détaillées et exécutables (le "Faire").
- Recevoir les résultats bruts des agents, les nettoyer, les normaliser et les
  transmettre à la couche tactique pour analyse.
"""

from typing import Dict, List, Any, Optional, Callable
import logging
import uuid

from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.paths import DATA_DIR, RESULTS_DIR
from argumentation_analysis.core.communication import (
    MessageMiddleware, TacticalAdapter, OperationalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TacticalOperationalInterface:
    """
    Assure la traduction entre la planification tactique et l'exécution opérationnelle.

    Cette interface garantit que la couche tactique n'a pas besoin de connaître
    les détails d'implémentation des agents. Elle envoie des tâches abstraites,
    et cette interface les traduit en commandes spécifiques que les adaptateurs
    d'agents peuvent comprendre.

    Attributes:
        tactical_state (TacticalState): L'état de la couche tactique.
        operational_state (Optional[OperationalState]): L'état de la couche opérationnelle.
        logger (logging.Logger): Le logger pour l'interface.
        middleware (MessageMiddleware): Le middleware pour la communication.
        tactical_adapter (TacticalAdapter): L'adaptateur pour communiquer en tant que
                                            couche tactique.
        operational_adapter (OperationalAdapter): L'adaptateur pour communiquer
                                                  en tant que couche opérationnelle.
    """

    def __init__(self,
                 tactical_state: Optional[TacticalState] = None,
                 operational_state: Optional[OperationalState] = None,
                 middleware: Optional[MessageMiddleware] = None):
        """
        Initialise l'interface tactique-opérationnelle.

        Args:
            tactical_state: L'état de la couche tactique pour le contexte.
            operational_state: L'état de la couche opérationnelle pour le suivi.
            middleware: Le middleware de communication partagé.
        """
        self.tactical_state = tactical_state or TacticalState()
        self.operational_state = operational_state
        self.logger = logging.getLogger(__name__)

        self.middleware = middleware or MessageMiddleware()
        self.tactical_adapter = TacticalAdapter(agent_id="tactical_interface", middleware=self.middleware)
        self.operational_adapter = OperationalAdapter(
            agent_id="operational_interface",
            middleware=self.middleware
        )
    
    def translate_task_to_command(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traduit une tâche tactique en une commande opérationnelle détaillée.

        C'est la méthode principale du flux descendant. Elle prend une tâche
        abstraite du `TaskCoordinator` et l'enrichit avec tous les détails
        nécessaires pour l'exécution : techniques spécifiques, extraits de texte,
        paramètres, etc.

        Args:
            task: La tâche tactique à traduire.

        Returns:
            La commande opérationnelle enrichie, prête à être assignée à un agent.
        """
        self.logger.info(f"Traduction de la tâche {task.get('id', 'unknown')} en commande opérationnelle.")
        
        operational_task_id = f"op-{task.get('id', uuid.uuid4().hex[:8])}"
        required_capabilities = task.get("required_capabilities", [])
        
        operational_command = {
            "id": operational_task_id,
            "tactical_task_id": task.get("id"),
            "description": task.get("description", ""),
            "objective_id": task.get("objective_id", ""),
            "required_capabilities": required_capabilities,
            "techniques": self._determine_techniques(required_capabilities),
            "text_extracts": self._determine_relevant_extracts(task),
            "parameters": self._determine_execution_parameters(task),
            "expected_outputs": self._determine_expected_outputs(task),
            "priority": task.get("priority", "medium"),
            "deadline": self._determine_deadline(task),
            "context": self._get_local_context(task)
        }
        
        recipient_id = self._determine_appropriate_agent(required_capabilities)
        
        self.tactical_adapter.assign_task(
            task_type="operational_command",
            parameters=operational_command,
            recipient_id=recipient_id,
            priority=self._map_priority_to_enum(operational_command["priority"]),
            requires_ack=True,
            metadata={"objective_id": operational_command["objective_id"]}
        )
        
        self.logger.info(f"Commande {operational_task_id} assignée à l'agent {recipient_id}.")
        
        return operational_command
    
    def process_operational_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un résultat brut d'un agent et le consolide pour la couche tactique.

        C'est la méthode principale du flux ascendant. Elle prend les `outputs`
        bruts d'un agent, les nettoie, les structure et les agrège en un rapport
        de résultat que le `TaskCoordinator` peut utiliser pour mettre à jour
        son plan.

        Args:
            result: Le dictionnaire de résultat brut de l'agent.

        Returns:
            Le résultat consolidé et structuré pour la couche tactique.
        """
        self.logger.info(f"Traitement du résultat opérationnel pour la tâche {result.get('tactical_task_id', 'unknown')}")
        
        tactical_task_id = result.get("tactical_task_id")
        
        tactical_report = {
            "tactical_task_id": tactical_task_id,
            "completion_status": result.get("status", "completed"),
            "results": self._translate_outputs(result.get("outputs", {})),
            "results_path": str(RESULTS_DIR / f"{tactical_task_id}_results.json"),
            "execution_metrics": self._translate_metrics(result.get("metrics", {})),
            "issues": self._translate_issues(result.get("issues", []))
        }
        
        self.operational_adapter.send_result(
            task_id=tactical_task_id,
            result_type="task_completion_report",
            result=tactical_report,
            recipient_id="tactical_coordinator",
            metadata={"original_task_id": tactical_task_id}
        )
        
        return tactical_report

    def subscribe_to_operational_updates(self, update_types: List[str], callback: Callable) -> str:
        """
        Abonne la couche tactique aux mises à jour du niveau opérationnel.

        Permet un suivi en temps réel de l'exécution, par exemple pour implémenter
        des barres de progression ou des tableaux de bord.

        Args:
            update_types: Liste des types de mise à jour (ex: "task_progress").
            callback: La fonction à appeler lorsqu'une mise à jour est reçue.

        Returns:
            Un identifiant d'abonnement pour une éventuelle désinscription.
        """
        return self.tactical_adapter.subscribe_to_operational_updates(
            update_types=update_types,
            callback=callback
        )
    
    def request_operational_status(self, agent_id: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Demande le statut d'un agent opérationnel spécifique.

        Args:
            agent_id: L'identifiant de l'agent à interroger.
            timeout: Le délai d'attente en secondes.

        Returns:
            Le statut de l'agent, ou None en cas d'échec.
        """
        try:
            response = self.tactical_adapter.request_operational_info(
                request_type="agent_status",
                parameters={"agent_id": agent_id},
                recipient_id=agent_id,
                timeout=timeout
            )
            if response:
                self.logger.info(f"Statut de l'agent {agent_id} reçu")
                return response
            
            self.logger.warning(f"Timeout pour la demande de statut de l'agent {agent_id}")
            return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la demande de statut de l'agent {agent_id}: {e}")
            return None

    # Les méthodes privées restent inchangées car elles sont des détails d'implémentation.
    # ... (le reste des méthodes privées de _determine_techniques à _determine_appropriate_agent)
    def _determine_techniques(self, required_capabilities: List[str]) -> List[Dict[str, Any]]:
        capability_technique_mapping = {
            "argument_identification": [{"name": "premise_conclusion_extraction"}],
            "fallacy_detection": [{"name": "fallacy_pattern_matching"}],
            "complex_fallacy_analysis": [{"name": "complex_fallacy_analysis"}],
            "contextual_fallacy_analysis": [{"name": "contextual_fallacy_analysis"}],
            "formal_logic": [{"name": "propositional_logic_formalization"}]
        }
        techniques = []
        for capability in required_capabilities:
            if capability in capability_technique_mapping:
                techniques.extend(capability_technique_mapping[capability])
        return techniques

    def _determine_relevant_extracts(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"id": f"extract-{uuid.uuid4().hex[:8]}", "source": "raw_text", "content": "Extrait à analyser..."}]

    def _determine_execution_parameters(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"timeout": 60, "max_iterations": 3, "precision_target": 0.8}

    def _determine_expected_outputs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"generic_result": {"format": "object"}}

    def _determine_deadline(self, task: Dict[str, Any]) -> Optional[str]:
        return None

    def _get_local_context(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "position_in_workflow": self._determine_position_in_workflow(task),
            "related_tasks": self._find_related_tasks(task),
            "dependencies": self._translate_dependencies(task),
            "constraints": self._determine_constraints(task)
        }

    def _determine_position_in_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"phase": "intermediate", "is_first": False, "is_last": False}

    def _find_related_tasks(self, task: Dict[str, Any]) -> List[str]:
        related_tasks = []
        task_id = task.get("id")
        objective_id = task.get("objective_id")
        if not objective_id:
            return related_tasks
        for status, tasks in self.tactical_state.tasks.items():
            for other_task in tasks:
                if other_task.get("id") != task_id and other_task.get("objective_id") == objective_id:
                    related_tasks.append(other_task.get("id"))
        return related_tasks

    def _translate_dependencies(self, task: Dict[str, Any]) -> List[str]:
        dependencies = self.tactical_state.get_task_dependencies(task.get("id"))
        return [f"op-{dep_id}" for dep_id in dependencies]

    def _determine_constraints(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"max_runtime": 60, "min_confidence": 0.7}

    def _translate_outputs(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        return outputs

    def _translate_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "processing_time": metrics.get("execution_time", 0.0),
            "confidence_score": metrics.get("confidence", 0.0)
        }

    def _translate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tactical_issues = []
        for issue in issues:
            issue_type = issue.get("type")
            if issue_type == "execution_error":
                tactical_issues.append({"type": "task_failure", "description": issue.get("description")})
            elif issue_type == "timeout":
                tactical_issues.append({"type": "task_timeout", "description": "Timeout"})
            else:
                tactical_issues.append(issue)
        return tactical_issues

    def _map_priority_to_enum(self, priority: str) -> MessagePriority:
        return {"high": MessagePriority.HIGH, "medium": MessagePriority.NORMAL, "low": MessagePriority.LOW}.get(priority.lower(), MessagePriority.NORMAL)

    def _determine_appropriate_agent(self, required_capabilities: List[str]) -> str:
        capability_agent_mapping = {
            "argument_identification": "informal_analyzer",
            "fallacy_detection": "informal_analyzer",
            "formal_logic": "logic_analyzer",
            "text_extraction": "extract_processor",
            "complex_fallacy_analysis": "rhetorical_analyzer",
            "contextual_fallacy_analysis": "rhetorical_analyzer"
        }
        agent_counts = {}
        for capability in required_capabilities:
            agent = capability_agent_mapping.get(capability)
            if agent:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        if agent_counts:
            return max(agent_counts, key=agent_counts.get)
        
        return "default_operational_agent"
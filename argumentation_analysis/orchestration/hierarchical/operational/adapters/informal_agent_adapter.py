"""
Fournit un adaptateur pour intégrer `InformalAnalysisAgent` dans l'architecture.

Ce module contient la classe `InformalAgentAdapter`, qui sert de "traducteur"
entre les commandes génériques de l'`OperationalManager` et l'API spécifique de
l'`InformalAnalysisAgent`, spécialisé dans l'analyse de sophismes et
d'arguments informels.
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional
import semantic_kernel as sk

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.core.bootstrap import ProjectContext

class InformalAgentAdapter(OperationalAgent):
    """
    Traduit les commandes opérationnelles pour l'`InformalAnalysisAgent`.

    Cette classe implémente l'interface `OperationalAgent`. Son rôle est de :
    1.  Recevoir une tâche générique de l'`OperationalManager` (ex: "détecter les
        sophismes").
    2.  Traduire les "techniques" de cette tâche en appels de méthode concrets
        sur une instance de `InformalAnalysisAgent` (ex: appeler
        `self.agent.detect_fallacies(...)`).
    3.  Prendre les résultats retournés par l'agent.
    4.  Les reformater en un dictionnaire de résultat standardisé, attendu
        par l'`OperationalManager`.
    """

    def __init__(self, name: str = "InformalAgent", operational_state: Optional[OperationalState] = None, project_context: Optional[ProjectContext] = None):
        """
        Initialise l'adaptateur pour l'agent d'analyse informelle.

        Args:
            name: Le nom de l'instance de l'agent.
            operational_state: L'état opérationnel partagé.
            project_context: Le contexte du projet.
        """
        super().__init__(name, operational_state)
        self.agent: Optional[InformalAnalysisAgent] = None
        self.kernel: Optional[sk.Kernel] = None
        self.llm_service_id: Optional[str] = None
        self.project_context = project_context
        self.initialized = False
        self.logger = logging.getLogger(f"InformalAgentAdapter.{name}")

    async def initialize(self, kernel: sk.Kernel, llm_service_id: str) -> bool:
        """
        Initialise l'agent d'analyse informelle sous-jacent.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            llm_service_id: L'ID du service LLM à utiliser.

        Returns:
            True si l'initialisation a réussi, False sinon.
        """
        if self.initialized:
            return True
        
        self.kernel = kernel
        self.llm_service_id = llm_service_id
        
        try:
            self.logger.info("Initialisation de l'agent d'analyse informelle interne...")
            self.agent = InformalAnalysisAgent(kernel=self.kernel, agent_name=f"{self.name}_InformalAgent")
            self.agent.setup_agent_components(llm_service_id=self.llm_service_id)
            self.initialized = True
            self.logger.info("Agent d'analyse informelle interne initialisé.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent informel: {e}", exc_info=True)
            return False

    def get_capabilities(self) -> List[str]:
        """Retourne les capacités de cet agent."""
        return [
            "argument_identification",
            "fallacy_detection",
            "informal_analysis",
            "complex_fallacy_analysis",
            "contextual_fallacy_analysis",
            "fallacy_severity_evaluation"
        ]

    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """Vérifie si l'agent peut traiter la tâche."""
        if not self.initialized:
            return False
        required = task.get("required_capabilities", [])
        return any(cap in self.get_capabilities() for cap in required)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche en la traduisant en appels à l'InformalAnalysisAgent.

        Cette méthode est le cœur de l'adaptateur. Elle itère sur les techniques
        de la tâche. Pour chaque technique (ex: "fallacy_pattern_matching"),
        elle appelle la méthode correspondante de l'agent sous-jacent (ex:
        `self.agent.detect_fallacies`).

        Les résultats bruts sont ensuite collectés et formatés en une réponse
        standard pour la couche opérationnelle.

        Args:
            task: La tâche opérationnelle à traiter.

        Returns:
            Le résultat du traitement, formaté pour l'OperationalManager.
        """
        task_id = self.register_task(task)
        self.update_task_status(task_id, "in_progress")
        start_time = time.time()

        if not self.initialized:
            self.logger.error(f"Tentative de traitement de la tâche {task_id} sans initialisation.")
            return self.format_result(task, [], {}, [{"type": "initialization_error"}], task_id)

        try:
            results = []
            issues = []
            text_to_analyze = " ".join([extract.get("content", "") for extract in task.get("text_extracts", [])])
            if not text_to_analyze:
                 raise ValueError("Aucun contenu textuel trouvé dans `text_extracts`.")
            
            for technique in task.get("techniques", []):
                technique_name = technique.get("name")
                params = technique.get("parameters", {})
                
                # Traduction de la technique en appel de méthode de l'agent
                if technique_name == "premise_conclusion_extraction" and self.agent:
                    res = await self.agent.identify_arguments(text=text_to_analyze, parameters=params)
                    results.extend([{"type": "identified_arguments", **arg} for arg in res])
                elif technique_name == "fallacy_pattern_matching" and self.agent:
                    res = await self.agent.detect_fallacies(text=text_to_analyze, parameters=params)
                    results.extend([{"type": "identified_fallacies", **fallacy} for fallacy in res])
                else:
                    issues.append({"type": "unsupported_technique", "name": technique_name})

            metrics = {"execution_time": time.time() - start_time}
            status = "completed_with_issues" if issues else "completed"
            self.update_task_status(task_id, status)
            
            return self.format_result(task, results, metrics, issues, task_id)

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche {task_id}: {e}", exc_info=True)
            self.update_task_status(task_id, "failed")
            return self.format_result(task, [], {}, [{"type": "execution_error", "description": str(e)}], task_id)

    async def shutdown(self) -> bool:
        """Arrête l'adaptateur et nettoie les ressources."""
        self.logger.info("Arrêt de l'adaptateur d'agent informel.")
        self.agent = None
        self.kernel = None
        self.initialized = False
        return True

    def format_result(self, task: Dict[str, Any], results: List[Dict[str, Any]], metrics: Dict[str, Any], issues: List[Dict[str, Any]], task_id_to_report: Optional[str] = None) -> Dict[str, Any]:
        """Formate le résultat final dans la structure attendue."""
        final_task_id = task_id_to_report or task.get("id")
        
        outputs = {}
        for res_item in results:
            res_type = res_item.pop("type", "unknown")
            if res_type not in outputs:
                outputs[res_type] = []
            outputs[res_type].append(res_item)
            
        return {
            "id": f"result-{final_task_id}",
            "task_id": final_task_id,
            "tactical_task_id": task.get("tactical_task_id"),
            "status": "completed" if not issues else "completed_with_issues",
            "outputs": outputs,
            "metrics": metrics,
            "issues": issues
        }

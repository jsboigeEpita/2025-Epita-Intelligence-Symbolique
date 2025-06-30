"""
Fournit un adaptateur pour intégrer `ExtractAgent` dans l'architecture.

Ce module contient la classe `ExtractAgentAdapter`, qui sert de "traducteur"
entre le langage générique de l'`OperationalManager` et l'API spécifique de
l'`ExtractAgent`.
"""

import logging
import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional

from argumentation_analysis.core.bootstrap import ProjectContext
from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.core.communication import MessageMiddleware
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractResult


class ExtractAgentAdapter(OperationalAgent):
    """
    Traduit les commandes opérationnelles pour l'`ExtractAgent`.

    Cette classe implémente l'interface `OperationalAgent`. Son rôle est de :
    1.  Recevoir une tâche générique de l'`OperationalManager`.
    2.  Traduire les "techniques" et "paramètres" de cette tâche en appels
        de méthode concrets sur une instance de `ExtractAgent`.
    3.  Invoquer l'agent sous-jacent.
    4.  Prendre le `ExtractResult` retourné par l'agent.
    5.  Le reformater en un dictionnaire de résultat standardisé, attendu
        par l'`OperationalManager`.
    """

    def __init__(self, name: str = "ExtractAgent",
                 operational_state: Optional[OperationalState] = None,
                 middleware: Optional[MessageMiddleware] = None,
                 project_context: Optional[ProjectContext] = None):
        """
        Initialise l'adaptateur pour l'agent d'extraction.

        Args:
            name: Le nom de l'instance de l'agent.
            operational_state: L'état opérationnel partagé.
            middleware: Le middleware de communication.
            project_context: Le contexte du projet.
        """
        super().__init__(name, operational_state, middleware=middleware)
        self.agent: Optional[ExtractAgent] = None
        self.kernel: Optional[Any] = None
        self.llm_service_id: Optional[str] = None
        self.project_context = project_context
        self.initialized = False
        self.logger = logging.getLogger(f"ExtractAgentAdapter.{name}")

    async def initialize(self, kernel: Any, llm_service_id: str, project_context: ProjectContext) -> bool:
        """
        Initialise l'agent d'extraction sous-jacent avec son kernel.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            llm_service_id: L'ID du service LLM à utiliser.
            project_context: Le contexte du projet.

        Returns:
            True si l'initialisation a réussi, False sinon.
        """
        if self.initialized:
            return True
        
        self.kernel = kernel
        self.llm_service_id = llm_service_id
        self.project_context = project_context

        try:
            self.logger.info("Initialisation de l'agent d'extraction interne...")
            self.agent = ExtractAgent(kernel=self.kernel, agent_name=f"{self.name}_ExtractAgent", llm_service_id=self.llm_service_id)
            
            if self.agent is None:
                self.logger.error("Échec de l'instanciation de l'agent d'extraction.")
                return False
            
            self.initialized = True
            self.logger.info("Agent d'extraction interne initialisé.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent: {e}", exc_info=True)
            return False

    def get_capabilities(self) -> List[str]:
        """Retourne les capacités de cet agent."""
        return [
            "text_extraction",
            "preprocessing",
            "extract_validation"
        ]

    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """Vérifie si l'agent peut traiter la tâche."""
        if not self.initialized:
            return False
        
        required = task.get("required_capabilities", [])
        return any(cap in self.get_capabilities() for cap in required)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche en la traduisant en appels à l'ExtractAgent.

        Cette méthode est le cœur de l'adaptateur. Elle parcourt les "techniques"
        spécifiées dans la tâche opérationnelle. Pour chaque technique, elle
        appelle la méthode privée correspondante (ex: `_process_extract`) qui
        elle-même appelle l'agent `ExtractAgent` sous-jacent.

        Les résultats de chaque appel sont collectés, et à la fin, l'ensemble
        est formaté en un seul dictionnaire de résultat standard.

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
            techniques = task.get("techniques", [])
            text_extracts = task.get("text_extracts", [])

            if not text_extracts:
                raise ValueError("Aucun extrait de texte (`text_extracts`) fourni dans la tâche.")

            for technique in techniques:
                technique_name = technique.get("name")
                params = technique.get("parameters", {})
                
                if technique_name == "relevant_segment_extraction":
                    for extract in text_extracts:
                        extract_result = await self._process_extract(extract, params)
                        if extract_result.status == "valid":
                            results.append({
                                "type": "extracted_segments",
                                "extract_id": extract.get("id"),
                                "content": extract_result.extracted_text,
                            })
                        else:
                            issues.append({"type": "extraction_error", "description": extract_result.message})
                # Ajouter d'autres techniques ici si nécessaire
            
            metrics = {"execution_time": time.time() - start_time}
            status = "completed_with_issues" if issues else "completed"
            self.update_task_status(task_id, status)
            
            return self.format_result(task, results, metrics, issues, task_id)

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche {task_id}: {e}", exc_info=True)
            self.update_task_status(task_id, "failed")
            return self.format_result(task, [], {}, [{"type": "execution_error", "description": str(e)}], task_id)

    async def _process_extract(self, extract: Dict[str, Any], parameters: Dict[str, Any]) -> ExtractResult:
        """Appelle la méthode d'extraction de l'agent sous-jacent."""
        if not self.agent:
            raise RuntimeError("Agent `ExtractAgent` non initialisé.")

        source_info = {
            "source_name": extract.get("source", "Source inconnue"),
            "source_text": extract.get("content", "")
        }
        extract_name = extract.get("id", "Extrait sans nom")
        
        return await self.agent.extract_from_name(source_info, extract_name)
    
    async def shutdown(self) -> bool:
        """Arrête l'adaptateur et nettoie les ressources."""
        self.logger.info("Arrêt de l'adaptateur d'agent d'extraction.")
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
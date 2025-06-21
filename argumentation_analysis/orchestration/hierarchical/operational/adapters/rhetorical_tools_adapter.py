"""
Fournit un adaptateur pour les outils avancés d'analyse rhétorique.

Ce module contient la classe `RhetoricalToolsAdapter`, qui sert de point d'entrée
unifié pour un ensemble d'outils spécialisés dans l'analyse fine de la
rhétorique, comme l'analyse de sophismes complexes, l'évaluation de la
cohérence ou la visualisation de structures argumentatives.
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.core.bootstrap import ProjectContext

# L'agent RhetoricalAnalysisAgent est supposé encapsuler ces outils.
# Pour l'instant, un Mock est utilisé.
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
# ... autres imports d'outils ...

# TODO: Remplacer ce mock par le véritable agent une fois qu'il sera créé.
class MockRhetoricalAnalysisAgent:
    """Mock de l'agent d'analyse rhétorique pour le développement."""
    def __init__(self, kernel, agent_name, project_context: ProjectContext):
        self.logger = logging.getLogger(agent_name)
        # Les outils seraient initialisés ici
    async def setup_agent_components(self, llm_service_id):
        self.logger.info("MockRhetoricalAnalysisAgent setup.")
    async def analyze_complex_fallacies(self, arguments: List[str], context: str, **kwargs):
        self.logger.info("Mock-analysing complex fallacies.")
        return [{"mock_result": "complex"}]
    async def analyze_contextual_fallacies(self, text: str, context: str, **kwargs):
        self.logger.info("Mock-analysing contextual fallacies.")
        return [{"mock_result": "contextual"}]
    # ... autres méthodes mock ...

RhetoricalAnalysisAgent = MockRhetoricalAnalysisAgent


class RhetoricalToolsAdapter(OperationalAgent):
    """
    Traduit les commandes opérationnelles pour le `RhetoricalAnalysisAgent`.

    Cette classe agit comme une façade pour un ensemble d'outils d'analyse
    rhétorique avancée, exposés via un agent unique (actuellement un mock).
    Son rôle est de :
    1.  Recevoir une tâche générique (ex: "évaluer la cohérence").
    2.  Identifier la bonne méthode à appeler sur l'agent rhétorique sous-jacent.
    3.  Transmettre les paramètres et le contexte nécessaires.
    4.  Formatter la réponse de l'outil en un résultat opérationnel standard.
    """

    def __init__(self, name: str = "RhetoricalTools", operational_state: Optional[OperationalState] = None, project_context: Optional[ProjectContext] = None):
        """
        Initialise l'adaptateur pour les outils d'analyse rhétorique.

        Args:
            name: Le nom de l'instance de l'agent.
            operational_state: L'état opérationnel partagé.
            project_context: Le contexte global du projet.
        """
        super().__init__(name, operational_state)
        self.logger = logging.getLogger(f"RhetoricalToolsAdapter.{name}")
        self.agent: Optional[RhetoricalAnalysisAgent] = None
        self.kernel: Optional[Any] = None
        self.llm_service_id: Optional[str] = None
        self.project_context = project_context
        self.initialized = False

    async def initialize(self, kernel: Any, llm_service_id: str, project_context: ProjectContext) -> bool:
        """
        Initialise l'agent d'analyse rhétorique sous-jacent.

        Args:
            kernel: Le kernel Semantic Kernel.
            llm_service_id: L'ID du service LLM.
            project_context: Le contexte global du projet.

        Returns:
            True si l'initialisation réussit.
        """
        if self.initialized:
            return True
        
        self.kernel = kernel
        self.llm_service_id = llm_service_id
        self.project_context = project_context

        if not self.project_context:
            self.logger.error("ProjectContext est requis pour l'initialisation.")
            return False

        try:
            self.logger.info("Initialisation de l'agent d'analyse rhétorique...")
            self.agent = RhetoricalAnalysisAgent(kernel=self.kernel, agent_name=f"{self.name}_RhetoricalAgent", project_context=self.project_context)
            await self.agent.setup_agent_components(llm_service_id=self.llm_service_id)
            self.initialized = True
            self.logger.info("Agent d'analyse rhétorique initialisé.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent rhétorique: {e}", exc_info=True)
            return False

    def get_capabilities(self) -> List[str]:
        """Retourne les capacités de cet agent."""
        return [
            "complex_fallacy_analysis",
            "contextual_fallacy_analysis",
            "fallacy_severity_evaluation",
            "argument_structure_visualization",
            "argument_coherence_evaluation",
            "semantic_argument_analysis",
            "contextual_fallacy_detection"
        ]

    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """Vérifie si l'agent peut traiter la tâche."""
        if not self.initialized:
            return False
        required = task.get("required_capabilities", [])
        return any(cap in self.get_capabilities() for cap in required)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche en l'aiguillant vers le bon outil d'analyse rhétorique.

        Args:
            task: La tâche opérationnelle à traiter.

        Returns:
            Le résultat du traitement, formaté.
        """
        task_id = self.register_task(task)
        self.update_task_status(task_id, "in_progress")
        start_time = time.time()

        if not self.agent:
             return self.format_result(task, [], {}, [{"type": "initialization_error"}], task_id)
        
        try:
            results = []
            issues = []
            text_to_analyze = " ".join([extract.get("content", "") for extract in task.get("text_extracts", [])])
            arguments = self._extract_arguments(text_to_analyze)

            for technique in task.get("techniques", []):
                technique_name = technique.get("name")
                params = technique.get("parameters", {})
                context = params.get("context", "général")
                
                # Aiguillage vers la méthode correspondante de l'agent.
                if technique_name == "complex_fallacy_analysis":
                    res = await self.agent.analyze_complex_fallacies(arguments, context, parameters=params)
                    results.append({"type": technique_name, **res})
                elif technique_name == "contextual_fallacy_analysis":
                    res = await self.agent.analyze_contextual_fallacies(text_to_analyze, context, parameters=params)
                    results.append({"type": technique_name, **res})
                # ... ajouter les autres cas d'aiguillage ici ...
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

    def _extract_arguments(self, text: str) -> List[str]:
        """Méthode simple pour extraire des arguments (paragraphes)."""
        return [p.strip() for p in text.split('\n\n') if p.strip()]

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
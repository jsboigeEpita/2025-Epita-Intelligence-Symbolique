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

# Importe le plugin consolidé qui remplace les outils individuels.
try:
    from plugins.AnalysisToolsPlugin.plugin import AnalysisToolsPlugin
    PLUGIN_ANALYSIS_AVAILABLE = True
except ImportError:
    AnalysisToolsPlugin = None
    PLUGIN_ANALYSIS_AVAILABLE = False


class RhetoricalToolsAdapter(OperationalAgent):
    """
    Traduit les commandes opérationnelles pour le `AnalysisToolsPlugin`.
    """

    def __init__(self, name: str = "RhetoricalTools", operational_state: Optional[OperationalState] = None, project_context: Optional[ProjectContext] = None):
        """
        Initialise l'adaptateur pour les outils d'analyse rhétorique.
        """
        super().__init__(name, operational_state)
        self.logger = logging.getLogger(f"RhetoricalToolsAdapter.{name}")
        self.analysis_plugin: Optional[AnalysisToolsPlugin] = None
        self.initialized = False

    async def initialize(self, kernel: Any, llm_service_id: str, project_context: ProjectContext) -> bool:
        """
        Initialise le plugin d'analyse.
        """
        if self.initialized:
            return True
        
        if not PLUGIN_ANALYSIS_AVAILABLE:
            self.logger.error("Le plugin d'analyse n'a pas pu être importé. L'adaptateur ne peut pas fonctionner.")
            return False

        try:
            self.logger.info("Initialisation du AnalysisToolsPlugin via l'adaptateur...")
            # L'initialisation du plugin se fait maintenant en interne
            self.analysis_plugin = AnalysisToolsPlugin()
            self.initialized = True
            self.logger.info("AnalysisToolsPlugin initialisé.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du plugin d'analyse: {e}", exc_info=True)
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
        Traite une tâche en utilisant le AnalysisToolsPlugin.
        """
        task_id = self.register_task(task)
        self.update_task_status(task_id, "in_progress")
        start_time = time.time()

        if not self.analysis_plugin:
             return self.format_result(task, [], {}, [{"type": "initialization_error", "description": "AnalysisToolsPlugin non initialisé."}], task_id)
        
        try:
            results = []
            issues = []
            text_to_analyze = " ".join([extract.get("content", "") for extract in task.get("text_extracts", [])])
            context = task.get("context", "général")

            # La logique ici est simplifiée : on suppose une analyse globale.
            # L'aiguillage fin par "technique" est maintenant une responsabilité interne au plugin.
            # Pour ce refactoring, nous appelons la capacité principale du plugin.
            
            analysis_result = self.analysis_plugin.analyze_text(text_to_analyze, context)
            results.append({"type": "full_rhetorical_analysis", **analysis_result})

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
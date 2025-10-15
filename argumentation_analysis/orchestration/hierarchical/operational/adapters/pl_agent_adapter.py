"""
Fournit un adaptateur pour intégrer `PropositionalLogicAgent` dans l'architecture.

Ce module contient la classe `PLAgentAdapter`, qui sert de "traducteur"
entre les commandes génériques de l'`OperationalManager` et l'API spécifique du
`PropositionalLogicAgent`, spécialisé dans l'analyse logique formelle.
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional
import semantic_kernel as sk

from argumentation_analysis.core.bootstrap import ProjectContext
from argumentation_analysis.core.communication import MessageMiddleware
from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import (
    OperationalAgent,
)
from argumentation_analysis.orchestration.hierarchical.operational.state import (
    OperationalState,
)
from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)
from argumentation_analysis.core.jvm_setup import initialize_jvm


class PLAgentAdapter(OperationalAgent):
    """
    Traduit les commandes opérationnelles pour le `PropositionalLogicAgent`.

    Cette classe implémente l'interface `OperationalAgent`. Son rôle est de :
    1.  Recevoir une tâche générique de l'`OperationalManager` (ex: "vérifier
        la validité logique").
    2.  Traduire les "techniques" de cette tâche en appels de méthode concrets
        sur une instance de `PropositionalLogicAgent` (ex: appeler
        `self.agent.check_pl_validity(...)`).
    3.  Prendre les résultats retournés par l'agent (souvent des structures de
        données complexes incluant des "belief sets" et des résultats de "queries").
    4.  Les reformater en un dictionnaire de résultat standardisé, attendu
        par l'`OperationalManager`.
    """

    def __init__(
        self,
        name: str = "PLAgent",
        operational_state: Optional[OperationalState] = None,
        middleware: Optional[MessageMiddleware] = None,
        project_context: Optional[ProjectContext] = None,
    ):
        """
        Initialise l'adaptateur pour l'agent de logique propositionnelle.

        Args:
            name: Le nom de l'instance de l'agent.
            operational_state: L'état opérationnel partagé.
            middleware: Le middleware de communication.
            project_context: Le contexte du projet.
        """
        super().__init__(name, operational_state, middleware=middleware)
        self.agent: Optional[PropositionalLogicAgent] = None
        self.kernel: Optional[sk.Kernel] = None
        self.llm_service_id: Optional[str] = None
        self.project_context = project_context
        self.initialized = False
        self.logger = logging.getLogger(f"PLAgentAdapter.{name}")

    async def initialize(
        self, kernel: sk.Kernel, llm_service_id: str, project_context: ProjectContext
    ) -> bool:
        """
        Initialise l'agent de logique propositionnelle sous-jacent.

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
            self.logger.info(
                "Démarrage de la JVM pour l'agent PL (géré par la fixture de test globale)..."
            )
            # L'initialisation de la JVM est maintenant gérée par une fixture pytest de portée session (`jvm_session`)
            # pour éviter les démarrages multiples qui causent des crashs. L'appel direct est désactivé.
            # if not initialize_jvm():
            #     raise RuntimeError("La JVM n'a pas pu être initialisée.")

            self.logger.info("Initialisation de l'agent PL interne...")
            self.agent = PropositionalLogicAgent(
                kernel=self.kernel,
                agent_name=f"{self.name}_PLAgent",
                service_id=self.llm_service_id,
            )
            self.initialized = True
            self.logger.info("Agent PL interne initialisé.")
            return True
        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'initialisation de l'agent PL: {e}", exc_info=True
            )
            return False

    def get_capabilities(self) -> List[str]:
        """Retourne les capacités de cet agent."""
        return [
            "formal_logic",
            "propositional_logic",
            "validity_checking",
            "consistency_analysis",
        ]

    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """Vérifie si l'agent peut traiter la tâche."""
        if not self.initialized:
            return False
        required = task.get("required_capabilities", [])
        return any(cap in self.get_capabilities() for cap in required)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche en la traduisant en appels au PropositionalLogicAgent.

        Le cœur de l'adaptateur : il itère sur les techniques de la tâche
        et appelle la méthode correspondante de l'agent sous-jacent.
        Les résultats bruts sont ensuite collectés et formatés.

        Args:
            task: La tâche opérationnelle à traiter.

        Returns:
            Le résultat du traitement, formaté pour l'OperationalManager.
        """
        task_id = self.register_task(task)
        self.update_task_status(task_id, "in_progress")
        start_time = time.time()

        if not self.initialized:
            self.logger.error(
                f"Tentative de traitement de la tâche {task_id} sans initialisation."
            )
            return self.format_result(
                task, [], {}, [{"type": "initialization_error"}], task_id
            )
        if not self.agent:
            return self.format_result(
                task, [], {}, [{"type": "agent_not_found"}], task_id
            )

        try:
            results = []
            issues = []
            text_to_analyze = " ".join(
                [
                    extract.get("content", "")
                    for extract in task.get("text_extracts", [])
                ]
            )
            if not text_to_analyze:
                raise ValueError("Aucun contenu textuel trouvé dans `text_extracts`.")

            for technique in task.get("techniques", []):
                technique_name = technique.get("name")
                params = technique.get("parameters", {})

                # Traduction de la technique en appel de méthode
                if technique_name == "propositional_logic_formalization":
                    res = await self.agent.formalize_to_pl(
                        text=text_to_analyze, parameters=params
                    )
                    if res:
                        results.append({"type": "formal_analyses", "belief_set": res})
                    else:
                        issues.append(
                            {
                                "type": "formalization_error",
                                "description": "L'agent n'a pas pu formaliser le texte.",
                            }
                        )
                elif technique_name == "validity_checking":
                    res = await self.agent.check_pl_validity(
                        text=text_to_analyze, parameters=params
                    )
                    results.append({"type": "validity_analysis", **res})
                elif technique_name == "consistency_checking":
                    res = await self.agent.check_pl_consistency(
                        text=text_to_analyze, parameters=params
                    )
                    results.append({"type": "consistency_analysis", **res})
                else:
                    issues.append(
                        {"type": "unsupported_technique", "name": technique_name}
                    )

            metrics = {"execution_time": time.time() - start_time}
            status = "completed_with_issues" if issues else "completed"
            self.update_task_status(task_id, status)
            return self.format_result(task, results, metrics, issues, task_id)

        except Exception as e:
            self.logger.error(
                f"Erreur lors du traitement de la tâche {task_id}: {e}", exc_info=True
            )
            self.update_task_status(task_id, "failed")
            return self.format_result(
                task,
                [],
                {},
                [{"type": "execution_error", "description": str(e)}],
                task_id,
            )

    async def shutdown(self) -> bool:
        """Arrête l'adaptateur et nettoie les ressources."""
        self.logger.info("Arrêt de l'adaptateur d'agent PL.")
        self.agent = None
        self.kernel = None
        self.initialized = False
        # Note : La JVM n'est pas arrêtée ici, car elle peut être partagée.
        return True

    def format_result(
        self,
        task: Dict[str, Any],
        results: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        issues: List[Dict[str, Any]],
        task_id_to_report: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            "issues": issues,
        }

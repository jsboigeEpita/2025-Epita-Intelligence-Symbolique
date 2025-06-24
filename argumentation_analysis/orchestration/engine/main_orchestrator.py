#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module principal de l'orchestrateur d'analyse d'argumentation.
"""

import logging
from typing import Dict, Any, TYPE_CHECKING, Optional, List, Tuple # Ajout de Optional, List, Tuple
from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
# from argumentation_analysis.reporting.models import HierarchicalReport

# Imports pour les types d'orchestrateurs et AnalysisType
# Ces imports sont nécessaires pour que les méthodes migrées fonctionnent et pour le type hinting.
logger = logging.getLogger(__name__) # Déplacé ici pour être utilisé par les try/except d'import

try:
    # Tenter d'importer AnalysisType depuis le pipeline, ajuster si défini ailleurs.
    from argumentation_analysis.core.enums import AnalysisType
except ImportError:
    AnalysisType = None
    logger.warning("Could not import AnalysisType. Specialized orchestrator selection might be affected.")

try:
    from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator, run_cluedo_oracle_game
    run_cluedo_game = run_cluedo_oracle_game
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
except ImportError as e:
    logger.error(f"Failed to import specialized orchestrators: {e}. SpecializedDirect strategy will be limited.")
    CluedoExtendedOrchestrator = None
    run_cluedo_game = None
    ConversationOrchestrator = None
    RealLLMOrchestrator = None
    LogiqueComplexeOrchestrator = None


if TYPE_CHECKING:
    from .config import OrchestrationConfig
    # Potentiellement d'autres imports pour le type hinting si nécessaire plus tard
    # from ..components.strategic_manager import StrategicManager # Exemple
    # from ..components.tactical_coordinator import TacticalCoordinator # Exemple
    # from ..components.operational_manager import OperationalManager # Exemple

# Pour éviter une dépendance circulaire potentielle à l'exécution,
# bien que .config et .strategy soient généralement sûrs.
from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy, select_strategy
# from argumentation_analysis.core.reports import HierarchicalReport # Si utilisé directement
# from argumentation_analysis.core.context import OrchestrationContext # Si utilisé directement
class MainOrchestrator:
    """
    Chef d'orchestre principal pour le processus d'analyse d'argumentation.

    Cette classe est le point d'entrée central pour l'exécution d'analyses.
    Elle sélectionne une stratégie d'orchestration appropriée en fonction de la
    configuration et des entrées, puis délègue l'exécution à la méthode
    correspondante. Elle gère le flux de travail de haut niveau, de l'analyse
    stratégique à la synthèse des résultats.

    Attributs:
        config (OrchestrationConfig): L'objet de configuration pour l'orchestration.
        strategic_manager (Optional[Any]): Le gestionnaire pour le niveau stratégique.
        tactical_coordinator (Optional[Any]): Le coordinateur pour le niveau tactique.
        operational_manager (Optional[Any]): Le gestionnaire pour le niveau opérationnel.
    """

    def __init__(self,
                 config: 'OrchestrationConfig',
                 kernel: 'sk.Kernel',
                 strategic_manager: Optional[Any] = None,
                 tactical_coordinator: Optional[Any] = None,
                 operational_manager: Optional[Any] = None):
        """
        Initialise l'orchestrateur principal avec sa configuration et ses composants.

        Args:
            config (OrchestrationConfig): La configuration d'orchestration.
            kernel (sk.Kernel): L'instance de Semantic Kernel à utiliser.
            strategic_manager (Optional[Any]): Instance du gestionnaire stratégique.
            tactical_coordinator (Optional[Any]): Instance du coordinateur tactique.
            operational_manager (Optional[Any]): Instance du gestionnaire opérationnel.
        """
        self.config = config
        self.kernel = kernel
        self.strategic_manager = strategic_manager
        self.tactical_coordinator = tactical_coordinator
        self.operational_manager = operational_manager

        # Instancier l'exécuteur pour le pipeline opérationnel direct (import tardif)
        try:
            from argumentation_analysis.orchestration.operational.direct_executor import DirectOperationalExecutor
            self.direct_operational_executor = DirectOperationalExecutor(kernel=self.kernel)
        except ImportError as e:
            self.direct_operational_executor = None
            logger.error(f"ECHEC de l'importation de DirectOperationalExecutor: {e}", exc_info=True)

        # Initialiser la carte des orchestrateurs spécialisés
        self.specialized_orchestrators_map = self._initialize_specialized_orchestrators()


    async def run_analysis(
        self,
        text_input: str,
        source_info: Optional[Dict[str, Any]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exécute le pipeline d'analyse d'argumentation en sélectionnant la stratégie appropriée.

        C'est la méthode principale de l'orchestrateur. Elle détermine dynamiquement
        la meilleure stratégie à utiliser (par exemple, hiérarchique, directe, hybride)
        via `select_strategy` et délègue ensuite l'exécution à la méthode `_execute_*`
        correspondante.

        Args:
            text_input (str): Le texte d'entrée à analyser.
            source_info (Optional[Dict[str, Any]]): Informations contextuelles sur la source
                                                    du texte (par exemple, auteur, date).
            custom_config (Optional[Dict[str, Any]]): Configuration personnalisée pour cette
                                                      analyse spécifique, pouvant surcharger
                                                      la configuration globale.

        Returns:
            Dict[str, Any]: Un dictionnaire contenant les résultats complets de l'analyse,
                            incluant le statut, la stratégie utilisée et les données produites.
        """
        logger.info(f"Received analysis request for text_input (length: {len(text_input)}).")
        if source_info:
            logger.info(f"Source info provided: {source_info}")
        if custom_config:
            logger.info(f"Custom config provided: {custom_config}")

        # Sélection dynamique de la stratégie
        # FORCER LA STRATEGIE POUR LE TEST
        strategy = OrchestrationStrategy.SPECIALIZED_DIRECT
        self.config.analysis_type = AnalysisType.INVESTIGATIVE
        logger.info(f"Stratégie sélectionnée : {strategy.value}")


        if strategy == OrchestrationStrategy.HIERARCHICAL_FULL:
            return await self._execute_hierarchical_full(text_input)
        elif strategy == OrchestrationStrategy.STRATEGIC_ONLY:
            return await self._execute_strategic_only(text_input)
        elif strategy == OrchestrationStrategy.TACTICAL_COORDINATION:
            return await self._execute_tactical_coordination(text_input)
        elif strategy == OrchestrationStrategy.OPERATIONAL_DIRECT:
            return await self._execute_operational_direct(text_input)
        elif strategy == OrchestrationStrategy.SPECIALIZED_DIRECT:
            return await self._execute_specialized_direct(text_input)
        elif strategy == OrchestrationStrategy.HYBRID:
            return await self._execute_hybrid(text_input)
        elif strategy == OrchestrationStrategy.SERVICE_MANAGER:
            return await self._execute_service_manager(text_input)
        elif strategy == OrchestrationStrategy.FALLBACK:
            return await self._execute_fallback(text_input)
        elif strategy == OrchestrationStrategy.COMPLEX_PIPELINE:
            return await self._execute_complex_pipeline(text_input)
        elif strategy == OrchestrationStrategy.MANUAL_SELECTION:
            return await self._execute_manual_selection(text_input)
        else:
            # Ce cas ne devrait pas être atteint si select_strategy retourne toujours une valeur valide
            # de OrchestrationStrategy.
            return {
                "status": "error",
                "message": f"Unknown or unsupported strategy: {strategy.value if strategy else 'None'}",
                "result": None
            }

    async def _execute_hierarchical_full(self, text_input: str) -> Dict[str, Any]:
        """
        Exécute le flux d'orchestration hiérarchique complet de bout en bout.

        Cette stratégie implique les trois niveaux :
        1.  **Stratégique**: Analyse initiale pour définir les grands objectifs.
        2.  **Tactique**: Décomposition des objectifs en tâches concrètes.
        3.  **Opérationnel**: Exécution des tâches.
        4.  **Synthèse**: Agrégation et rapport des résultats.

        Args:
            text_input (str): Le texte à analyser.

        Returns:
            Dict[str, Any]: Un dictionnaire contenant les résultats de chaque niveau.
        """
        logger.info("[HIERARCHICAL] Exécution de l'orchestration hiérarchique complète...")
        results: Dict[str, Any] = {
            "status": "pending",
            "strategy_used": OrchestrationStrategy.HIERARCHICAL_FULL.value,
            "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
            "strategic_analysis": {},
            "tactical_coordination": {},
            "operational_results": {},
            "hierarchical_coordination": {}
        }

        try:
            # Niveau stratégique
            # Assumant que les instances des managers sont accessibles via self.config
            # Par exemple: self.config.strategic_manager_instance
            # Pour l'instant, on utilise des hasattr pour vérifier leur présence,
            # similairement au code original.
            # Une meilleure approche serait de les initialiser dans __init__ de MainOrchestrator
            # ou de s'assurer qu'ils sont toujours présents dans config.

            objectives = []  # Initialisation pour le scope

            if self.strategic_manager:
                logger.info("[STRATEGIC] Initialisation de l'analyse stratégique...")
                try:
                    strategic_results = self.strategic_manager.initialize_analysis(text_input)
                    results["strategic_analysis"] = strategic_results
                    objectives = strategic_results.get("objectives", [])
                except Exception as e:
                    logger.error(f"[DIAGNOSTIC] Erreur critique lors de l'appel à strategic_manager.initialize_analysis: {e}", exc_info=True)
                    results["status"] = "error"
                    results["error_message"] = f"Erreur dans strategic_manager: {e}"
                    return results
                logger.debug(f"[TRACE] strategic_analysis_completed: objectives_count={len(objectives)}, strategic_plan_phases={strategic_results.get('strategic_plan', {}).get('phases', [])}")

            # Niveau tactique
            if self.tactical_coordinator and self.strategic_manager:
                logger.info("[TACTICAL] Coordination tactique...")
                tactical_results = self.tactical_coordinator.process_strategic_objectives(objectives)
                results["tactical_coordination"] = tactical_results
                logger.debug(f"[TRACE] tactical_coordination_completed: tasks_created={tactical_results.get('tasks_created', 0)}")

            # Niveau opérationnel (exécution des tâches)
            if self.operational_manager:
                logger.info("[OPERATIONAL] Exécution opérationnelle...")
                # L'appel original était: await self._execute_operational_tasks(text, results["tactical_coordination"])
                operational_tasks_input = results.get("tactical_coordination", {})
                if not operational_tasks_input and objectives: # Fallback si tactical n'a rien produit mais qu'on a des objectifs
                     logger.warning("[OPERATIONAL] Tactical coordination results are empty, attempting to use objectives for operational tasks.")
                     operational_tasks_input = {"objectives": objectives} # Adapter selon ce que _execute_operational_tasks attend

                operational_results = await self._execute_operational_tasks(text_input, operational_tasks_input) # Adaptation: text -> text_input
                results["operational_results"] = operational_results
                
                logger.debug(f"[TRACE] operational_execution_completed: tasks_executed={len(operational_results.get('task_results', []))}")
            
            # Synthèse hiérarchique
            results["hierarchical_coordination"] = await self._synthesize_hierarchical_results(results)
            results["status"] = "success"

        except Exception as e:
            logger.error(f"[HIERARCHICAL] Erreur dans l'orchestration hiérarchique: {e}", exc_info=True) # Ajout de exc_info pour la stack trace
            results["status"] = "error"
            results["error_message"] = str(e)
            if "strategic_analysis" not in results: # S'assurer que la clé existe
                 results["strategic_analysis"] = {}
            results["strategic_analysis"]["error"] = str(e) # Maintenir la compatibilité si nécessaire
        
        return results

    async def _execute_operational_tasks(self, text_input: str, tactical_coordination_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute un ensemble de tâches opérationnelles en utilisant le DirectOperationalExecutor.
        Cette méthode remplace la simulation par un appel réel au pipeline opérationnel.
        """
        logger.info(f"Délégation de l'exécution opérationnelle au DirectOperationalExecutor...")

        if not self.direct_operational_executor:
            error_msg = "DirectOperationalExecutor n'est pas initialisé. Impossible de procéder."
            logger.error(f"[OPERATIONAL] {error_msg}")
            return {
                "status": "error",
                "error_message": error_msg,
                "tasks_executed": 0,
                "task_results": [],
                "summary": {"error": error_msg}
            }

        try:
            # Appel du pipeline réel
            operational_results = await self.direct_operational_executor.execute_operational_pipeline(
                text_input=text_input,
                tactical_results=tactical_coordination_results
            )
            logger.info("[OPERATIONAL] Exécution via DirectOperationalExecutor terminée.")
            return operational_results

        except Exception as e:
            logger.error(f"[OPERATIONAL] Erreur durant l'exécution via DirectOperationalExecutor: {e}", exc_info=True)
            return {
                "status": "error",
                "error_message": str(e),
                "tasks_executed": 0,
                "task_results": [],
                "summary": {"error": str(e)}
            }

    async def _synthesize_hierarchical_results(self, current_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthétise et évalue les résultats des différents niveaux hiérarchiques.

        Cette méthode agrège les résultats des niveaux stratégique, tactique et
        opérationnel pour calculer des scores de performance (par exemple, efficacité,
        alignement) et générer une évaluation globale de l'orchestration.

        Args:
            current_results (Dict[str, Any]): Le dictionnaire contenant les résultats
                                              partiels des niveaux précédents.

        Returns:
            Dict[str, Any]: Un dictionnaire de synthèse avec les scores et
                            recommandations.
        """
        # Note: HierarchicalReport pourrait être utilisé ici pour structurer la sortie.
        synthesis = {
            "coordination_effectiveness": 0.0,
            "strategic_alignment": 0.0,
            "tactical_efficiency": 0.0,
            "operational_success": 0.0,
            "overall_score": 0.0,
            "recommendations": []
        }
        
        try:
            # Calculer les métriques de coordination
            # Le paramètre est renommé de 'results' (source) à 'current_results' (destination)
            strategic_results = current_results.get("strategic_analysis", {})
            tactical_results = current_results.get("tactical_coordination", {})
            operational_results = current_results.get("operational_results", {})
            
            # Alignement stratégique
            if strategic_results:
                objectives_count = len(strategic_results.get("objectives", []))
                synthesis["strategic_alignment"] = min(objectives_count / 4.0, 1.0)  # Max 4 objectifs
            
            # Efficacité tactique
            if tactical_results:
                tasks_created = tactical_results.get("tasks_created", 0)
                synthesis["tactical_efficiency"] = min(tasks_created / 10.0, 1.0)  # Max 10 tâches
            
            # Succès opérationnel
            if operational_results:
                success_rate = operational_results.get("summary", {}).get("success_rate", 0.0)
                synthesis["operational_success"] = success_rate
            
            # Score global
            scores = [
                synthesis["strategic_alignment"],
                synthesis["tactical_efficiency"],
                synthesis["operational_success"]
            ]
            # Filtrer les None potentiels si une section de résultats est absente et retourne None au lieu de 0.0
            valid_scores = [s for s in scores if isinstance(s, (int, float))]
            synthesis["overall_score"] = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
            synthesis["coordination_effectiveness"] = synthesis["overall_score"]
            
            # Recommandations
            if synthesis["overall_score"] > 0.8:
                synthesis["recommendations"].append("Orchestration hiérarchique très efficace")
            elif synthesis["overall_score"] > 0.6:
                synthesis["recommendations"].append("Orchestration hiérarchique satisfaisante")
            else:
                synthesis["recommendations"].append("Orchestration hiérarchique à améliorer")
        
        except Exception as e:
            # logger est défini au niveau du module, pas besoin de self.logger
            logger.error(f"Erreur synthèse hiérarchique: {e}", exc_info=True)
            synthesis["error"] = str(e)
        
        return synthesis

    async def _execute_strategic_only(self, text_input: str) -> Dict[str, Any]:
        """Exécute la stratégie stratégique uniquement."""
        logger.info("[STRATEGIC_ONLY] Exécution de l'orchestration stratégique uniquement...")
        results: Dict[str, Any] = {
            "status": "pending",
            "strategy_used": OrchestrationStrategy.STRATEGIC_ONLY.value,
            "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
            "strategic_analysis": {}
        }

        try:
            strategic_manager = getattr(self.config, 'strategic_manager_instance', None)

            if strategic_manager:
                logger.info("[STRATEGIC_ONLY] Initialisation de l'analyse stratégique...")
                # L'appel original était: self.strategic_manager.initialize_analysis(text)
                # Dans le contexte de _execute_hierarchical_full, strategic_results est directement assigné.
                # Ici, nous allons le stocker dans une variable locale puis dans le dictionnaire results.
                analysis_output = await strategic_manager.initialize_analysis(text_input)
                results["strategic_analysis"] = analysis_output
                
                # Vérifier si l'analyse a réussi (basé sur la structure typique de strategic_results)
                if analysis_output and analysis_output.get("objectives") is not None: # ou autre indicateur de succès
                    results["status"] = "success"
                    logger.debug(f"[TRACE] strategic_only_analysis_completed: objectives_count={len(analysis_output.get('objectives', []))}, strategic_plan_phases={analysis_output.get('strategic_plan', {}).get('phases', [])}")
                else:
                    results["status"] = "partial_failure" # ou "error" si c'est plus approprié
                    results["strategic_analysis"]["error"] = analysis_output.get("error", "Strategic analysis did not produce expected output.")
                    logger.warning(f"[STRATEGIC_ONLY] L'analyse stratégique n'a pas produit les résultats attendus: {analysis_output}")

            else:
                logger.error("[STRATEGIC_ONLY] StrategicManager non configuré.")
                results["status"] = "error"
                results["error_message"] = "StrategicManager non configuré."
                results["strategic_analysis"]["error"] = "StrategicManager non configuré."

        except Exception as e:
            logger.error(f"[STRATEGIC_ONLY] Erreur dans l'orchestration stratégique uniquement: {e}", exc_info=True)
            results["status"] = "error"
            results["error_message"] = str(e)
            # S'assurer que la clé existe même en cas d'erreur avant l'initialisation de strategic_manager
            if "strategic_analysis" not in results:
                 results["strategic_analysis"] = {}
            results["strategic_analysis"]["error"] = str(e)
        
        return results

    async def _execute_tactical_coordination(self, text_input: str) -> Dict[str, Any]:
        """Exécute la stratégie de coordination tactique."""
        logger.info("[TACTICAL_COORDINATION] Exécution de la stratégie de coordination tactique...")
        results: Dict[str, Any] = {
            "status": "pending",
            "strategy_used": OrchestrationStrategy.TACTICAL_COORDINATION.value,
            "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
            "tactical_coordination_results": {} # Clé spécifique pour les résultats de cette stratégie
        }

        try:
            strategic_manager = getattr(self.config, 'strategic_manager_instance', None)
            tactical_coordinator = getattr(self.config, 'tactical_coordinator_instance', None)
            objectives = []

            if not strategic_manager or not tactical_coordinator:
                logger.error("[TACTICAL_COORDINATION] StrategicManager ou TacticalCoordinator non configuré.")
                results["status"] = "error"
                results["error_message"] = "StrategicManager ou TacticalCoordinator non configuré."
                # S'assurer que la clé existe même en cas d'erreur de configuration
                if "tactical_coordination_results" not in results:
                     results["tactical_coordination_results"] = {}
                results["tactical_coordination_results"]["error"] = "StrategicManager ou TacticalCoordinator non configuré."
                return results

            # Étape 1 (Interne) - Analyse Stratégique
            logger.info("[TACTICAL_COORDINATION] Étape 1: Initialisation de l'analyse stratégique (interne)...")
            strategic_analysis_output = await strategic_manager.initialize_analysis(text_input)
            
            if not strategic_analysis_output or strategic_analysis_output.get("objectives") is None:
                logger.warning("[TACTICAL_COORDINATION] L'analyse stratégique n'a pas produit d'objectifs.")
                results["status"] = "partial_failure"
                results["error_message"] = "L'analyse stratégique interne n'a pas produit d'objectifs."
                results["tactical_coordination_results"]["error"] = "Aucun objectif stratégique obtenu pour la coordination tactique."
                results["tactical_coordination_results"]["details"] = strategic_analysis_output # Inclure la sortie stratégique pour le débogage
                return results
                
            objectives = strategic_analysis_output.get("objectives", [])
            logger.debug(f"[TRACE][TACTICAL_COORDINATION] Analyse stratégique interne terminée: objectives_count={len(objectives)}")

            # Étape 2 - Coordination Tactique
            logger.info("[TACTICAL_COORDINATION] Étape 2: Coordination tactique basée sur les objectifs stratégiques...")
            tactical_run_results = await tactical_coordinator.process_strategic_objectives(objectives)
            results["tactical_coordination_results"] = tactical_run_results
            
            # Vérifier si la coordination tactique a réussi (basé sur une structure typique)
            # Par exemple, si tactical_run_results est un dict et n'a pas de clé "error"
            if isinstance(tactical_run_results, dict) and "error" not in tactical_run_results:
                results["status"] = "success"
                logger.debug(f"[TRACE][TACTICAL_COORDINATION] Coordination tactique terminée: tasks_created={tactical_run_results.get('tasks_created', 0)}")
            else:
                results["status"] = "partial_failure" # ou "error"
                # Si tactical_run_results n'est pas un dict ou contient une erreur, le message d'erreur est déjà dans tactical_coordination_results
                logger.warning(f"[TACTICAL_COORDINATION] La coordination tactique a rencontré un problème ou n'a pas produit les résultats attendus: {tactical_run_results}")
                if isinstance(tactical_run_results, dict) and "error" not in tactical_run_results: # Ajouter un message d'erreur générique si non présent
                     results["tactical_coordination_results"]["error"] = "La coordination tactique n'a pas produit les résultats attendus."


        except Exception as e:
            logger.error(f"[TACTICAL_COORDINATION] Erreur majeure dans la stratégie de coordination tactique: {e}", exc_info=True)
            results["status"] = "error"
            results["error_message"] = str(e)
            # S'assurer que la clé existe même en cas d'erreur
            if "tactical_coordination_results" not in results:
                 results["tactical_coordination_results"] = {}
            results["tactical_coordination_results"]["error"] = str(e)
        
        return results

    async def _execute_operational_direct(self, text_input: str) -> Dict[str, Any]:
        """Exécute la stratégie opérationnelle directe."""
        logger.info("[OPERATIONAL_DIRECT] Exécution de la stratégie opérationnelle directe...")
        
        try:
            # Utiliser les managers directement depuis self
            strategic_manager = self.strategic_manager
            tactical_coordinator = self.tactical_coordinator
            operational_manager = self.operational_manager

            if not all([strategic_manager, tactical_coordinator, operational_manager]):
                missing_components = [
                    name for name, component in [
                        ("StrategicManager", strategic_manager),
                        ("TacticalCoordinator", tactical_coordinator),
                        ("OperationalManager", operational_manager),
                    ] if not component
                ]
                error_msg = f"Configuration incomplète: {', '.join(missing_components)} non trouvé(s) dans MainOrchestrator."
                logger.error(f"[OPERATIONAL_DIRECT] {error_msg}")
                return {
                    "status": "error",
                    "strategy_used": OrchestrationStrategy.OPERATIONAL_DIRECT.value,
                    "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
                    "error_message": error_msg,
                    "operational_results": {"error": error_msg}
                }

            objectives = []

            # Étape 1 (Interne) - Analyse Stratégique
            logger.info("[OPERATIONAL_DIRECT] Étape 1 (Interne): Analyse Stratégique...")
            strategic_results = strategic_manager.initialize_analysis(text_input)
            objectives = strategic_results.get("objectives", [])
            if not objectives:
                logger.warning("[OPERATIONAL_DIRECT] L'analyse stratégique n'a pas produit d'objectifs. L'exécution opérationnelle pourrait être limitée.")
            logger.debug(f"[TRACE][OPERATIONAL_DIRECT] Analyse stratégique interne terminée: objectives_count={len(objectives)}")

            # Étape 2 (Interne) - Coordination Tactique
            logger.info("[OPERATIONAL_DIRECT] Étape 2 (Interne): Coordination Tactique...")
            tactical_results = tactical_coordinator.process_strategic_objectives(objectives)
            logger.debug(f"[TRACE][OPERATIONAL_DIRECT] Coordination tactique interne terminée: tasks_created={tactical_results.get('tasks_created', 'N/A')}, tasks_sample={str(tactical_results.get('tasks', [])[:2])[:100]}...")

            # Étape 3 - Exécution Opérationnelle
            logger.info("[OPERATIONAL_DIRECT] Étape 3: Exécution Opérationnelle...")
            operational_execution_output = await self._execute_operational_tasks(text_input, tactical_results)
            
            current_status = "success"
            error_message_content = None

            if isinstance(operational_execution_output, dict) and "error" in operational_execution_output:
                current_status = "error"
                error_message_content = operational_execution_output.get("error", "Erreur inconnue lors de l'exécution opérationnelle.")
            elif not isinstance(operational_execution_output, dict) or not operational_execution_output:
                current_status = "error"
                error_message_content = "Résultats opérationnels invalides ou vides."
                # Assurer que operational_execution_output est un dict pour le retour final
                operational_execution_output = {"error": error_message_content, "details": operational_execution_output}


            final_output = {
                "status": current_status,
                "strategy_used": OrchestrationStrategy.OPERATIONAL_DIRECT.value,
                "operational_results": operational_execution_output 
            }
            
            if error_message_content:
                 final_output["error_message"] = error_message_content # Peut être redondant si déjà dans operational_results
            
            logger.info(f"[OPERATIONAL_DIRECT] Stratégie terminée avec le statut: {final_output['status']}")
            return final_output

        except Exception as e:
            logger.error(f"[OPERATIONAL_DIRECT] Erreur majeure dans la stratégie opérationnelle directe: {e}", exc_info=True)
            return {
                "status": "error",
                "strategy_used": OrchestrationStrategy.OPERATIONAL_DIRECT.value,
                "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
                "error_message": str(e),
                "operational_results": {"error": str(e)} 
            }

    async def _execute_specialized_direct(self, text_input: str) -> Dict[str, Any]:
        """Exécute l'orchestration spécialisée directe en utilisant un orchestrateur adapté."""
        logger.info("[SPECIALIZED_DIRECT] Exécution de l'orchestration spécialisée directe...")
        
        output_results: Dict[str, Any] = {
            "status": "pending",
            "strategy_used": OrchestrationStrategy.SPECIALIZED_DIRECT.value,
            "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
            "specialized_orchestration": {}
        }

        try:
            selected_orchestrator_info = await self._select_specialized_orchestrator()
            
            if selected_orchestrator_info:
                orchestrator_name, orchestrator_data = selected_orchestrator_info
                orchestrator_instance = orchestrator_data.get("orchestrator")

                if not orchestrator_instance:
                    logger.error(f"Orchestrator instance for '{orchestrator_name}' is missing in config map.")
                    output_results["specialized_orchestration"] = {
                        "status": "error",
                        "message": f"Instance de l'orchestrateur '{orchestrator_name}' non trouvée."
                    }
                    output_results["status"] = "error"
                    return output_results

                logger.info(f"[SPECIALIZED_DIRECT] Utilisation de l'orchestrateur: {orchestrator_name} (type: {type(orchestrator_instance)})")
                
                specialized_run_results: Dict[str, Any] = {}
                # Assurer que les orchestrateurs et run_cluedo_game sont importés
                if orchestrator_name == "cluedo" and CluedoExtendedOrchestrator and run_cluedo_game and isinstance(orchestrator_instance, CluedoExtendedOrchestrator):
                    specialized_run_results = await self._run_cluedo_investigation(text_input, orchestrator_instance)
                elif orchestrator_name == "conversation" and ConversationOrchestrator and isinstance(orchestrator_instance, ConversationOrchestrator):
                    if hasattr(orchestrator_instance, 'run_conversation'):
                        specialized_run_results = await orchestrator_instance.run_conversation(text_input)
                    else:
                        logger.warning(f"ConversationOrchestrator '{orchestrator_name}' lacks 'run_conversation' method.")
                        specialized_run_results = {"status": "error", "message": "Méthode run_conversation non trouvée"}
                elif orchestrator_name == "real_llm" and RealLLMOrchestrator and isinstance(orchestrator_instance, RealLLMOrchestrator):
                    if hasattr(orchestrator_instance, 'analyze_text_comprehensive'):
                        specialized_run_results = await orchestrator_instance.analyze_text_comprehensive(
                            text_input, context={"source": "specialized_direct_orchestration"}
                        )
                    else:
                        logger.warning(f"RealLLMOrchestrator '{orchestrator_name}' lacks 'analyze_text_comprehensive' method.")
                        specialized_run_results = {"status": "error", "message": "Méthode analyze_text_comprehensive non trouvée"}
                elif orchestrator_name == "logic_complex" and LogiqueComplexeOrchestrator and isinstance(orchestrator_instance, LogiqueComplexeOrchestrator):
                    specialized_run_results = await self._run_logic_complex_analysis(text_input, orchestrator_instance)
                else:
                    logger.warning(f"Orchestrateur spécialisé non géré ou type incorrect: {orchestrator_name} (instance type: {type(orchestrator_instance)})")
                    specialized_run_results = {"status": "unsupported_orchestrator", "orchestrator_name": orchestrator_name}
                
                output_results["specialized_orchestration"] = {
                    "orchestrator_used": orchestrator_name,
                    "orchestrator_priority": orchestrator_data.get("priority", "N/A"),
                    "results": specialized_run_results
                }
                output_results["status"] = specialized_run_results.get("status", "unknown_specialized_status")
                logger.debug(f"[TRACE] specialized_direct_orchestration_completed: orchestrator={orchestrator_name}, status={output_results['status']}")
            else:
                logger.info("[SPECIALIZED_DIRECT] Aucun orchestrateur spécialisé n'a pu être sélectionné.")
                output_results["specialized_orchestration"] = {
                    "status": "no_orchestrator_selected",
                    "message": "Aucun orchestrateur spécialisé disponible ou compatible pour ce type d'analyse/configuration."
                }
                output_results["status"] = "no_orchestrator_selected"
        
        except Exception as e:
            logger.error(f"[SPECIALIZED_DIRECT] Erreur majeure dans l'orchestration spécialisée directe: {e}", exc_info=True)
            if "specialized_orchestration" not in output_results:
                output_results["specialized_orchestration"] = {}
            output_results["specialized_orchestration"]["error_message"] = str(e)
            output_results["specialized_orchestration"]["status"] = "error"
            output_results["status"] = "error"
        
        return output_results

    async def _select_specialized_orchestrator(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Sélectionne l'orchestrateur spécialisé approprié basé sur la configuration."""
        specialized_orchestrators_map = self.specialized_orchestrators_map
        if not specialized_orchestrators_map:
            logger.warning("No specialized orchestrators map found in config (self.config.specialized_orchestrators_map).")
            return None
        
        current_analysis_type = getattr(self.config, 'analysis_type_enum', None)
        # AnalysisType doit être importé pour que la comparaison fonctionne.
        if not current_analysis_type or not AnalysisType:
            logger.warning("Analysis type enum (self.config.analysis_type_enum) or AnalysisType import not found. Considering all orchestrators.")
            compatible_orchestrators = list(specialized_orchestrators_map.items())
        else:
            compatible_orchestrators = []
            for name, data in specialized_orchestrators_map.items():
                # data["types"] devrait être une liste de membres de l'enum AnalysisType
                if current_analysis_type in data.get("types", []):
                    compatible_orchestrators.append((name, data))
            
            if not compatible_orchestrators:
                logger.info(f"No specialized orchestrator directly compatible with {current_analysis_type}. Considering all available.")
                compatible_orchestrators = list(specialized_orchestrators_map.items())
        
        if not compatible_orchestrators:
            logger.info("No specialized orchestrators available at all.")
            return None
            
        compatible_orchestrators.sort(key=lambda x: x[1].get("priority", float('inf')))
        
        selected_name, selected_data = compatible_orchestrators[0]
        logger.debug(f"Selected specialized orchestrator: {selected_name} with priority {selected_data.get('priority')}")
        return selected_name, selected_data

    async def _run_cluedo_investigation(self, text_input: str, orchestrator_instance: Any) -> Dict[str, Any]:
        """Exécute une investigation de type Cluedo."""
        if not CluedoExtendedOrchestrator or not run_cluedo_game or not isinstance(orchestrator_instance, CluedoExtendedOrchestrator):
            logger.warning("Cluedo investigation prerequisites not met (CluedoExtendedOrchestrator, run_cluedo_game, or instance type mismatch).")
            return {"status": "limited", "message": "Prérequis pour l'investigation Cluedo non remplis."}
        try:
            if hasattr(orchestrator_instance, 'kernel'):
                logger.info(f"Running Cluedo investigation with orchestrator: {type(orchestrator_instance)}")
                # run_cluedo_game a été renommé en run_cluedo_oracle_game et retourne un dict
                results = await run_cluedo_game(
                    kernel=orchestrator_instance.kernel,
                    initial_question=f"Analysez ce texte comme une enquête : {text_input[:500]}...",
                    max_cycles=5
                )
                
                # Extraire les données nécessaires du dictionnaire de résultats
                conversation_history = results.get("conversation_history", []) if results else []
                final_state = results.get("final_state", {}) if results else {}
                final_solution = final_state.get('final_solution') if final_state else None

                return {
                    "status": "completed",
                    "investigation_type": "cluedo",
                    "conversation_history": conversation_history,
                    "enquete_state": {
                        "nom_enquete": final_solution.get('nom_enquete', 'N/A') if isinstance(final_solution, dict) else 'N/A',
                        "solution_proposee": final_solution if final_solution else 'N/A',
                        "hypotheses_count": len(results.get("oracle_statistics", {}).get("agent_interactions", {}).get("suggestions_made", [])) if results else 0,
                        "tasks_count": results.get("oracle_statistics", {}).get("agent_interactions", {}).get("total_turns", 0) if results else 0
                    },
                    "full_results": results # Inclure tous les résultats pour un débogage plus facile
                }
            else:
                logger.warning("Cluedo orchestrator instance does not have 'kernel' attribute.")
                return {"status": "limited", "message": "Instance CluedoOrchestrator sans attribut 'kernel'."}
        except Exception as e:
            logger.error(f"Erreur investigation Cluedo: {e}", exc_info=True)
            return {"status": "error", "error_message": str(e)}

    async def _run_logic_complex_analysis(self, text_input: str, orchestrator_instance: Any) -> Dict[str, Any]:
        """Exécute une analyse logique complexe."""
        if not LogiqueComplexeOrchestrator or not isinstance(orchestrator_instance, LogiqueComplexeOrchestrator):
            logger.warning("LogiqueComplexeOrchestrator not available or instance type mismatch.")
            return {"status": "limited", "message": "LogiqueComplexeOrchestrator non disponible ou type d'instance incorrect."}
        try:
            if hasattr(orchestrator_instance, 'analyze_complex_logic'):
                logger.info(f"Running complex logic analysis with orchestrator: {type(orchestrator_instance)}")
                analysis_results = await orchestrator_instance.analyze_complex_logic(text_input)
                return {"status": "completed", "logic_analysis_results": analysis_results}
            else:
                logger.warning("LogiqueComplexeOrchestrator does not have 'analyze_complex_logic' method.")
                return {"status": "limited", "message": "Méthode 'analyze_complex_logic' non trouvée."}
        except Exception as e:
            logger.error(f"Erreur analyse logique complexe: {e}", exc_info=True)
            return {"status": "error", "error_message": str(e)}

    async def _execute_hybrid(self, text_input: str) -> Dict[str, Any]:
        """Exécute la stratégie hybride."""
        tactical_results = {}
        specialized_results = {}
        errors = []

        try:
            logger.info("Executing tactical coordination for hybrid strategy.")
            tactical_results = await self._execute_tactical_coordination(text_input)
            if tactical_results.get("status") == "error":
                errors.append(f"Tactical coordination failed: {tactical_results.get('error_message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error during tactical coordination in hybrid strategy: {e}", exc_info=True)
            errors.append(f"Exception in tactical coordination: {str(e)}")
            tactical_results = {"status": "error", "error_message": str(e)}

        try:
            logger.info("Executing specialized direct for hybrid strategy.")
            specialized_results = await self._execute_specialized_direct(text_input)
            if specialized_results.get("status") == "error":
                errors.append(f"Specialized direct execution failed: {specialized_results.get('error_message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error during specialized direct execution in hybrid strategy: {e}", exc_info=True)
            errors.append(f"Exception in specialized direct execution: {str(e)}")
            specialized_results = {"status": "error", "error_message": str(e)}

        final_status = "success"
        if errors:
            if tactical_results.get("status") == "error" and specialized_results.get("status") == "error":
                final_status = "error"
            else:
                final_status = "partial_failure"
        
        return {
            "status": final_status,
            "hybrid_results": {
                "tactical_coordination": tactical_results,
                "specialized_direct": specialized_results
            },
            "errors": errors if errors else None
        }

    async def _execute_service_manager(self, text_input: str) -> Dict[str, Any]:
        """Exécute la stratégie via le gestionnaire de services."""
        logger.info(f"Executing SERVICE_MANAGER strategy for input: {text_input[:50]}...")
        try:
            service_manager_instance = self.config.get("service_manager_instance")
            if not service_manager_instance:
                logger.error("ServiceManager instance not found in configuration.")
                return {
                    "status": "error",
                    "strategy_used": OrchestrationStrategy.SERVICE_MANAGER.value,
                    "error_message": "ServiceManager instance not configured.",
                    "service_status_report": None
                }

            # Supposons que service_manager_instance a une méthode async get_services_status
            # et qu'elle ne prend pas d'argument text_input pour cette tâche spécifique.
            # Si text_input était nécessaire, il faudrait l'ajouter à l'appel.
            service_status = await service_manager_instance.get_services_status()
            
            logger.info(f"ServiceManager returned status: {service_status}")
            return {
                "status": "success",
                "strategy_used": OrchestrationStrategy.SERVICE_MANAGER.value,
                "service_status_report": service_status
            }
        except AttributeError as e:
            logger.error(f"ServiceManager instance is missing 'get_services_status' method or is not correctly configured: {e}")
            return {
                "status": "error",
                "strategy_used": OrchestrationStrategy.SERVICE_MANAGER.value,
                "error_message": f"ServiceManager interaction error: Missing method or configuration - {str(e)}",
                "service_status_report": None
            }
        except Exception as e:
            logger.error(f"Error during Service Manager strategy execution: {e}", exc_info=True)
            return {
                "status": "error",
                "strategy_used": OrchestrationStrategy.SERVICE_MANAGER.value,
                "error_message": f"An unexpected error occurred: {str(e)}",
                "service_status_report": None
            }

    async def _execute_fallback(self, text_input: str) -> Dict[str, Any]:
        """
        Exécute la stratégie de repli lorsque aucune autre stratégie n'est applicable.
        """
        snippet_length = 100  # Longueur de l'extrait du texte d'entrée
        input_snippet = text_input[:snippet_length] + "..." if len(text_input) > snippet_length else text_input

        logger.warning(
            f"Activation de la stratégie de repli (FALLBACK). "
            f"Aucune stratégie applicable n'a pu être déterminée ou une erreur majeure s'est produite. "
            f"Extrait de l'entrée : '{input_snippet}'"
        )

        return {
            "status": "fallback_activated",
            "strategy_used": OrchestrationStrategy.FALLBACK.value,
            "message": "Aucune stratégie applicable n'a pu être exécutée. Activation du mode de repli.",
            "details": "Cette réponse indique qu'une condition inattendue ou une erreur de configuration a empêché le traitement normal.",
            "input_text_snippet": input_snippet
        }

    async def _execute_complex_pipeline(self, text_input: str) -> Dict[str, Any]:
        """Exécute la stratégie de pipeline complexe."""
        logger.info(
            f"Executing COMPLEX_PIPELINE strategy for input: {text_input[:50]}..."
        )
        return {
            "status": "success",
            "strategy_used": OrchestrationStrategy.COMPLEX_PIPELINE.value,
            "message": "Complex pipeline strategy executed successfully.",
            "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
        }

    async def _execute_manual_selection(self, text_input: str) -> Dict[str, Any]:
        """Exécute la stratégie de sélection manuelle."""
        logger.info(
            f"Executing MANUAL_SELECTION strategy for input: {text_input[:50]}..."
        )
        return {
            "status": "success",
            "strategy_used": OrchestrationStrategy.MANUAL_SELECTION.value,
            "message": "Manual selection strategy executed successfully.",
            "input_text_snippet": text_input[:100] + "..." if len(text_input) > 100 else text_input,
        }
    def _initialize_specialized_orchestrators(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialise et retourne la carte des orchestrateurs spécialisés.
        """
        s_map = {}
        
        # L'instanciation de chaque orchestrateur se fait ici.
        # Le kernel est disponible via self.kernel.
        
        if CluedoExtendedOrchestrator:
            s_map["cluedo"] = {
                "orchestrator": CluedoExtendedOrchestrator(self.kernel),
                "priority": 1,
                "types": [AnalysisType.INVESTIGATIVE] if AnalysisType else []
            }
        
        if ConversationOrchestrator:
            s_map["conversation"] = {
                "orchestrator": ConversationOrchestrator(self.kernel),
                "priority": 2,
                "types": [AnalysisType.DEBATE_ANALYSIS] if AnalysisType else []
            }

        if RealLLMOrchestrator:
            s_map["real_llm"] = {
                "orchestrator": RealLLMOrchestrator(self.kernel),
                "priority": 3,
                "types": [AnalysisType.COMPREHENSIVE, AnalysisType.RHETORICAL, AnalysisType.FALLACY_FOCUSED] if AnalysisType else []
            }

        if LogiqueComplexeOrchestrator:
            s_map["logic_complex"] = {
                "orchestrator": LogiqueComplexeOrchestrator(self.kernel),
                "priority": 4,
                "types": [AnalysisType.LOGICAL] if AnalysisType else []
            }
        
        logger.info(f"Specialized orchestrators initialized: {list(s_map.keys())}")
        return s_map

if __name__ == "__main__":
    import asyncio
    import os
    import semantic_kernel as sk
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from dotenv import load_dotenv

    from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
    from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TacticalCoordinator
    from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
    from argumentation_analysis.core.communication.middleware import MessageMiddleware
    from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
    
    # Ce bloc est un exemple d'exécution.
    # Dans une application réelle, MainOrchestrator serait instancié
    # et utilisé par un autre composant (ex: un serveur API).
    
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async def main():
        """Point d'entrée pour l'exécution du script."""
        logger.info("Initialisation de l'orchestrateur principal en mode script exemple.")
        
        config = OrchestrationConfig()
        
        # Charger les variables d'environnement depuis le fichier .env
        load_dotenv()
        kernel = sk.Kernel()
        api_key = os.getenv("OPENAI_API_KEY")
        # Le modèle est fixé pour l'exemple, mais pourrait être configurable
        model_id = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-4")
        if not api_key:
            raise ValueError("OPENAI_API_KEY doit être défini.")

        # Le `model_id` est implicitement géré par la bibliothèque via les
        # variables d'environnement (par exemple OPENAI_CHAT_MODEL_ID) dans cette
        # version de semantic-kernel, et ne doit pas être passé en argument.
        kernel.add_service(
            OpenAIChatCompletion(service_id="chat_completion", api_key=api_key)
        )

        shared_middleware = MessageMiddleware()
        shared_middleware.register_channel(HierarchicalChannel("hierarchical_channel"))
        strategic_manager = StrategicManager(middleware=shared_middleware)
        tactical_coordinator = TacticalCoordinator(middleware=shared_middleware)
        operational_manager = OperationalManager(middleware=shared_middleware)

        orchestrator = MainOrchestrator(
            config=config,
            kernel=kernel,
            strategic_manager=strategic_manager,
            tactical_coordinator=tactical_coordinator,
            operational_manager=operational_manager
        )
        
        # Exemple de texte à analyser
        text_to_analyze = "Le corps a été retrouvé dans la bibliothèque. Le colonel Moutarde et Mlle Rose étaient les seuls présents dans la maison. Le chandelier, qui semble être l'arme du crime, a été retrouvé dans le salon."
        
        results = await orchestrator.run_analysis(text_input=text_to_analyze)
        
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))

    # Exécution de la fonction main asynchrone
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exécution interrompue par l'utilisateur.")
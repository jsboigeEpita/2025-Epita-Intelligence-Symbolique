# core/state_manager_plugin.py
import json
from typing import Dict, List, Any, Optional
import logging
from semantic_kernel.functions import kernel_function

# Importer la classe d'état depuis le même répertoire
from .shared_state import RhetoricalAnalysisState

# Logger spécifique pour le StateManager
sm_logger = logging.getLogger("Orchestration.StateManager")
if not sm_logger.handlers and not sm_logger.propagate:
     handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); sm_logger.addHandler(handler); sm_logger.setLevel(logging.INFO)


class StateManagerPlugin:
    """Plugin Semantic Kernel pour lire et modifier l'état d'analyse partagé."""
    _state: 'RhetoricalAnalysisState' # Référence à l'instance d'état unique
    _logger: logging.Logger

    def __init__(self, state: 'RhetoricalAnalysisState'):
        """Initialise le plugin avec une instance d'état."""
        self._state = state
        self._logger = sm_logger
        self._logger.info(f"StateManagerPlugin initialisé avec l'instance RhetoricalAnalysisState (id: {id(self._state)}).")

    # ... (Le code complet de la classe StateManagerPlugin avec ses @kernel_function va ici) ...
    # ... (Reprendre le code de la réponse précédente pour cette classe) ...
    @kernel_function(description="Récupère un aperçu (complet ou résumé) de l'état actuel de l'analyse.", name="get_current_state_snapshot")
    def get_current_state_snapshot(self, summarize: bool = True) -> str:
        """Retourne l'état actuel sous forme de chaîne JSON."""
        self._logger.info(f"Appel get_current_state_snapshot (state id: {id(self._state)}, summarize={summarize})...")
        try:
            snapshot_dict = self._state.get_state_snapshot(summarize=summarize)
            indent = 2 if not summarize else None
            snapshot_json = json.dumps(snapshot_dict, indent=indent, ensure_ascii=False, default=str)
            self._logger.info(" -> Snapshot de l'état généré avec succès.")
            self._logger.debug(f" -> Snapshot (summarize={summarize}): {snapshot_json[:500] + '...' if len(snapshot_json)>500 else snapshot_json}")
            return snapshot_json
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération/sérialisation du snapshot de l'état: {e}", exc_info=True)
            return json.dumps({"error": f"Erreur récupération/sérialisation snapshot: {e}"})

    @kernel_function(description="Ajoute une nouvelle tâche d'analyse à l'état.", name="add_analysis_task")
    def add_analysis_task(self, description: str) -> str:
        """Interface Kernel Function pour ajouter une tâche via l'état."""
        self._logger.info(f"Appel add_analysis_task (state id: {id(self._state)}): '{description[:60]}...'")
        try:
            task_id = self._state.add_task(description)
            self._logger.info(f" -> Tâche '{task_id}' ajoutée avec succès via l'état.")
            return task_id
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de la tâche '{description[:60]}...': {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur ajout tâche: {e}"

    @kernel_function(description="Ajoute un argument identifié à l'état.", name="add_identified_argument")
    def add_identified_argument(self, description: str) -> str:
        """Interface Kernel Function pour ajouter un argument via l'état."""
        self._logger.info(f"Appel add_identified_argument (state id: {id(self._state)}): '{description[:60]}...'")
        try:
            arg_id = self._state.add_argument(description)
            self._logger.info(f" -> Argument '{arg_id}' ajouté avec succès via l'état.")
            return arg_id
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de l'argument '{description[:60]}...': {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur ajout argument: {e}"

    @kernel_function(description="Ajoute un sophisme identifié à l'état.", name="add_identified_fallacy")
    def add_identified_fallacy(self, fallacy_type: str, justification: str, target_argument_id: Optional[str] = None) -> str:
        """Interface Kernel Function pour ajouter un sophisme via l'état."""
        self._logger.info(f"Appel add_identified_fallacy (state id: {id(self._state)}): Type='{fallacy_type}', Target='{target_argument_id or 'None'}'...")
        try:
            fallacy_id = self._state.add_fallacy(fallacy_type, justification, target_argument_id)
            self._logger.info(f" -> Sophisme '{fallacy_id}' ajouté avec succès via l'état.")
            return fallacy_id
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout du sophisme (Type: {fallacy_type}): {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur ajout sophisme: {e}"

    @kernel_function(description="Ajoute un belief set formel (ex: Propositional) à l'état.", name="add_belief_set")
    def add_belief_set(self, logic_type: str, content: str) -> str:
        """Interface Kernel Function pour ajouter un belief set via l'état. Valide le type logique."""
        self._logger.info(f"Appel add_belief_set (state id: {id(self._state)}): Type='{logic_type}'...")
        valid_logic_types = {"propositional": "Propositional", "pl": "Propositional"}
        normalized_logic_type = logic_type.strip().lower()

        if normalized_logic_type not in valid_logic_types:
            error_msg = f"Type logique '{logic_type}' non supporté. Types valides (insensible casse): {list(valid_logic_types.keys())}"
            self._logger.error(error_msg)
            return f"FUNC_ERROR: {error_msg}"

        validated_logic_type = valid_logic_types[normalized_logic_type]
        try:
            bs_id = self._state.add_belief_set(validated_logic_type, content)
            self._logger.info(f" -> Belief Set '{bs_id}' ajouté avec succès via l'état (Type: {validated_logic_type}).")
            return bs_id
        except Exception as e:
            self._logger.error(f"Erreur interne lors de l'ajout du Belief Set (Type: {validated_logic_type}): {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur interne ajout Belief Set: {e}"

    @kernel_function(description="Enregistre une requête formelle et son résultat brut dans le log de l'état.", name="log_query_result")
    def log_query_result(self, belief_set_id: str, query: str, raw_result: str) -> str:
        """Interface Kernel Function pour logger une requête via l'état."""
        self._logger.info(f"Appel log_query_result (state id: {id(self._state)}): BS_ID='{belief_set_id}', Query='{query[:60]}...'")
        try:
            log_id = self._state.log_query(belief_set_id, query, raw_result)
            self._logger.info(f" -> Requête '{log_id}' loggée avec succès via l'état.")
            return log_id
        except Exception as e:
            self._logger.error(f"Erreur lors du logging de la requête (BS_ID: {belief_set_id}): {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur logging requête: {e}"

    @kernel_function(description="Ajoute une réponse d'un agent à une tâche d'analyse spécifique dans l'état.", name="add_answer")
    def add_answer(self, task_id: str, author_agent: str, answer_text: str, source_ids: List[str]) -> str:
        """Interface Kernel Function pour ajouter une réponse via l'état."""
        self._logger.info(f"Appel add_answer (state id: {id(self._state)}): TaskID='{task_id}', Author='{author_agent}'...")
        try:
            self._state.add_answer(task_id, author_agent, answer_text, source_ids)
            self._logger.info(f" -> Réponse pour tâche '{task_id}' ajoutée avec succès via l'état.")
            return f"OK: Réponse pour {task_id} ajoutée."
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de la réponse pour la tâche '{task_id}': {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur ajout réponse pour {task_id}: {e}"

    @kernel_function(description="Enregistre la conclusion finale de l'analyse dans l'état.", name="set_final_conclusion")
    def set_final_conclusion(self, conclusion: str) -> str:
        """Interface Kernel Function pour enregistrer la conclusion via l'état."""
        self._logger.info(f"Appel set_final_conclusion (state id: {id(self._state)}): '{conclusion[:60]}...'")
        try:
            self._state.set_conclusion(conclusion)
            self._logger.info(f" -> Conclusion finale enregistrée avec succès via l'état.")
            return "OK: Conclusion finale enregistrée."
        except Exception as e:
            self._logger.error(f"Erreur lors de l'enregistrement de la conclusion finale: {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur enregistrement conclusion: {e}"

    @kernel_function(description="Désigne quel agent doit parler au prochain tour. Utiliser le nom EXACT de l'agent.", name="designate_next_agent")
    def designate_next_agent(self, agent_name: str) -> str:
        """Interface Kernel Function pour désigner le prochain agent via l'état."""
        self._logger.info(f"Appel designate_next_agent (state id: {id(self._state)}): Prochain = '{agent_name}'")
        try:
            self._state.designate_next_agent(agent_name)
            self._logger.info(f" -> Agent '{agent_name}' désigné avec succès via l'état.")
            return f"OK. Agent '{agent_name}' désigné pour le prochain tour."
        except Exception as e:
            self._logger.error(f"Erreur lors de la désignation de l'agent '{agent_name}': {e}", exc_info=True)
            return f"FUNC_ERROR: Erreur désignation agent {agent_name}: {e}"

# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.state_manager_plugin chargé.")
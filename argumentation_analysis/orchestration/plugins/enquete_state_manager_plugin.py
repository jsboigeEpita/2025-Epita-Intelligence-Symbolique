# argumentation_analysis/orchestration/plugins/enquete_state_manager_plugin.py
import json
import logging
from typing import Any, Dict, List, Optional

from semantic_kernel.functions import kernel_function

# Import des classes d'état nécessaires
from argumentation_analysis.core.enquete_states import BaseWorkflowState, EnquetePoliciereState, EnqueteCluedoState

# Logger spécifique pour ce plugin
plugin_logger = logging.getLogger(f"SK.{__name__}")
if not plugin_logger.handlers and not plugin_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    plugin_logger.addHandler(handler)
    plugin_logger.setLevel(logging.INFO)

class EnqueteStateManagerPlugin:
    """
    Plugin Semantic Kernel pour interagir avec l'état d'une enquête (EnquetePoliciereState, EnqueteCluedoState).
    Expose les méthodes de l'objet d'état comme des fonctions Kernel.
    """
    _state: BaseWorkflowState
    _logger: logging.Logger

    def __init__(self, state: BaseWorkflowState):
        """
        Initialise le plugin avec une instance d'état d'enquête.
        """
        self._state = state
        self._logger = plugin_logger
        self._logger.info(f"EnqueteStateManagerPlugin initialisé avec l'instance d'état (id: {id(self._state)}, type: {type(self._state).__name__}).")

    # --- Méthodes héritées de BaseWorkflowState ---

    @kernel_function(description="Ajoute une nouvelle tâche au workflow de l'enquête.", name="add_task")
    def add_task(self, description: str, assignee: str, task_id: Optional[str] = None) -> str:
        self._logger.info(f"Appel add_task: desc='{description[:50]}...', assignee='{assignee}'")
        try:
            task = self._state.add_task(description, assignee, task_id)
            return json.dumps(task)
        except Exception as e:
            self._logger.error(f"Erreur dans add_task: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Récupère les détails d'une tâche spécifique.", name="get_task")
    def get_task(self, task_id: str) -> str:
        self._logger.info(f"Appel get_task: task_id='{task_id}'")
        try:
            task = self._state.get_task(task_id)
            return json.dumps(task) if task else json.dumps(None)
        except Exception as e:
            self._logger.error(f"Erreur dans get_task: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Met à jour le statut d'une tâche.", name="update_task_status")
    def update_task_status(self, task_id: str, status: str) -> str:
        self._logger.info(f"Appel update_task_status: task_id='{task_id}', status='{status}'")
        try:
            success = self._state.update_task_status(task_id, status)
            return json.dumps({"success": success})
        except Exception as e:
            self._logger.error(f"Erreur dans update_task_status: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Récupère une liste de tâches, potentiellement filtrée par assigné ou statut.", name="get_tasks")
    def get_tasks(self, assignee: Optional[str] = None, status: Optional[str] = None) -> str:
        self._logger.info(f"Appel get_tasks: assignee='{assignee}', status='{status}'")
        try:
            tasks = self._state.get_tasks(assignee, status)
            return json.dumps(tasks)
        except Exception as e:
            self._logger.error(f"Erreur dans get_tasks: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Désigne quel agent doit parler au prochain tour. Utiliser le nom EXACT de l'agent.", name="designate_next_agent")
    def designate_next_agent(self, agent_name: str) -> str:
        self._logger.info(f"Appel designate_next_agent: Prochain = '{agent_name}'")
        try:
            self._state.designate_next_agent(agent_name)
            return json.dumps({"message": f"Agent '{agent_name}' désigné pour le prochain tour."})
        except Exception as e:
            self._logger.error(f"Erreur dans designate_next_agent: {e}", exc_info=True)
            return json.dumps({"error": str(e)})
            
    @kernel_function(description="Récupère l'agent désigné pour le prochain tour.", name="get_designated_next_agent")
    def get_designated_next_agent(self) -> str:
        self._logger.info(f"Appel get_designated_next_agent")
        try:
            agent_name = self._state.get_designated_next_agent()
            return json.dumps({"next_agent": agent_name})
        except Exception as e:
            self._logger.error(f"Erreur dans get_designated_next_agent: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    # --- Méthodes spécifiques à EnquetePoliciereState ---

    @kernel_function(description="Récupère la description principale du cas d'enquête.", name="get_case_description")
    def get_case_description(self) -> str:
        self._logger.info("Appel get_case_description")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode get_case_description n'est disponible que pour EnquetePoliciereState."})
        try:
            description = self._state.get_case_description()
            return json.dumps({"case_description": description})
        except Exception as e:
            self._logger.error(f"Erreur dans get_case_description: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Met à jour la description principale du cas d'enquête.", name="update_case_description")
    def update_case_description(self, new_description: str) -> str:
        self._logger.info(f"Appel update_case_description: new_desc='{new_description[:50]}...'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode update_case_description n'est disponible que pour EnquetePoliciereState."})
        try:
            self._state.update_case_description(new_description)
            return json.dumps({"message": "Description du cas mise à jour."})
        except Exception as e:
            self._logger.error(f"Erreur dans update_case_description: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Ajoute un élément identifié (preuve, témoignage, etc.) à l'enquête.", name="add_identified_element")
    def add_identified_element(self, element_type: str, description: str, source: str) -> str:
        self._logger.info(f"Appel add_identified_element: type='{element_type}', desc='{description[:50]}...'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode add_identified_element n'est disponible que pour EnquetePoliciereState."})
        try:
            element = self._state.add_identified_element(element_type, description, source)
            return json.dumps(element)
        except Exception as e:
            self._logger.error(f"Erreur dans add_identified_element: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Récupère les éléments identifiés, potentiellement filtrés par type.", name="get_identified_elements")
    def get_identified_elements(self, element_type: Optional[str] = None) -> str:
        self._logger.info(f"Appel get_identified_elements: type='{element_type}'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode get_identified_elements n'est disponible que pour EnquetePoliciereState."})
        try:
            elements = self._state.get_identified_elements(element_type)
            return json.dumps(elements)
        except Exception as e:
            self._logger.error(f"Erreur dans get_identified_elements: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Ajoute ou met à jour un Belief Set (ensemble de croyances/formules logiques).", name="add_or_update_belief_set")
    def add_or_update_belief_set(self, bs_id: str, content: str) -> str:
        self._logger.info(f"Appel add_or_update_belief_set: bs_id='{bs_id}'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode add_or_update_belief_set n'est disponible que pour EnquetePoliciereState."})
        try:
            self._state.add_or_update_belief_set(bs_id, content)
            return json.dumps({"message": f"Belief Set '{bs_id}' ajouté/mis à jour."})
        except Exception as e:
            self._logger.error(f"Erreur dans add_or_update_belief_set: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Récupère le contenu d'un Belief Set spécifique.", name="get_belief_set_content")
    def get_belief_set_content(self, bs_id: str) -> str:
        self._logger.info(f"Appel get_belief_set_content: bs_id='{bs_id}'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode get_belief_set_content n'est disponible que pour EnquetePoliciereState."})
        try:
            content = self._state.get_belief_set_content(bs_id)
            return json.dumps({"belief_set_id": bs_id, "content": content}) if content is not None else json.dumps(None)
        except Exception as e:
            self._logger.error(f"Erreur dans get_belief_set_content: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Liste les IDs de tous les Belief Sets existants.", name="list_belief_sets")
    def list_belief_sets(self) -> str:
        self._logger.info(f"Appel list_belief_sets")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode list_belief_sets n'est disponible que pour EnquetePoliciereState."})
        try:
            bs_ids = self._state.list_belief_sets()
            return json.dumps({"belief_set_ids": bs_ids})
        except Exception as e:
            self._logger.error(f"Erreur dans list_belief_sets: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Ajoute une nouvelle hypothèse à l'enquête.", name="add_hypothesis")
    def add_hypothesis(self, text: str, confidence_score: float, hypothesis_id: Optional[str] = None) -> str:
        self._logger.info(f"Appel add_hypothesis: text='{text[:50]}...', confidence={confidence_score}")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode add_hypothesis n'est disponible que pour EnquetePoliciereState."})
        try:
            hypothesis = self._state.add_hypothesis(text, confidence_score, hypothesis_id)
            return json.dumps(hypothesis)
        except Exception as e:
            self._logger.error(f"Erreur dans add_hypothesis: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Récupère une hypothèse spécifique par son ID.", name="get_hypothesis")
    def get_hypothesis(self, hypothesis_id: str) -> str:
        self._logger.info(f"Appel get_hypothesis: id='{hypothesis_id}'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode get_hypothesis n'est disponible que pour EnquetePoliciereState."})
        try:
            hypothesis = self._state.get_hypothesis(hypothesis_id)
            return json.dumps(hypothesis) if hypothesis else json.dumps(None)
        except Exception as e:
            self._logger.error(f"Erreur dans get_hypothesis: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Met à jour une hypothèse existante.", name="update_hypothesis")
    def update_hypothesis(
        self,
        hypothesis_id: str,
        new_text: Optional[str] = None,
        new_confidence: Optional[float] = None,
        new_status: Optional[str] = None,
        add_supporting_evidence_id: Optional[str] = None,
        add_contradicting_evidence_id: Optional[str] = None
    ) -> str:
        self._logger.info(f"Appel update_hypothesis: id='{hypothesis_id}'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode update_hypothesis n'est disponible que pour EnquetePoliciereState."})
        try:
            success = self._state.update_hypothesis(
                hypothesis_id, new_text, new_confidence, new_status,
                add_supporting_evidence_id, add_contradicting_evidence_id
            )
            return json.dumps({"success": success})
        except Exception as e:
            self._logger.error(f"Erreur dans update_hypothesis: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Récupère les hypothèses, potentiellement filtrées par statut.", name="get_hypotheses")
    def get_hypotheses(self, status: Optional[str] = None) -> str:
        self._logger.info(f"Appel get_hypotheses: status='{status}'")
        if not isinstance(self._state, EnquetePoliciereState):
            return json.dumps({"error": "La méthode get_hypotheses n'est disponible que pour EnquetePoliciereState."})
        try:
            hypotheses = self._state.get_hypotheses(status)
            return json.dumps(hypotheses)
        except Exception as e:
            self._logger.error(f"Erreur dans get_hypotheses: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    # --- Méthodes spécifiques à EnqueteCluedoState ---

    @kernel_function(description="Récupère les éléments du jeu Cluedo (suspects, armes, lieux).", name="get_cluedo_game_elements")
    def get_cluedo_game_elements(self) -> str:
        self._logger.info("Appel get_cluedo_game_elements")
        if not isinstance(self._state, EnqueteCluedoState):
            return json.dumps({"error": "La méthode get_cluedo_game_elements n'est disponible que pour EnqueteCluedoState."})
        try:
            elements = self._state.get_elements_jeu()
            return json.dumps(elements)
        except Exception as e:
            self._logger.error(f"Erreur dans get_cluedo_game_elements: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Récupère l'ID du Belief Set principal pour l'enquête Cluedo.", name="get_cluedo_main_belief_set_id")
    def get_cluedo_main_belief_set_id(self) -> str:
        self._logger.info("Appel get_cluedo_main_belief_set_id")
        if not isinstance(self._state, EnqueteCluedoState):
            return json.dumps({"error": "La méthode get_cluedo_main_belief_set_id n'est disponible que pour EnqueteCluedoState."})
        try:
            return json.dumps({"main_cluedo_bs_id": self._state.main_cluedo_bs_id})
        except Exception as e:
            self._logger.error(f"Erreur dans get_cluedo_main_belief_set_id: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(description="Propose une solution finale à l'enquête Cluedo.", name="propose_final_solution")
    def propose_final_solution(self, solution: Dict[str, str]) -> str:
        self._logger.info(f"Appel propose_final_solution: solution='{solution}'")
        if not isinstance(self._state, EnqueteCluedoState):
            return json.dumps({"error": "La méthode propose_final_solution n'est disponible que pour EnqueteCluedoState."})
        try:
            self._state.propose_final_solution(solution)
            return json.dumps({"message": "Solution finale enregistrée.", "solution_proposed": True})
        except Exception as e:
            self._logger.error(f"Erreur dans propose_final_solution: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

# Log de chargement du module
module_logger = logging.getLogger(__name__)
module_logger.debug("Module argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin chargé.")
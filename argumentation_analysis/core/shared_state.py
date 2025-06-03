# core/shared_state.py
import json
from typing import Dict, List, Any, Optional
import logging

# Logger spécifique pour l'état
state_logger = logging.getLogger("RhetoricalAnalysisState")
# Assurer qu'un handler de base est présent si non configuré globalement tôt
if not state_logger.handlers and not state_logger.propagate:
     handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); state_logger.addHandler(handler); state_logger.setLevel(logging.INFO)

class RhetoricalAnalysisState:
    """Représente l'état partagé d'une analyse rhétorique collaborative."""

    # ... (Le code complet de la classe RhetoricalAnalysisState tel que fourni dans la réponse précédente va ici) ...
    # Structure des données de l'état (pour référence)
    raw_text: str
    analysis_tasks: Dict[str, str] # {task_id: description}
    identified_arguments: Dict[str, str] # {arg_id: description}
    identified_fallacies: Dict[str, Dict[str, str]] # {fallacy_id: {type:..., justification:..., target_argument_id?:...}}
    belief_sets: Dict[str, Dict[str, str]] # {bs_id: {logic_type:..., content:...}}
    query_log: List[Dict[str, str]] # [{log_id:..., belief_set_id:..., query:..., raw_result:...}]
    answers: Dict[str, Dict[str, Any]] # {task_id: {author_agent:..., answer_text:..., source_ids:[...]}}
    final_conclusion: Optional[str]
    _next_agent_designated: Optional[str] # Nom de l'agent désigné pour le prochain tour

    def __init__(self, initial_text: str):
        """Initialise un état vide avec le texte brut."""
        self.raw_text = initial_text
        self.analysis_tasks = {}
        self.identified_arguments = {}
        self.identified_fallacies = {}
        self.belief_sets = {}
        self.query_log = []
        self.answers = {}
        self.extracts = []
        self.errors = []
        self.final_conclusion = None
        self._next_agent_designated = None
        state_logger.debug(f"Nouvelle instance RhetoricalAnalysisState créée (id: {id(self)}) avec texte (longueur: {len(initial_text)}).")

    def _generate_id(self, prefix: str, current_dict_or_list: Any) -> str:
        """Génère un ID simple basé sur la taille actuelle."""
        index = 0
        try:
            if isinstance(current_dict_or_list, (dict, list)):
                index = len(current_dict_or_list)
            else:
                 index = 0
                 state_logger.warning(f"_generate_id: Type inattendu '{type(current_dict_or_list)}' pour prefix '{prefix}'. Index sera 0.")
        except Exception as e:
            state_logger.error(f"Erreur dans _generate_id pour prefix '{prefix}': {e}", exc_info=True)
            index = 999
        safe_index = min(index, 9999)
        return f"{prefix}_{safe_index + 1}"

    def add_task(self, description: str) -> str:
        """Ajoute une tâche d'analyse et retourne son ID."""
        task_id = self._generate_id("task", self.analysis_tasks)
        self.analysis_tasks[task_id] = description
        state_logger.info(f"Tâche ajoutée: {task_id} - '{description[:60]}...'")
        state_logger.debug(f"État tasks après ajout {task_id}: {self.analysis_tasks}")
        return task_id

    def add_argument(self, description: str) -> str:
        """Ajoute un argument identifié et retourne son ID."""
        arg_id = self._generate_id("arg", self.identified_arguments)
        self.identified_arguments[arg_id] = description
        state_logger.info(f"Argument ajouté: {arg_id} - '{description[:60]}...'")
        state_logger.debug(f"État arguments après ajout {arg_id}: {self.identified_arguments}")
        return arg_id

    def add_fallacy(self, fallacy_type: str, justification: str, target_arg_id: Optional[str] = None) -> str:
        """Ajoute un sophisme identifié et retourne son ID."""
        fallacy_id = self._generate_id("fallacy", self.identified_fallacies)
        entry = {"type": fallacy_type, "justification": justification}
        log_target_info = ""
        if target_arg_id:
             if target_arg_id not in self.identified_arguments:
                 state_logger.warning(f"ID argument cible '{target_arg_id}' pour sophisme '{fallacy_id}' non trouvé dans les arguments identifiés ({list(self.identified_arguments.keys())}).")
             entry["target_argument_id"] = target_arg_id
             log_target_info = f" (cible: {target_arg_id})"
        self.identified_fallacies[fallacy_id] = entry
        state_logger.info(f"Sophisme ajouté: {fallacy_id} - Type: {fallacy_type}{log_target_info}")
        state_logger.debug(f"État fallacies après ajout {fallacy_id}: {self.identified_fallacies}")
        return fallacy_id

    def add_belief_set(self, logic_type: str, content: str) -> str:
        """Ajoute un belief set formel et retourne son ID."""
        normalized_type = logic_type.strip().lower().replace(" ", "_")
        bs_id = self._generate_id(f"{normalized_type}_bs", self.belief_sets)
        self.belief_sets[bs_id] = {"logic_type": logic_type, "content": content}
        state_logger.info(f"Belief Set ajouté: {bs_id} - Type: {logic_type}")
        state_logger.debug(f"État belief_sets après ajout {bs_id}: {self.belief_sets}")
        return bs_id

    def log_query(self, belief_set_id: str, query: str, raw_result: str) -> str:
         """Enregistre une requête formelle et son résultat brut."""
         log_id = self._generate_id("qlog", self.query_log)
         if belief_set_id not in self.belief_sets:
             state_logger.warning(f"ID Belief Set '{belief_set_id}' pour query log '{log_id}' non trouvé dans les belief sets ({list(self.belief_sets.keys())}).")
         log_entry = {"log_id": log_id, "belief_set_id": belief_set_id, "query": query, "raw_result": raw_result}
         self.query_log.append(log_entry)
         state_logger.info(f"Requête loggée: {log_id} (sur BS: {belief_set_id}, Query: '{query[:60]}...')")
         state_logger.debug(f"État query_log après ajout {log_id} (taille: {len(self.query_log)}): {self.query_log}")
         return log_id

    def add_answer(self, task_id: str, author_agent: str, answer_text: str, source_ids: List[str]):
        """Ajoute la réponse d'un agent à une tâche spécifiques."""
        if task_id not in self.analysis_tasks:
            state_logger.warning(f"ID Tâche '{task_id}' pour réponse de '{author_agent}' non trouvé dans les tâches définies ({list(self.analysis_tasks.keys())}).")
        self.answers[task_id] = {"author_agent": author_agent, "answer_text": answer_text, "source_ids": source_ids}
        state_logger.info(f"Réponse ajoutée pour tâche '{task_id}' par agent '{author_agent}'.")
        state_logger.debug(f"État answers après ajout réponse pour {task_id}: {self.answers}")

    def set_conclusion(self, conclusion: str):
        """Enregistre la conclusion finale de l'analyse."""
        self.final_conclusion = conclusion
        state_logger.info(f"Conclusion finale enregistrée : '{conclusion[:60]}...'")
        state_logger.debug(f"État final_conclusion après enregistrement: {self.final_conclusion is not None}")

    def designate_next_agent(self, agent_name: str):
        """Désigne l'agent qui doit parler au prochain tour."""
        self._next_agent_designated = agent_name
        state_logger.info(f"Prochain agent désigné: '{agent_name}'")
        state_logger.debug(f"État _next_agent_designated après désignation: '{self._next_agent_designated}'")
    
    def add_extract(self, name: str, content: str) -> str:
        """Ajoute un extrait de texte et retourne son ID."""
        if not hasattr(self, 'extracts'):
            self.extracts = []
        extract_id = self._generate_id("extract", self.extracts)
        extract = {"id": extract_id, "name": name, "content": content}
        self.extracts.append(extract)
        state_logger.info(f"Extrait ajouté: {extract_id} - '{name}'")
        state_logger.debug(f"État extracts après ajout {extract_id}: {self.extracts}")
        return extract_id
    
    def log_error(self, agent_name: str, message: str) -> str:
        """Enregistre une erreur et retourne son ID."""
        if not hasattr(self, 'errors'):
            self.errors = []
        error_id = self._generate_id("error", self.errors)
        error = {"id": error_id, "agent_name": agent_name, "message": message, "timestamp": None}
        self.errors.append(error)
        state_logger.warning(f"Erreur enregistrée: {error_id} - Agent: {agent_name} - '{message}'")
        state_logger.debug(f"État errors après ajout {error_id}: {self.errors}")
        return error_id

    def consume_next_agent_designation(self) -> Optional[str]:
        """Récupère le nom de l'agent désigné et réinitialise la désignation."""
        agent_name = self._next_agent_designated
        self._next_agent_designated = None
        if agent_name:
            state_logger.info(f"Désignation pour '{agent_name}' consommée.")
        return agent_name

    def reset_state(self):
        """Réinitialise l'état à son état initial (vide sauf texte brut)."""
        state_logger.info(">>> Réinitialisation de l'état d'analyse...")
        initial_text = self.raw_text
        self.__init__(initial_text)
        assert not self.analysis_tasks, "Reset analysis_tasks failed"
        assert not self.identified_arguments, "Reset identified_arguments failed"
        assert not self.identified_fallacies, "Reset identified_fallacies failed"
        assert not self.belief_sets, "Reset belief_sets failed"
        assert not self.query_log, "Reset query_log failed"
        assert not self.answers, "Reset answers failed"
        assert self.final_conclusion is None, "Reset final_conclusion failed"
        assert self._next_agent_designated is None, "Reset _next_agent_designated failed"
        # Réinitialiser les attributs extracts et errors s'ils existent
        if hasattr(self, 'extracts'):
            self.extracts = []
        if hasattr(self, 'errors'):
            self.errors = []
        state_logger.info("<<< Réinitialisation de l'état terminée et vérifiée.")

    def get_state_snapshot(self, summarize: bool = False) -> Dict[str, Any]:
        """Retourne un dictionnaire représentant l'état actuel (complet ou résumé)."""
        if summarize:
             # Assurer que le texte est tronqué dans le résumé
             truncated_text = self.raw_text[:50] + "..." if len(self.raw_text) > 50 else self.raw_text
             return {
                 "raw_text": self.raw_text[:150] + "..." if len(self.raw_text) > 150 else self.raw_text,
                 "raw_text_snippet": self.raw_text[:150] + "..." if len(self.raw_text) > 150 else self.raw_text,
                 "task_count": len(self.analysis_tasks),
                 "tasks_defined": list(self.analysis_tasks.keys()),
                 "argument_count": len(self.identified_arguments),
                 "fallacy_count": len(self.identified_fallacies),
                 "belief_set_count": len(self.belief_sets),
                 "query_log_count": len(self.query_log),
                 "answer_count": len(self.answers),
                 "extract_count": len(getattr(self, 'extracts', [])),
                 "error_count": len(getattr(self, 'errors', [])),
                 "tasks_answered": list(self.answers.keys()),
                 "conclusion_present": self.final_conclusion is not None,
                 "next_agent_designated": self._next_agent_designated
             }
        else:
            return json.loads(self.to_json(indent=None))

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Sérialise l'état actuel en chaîne JSON."""
        state_dict = {k: v for k, v in self.__dict__.items() if not callable(v) and not k.startswith("_logger")}
        try:
            return json.dumps(state_dict, indent=indent, ensure_ascii=False, default=str)
        except TypeError as e:
            state_logger.error(f"Erreur de sérialisation JSON de l'état: {e}")
            safe_dict = {k: repr(v) for k, v in state_dict.items()}
            return json.dumps({"error": f"JSON serialization failed: {e}", "safe_state_repr": safe_dict}, indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RhetoricalAnalysisState':
        """Crée une instance d'état à partir d'un dictionnaire."""
        state = cls(data.get('raw_text', ''))
        state.analysis_tasks = data.get('analysis_tasks', {})
        state.identified_arguments = data.get('identified_arguments', {})
        state.identified_fallacies = data.get('identified_fallacies', {})
        state.belief_sets = data.get('belief_sets', {})
        state.query_log = data.get('query_log', [])
        state.answers = data.get('answers', {})
        state.extracts = data.get('extracts', [])
        state.errors = data.get('errors', [])
        state.final_conclusion = data.get('final_conclusion', None)
        state._next_agent_designated = data.get('_next_agent_designated', None)
        state_logger.debug(f"Instance RhetoricalAnalysisState créée depuis dict (id: {id(state)}).")
        return state
    
# Optionnel : Ajouter un log à la fin du fichier pour confirmer le chargement du module
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.shared_state chargé.")

# Créer un alias SharedState pour maintenir la compatibilité avec le code existant
SharedState = RhetoricalAnalysisState
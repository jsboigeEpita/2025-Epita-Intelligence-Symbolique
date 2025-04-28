# core/strategies.py
from semantic_kernel.agents import Agent
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.agents.strategies.selection.selection_strategy import SelectionStrategy
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from typing import List, Dict, TYPE_CHECKING
import logging
from pydantic import PrivateAttr

# Importer la classe d'état
from .shared_state import RhetoricalAnalysisState

# Type hinting (si nécessaire, mais RhetoricalAnalysisState est importé)
if TYPE_CHECKING:
    pass

# Loggers
termination_logger = logging.getLogger("Orchestration.Termination")
if not termination_logger.handlers and not termination_logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); termination_logger.addHandler(handler); termination_logger.setLevel(logging.INFO)

selection_logger = logging.getLogger("Orchestration.Selection")
if not selection_logger.handlers and not selection_logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); selection_logger.addHandler(handler); selection_logger.setLevel(logging.INFO)


class SimpleTerminationStrategy(TerminationStrategy):
    """Stratégie d'arrêt simple basée sur la conclusion ou le nombre max de tours."""
    _state: 'RhetoricalAnalysisState'
    _max_steps: int
    _step_count: int
    _instance_id: int

    def __init__(self, state: 'RhetoricalAnalysisState', max_steps: int = 15):
        """Initialise avec l'état partagé et le nombre max de tours."""
        super().__init__()
        if not hasattr(state, 'final_conclusion'):
             raise TypeError("Objet 'state' invalide pour SimpleTerminationStrategy.")
        self._state = state
        self._max_steps = max(1, max_steps)
        self._step_count = 0
        self._instance_id = id(self)
        self._logger = termination_logger
        self._logger.info(f"SimpleTerminationStrategy instance {self._instance_id} créée (max_steps={self._max_steps}, state_id={id(self._state)}).")

    async def should_terminate(self, agent: Agent, history: List[ChatMessageContent]) -> bool:
        """Vérifie si la conversation doit se terminer."""
        self._step_count += 1
        step_info = f"Tour {self._step_count}/{self._max_steps}"
        terminate = False
        reason = ""
        try:
            if self._state.final_conclusion is not None:
                terminate = True
                reason = "Conclusion finale trouvée dans l'état."
        except Exception as e_state_access:
             self._logger.error(f"[{self._instance_id}] Erreur accès état pour conclusion: {e_state_access}")
             terminate = False
        if not terminate and self._step_count > self._max_steps:
            terminate = True
            reason = f"Nombre max étapes ({self._max_steps}) atteint."
        if terminate:
            self._logger.info(f"[{self._instance_id}] Terminaison OUI. {step_info}. Raison: {reason}")
            return True
        else:
            self._logger.debug(f"[{self._instance_id}] Terminaison NON. {step_info}.")
            return False

    async def reset(self) -> None:
        """Réinitialise le compteur de tours."""
        self._logger.info(f"[{self._instance_id}] Reset SimpleTerminationStrategy (compteur {self._step_count} -> 0).")
        self._step_count = 0
        try:
            if self._state.final_conclusion is not None:
                 self._logger.warning(f"[{self._instance_id}] Reset strat, mais conclusion toujours présente dans état!")
        except Exception as e:
             self._logger.warning(f"[{self._instance_id}] Erreur accès état pendant reset: {e}")


class DelegatingSelectionStrategy(SelectionStrategy):
    """Stratégie de sélection qui priorise la désignation explicite via l'état."""
    # *** CORRECTION: Utiliser PrivateAttr pour les champs gérés par __init__ ***
    _agents_map: Dict[str, Agent] = PrivateAttr()
    _default_agent_name: str = PrivateAttr(default="ProjectManagerAgent") # On peut mettre le défaut ici
    _analysis_state: 'RhetoricalAnalysisState' = PrivateAttr()
    # Ces deux-là ne semblent pas faire partie du modèle Pydantic de base, on peut les laisser
    # S'ils ne sont pas définis par Pydantic, ils doivent être explicitement typés
    _instance_id: int
    _logger: logging.Logger

    def __init__(self, agents: List[Agent], state: 'RhetoricalAnalysisState', default_agent_name: str = "ProjectManagerAgent"):
        """Initialise avec agents, état, et nom agent par défaut."""
        # L'appel super() doit rester ici
        super().__init__()
        if not isinstance(agents, list) or not all(isinstance(a, Agent) for a in agents):
            raise TypeError("'agents' doit être une liste d'instances Agent.")
        # S'assurer que la classe State est définie et que l'objet state a la bonne méthode
        if 'RhetoricalAnalysisState' not in globals() or not isinstance(state, RhetoricalAnalysisState) or not hasattr(state, 'consume_next_agent_designation'):
             raise TypeError("Objet 'state' invalide ou classe RhetoricalAnalysisState non définie pour DelegatingSelectionStrategy.")

        # *** CORRECTION: Assigner aux attributs privés ***
        self._agents_map = {agent.name: agent for agent in agents}
        self._analysis_state = state
        self._default_agent_name = default_agent_name # Le paramètre a priorité sur le défaut de PrivateAttr

        # Le reste de l'initialisation utilise maintenant les attributs privés
        self._instance_id = id(self)
        self._logger = selection_logger

        if self._default_agent_name not in self._agents_map:
            if not self._agents_map: raise ValueError("Liste d'agents vide.")
            first_agent_name = list(self._agents_map.keys())[0]
            self._logger.warning(f"[{self._instance_id}] Agent défaut '{self._default_agent_name}' non trouvé. Fallback -> '{first_agent_name}'.")
            self._default_agent_name = first_agent_name # Mettre à jour l'attribut privé

        self._logger.info(f"DelegatingSelectionStrategy instance {self._instance_id} créée (agents: {list(self._agents_map.keys())}, default: '{self._default_agent_name}', state_id={id(self._analysis_state)}).")

    async def next(self, agents: List[Agent], history: List[ChatMessageContent]) -> Agent:
        """Sélectionne le prochain agent à parler."""
        self._logger.debug(f"[{self._instance_id}] Appel next()...")
        # *** CORRECTION: Utiliser les attributs privés pour la logique ***
        default_agent_instance = self._agents_map.get(self._default_agent_name)
        if not default_agent_instance:
            self._logger.error(f"[{self._instance_id}] ERREUR: Agent défaut '{self._default_agent_name}' introuvable! Retourne premier agent.")
            available_agents = list(self._agents_map.values()) # Utilise _agents_map
            if not available_agents: raise RuntimeError("Aucun agent disponible.")
            return available_agents[0]

        try:
            # Utilise l'attribut privé _analysis_state
            designated_agent_name = self._analysis_state.consume_next_agent_designation()
        except Exception as e_state_access:
            self._logger.error(f"[{self._instance_id}] Erreur accès état pour désignation: {e_state_access}. Retour PM.")
            return default_agent_instance

        if designated_agent_name:
            self._logger.info(f"[{self._instance_id}] Désignation explicite: '{designated_agent_name}'.")
            # Utilise _agents_map
            designated_agent = self._agents_map.get(designated_agent_name)
            if designated_agent:
                self._logger.info(f" -> Sélection agent désigné: {designated_agent.name}")
                return designated_agent
            else:
                self._logger.error(f"[{self._instance_id}] Agent désigné '{designated_agent_name}' INTROUVABLE! Retour PM.")
                return default_agent_instance

        self._logger.debug(f"[{self._instance_id}] Pas de désignation. Fallback.")
        if not history:
            # Utilise _default_agent_name
            self._logger.info(f" -> Sélection (fallback): Premier tour -> Agent défaut ({self._default_agent_name}).")
            return default_agent_instance

        last_message = history[-1]
        last_author_name = getattr(last_message, 'name', getattr(last_message, 'author_name', None))
        last_role = getattr(last_message, 'role', AuthorRole.SYSTEM)
        self._logger.debug(f"   Dernier message: Role={last_role.name}, Author='{last_author_name}'")

        agent_to_select = default_agent_instance # Par défaut, on retourne au PM
        # Utilise _default_agent_name
        if last_role == AuthorRole.ASSISTANT and last_author_name != self._default_agent_name:
            self._logger.info(f" -> Sélection (fallback): Agent '{last_author_name}' a parlé -> Retour PM.")
        elif last_role == AuthorRole.USER:
             # Utilise _default_agent_name
            self._logger.info(f" -> Sélection (fallback): User a parlé -> Agent défaut ({self._default_agent_name}).")
        elif last_role == AuthorRole.TOOL:
             # Utilise _default_agent_name
             self._logger.info(f" -> Sélection (fallback): Outil a parlé -> Agent défaut ({self._default_agent_name}).")
        # Si le PM a parlé sans désigner, on retourne au PM (implicite car agent_to_select = default_agent_instance)
        else: # Autres cas ou PM a parlé sans désigner
            # Utilise _default_agent_name
            self._logger.info(f" -> Sélection (fallback): Rôle '{last_role.name}', Author '{last_author_name}' -> Agent défaut ({self._default_agent_name}).")

        self._logger.info(f" -> Agent sélectionné (fallback): {agent_to_select.name}")
        return agent_to_select

    async def reset(self) -> None:
        """Réinitialise la stratégie."""
        self._logger.info(f"[{self._instance_id}] Reset DelegatingSelectionStrategy.")
        try:
            # Utilise _analysis_state
            consumed = self._analysis_state.consume_next_agent_designation()
            if consumed: self._logger.debug(f"   Ancienne désignation '{consumed}' effacée.")
        except Exception as e:
            self._logger.warning(f"   Erreur accès état pendant reset sélection: {e}")


# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.strategies chargé.")
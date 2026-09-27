# core/strategies.py
# CD #1534: inherit the REAL Semantic Kernel strategy bases so our strategy
# instances are accepted by AgentGroupChat's Pydantic validator.
from semantic_kernel.contents import ChatMessageContent

# from semantic_kernel.contents import AuthorRole

from typing import List, Dict, TYPE_CHECKING
import logging
from pydantic import PrivateAttr

# CD #1534 (anti-#1019): AgentGroupChat.selection_strategy is type-annotated to
# SK's SelectionStrategy, so its Pydantic validator (model_type) only accepts
# real SK subclasses. The previous import pointed at
# argumentation_analysis.orchestration.base, whose SelectionStrategy /
# TerminationStrategy are a LOCAL BaseModel+ABC stub with no link to SK — so SK
# silently rejected our instances and the conversational mode fell back to
# round-robin forever (the failure was logged as a WARNING, then masked).
# SK's bases expose the SAME abstract signatures as the stub —
#   SelectionStrategy.next(self, agents, history) -> Agent
#   TerminationStrategy.should_terminate(self, agent, history) -> bool
# — verified firsthand on SK 1.34.0 — so no method-body change is required, only
# the base class. The cluedo strategies (CyclicSelectionStrategy /
# OracleTerminationStrategy in orchestration/strategies.py) still use the local
# stub; they are never passed to AgentGroupChat and are deliberately left
# untouched (anti-pendule: the stub has other consumers).
from semantic_kernel.agents.strategies.selection.selection_strategy import (
    SelectionStrategy,
)
from semantic_kernel.agents.strategies.termination.termination_strategy import (
    TerminationStrategy,
)

# Importer la classe d'état
from .shared_state import RhetoricalAnalysisState, record_unresolved_designation

# Type hinting — the agents flowing through selection/termination ARE SK
# agents (BaseAgent extends ChatCompletionAgent extends this Agent), so the
# annotation names SK's class directly. The previous import pointed at
# ``abc.agent_bases``, which exports no ``Agent`` symbol (#2137).
if TYPE_CHECKING:
    from semantic_kernel.agents.agent import Agent

# Loggers
termination_logger = logging.getLogger("Orchestration.Termination")
if not termination_logger.handlers and not termination_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    termination_logger.addHandler(handler)
    termination_logger.setLevel(logging.INFO)

selection_logger = logging.getLogger("Orchestration.Selection")
if not selection_logger.handlers and not selection_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    selection_logger.addHandler(handler)
    selection_logger.setLevel(logging.INFO)


class SimpleTerminationStrategy(TerminationStrategy):
    """Stratégie d'arrêt simple basée sur la conclusion ou le nombre max de tours."""

    _state: "RhetoricalAnalysisState"
    _max_steps: int
    _step_count: int
    _instance_id: int

    def __init__(self, state: "RhetoricalAnalysisState", max_steps: int = 15):
        """Initialise avec l'état partagé et le nombre max de tours."""
        super().__init__()
        if not hasattr(state, "final_conclusion"):
            raise TypeError("Objet 'state' invalide pour SimpleTerminationStrategy.")
        self._state = state
        self._max_steps = max(1, max_steps)
        self._step_count = 0
        self._instance_id = id(self)
        self._logger = termination_logger
        self._logger.info(
            f"SimpleTerminationStrategy instance {self._instance_id} créée (max_steps={self._max_steps}, state_id={id(self._state)})."
        )

    async def should_terminate(
        self, agent: "Agent", history: List[ChatMessageContent]
    ) -> bool:
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
            self._logger.error(
                f"[{self._instance_id}] Erreur accès état pour conclusion: {e_state_access}"
            )
            terminate = False
        if not terminate and self._step_count >= self._max_steps:
            terminate = True
            reason = f"Nombre max étapes ({self._max_steps}) atteint."
        if terminate:
            self._logger.info(
                f"[{self._instance_id}] Terminaison OUI. {step_info}. Raison: {reason}"
            )
            return True
        else:
            self._logger.debug(f"[{self._instance_id}] Terminaison NON. {step_info}.")
            return False

    async def reset(self) -> None:
        """Réinitialise le compteur de tours."""
        self._logger.info(
            f"[{self._instance_id}] Reset SimpleTerminationStrategy (compteur {self._step_count} -> 0)."
        )
        self._step_count = 0
        try:
            if self._state.final_conclusion is not None:
                self._logger.warning(
                    f"[{self._instance_id}] Reset strat, mais conclusion toujours présente dans état!"
                )
        except Exception as e:
            self._logger.warning(
                f"[{self._instance_id}] Erreur accès état pendant reset: {e}"
            )


class DelegatingSelectionStrategy(SelectionStrategy):
    """Stratégie de sélection qui priorise la désignation explicite via l'état."""

    _agents_map: Dict[str, "Agent"] = PrivateAttr()
    _default_agent_name: str = PrivateAttr(default="ProjectManager")
    _analysis_state: "RhetoricalAnalysisState" = PrivateAttr()
    _instance_id: int  # Non géré par Pydantic, initialisé dans __init__
    _logger: logging.Logger  # Non géré par Pydantic, initialisé dans __init__

    def __init__(
        self,
        agents: List["Agent"],
        state: "RhetoricalAnalysisState",
        default_agent_name: str = "ProjectManager",
    ):
        super().__init__()
        if not isinstance(agents, list):
            raise TypeError("'agents' doit être une liste d'agents.")
        for a in agents:
            if not hasattr(a, "name"):
                raise TypeError(
                    f"Chaque agent doit avoir un attribut 'name'. Agent problématique: {a}"
                )
        if not isinstance(state, RhetoricalAnalysisState) or not hasattr(
            state, "consume_next_agent_designation"
        ):
            raise TypeError(
                "Objet 'state' invalide ou classe RhetoricalAnalysisState non définie pour DelegatingSelectionStrategy."
            )

        self._agents_map = {agent.name: agent for agent in agents}
        self._analysis_state = state
        self._default_agent_name = default_agent_name

        self._instance_id = id(self)
        self._logger = selection_logger

        if self._default_agent_name not in self._agents_map:
            if not self._agents_map:
                raise ValueError("Liste d'agents vide.")
            first_agent_name = list(self._agents_map.keys())[0]
            self._logger.warning(
                f"[{self._instance_id}] Agent défaut '{self._default_agent_name}' non trouvé. Fallback -> '{first_agent_name}'."
            )
            self._default_agent_name = first_agent_name

        self._logger.info(
            f"DelegatingSelectionStrategy instance {self._instance_id} créée (agents: {list(self._agents_map.keys())}, default: '{self._default_agent_name}', state_id={id(self._analysis_state)})."
        )

    async def next(
        self, agents: List["Agent"], history: List[ChatMessageContent]
    ) -> "Agent":
        """Sélectionne le prochain agent à parler."""
        self._logger.debug(f"[{self._instance_id}] Appel next()...")

        try:
            designated_agent_name = (
                self._analysis_state.consume_next_agent_designation()
            )
            if designated_agent_name:
                self._logger.info(
                    f"[{self._instance_id}] Désignation explicite: '{designated_agent_name}'."
                )
                designated_agent = self._agents_map.get(designated_agent_name)
                if designated_agent:
                    self._logger.info(
                        f" -> Sélection agent désigné: {designated_agent.name}"
                    )
                    return designated_agent
                else:
                    # #1751: a log line is not an effect. The turn that follows
                    # is the DEFAULT agent — the PM, first in every phase
                    # casting — so without a trace entry an absorbed
                    # designation is indistinguishable from an honoured one.
                    record_unresolved_designation(
                        self._analysis_state,
                        requested_agent=designated_agent_name,
                        present_agents=list(self._agents_map.keys()),
                        selection_path="delegating",
                    )
                    self._logger.error(
                        f"[{self._instance_id}] Agent désigné '{designated_agent_name}' INTROUVABLE! Poursuite avec fallback."
                    )
        except Exception as e_state_access:
            self._logger.error(
                f"[{self._instance_id}] Erreur accès état pour désignation: {e_state_access}. Poursuite avec fallback."
            )

        default_agent_instance = self._agents_map.get(self._default_agent_name)
        if not default_agent_instance:
            self._logger.error(
                f"[{self._instance_id}] ERREUR: Agent défaut '{self._default_agent_name}' introuvable! Retourne premier agent."
            )
            available_agents = list(self._agents_map.values())
            if not available_agents:
                raise RuntimeError("Aucun agent disponible.")
            return available_agents[0]

        self._logger.debug(
            f"[{self._instance_id}] Pas de désignation valide. Logique de fallback."
        )
        if not history:
            self._logger.info(
                f" -> Sélection (fallback): Premier tour -> Agent défaut ({self._default_agent_name})."
            )
            return default_agent_instance

        agent_to_select = default_agent_instance
        self._logger.info(f" -> Agent sélectionné (fallback): {agent_to_select.name}")
        return agent_to_select

    async def reset(self) -> None:
        """Réinitialise la stratégie."""
        self._logger.info(f"[{self._instance_id}] Reset DelegatingSelectionStrategy.")
        try:
            consumed = self._analysis_state.consume_next_agent_designation()
            if consumed:
                self._logger.debug(f"   Ancienne désignation '{consumed}' effacée.")
        except Exception as e:
            self._logger.warning(f"   Erreur accès état pendant reset sélection: {e}")


module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.strategies chargé.")

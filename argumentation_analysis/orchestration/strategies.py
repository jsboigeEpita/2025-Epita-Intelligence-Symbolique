# argumentation_analysis/orchestration/strategies.py
"""Module contenant les stratégies de sélection et de terminaison pour les conversations multi-agents."""

import logging
from typing import List, Dict, Any
from semantic_kernel.contents import ChatMessageContent
from pydantic import Field

from .base import Agent, SelectionStrategy, TerminationStrategy
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState


class CyclicSelectionStrategy(SelectionStrategy):
    """
    Stratégie de sélection cyclique adaptée au workflow Oracle : Sherlock → Watson → Moriarty.

    Implémente une sélection cyclique avec adaptations contextuelles optionnelles
    selon l'état du jeu et les interactions précédentes.
    """

    def __init__(
        self,
        agents: List[Agent],
        adaptive_selection: bool = False,
        oracle_state: "CluedoOracleState" = None,
    ):
        """
        Initialise la stratégie de sélection cyclique.

        Args:
            agents: Liste des agents dans l'ordre cyclique souhaité
            adaptive_selection: Active les adaptations contextuelles (Phase 2)
            oracle_state: État Oracle pour accès au contexte (Phase C)
        """
        super().__init__()
        # Stockage direct dans __dict__ pour éviter les problèmes Pydantic
        self.__dict__["agents"] = agents
        self.__dict__["agent_order"] = [agent.name for agent in agents]
        self.__dict__["current_index"] = 0
        self.__dict__["adaptive_selection"] = adaptive_selection
        self.__dict__["turn_count"] = 0
        self.__dict__["oracle_state"] = oracle_state  # PHASE C: Accès au contexte

        self.__dict__["_logger"] = logging.getLogger(self.__class__.__name__)
        self._logger.info(
            f"CyclicSelectionStrategy initialisée avec ordre: {self.agent_order}"
        )

    async def next(
        self, agents: List[Agent], history: List[ChatMessageContent]
    ) -> Agent:
        """
        Sélectionne le prochain agent selon l'ordre cyclique.

        Args:
            agents: Liste des agents disponibles
            history: Historique des messages

        Returns:
            Agent sélectionné pour le prochain tour
        """
        if not agents:
            raise ValueError("Aucun agent disponible pour la sélection")

        # Sélection cyclique de base
        selected_agent_name = self.agent_order[self.current_index]
        selected_agent = next(
            (agent for agent in agents if agent.name == selected_agent_name), None
        )

        if not selected_agent:
            self._logger.warning(
                f"Agent {selected_agent_name} non trouvé, sélection du premier agent disponible"
            )
            selected_agent = agents[0]

        # PHASE C: Injection du contexte récent dans l'agent sélectionné
        if self.oracle_state and hasattr(selected_agent, "_context_enhanced_prompt"):
            contextual_addition = self.oracle_state.get_contextual_prompt_addition(
                selected_agent.name
            )
            if contextual_addition:
                # Stockage temporaire du contexte pour l'agent
                selected_agent._current_context = contextual_addition
                self._logger.debug(
                    f"Contexte injecté pour {selected_agent.name}: {len(contextual_addition)} caractères"
                )

        # Avance l'index cyclique (contournement Pydantic)
        object.__setattr__(
            self, "current_index", (self.current_index + 1) % len(self.agent_order)
        )
        object.__setattr__(self, "turn_count", self.turn_count + 1)

        # Adaptations contextuelles (optionnelles pour Phase 1)
        if self.adaptive_selection:
            selected_agent = await self._apply_contextual_adaptations(
                selected_agent, agents, history
            )

        self._logger.info(
            f"Agent sélectionné: {selected_agent.name} (tour {self.turn_count})"
        )
        return selected_agent

    async def _apply_contextual_adaptations(
        self,
        default_agent: Agent,
        agents: List[Agent],
        history: List[ChatMessageContent],
    ) -> Agent:
        """
        Applique des adaptations contextuelles à la sélection (Phase 2).

        Adaptations possibles:
        - Si Sherlock fait une suggestion → priorité à Moriarty
        - Si Watson détecte contradiction → retour à Sherlock
        - Si Moriarty révèle information cruciale → priorité à Watson
        """
        # Pour Phase 1, on retourne l'agent par défaut
        # Cette méthode sera étoffée en Phase 2
        return default_agent

    def reset(self) -> None:
        """Remet à zéro la stratégie de sélection."""
        self.current_index = 0
        self.turn_count = 0
        self._logger.info("Stratégie de sélection cyclique remise à zéro")


class OracleTerminationStrategy(TerminationStrategy):
    """
    Stratégie de terminaison adaptée au workflow avec Oracle.

    Critères de terminaison:
    1. Solution correcte proposée ET validée par Oracle
    2. Toutes les cartes révélées (solution par élimination)
    3. Consensus des 3 agents sur une solution (futur)
    4. Timeout (max_turns atteint)
    """

    max_turns: int = Field(default=15)  # Plus de tours pour 3 agents
    max_cycles: int = Field(default=5)  # 5 cycles de 3 agents
    turn_count: int = Field(default=0, exclude=True)
    cycle_count: int = Field(default=0, exclude=True)
    is_solution_found: bool = Field(default=False, exclude=True)
    oracle_state: CluedoOracleState = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        max_turns: int = 15,
        max_cycles: int = 5,
        oracle_state: CluedoOracleState = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_turns = max_turns
        self.max_cycles = max_cycles
        self.oracle_state = oracle_state
        self.turn_count = 0
        self.cycle_count = 0
        self.is_solution_found = False

        self._logger = logging.getLogger(self.__class__.__name__)

    async def should_terminate(
        self, agent: Agent, history: List[ChatMessageContent]
    ) -> bool:
        """
        Détermine si le workflow doit se terminer selon les critères Oracle.

        Args:
            agent: Agent actuel
            history: Historique des messages

        Returns:
            True si le workflow doit se terminer
        """
        # Comptage des tours et cycles
        self.turn_count += 1
        if agent and agent.name == "Sherlock":  # Début d'un nouveau cycle
            self.cycle_count += 1
            self._logger.info(
                f"\n--- CYCLE {self.cycle_count}/{self.max_cycles} - TOUR {self.turn_count}/{self.max_turns} ---"
            )

        # Critère 1: Solution proposée et correcte
        if self._check_solution_found():
            self.is_solution_found = True
            self._logger.info("[OK] Solution correcte trouvée et validée. Terminaison.")
            return True

        # Critère 2: Solution par élimination complète
        if self._check_elimination_complete():
            self._logger.info(
                "[OK] Toutes les cartes révélées - solution par élimination possible. Terminaison."
            )
            return True

        # Critère 3: Timeout par nombre de tours
        if self.turn_count >= self.max_turns:
            self._logger.info(
                f"⏰ Nombre maximum de tours atteint ({self.max_turns}). Terminaison."
            )
            return True

        # Critère 4: Timeout par nombre de cycles
        if self.cycle_count >= self.max_cycles:
            self._logger.info(
                f"⏰ Nombre maximum de cycles atteint ({self.max_cycles}). Terminaison."
            )
            return True

        return False

    def _check_solution_found(self) -> bool:
        """Vérifie si une solution correcte a été proposée."""
        if not self.oracle_state or not self.oracle_state.is_solution_proposed:
            return False

        solution_proposee = self.oracle_state.final_solution
        solution_correcte = self.oracle_state.get_solution_secrete()

        if solution_proposee == solution_correcte:
            self._logger.info(f"Solution correcte: {solution_proposee}")
            return True

        self._logger.info(
            f"Solution incorrecte: {solution_proposee} ≠ {solution_correcte}"
        )
        return False

    def _check_elimination_complete(self) -> bool:
        """Vérifie si toutes les cartes non-secrètes ont été révélées."""
        if not self.oracle_state:
            return False

        return self.oracle_state.is_game_solvable_by_elimination()

    def get_termination_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des conditions de terminaison."""
        return {
            "turn_count": self.turn_count,
            "cycle_count": self.cycle_count,
            "max_turns": self.max_turns,
            "max_cycles": self.max_cycles,
            "is_solution_found": self.is_solution_found,
            "solution_proposed": self.oracle_state.is_solution_proposed
            if self.oracle_state
            else False,
            "elimination_possible": self._check_elimination_complete(),
        }

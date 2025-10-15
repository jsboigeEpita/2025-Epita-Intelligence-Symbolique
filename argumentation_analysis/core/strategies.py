# core/strategies.py
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité
from semantic_kernel.contents import ChatMessageContent

# from semantic_kernel.contents import AuthorRole

from typing import List, Dict, TYPE_CHECKING, Optional  # Ajout de Optional
import logging
from pydantic import PrivateAttr
from argumentation_analysis.orchestration.base import (
    SelectionStrategy,
    TerminationStrategy,
)

# L'import de 'argumentation_analysis.orchestration.base.SelectionStrategy' et
# 'argumentation_analysis.orchestration.base.TerminationStrategy' est omis
# car ces noms sont maintenant fournis par 'argumentation_analysis.utils.semantic_kernel_compatibility'.
# Les classes de stratégies ci-dessous hériteront donc des versions du module de compatibilité.

# Importer la classe d'état
from .shared_state import RhetoricalAnalysisState

# Type hinting
if TYPE_CHECKING:
    from argumentation_analysis.agents.core.abc.agent_bases import Agent

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
    _default_agent_name: str = PrivateAttr(default="ProjectManagerAgent")
    _analysis_state: "RhetoricalAnalysisState" = PrivateAttr()
    _instance_id: int  # Non géré par Pydantic, initialisé dans __init__
    _logger: logging.Logger  # Non géré par Pydantic, initialisé dans __init__

    def __init__(
        self,
        agents: List["Agent"],
        state: "RhetoricalAnalysisState",
        default_agent_name: str = "ProjectManagerAgent",
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


class BalancedParticipationStrategy(SelectionStrategy):
    """Stratégie de sélection qui équilibre la participation des agents tout en respectant les désignations explicites.

    Cette stratégie poursuit deux objectifs principaux :
    1.  **Respecter les désignations explicites** : Si l'état partagé (`RhetoricalAnalysisState`)
        désigne un agent spécifique pour le prochain tour, cet agent est prioritaire.
    2.  **Équilibrer la participation** : En l'absence de désignation, la stratégie calcule un
        score de priorité pour chaque agent. Ce score vise à combler l'écart entre le taux de
        participation actuel de l'agent et son taux cible, tout en tenant compte de la
        récence de sa dernière intervention.

    La stratégie maintient un "budget de déséquilibre" (`_imbalance_budget`) pour compenser
    les tours où la désignation explicite a empêché la sélection d'un agent qui en avait
    pourtant besoin pour atteindre sa cible.
    """

    _agents_map: Dict[str, "Agent"] = PrivateAttr(default_factory=dict)
    _default_agent_name: str = PrivateAttr(default="ProjectManagerAgent")
    _analysis_state: "RhetoricalAnalysisState" = (
        PrivateAttr()
    )  # Doit être passé à __init__
    _participation_counts: Dict[str, int] = PrivateAttr(default_factory=dict)
    _target_participation: Dict[str, float] = PrivateAttr(default_factory=dict)
    _imbalance_budget: Dict[str, float] = PrivateAttr(default_factory=dict)
    _total_turns: int = PrivateAttr(default=0)
    _last_selected: Dict[str, int] = PrivateAttr(default_factory=dict)
    _logger: logging.Logger = PrivateAttr()  # Sera initialisé dans __init__
    _instance_id: int  # Sera initialisé dans __init__

    def __init__(
        self,
        agents: List["Agent"],
        state: "RhetoricalAnalysisState",
        default_agent_name: str = "ProjectManagerAgent",
        target_participation: Optional[Dict[str, float]] = None,
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
                "Objet 'state' invalide pour BalancedParticipationStrategy."
            )

        self._agents_map = {agent.name: agent for agent in agents}
        self._analysis_state = state
        self._default_agent_name = default_agent_name
        self._total_turns = 0

        self._participation_counts = {agent.name: 0 for agent in agents}
        self._last_selected = {agent.name: 0 for agent in agents}

        if target_participation and isinstance(target_participation, dict):
            # Validation #1: S'assurer que tous les agents ciblés sont connus.
            known_agent_names = set(self._agents_map.keys())
            for name in target_participation:
                if name not in known_agent_names:
                    raise ValueError(
                        f"L'agent '{name}' défini dans target_participation est inconnu."
                    )

            # Validation #2: S'assurer que la somme des participations est (proche de) 1.0.
            total_participation = sum(target_participation.values())
            if not (0.99 < total_participation < 1.01):
                raise ValueError(
                    f"La somme des participations cibles doit être 1.0, mais est de {total_participation}."
                )

            self._target_participation = (
                target_participation.copy()
            )  # Copier pour éviter modif externe
        else:
            num_agents = len(agents)
            equal_share = 1.0 / num_agents if num_agents > 0 else 0
            self._target_participation = {agent.name: equal_share for agent in agents}
            if default_agent_name in self._target_participation and num_agents > 0:
                pm_share = min(0.4, (1.0 / num_agents) * 2.0) if num_agents > 0 else 0.0
                num_other_agents = num_agents - 1
                remaining_share_total = 1.0 - pm_share
                individual_remaining_share = (
                    remaining_share_total / num_other_agents
                    if num_other_agents > 0
                    else 0.0
                )

                for (
                    name_key
                ) in (
                    self._target_participation
                ):  # Utiliser name_key pour éviter conflit
                    if name_key == default_agent_name:
                        self._target_participation[name_key] = pm_share
                    else:
                        self._target_participation[
                            name_key
                        ] = individual_remaining_share

        self._imbalance_budget = {agent.name: 0.0 for agent in agents}

        self._instance_id = id(self)
        self._logger = selection_logger  # Utiliser le logger défini globalement

        if self._default_agent_name not in self._agents_map:
            if not self._agents_map:
                raise ValueError("Liste d'agents vide.")
            first_agent_name = list(self._agents_map.keys())[0]
            self._logger.warning(
                f"[{self._instance_id}] Agent défaut '{self._default_agent_name}' non trouvé. Fallback -> '{first_agent_name}'."
            )
            self._default_agent_name = first_agent_name

        self._logger.info(
            f"BalancedParticipationStrategy instance {self._instance_id} créée (agents: {list(self._agents_map.keys())}, default: '{self._default_agent_name}', state_id={id(self._analysis_state)})."
        )
        self._logger.info(f"Participations cibles: {self._target_participation}")

    async def next(
        self, agents: List["Agent"], history: List[ChatMessageContent]
    ) -> "Agent":
        self._logger.debug(f"[{self._instance_id}] Appel next()...")
        self._total_turns += 1

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
                    self._update_participation_counts(designated_agent.name)
                    self._adjust_imbalance_budget(designated_agent.name)
                    return designated_agent
                else:
                    self._logger.error(
                        f"[{self._instance_id}] Agent désigné '{designated_agent_name}' INTROUVABLE! Poursuite avec équilibrage."
                    )
        except Exception as e_state_access:
            self._logger.error(
                f"[{self._instance_id}] Erreur accès état pour désignation: {e_state_access}. Poursuite avec équilibrage."
            )

        priority_scores = self._calculate_priority_scores()

        default_agent_instance = self._agents_map.get(self._default_agent_name)
        selected_agent_name = (
            max(priority_scores, key=priority_scores.get)
            if priority_scores
            else self._default_agent_name
        )
        selected_agent = self._agents_map.get(
            selected_agent_name, default_agent_instance
        )

        if not selected_agent:
            if not self._agents_map:
                raise RuntimeError("Aucun agent disponible pour la sélection.")
            selected_agent = list(self._agents_map.values())[0]
            self._logger.error(
                f"[{self._instance_id}] ERREUR CRITIQUE: Agent sélectionné '{selected_agent_name}' ou défaut introuvable. Fallback au premier agent: {selected_agent.name}"
            )

        self._logger.info(
            f" -> Agent sélectionné (équilibrage): {selected_agent.name} (score: {priority_scores.get(selected_agent.name, 0.0):.2f})"
        )

        self._update_participation_counts(selected_agent.name)

        return selected_agent

    def _calculate_priority_scores(self) -> Dict[str, float]:
        scores = {}
        if not self._agents_map:
            return scores

        for agent_name_key in self._agents_map:  # Utiliser agent_name_key
            current_participation_rate = self._participation_counts.get(
                agent_name_key, 0
            ) / max(1, self._total_turns)
            target_rate = self._target_participation.get(
                agent_name_key, 0.0
            )  # Fournir une valeur par défaut
            participation_gap = target_rate - current_participation_rate

            turns_since_last_selection = self._total_turns - self._last_selected.get(
                agent_name_key, 0
            )
            recency_factor = min(1.0, turns_since_last_selection / 3.0)

            base_score = participation_gap * 10.0
            recency_boost = recency_factor * 0.5
            budget_boost = (
                self._imbalance_budget.get(agent_name_key, 0.0) * 0.2
            )  # Fournir une valeur par défaut

            scores[agent_name_key] = base_score + recency_boost + budget_boost

            self._logger.debug(
                f"Score {agent_name_key}: {scores[agent_name_key]:.2f} (écart={participation_gap:.2f}, "
                f"récence={recency_factor:.2f}, budget={self._imbalance_budget.get(agent_name_key, 0.0):.2f})"
            )

        return scores

    def _update_participation_counts(self, agent_name: str) -> None:
        if agent_name in self._participation_counts:
            self._participation_counts[agent_name] += 1
            self._last_selected[agent_name] = self._total_turns

            if self._total_turns > 0:
                participation_rates = {
                    name_key: count / self._total_turns
                    for name_key, count in self._participation_counts.items()
                }
                self._logger.debug(
                    f"Compteurs mis à jour: {self._participation_counts}"
                )
                self._logger.debug(f"Taux participation: {participation_rates}")

    def _adjust_imbalance_budget(self, agent_name: str) -> None:
        if self._total_turns == 0:
            return

        current_rates = {
            name_key: count / self._total_turns
            for name_key, count in self._participation_counts.items()
        }

        target_rate = self._target_participation.get(agent_name, 0.0)
        current_rate = current_rates.get(agent_name, 0.0)

        if current_rate > target_rate:
            excess = current_rate - target_rate
            total_other_target = sum(
                self._target_participation.get(name_key, 0.0)
                for name_key in self._agents_map
                if name_key != agent_name
            )

            if total_other_target > 0:
                for other_name_key in self._agents_map:  # Utiliser other_name_key
                    if other_name_key != agent_name:
                        other_target = self._target_participation.get(
                            other_name_key, 0.0
                        )
                        share = other_target / total_other_target
                        self._imbalance_budget[other_name_key] = (
                            self._imbalance_budget.get(other_name_key, 0.0)
                            + excess * share
                        )

        self._imbalance_budget[agent_name] = max(
            0.0, self._imbalance_budget.get(agent_name, 0.0) - 0.1
        )  # Assurer float

        self._logger.debug(f"Budgets ajustés: {self._imbalance_budget}")

    async def reset(self) -> None:
        self._logger.info(f"[{self._instance_id}] Reset BalancedParticipationStrategy.")

        self._participation_counts = {name_key: 0 for name_key in self._agents_map}
        self._total_turns = 0
        self._last_selected = {name_key: 0 for name_key in self._agents_map}
        self._imbalance_budget = {name_key: 0.0 for name_key in self._agents_map}

        try:
            consumed = self._analysis_state.consume_next_agent_designation()
            if consumed:
                self._logger.debug(f"   Ancienne désignation '{consumed}' effacée.")
        except Exception as e:
            self._logger.warning(f"   Erreur accès état pendant reset sélection: {e}")


module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.strategies chargé.")

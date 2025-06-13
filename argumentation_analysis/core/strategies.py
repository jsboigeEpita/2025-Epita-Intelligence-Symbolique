# core/strategies.py
# CORRECTIF COMPATIBILITÉ: Import direct depuis semantic_kernel
from semantic_kernel.contents import ChatMessageContent
# from semantic_kernel.agents import Agent # AJOUTÉ POUR CORRIGER NameError - Commenté car non disponible dans SK 0.9.6b1
# Note: Agent, TerminationStrategy, SelectionStrategy non disponibles dans SK 0.9.6b1
from typing import List, Dict, TYPE_CHECKING
import logging
from pydantic import PrivateAttr
from argumentation_analysis.orchestration.base import SelectionStrategy, TerminationStrategy

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

    async def should_terminate(self, agent, history: List[ChatMessageContent]) -> bool: # Agent type hint commenté
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
    _agents_map: Dict[str, any] = PrivateAttr() # Agent type hint remplacé par any
    _default_agent_name: str = PrivateAttr(default="ProjectManagerAgent") # On peut mettre le défaut ici
    _analysis_state: 'RhetoricalAnalysisState' = PrivateAttr()
    # Ces deux-là ne semblent pas faire partie du modèle Pydantic de base, on peut les laisser
    # S'ils ne sont pas définis par Pydantic, ils doivent être explicitement typés
    _instance_id: int
    _logger: logging.Logger

    def __init__(self, agents: List, state: 'RhetoricalAnalysisState', default_agent_name: str = "ProjectManagerAgent"): # Agent type hint commenté dans List
        """Initialise avec agents, état, et nom agent par défaut."""
        # L'appel super() doit rester ici
        super().__init__()
        if not isinstance(agents, list):
            raise TypeError("'agents' doit être une liste d'agents.")
        # Vérification assouplie pour les tests : on vérifie seulement que chaque agent a un attribut 'name'
        for a in agents:
            if not hasattr(a, 'name'):
                raise TypeError("Chaque agent doit avoir un attribut 'name'.")
        # S'assurer que la classe State est définie et que l'objet state a la bonne méthode
        if not isinstance(state, RhetoricalAnalysisState) or not hasattr(state, 'consume_next_agent_designation'):
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

    async def next(self, agents: List, history: List[ChatMessageContent]): # Agent type hint commenté dans List et en retour
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


class BalancedParticipationStrategy(SelectionStrategy):
    """Stratégie de sélection qui équilibre la participation des agents tout en respectant les désignations explicites."""
    # Attributs privés
    _agents_map: Dict[str, any] = PrivateAttr() # Agent type hint remplacé par any
    _default_agent_name: str = PrivateAttr(default="ProjectManagerAgent")
    _analysis_state: 'RhetoricalAnalysisState' = PrivateAttr()
    _participation_counts: Dict[str, int] = PrivateAttr()
    _target_participation: Dict[str, float] = PrivateAttr()
    _imbalance_budget: Dict[str, float] = PrivateAttr()
    _total_turns: int = PrivateAttr()
    _last_selected: Dict[str, int] = PrivateAttr()
    _logger: logging.Logger = PrivateAttr()
    
    # Ces attributs ne sont pas gérés par Pydantic
    _instance_id: int

    def __init__(self, agents: List, state: 'RhetoricalAnalysisState', # Agent type hint commenté dans List
                 default_agent_name: str = "ProjectManagerAgent",
                 target_participation: Dict[str, float] = None):
        """
        Initialise la stratégie avec les agents, l'état et les paramètres d'équilibrage.
        
        Args:
            agents: Liste des agents disponibles
            state: Instance de l'état partagé
            default_agent_name: Nom de l'agent par défaut
            target_participation: Dictionnaire des participations cibles par agent (%)
        """
        super().__init__()
        if not isinstance(agents, list):
            raise TypeError("'agents' doit être une liste d'agents.")
        # Vérification assouplie pour les tests : on vérifie seulement que chaque agent a un attribut 'name'
        for a in agents:
            if not hasattr(a, 'name'):
                raise TypeError("Chaque agent doit avoir un attribut 'name'.")
        if not isinstance(state, RhetoricalAnalysisState) or not hasattr(state, 'consume_next_agent_designation'):
            raise TypeError("Objet 'state' invalide pour BalancedParticipationStrategy.")

        # Initialisation des attributs privés
        self._agents_map = {agent.name: agent for agent in agents}
        self._analysis_state = state
        self._default_agent_name = default_agent_name
        self._total_turns = 0
        
        # Initialisation des compteurs et budgets
        self._participation_counts = {agent.name: 0 for agent in agents}
        self._last_selected = {agent.name: 0 for agent in agents}
        
        # Définition des participations cibles
        if target_participation and isinstance(target_participation, dict):
            self._target_participation = target_participation
        else:
            # Distribution équitable par défaut
            equal_share = 1.0 / len(agents) if agents else 0
            self._target_participation = {agent.name: equal_share for agent in agents}
            
            # Donner une part plus importante au PM par défaut
            if default_agent_name in self._target_participation:
                pm_share = min(0.4, 1.0 / len(agents) * 2)  # Max 40% ou double de la part équitable
                remaining_share = (1.0 - pm_share) / (len(agents) - 1) if len(agents) > 1 else 0
                
                for name in self._target_participation:
                    if name == default_agent_name:
                        self._target_participation[name] = pm_share
                    else:
                        self._target_participation[name] = remaining_share
        
        # Initialisation des budgets de déséquilibre
        self._imbalance_budget = {agent.name: 0.0 for agent in agents}
        
        # Configuration du logger
        self._instance_id = id(self)
        self._logger = selection_logger
        
        # Vérification de l'agent par défaut
        if self._default_agent_name not in self._agents_map:
            if not self._agents_map:
                raise ValueError("Liste d'agents vide.")
            first_agent_name = list(self._agents_map.keys())[0]
            self._logger.warning(f"[{self._instance_id}] Agent défaut '{self._default_agent_name}' non trouvé. Fallback -> '{first_agent_name}'.")
            self._default_agent_name = first_agent_name
            
        self._logger.info(f"BalancedParticipationStrategy instance {self._instance_id} créée (agents: {list(self._agents_map.keys())}, default: '{self._default_agent_name}', state_id={id(self._analysis_state)}).")
        self._logger.info(f"Participations cibles: {self._target_participation}")

    async def next(self, agents: List, history: List[ChatMessageContent]): # Agent type hint commenté dans List et en retour
        """
        Sélectionne le prochain agent selon la stratégie d'équilibrage.
        
        Args:
            agents: Liste des agents disponibles
            history: Historique des messages
            
        Returns:
            Agent: L'agent sélectionné pour le prochain tour
        """
        self._logger.debug(f"[{self._instance_id}] Appel next()...")
        self._total_turns += 1
        
        # Récupérer l'agent par défaut
        default_agent_instance = self._agents_map.get(self._default_agent_name)
        if not default_agent_instance:
            self._logger.error(f"[{self._instance_id}] ERREUR: Agent défaut '{self._default_agent_name}' introuvable! Retourne premier agent.")
            available_agents = list(self._agents_map.values())
            if not available_agents:
                raise RuntimeError("Aucun agent disponible.")
            return available_agents[0]
        
        # 1. Vérifier s'il y a une désignation explicite via l'état
        try:
            designated_agent_name = self._analysis_state.consume_next_agent_designation()
        except Exception as e_state_access:
            self._logger.error(f"[{self._instance_id}] Erreur accès état pour désignation: {e_state_access}. Retour agent défaut.")
            return default_agent_instance
        
        # 2. Si oui, sélectionner cet agent et ajuster le budget de déséquilibre
        if designated_agent_name:
            self._logger.info(f"[{self._instance_id}] Désignation explicite: '{designated_agent_name}'.")
            designated_agent = self._agents_map.get(designated_agent_name)
            if designated_agent:
                self._logger.info(f" -> Sélection agent désigné: {designated_agent.name}")
                self._update_participation_counts(designated_agent.name)
                self._adjust_imbalance_budget(designated_agent.name)
                return designated_agent
            else:
                self._logger.error(f"[{self._instance_id}] Agent désigné '{designated_agent_name}' INTROUVABLE! Retour agent défaut.")
                self._update_participation_counts(default_agent_instance.name)
                return default_agent_instance
        
        # 3. Sinon, calculer les scores de priorité pour chaque agent
        priority_scores = self._calculate_priority_scores()
        
        # 4. Sélectionner l'agent avec le score le plus élevé
        selected_agent_name = max(priority_scores.items(), key=lambda x: x[1])[0]
        selected_agent = self._agents_map.get(selected_agent_name, default_agent_instance)
        
        self._logger.info(f" -> Agent sélectionné (équilibrage): {selected_agent.name} (score: {priority_scores[selected_agent.name]:.2f})")
        
        # 5. Mettre à jour les compteurs et budgets
        self._update_participation_counts(selected_agent.name)
        
        return selected_agent
    
    def _calculate_priority_scores(self) -> Dict[str, float]:
        """
        Calcule les scores de priorité pour chaque agent.
        
        Returns:
            Dict[str, float]: Dictionnaire des scores de priorité par agent
        """
        scores = {}
        
        for agent_name in self._agents_map:
            # Calculer le taux de participation actuel
            current_participation_rate = self._participation_counts.get(agent_name, 0) / max(1, self._total_turns)
            
            # Calculer l'écart par rapport à la cible
            target_rate = self._target_participation.get(agent_name, 0)
            participation_gap = target_rate - current_participation_rate
            
            # Facteur de temps depuis la dernière sélection
            turns_since_last_selection = self._total_turns - self._last_selected.get(agent_name, 0)
            recency_factor = min(1.0, turns_since_last_selection / 3.0)  # Plafonné à 1.0
            
            # Calculer le score final
            # Plus l'écart est positif (sous-représenté), plus le score est élevé
            # Plus le temps depuis la dernière sélection est grand, plus le score est élevé
            base_score = participation_gap * 10.0  # Facteur d'échelle pour l'écart
            recency_boost = recency_factor * 0.5   # Bonus pour le temps écoulé
            budget_boost = self._imbalance_budget.get(agent_name, 0) * 0.2  # Bonus pour le budget accumulé
            
            scores[agent_name] = base_score + recency_boost + budget_boost
            
            # Log détaillé pour le débogage
            self._logger.debug(f"Score {agent_name}: {scores[agent_name]:.2f} (écart={participation_gap:.2f}, "
                              f"récence={recency_factor:.2f}, budget={self._imbalance_budget.get(agent_name, 0):.2f})")
        
        return scores
    
    def _update_participation_counts(self, agent_name: str) -> None:
        """
        Met à jour les compteurs après sélection d'un agent.
        
        Args:
            agent_name: Nom de l'agent sélectionné
        """
        if agent_name in self._participation_counts:
            self._participation_counts[agent_name] += 1
            self._last_selected[agent_name] = self._total_turns
            
            # Log des compteurs mis à jour
            participation_rates = {name: count / max(1, self._total_turns)
                                 for name, count in self._participation_counts.items()}
            self._logger.debug(f"Compteurs mis à jour: {self._participation_counts}")
            self._logger.debug(f"Taux participation: {participation_rates}")
    
    def _adjust_imbalance_budget(self, agent_name: str) -> None:
        """
        Ajuste le budget de déséquilibre après une désignation explicite.
        
        Args:
            agent_name: Nom de l'agent désigné explicitement
        """
        # Calculer le taux de participation actuel pour tous les agents
        current_rates = {name: count / max(1, self._total_turns)
                        for name, count in self._participation_counts.items()}
        
        # Pour l'agent sélectionné, calculer l'écart par rapport à sa cible
        target_rate = self._target_participation.get(agent_name, 0)
        current_rate = current_rates.get(agent_name, 0)
        
        # Si l'agent est déjà surreprésenté, augmenter le budget des autres
        if current_rate > target_rate:
            excess = current_rate - target_rate
            # Distribuer l'excès aux autres agents proportionnellement à leur cible
            total_other_target = sum(self._target_participation.get(name, 0)
                                   for name in self._agents_map if name != agent_name)
            
            if total_other_target > 0:
                for other_name in self._agents_map:
                    if other_name != agent_name:
                        other_target = self._target_participation.get(other_name, 0)
                        share = other_target / total_other_target if total_other_target > 0 else 0
                        self._imbalance_budget[other_name] += excess * share
        
        # Réduire le budget de l'agent sélectionné
        self._imbalance_budget[agent_name] = max(0, self._imbalance_budget.get(agent_name, 0) - 0.1)
        
        self._logger.debug(f"Budgets ajustés: {self._imbalance_budget}")

    async def reset(self) -> None:
        """Réinitialise les compteurs et budgets."""
        self._logger.info(f"[{self._instance_id}] Reset BalancedParticipationStrategy.")
        
        # Réinitialiser les compteurs
        self._participation_counts = {name: 0 for name in self._agents_map}
        self._total_turns = 0
        self._last_selected = {name: 0 for name in self._agents_map}
        self._imbalance_budget = {name: 0.0 for name in self._agents_map}
        
        # Effacer toute désignation en attente
        try:
            consumed = self._analysis_state.consume_next_agent_designation()
            if consumed:
                self._logger.debug(f"   Ancienne désignation '{consumed}' effacée.")
        except Exception as e:
            self._logger.warning(f"   Erreur accès état pendant reset sélection: {e}")


# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.strategies chargé.")

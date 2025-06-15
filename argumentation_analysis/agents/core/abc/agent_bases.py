"""
Module définissant les classes de base abstraites pour les agents.

Ce module fournit `BaseAgent` comme fondation pour tous les agents,
et `BaseLogicAgent` comme spécialisation pour les agents basés sur
une logique formelle. Ces classes utilisent le pattern Abstract Base Class (ABC)
pour définir une interface commune que les agents concrets doivent implémenter.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING, Coroutine
import logging

from semantic_kernel import Kernel
from semantic_kernel.agents import Agent
from semantic_kernel.contents import ChatHistory
from semantic_kernel.agents.channels.chat_history_channel import ChatHistoryChannel
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatHistoryAgentThread

# Résoudre la dépendance circulaire de Pydantic
ChatHistoryChannel.model_rebuild()

# Import paresseux pour éviter le cycle d'import - uniquement pour le typage
if TYPE_CHECKING:
    from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class BaseAgent(Agent, ABC):
    """
    Classe de base abstraite pour tous les agents du système.

    Cette classe définit l'interface commune que tous les agents doivent respecter,
    y compris la gestion d'un kernel Semantic Kernel, un nom d'agent, un logger,
    et un prompt système optionnel. Elle impose l'implémentation de méthodes
    pour décrire les capacités de l'agent et configurer ses composants.

    Attributes:
        _kernel (Kernel): Le kernel Semantic Kernel associé à l'agent.
        _agent_name (str): Le nom unique de l'agent.
        _logger (logging.Logger): Le logger spécifique à cette instance d'agent.
        _llm_service_id (Optional[str]): L'ID du service LLM utilisé, configuré via `setup_agent_components`.
        _system_prompt (Optional[str]): Le prompt système global pour l'agent.
    """
    _logger: logging.Logger
    _llm_service_id: Optional[str]

    def __init__(self, kernel: "Kernel", agent_name: str, system_prompt: Optional[str] = None, description: Optional[str] = None):
        """
        Initialise une instance de BaseAgent.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            system_prompt: Le prompt système optionnel pour l'agent.
            description: La description optionnelle de l'agent.
        """
        effective_description = description if description else (system_prompt if system_prompt else f"Agent {agent_name}")
        
        # Appel du constructeur de la classe parente sk.Agent
        super().__init__(
            id=agent_name,
            name=agent_name,
            instructions=system_prompt,
            description=effective_description,
            kernel=kernel
        )

        # Le kernel est déjà stocké dans self.kernel par la classe de base Agent.
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}.{self.name}")
        self._llm_service_id = None  # Sera défini par setup_agent_components

    @property
    def logger(self) -> logging.Logger:
        """Retourne le logger de l'agent."""
        return self._logger

    @property
    def system_prompt(self) -> Optional[str]:
        """Retourne le prompt système de l'agent (alias pour self.instructions)."""
        return self.instructions

    @abstractmethod
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Méthode abstraite pour décrire les capacités spécifiques de l'agent.

        Les classes dérivées doivent implémenter cette méthode pour retourner un
        dictionnaire décrivant leurs fonctionnalités.

        :return: Un dictionnaire des capacités.
        :rtype: Dict[str, Any]
        """
        pass

    @abstractmethod
    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Méthode abstraite pour configurer les composants spécifiques de l'agent.

        Les classes dérivées doivent implémenter cette méthode pour initialiser
        leurs dépendances, enregistrer les fonctions sémantiques et natives
        dans le kernel Semantic Kernel, et stocker l'ID du service LLM.

        :param llm_service_id: L'ID du service LLM à utiliser.
        :type llm_service_id: str
        """
        self._llm_service_id = llm_service_id
        pass

    def get_agent_info(self) -> Dict[str, Any]:
        """
        Retourne un dictionnaire d'informations sur l'agent.

        Inclut le nom, la classe, le prompt système, l'ID du service LLM
        et les capacités de l'agent.

        :return: Un dictionnaire contenant les informations de l'agent.
        :rtype: Dict[str, Any]
        """
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "system_prompt": self.system_prompt,
            "llm_service_id": self._llm_service_id,
            "capabilities": self.get_agent_capabilities()
        }

    def get_channel_keys(self) -> List[str]:
        """
        Retourne les clés uniques pour identifier le canal de communication de l'agent.
        Cette méthode est requise par AgentGroupChat.
        """
        # Utiliser self.id car il est déjà garanti comme étant unique
        # (initialisé avec agent_name).
        return [self.id]

    async def create_channel(self) -> ChatHistoryChannel:
        """
        Crée un canal de communication pour l'agent.

        Cette méthode est requise par AgentGroupChat pour permettre à l'agent
        de participer à une conversation. Nous utilisons ChatHistoryChannel,
        qui est une implémentation générique basée sur ChatHistory.
        """
        thread = ChatHistoryAgentThread()
        return ChatHistoryChannel(thread=thread)

    @abstractmethod
    async def get_response(self, *args, **kwargs):
        """Méthode abstraite pour obtenir une réponse de l'agent."""
        pass

    @abstractmethod
    async def invoke_single(self, *args, **kwargs):
        """
        Méthode abstraite pour l'invocation de l'agent qui retourne une réponse unique.
        Les agents concrets DOIVENT implémenter cette logique.
        """
        pass

    async def invoke(self, *args, **kwargs):
        """
        Méthode d'invocation principale compatible avec le streaming attendu par le framework SK.
        Elle transforme la réponse unique de `invoke_single` en un flux.
        """
        result = await self.invoke_single(*args, **kwargs)
        yield result

    async def invoke_stream(self, *args, **kwargs):
        """
        Implémentation de l'interface de streaming de SK.
        Cette méthode délègue à `invoke`, qui retourne maintenant un générateur asynchrone.
        """
        async for Elt in self.invoke(*args, **kwargs):
            yield Elt
  
      # Optionnel, à considérer pour une interface d'appel atomique standardisée
      # def invoke_atomic(self, method_name: str, **kwargs) -> Any:
    #     if hasattr(self, method_name) and callable(getattr(self, method_name)):
    #         method_to_call = getattr(self, method_name)
    #         # Potentiellement vérifier si la méthode est "publique" ou listée dans capabilities
    #         return method_to_call(**kwargs)


class BaseLogicAgent(BaseAgent, ABC):
    """
    Classe de base abstraite pour les agents utilisant une logique formelle.

    Hérite de `BaseAgent` et ajoute des abstractions spécifiques aux agents
    logiques, telles que la gestion d'un type de logique, l'utilisation
    d'un `TweetyBridge` pour interagir avec des solveurs logiques, et des
    méthodes pour la manipulation d'ensembles de croyances et l'exécution
    de requêtes.

    Attributes:
        _tweety_bridge (TweetyBridge): Instance de `TweetyBridge` pour la logique spécifique.
        _logic_type_name (str): Nom du type de logique (ex: "PL", "FOL", "ML").
        _syntax_bnf (Optional[str]): Description BNF de la syntaxe logique (optionnel).
    """
    _tweety_bridge: "TweetyBridge"
    _logic_type_name: str
    _syntax_bnf: Optional[str]
    # _parser: Any  # Ces éléments seront gérés par TweetyBridge
    # _solver: Any  # Ces éléments seront gérés par TweetyBridge

    def __init__(self, kernel: "Kernel", agent_name: str, logic_type_name: str, system_prompt: Optional[str] = None):
        """
        Initialise une instance de BaseLogicAgent.

        :param kernel: Le kernel Semantic Kernel à utiliser.
        :type kernel: Kernel
        :param agent_name: Le nom de l'agent.
        :type agent_name: str
        :param logic_type_name: Le nom du type de logique (ex: "PL", "FOL").
        :type logic_type_name: str
        :param system_prompt: Le prompt système optionnel pour l'agent.
        :type system_prompt: Optional[str]
        """
        super().__init__(kernel, agent_name, system_prompt)
        self._logic_type_name = logic_type_name
        # L'instance de TweetyBridge devrait être passée ou créée ici.
        # Pour l'instant, on suppose qu'elle sera initialisée dans setup_agent_components
        # ou passée d'une manière ou d'une autre.
        # self._tweety_bridge = TweetyBridge() # Exemple
        self._syntax_bnf = None # Pourrait être chargé par le bridge ou la sous-classe

    @property
    def logic_type(self) -> str:
        """
        Retourne le nom du type de logique géré par l'agent.

        :return: Le nom du type de logique (ex: "PL", "FOL").
        :rtype: str
        """
        return self._logic_type_name

    @property
    def tweety_bridge(self) -> "TweetyBridge":
        """
        Retourne l'instance de `TweetyBridge` associée à cet agent.

        L'instance de `TweetyBridge` est typiquement initialisée lors de l'appel
        à `setup_agent_components` par la classe concrète.

        :return: L'instance de `TweetyBridge`.
        :rtype: TweetyBridge
        :raises RuntimeError: Si `TweetyBridge` n'a pas été initialisé.
        """
        if not hasattr(self, '_tweety_bridge') or self._tweety_bridge is None:
            # Cela suppose que setup_agent_components a été appelé et a initialisé le bridge.
            # Une meilleure approche pourrait être d'injecter TweetyBridge au constructeur
            # ou d'avoir une méthode dédiée pour son initialisation si elle est complexe.
            raise RuntimeError("TweetyBridge not initialized. Call setup_agent_components or ensure it's injected.")
        return self._tweety_bridge

    @abstractmethod
    def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional["BeliefSet"], str]:
        """
        Méthode abstraite pour convertir un texte en langage naturel en un ensemble de croyances.

        :param text: Le texte à convertir.
        :type text: str
        :param context: Contexte additionnel optionnel.
        :type context: Optional[Dict[str, Any]]
        :return: Un tuple contenant l'objet `BeliefSet` et un message de statut.
        :rtype: Tuple[Optional['BeliefSet'], str]
        """
        pass

    @abstractmethod
    def generate_queries(self, text: str, belief_set: "BeliefSet", context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Méthode abstraite pour générer des requêtes logiques pertinentes.

        :param text: Le texte source.
        :type text: str
        :param belief_set: L'ensemble de croyances associé.
        :type belief_set: BeliefSet
        :param context: Contexte additionnel optionnel.
        :type context: Optional[Dict[str, Any]]
        :return: Une liste de requêtes sous forme de chaînes de caractères.
        :rtype: List[str]
        """
        pass

    @abstractmethod
    def execute_query(self, belief_set: "BeliefSet", query: str) -> Tuple[Optional[bool], str]:
        """
        Méthode abstraite pour exécuter une requête logique sur un ensemble de croyances.

        Devrait utiliser `self.tweety_bridge` et son solveur spécifique à la logique.

        :param belief_set: L'ensemble de croyances sur lequel exécuter la requête.
        :type belief_set: BeliefSet
        :param query: La requête à exécuter.
        :type query: str
        :return: Un tuple contenant le résultat booléen (True, False, ou None si indéterminé)
                 et un message de statut/résultat brut.
        :rtype: Tuple[Optional[bool], str]
        """
        pass

    @abstractmethod
    def interpret_results(self, text: str, belief_set: "BeliefSet", queries: List[str], results: List[Tuple[Optional[bool], str]], context: Optional[Dict[str, Any]] = None) -> str:
        """
        Méthode abstraite pour interpréter les résultats des requêtes logiques en langage naturel.

        :param text: Le texte source original.
        :type text: str
        :param belief_set: L'ensemble de croyances utilisé.
        :type belief_set: BeliefSet
        :param queries: La liste des requêtes qui ont été exécutées.
        :type queries: List[str]
        :param results: La liste des résultats (booléen/None, message) pour chaque requête.
        :type results: List[Tuple[Optional[bool], str]]
        :param context: Contexte additionnel optionnel.
        :type context: Optional[Dict[str, Any]]
        :return: Une interprétation en langage naturel des résultats.
        :rtype: str
        """
        pass

    # @abstractmethod # Remplacé par l'utilisation directe du bridge
    # def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> 'BeliefSet':
    #     pass

    @abstractmethod
    def validate_formula(self, formula: str) -> bool:
        """
        Méthode abstraite pour valider la syntaxe d'une formule logique.

        Devrait utiliser `self.tweety_bridge` et son parser spécifique à la logique.

        :param formula: La formule à valider.
        :type formula: str
        :return: True si la formule est valide, False sinon.
        :rtype: bool
        """
        pass

    @abstractmethod
    def is_consistent(self, belief_set: "BeliefSet") -> Tuple[bool, str]:
        """
        Vérifie si un ensemble de croyances est cohérent.

        Utilise le TweetyBridge pour appeler la méthode de vérification de
        cohérence appropriée pour la logique de l'agent.

        :param belief_set: L'ensemble de croyances à vérifier.
        :type belief_set: BeliefSet
        :return: Un tuple contenant un booléen (True si cohérent, False sinon)
                 et un message de détails du solveur.
        :rtype: Tuple[bool, str]
        """
        pass

    def process_task(self, task_id: str, task_description: str, state_manager: Any) -> Dict[str, Any]:
        """
        Traite une tâche assignée à l'agent logique.
        Migré depuis AbstractLogicAgent pour unifier l'architecture.
        """
        self.logger.info(f"Traitement de la tâche {task_id}: {task_description}")
        state = state_manager.get_current_state_snapshot(summarize=False)
        if "Traduire" in task_description and "Belief Set" in task_description:
            return self._handle_translation_task(task_id, task_description, state, state_manager)
        elif "Exécuter" in task_description and "Requêtes" in task_description:
            return self._handle_query_task(task_id, task_description, state, state_manager)
        else:
            error_msg = f"Type de tâche non reconnu: {task_description}"
            self.logger.error(error_msg)
            state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=error_msg, source_ids=[])
            return {"status": "error", "message": error_msg}

    def _handle_translation_task(self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any) -> Dict[str, Any]:
        """
        Gère une tâche spécifique de conversion de texte en un ensemble de croyances logiques.
        """
        raw_text = self._extract_source_text(task_description, state)
        if not raw_text:
            error_msg = "Impossible de trouver le texte source pour la traduction"
            self.logger.error(error_msg)
            state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=error_msg, source_ids=[])
            return {"status": "error", "message": error_msg}
        
        belief_set, status_msg = self.text_to_belief_set(raw_text)
        if not belief_set:
            error_msg = f"Échec de la conversion en ensemble de croyances: {status_msg}"
            self.logger.error(error_msg)
            state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=error_msg, source_ids=[])
            return {"status": "error", "message": error_msg}

        bs_id = state_manager.add_belief_set(logic_type=belief_set.logic_type, content=belief_set.content)
        answer_text = f"Ensemble de croyances créé avec succès (ID: {bs_id}).\n\n{status_msg}"
        state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=answer_text, source_ids=[bs_id])
        return {"status": "success", "message": answer_text, "belief_set_id": bs_id}

    def _handle_query_task(self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any) -> Dict[str, Any]:
        """
        Gère une tâche d'exécution de requêtes logiques sur un ensemble de croyances existant.
        """
        belief_set_id = self._extract_belief_set_id(task_description)
        if not belief_set_id:
            error_msg = "Impossible de trouver l'ID de l'ensemble de croyances dans la description de la tâche"
            self.logger.error(error_msg)
            state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=error_msg, source_ids=[])
            return {"status": "error", "message": error_msg}

        belief_sets = state.get("belief_sets", {})
        if belief_set_id not in belief_sets:
            error_msg = f"Ensemble de croyances non trouvé: {belief_set_id}"
            self.logger.error(error_msg)
            state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=error_msg, source_ids=[])
            return {"status": "error", "message": error_msg}

        belief_set_data = belief_sets[belief_set_id]
        belief_set = self._create_belief_set_from_data(belief_set_data)
        raw_text = self._extract_source_text(task_description, state)
        queries = self.generate_queries(raw_text, belief_set)
        if not queries:
            error_msg = "Aucune requête n'a pu être générée"
            self.logger.error(error_msg)
            state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=error_msg, source_ids=[belief_set_id])
            return {"status": "error", "message": error_msg}

        formatted_results = []
        log_ids = []
        raw_results = []
        for query in queries:
            result, result_str = self.execute_query(belief_set, query)
            raw_results.append((result, result_str))
            formatted_results.append(result_str)
            log_id = state_manager.log_query_result(belief_set_id=belief_set_id, query=query, raw_result=result_str)
            log_ids.append(log_id)

        interpretation = self.interpret_results(raw_text, belief_set, queries, raw_results)
        state_manager.add_answer(task_id=task_id, author_agent=self.name, answer_text=interpretation, source_ids=[belief_set_id] + log_ids)
        return {"status": "success", "message": interpretation, "queries": queries, "results": formatted_results, "log_ids": log_ids}

    def _extract_source_text(self, task_description: str, state: Dict[str, Any]) -> str:
        """
        Extrait le texte source pertinent pour une tâche.
        """
        raw_text = state.get("raw_text", "")
        if not raw_text and "texte:" in task_description.lower():
            parts = task_description.split("texte:", 1)
            if len(parts) > 1:
                raw_text = parts[1].strip()
        return raw_text

    def _extract_belief_set_id(self, task_description: str) -> Optional[str]:
        """
        Extrait un ID d'ensemble de croyances à partir de la description d'une tâche.
        """
        if "belief_set_id:" in task_description.lower():
            parts = task_description.split("belief_set_id:", 1)
            if len(parts) > 1:
                bs_id_part = parts[1].strip()
                bs_id = bs_id_part.split()[0].strip()
                return bs_id
        return None

    @abstractmethod
    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> "BeliefSet":
        """
        Crée une instance de `BeliefSet` à partir d'un dictionnaire de données.
        """
        pass
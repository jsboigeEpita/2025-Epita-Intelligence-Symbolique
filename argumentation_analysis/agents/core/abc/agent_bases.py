"""
Module définissant les classes de base abstraites pour les agents.

Ce module fournit `BaseAgent` comme fondation pour tous les agents,
et `BaseLogicAgent` comme spécialisation pour les agents basés sur
une logique formelle. Ces classes utilisent le pattern Abstract Base Class (ABC)
pour définir une interface commune que les agents concrets doivent implémenter.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
import logging

from semantic_kernel.agents import Agent
from semantic_kernel import Kernel # Exemple d'importation

from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
# from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class BaseAgent(ABC):
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
    _kernel: 'Kernel'  # Utilisation de guillemets pour forward reference si Kernel n'est pas encore importé
    _agent_name: str
    _logger: logging.Logger
    _llm_service_id: Optional[str]
    # _system_prompt: Optional[str] # Déjà dans Agent as instructions

    def __init__(self, kernel: 'Kernel', agent_name: str, system_prompt: Optional[str] = None, description: Optional[str] = None):
        """
        Initialise une instance de BaseAgent.

        :param kernel: Le kernel Semantic Kernel à utiliser.
        :type kernel: Kernel
        :param agent_name: Le nom de l'agent.
        :type agent_name: str
        :param system_prompt: Le prompt système optionnel pour l'agent.
        :type system_prompt: Optional[str]
        :param description: La description optionnelle de l'agent.
        :type description: Optional[str]
        """
        self._agent_name = agent_name
        self.description = description if description else (system_prompt if system_prompt else f"Agent {agent_name}")
        self.instructions = system_prompt if system_prompt else ""
        self._kernel = kernel
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}.{agent_name}")
        self._llm_service_id = None # Initialisé dans setup_agent_components
        self._system_prompt = system_prompt

    @property
    def name(self) -> str:
        """
        Retourne le nom de l'agent.

        :return: Le nom de l'agent.
        :rtype: str
        """
        return self._agent_name

    @property
    def sk_kernel(self) -> 'Kernel':
        """
        Retourne le kernel Semantic Kernel associé à l'agent.

        :return: Le kernel Semantic Kernel.
        :rtype: Kernel
        """
        return self._kernel

    @property
    def logger(self) -> logging.Logger:
        """
        Retourne le logger de l'agent.

        :return: L'instance du logger.
        :rtype: logging.Logger
        """
        return self._logger

    @property
    def system_prompt(self) -> Optional[str]:
        """
        Retourne le prompt système de l'agent.

        :return: Le prompt système, ou None s'il n'est pas défini.
        :rtype: Optional[str]
        """
        return self._system_prompt

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
    
    async def get_response(self, *args, **kwargs):
        """Méthode abstraite de Agent."""
        raise NotImplementedError("get_response n'est pas implémenté dans BaseAgent.")

    async def invoke(self, *args, **kwargs):
        """Méthode abstraite de Agent."""
        raise NotImplementedError("invoke n'est pas implémenté dans BaseAgent.")

    async def invoke_stream(self, *args, **kwargs):
        """Méode abstraite de Agent."""
        raise NotImplementedError("invoke_stream n'est pas implémenté dans BaseAgent.")
 
     # Optionnel, à considérer pour une interface d'appel atomique standardisée
     # def invoke_atomic(self, method_name: str, **kwargs) -> Any:
    #     if hasattr(self, method_name) and callable(getattr(self, method_name)):
    #         method_to_call = getattr(self, method_name)
    #         # Potentiellement vérifier si la méthode est "publique" ou listée dans capabilities
    #         return method_to_call(**kwargs)
    #     else:
    #         raise AttributeError(f"{self.name} has no capability named {method_name}")


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
    _tweety_bridge: 'TweetyBridge'
    _logic_type_name: str
    _syntax_bnf: Optional[str]
    # _parser: Any  # Ces éléments seront gérés par TweetyBridge
    # _solver: Any  # Ces éléments seront gérés par TweetyBridge

    def __init__(self, kernel: 'Kernel', agent_name: str, logic_type_name: str, system_prompt: Optional[str] = None):
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
    def tweety_bridge(self) -> 'TweetyBridge':
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
    def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional['BeliefSet'], str]:
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
    def generate_queries(self, text: str, belief_set: 'BeliefSet', context: Optional[Dict[str, Any]] = None) -> List[str]:
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
    def execute_query(self, belief_set: 'BeliefSet', query: str) -> Tuple[Optional[bool], str]:
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
    def interpret_results(self, text: str, belief_set: 'BeliefSet', queries: List[str], results: List[Tuple[Optional[bool], str]], context: Optional[Dict[str, Any]] = None) -> str:
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
    def is_consistent(self, belief_set: 'BeliefSet') -> Tuple[bool, str]:
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
 
    # La méthode setup_agent_components de BaseAgent doit être implémentée
    # par les sous-classes concrètes (PLAgent, FOLAgent) pour enregistrer
    # leurs fonctions sémantiques spécifiques et initialiser/configurer TweetyBridge.
    # Exemple dans une sous-classe :
    # def setup_agent_components(self, llm_service_id: str) -> None:
    #     super().setup_agent_components(llm_service_id)
    #     self._tweety_bridge = TweetyBridge(self.logic_type) # Initialisation du bridge
    #     # Enregistrement des fonctions sémantiques spécifiques à la logique X
    #     # self.sk_kernel.add_functions(...)
    #     # Enregistrement du tweety_bridge comme plugin si ses méthodes doivent être appelées par SK
    #     # self.sk_kernel.add_plugin(self._tweety_bridge, plugin_name=f"{self.name}_TweetyBridge")
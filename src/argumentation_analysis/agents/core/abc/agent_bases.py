from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
import logging

# Supposons que Kernel et BeliefSet sont importables ou seront définis/importés ailleurs.
# Pour l'instant, nous pouvons utiliser des alias ou des types génériques si nécessaire.
# from semantic_kernel import Kernel # Exemple d'importation
class Kernel: pass # Placeholder
class BeliefSet: pass # Placeholder

# Supposons que TweetyBridge est importable
# from ..logic.tweety_bridge import TweetyBridge # Exemple d'importation
class TweetyBridge: pass # Placeholder


class BaseAgent(ABC):
    """
    Classe abstraite fondamentale fournissant une fondation commune à tous les agents.
    Elle rend explicite la configuration du kernel SK associée à chaque agent.
    """
    _kernel: 'Kernel'  # Utilisation de guillemets pour forward reference si Kernel n'est pas encore importé
    _agent_name: str
    _logger: logging.Logger
    _llm_service_id: Optional[str]
    _system_prompt: Optional[str]

    def __init__(self, kernel: 'Kernel', agent_name: str, system_prompt: Optional[str] = None):
        self._kernel = kernel
        self._agent_name = agent_name
        self._system_prompt = system_prompt
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}.{agent_name}")
        self._llm_service_id = None # Initialisé dans setup_agent_components

    @property
    def name(self) -> str:
        return self._agent_name

    @property
    def sk_kernel(self) -> 'Kernel':
        return self._kernel

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def system_prompt(self) -> Optional[str]:
        return self._system_prompt

    @abstractmethod
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Décrit ce que l'agent peut faire."""
        pass

    @abstractmethod
    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants spécifiques de l'agent dans le kernel SK.
        Doit être implémentée par chaque agent concret pour :
        1. Stocker llm_service_id.
        2. Enregistrer ses plugins natifs spécifiques dans le sk_kernel.
        3. Enregistrer ses fonctions sémantiques dans le sk_kernel.
        4. Définir/confirmer le prompt système si applicable.
        """
        self._llm_service_id = llm_service_id
        pass

    def get_agent_info(self) -> Dict[str, Any]:
        """Retourne des informations sur l'agent."""
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "system_prompt": self.system_prompt,
            "llm_service_id": self._llm_service_id,
            "capabilities": self.get_agent_capabilities()
        }

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
    Classe abstraite pour les agents basés sur une logique formelle,
    factorisant les comportements communs.
    """
    _tweety_bridge: 'TweetyBridge'
    _logic_type_name: str
    _syntax_bnf: Optional[str]
    # _parser: Any  # Ces éléments seront gérés par TweetyBridge
    # _solver: Any  # Ces éléments seront gérés par TweetyBridge

    def __init__(self, kernel: 'Kernel', agent_name: str, logic_type_name: str, system_prompt: Optional[str] = None):
        super().__init__(kernel, agent_name, system_prompt)
        self._logic_type_name = logic_type_name
        # L'instance de TweetyBridge devrait être passée ou créée ici.
        # Pour l'instant, on suppose qu'elle sera initialisée dans setup_agent_components
        # ou passée d'une manière ou d'une autre.
        # self._tweety_bridge = TweetyBridge() # Exemple
        self._syntax_bnf = None # Pourrait être chargé par le bridge ou la sous-classe

    @property
    def logic_type(self) -> str:
        return self._logic_type_name

    @property
    def tweety_bridge(self) -> 'TweetyBridge':
        if not hasattr(self, '_tweety_bridge') or self._tweety_bridge is None:
            # Cela suppose que setup_agent_components a été appelé et a initialisé le bridge.
            # Une meilleure approche pourrait être d'injecter TweetyBridge au constructeur
            # ou d'avoir une méthode dédiée pour son initialisation si elle est complexe.
            raise RuntimeError("TweetyBridge not initialized. Call setup_agent_components or ensure it's injected.")
        return self._tweety_bridge

    @abstractmethod
    def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional['BeliefSet'], str]:
        pass

    @abstractmethod
    def generate_queries(self, text: str, belief_set: 'BeliefSet', context: Optional[Dict[str, Any]] = None) -> List[str]:
        pass

    @abstractmethod
    def execute_query(self, belief_set: 'BeliefSet', query: str) -> Tuple[Optional[bool], str]:
        # Devrait utiliser self.tweety_bridge et son solver spécifique
        pass

    @abstractmethod
    def interpret_results(self, text: str, belief_set: 'BeliefSet', queries: List[str], results: List[Tuple[Optional[bool], str]], context: Optional[Dict[str, Any]] = None) -> str:
        pass

    # @abstractmethod # Remplacé par l'utilisation directe du bridge
    # def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> 'BeliefSet':
    #     pass

    @abstractmethod
    def validate_formula(self, formula: str) -> bool:
        # Devrait utiliser self.tweety_bridge et son parser spécifique
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
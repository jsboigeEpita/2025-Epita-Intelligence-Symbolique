"""
Module de compatibilité pour semantic_kernel 0.9.6b1

Ce module fournit des adaptateurs et mocks pour les classes d'agents 
non disponibles dans semantic_kernel 0.9.6b1, permettant de maintenir
la compatibilité du code existant.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Callable, Awaitable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from semantic_kernel import Kernel
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.services.ai_service_selector import AIServiceSelector


logger = logging.getLogger(__name__)


# Classes pour la compatibilité des filters
class FunctionInvocationContext:
    """
    Adaptateur pour semantic_kernel.filters.functions.function_invocation_context.FunctionInvocationContext
    
    Fournit une interface compatible pour le contexte d'invocation de fonction.
    """
    
    def __init__(self, function_name: str = "", arguments: Optional[KernelArguments] = None, **kwargs):
        self.function_name = function_name
        self.arguments = arguments or KernelArguments()
        self.result = None
        self.exception = None
        self.is_cancelled = False
        
        # Propriétés additionnelles pour compatibilité
        self.kernel = kwargs.get('kernel')
        self.culture = kwargs.get('culture', 'en-US')
        
        self._logger = logging.getLogger(f"FunctionInvocationContext.{function_name}")
    
    def cancel(self):
        """Marque le contexte comme annulé."""
        self.is_cancelled = True
        self._logger.info(f"Contexte d'invocation annulé pour {self.function_name}")
    
    def set_result(self, result: Any):
        """Définit le résultat de l'invocation."""
        self.result = result
    
    def set_exception(self, exception: Exception):
        """Définit l'exception de l'invocation."""
        self.exception = exception


class FilterTypes:
    """
    Adaptateur pour semantic_kernel.filters.filter_types.FilterTypes
    
    Énumération des types de filtres disponibles.
    """
    
    # Types de filtres simulés
    FUNCTION_INVOCATION = "function_invocation"
    PROMPT_RENDERING = "prompt_rendering"
    AUTO_FUNCTION_INVOCATION = "auto_function_invocation"
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """Retourne tous les types de filtres disponibles."""
        return [
            cls.FUNCTION_INVOCATION,
            cls.PROMPT_RENDERING,
            cls.AUTO_FUNCTION_INVOCATION
        ]


# Classes pour la compatibilité des filtres génériques
class FilterBase:
    """Classe de base pour tous les filtres."""
    
    def __init__(self, filter_type: str):
        self.filter_type = filter_type
        self._logger = logging.getLogger(f"Filter.{filter_type}")
    
    async def on_function_invocation(self, context: FunctionInvocationContext) -> None:
        """Hook appelé lors de l'invocation d'une fonction."""
        pass


class FunctionInvocationFilter(FilterBase):
    """
    Filtre pour l'invocation de fonctions.
    
    Adaptateur pour les filtres d'invocation de fonction semantic_kernel.
    """
    
    def __init__(self):
        super().__init__(FilterTypes.FUNCTION_INVOCATION)
    
    async def on_function_invocation(self, context: FunctionInvocationContext) -> None:
        """
        Hook appelé lors de l'invocation d'une fonction.
        
        Args:
            context: Le contexte d'invocation de la fonction
        """
        self._logger.debug(f"Invocation de fonction: {context.function_name}")
        
        # Simulation du traitement du filtre
        if context.arguments:
            self._logger.debug(f"Arguments: {context.arguments}")


class Agent:
    """
    Adaptateur pour semantic_kernel.agents.Agent
    
    Fournit une interface compatible avec l'API Agent attendue
    tout en utilisant les services disponibles dans SK 0.9.6b1.
    """
    
    def __init__(self, 
                 name: str, 
                 kernel: Kernel,
                 instructions: str = "",
                 description: str = "",
                 **kwargs):
        self.name = name
        self.kernel = kernel
        self.instructions = instructions
        self.description = description
        self.id = f"agent_{name.lower().replace(' ', '_')}"
        
        # Propriétés additionnelles pour compatibilité
        self._context_enhanced_prompt = True
        self._current_context = ""
        
        self._logger = logging.getLogger(f"Agent.{name}")
    
    async def invoke(self, message: str, arguments: Optional[KernelArguments] = None) -> str:
        """
        Invoque l'agent avec un message et retourne la réponse.
        
        Utilise les services disponibles dans le kernel pour générer une réponse.
        """
        try:
            # Construire le prompt complet avec instructions et contexte
            full_prompt = self._build_full_prompt(message)
            
            # Utiliser le premier service de chat disponible
            chat_service = self._get_chat_service()
            if chat_service:
                # Créer les arguments si non fournis
                if arguments is None:
                    arguments = KernelArguments()
                
                # Exécuter avec le service de chat
                response = await chat_service.get_chat_message_content(
                    chat_history=[ChatMessageContent(role="user", content=full_prompt)],
                    settings=None
                )
                
                return str(response.content) if response else "Aucune réponse générée."
            else:
                self._logger.warning(f"Aucun service de chat disponible pour {self.name}")
                return f"[{self.name}] Service de chat non disponible - réponse simulée."
                
        except Exception as e:
            self._logger.error(f"Erreur lors de l'invocation de {self.name}: {e}")
            return f"[{self.name}] Erreur: {str(e)}"
    
    def _build_full_prompt(self, message: str) -> str:
        """Construit le prompt complet avec instructions et contexte."""
        parts = []
        
        if self.instructions:
            parts.append(f"Instructions: {self.instructions}")
        
        if hasattr(self, '_current_context') and self._current_context:
            parts.append(f"Contexte: {self._current_context}")
        
        parts.append(f"Message: {message}")
        
        return "\n\n".join(parts)
    
    def _get_chat_service(self):
        """Récupère le premier service de chat disponible dans le kernel."""
        try:
            # Tenter de récupérer un service de chat
            services = getattr(self.kernel, 'services', {})
            for service in services.values():
                if hasattr(service, 'get_chat_message_content'):
                    return service
            return None
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération du service de chat: {e}")
            return None


class ChatCompletionAgent(Agent):
    """
    Adaptateur pour semantic_kernel.agents.ChatCompletionAgent
    
    Hérite d'Agent et ajoute des fonctionnalités spécifiques 
    au chat completion.
    """
    
    def __init__(self, 
                 kernel: Kernel,
                 name: str,
                 instructions: str = "",
                 description: str = "",
                 **kwargs):
        super().__init__(name, kernel, instructions, description, **kwargs)
        self.execution_settings = kwargs.get('execution_settings', {})


class SelectionStrategy(ABC):
    """
    Classe de base abstraite pour les stratégies de sélection d'agents.
    
    Fournit l'interface attendue par les orchestrateurs.
    """
    
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def next(self, agents: List[Agent], history: List[ChatMessageContent]) -> Agent:
        """Sélectionne le prochain agent à exécuter."""
        pass
    
    def reset(self) -> None:
        """Remet à zéro la stratégie de sélection."""
        pass


class SequentialSelectionStrategy(SelectionStrategy):
    """
    Stratégie de sélection séquentielle des agents.
    
    Remplace semantic_kernel.agents.strategies.selection.sequential_selection_strategy.
    """
    
    def __init__(self, agents: Optional[List[Agent]] = None):
        super().__init__()
        self.agents = agents or []
        self.current_index = 0
    
    async def next(self, agents: List[Agent], history: List[ChatMessageContent]) -> Agent:
        """Sélectionne le prochain agent de manière séquentielle."""
        if not agents:
            raise ValueError("Aucun agent disponible pour la sélection")
        
        # Utiliser la liste fournie ou celle stockée
        agent_list = agents if agents else self.agents
        if not agent_list:
            raise ValueError("Aucun agent configuré pour la sélection")
        
        # Sélection cyclique
        selected_agent = agent_list[self.current_index % len(agent_list)]
        self.current_index += 1
        
        self._logger.info(f"Agent sélectionné: {selected_agent.name}")
        return selected_agent
    
    def reset(self) -> None:
        """Remet à zéro la stratégie de sélection."""
        self.current_index = 0


class TerminationStrategy(ABC):
    """
    Classe de base abstraite pour les stratégies de terminaison.
    
    Fournit l'interface attendue par les orchestrateurs.
    """
    
    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
        self.iteration_count = 0
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def should_terminate(self, agent: Agent, history: List[ChatMessageContent]) -> bool:
        """Détermine si l'exécution doit se terminer."""
        pass
    
    def reset(self) -> None:
        """Remet à zéro la stratégie de terminaison."""
        self.iteration_count = 0


class MaxIterationsTerminationStrategy(TerminationStrategy):
    """
    Stratégie de terminaison basée sur un nombre maximum d'itérations.
    """
    
    def __init__(self, max_iterations: int = 10):
        super().__init__(max_iterations)
    
    async def should_terminate(self, agent: Agent, history: List[ChatMessageContent]) -> bool:
        """Termine après max_iterations tours."""
        self.iteration_count += 1
        should_stop = self.iteration_count >= self.max_iterations
        
        if should_stop:
            self._logger.info(f"Terminaison après {self.iteration_count} itérations")
        
        return should_stop


class AgentGroupChat:
    """
    Adaptateur pour semantic_kernel.agents.AgentGroupChat
    
    Fournit une orchestration simple de groupe d'agents
    en utilisant les services disponibles dans SK 0.9.6b1.
    """
    
    def __init__(self,
                 agents: Optional[List[Agent]] = None,
                 selection_strategy: Optional[SelectionStrategy] = None,
                 termination_strategy: Optional[TerminationStrategy] = None,
                 **kwargs):
        self.agents = agents or []
        self.selection_strategy = selection_strategy or SequentialSelectionStrategy(self.agents)
        self.termination_strategy = termination_strategy or MaxIterationsTerminationStrategy()
        
        self.history: List[ChatMessageContent] = []
        self.is_active = False
        
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def add_agent(self, agent: Agent) -> None:
        """Ajoute un agent au groupe."""
        if agent not in self.agents:
            self.agents.append(agent)
            self._logger.info(f"Agent {agent.name} ajouté au groupe")
    
    async def invoke(self, message: str) -> List[ChatMessageContent]:
        """
        Lance une conversation de groupe avec le message initial.
        
        Returns:
            Liste des messages de la conversation
        """
        self.is_active = True
        self.history = []
        
        # Message initial
        initial_message = ChatMessageContent(
            role="user",
            content=message,
            name="System"
        )
        self.history.append(initial_message)
        
        self._logger.info(f"Début de conversation de groupe avec {len(self.agents)} agents")
        
        try:
            while self.is_active:
                # Sélectionner le prochain agent
                current_agent = await self.selection_strategy.next(self.agents, self.history)
                
                # Vérifier la terminaison
                if await self.termination_strategy.should_terminate(current_agent, self.history):
                    self._logger.info("Condition de terminaison atteinte")
                    break
                
                # Exécuter l'agent
                last_message = self.history[-1].content if self.history else message
                response = await current_agent.invoke(last_message)
                
                # Ajouter la réponse à l'historique
                response_message = ChatMessageContent(
                    role="assistant",
                    content=response,
                    name=current_agent.name
                )
                self.history.append(response_message)
                
                self._logger.info(f"Réponse de {current_agent.name}: {response[:100]}...")
                
        except Exception as e:
            self._logger.error(f"Erreur durant la conversation de groupe: {e}")
            error_message = ChatMessageContent(
                role="assistant",
                content=f"Erreur: {str(e)}",
                name="System"
            )
            self.history.append(error_message)
        
        finally:
            self.is_active = False
        
        self._logger.info(f"Conversation terminée avec {len(self.history)} messages")
        return self.history


# Exceptions compatibles
class AgentChatException(Exception):
    """Exception compatible pour les erreurs de chat d'agents."""
    pass


# Alias pour compatibilité avec les imports existants
Agent = Agent
ChatCompletionAgent = ChatCompletionAgent
AgentGroupChat = AgentGroupChat


def get_semantic_kernel_version() -> str:
    """Retourne la version de semantic_kernel et le statut de compatibilité."""
    try:
        import semantic_kernel
        version = getattr(semantic_kernel, '__version__', 'Unknown')
        return f"semantic_kernel {version} (compatibilité agents via adaptateur)"
    except Exception:
        return "semantic_kernel version inconnue (compatibilité agents via adaptateur)"


# Alias pour compatibilité avec les imports de filters
FunctionInvocationContext = FunctionInvocationContext
FilterTypes = FilterTypes
FunctionInvocationFilter = FunctionInvocationFilter


# Logging de compatibilité
logger.info("Module de compatibilité semantic_kernel agents chargé")
logger.info("Module de compatibilité semantic_kernel filters chargé")
logger.info(f"Version: {get_semantic_kernel_version()}")
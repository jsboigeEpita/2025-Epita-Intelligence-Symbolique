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
from semantic_kernel.contents.chat_message_content import ChatMessageContent as OriginalChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.services.ai_service_selector import AIServiceSelector
from enum import Enum


logger = logging.getLogger(__name__)


# Ajout d'AuthorRole pour la compatibilité
class AuthorRole(Enum):
    """Énumération des rôles d'auteur pour les messages de chat."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    
    @property
    def name(self):
        """Retourne le nom du rôle pour compatibilité."""
        return self.value


# Classe de compatibilité pour FunctionChoiceBehavior
class FunctionChoiceBehavior:
    """
    Classe de compatibilité pour semantic_kernel.connectors.ai.function_choice_behavior.FunctionChoiceBehavior
    
    Fournit le comportement de choix de fonction pour la compatibilité.
    """
    
    def __init__(self, auto_invoke_kernel_functions=False, max_auto_invoke_attempts=1):
        self.auto_invoke_kernel_functions = auto_invoke_kernel_functions
        self.max_auto_invoke_attempts = max_auto_invoke_attempts
        self.type_ = "auto" if auto_invoke_kernel_functions else "manual"
    
    @classmethod
    def Auto(cls, auto_invoke_kernel_functions=True, max_auto_invoke_attempts=5):
        """Crée un comportement de choix automatique."""
        return cls(auto_invoke_kernel_functions=auto_invoke_kernel_functions,
                  max_auto_invoke_attempts=max_auto_invoke_attempts)
    
    @classmethod
    def Manual(cls):
        """Crée un comportement de choix manuel."""
        return cls(auto_invoke_kernel_functions=False, max_auto_invoke_attempts=1)
    
    def __str__(self):
        return f"enable_kernel_functions={self.auto_invoke_kernel_functions} maximum_auto_invoke_attempts={self.max_auto_invoke_attempts} filters=None type_=<FunctionChoiceType.AUTO: '{self.type_}'>"


# Exception compatible
class AgentChatException(Exception):
    """Exception compatible pour les erreurs de chat d'agents."""
    pass


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
        
        Utilise les services disponibles dans le kernel pour générer une réponse
        et peut exécuter des fonctions si nécessaire.
        """
        try:
            # Construire le prompt complet avec instructions et contexte
            full_prompt = self._build_full_prompt(message)
            
            # Ajouter les fonctions disponibles au prompt
            functions_info = self._get_available_functions_info()
            if functions_info:
                full_prompt += f"\n\nFonctions disponibles:\n{functions_info}"
                full_prompt += "\n\nPour utiliser une fonction, incluez dans votre réponse: FUNCTION_CALL: NomPlugin.nom_fonction(param1=valeur1, param2=valeur2)"
            
            # Utiliser le premier service de chat disponible
            chat_service = self._get_chat_service()
            if chat_service:
                # Créer les arguments si non fournis
                if arguments is None:
                    arguments = KernelArguments()
                
                # Créer des settings appropriés pour OpenAI
                from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import OpenAIChatPromptExecutionSettings
                
                settings = OpenAIChatPromptExecutionSettings(
                    max_tokens=1000,
                    temperature=0.1
                )
                
                # Créer un ChatHistory avec les messages
                from semantic_kernel.contents.chat_history import ChatHistory
                chat_history = ChatHistory()
                chat_history.add_user_message(full_prompt)
                
                # Exécuter avec le service de chat
                response = await chat_service.get_chat_message_content(
                    chat_history=chat_history,
                    settings=settings
                )
                
                response_text = str(response.content) if response else "Aucune réponse générée."
                
                # Traiter les appels de fonction dans la réponse
                processed_response = await self._process_function_calls(response_text)
                
                return processed_response
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
    
    def _get_available_functions_info(self) -> str:
        """Récupère des informations sur les fonctions disponibles dans le kernel."""
        try:
            functions_info = []
            plugins = getattr(self.kernel, 'plugins', {})
            
            self._logger.debug(f"Plugins trouvés: {list(plugins.keys())}")
            
            for plugin_name, plugin in plugins.items():
                self._logger.debug(f"Inspection du plugin: {plugin_name} (type: {type(plugin)})")
                
                # Semantic Kernel 1.x encapsule les plugins dans des KernelPlugin
                # Les fonctions sont dans plugin.functions
                if hasattr(plugin, 'functions'):
                    functions_dict = getattr(plugin, 'functions')
                    self._logger.debug(f"  Plugin {plugin_name} a {len(functions_dict)} fonctions: {list(functions_dict.keys())}")
                    
                    for func_name, kernel_function in functions_dict.items():
                        try:
                            # Extraire les paramètres depuis les métadonnées de la fonction
                            params = []
                            if hasattr(kernel_function, 'metadata') and hasattr(kernel_function.metadata, 'parameters'):
                                for param in kernel_function.metadata.parameters:
                                    param_name = param.name
                                    if hasattr(param, 'is_required') and not param.is_required:
                                        if hasattr(param, 'default_value') and param.default_value is not None:
                                            param_name += f"={param.default_value}"
                                        else:
                                            param_name += "=None"
                                    params.append(param_name)
                            
                            param_str = ', '.join(params)
                            functions_info.append(f"- {plugin_name}.{func_name}({param_str})")
                            self._logger.debug(f"    {func_name}({param_str}) - ajouté")
                            
                        except Exception as func_error:
                            # Fallback sans signature détaillée
                            functions_info.append(f"- {plugin_name}.{func_name}()")
                            self._logger.debug(f"    {func_name}() - ajouté (fallback): {func_error}")
                else:
                    self._logger.debug(f"  Plugin {plugin_name} n'a pas d'attribut 'functions'")
            
            result = "\n".join(functions_info) if functions_info else "Aucune fonction disponible"
            self._logger.info(f"Fonctions disponibles détectées ({len(functions_info)}): {[f.split('- ')[1] if f.startswith('- ') else f for f in functions_info]}")
            return result
            
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération des fonctions: {e}", exc_info=True)
            return "Erreur lors de la récupération des fonctions"
    
    async def _process_function_calls(self, response_text: str) -> str:
        """Traite les appels de fonction dans la réponse de l'agent."""
        try:
            import re
            
            # Chercher les patterns FUNCTION_CALL: PluginName.function_name(params)
            function_pattern = r'FUNCTION_CALL:\s*([^.]+)\.([^(]+)\(([^)]*)\)'
            matches = re.findall(function_pattern, response_text)
            
            processed_response = response_text
            
            for plugin_name, function_name, params_str in matches:
                try:
                    # Récupérer le plugin
                    plugins = getattr(self.kernel, 'plugins', {})
                    plugin = plugins.get(plugin_name)
                    
                    # Vérifier si le plugin existe et a des fonctions
                    if plugin and hasattr(plugin, 'functions'):
                        functions_dict = getattr(plugin, 'functions')
                        if function_name in functions_dict:
                            kernel_function = functions_dict[function_name]
                            
                            # Parser les paramètres (format simple: param1=value1, param2=value2)
                            kwargs = {}
                            if params_str.strip():
                                param_pairs = params_str.split(',')
                                for pair in param_pairs:
                                    if '=' in pair:
                                        key, value = pair.split('=', 1)
                                        key = key.strip()
                                        value = value.strip().strip('"\'')
                                        # Convertir les valeurs booléennes
                                        if value.lower() == 'true':
                                            value = True
                                        elif value.lower() == 'false':
                                            value = False
                                        kwargs[key] = value
                            
                            # Exécuter la fonction via invoke du kernel
                            try:
                                kernel_args = KernelArguments(**kwargs)
                                result = await self.kernel.invoke(kernel_function, kernel_args)
                                result_content = str(result.value) if hasattr(result, 'value') else str(result)
                            except Exception as invoke_error:
                                self._logger.debug(f"Échec invoke kernel, tentative méthode directe: {invoke_error}")
                                # Fallback: accès direct à la méthode
                                if hasattr(kernel_function, 'method'):
                                    direct_method = kernel_function.method
                                    if asyncio.iscoroutinefunction(direct_method):
                                        result_content = await direct_method(**kwargs)
                                    else:
                                        result_content = direct_method(**kwargs)
                                    result_content = str(result_content)
                                else:
                                    raise invoke_error
                            
                            # Remplacer l'appel de fonction par le résultat
                            function_call = f"FUNCTION_CALL: {plugin_name}.{function_name}({params_str})"
                            function_result = f"[Résultat de {plugin_name}.{function_name}]: {result_content}"
                            processed_response = processed_response.replace(function_call, function_result)
                            
                            self._logger.info(f"Fonction exécutée: {plugin_name}.{function_name} -> {result_content[:100]}...")
                        
                        else:
                            error_msg = f"[Erreur]: Fonction {function_name} non trouvée dans le plugin {plugin_name}"
                            function_call = f"FUNCTION_CALL: {plugin_name}.{function_name}({params_str})"
                            processed_response = processed_response.replace(function_call, error_msg)
                            self._logger.warning(f"Fonction non trouvée: {plugin_name}.{function_name} (fonctions disponibles: {list(functions_dict.keys())})")
                    
                    else:
                        error_msg = f"[Erreur]: Plugin {plugin_name} non trouvé ou sans fonctions"
                        function_call = f"FUNCTION_CALL: {plugin_name}.{function_name}({params_str})"
                        processed_response = processed_response.replace(function_call, error_msg)
                        self._logger.warning(f"Plugin non trouvé: {plugin_name} (plugins disponibles: {list(plugins.keys())})")
                        
                except Exception as func_error:
                    error_msg = f"[Erreur lors de l'exécution]: {str(func_error)}"
                    function_call = f"FUNCTION_CALL: {plugin_name}.{function_name}({params_str})"
                    processed_response = processed_response.replace(function_call, error_msg)
                    self._logger.error(f"Erreur lors de l'exécution de {plugin_name}.{function_name}: {func_error}")
            
            return processed_response
            
        except Exception as e:
            self._logger.error(f"Erreur lors du traitement des appels de fonction: {e}")
            return response_text


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
    async def next(self, agents: List[Agent], history: List['ChatMessageContent']) -> Agent:
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
    
    async def next(self, agents: List[Agent], history: List['ChatMessageContent']) -> Agent:
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
    async def should_terminate(self, agent: Agent, history: List['ChatMessageContent']) -> bool:
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
    
    async def should_terminate(self, agent: Agent, history: List['ChatMessageContent']) -> bool:
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
        
        self.history: List['ChatMessageContent'] = []
        self.is_active = False
        
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def add_agent(self, agent: Agent) -> None:
        """Ajoute un agent au groupe."""
        if agent not in self.agents:
            self.agents.append(agent)
            self._logger.info(f"Agent {agent.name} ajouté au groupe")
    
    async def invoke(self, message: str) -> List['ChatMessageContent']:
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


# Classe de compatibilité pour ChatMessageContent avec propriété .name
class ChatMessageContent(OriginalChatMessageContent):
    """
    Classe de compatibilité pour ChatMessageContent qui ajoute le support de la propriété .name
    en utilisant metadata["name"] pour maintenir la compatibilité avec l'ancienne API.
    """
    
    def __init__(self, role=None, content=None, name=None, **kwargs):
        # Si name est fourni comme paramètre, l'ajouter aux metadata
        if name is not None:
            if 'metadata' not in kwargs:
                kwargs['metadata'] = {}
            kwargs['metadata']['name'] = name
        
        # Appeler le constructeur parent sans le paramètre name
        super().__init__(role=role, content=content, **kwargs)
    
    @property
    def name(self):
        """Propriété de compatibilité pour accéder au nom via metadata."""
        return self.metadata.get("name", "") if self.metadata else ""
    
    @name.setter
    def name(self, value):
        """Setter pour la propriété name qui utilise metadata."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata["name"] = value


# Export de la classe de compatibilité
__all__ = [
    'AuthorRole', 'FunctionChoiceBehavior', 'AgentChatException',
    'FunctionInvocationContext', 'FilterTypes', 'FunctionInvocationFilter',
    'Agent', 'ChatCompletionAgent', 'SelectionStrategy', 'SequentialSelectionStrategy',
    'TerminationStrategy', 'MaxIterationsTerminationStrategy', 'AgentGroupChat',
    'ChatMessageContent', 'get_semantic_kernel_version'
]
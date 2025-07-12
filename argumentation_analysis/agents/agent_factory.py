# Fichier : argumentation_analysis/agents/agent_factory.py
import logging
from typing import List, Optional, Type, Dict, Any, TYPE_CHECKING
from semantic_kernel import Kernel
from semantic_kernel.agents import Agent, ChatCompletionAgent

# Importations de la version distante (nettoyées)
from .utils.tracer import TracedAgent

# Importations de ma version (renommées pour clarté)
from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.config.settings import AppSettings

if TYPE_CHECKING:
    from semantic_kernel.functions import KernelPlugin

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Usine pour la création et la configuration centralisée des agents.
    Le principe est de toujours envelopper un agent métier "pur" (héritant de BaseAgent)
    dans un agent d'infrastructure `ChatCompletionAgent` de Semantic Kernel.
    """

    def __init__(self, kernel: Kernel, settings: AppSettings):
        """Initialise la factory avec les dépendances partagées."""
        self.kernel = kernel
        self.settings = settings
        self.llm_service_id = settings.service_manager.default_llm_service_id

    def create_agent(
        self,
        agent_class: Type[BaseAgent],
        agent_name: Optional[str] = None,
        trace_log_path: Optional[str] = None,
        **kwargs: Any
    ) -> ChatCompletionAgent:
        """
        Crée, configure, enveloppe et trace (optionnellement) un agent métier.
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"La classe '{agent_class.__name__}' doit hériter de BaseAgent.")

        final_agent_name = agent_name or agent_class.__name__
        logger.info(f"Création de l'agent de type '{agent_class.__name__}' nommé '{final_agent_name}'...")

        # 1. Instancier l'agent métier "pur"
        common_kwargs = {"kernel": self.kernel, "agent_name": final_agent_name, **kwargs}
        business_agent_instance = agent_class(**common_kwargs)
        logger.debug(f"Instance de l'agent métier '{final_agent_name}' créée.")

        # 2. Récupérer les instructions et les plugins de l'instance métier
        instructions = getattr(business_agent_instance, 'instructions', '')
        if not instructions:
            logger.warning(f"L'agent métier '{final_agent_name}' n'a pas d'instructions définies.")

        agent_plugins: List["KernelPlugin"] = getattr(business_agent_instance, 'get_plugins', lambda: [])()
        logger.debug(f"L'agent '{final_agent_name}' a fourni {len(agent_plugins)} plugin(s).")
        
        # 3. Envelopper dans un ChatCompletionAgent
        llm_service = self.kernel.get_service(self.llm_service_id)
        wrapper_agent = ChatCompletionAgent(
            kernel=self.kernel,
            service_id=self.llm_service_id, # Utilisation explicite du service_id
            name=final_agent_name,
            instructions=instructions,
            plugins=agent_plugins,
        )
        logger.info(f"Agent métier '{final_agent_name}' enveloppé dans un ChatCompletionAgent.")

        # 4. Envelopper dans un agent de traçage si demandé
        if trace_log_path:
            return TracedAgent(agent_to_wrap=wrapper_agent, trace_log_path=trace_log_path)
            
        return wrapper_agent

    # Les méthodes ci-dessous sont conservées pour la rétrocompatibilité
    # et la facilité d'utilisation, mais elles utilisent maintenant la nouvelle factory.

    def create_sherlock_agent(self, agent_name: str = "Sherlock", trace_log_path: Optional[str] = None) -> Agent:
        return self.create_agent(
            agent_class=SherlockEnqueteAgent,
            agent_name=agent_name,
            trace_log_path=trace_log_path,
        )

    def create_watson_agent(
        self,
        agent_name: str = "Watson",
        trace_log_path: Optional[str] = None,
        constants: Optional[List[str]] = None,
    ) -> Agent:
        return self.create_agent(
            agent_class=WatsonLogicAssistant,
            agent_name=agent_name,
            trace_log_path=trace_log_path,
            constants=constants,
        )

    def create_project_manager_agent(self, trace_log_path: Optional[str] = None) -> Agent:
        return self.create_agent(
            agent_class=ProjectManagerAgent,
            agent_name="ProjectManager",
            trace_log_path=trace_log_path
        )
    
    def create_informal_fallacy_agent(self, trace_log_path: Optional[str] = None) -> Agent:
        """Crée l'agent d'analyse de sophismes informels (ancienne version)."""
        return self.create_agent(
            agent_class=InformalAnalysisAgent,
            agent_name="InformalFallacyAgent",
            trace_log_path=trace_log_path
        )

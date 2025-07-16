# Fichier : argumentation_analysis/agents/agent_factory.py
import logging
from typing import List, Optional, Type, Dict, Any

from semantic_kernel import Kernel
from semantic_kernel.agents import Agent, ChatCompletionAgent

from argumentation_analysis.agents.channels.volatile_agent_channel import VolatileAgentChannel
from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.config.settings import AppSettings

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Usine pour la création et la configuration centralisée des agents.
    Le principe est de toujours envelopper un agent métier "pur" (héritant de BaseAgent)
    dans un agent d'infrastructure `ChatCompletionAgent` de Semantic Kernel,
    en appliquant le pattern "Composition over Inheritance".
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
        **kwargs: Any
    ) -> ChatCompletionAgent:
        """
        Crée, configure et enveloppe un agent métier à partir de sa classe.

        Args:
            agent_class (Type[BaseAgent]): La classe de l'agent métier à instancier.
            agent_name (Optional[str]): Un nom spécifique pour l'instance de l'agent.
                                         Si non fourni, le nom de la classe sera utilisé.
            **kwargs: Arguments supplémentaires à passer au constructeur de l'agent métier.

        Returns:
            Une instance de `ChatCompletionAgent` qui enveloppe l'agent métier configuré.
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"La classe '{agent_class.__name__}' doit hériter de BaseAgent.")

        final_agent_name = agent_name or agent_class.__name__
        logger.info(f"Création de l'agent de type '{agent_class.__name__}' nommé '{final_agent_name}'...")

        # 1. Instancier l'agent métier "pur"
        # On passe les dépendances nécessaires.
        # Correction: Adapter l'instanciation aux signatures des constructeurs des agents
        common_kwargs = {"kernel": self.kernel, **kwargs}

        if agent_class in [ProjectManagerAgent, InformalAnalysisAgent, PropositionalLogicAgent, ExtractAgent, WatsonLogicAssistant, SherlockEnqueteAgent]:
            # Ces classes attendent 'agent_name' au lieu de 'name'
            # et certaines comme Watson/Sherlock attendent 'kernel'
            business_agent_instance = agent_class(
                agent_name=final_agent_name,
                **common_kwargs
            )
        else:
             # Comportement par défaut pour d'autres agents potentiels
            business_agent_instance = agent_class(
                name=final_agent_name,
                **common_kwargs
        )
        logger.debug(f"Instance de l'agent métier '{final_agent_name}' créée.")

        # 2. Récupérer les instructions et les plugins depuis l'instance métier
        # L'agent métier est la source de vérité pour sa configuration.
        instructions = getattr(business_agent_instance, 'instructions',
                               getattr(business_agent_instance, '_instructions', ''))
        if not instructions:
            logger.warning(f"L'agent métier '{final_agent_name}' n'a pas d'instructions claires définies.")

        # La méthode get_plugins() permet à l'agent de déclarer les plugins dont il a besoin.
        # Cela favorise l'encapsulation.
        try:
            agent_plugins: List[KernelPlugin] = business_agent_instance.get_plugins()
            logger.debug(f"L'agent '{final_agent_name}' a fourni {len(agent_plugins)} plugin(s).")
        except AttributeError:
            # Rétrocompatibilité ou cas où l'agent n'a pas de plugins spécifiques.
            agent_plugins = []
            logger.debug(f"L'agent '{final_agent_name}' n'a pas de méthode get_plugins(). Aucun plugin spécifique chargé.")

        # 3. Envelopper l'agent métier dans un ChatCompletionAgent
        wrapper_agent = ChatCompletionAgent(
            kernel=self.kernel,
            name=final_agent_name,
            instructions=instructions,
            plugins=agent_plugins, # On utilise les plugins fournis par l'agent
        )
        logger.info(f"Agent métier '{final_agent_name}' enveloppé dans un ChatCompletionAgent.")

        # 4. Attribuer un canal de communication
        # Correction: Le constructeur attend maintenant l'instance de l'agent
        channel = VolatileAgentChannel(agent=wrapper_agent)
        # L'assignation du canal est maintenant implicite via le constructeur du canal.
        # wrapper_agent.channel = channel # Cette ligne est supprimée car l'attribut n'existe plus.
        logger.debug(f"Canal de communication volatile associé à '{final_agent_name}'.")

        return wrapper_agent

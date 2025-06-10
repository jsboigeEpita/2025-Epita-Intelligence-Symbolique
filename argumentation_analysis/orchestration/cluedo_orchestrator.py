import asyncio
from typing import List, Dict, Any, Optional

import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.kernel import Kernel
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité pour agents et filters
from semantic_kernel.agents import (
    Agent, AgentGroupChat, SequentialSelectionStrategy, TerminationStrategy
)
from semantic_kernel.functions import FunctionInvocationContext, FilterTypes
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from pydantic import Field
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant

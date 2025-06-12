import asyncio
import logging
from typing import List, Dict, Any, Optional

import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.kernel import Kernel

# Configuration du logging en premier
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité pour agents et filters
# SequentialSelectionStrategy a été remplacée par CyclicSelectionStrategy depuis cluedo_extended_orchestrator
# Agent et TerminationStrategy sont maintenant aussi importés depuis cluedo_extended_orchestrator.
# AgentGroupChat est conservé depuis semantic_kernel.agents pour l'instant.
# Agent et TerminationStrategy sont maintenant dans le module `base` pour éviter les dépendances circulaires.
# CyclicSelectionStrategy est bien défini dans cluedo_extended_orchestrator.
from .base import Agent, TerminationStrategy
from .cluedo_extended_orchestrator import CyclicSelectionStrategy

# Tentative d'import depuis semantic_kernel.filters pour SK 1.32.2+
# Note: La structure des filtres a changé dans les versions plus récentes de semantic-kernel.
# Pour la version 0.9.6b1, ces imports ne sont pas valides. Le code qui les utilise doit être adapté.
# Pour le moment, nous commentons le bloc pour éviter le crash.
# try:
#     from semantic_kernel.filters.functions.function_invocation_context import FunctionInvocationContext
#     from semantic_kernel.filters.filter_types import FilterTypes
# except ImportError:
#     logging.warning("Impossible d'importer FunctionInvocationContext ou FilterTypes depuis semantic_kernel.filters. "
#                     "Les fonctionnalités dépendantes pourraient être affectées. Définition de placeholders.")
#     class FunctionInvocationContext: pass
#     class FilterTypes: pass

from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from pydantic import Field

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant

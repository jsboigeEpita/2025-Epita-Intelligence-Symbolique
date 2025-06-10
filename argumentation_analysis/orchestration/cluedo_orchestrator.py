import asyncio
from typing import List, Dict, Any, Optional

import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.kernel import Kernel
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité pour agents et filters
from semantic_kernel.agents import Agent, AgentGroupChat
from argumentation_analysis.utils.semantic_kernel_compatibility import SequentialSelectionStrategy, TerminationStrategy, FunctionInvocationContext, FilterTypes
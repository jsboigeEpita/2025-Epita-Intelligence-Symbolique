# argumentation_analysis/orchestration/logique_complexe_orchestrator.py

import logging
from typing import Optional, List, Dict, Any
from semantic_kernel import Kernel
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from argumentation_analysis.utils.semantic_kernel_compatibility import SequentialSelectionStrategy
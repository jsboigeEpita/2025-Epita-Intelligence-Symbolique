# argumentation_analysis/agents/orchestration/cluedo_sherlock_watson_demo.py

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité
from semantic_kernel.agents import AgentGroupChat
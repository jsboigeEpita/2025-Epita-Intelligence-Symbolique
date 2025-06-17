# argumentation_analysis/pipelines/orchestration/__init__.py

"""
Ce package rend les composants clés de la nouvelle architecture d'orchestration
directement accessibles, assurant la rétrocompatibilité et une transition en douceur.
"""

# 1. Configuration Essentielle
from .config.base_config import ExtendedOrchestrationConfig
from .config.enums import OrchestrationMode, AnalysisType

# 2. Composants Core du Système
try:
    from argumentation_analysis.core.communication import MessageMiddleware as Middleware
except ImportError:
    Middleware = None

try:
    from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager as ServiceManager
except ImportError:
    ServiceManager = None

# 3. Moteur d'Éxécution Principal
from .execution.engine import analyze_text_orchestrated as Engine

# 4. Processeurs et Post-Processeurs d'Analyse
from .analysis.processors import execute_operational_tasks, synthesize_hierarchical_results
from .analysis.post_processors import post_process_orchestration_results
from .analysis.traces import save_orchestration_trace

# 5. Orchestrateurs Spécialisés (Wrappers)
from .orchestrators.specialized.cluedo_orchestrator import CluedoOrchestratorWrapper
from .orchestrators.specialized.conversation_orchestrator import ConversationOrchestratorWrapper
from .orchestrators.specialized.logic_orchestrator import LogicOrchestratorWrapper
from .orchestrators.specialized.real_llm_orchestrator import RealLLMOrchestratorWrapper

__all__ = [
    # Config
    "ExtendedOrchestrationConfig",
    "OrchestrationMode",
    "AnalysisType",
    
    # Core
    "Middleware",
    "ServiceManager",
    
    # Execution
    "Engine",
    
    # Analysis
    "execute_operational_tasks",
    "synthesize_hierarchical_results",
    "post_process_orchestration_results",
    "save_orchestration_trace",
    
    # Specialized Orchestrators
    "CluedoOrchestratorWrapper",
    "ConversationOrchestratorWrapper",
    "LogicOrchestratorWrapper",
    "RealLLMOrchestratorWrapper",
]
# argumentation_analysis/orchestration/cluedo_extended_orchestrator.py
"""
Orchestrateur principal pour le workflow Cluedo étendu (Sherlock → Watson → Moriarty).
Ce module gère l'orchestration du flux de conversation, en déléguant les
logiques spécifiques (stratégies, métriques, analyse) à des composants dédiés.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.kernel import Kernel
from pydantic import Field

try:
    from semantic_kernel.events import FunctionInvokedEventArgs, FunctionInvokingEventArgs
    from semantic_kernel.functions.function_filter_base import FunctionFilterBase
    FILTERS_AVAILABLE = True
except ImportError:
    class FunctionInvokingEventArgs:
        def __init__(self, **kwargs): pass
    class FunctionInvokedEventArgs:
        def __init__(self, **kwargs): pass
    class FunctionFilterBase:
        pass
    FILTERS_AVAILABLE = False
    
# Imports des dépendances du projet
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
from argumentation_analysis.agents.core.oracle.permissions import QueryType, PermissionRule
from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Nouvelle implémentation du logging via un filtre, conforme aux standards SK modernes
if FILTERS_AVAILABLE:
    class ToolCallLoggingFilter(FunctionFilterBase):
        """
        Filtre pour journaliser les appels de fonctions (outils) du kernel.
        """
        async def on_function_invoking(self, context: FunctionInvokingEventArgs) -> None:
            function_name = f"{context.function.plugin_name}.{context.function.name}"
            logger.debug(f"▶️  INVOKING KERNEL FUNCTION: {function_name}")
            args_str = ", ".join(f"{k}='{str(v)[:100]}...'" for k, v in context.arguments.items())
            logger.debug(f"  ▶️  ARGS: {args_str}")

        async def on_function_invoked(self, context: FunctionInvokedEventArgs) -> None:
            function_name = f"{context.function.plugin_name}.{context.function.name}"
            result_content = str(context.result) if context.result else "N/A"
            logger.debug(f"  ◀️  RESULT: {result_content[:500]}...") # Tronqué
            logger.debug(f"◀️  FINISHED KERNEL FUNCTION: {function_name}")

class CluedoExtendedOrchestrator:
    """
    Orchestrateur pour le workflow Cluedo 3-agents.
    """

    def __init__(self,
                 kernel: Kernel,
                 max_turns: int = 15,
                 max_cycles: int = 5,
                 oracle_strategy: str = "balanced",
                 adaptive_selection: bool = False,
                 service_id: str = "chat_completion"):
        self.kernel = kernel
        self.service_id = service_id
        self.max_turns = max_turns
        self.max_cycles = max_cycles
        self.oracle_strategy = oracle_strategy
        self.adaptive_selection = adaptive_selection
        self.kernel_lock = asyncio.Lock()

        self.oracle_state: Optional[CluedoOracleState] = None
        self.sherlock_agent: Optional[SherlockEnqueteAgent] = None
        self.watson_agent: Optional[WatsonLogicAssistant] = None
        self.moriarty_agent: Optional[MoriartyInterrogatorAgent] = None
        self.orchestration: Optional[GroupChatOrchestration] = None
        
        self.selection_strategy = None
        self.termination_strategy = None
        self.suggestion_handler = None
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    async def setup_workflow(self,
                           nom_enquete: str = "Le Mystère du Manoir Tudor",
                           elements_jeu: Optional[Dict[str, List[str]]] = None,
                           initial_cards: Dict[str, List[str]] = None):
        """Configure le workflow, l'état Oracle, les agents et les composants logiques."""
        logger.info(f"Configuration du workflow 3-agents - Stratégie: {self.oracle_strategy}")

        if elements_jeu is None:
            elements_jeu = {
                "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
                "armes": ["Poignard", "Chandelier", "Revolver"],
                "lieux": ["Salon", "Cuisine", "Bureau"]
            }
        
        self.oracle_state = CluedoOracleState(
            nom_enquete_cluedo=nom_enquete,
            elements_jeu_cluedo=elements_jeu,
            description_cas="Un meurtre a été commis.",
            initial_context={"raison_enquete": "Validation du workflow"},
            oracle_strategy=self.oracle_strategy,
            initial_cards=initial_cards
        )
        
        # Ajout du filtre de logging moderne
        if FILTERS_AVAILABLE:
            self.kernel.add_filter("function_invocation", ToolCallLoggingFilter())
            logger.info("Filtre de journalisation (ToolCallLoggingFilter) activé.")
        
        all_constants = [name.replace(" ", "") for category in elements_jeu.values() for name in category]
        
        try:
            tweety_bridge = TweetyBridge()
            logger.info("✅ TweetyBridge initialisé.")
        except Exception as e:
            logger.warning(f"⚠️ Échec initialisation TweetyBridge: {e}. Watson en mode dégradé.")
            tweety_bridge = None

        self.sherlock_agent = SherlockEnqueteAgent(
            kernel=self.kernel, agent_name="Sherlock", service_id=self.service_id
        )
        self.watson_agent = WatsonLogicAssistant(
            kernel=self.kernel, agent_name="Watson", tweety_bridge=tweety_bridge,
            constants=all_constants, service_id=self.service_id
        )
        self.moriarty_agent = MoriartyInterrogatorAgent(
            kernel=self.kernel, dataset_manager=self.oracle_state.dataset_access_manager,
            game_strategy=self.oracle_strategy, agent_name="Moriarty"
        )
        
        agents = [self.sherlock_agent, self.watson_agent, self.moriarty_agent]
        
        from argumentation_analysis.orchestration.cluedo_components.strategies import CyclicSelectionStrategy, OracleTerminationStrategy
        from argumentation_analysis.orchestration.cluedo_components.suggestion_handler import SuggestionHandler
        from argumentation_analysis.orchestration.cluedo_components.cluedo_plugins import CluedoInvestigatorPlugin
        
        self.suggestion_handler = SuggestionHandler(self.moriarty_agent)
        investigator_plugin = CluedoInvestigatorPlugin(self.suggestion_handler)
        self.kernel.add_plugin(investigator_plugin, "Investigator")

        self.selection_strategy = CyclicSelectionStrategy(agents, self.adaptive_selection, self.oracle_state)
        self.termination_strategy = OracleTerminationStrategy(self.max_turns, self.max_cycles, self.oracle_state)
        
        self.orchestration = GroupChatOrchestration()
        session_id = f"cluedo_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.orchestration.initialize_session(session_id, {agent.name: agent for agent in agents})
        
        logger.info(f"Workflow configuré. Solution secrète: {self.oracle_state.get_solution_secrete()}")
        return self.oracle_state

    async def execute_workflow(self, initial_question: str) -> Dict[str, Any]:
        """Exécute la boucle principale du workflow."""
        if not self.orchestration:
            raise ValueError("Workflow non configuré.")

        self.start_time = datetime.now()
        history: List[ChatMessageContent] = [ChatMessageContent(role="user", content=initial_question, name="Orchestrator")]
        active_agent = None

        try:
            while not await self.termination_strategy.should_terminate(active_agent, history):
                active_agent = await self.selection_strategy.next(list(self.orchestration.active_agents.values()), history)
                
                if hasattr(active_agent, 'invoke'):
                    agent_response_content = await active_agent.invoke(history)
                    agent_response = ChatMessageContent(role="assistant", content=str(agent_response_content), name=active_agent.name)
                else:
                    agent_response = ChatMessageContent(role="assistant", content=f"Agent {active_agent.name} non invocable.", name=active_agent.name)

                if agent_response:
                    history.append(agent_response)
                    logger.info(f"[{active_agent.name}]: {agent_response.content}")
        
        except Exception as e:
            logger.error(f"Erreur durant l'orchestration: {e}", exc_info=True)
        
        finally:
            self.end_time = datetime.now()

        return self._collect_final_results(history)

    def _collect_final_results(self, history: List[ChatMessageContent]) -> Dict[str, Any]:
        """Collecte et structure les résultats finaux."""
        from argumentation_analysis.orchestration.cluedo_components.metrics_collector import MetricsCollector
        
        metrics_collector = MetricsCollector(
            oracle_state=self.oracle_state,
            start_time=self.start_time,
            end_time=self.end_time,
            history=history,
            strategy=self.oracle_strategy
        )
        
        final_metrics = metrics_collector.collect_final_metrics()

        return {
            "workflow_info": {
                "strategy": self.oracle_strategy,
                "execution_time_seconds": (self.end_time - self.start_time).total_seconds(),
            },
            **final_metrics
        }
# argumentation_analysis/orchestration/cluedo_extended_orchestrator.py
"""
Orchestrateur principal pour le workflow Cluedo étendu (Sherlock → Watson → Moriarty).
Ce module gère l'orchestration du flux de conversation, en déléguant les
logiques spécifiques (stratégies, métriques, analyse) à des composants dédiés.
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Awaitable

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.kernel import Kernel
from semantic_kernel.filters.filter_types import FilterTypes
from semantic_kernel.filters.functions.function_invocation_context import FunctionInvocationContext


# Imports locaux des composants
# Assumant que ces composants existent dans un sous-dossier.
# Si ce n'est pas le cas, ces imports devront être ajustés.
try:
    from argumentation_analysis.orchestration.cluedo_components.logging_handler import ToolCallLoggingHandler
    from argumentation_analysis.orchestration.cluedo_components.strategies import CyclicSelectionStrategy, OracleTerminationStrategy
    from argumentation_analysis.orchestration.cluedo_components.metrics_collector import MetricsCollector
    from argumentation_analysis.orchestration.cluedo_components.suggestion_handler import SuggestionHandler
    from argumentation_analysis.orchestration.cluedo_components.dialogue_analyzer import DialogueAnalyzer
    from argumentation_analysis.orchestration.cluedo_components.enhanced_logic import EnhancedLogicHandler
except ImportError as e:
    # Fallback si la structure de cluedo_components n'existe pas, pour éviter un crash complet
    logging.error(f"Impossible d'importer les composants depuis cluedo_components: L'orchestrateur sera non fonctionnel. Erreur: {e}")
    ToolCallLoggingHandler = object
    CyclicSelectionStrategy = object
    OracleTerminationStrategy = object
    MetricsCollector = object
    SuggestionHandler = object
    DialogueAnalyzer = object
    EnhancedLogicHandler = object


# Imports des dépendances du projet
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
from argumentation_analysis.agents.core.oracle.permissions import QueryType
from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration

logger = logging.getLogger(__name__)

class CluedoExtendedOrchestrator:
    """
    Orchestrateur pour le workflow Cluedo 3-agents.
    Coordonne les interactions entre agents, l'état du jeu, et les stratégies,
    en utilisant des composants spécialisés pour chaque partie de la logique.
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

        # État et agents (initialisés lors du setup)
        self.oracle_state: Optional[CluedoOracleState] = None
        self.sherlock_agent: Optional[SherlockEnqueteAgent] = None
        self.watson_agent: Optional[WatsonLogicAssistant] = None
        self.moriarty_agent: Optional[MoriartyInterrogatorAgent] = None
        self.orchestration: Optional[GroupChatOrchestration] = None
        
        # Composants logiques (initialisés lors du setup)
        self.logging_handler: Optional[ToolCallLoggingHandler] = None
        self.selection_strategy: Optional[CyclicSelectionStrategy] = None
        self.termination_strategy: Optional[OracleTerminationStrategy] = None
        self.suggestion_handler: Optional[SuggestionHandler] = None
        self.dialogue_analyzer: Optional[DialogueAnalyzer] = None
        self.enhanced_logic: Optional[EnhancedLogicHandler] = None
        
        # Métriques
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    async def setup_workflow(self,
                           nom_enquete: str = "Le Mystère du Manoir Tudor",
                           elements_jeu: Optional[Dict[str, List[str]]] = None):
        """Configure le workflow, l'état Oracle, les agents et les composants logiques."""
        logger.info(f"Configuration du workflow 3-agents - Stratégie: {self.oracle_strategy}")

        # 1. Configuration de l'état Oracle
        if elements_jeu is None:
            elements_jeu = {
                "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose", "Docteur Orchidée"],
                "armes": ["Poignard", "Chandelier", "Revolver", "Corde"],
                "lieux": ["Salon", "Cuisine", "Bureau", "Bibliothèque"]
            }
        
        self.oracle_state = CluedoOracleState(
            nom_enquete_cluedo=nom_enquete,
            elements_jeu_cluedo=elements_jeu,
            description_cas="Un meurtre a été commis. Qui, où, et avec quoi ?",
            oracle_strategy=self.oracle_strategy
        )

        # 2. Configuration des agents
        try:
            tweety_bridge = TweetyBridge()
            logger.info("✅ TweetyBridge initialisé.")
        except Exception as e:
            logger.warning(f"⚠️ Échec initialisation TweetyBridge: {e}. Watson en mode dégradé.")
            tweety_bridge = None

        self.sherlock_agent = SherlockEnqueteAgent(kernel=self.kernel, agent_name="Sherlock", service_id=self.service_id)
        self.watson_agent = WatsonLogicAssistant(
            kernel=self.kernel, agent_name="Watson", tweety_bridge=tweety_bridge,
            constants=[name.replace(" ", "") for cat in elements_jeu.values() for name in cat],
            service_id=self.service_id
        )
        self.moriarty_agent = MoriartyInterrogatorAgent(
            kernel=self.kernel, cluedo_dataset=self.oracle_state.cluedo_dataset,
            game_strategy=self.oracle_strategy, agent_name="Moriarty"
        )
        
        # 3. Configuration des composants logiques et stratégies
        self.logging_handler = ToolCallLoggingHandler()
        self.kernel.add_filter(FilterTypes.FUNCTION_INVOCATION, self.logging_handler)
        
        agents = [self.sherlock_agent, self.watson_agent, self.moriarty_agent]
        self.selection_strategy = CyclicSelectionStrategy(agents, self.adaptive_selection, self.oracle_state)
        self.termination_strategy = OracleTerminationStrategy(self.max_turns, self.max_cycles, self.oracle_state)
        
        self.suggestion_handler = SuggestionHandler(self.moriarty_agent)
        self.dialogue_analyzer = DialogueAnalyzer(self.oracle_state)
        self.enhanced_logic = EnhancedLogicHandler(self.oracle_state, self.oracle_strategy)
        
        # 4. Configuration de l'orchestration de chat
        self.orchestration = GroupChatOrchestration()
        session_id = f"cluedo_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.orchestration.initialize_session(session_id, {agent.name: agent for agent in agents})
        
        logger.info(f"Workflow configuré. Solution secrète: {self.oracle_state.get_solution_secrete()}")

    async def execute_workflow(self, initial_question: str) -> Dict[str, Any]:
        """Exécute la boucle principale du workflow."""
        if not all([self.orchestration, self.oracle_state, self.selection_strategy, self.termination_strategy, self.suggestion_handler]):
            raise ValueError("Workflow non configuré. Appelez setup_workflow() d'abord.")

        self.start_time = datetime.now()
        logger.info("🚀 Début du workflow 3-agents")
        history: List[ChatMessageContent] = [ChatMessageContent(role="user", content=initial_question, name="Orchestrator")]
        active_agent = None

        try:
            while not await self.termination_strategy.should_terminate(active_agent, history):
                active_agent = await self.selection_strategy.next(list(self.orchestration.active_agents.values()), history)
                logger.info(f"==> Agent suivant: {active_agent.name}")

                if hasattr(active_agent, 'invoke_custom'):
                    agent_response = await active_agent.invoke_custom(history)
                else:
                    agent_response = ChatMessageContent(role="assistant", content=f"Je suis {active_agent.name}.", name=active_agent.name)
                
                if agent_response:
                    history.append(agent_response)
                    logger.info(f"[{active_agent.name}]: {agent_response.content}")
                    
                    # Logique de suggestion déléguée
                    suggestion = self.suggestion_handler.extract_cluedo_suggestion(str(agent_response.content))
                    if suggestion:
                        oracle_revelation = await self.suggestion_handler.force_moriarty_oracle_revelation(suggestion, active_agent.name)
                        if oracle_revelation:
                            history.append(ChatMessageContent(role="assistant", content=str(oracle_revelation), name="Moriarty"))
                            logger.info(f"[Moriarty - Oracle]: {oracle_revelation.get('content')}")

        except Exception as e:
            logger.error(f"Erreur durant la boucle d'orchestration: {e}", exc_info=True)
            history.append(ChatMessageContent(role="system", content=f"Erreur système: {e}"))
        
        finally:
            self.end_time = datetime.now()

        return self._collect_final_results(history)

    def _collect_final_results(self, history: List[ChatMessageContent]) -> Dict[str, Any]:
        """Collecte et structure les résultats finaux en utilisant MetricsCollector."""
        logger.info("[OK] Workflow 3-agents terminé. Collecte des métriques...")

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
                "max_turns": self.max_turns,
                "execution_time_seconds": (self.end_time - self.start_time).total_seconds(),
                "timestamp": self.end_time.isoformat()
            },
            **final_metrics 
        }
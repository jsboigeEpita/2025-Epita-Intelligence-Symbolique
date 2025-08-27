# argumentation_analysis/orchestration/cluedo_extended_orchestrator.py
"""
Orchestrateur pour workflow Cluedo étendu avec 3 agents : Sherlock → Watson → Moriarty.

Ce module implémente l'orchestration avancée pour le workflow 3-agents avec agent Oracle,
incluant la sélection cyclique, la terminaison Oracle, et l'intégration avec CluedoOracleState.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.kernel import Kernel
from argumentation_analysis.orchestration.base import SelectionStrategy, TerminationStrategy
from semantic_kernel.agents import Agent
# from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from semantic_kernel.contents.chat_message_content import ChatMessageContent

class AgentGroupChat:
    """Fallback class for compatibility."""
    def __init__(self, agents: List[Agent] = None, **kwargs):
        self.agents = agents or []
        
AGENTS_AVAILABLE = True
from semantic_kernel.functions import KernelArguments
from semantic_kernel.contents.streaming_chat_message_content import StreamingChatMessageContent

# Import conditionnel pour les modules filters qui peuvent ne pas exister
try:
    from semantic_kernel.functions.kernel_function_context import KernelFunctionContext as FunctionInvocationContext
    from semantic_kernel.functions.kernel_function_context import KernelFunctionContext
    FILTERS_AVAILABLE = True
except ImportError:
    # Fallbacks pour compatibilité
    class KernelFunctionContext:
        def __init__(self, **kwargs):
            pass
    
    FunctionInvocationContext = KernelFunctionContext
            
    class FilterTypes:
        pass
        
    FILTERS_AVAILABLE = False
# from semantic_kernel.processes.runtime.in_process_runtime import InProcessRuntime  # Module non disponible
from pydantic import Field

# Imports locaux
from ..core.cluedo_oracle_state import CluedoOracleState
from ..orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from ..orchestration.group_chat import GroupChatOrchestration
from ..agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
from ..agents.core.oracle.cluedo_dataset import CluedoDataset
from argumentation_analysis.config.settings import AppSettings

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CyclicSelectionStrategy(SelectionStrategy):
    """
    Stratégie de sélection cyclique adaptée au workflow Oracle : Sherlock → Watson → Moriarty.
    
    Implémente une sélection cyclique avec adaptations contextuelles optionnelles
    selon l'état du jeu et les interactions précédentes.
    """
    
    def __init__(self, agents: List[Agent], adaptive_selection: bool = False, oracle_state: 'CluedoOracleState' = None):
        """
        Initialise la stratégie de sélection cyclique.
        
        Args:
            agents: Liste des agents dans l'ordre cyclique souhaité
            adaptive_selection: Active les adaptations contextuelles (Phase 2)
            oracle_state: État Oracle pour accès au contexte (Phase C)
        """
        super().__init__()
        # Stockage direct dans __dict__ pour éviter les problèmes Pydantic
        self.__dict__['agents'] = agents
        self.__dict__['agent_order'] = [getattr(agent, 'name', getattr(agent, 'id', str(agent))) for agent in agents]
        self.__dict__['current_index'] = 0
        self.__dict__['adaptive_selection'] = adaptive_selection
        self.__dict__['turn_count'] = 0
        self.__dict__['oracle_state'] = oracle_state  # PHASE C: Accès au contexte
        
        self.__dict__['_logger'] = logging.getLogger(self.__class__.__name__)
        self._logger.info(f"CyclicSelectionStrategy initialisée avec ordre: {self.agent_order}")
    
    async def next(self, agents: List[Agent], history: List[ChatMessageContent]) -> Agent:
        """
        Sélectionne le prochain agent selon l'ordre cyclique.
        
        Args:
            agents: Liste des agents disponibles
            history: Historique des messages
            
        Returns:
            Agent sélectionné pour le prochain tour
        """
        if not agents:
            raise ValueError("Aucun agent disponible pour la sélection")
        
        # Sélection cyclique de base
        selected_agent_name = self.agent_order[self.current_index]
        selected_agent = next((agent for agent in agents if agent.name == selected_agent_name), None)
        
        if not selected_agent:
            self._logger.warning(f"Agent {selected_agent_name} non trouvé, sélection du premier agent disponible")
            selected_agent = agents[0]
        
        # PHASE C: Injection du contexte récent dans l'agent sélectionné
        if self.oracle_state and hasattr(selected_agent, '_context_enhanced_prompt'):
            contextual_addition = self.oracle_state.get_contextual_prompt_addition(selected_agent.name)
            if contextual_addition:
                # Stockage temporaire du contexte pour l'agent
                selected_agent._current_context = contextual_addition
                self._logger.debug(f"Contexte injecté pour {selected_agent.name}: {len(contextual_addition)} caractères")
        
        # Avance l'index cyclique (contournement Pydantic)
        object.__setattr__(self, 'current_index', (self.current_index + 1) % len(self.agent_order))
        object.__setattr__(self, 'turn_count', self.turn_count + 1)
        
        # Adaptations contextuelles (optionnelles pour Phase 1)
        if self.adaptive_selection:
            selected_agent = await self._apply_contextual_adaptations(selected_agent, agents, history)
        
        self._logger.info(f"Agent sélectionné: {selected_agent.name} (tour {self.turn_count})")
        return selected_agent
    
    async def _apply_contextual_adaptations(self, default_agent: Agent, agents: List[Agent], history: List[ChatMessageContent]) -> Agent:
        """
        Applique des adaptations contextuelles à la sélection (Phase 2).
        
        Adaptations possibles:
        - Si Sherlock fait une suggestion → priorité à Moriarty
        - Si Watson détecte contradiction → retour à Sherlock
        - Si Moriarty révèle information cruciale → priorité à Watson
        """
        # Pour Phase 1, on retourne l'agent par défaut
        # Cette méthode sera étoffée en Phase 2
        return default_agent
    
    def reset(self) -> None:
        """Remet à zéro la stratégie de sélection."""
        self.current_index = 0
        self.turn_count = 0
        self._logger.info("Stratégie de sélection cyclique remise à zéro")


class OracleTerminationStrategy(TerminationStrategy):
    """
    Stratégie de terminaison adaptée au workflow avec Oracle.
    
    Critères de terminaison:
    1. Solution correcte proposée ET validée par Oracle
    2. Toutes les cartes révélées (solution par élimination)
    3. Consensus des 3 agents sur une solution (futur)
    4. Timeout (max_turns atteint)
    """
    
    max_turns: int = Field(default=15)  # Plus de tours pour 3 agents
    max_cycles: int = Field(default=5)  # 5 cycles de 3 agents
    turn_count: int = Field(default=0, exclude=True)
    cycle_count: int = Field(default=0, exclude=True)
    is_solution_found: bool = Field(default=False, exclude=True)
    oracle_state: CluedoOracleState = Field(default=None)
    
    def __init__(self, max_turns: int = 15, max_cycles: int = 5, oracle_state: CluedoOracleState = None, **kwargs):
        super().__init__(**kwargs)
        self.max_turns = max_turns
        self.max_cycles = max_cycles
        self.oracle_state = oracle_state
        self.turn_count = 0
        self.cycle_count = 0
        self.is_solution_found = False
        
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def should_terminate(self, agent: Agent, history: List[ChatMessageContent]) -> bool:
        """
        Détermine si le workflow doit se terminer selon les critères Oracle.
        
        Args:
            agent: Agent actuel
            history: Historique des messages
            
        Returns:
            True si le workflow doit se terminer
        """
        # Comptage des tours et cycles
        self.turn_count += 1
        if agent.name == "Sherlock":  # Début d'un nouveau cycle
            self.cycle_count += 1
            self._logger.info(f"\n--- CYCLE {self.cycle_count}/{self.max_cycles} - TOUR {self.turn_count}/{self.max_turns} ---")
        
        # Critère 1: Solution proposée et correcte
        if self._check_solution_found():
            self.is_solution_found = True
            self._logger.info("[OK] Solution correcte trouvée et validée. Terminaison.")
            return True
        
        # Critère 2: Solution par élimination complète
        if self._check_elimination_complete():
            self._logger.info("[OK] Toutes les cartes révélées - solution par élimination possible. Terminaison.")
            return True
        
        # Critère 3: Timeout par nombre de tours
        if self.turn_count >= self.max_turns:
            self._logger.info(f"⏰ Nombre maximum de tours atteint ({self.max_turns}). Terminaison.")
            return True
        
        # Critère 4: Timeout par nombre de cycles
        if self.cycle_count >= self.max_cycles:
            self._logger.info(f"⏰ Nombre maximum de cycles atteint ({self.max_cycles}). Terminaison.")
            return True
        
        return False
    
    def _check_solution_found(self) -> bool:
        """Vérifie si une solution correcte a été proposée."""
        if not self.oracle_state or not self.oracle_state.is_solution_proposed:
            return False
        
        solution_proposee = self.oracle_state.final_solution
        solution_correcte = self.oracle_state.get_solution_secrete()
        
        if solution_proposee == solution_correcte:
            self._logger.info(f"Solution correcte: {solution_proposee}")
            return True
        
        self._logger.info(f"Solution incorrecte: {solution_proposee} ≠ {solution_correcte}")
        return False
    
    def _check_elimination_complete(self) -> bool:
        """Vérifie si toutes les cartes non-secrètes ont été révélées."""
        if not self.oracle_state:
            return False
        
        return self.oracle_state.is_game_solvable_by_elimination()
    
    def get_termination_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des conditions de terminaison."""
        return {
            "turn_count": self.turn_count,
            "cycle_count": self.cycle_count,
            "max_turns": self.max_turns,
            "max_cycles": self.max_cycles,
            "is_solution_found": self.is_solution_found,
            "solution_proposed": self.oracle_state.is_solution_proposed if self.oracle_state else False,
            "elimination_possible": self._check_elimination_complete()
        }


async def oracle_logging_filter(context: KernelFunctionContext, next):
    """Filtre de logging spécialisé pour les interactions Oracle."""
    agent_name = getattr(context, 'agent_name', 'Unknown')
    
    # Logging spécial pour les outils Oracle
    if context.function.plugin_name and "oracle" in context.function.plugin_name.lower():
        logger.info(f"🔮 [ORACLE] {agent_name} → {context.function.plugin_name}.{context.function.name}")
        logger.info(f"🔮 [ORACLE] Arguments: {context.arguments}")
    else:
        logger.info(f"[{agent_name}] Appel: {context.function.plugin_name}.{context.function.name}")
    
    await next(context)
    
    # Logging des révélations Oracle
    if context.result and "révèle" in str(context.result).lower():
        logger.info(f"💎 [RÉVÉLATION] {context.result}")
    elif context.function.plugin_name and "oracle" in context.function.plugin_name.lower():
        logger.info(f"🔮 [ORACLE RESULT] {context.result}")


class CluedoExtendedOrchestrator:
    """
    Orchestrateur pour workflow Cluedo étendu avec 3 agents.
    
    Gère l'orchestration complète Sherlock → Watson → Moriarty avec:
    - Sélection cyclique des agents
    - Intégration du système Oracle
    - Terminaison avancée avec critères Oracle
    - Métriques de performance 3-agents
    """
    
    MAX_HISTORY_MESSAGES: int = 10

    def __init__(self,
                 kernel: Kernel,
                 settings: AppSettings,
                 max_turns: int = 15,
                 max_cycles: int = 5,
                 oracle_strategy: str = "balanced",
                 adaptive_selection: bool = False):
        """
        Initialise l'orchestrateur étendu.
        
        Args:
            kernel: Kernel Semantic Kernel
            settings: Instance de AppSettings pour la configuration.
            max_turns: Nombre maximum de tours total
            max_cycles: Nombre maximum de cycles (3 agents par cycle)
            oracle_strategy: Stratégie Oracle ("cooperative", "competitive", "balanced", "progressive")
            adaptive_selection: Active la sélection adaptative (Phase 2)
        """
        self.kernel = kernel
        self.settings = settings
        self.max_turns = max_turns
        self.max_cycles = max_cycles
        self.oracle_strategy = oracle_strategy
        self.adaptive_selection = adaptive_selection
        
        # État et agents (initialisés lors de l'exécution)
        self.oracle_state: Optional[CluedoOracleState] = None
        self.sherlock_agent: Optional[SherlockEnqueteAgent] = None
        self.watson_agent: Optional[WatsonLogicAssistant] = None
        self.moriarty_agent: Optional[MoriartyInterrogatorAgent] = None
        self.orchestration: Optional[GroupChatOrchestration] = None
        # self.runtime: Optional[InProcessRuntime] = None  # Module non disponible
        
        # Métriques de performance
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.execution_metrics: Dict[str, Any] = {}
        
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def setup_workflow(self,
                           nom_enquete: str = "Le Mystère du Manoir Tudor",
                           elements_jeu: Optional[Dict[str, List[str]]] = None) -> CluedoOracleState:
        """
        Configure le workflow 3-agents avec état Oracle.
        
        Args:
            nom_enquete: Nom de l'enquête
            elements_jeu: Éléments du jeu Cluedo (optionnel)
            
        Returns:
            État Oracle configuré
        """
        self._logger.info(f"Configuration du workflow 3-agents - Stratégie: {self.oracle_strategy}")
        
        # Configuration des éléments par défaut
        if elements_jeu is None:
            elements_jeu = {
                "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
                "armes": ["Poignard", "Chandelier", "Revolver"],
                "lieux": ["Salon", "Cuisine", "Bureau"]
            }
        
        # Création de l'état Oracle étendu
        self.oracle_state = CluedoOracleState(
            nom_enquete_cluedo=nom_enquete,
            elements_jeu_cluedo=elements_jeu,
            description_cas="Un meurtre a été commis dans le manoir. Qui, où, et avec quoi ?",
            initial_context="L'enquête débute avec 3 enquêteurs spécialisés.",
            oracle_strategy=self.oracle_strategy
        )
        
        # Configuration du plugin d'état étendu
        state_plugin = EnqueteStateManagerPlugin(self.oracle_state)
        self.kernel.add_plugin(state_plugin, "EnqueteStatePlugin")
        # self.kernel.add_filter(FilterTypes.FUNCTION_INVOCATION, oracle_logging_filter)
        # Note: add_filter API n'est pas disponible dans semantic-kernel 0.9.6b1
        
        # Préparation des constantes pour Watson
        all_constants = [name.replace(" ", "") for category in elements_jeu.values() for name in category]

        # Création du DatasetManager pour Moriarty
        from ..agents.core.oracle.dataset_access_manager import CluedoDatasetManager
        dataset_manager = CluedoDatasetManager(self.oracle_state.cluedo_dataset)
        
        # Création des agents
        from ..agents.factory import AgentFactory
        factory = AgentFactory(self.kernel, self.kernel.get_service(None).service_id)
        self.sherlock_agent = factory.create_sherlock_agent(agent_name="Sherlock")
        self.watson_agent = factory.create_watson_agent(agent_name="Watson")
        self.moriarty_agent = MoriartyInterrogatorAgent(
            kernel=self.kernel,
            dataset_manager=dataset_manager,
            game_strategy=self.oracle_strategy,
            agent_name="Moriarty"
        )
        
        # Configuration des stratégies
        agents = [self.sherlock_agent, self.watson_agent, self.moriarty_agent]
        selection_strategy = CyclicSelectionStrategy(agents, self.adaptive_selection, self.oracle_state)  # PHASE C: Passer oracle_state
        termination_strategy = OracleTerminationStrategy(
            max_turns=self.max_turns,
            max_cycles=self.max_cycles,
            oracle_state=self.oracle_state
        )
        
        # Création de l'orchestration avec GroupChatOrchestration (système original qui fonctionne)
        self.orchestration = GroupChatOrchestration()
        
        # Configuration des agents
        agent_dict = {getattr(agent, 'name', getattr(agent, 'id', str(agent))): agent for agent in agents}
        session_id = f"cluedo_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.orchestration.initialize_session(session_id, agent_dict)
        
        # Stocker les stratégies pour usage ultérieur
        self.selection_strategy = selection_strategy
        self.termination_strategy = termination_strategy
        
        # # Initialisation du runtime - Module non disponible
        # self.runtime = InProcessRuntime()
        # self.runtime.start()
        
        self._logger.info(f"Workflow configuré avec {len(agents)} agents")
        self._logger.info(f"Solution secrète: {self.oracle_state.get_solution_secrete()}")
        self._logger.info(f"Cartes Moriarty: {self.oracle_state.get_moriarty_cards()}")
        
        return self.oracle_state
    
    async def execute_workflow(self, initial_question: str = "L'enquête commence. Sherlock, menez l'investigation !") -> Dict[str, Any]:
        """
        Exécute le workflow complet avec les 3 agents.
        
        Args:
            initial_question: Question/instruction initiale
            
        Returns:
            Résultat complet du workflow avec métriques
        """
        if not self.orchestration or not self.oracle_state:
            raise ValueError("Workflow non configuré. Appelez setup_workflow() d'abord.")
        
        self.start_time = datetime.now()
        self._logger.info("Début du workflow 3-agents")
        
        # Historique des messages
        history: List[ChatMessageContent] = [
            ChatMessageContent(role="user", content=initial_question, name="System")
        ]
        
        # Boucle principale d'orchestration
        self._logger.info("Début de la boucle d'orchestration 3-agents...")
        
        try:
            fake_initial_agent = self.sherlock_agent
            while not await self.termination_strategy.should_terminate(agent=fake_initial_agent, history=history):

                next_agent = await self.selection_strategy.next(agents=list(self.orchestration.active_agents.values()), history=history)
                fake_initial_agent = next_agent
                
                self._logger.info(f"--- Tour de {next_agent.name} ---")
                
                # 1. Tronquer et nettoyer l'historique avant de l'envoyer
                if len(history) > self.MAX_HISTORY_MESSAGES:
                    self._logger.warning(f"L'historique dépasse {self.MAX_HISTORY_MESSAGES} messages. Troncation...")
                    history_to_process = [history[0]] + history[-(self.MAX_HISTORY_MESSAGES - 1):]
                else:
                    history_to_process = history

                # Étape de nettoyage la plus critique:
                # Reconstruire un historique entièrement neuf avec des objets simples.
                history_to_send = [
                    self.consolidate_agent_response(msg, getattr(msg, 'name', msg.role))
                    for msg in history_to_process
                ]

                # 2. Exécuter l'agent avec l'historique nettoyé
                agent_response_stream = next_agent.invoke(input=history_to_send, arguments=KernelArguments())

                # Gérer les réponses streamées et non-streamées (mock)
                from inspect import isawaitable
                if hasattr(agent_response_stream, '__aiter__'):
                    agent_response_raw = [message async for message in agent_response_stream]
                elif isawaitable(agent_response_stream):
                    agent_response_raw = await agent_response_stream
                else:
                    agent_response_raw = agent_response_stream
                
                # 3. Consolider et nettoyer la réponse de l'agent
                # C'est une étape CRUCIALE pour éviter le context overflow avec les réponses en streaming.
                clean_message = self.consolidate_agent_response(agent_response_raw, next_agent.name)
                
                # 4. Mettre à jour l'historique avec le message propre
                history.append(clean_message)
                last_message_content = str(clean_message.content)

                # 5. Log et mise à jour de l'état
                self._logger.info(f"Réponse de {next_agent.name}: {last_message_content[:150]}...")
                self.oracle_state.add_conversation_message(
                    agent_name=next_agent.name,
                    content=last_message_content,
                    message_type=self._detect_message_type(last_message_content)
                )
                
                turn_input = history[-2].content if len(history) > 1 else initial_question
                self.oracle_state.record_agent_turn(
                    agent_name=next_agent.name,
                    action_type="invoke_with_history",
                    action_details={"input": str(turn_input)[:150], "output": last_message_content[:150]}
                )

                # CORRECTIF ORACLE: Réintroduction de l'interception des suggestions
                if next_agent.name != "Moriarty":
                    suggestion = self._extract_cluedo_suggestion(last_message_content)
                    if suggestion:
                        self._logger.info(f"SUGGESTION DÉTECTÉE: {suggestion} par {next_agent.name}")
                        oracle_response = await self._force_moriarty_oracle_revelation(
                            suggestion=suggestion,
                            suggesting_agent=next_agent.name
                        )
                        if oracle_response:
                            oracle_message = self.consolidate_agent_response(oracle_response.get("content"), "Moriarty")
                            history.append(oracle_message)
                            self._logger.info(f"[Moriarty Oracle Auto-Reveal]: {oracle_response.get('content')[:100]}...")
                            self.oracle_state.add_conversation_message(
                                agent_name="Moriarty",
                                content=str(oracle_message.content),
                                message_type="revelation"
                            )


        except Exception as e:
            self._logger.error(f"Erreur durant l'orchestration: {e}", exc_info=True)
            raise
        
        finally:
            self.end_time = datetime.now()
        
        workflow_result = await self._collect_final_metrics(history)
        
        self._logger.info("[OK] Workflow 3-agents terminé")
        return workflow_result
    
    def consolidate_agent_response(self, response_raw: Any, agent_name: str) -> ChatMessageContent:
        """
        Consolide la réponse brute d'un agent (qui peut être un string, un objet complexe,
        un stream, etc.) en un unique ChatMessageContent simple (rôle, contenu texte, nom).
        Ceci est LA fonction critique pour éviter le context_length_exceeded.
        """
        full_content = ""
        role = "assistant"
        
        # Cas 1: La réponse est une liste de chunks de streaming
        if isinstance(response_raw, list):
            for chunk in response_raw:
                if isinstance(chunk, StreamingChatMessageContent):
                    for part in chunk.items:
                        if hasattr(part, 'text'):
                            full_content += part.text
                # Gérer le cas où un ChatMessageContent se retrouve dans la liste
                elif isinstance(chunk, ChatMessageContent):
                     full_content += str(chunk.content or "")

        # Cas 2: La réponse est un objet de streaming unique
        elif isinstance(response_raw, StreamingChatMessageContent):
            for part in response_raw.items:
                if hasattr(part, 'text'):
                    full_content += part.text

        # Cas 3: C'est déjà un ChatMessageContent (potentiellement avec un contenu complexe)
        elif isinstance(response_raw, ChatMessageContent):
            # Extraire le contenu texte, peu importe comment il est encapsulé
            content_obj = response_raw.content
            if hasattr(content_obj, 'text'):
                full_content = content_obj.text
            elif isinstance(content_obj, str):
                full_content = content_obj
            else:
                full_content = str(content_obj or "")
            role = response_raw.role

        # Cas 4: C'est juste un string ou un autre type de base
        else:
            full_content = str(response_raw or "")

        return ChatMessageContent(role=role, content=full_content, name=agent_name)


    async def _collect_final_metrics(self, history: List[ChatMessageContent]) -> Dict[str, Any]:
        """Collecte les métriques finales du workflow."""
        execution_time = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
        
        # Statistiques de base
        conversation_history = [
            {"sender": getattr(msg, 'name', getattr(msg, 'role', str(getattr(msg, 'author', 'Unknown')))),
             "message": str(getattr(msg, 'content', msg))}
            for msg in history if getattr(msg, 'name', getattr(msg, 'role', getattr(msg, 'author', ''))) != "System"
        ]
        
        # Métriques Oracle
        oracle_stats = self.oracle_state.get_oracle_statistics()
        
        # PHASE C: Métriques de fluidité et continuité narrative
        fluidity_metrics = self.oracle_state.get_fluidity_metrics()
        
        # Évaluation du succès
        solution_correcte = self._evaluate_solution_success()
        
        # Métriques de performance comparatives
        performance_metrics = self._calculate_performance_metrics(oracle_stats, execution_time)
        
        return {
            "workflow_info": {
                "strategy": self.oracle_strategy,
                "max_turns": self.max_turns,
                "max_cycles": self.max_cycles,
                "execution_time_seconds": execution_time,
                "timestamp": self.end_time.isoformat() if self.end_time else None
            },
            "solution_analysis": solution_correcte,
            "conversation_history": conversation_history,
            "oracle_statistics": oracle_stats,
            "performance_metrics": performance_metrics,
            "phase_c_fluidity_metrics": fluidity_metrics,  # PHASE C: Nouvelles métriques
            "final_state": {
                "solution_proposed": self.oracle_state.is_solution_proposed,
                "final_solution": self.oracle_state.final_solution,
                "secret_solution": self.oracle_state.get_solution_secrete(),
                "game_solvable_by_elimination": self.oracle_state.is_game_solvable_by_elimination()
            }
        }
    
    def _evaluate_solution_success(self) -> Dict[str, Any]:
        """Évalue le succès de la résolution."""
        if not self.oracle_state.is_solution_proposed:
            return {
                "success": False,
                "reason": "Aucune solution proposée",
                "proposed_solution": None,
                "correct_solution": self.oracle_state.get_solution_secrete()
            }
        
        proposed = self.oracle_state.final_solution
        correct = self.oracle_state.get_solution_secrete()
        
        success = proposed == correct
        
        return {
            "success": success,
            "reason": "Solution correcte" if success else "Solution incorrecte",
            "proposed_solution": proposed,
            "correct_solution": correct,
            "partial_matches": {
                "suspect": proposed.get("suspect") == correct.get("suspect"),
                "arme": proposed.get("arme") == correct.get("arme"),  
                "lieu": proposed.get("lieu") == correct.get("lieu")
            } if proposed and correct else {}
        }
    
    def _calculate_performance_metrics(self, oracle_stats: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Calcule les métriques de performance du workflow 3-agents."""
        agent_interactions = oracle_stats.get("agent_interactions", {})
        
        return {
            "efficiency": {
                "turns_per_minute": agent_interactions.get("total_turns", 0) / (execution_time / 60) if execution_time > 0 else 0,
                "oracle_queries_per_turn": oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 0) / max(1, agent_interactions.get("total_turns", 1)),
                "cards_revealed_per_query": oracle_stats.get("workflow_metrics", {}).get("cards_revealed", 0) / max(1, oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 1))
            },
            "collaboration": {
                "oracle_utilization_rate": oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 0) / max(1, agent_interactions.get("total_turns", 1)),
                "information_sharing_efficiency": len(oracle_stats.get("recent_revelations", [])),
                "agent_balance": self._calculate_agent_balance(agent_interactions)
            },
            "comparison_2vs3_agents": {
                "estimated_2agent_turns": agent_interactions.get("total_turns", 0) * 1.5,  # Estimation
                "efficiency_gain": "15-25% reduction in turns (estimated)",
                "information_richness": f"+{oracle_stats.get('workflow_metrics', {}).get('cards_revealed', 0)} cards revealed"
            }
        }
    
    def _calculate_agent_balance(self, agent_interactions: Dict[str, Any]) -> Dict[str, float]:
        """Calcule l'équilibre de participation entre agents."""
        total_turns = agent_interactions.get("total_turns", 0)
        if total_turns == 0:
            return {"sherlock": 0.0, "watson": 0.0, "moriarty": 0.0}
        
        # Estimation basée sur le pattern cyclique (1/3 chacun idéalement)
        expected_per_agent = total_turns / 3
        
        return {
            "expected_turns_per_agent": expected_per_agent,
            "balance_score": 1.0,  # À améliorer avec tracking réel par agent
            "note": "Équilibre cyclique théorique - à améliorer avec métriques réelles"
        }
    
    # PHASE C: Méthodes d'analyse contextuelle pour fluidité
    
    def _detect_message_type(self, content: str) -> str:
        """
        Détecte le type de message basé sur son contenu.
        
        Args:
            content: Contenu du message
            
        Returns:
            Type de message détecté
        """
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ["révèle", "possède", "carte", "j'ai"]):
            return "revelation"
        elif any(keyword in content_lower for keyword in ["suggère", "propose", "suspect", "arme", "lieu"]):
            return "suggestion"
        elif any(keyword in content_lower for keyword in ["analyse", "déduction", "conclusion", "donc"]):
            return "analysis"
        elif any(keyword in content_lower for keyword in ["brillant", "exactement", "aha", "intéressant", "magistral"]):
            return "reaction"
        else:
            return "message"
    
    def _analyze_contextual_elements(self, agent_name: str, content: str, history: List) -> None:
        """
        Analyse les éléments contextuels d'un message et enregistre les références/réactions.
        
        Args:
            agent_name: Nom de l'agent qui parle
            content: Contenu du message
            history: Historique des messages
        """
        content_lower = content.lower()
        
        # Détection des références contextuelles explicites
        reference_indicators = [
            ("suite à", "building_on"),
            ("en réaction à", "reacting_to"),
            ("après cette", "responding_to"),
            ("comme dit", "referencing"),
            ("précédemment", "referencing")
        ]
        
        for indicator, ref_type in reference_indicators:
            if indicator in content_lower:
                # Trouve le message précédent le plus proche
                if len(history) > 1:
                    target_turn = len(history) - 1  # Message précédent
                    self.oracle_state.record_contextual_reference(
                        source_agent=agent_name,
                        target_message_turn=target_turn,
                        reference_type=ref_type,
                        reference_content=indicator
                    )
                break
        
        # Détection des réactions émotionnelles
        emotional_patterns = self._detect_emotional_reactions(agent_name, content, history)
        for reaction in emotional_patterns:
            self.oracle_state.record_emotional_reaction(**reaction)
    
    def _detect_emotional_reactions(self, agent_name: str, content: str, history: List) -> List[Dict[str, str]]:
        """
        Détecte les réactions émotionnelles spécifiques à chaque agent.
        
        Args:
            agent_name: Nom de l'agent
            content: Contenu du message
            history: Historique des messages
            
        Returns:
            Liste des réactions détectées
        """
        reactions = []
        content_lower = content.lower()
        
        # Pour l'instant, retourne une liste vide - à implémenter si nécessaire
        return reactions
        
# CORRECTIF ORACLE: Méthodes pour détection et révélation automatique
    
    def _extract_cluedo_suggestion(self, message_content: str) -> Optional[Dict[str, str]]:
        """
        Extrait une suggestion Cluedo d'un message (suspect, arme, lieu).
        
        Args:
            message_content: Contenu du message à analyser
            
        Returns:
            Dict avec suspect/arme/lieu ou None si pas de suggestion détectée
        """
        content_lower = message_content.lower()
        
        # Mots-clés indiquant une suggestion
        suggestion_keywords = ['suggère', 'propose', 'accuse', 'pense que', 'suspect', 'suppose']
        if not any(keyword in content_lower for keyword in suggestion_keywords):
            return None
        
        # Listes des éléments Cluedo (en minuscules pour matching)
        suspects = ["colonel moutarde", "professeur violet", "mademoiselle rose", "docteur orchidée"]
        armes = ["poignard", "chandelier", "revolver", "corde"]
        lieux = ["salon", "cuisine", "bureau", "bibliothèque"]
        
        # Recherche d'éléments dans le message
        found_suspect = None
        found_arme = None
        found_lieu = None
        
        for suspect in suspects:
            if suspect in content_lower:
                found_suspect = suspect.title()
                break
        
        for arme in armes:
            if arme in content_lower:
                found_arme = arme.title()
                break
        
        for lieu in lieux:
            if lieu in content_lower:
                found_lieu = lieu.title()
                break
        
        # Suggestion valide seulement si au moins 2 éléments trouvés
        if sum(x is not None for x in [found_suspect, found_arme, found_lieu]) >= 2:
            return {
                "suspect": found_suspect or "Indéterminé",
                "arme": found_arme or "Indéterminée", 
                "lieu": found_lieu or "Indéterminé"
            }
        
        return None
    
    async def _force_moriarty_oracle_revelation(self, suggestion: Dict[str, str], suggesting_agent: str) -> Optional[Dict[str, Any]]:
        """
        Force Moriarty à révéler ses cartes pour une suggestion donnée.
        
        Args:
            suggestion: Dict avec suspect/arme/lieu
            suggesting_agent: Nom de l'agent qui fait la suggestion
            
        Returns:
            Réponse Oracle de Moriarty ou None si erreur
        """
        try:
            self._logger.info(f"Force Oracle révélation: {suggestion} par {suggesting_agent}")
            
            # Appel direct à Moriarty pour validation Oracle
            oracle_result = self.moriarty_agent.validate_suggestion_cluedo(
                suspect=suggestion.get('suspect', ''),
                arme=suggestion.get('arme', ''),
                lieu=suggestion.get('lieu', ''),
                suggesting_agent=suggesting_agent
            )
            
            # Construction de la réponse théâtrale selon le résultat
            if oracle_result.authorized and oracle_result.data and oracle_result.data.can_refute:
                # Moriarty peut réfuter - révèle ses cartes
                revealed_cards = oracle_result.revealed_information or []
                
                moriarty_responses = [
                    f"*sourire énigmatique* Ah, {suggesting_agent}... Je possède {', '.join(revealed_cards)} ! Votre théorie s'effondre.",
                    f"*regard perçant* Hélas... {', '.join(revealed_cards)} repose dans ma main. Réfléchissez encore.",
                    f"Tiens, tiens... {', '.join(revealed_cards)} me permet de contrarier vos plans, {suggesting_agent}.",
                    f"*applaudit* Magnifique tentative ! Mais j'ai {', '.join(revealed_cards)}. Continuez à chercher."
                ]
                
                content = moriarty_responses[len(revealed_cards) % len(moriarty_responses)]
                
                return {
                    "content": content,
                    "type": "oracle_revelation",
                    "revealed_cards": revealed_cards,
                    "can_refute": True,
                    "suggestion": suggestion
                }
            else:
                # Moriarty ne peut pas réfuter - suggestion potentiellement correcte
                warning_responses = [
                    f"*silence inquiétant* Intéressant, {suggesting_agent}... Je ne peux rien révéler sur cette suggestion.",
                    f"*sourire mystérieux* Voilà qui est... troublant. Aucune carte à révéler, {suggesting_agent}.",
                    f"*regard intense* Cette combinaison me laisse sans réponse... Serait-ce la vérité ?",
                    f"Ah... *pause dramatique* Vous touchez peut-être au but, {suggesting_agent}."
                ]
                
                content = warning_responses[0]  # Première réponse par défaut
                
                return {
                    "content": content,
                    "type": "oracle_no_refutation",
                    "revealed_cards": [],
                    "can_refute": False,
                    "suggestion": suggestion,
                    "warning": "Suggestion potentiellement correcte"
                }
                
        except Exception as e:
            self._logger.error(f"❌ Erreur Oracle révélation: {e}", exc_info=True)
            
            # Réponse d'erreur théâtrale
            error_content = f"*confusion momentanée* Pardonnez-moi, {suggesting_agent}... Un mystère technique m'empêche de répondre."
            
            return {
                "content": error_content,
                "type": "oracle_error",
                "revealed_cards": [],
                "can_refute": False,
                "error": str(e)
            }
        # Trouver l'agent et le contenu qui ont déclenché la réaction
        trigger_agent = None
        trigger_content = ""
        
        if len(history) > 1:
            last_message = history[-2]  # Message précédent (avant le message actuel)
            trigger_agent = last_message.name
            trigger_content = str(last_message.content)
        
        if not trigger_agent or trigger_agent == "System":
            return reactions
        
        # Patterns de réaction spécifiques par agent
        if agent_name == "Watson":
            watson_reactions = [
                (["brillant", "exactement", "ça colle parfaitement"], "approval"),
                (["aha", "intéressant retournement", "ça change la donne"], "surprise"),
                (["précisément", "logique", "cohérent"], "analysis")
            ]
            
            for keywords, reaction_type in watson_reactions:
                if any(keyword in content_lower for keyword in keywords):
                    reactions.append({
                        "agent_name": agent_name,
                        "trigger_agent": trigger_agent,
                        "trigger_content": trigger_content,
                        "reaction_type": reaction_type,
                        "reaction_content": content[:100]
                    })
                    break
        
        elif agent_name == "Sherlock":
            sherlock_reactions = [
                (["précisément watson", "tu vises juste", "c'est noté"], "approval"),
                (["comme prévu", "merci pour cette clarification", "parfait"], "satisfaction"),
                (["intéressant", "fascinant", "remarquable"], "analysis")
            ]
            
            for keywords, reaction_type in sherlock_reactions:
                if any(keyword in content_lower for keyword in keywords):
                    reactions.append({
                        "agent_name": agent_name,
                        "trigger_agent": trigger_agent,
                        "trigger_content": trigger_content,
                        "reaction_type": reaction_type,
                        "reaction_content": content[:100]
                    })
                    break
        
        elif agent_name == "Moriarty":
            moriarty_reactions = [
                (["chaud", "très chaud", "vous brûlez"], "encouragement"),
                (["pas tout à fait", "pas si vite"], "correction"),
                (["magistral", "vous m'impressionnez", "bien joué"], "excitement"),
                (["hmm", "attendez"], "suspense")
            ]
            
            for keywords, reaction_type in moriarty_reactions:
                if any(keyword in content_lower for keyword in keywords):
                    reactions.append({
                        "agent_name": agent_name,
                        "trigger_agent": trigger_agent,
                        "trigger_content": trigger_content,
                        "reaction_type": reaction_type,
                        "reaction_content": content[:100]
                    })
                    break
        
        return reactions


async def run_cluedo_oracle_game(
    kernel: Kernel,
    initial_question: str = "L'enquête commence. Sherlock, menez l'investigation !",
    max_turns: int = 15,
    max_cycles: int = 5,
    oracle_strategy: str = "balanced"
) -> Dict[str, Any]:
    """
    Interface simplifiée pour exécuter une partie Cluedo avec Oracle.
    
    Args:
        kernel: Kernel Semantic Kernel configuré
        initial_question: Question initiale
        max_turns: Nombre maximum de tours
        max_cycles: Nombre maximum de cycles
        oracle_strategy: Stratégie Oracle
        
    Returns:
        Résultat complet du workflow
    """
    orchestrator = CluedoExtendedOrchestrator(
        kernel=kernel,
        max_turns=max_turns,
        max_cycles=max_cycles,
        oracle_strategy=oracle_strategy
    )
    
    await orchestrator.setup_workflow()
    return await orchestrator.execute_workflow(initial_question)


async def main():
    """Point d'entrée pour exécuter le workflow 3-agents de manière autonome."""
    kernel = Kernel()
    
    # --- DEBUT BLOC DE CORRECTION ---
    # Ajout de la configuration du service LLM, comme dans cluedo_orchestrator.py
    from argumentation_analysis.config.settings import settings
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    if not settings.use_mock_llm and settings.openai.api_key:
        kernel.add_service(
            OpenAIChatCompletion(
                service_id=settings.openai.chat_model_id,
                ai_model_id=settings.openai.chat_model_id,
                api_key=settings.openai.api_key.get_secret_value(),
            )
        )
    # --- FIN BLOC DE CORRECTION ---
    
    try:
        result = await run_cluedo_oracle_game(
            kernel=kernel,
            oracle_strategy="balanced",
            max_cycles=5
        )
        
        print("\n" + "="*60)
        print("RÉSULTAT WORKFLOW 3-AGENTS CLUEDO ORACLE")
        print("="*60)
        
        print(f"\n🎯 SUCCÈS: {result['solution_analysis']['success']}")
        print(f"📊 TOURS: {result['oracle_statistics']['agent_interactions']['total_turns']}")
        print(f"🔮 REQUÊTES ORACLE: {result['oracle_statistics']['workflow_metrics']['oracle_interactions']}")
        print(f"💎 CARTES RÉVÉLÉES: {result['oracle_statistics']['workflow_metrics']['cards_revealed']}")
        print(f"⏱️  TEMPS: {result['workflow_info']['execution_time_seconds']:.2f}s")
        
        if result['solution_analysis']['success']:
            print(f"[OK] Solution: {result['final_state']['final_solution']}")
        else:
            print(f"❌ Solution proposée: {result['final_state']['final_solution']}")
            print(f"🎯 Solution correcte: {result['final_state']['secret_solution']}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ Erreur durant l'exécution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

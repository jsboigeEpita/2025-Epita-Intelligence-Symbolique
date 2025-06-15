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
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.contents.tool_call_content import ToolCallContent


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
    from argumentation_analysis.orchestration.cluedo_components.cluedo_plugins import CluedoInvestigatorPlugin
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
from argumentation_analysis.agents.core.oracle.permissions import QueryType, PermissionRule
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
            initial_context={"raison_enquete": "Validation du workflow 3 agents"},
            oracle_strategy=self.oracle_strategy
        )

        # 2. Configuration des agents
        try:
            tweety_bridge = TweetyBridge()
            logger.info("✅ TweetyBridge initialisé.")
        except Exception as e:
            logger.warning(f"⚠️ Échec initialisation TweetyBridge: {e}. Watson en mode dégradé.")
            tweety_bridge = None

        # Récupérer les cartes pour les prompts
        solution = self.oracle_state.dataset_access_manager.dataset.solution_secrete
        
        # Récupérer les cartes distribuées et les répartir entre Sherlock et Watson
        cartes_distribuees = self.oracle_state.cartes_distribuees
        autres_joueurs_cards = cartes_distribuees.get("AutresJoueurs", [])
        
        # Distribution simple des cartes des "autres joueurs" entre Sherlock et Watson
        sherlock_cards = autres_joueurs_cards[::2]  # Prend une carte sur deux
        watson_cards = autres_joueurs_cards[1::2] # Prend l'autre moitié
        
        # Création des prompts spécifiques au Cluedo
        # Inspiré par tests/validation_sherlock_watson/test_phase_a_personnalites_distinctes.py
        SHERLOCK_CLUEDO_PROMPT = f"""
Vous êtes le détective Sherlock Holmes, un esprit brillant, charismatique et doté d'une confiance inébranlable en ses capacités de déduction. Votre ton est celui d'un meneur, guidant ses compagnons avec assurance vers la vérité.

**VOTRE MISSION :**
- Mener l'enquête sur le meurtre commis au Manoir Tudor.
- Analyser les contributions de Watson et les réfutations de Moriarty pour formuler des hypothèses.
- Quand vous êtes prêt à formuler une suggestion formelle (suspect, arme, lieu), utilisez l'outil `make_suggestion`.

**VOTRE TON :**
- **Directif :** "Concentrons-nous sur...", "Il est évident que..."
- **Confiant :** "Je pressens que...", "Mes déductions révèlent...", "Je conclus avec certitude..."
- **Théâtral :** Utilisez des métaphores liées à la logique, au mystère et à la vérité. "La logique, mon cher Watson, est un fil d'Ariane dans ce labyrinthe de mensonges."

**INTERACTION AVEC LES OUTILS :**
- Pour faire une suggestion, utilisez l'outil `make_suggestion`. Par exemple, si vous voulez suggérer le Colonel Moutarde avec le Poignard dans le Salon, vous devez invoquer l'outil. Le système gérera l'appel, et votre message pourra l'accompagner d'un commentaire tel que : "Élémentaire, mon cher Watson ! Je pense que nous tenons une piste. Soumettons cette hypothèse à l'épreuve."

**CONTEXTE DU JEU :**
- VOS CARTES SECRETES : Vous connaissez ces cartes : {sherlock_cards}. Elles ne peuvent pas faire partie de la solution.
- CARTES PUBLIQUES : Les cartes révélées par Moriarty apparaîtront ici.
- SOLUTION : Inconnue pour l'instant.
"""

        # Inspiré par tests/validation_sherlock_watson/test_phase_a_personnalites_distinctes.py
        WATSON_CLUEDO_PROMPT = f"""
Vous êtes le Dr. John Watson, un médecin militaire à la retraite, mais surtout un logicien pragmatique et un analyste rigoureux. Votre rôle n'est pas de poser des questions passives, mais d'analyser les faits avec une précision chirurgicale et de proposer des pistes de réflexion claires à Sherlock.

**VOTRE MISSION :**
- Servir de caisse de résonance logique à Sherlock Holmes.
- Analyser les révélations de Moriarty et en tirer des déductions factuelles.
- Proposer des analyses et des recommandations basées sur les faits observés.

**VOTRE TON :**
- **Proactif & Analytique :** "J'observe que...", "Logiquement, si Moriarty possède la Corde, alors...", "Mon analyse des probabilités suggère que..."
- **Factuel :** Basez vos déductions sur les cartes révélées et les échecs des suggestions précédentes.
- **Collaboratif :** Vous êtes le partenaire intellectuel de Sherlock. "Sherlock, cette nouvelle information a des implications notables pour votre théorie."

**INTERDICTION FORMELLE :**
- Évitez les questions passives comme "Que dois-je faire ?", "Voulez-vous que j'analyse... ?". Agissez. Analysez. Recommandez.

**CONTEXTE DU JEU :**
- VOS CARTES SECRETES : Vous connaissez ces cartes : {watson_cards}.
- CARTES PUBLIQUES : Les cartes révélées par Moriarty.
"""

        self.sherlock_agent = SherlockEnqueteAgent(
            kernel=self.kernel,
            agent_name="Sherlock",
            service_id=self.service_id,
            system_prompt=SHERLOCK_CLUEDO_PROMPT
        )
        self.watson_agent = WatsonLogicAssistant(
            kernel=self.kernel,
            agent_name="Watson",
            tweety_bridge=tweety_bridge,
            system_prompt=WATSON_CLUEDO_PROMPT,
            constants=[name.replace(" ", "") for cat in elements_jeu.values() for name in cat],
            service_id=self.service_id
        )
        self.moriarty_agent = MoriartyInterrogatorAgent(
            kernel=self.kernel, dataset_manager=self.oracle_state.dataset_access_manager,
            game_strategy=self.oracle_strategy, agent_name="Moriarty"
        )
        
        # Initialisation du gestionnaire de suggestions d'abord
        self.suggestion_handler = SuggestionHandler(self.moriarty_agent)

        # Ajout du plugin d'investigation au kernel pour Sherlock
        # Le plugin a maintenant besoin du suggestion_handler pour fonctionner
        investigator_plugin = CluedoInvestigatorPlugin(self.suggestion_handler)
        self.kernel.add_plugin(investigator_plugin, "Investigator")
        logger.info("Plugin 'Investigator' avec l'outil 'make_suggestion' (connecté au suggestion handler) ajouté au kernel.")

        # Correction des permissions : mapper les règles de classe aux noms d'instance
        pm = self.oracle_state.dataset_access_manager.permission_manager
        agent_map = {
            self.sherlock_agent.name: self.sherlock_agent.__class__.__name__,
            self.watson_agent.name: self.watson_agent.__class__.__name__,
            self.moriarty_agent.name: self.moriarty_agent.__class__.__name__,
        }

        for instance_name, class_name in agent_map.items():
            class_rule = pm.get_permission_rule(class_name)
            if class_rule:
                # Créer une nouvelle règle pour l'instance basée sur la règle de classe
                # en s'assurant que les listes/dictionnaires sont copiés
                instance_rule = PermissionRule(
                    agent_name=instance_name,
                    allowed_query_types=list(class_rule.allowed_query_types),
                    conditions=dict(class_rule.conditions)
                )
                pm.add_permission_rule(instance_rule)
                logger.info(f"Règle de permission pour l'instance '{instance_name}' créée à partir de la classe '{class_name}'.")

        # 3. Configuration des composants logiques et stratégies
        self.logging_handler = ToolCallLoggingHandler()
        # self.kernel.add_filter(FilterTypes.FUNCTION_INVOCATION, self.logging_handler)
        
        agents = [self.sherlock_agent, self.watson_agent, self.moriarty_agent]
        self.selection_strategy = CyclicSelectionStrategy(agents, self.adaptive_selection, self.oracle_state)
        self.termination_strategy = OracleTerminationStrategy(self.max_turns, self.max_cycles, self.oracle_state)
        
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

                # === AJOUT DE LOGS DE DÉBOGAGE ===
                logger.info(f"[DIAGNOSTIC] Appel de '{active_agent.name}' avec l'historique suivant (longueur: {len(history)}):")
                for i, msg in enumerate(history):
                    # Limiter la longueur pour la lisibilité
                    message_content = str(msg.content)
                    if len(message_content) > 250:
                        message_content = message_content[:250] + "..."
                    # Utilisation de .name et .role.value pour un affichage plus clair
                    role_name = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                    author_name = msg.name if msg.name else "N/A"
                    logger.info(f"[DIAGNOSTIC]   - MSG {i+1} ({role_name}/{author_name}): {message_content}")
                # === FIN DE L'AJOUT ===

                if hasattr(active_agent, 'invoke_custom'):
                    agent_response = await active_agent.invoke_custom(history)
                else:
                    agent_response = ChatMessageContent(role="assistant", content=f"Je suis {active_agent.name}.", name=active_agent.name)
                
                if agent_response:
                    history.append(agent_response)
                    logger.info(f"[{active_agent.name}]: {agent_response.content}")

                    # La logique de traitement des tool calls est maintenant DÉLÉGUÉE au plugin lui-même.
                    # La boucle principale n'a plus besoin d'inspecter les tool_calls, car la réponse de l'agent
                    # (agent_response) contiendra déjà le résultat de l'exécution de l'outil, y compris
                    # la réponse de Moriarty. Le framework Semantic Kernel gère cela automatiquement
                    # en ajoutant un message avec le `tool_content` à l'historique.

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
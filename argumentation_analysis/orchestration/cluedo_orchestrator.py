import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.kernel import Kernel
from argumentation_analysis.orchestration.base import (
    SelectionStrategy,
    TerminationStrategy,
)
from semantic_kernel.agents import Agent
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions import KernelArguments
from pydantic import Field

# Imports locaux
from .base import Agent, TerminationStrategy
from .cluedo_extended_orchestrator import CyclicSelectionStrategy
from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
    EnqueteStateManagerPlugin,
)
from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration
from argumentation_analysis.agents.factory import AgentFactory
from argumentation_analysis.config.settings import AppSettings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CluedoTerminationStrategy(TerminationStrategy):
    """Stratégie de terminaison personnalisée pour le Cluedo."""

    max_turns: int = Field(default=10)
    turn_count: int = Field(default=0, exclude=True)
    is_solution_found: bool = Field(default=False, exclude=True)
    enquete_plugin: EnqueteStateManagerPlugin = Field(...)

    async def should_terminate(
        self, agent: Agent, history: List[ChatMessageContent]
    ) -> bool:
        """Termine si la solution est trouvée ou si le nombre max de tours est atteint."""
        self.turn_count += 1
        if self.is_solution_found:
            logger.info("Solution trouvée. Terminaison.")
            return True
        if self.turn_count >= self.max_turns:
            logger.info("Nombre maximum de tours atteint. Terminaison.")
            return True
        return False


class CluedoOrchestrator:
    """
    Orchestrateur pour workflow Cluedo de base avec 2 agents : Sherlock ↔ Watson.

    Implémente la sélection cyclique, la terminaison, et la gestion d'état.
    """

    def __init__(
        self,
        kernel: Kernel,
        settings: AppSettings,
        max_turns: int = 10,
        termination_strategy: Optional[CluedoTerminationStrategy] = None,
    ):
        """
        Initialise l'orchestrateur Cluedo de base.

        Args:
            kernel: Kernel Semantic Kernel
            settings: Configuration de l'application
            max_turns: Nombre maximum de tours
            termination_strategy: Stratégie de terminaison personnalisée
        """
        self.kernel = kernel
        self.settings = settings
        self.max_turns = max_turns
        self.termination_strategy = termination_strategy or CluedoTerminationStrategy()

        # État et agents
        self.sherlock_agent: Optional[Agent] = None
        self.watson_agent: Optional[Agent] = None
        self.orchestration: Optional[GroupChatOrchestration] = None

        # Métriques de performance
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.execution_metrics: Dict[str, Any] = {}

        self._logger = logging.getLogger(self.__class__.__name__)

    async def setup_workflow(
        self,
        nom_enquete: str = "Le Mystère du Manoir Tudor",
        elements_jeu: Optional[Dict[str, List[str]]] = None,
    ) -> EnqueteCluedoState:
        """
        Configure le workflow 2-agents avec état Cluedo.

        Args:
            nom_enquete: Nom de l'enquête
            elements_jeu: Éléments du jeu Cluedo (optionnel)

        Returns:
            État Cluedo configuré
        """
        self._logger.info("Configuration du workflow 2-agents Cluedo")

        # Configuration des éléments par défaut
        if elements_jeu is None:
            elements_jeu = {
                "suspects": [
                    "Colonel Moutarde",
                    "Professeur Violet",
                    "Mademoiselle Rose",
                ],
                "armes": ["Poignard", "Chandelier", "Revolver"],
                "lieux": ["Salon", "Cuisine", "Bureau"],
            }

        # Création de l'état Cluedo
        enquete_state = EnqueteCluedoState(
            nom_enquete_cluedo=nom_enquete,
            elements_jeu_cluedo=elements_jeu,
            description_cas="Un meurtre a été commis dans le manoir. Qui, où, et avec quoi ?",
            initial_context="L'enquête débute avec 2 enquêteurs spécialisés.",
        )

        # Configuration du plugin d'état
        state_plugin = EnqueteStateManagerPlugin(enquete_state)
        self.kernel.add_plugin(state_plugin, "EnqueteStatePlugin")

        # Création des agents
        from ..agents.factory import AgentFactory

        factory = AgentFactory(self.kernel, self.kernel.get_service(None).service_id)
        self.sherlock_agent = factory.create_sherlock_agent(agent_name="Sherlock")
        self.watson_agent = factory.create_watson_agent(agent_name="Watson")

        # Configuration des stratégies
        agents = [self.sherlock_agent, self.watson_agent]
        selection_strategy = CyclicSelectionStrategy(agents)

        # Création de l'orchestration avec GroupChatOrchestration (système original qui fonctionne)
        self.orchestration = GroupChatOrchestration()
        session_id = f"cluedo_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Configuration des agents
        agent_dict = {
            getattr(agent, "name", getattr(agent, "id", str(agent))): agent
            for agent in agents
        }
        self.orchestration.initialize_session(session_id, agent_dict)

        # Stocker les stratégies pour usage ultérieur
        self.selection_strategy = selection_strategy
        self.termination_strategy = self.termination_strategy

        self._logger.info(f"Workflow configuré avec {len(agents)} agents")
        return enquete_state

    async def execute_workflow(
        self,
        initial_question: str = "L'enquête commence. Sherlock, menez l'investigation !",
    ) -> Dict[str, Any]:
        """
        Exécute le workflow complet avec les 2 agents.

        Args:
            initial_question: Question/instruction initiale

        Returns:
            Résultat complet du workflow avec métriques
        """
        if not self.orchestration:
            raise ValueError(
                "Workflow non configuré. Appelez setup_workflow() d'abord."
            )

        self.start_time = datetime.now()
        self._logger.info("Début du workflow 2-agents Cluedo")

        # Historique des messages
        history: List[ChatMessageContent] = [
            ChatMessageContent(role="user", content=initial_question, name="System")
        ]

        # Boucle principale d'orchestration
        self._logger.info("Début de la boucle d'orchestration 2-agents...")
        try:
            while not await self.termination_strategy.should_terminate(
                agent=self.sherlock_agent, history=history
            ):
                next_agent = await self.selection_strategy.next(
                    agents=[self.sherlock_agent, self.watson_agent], history=history
                )
                self._logger.info(f"--- Tour de {next_agent.name} ---")

                # 1. Tronquer et nettoyer l'historique avant de l'envoyer
                history_to_send = history[-5:] if len(history) > 5 else history

                # 2. Exécuter l'agent avec l'historique nettoyé
                agent_response = await next_agent.invoke(
                    input=history_to_send, arguments=KernelArguments()
                )

                # 3. Consolider et nettoyer la réponse de l'agent
                clean_message = self._consolidate_agent_response(
                    agent_response, next_agent.name
                )

                # 4. Mettre à jour l'historique avec le message propre
                history.append(clean_message)
                last_message_content = str(clean_message.content)

                # 5. Log et mise à jour de l'état
                self._logger.info(
                    f"Réponse de {next_agent.name}: {last_message_content[:150]}..."
                )
                enquete_state.add_conversation_message(
                    agent_name=next_agent.name,
                    content=last_message_content,
                    message_type=self._detect_message_type(last_message_content),
                )

                turn_input = (
                    history[-2].content if len(history) > 1 else initial_question
                )
                enquete_state.record_agent_turn(
                    agent_name=next_agent.name,
                    action_type="invoke_with_history",
                    action_details={
                        "input": str(turn_input)[:150],
                        "output": last_message_content[:150],
                    },
                )

        except Exception as e:
            self._logger.error(f"Erreur durant l'orchestration: {e}", exc_info=True)
            raise

        finally:
            self.end_time = datetime.now()

            workflow_result = await self._collect_final_metrics(history)

            self._logger.info("[OK] Workflow 2-agents Cluedo terminé")
            return workflow_result

    def _consolidate_agent_response(
        self, response: Any, agent_name: str
    ) -> ChatMessageContent:
        """
        Consolide la réponse brute d'un agent en un unique ChatMessageContent.
        """
        full_content = ""
        role = "assistant"

        # Cas 1: La réponse est une liste de chunks de streaming
        if isinstance(response, list):
            for chunk in response:
                if hasattr(chunk, "items"):
                    for part in chunk.items:
                        if hasattr(part, "text"):
                            full_content += part.text
                # Gérer le cas où un ChatMessageContent se retrouve dans la liste
                elif hasattr(chunk, "content"):
                    full_content += str(chunk.content or "")
            # Cas 2: La réponse est un objet de streaming unique
        elif hasattr(response, "items"):
            for part in response.items:
                if hasattr(part, "text"):
                    full_content += part.text
            # Cas 3: C'est déjà un ChatMessageContent (potentiellement avec un contenu complexe)
        elif isinstance(response, ChatMessageContent):
            # Extraire le contenu texte, peu importe Comment il est encapsulé
            content_obj = response.content
            if hasattr(content_obj, "text"):
                full_content = content_obj.text
            elif isinstance(content_obj, str):
                full_content = content_obj
            else:
                full_content = str(content_obj or "")
            role = response.role
            # Cas 4: C'est juste un string ou un autre type de base
        else:
            full_content = str(response or "")

        return ChatMessageContent(role=role, content=full_content, name=agent_name)

    async def _collect_final_metrics(
        self, history: List[ChatMessageContent]
    ) -> Dict[str, Any]:
        """Collecte les métriques finales du workflow."""
        execution_time = (
            (self.end_time - self.start_time).total_seconds()
            if self.start_time and self.end_time
            else 0
        )

        # Statistiques de base
        conversation_history = []
        for msg in history:
            # Skip system messages
            sender_name = getattr(msg, "name", None)
            role_name = getattr(msg, "role", None)

            if sender_name == "System" or role_name == "System":
                continue

            # Robustly extract sender and message
            if hasattr(msg, "content"):
                message = str(msg.content)
                # Prefer 'name' but fall back to 'role'
                sender = sender_name or role_name or "Unknown"
            else:
                # Handle cases where msg might be a plain string
                message = str(msg)
                sender = "Unknown"

            conversation_history.append({"sender": sender, "message": message})

        # Métriques de performance
        performance_metrics = {
            "efficiency": {
                "turns_per_minute": len(history) / (execution_time / 60)
                if execution_time > 0
                else 0,
            },
            "agent_balance": self._calculate_agent_balance(history),
        }

        return {
            "workflow_info": {
                "max_turns": self.max_turns,
                "execution_time_seconds": execution_time,
                "timestamp": self.end_time.isoformat() if self.end_time else None,
            },
            "conversation_history": conversation_history,
            "performance_metrics": performance_metrics,
            "final_state": {
                "solution_proposed": False,  # Pas de solution dans ce workflow
                "final_solution": None,
                "secret_solution": None,
                "game_solvable_by_elimination": False,
            },
        }

    def _calculate_agent_balance(
        self, history: List[ChatMessageContent]
    ) -> Dict[str, float]:
        """Calcule l'équilibre de participation entre agents."""
        total_turns = len(history)
        if total_turns == 0:
            return {"sherlock": 0.0, "watson": 0.0}

        # Estimation basée sur le pattern cyclique (1/2 chacun idéalement)
        expected_per_agent = total_turns / 2

        return {
            "expected_turns_per_agent": expected_per_agent,
            "balance_score": 1.0,  # À améliorer avec tracking réel par Agent
            "note": "Équilibre cyclique théorique - à améliorer avec métriques réelles",
        }

    def _detect_message_type(self, content: str) -> str:
        """
        Détecte le type de message basé sur son contenu.
        """
        content_lower = content.lower()

        if any(
            keyword in content_lower
            for keyword in ["révèle", "possède", "carte", "j'ai"]
        ):
            return "revelation"
        elif any(
            keyword in content_lower
            for keyword in ["suggère", "propose", "suspect", "arme", "lieu"]
        ):
            return "suggestion"
        elif any(
            keyword in content_lower
            for keyword in ["analyse", "déduction", "conclusion", "donc"]
        ):
            return "analysis"
        elif any(
            keyword in content_lower
            for keyword in ["brillant", "exactement", "aha", "intéressant", "magistral"]
        ):
            return "reaction"
        else:
            return "message"


async def run_cluedo_game(
    kernel: Kernel,
    initial_question: str = "L'enquête commence. Sherlock, menez l'investigation !",
    max_turns: Optional[int] = 10,
) -> (List[Dict[str, Any]], EnqueteCluedoState):
    """
    Exécute une partie de Cluedo avec 2 agents.

    Args:
        kernel: Kernel Semantic Kernel
        initial_question: Question initiale
        max_turns: Nombre maximum de tours

    Returns:
        Historique des messages et état final
    """
    warnings.warn(
        "`run_cluedo_game` is deprecated and part of a legacy module. "
        "It is maintained for backward compatibility only. "
        "Please use new agent group chat architecture for new implementations.",
        DeprecationWarning,
        stacklevel=2
    )

    orchestrator = CluedoOrchestrator(
        kernel=kernel,
        settings=AppSettings(),
        max_turns=max_turns or 10,
        termination_strategy=None,
    )

    await orchestrator.setup_workflow()
    final_history, final_state = await orchestrator.execute_workflow(initial_question)

    return final_history, final_state


async def main():
    """Point d'entrée pour exécuter le script de manière autonome."""
    kernel = Kernel()

    # Récupération du service_id depuis les settings
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
    else:
        logger.warning(
            "Aucun service LLM configuré ou utilisation de mock activée. "
            "L'exécution peut échouer ou être limitée."
        )

    try:
        final_history, final_state = await run_cluedo_game(
            kernel=kernel, initial_question="L'enquête commence. Sherlock, à vous."
        )

        print("\n--- Historique Final de la Conversation ---")
        for entry in final_history:
            print(f"  {entry['sender']}: {entry['message']}")
        print("--- Fin de la Conversation ---")

        print("\n--- État Final de l'Enquête ---")
        print(f"Nom de l'enquête: {final_state.nom_enquete_cluedo}")
        print(f"Description: {final_state.description_cas}")
        print(f"Solution proposée: {final_state.final_solution}")
        print(f"Solution correcte: {final_state.solution_secrete_cluedo}")
        print("\n--- Hypothèses ---")
        for hypo in final_state.get_hypotheses():
            print(
                f"  - ID: {hypo['id']}, Text: {hypo['text']}, Confiance: {hypo['confidence_score']}, Statut: {hypo['status']}"
            )
        print("--- Fin de l'État ---")

    except Exception as e:
        print(f"Une erreur est survenue: {e}")
        import traceback

    if __name__ == "__main__":
        asyncio.run(main())

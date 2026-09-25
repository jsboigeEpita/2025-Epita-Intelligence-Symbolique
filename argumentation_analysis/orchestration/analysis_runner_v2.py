# -*- coding: utf-8 -*-
"""
analysis_runner_v2.py

Ce module fusionne la robustesse de analysis_runner.py avec les fonctionnalités
avancées de enhanced_pm_analysis_runner.py pour créer un orchestrateur d'analyse
d'argumentation puissant et moderne.

Caractéristiques principales :
- Agents construits par le constructeur du mode conversationnel actif
  (`create_conversational_agents`), sur le service LLM fourni par l'appelant.
- Intégration d'un système de trace avancé pour la capture de métadonnées et d'état.
- Gestion d'état enrichie via UnifiedAnalysisState.
- Structure de conversation unique et robuste, inspirée de analysis_runner.py.
"""

# ===== GESTION DES IMPORTS ET DE L'ENVIRONNEMENT =====
import sys
import os
import time
import traceback
import asyncio
import logging
import json
import random
import argparse
from typing import List, Optional, Union, Any, Dict

# Configuration des chemins pour assurer la résolution des modules du projet
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Auto-activation de l'environnement virtuel si nécessaire
import project_core.core_from_scripts.environment_manager as environment_manager

# ===== IMPORTS SEMANTIC KERNEL =====
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    AzureChatCompletion,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.agents import Agent, ChatCompletionAgent
from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)

# ===== IMPORTS DU PROJET D'ANALYSE D'ARGUMENTATION =====

# --- Core ---
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# --- Agents ---
from argumentation_analysis.orchestration.conversational_orchestrator import (
    create_conversational_agents,
)

# --- Reporting et Trace (Fonctionnalités avancées) ---
from argumentation_analysis.reporting.enhanced_real_time_trace_analyzer import (
    enhanced_global_trace_analyzer,
    start_enhanced_pm_capture,
    stop_enhanced_pm_capture,
    start_pm_orchestration_phase,
    capture_shared_state,
    get_enhanced_pm_report,
    save_enhanced_pm_report,
)

# Configuration du logging
logger = logging.getLogger(__name__)

# ===== EXCEPTIONS PERSONNALISÉES =====


class AnalysisV2Exception(Exception):
    """Exception de base pour les erreurs dans AnalysisRunnerV2."""

    pass


# ===== CLASSE PRINCIPALE DE L'ORCHESTRATEUR =====


class AnalysisRunnerV2:
    """
    Orchestre une analyse d'argumentation complète en fusionnant les meilleures
    pratiques de analysis_runner.py et enhanced_pm_analysis_runner.py.
    """

    # Agents de chaque phase, dans l'ordre où ils prennent la parole : les
    # trois macro-phases du mode conversationnel (extraction et détection,
    # analyse formelle et qualité, synthèse et débat).
    PHASE_CASTING = {
        "phase_1": ["ProjectManager", "ExtractAgent", "InformalAgent"],
        "phase_2": ["ProjectManager", "FormalAgent", "QualityAgent"],
        "phase_3": ["ProjectManager", "DebateAgent", "CounterAgent", "GovernanceAgent"],
    }

    def __init__(
        self,
        llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None,
    ):
        self._llm_service = llm_service
        self.run_id = f"run_{random.randint(1000, 9999)}"
        self.logger = logging.getLogger(f"AnalysisRunnerV2.{self.run_id}")
        self.orchestration_phases = []
        self.current_phase = None
        self.tour_counter = 0
        self.phase_counter = 0
        self.agents = {}
        self.agent_list = []
        self.chat_history = ChatHistory()

    async def run_analysis(
        self,
        text_content: str,
        llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None,
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal pour exécuter le pipeline d'analyse complet.
        """
        active_llm_service = llm_service or self._llm_service
        if not active_llm_service:
            raise AnalysisV2Exception("Un service LLM doit être fourni pour l'analyse.")

        self.logger.info("Démarrage de l'analyse avec AnalysisRunnerV2...")

        # Démarrage de la capture de trace avancée
        start_enhanced_pm_capture()

        run_start_time = time.time()

        try:
            # Configuration et exécution de l'orchestration multi-phases
            await self._setup_orchestration(text_content, active_llm_service)

            # Phase 1: Analyse informelle
            await self._run_phase_1_informal_analysis()

            # Phase 2: Analyse formelle
            await self._run_phase_2_formal_analysis()

            # Phase 3: Synthèse
            await self._run_phase_3_synthesis_coordination()

            final_analysis = json.loads(self.shared_state.to_json())
            result = {
                "status": "success",
                "analysis": final_analysis,
                "history": [
                    self._format_message_for_json(m) for m in self.chat_history
                ],
            }

            self.logger.info("Analyse terminée avec succès.")
            return result

        except Exception as e:
            # L'échec remonte à l'appelant (#2630). Il était rendu comme un
            # dict {"status": "error"} que main_orchestrator et text_analyzer
            # ne lisaient pas : un setup cassé s'y affichait comme une analyse
            # terminée.
            self.logger.error(
                f"Une erreur critique est survenue durant l'analyse : {e}",
                exc_info=True,
            )
            raise

        finally:
            # Arrêt de la capture et génération du rapport de trace
            stop_enhanced_pm_capture()
            run_end_time = time.time()
            total_duration = run_end_time - run_start_time
            self.logger.info(
                f"Durée totale de l'analyse : {total_duration:.2f} secondes."
            )

            try:
                report_path = os.path.join(
                    project_root, "logs", f"analysis_v2_trace_{self.run_id}.md"
                )
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                if save_enhanced_pm_report(report_path):
                    self.logger.info(
                        f"Rapport de trace avancé sauvegardé dans : {report_path}"
                    )
                else:
                    self.logger.warning(
                        "Le rapport de trace avancé n'a pas pu être sauvegardé."
                    )
            except Exception as report_e:
                self.logger.error(
                    f"Erreur lors de la sauvegarde du rapport de trace : {report_e}",
                    exc_info=True,
                )

    async def _setup_orchestration(
        self,
        texte_a_analyser: str,
        llm_service: Union[OpenAIChatCompletion, AzureChatCompletion],
    ):
        """Configure l'orchestration, l'état, le kernel et les agents."""
        self.logger.info("Configuration de l'orchestration...")
        # L'état que les plugins des agents conversationnels écrivent : leur
        # StateManagerPlugin appelle 12 méthodes que RhetoricalAnalysisState
        # n'a pas (add_nl_to_logic_translation, add_quality_score, ...).
        self.shared_state = UnifiedAnalysisState(initial_text=texte_a_analyser)

        self.kernel = sk.Kernel()
        self.kernel.add_service(llm_service)

        # Les agents viennent du constructeur du mode conversationnel actif
        # (#2630), sur le service que l'appelant a fourni. Chacun porte son
        # StateManagerPlugin et ses plugins de spécialité. Les classes BaseAgent
        # que ce runner instanciait ne peuvent pas parler dans un AgentGroupChat :
        # leurs `invoke_single` ont chacune une signature propre, et le canal SK
        # les appelle avec `messages=`/`thread=` (6 agents sur 6 échouaient au
        # premier tour, mesure dans #2630).
        self.logger.info("Création des agents du mode conversationnel...")
        self.agent_list = create_conversational_agents(
            kernel=self.kernel,
            state=self.shared_state,
            llm_service_id=llm_service.service_id,
        )
        self.agents = {agent.name: agent for agent in self.agent_list}
        self.logger.info("Configuration de l'orchestration terminée.")

    async def _run_phase_1_informal_analysis(self):
        """Phase 1: Analyse informelle coordonnée par le PM."""
        self.phase_counter += 1
        phase_id = f"phase_{self.phase_counter}"
        self.logger.info(f"Démarrage Phase 1: Analyse Informelle ({phase_id})")

        start_pm_orchestration_phase(
            phase_id=phase_id,
            phase_name="Analyse Informelle Coordonnée",
            assigned_agents=self.PHASE_CASTING["phase_1"],
        )

        initial_prompt = f"Phase 1: Analyse informelle. PM, veuillez initier l'analyse du texte suivant:\n\n---\n{self.shared_state.raw_text}\n---"
        self.chat_history.add_user_message(initial_prompt)

        await self._execute_conversation_phase(
            phase_id, self.PHASE_CASTING["phase_1"], max_turns=5
        )
        self.logger.info("Phase 1 terminée.")

    async def _run_phase_2_formal_analysis(self):
        """Phase 2: Analyse formelle avec la logique propositionnelle."""
        self.phase_counter += 1
        phase_id = f"phase_{self.phase_counter}"
        self.logger.info(f"Démarrage Phase 2: Analyse Formelle ({phase_id})")

        start_pm_orchestration_phase(
            phase_id=phase_id,
            phase_name="Analyse Formelle (Logique)",
            assigned_agents=self.PHASE_CASTING["phase_2"],
        )

        transition_prompt = "Phase 2: Analyse formelle. PM, veuillez coordonner avec les experts en logique pour formaliser les arguments identifiés."
        self.chat_history.add_user_message(transition_prompt)

        await self._execute_conversation_phase(
            phase_id, self.PHASE_CASTING["phase_2"], max_turns=5
        )
        self.logger.info("Phase 2 terminée.")

    async def _run_phase_3_synthesis_coordination(self):
        """Phase 3: Synthèse finale coordonnée par le PM."""
        self.phase_counter += 1
        phase_id = f"phase_{self.phase_counter}"
        self.logger.info(f"Démarrage Phase 3: Synthèse ({phase_id})")

        start_pm_orchestration_phase(
            phase_id=phase_id,
            phase_name="Synthèse Finale",
            assigned_agents=self.PHASE_CASTING["phase_3"],
        )

        synthesis_prompt = "Phase 3: Synthèse finale. PM, veuillez consolider tous les résultats et produire un rapport final."
        self.chat_history.add_user_message(synthesis_prompt)

        await self._execute_conversation_phase(
            phase_id, self.PHASE_CASTING["phase_3"], max_turns=5
        )
        self.logger.info("Phase 3 terminée.")

    async def _execute_conversation_phase(
        self, phase_id: str, agent_names: List[str], max_turns: int
    ):
        """Exécute une phase de conversation en utilisant AgentGroupChat."""
        self.logger.info(f"Exécution de la phase de conversation '{phase_id}'...")

        # La salle est la distribution de la phase, celle que la trace déclare
        # (#2630). Avec tous les agents dans chaque phase et 5 tours, la
        # sélection séquentielle rejouait les 5 mêmes premiers agents à chaque
        # phase : DebateAgent, CounterAgent et GovernanceAgent ne parlaient
        # jamais.
        group_chat = AgentGroupChat(
            agents=[self.agents[name] for name in agent_names],
            chat_history=self.chat_history,
        )

        # Invoquer le chat pour un nombre limité de tours
        turn_count = 0
        async for message in group_chat.invoke():
            self.tour_counter += 1
            capture_shared_state(
                phase_id=phase_id,
                tour_number=self.tour_counter,
                agent_active=getattr(message, "name", message.role.value),
                state_variables={"history_length": len(self.chat_history)},
                metadata={"turn_in_phase": turn_count + 1},
            )
            turn_count += 1
            if turn_count >= max_turns:
                self.logger.info(
                    f"Nombre maximum de tours ({max_turns}) atteint pour la phase '{phase_id}'."
                )
                break

        self.logger.info(
            f"Phase de conversation '{phase_id}' terminée après {turn_count} tours."
        )

    def _log_conversation_history(self, history: List[ChatMessageContent]):
        self.logger.debug("=== Transcription de la Conversation ===")
        for message in history:
            author_name = getattr(message, "name", message.role.value)
            self.logger.debug(f"[{author_name}]:\n{message.content}")
        self.logger.debug("======================================")

    def _format_message_for_json(self, message: ChatMessageContent) -> Dict[str, Any]:
        return {
            "author_role": message.role.value,
            "author_name": getattr(message, "name", None),
            "content": message.content,
            "tool_calls": [
                {"function_name": tc.function.name, "arguments": tc.function.arguments}
                for tc in getattr(message, "tool_calls", [])
                if tc
            ],
        }


# ===== FONCTION WRAPPER POUR UNE UTILISATION FACILE =====


async def run_analysis_v2(
    text_content: str,
    llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None,
):
    """Fonction wrapper pour lancer une analyse avec AnalysisRunnerV2."""
    runner = AnalysisRunnerV2(llm_service=llm_service)
    return await runner.run_analysis(text_content=text_content)


# ===== POINT D'ENTRÉE POUR EXÉCUTION EN LIGNE DE COMMANDE =====

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Lanceur pour AnalysisRunnerV2.")
    parser.add_argument("--text", type=str, required=True, help="Le texte à analyser.")
    args = parser.parse_args()

    main_logger = logging.getLogger("main_v2")
    main_logger.info("Lancement de l'analyse v2 en mode CLI...")

    try:
        # Pour l'exécution en CLI, on a besoin de créer un service LLM
        # Assurez-vous que vos clés API sont configurées dans les variables d'environnement
        # ou via le fichier de configuration chargé par `settings`.
        from argumentation_analysis.core.llm_service import create_llm_service

        # Pas de model_id (#2377) : « gpt-4-turbo-2024-04-09 » était figé ici,
        # un modèle qu'aucun résolveur ne choisissait — la CLI routait donc vers
        # un modèle que la configuration ne pouvait pas changer. La fabrique
        # résout depuis l'environnement (et la table #1930).
        cli_llm_service = create_llm_service(service_id="default")

        # Exécution de l'analyse
        analysis_result = asyncio.run(
            run_analysis_v2(text_content=args.text, llm_service=cli_llm_service)
        )

        # Affichage du résultat final
        print("\n\n===== RÉSULTAT DE L'ANALYSE V2 =====")
        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        print("====================================")

        main_logger.info("Analyse CLI terminée avec succès.")

    except Exception as e:
        main_logger.error(
            f"Une erreur est survenue lors de l'exécution CLI : {e}", exc_info=True
        )
        traceback.print_exc()

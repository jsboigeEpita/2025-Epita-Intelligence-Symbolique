# argumentation_analysis/agents/core/pm/pm_agent.py
import logging
from typing import Dict, Any, Optional
from pydantic import Field

import warnings
from semantic_kernel import Kernel  # type: ignore
from semantic_kernel.functions import KernelArguments  # type: ignore
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.agents import Agent

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.core.semantic_setup import register_prompt_function
from .pm_definitions import (
    PM_INSTRUCTIONS,
)  # Ou PM_INSTRUCTIONS_V9 selon la version souhaitée
from .prompts import prompt_define_tasks_v15, prompt_write_conclusion_v7
from argumentation_analysis.config.settings import AppSettings

# Supposons que StateManagerPlugin est importable si nécessaire
# from ...services.state_manager_plugin import StateManagerPlugin # Exemple


class ProjectManagerAgent(BaseAgent):
    """
    Agent spécialisé dans la planification stratégique de l'analyse d'argumentation.
    Il définit les tâches séquentielles et génère la conclusion finale,
    en fournissant des instructions à un orchestrateur externe pour l'exécution.
    """

    # logger inherited from BaseAgent (read-only @property over _agent_logger PrivateAttr)

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "ProjectManagerAgent",
        instructions: Optional[str] = PM_INSTRUCTIONS,
    ):
        super().__init__(
            kernel=kernel, agent_name=agent_name, system_prompt=instructions
        )
        self.kernel = kernel
        self.instructions = instructions
        logging.getLogger(__name__).info(
            f"ProjectManagerAgent '{agent_name}' initialisé."
        )

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Décrit ce que l'agent peut faire."""
        return {
            "define_tasks_and_delegate": "Defines analysis tasks and delegates them to specialist agents.",
            "synthesize_results": "Synthesizes results from specialist agents (implicite via conclusion).",
            "write_conclusion": "Writes the final conclusion of the analysis.",
            "coordinate_analysis_flow": "Manages the overall workflow of the argumentation analysis based on the current state.",
            # Ajouter d'autres capacités si pertinent, ex: gestion d'état spécifique si le PM interagit directement avec.
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants spécifiques du ProjectManagerAgent dans le kernel SK.
        """
        self.logger.info(
            f"Configuration des composants pour {self.name} avec le service LLM: {llm_service_id}"
        )

        plugin_name = (
            self.name
        )  # Ou "ProjectManager" si l'on préfère un nom de plugin fixe

        # Enregistrement des fonctions sémantiques du PM
        # Note: Les settings de prompt (default_settings) sont récupérés par le kernel
        # lors de l'ajout de la fonction si llm_service_id est valide.

        # #2632 : un échec d'enregistrement lève ; l'agent n'existe pas sans
        # ses deux fonctions.
        register_prompt_function(
            self.kernel,
            self.name,
            plugin_name,
            "DefineTasksAndDelegate",  # Nom plus SK-conventionnel
            prompt_define_tasks_v15,  # Utiliser la dernière version du prompt
            "Defines the NEXT single task, registers it, and designates 1 agent (Exact Name Required).",
        )
        self.logger.debug(
            f"Fonction sémantique '{plugin_name}.DefineTasksAndDelegate' ajoutée."
        )

        register_prompt_function(
            self.kernel,
            self.name,
            plugin_name,
            "WriteAndSetConclusion",  # Nom plus SK-conventionnel
            prompt_write_conclusion_v7,  # Utiliser la dernière version du prompt
            "Writes and registers the final conclusion (with pre-check of state).",
        )
        self.logger.debug(
            f"Fonction sémantique '{plugin_name}.WriteAndSetConclusion' ajoutée."
        )

        # Gestion du StateManagerPlugin
        # Si le PM doit interagir avec le StateManager via des appels SK DANS ses fonctions sémantiques,
        # alors le plugin StateManager doit être ajouté ici.
        # Cependant, le plan de refactoring suggère que l'orchestrateur gère l'état.
        # Pour l'instant, on suppose que les fonctions sémantiques du PM (comme définies dans prompts.py)
        # génèrent des "instructions" pour appeler StateManager, que l'orchestrateur exécutera.
        # Si les prompts étaient conçus pour appeler directement {{StateManager.add_analysis_task}},
        # alors il faudrait ajouter le plugin ici.
        # self.logger.info("Vérification pour StateManagerPlugin...")
        # state_manager_plugin_instance = self.kernel.plugins.get("StateManager")
        # if state_manager_plugin_instance:
        #     self.logger.info("StateManagerPlugin déjà présent dans le kernel global, aucune action supplémentaire ici.")
        # else:
        #     self.logger.warning("StateManagerPlugin non trouvé dans le kernel. Si les fonctions sémantiques du PM "
        #                        "doivent l'appeler directement, il doit être ajouté au kernel (typiquement par l'orchestrateur).")
        #     # Exemple si on devait l'ajouter ici (nécessiterait l'instance):
        #     # sm_plugin = StateManagerPlugin(...) # Nécessite l'instance du StateManager
        #     # self.kernel.add_plugin(sm_plugin, plugin_name="StateManager")
        #     # self.logger.info("StateManagerPlugin ajouté localement au kernel du PM (ceci est un exemple).")

        self.logger.info(f"Composants pour {self.name} configurés.")

    async def define_tasks_and_delegate(
        self, analysis_state_snapshot: str, raw_text: str
    ) -> str:
        """
        Définit la prochaine tâche d'analyse et suggère sa délégation à un agent spécialiste.

        Cette méthode invoque la fonction sémantique `DefineTasksAndDelegate`.
        Le résultat est une chaîne (souvent JSON) que l'orchestrateur doit interpréter
        pour effectivement créer la tâche et la déléguer.

        Args:
            analysis_state_snapshot: Un instantané de l'état actuel de l'analyse.
            raw_text: Le texte brut original soumis à l'analyse.

        Returns:
            Une chaîne de caractères contenant la définition de la tâche et l'agent suggéré.
        """
        self.logger.info("Appel de define_tasks_and_delegate...")
        args = KernelArguments(
            analysis_state_snapshot=analysis_state_snapshot, raw_text=raw_text
        )

        try:
            response = await self.kernel.invoke(
                plugin_name=self.name,
                function_name="DefineTasksAndDelegate",
                arguments=args,
            )
            result = str(response)
            self.logger.debug(f"Réponse de DefineTasksAndDelegate: {result}")
            return result
        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'invocation de DefineTasksAndDelegate: {e}"
            )
            # Retourner une chaîne d'erreur ou lever une exception spécifique
            return f"ERREUR: Impossible de définir la tâche. Détails: {e}"

    async def write_conclusion(
        self, analysis_state_snapshot: str, raw_text: str
    ) -> str:
        """
        Rédige la conclusion finale de l'analyse basée sur l'état actuel.

        Cette méthode invoque la fonction sémantique `WriteAndSetConclusion`.
        Le résultat est une chaîne (la conclusion) que l'orchestrateur doit interpréter
        pour enregistrer formellement la conclusion.

        Args:
            analysis_state_snapshot: Un instantané de l'état actuel de l'analyse (devrait
                                     refléter l'achèvement des tâches précédentes).
            raw_text: Le texte brut original.

        Returns:
            Une chaîne de caractères contenant la conclusion finale proposée.
        """
        self.logger.info("Appel de write_conclusion...")
        args = KernelArguments(
            analysis_state_snapshot=analysis_state_snapshot, raw_text=raw_text
        )

        try:
            response = await self.kernel.invoke(
                plugin_name=self.name,
                function_name="WriteAndSetConclusion",
                arguments=args,
            )
            result = str(response)
            self.logger.debug(f"Réponse de WriteAndSetConclusion: {result}")
            return result
        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'invocation de WriteAndSetConclusion: {e}"
            )
            # Retourner une chaîne d'erreur ou lever une exception spécifique
            return f"ERREUR: Impossible d'écrire la conclusion. Détails: {e}"

    async def get_response(
        self, kernel: "Kernel", arguments: Optional["KernelArguments"] = None
    ) -> list[ChatMessageContent]:
        """Implémentation de la méthode abstraite requise."""
        self.logger.debug(
            f"get_response appelé, délégation à invoke_single pour {self.name}."
        )
        return await self.invoke_single(kernel, arguments)

    async def invoke_single(
        self, kernel: "Kernel", arguments: Optional["KernelArguments"] = None
    ) -> list[ChatMessageContent]:
        """
        Implémentation requise par la classe de base abstraite.
        Délègue à la méthode principale de l'agent.

        C'est l'unique définition de `invoke_single` pour cet agent (cf. #2339) :
        elle honore la signature `(kernel, arguments)` attendue par `get_response`
        ci-dessus et par le consommateur de production
        (`orchestration/enhanced_pm_analysis_runner.py`, qui construit lui-même
        ses `KernelArguments` puis itère chaque élément produit comme une liste).
        Elle délègue à `invoke_custom` — jamais à elle-même.
        """
        self.logger.debug(
            f"invoke_single appelé, délégation à invoke_custom pour {self.name}."
        )

        # Surcharge pour retourner une liste comme attendu par la nouvelle interface d'agent
        response_message = await self.invoke_custom(kernel, arguments)
        return [response_message]

    async def invoke_custom(
        self, kernel: "Kernel", arguments: Optional["KernelArguments"] = None
    ) -> ChatMessageContent:
        """
        Logique d'invocation principale du PM, qui décide de la prochaine action.
        """
        if not arguments or "chat_history" not in arguments:
            raise ValueError(
                "L'historique de chat ('chat_history') est manquant dans les arguments."
            )

        history = arguments["chat_history"]
        self.logger.info(
            f"invoke_custom called for {self.name} with {len(history)} messages."
        )

        # Extraire le texte brut initial du message utilisateur dans l'historique
        raw_text_user_message = next(
            (m.content for m in history if m.role == "user"), None
        )
        if not raw_text_user_message:
            raise ValueError(
                "Message utilisateur initial non trouvé dans l'historique."
            )
        # Isoler le texte brut de l'invite système
        raw_text = (
            raw_text_user_message.split("---\n")[-2].strip()
            if "---" in raw_text_user_message
            else raw_text_user_message
        )

        # Le StateManager est maintenant dans le kernel, on peut l'appeler
        state_manager_plugin = kernel.plugins.get("StateManager")
        if not state_manager_plugin:
            raise RuntimeError("StateManagerPlugin non trouvé dans le kernel.")

        # Correction: Utiliser le nom de fonction correct ("get_current_state_snapshot") et appeler la fonction.
        snapshot_function = state_manager_plugin["get_current_state_snapshot"]
        # Correction : Les fonctions natives du kernel nécessitent que le kernel
        # soit passé comme argument lors de l'appel.
        # Ajout du paramètre summarize requis.
        arguments = KernelArguments(summarize=False)
        snapshot_result = await snapshot_function(kernel=kernel, arguments=arguments)
        analysis_state_snapshot = str(snapshot_result)

        if not raw_text:
            self.logger.warning(
                "Aucun texte brut (message utilisateur initial) trouvé dans l'historique."
            )
            return ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content='{"error": "Initial text (user message) not found in history."}',
                name=self.name,
            )

        # La logique de décision est maintenant entièrement déléguée à la fonction sémantique
        # `DefineTasksAndDelegate` qui utilise `prompt_define_tasks_v11`.
        # Ce prompt est conçu pour analyser l'état et déterminer s'il faut
        # créer une tâche ou conclure.
        self.logger.info(
            "Délégation de la décision et de la définition de la tâche à la fonction sémantique."
        )

        try:
            result_str = await self.define_tasks_and_delegate(
                analysis_state_snapshot, raw_text
            )
            return ChatMessageContent(
                role=AuthorRole.ASSISTANT, content=result_str, name=self.name
            )

        except Exception as e:
            self.logger.error(
                f"Erreur durant l'invocation du PM Agent: {e}", exc_info=True
            )
            error_msg = f'{{"error": "An unexpected error occurred in ProjectManagerAgent: {e}"}}'
            return ChatMessageContent(
                role=AuthorRole.ASSISTANT, content=error_msg, name=self.name
            )

    # D'autres méthodes métiers pourraient être ajoutées ici si nécessaire,
    # par exemple, une méthode qui encapsule la logique de décision principale du PM
    # basée sur l'état actuel, et qui appellerait ensuite define_tasks_and_delegate ou write_conclusion.
    # async def decide_next_action(self, current_state_summary: str, full_state_snapshot: str, raw_text: str) -> str:
    #     """
    #     Méthode principale du PM pour décider de la prochaine action basée sur l'état.
    #     Cette méthode pourrait utiliser une fonction sémantique plus globale ou orchestrer
    #     les appels à define_tasks_and_delegate et write_conclusion.
    #     Pour l'instant, on se base sur les instructions système qui guident l'orchestrateur externe.
    #     """
    #     # La logique ici dépendrait de si le PM est "autonome" dans sa décision ou si
    #     # l'orchestrateur suit les instructions PM_INSTRUCTIONS et appelle les méthodes spécifiques.
    #     # Si PM_INSTRUCTIONS est utilisé par un orchestrateur externe, alors les méthodes
    #     # define_tasks_and_delegate et write_conclusion sont les points d'entrée principaux.
    #     self.logger.info("decide_next_action appelée (logique à implémenter si PM autonome)")
    #     # Exemple:
    #     # if "final_conclusion" in full_state_snapshot and "null" not in full_state_snapshot.split("final_conclusion")[1][:10]: # Heuristique simple
    #     #     return "L'analyse est déjà terminée."
    #     # elif "toutes les étapes pertinentes ... terminées" in current_state_summary: # Heuristique
    #     #     return await self.write_conclusion(full_state_snapshot, raw_text)
    #     # else:
    #     #     return await self.define_tasks_and_delegate(full_state_snapshot, raw_text)
    #     pass

    # #2339 — Deux surcharges ajoutées ici par 5b717ee7 ont été retirées :
    #
    # 1. Un second `async def invoke_single(self, messages)` qui écrasait, à la
    #    création de la classe, la définition conforme ci-dessus (l.214). Son corps
    #    faisait `arguments = KernelArguments(chat_history=messages)` puis
    #    `return await self.invoke_single(self.kernel, arguments)` : portant le même
    #    nom, cette délégation se résolvait vers elle-même. Aucun appelant réel ne
    #    demandait la forme `(messages)` (l'unique `AgentChannel` qui invoque avec
    #    une liste de messages, `channels/volatile_agent_channel.py:56`, n'est câblé
    #    que par `ExtractAgent.create_channel`; `SherlockEnqueteAgent` est une classe
    #    sœur portant sa propre `invoke_single`). Sa seule logique propre — envelopper
    #    des messages dans `KernelArguments(chat_history=...)` — est déjà faite par le
    #    consommateur de production lui-même, `enhanced_pm_analysis_runner.py:576`.
    #
    # 2. Un `async def invoke_stream(self, messages)` qui faisait
    #    `await self.invoke(messages)` alors que `BaseAgent.invoke` est un
    #    générateur asynchrone (`agent_bases.py:223-229`) — donc inopérant quelle que
    #    soit la forme d'appel, et incompatible avec l'appel de production
    #    `invoke_stream(self.kernel, arguments=arguments)`. Son intention déclarée
    #    (« envelopper la réponse non-streamée dans un stream ») est exactement ce que
    #    fournit la paire héritée `BaseAgent.invoke`/`BaseAgent.invoke_stream`
    #    (`agent_bases.py:223-237`), qui accepte la forme d'appel de production.

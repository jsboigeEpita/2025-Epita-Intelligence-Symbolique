# argumentation_analysis/agents/core/pm/pm_agent.py
import logging
from typing import Dict, Any, Optional

from semantic_kernel import Kernel # type: ignore
from semantic_kernel.functions.kernel_arguments import KernelArguments # type: ignore

from ..abc.agent_bases import BaseAgent
from .pm_definitions import PM_INSTRUCTIONS # Ou PM_INSTRUCTIONS_V9 selon la version souhaitée
from .prompts import prompt_define_tasks_v11, prompt_write_conclusion_v7

# Supposons que StateManagerPlugin est importable si nécessaire
# from ...services.state_manager_plugin import StateManagerPlugin # Exemple

class ProjectManagerAgent(BaseAgent):
    """
    Agent spécialisé dans la planification stratégique de l'analyse d'argumentation.
    Il définit les tâches séquentielles et génère la conclusion finale,
    en fournissant des instructions à un orchestrateur externe pour l'exécution.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "ProjectManagerAgent", system_prompt: Optional[str] = PM_INSTRUCTIONS):
        super().__init__(kernel, agent_name, system_prompt)
        self.logger.info(f"ProjectManagerAgent '{agent_name}' initialisé.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Décrit ce que l'agent peut faire."""
        return {
            "define_tasks_and_delegate": "Defines analysis tasks and delegates them to specialist agents.",
            "synthesize_results": "Synthesizes results from specialist agents (implicite via conclusion).",
            "write_conclusion": "Writes the final conclusion of the analysis.",
            "coordinate_analysis_flow": "Manages the overall workflow of the argumentation analysis based on the current state."
            # Ajouter d'autres capacités si pertinent, ex: gestion d'état spécifique si le PM interagit directement avec.
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants spécifiques du ProjectManagerAgent dans le kernel SK.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name} avec le service LLM: {llm_service_id}")

        plugin_name = self.name # Ou "ProjectManager" si l'on préfère un nom de plugin fixe

        # Enregistrement des fonctions sémantiques du PM
        # Note: Les settings de prompt (default_settings) sont récupérés par le kernel
        # lors de l'ajout de la fonction si llm_service_id est valide.

        try:
            self.sk_kernel.add_function(
                prompt=prompt_define_tasks_v11, # Utiliser la dernière version du prompt
                plugin_name=plugin_name,
                function_name="DefineTasksAndDelegate", # Nom plus SK-conventionnel
                description="Defines the NEXT single task, registers it, and designates 1 agent (Exact Name Required).",
                # prompt_execution_settings=self.sk_kernel.get_prompt_execution_settings_from_service_id(llm_service_id) # Géré par le kernel
            )
            self.logger.debug(f"Fonction sémantique '{plugin_name}.DefineTasksAndDelegate' ajoutée.")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout de la fonction '{plugin_name}.DefineTasksAndDelegate': {e}")

        try:
            self.sk_kernel.add_function(
                prompt=prompt_write_conclusion_v7, # Utiliser la dernière version du prompt
                plugin_name=plugin_name,
                function_name="WriteAndSetConclusion", # Nom plus SK-conventionnel
                description="Writes and registers the final conclusion (with pre-check of state).",
                # prompt_execution_settings=self.sk_kernel.get_prompt_execution_settings_from_service_id(llm_service_id) # Géré par le kernel
            )
            self.logger.debug(f"Fonction sémantique '{plugin_name}.WriteAndSetConclusion' ajoutée.")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout de la fonction '{plugin_name}.WriteAndSetConclusion': {e}")

        # Gestion du StateManagerPlugin
        # Si le PM doit interagir avec le StateManager via des appels SK DANS ses fonctions sémantiques,
        # alors le plugin StateManager doit être ajouté ici.
        # Cependant, le plan de refactoring suggère que l'orchestrateur gère l'état.
        # Pour l'instant, on suppose que les fonctions sémantiques du PM (comme définies dans prompts.py)
        # génèrent des "instructions" pour appeler StateManager, que l'orchestrateur exécutera.
        # Si les prompts étaient conçus pour appeler directement {{StateManager.add_analysis_task}},
        # alors il faudrait ajouter le plugin ici.
        # self.logger.info("Vérification pour StateManagerPlugin...")
        # state_manager_plugin_instance = self.sk_kernel.plugins.get("StateManager")
        # if state_manager_plugin_instance:
        #     self.logger.info("StateManagerPlugin déjà présent dans le kernel global, aucune action supplémentaire ici.")
        # else:
        #     self.logger.warning("StateManagerPlugin non trouvé dans le kernel. Si les fonctions sémantiques du PM "
        #                        "doivent l'appeler directement, il doit être ajouté au kernel (typiquement par l'orchestrateur).")
        #     # Exemple si on devait l'ajouter ici (nécessiterait l'instance):
        #     # sm_plugin = StateManagerPlugin(...) # Nécessite l'instance du StateManager
        #     # self.sk_kernel.add_plugin(sm_plugin, plugin_name="StateManager")
        #     # self.logger.info("StateManagerPlugin ajouté localement au kernel du PM (ceci est un exemple).")

        self.logger.info(f"Composants pour {self.name} configurés.")

    async def define_tasks_and_delegate(self, analysis_state_snapshot: str, raw_text: str) -> str:
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
        args = KernelArguments(analysis_state_snapshot=analysis_state_snapshot, raw_text=raw_text)
        
        try:
            response = await self.sk_kernel.invoke(
                plugin_name=self.name,
                function_name="DefineTasksAndDelegate",
                arguments=args
            )
            result = str(response)
            self.logger.debug(f"Réponse de DefineTasksAndDelegate: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'invocation de DefineTasksAndDelegate: {e}")
            # Retourner une chaîne d'erreur ou lever une exception spécifique
            return f"ERREUR: Impossible de définir la tâche. Détails: {e}"

    async def write_conclusion(self, analysis_state_snapshot: str, raw_text: str) -> str:
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
        args = KernelArguments(analysis_state_snapshot=analysis_state_snapshot, raw_text=raw_text)

        try:
            response = await self.sk_kernel.invoke(
                plugin_name=self.name,
                function_name="WriteAndSetConclusion",
                arguments=args
            )
            result = str(response)
            self.logger.debug(f"Réponse de WriteAndSetConclusion: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'invocation de WriteAndSetConclusion: {e}")
            # Retourner une chaîne d'erreur ou lever une exception spécifique
            return f"ERREUR: Impossible d'écrire la conclusion. Détails: {e}"

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

if __name__ == '__main__':
    # Section pour des tests unitaires ou des exemples d'utilisation rapides
    # Nécessiterait un kernel configuré, un service LLM, etc.
    
    # Configuration du logging de base pour les tests
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger_main = logging.getLogger(__name__)
    
    logger_main.info("Exemple d'initialisation et d'utilisation (nécessite un kernel configuré):")

    # # Exemple (nécessite un kernel et un service LLM configurés)
    # # from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
    # # kernel_instance = Kernel()
    # # llm_service_instance = OpenAIChatCompletion(service_id="default", ai_model_id="gpt-3.5-turbo", api_key="...", org_id="...") # Remplacer par vos infos
    # # kernel_instance.add_service(llm_service_instance)
    
    # # pm_agent = ProjectManagerAgent(kernel=kernel_instance)
    # # pm_agent.setup_agent_components(llm_service_id="default")
    
    # # print(pm_agent.get_agent_info())
    
    # # async def run_example():
    # #     # Simuler un état et un texte
    # #     dummy_state = '{"tasks_defined": [], "tasks_answered": [], "final_conclusion": null}'
    # #     dummy_text = "Ceci est un texte d'exemple pour l'analyse."
        
    # #     print("\n--- Test define_tasks_and_delegate ---")
    # #     delegation_result = await pm_agent.define_tasks_and_delegate(dummy_state, dummy_text)
    # #     print(f"Résultat de la délégation:\n{delegation_result}")
        
    # #     # Simuler un état plus avancé pour la conclusion
    # #     advanced_state = '{"tasks_defined": ["task_1"], "tasks_answered": {"task_1": "Extraction faite."}, "identified_arguments": ["Arg1"], "final_conclusion": null}'
    # #     print("\n--- Test write_conclusion ---")
    # #     conclusion_result = await pm_agent.write_conclusion(advanced_state, dummy_text)
    # #     print(f"Résultat de la conclusion:\n{conclusion_result}")

    # # import asyncio
    # # asyncio.run(run_example())
    pass
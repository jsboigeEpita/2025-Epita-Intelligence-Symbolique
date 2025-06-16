# argumentation_analysis/agents/core/pm/pm_agent.py
import logging
from typing import Dict, Any, Optional

from semantic_kernel import Kernel # type: ignore
from semantic_kernel.functions.kernel_arguments import KernelArguments # type: ignore
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.role import Role


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
            self.kernel.add_function(
                prompt=prompt_define_tasks_v11, # Utiliser la dernière version du prompt
                plugin_name=plugin_name,
                function_name="DefineTasksAndDelegate", # Nom plus SK-conventionnel
                description="Defines the NEXT single task, registers it, and designates 1 agent (Exact Name Required).",
                # prompt_execution_settings=self.kernel.get_prompt_execution_settings_from_service_id(llm_service_id) # Géré par le kernel
            )
            self.logger.debug(f"Fonction sémantique '{plugin_name}.DefineTasksAndDelegate' ajoutée.")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout de la fonction '{plugin_name}.DefineTasksAndDelegate': {e}")

        try:
            self.kernel.add_function(
                prompt=prompt_write_conclusion_v7, # Utiliser la dernière version du prompt
                plugin_name=plugin_name,
                function_name="WriteAndSetConclusion", # Nom plus SK-conventionnel
                description="Writes and registers the final conclusion (with pre-check of state).",
                # prompt_execution_settings=self.kernel.get_prompt_execution_settings_from_service_id(llm_service_id) # Géré par le kernel
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
            response = await self.kernel.invoke(
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
            response = await self.kernel.invoke(
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

    async def invoke(self, history: list[ChatMessageContent]) -> ChatMessageContent:
        """Méthode dépréciée, utilisez invoke_custom."""
        import warnings
        warnings.warn("The 'invoke' method is deprecated, use 'invoke_custom' instead.", DeprecationWarning)
        return await self.invoke_custom(history)

    async def get_response(self, history: list[ChatMessageContent]) -> ChatMessageContent:
        """Méthode dépréciée, utilisez invoke_custom."""
        import warnings
        warnings.warn("The 'get_response' method is deprecated, use 'invoke_custom' instead.", DeprecationWarning)
        return await self.invoke_custom(history)

    async def invoke_custom(self, history: list[ChatMessageContent]) -> ChatMessageContent:
        """
        Logique d'invocation principale du PM, qui décide de la prochaine action.
        """
        self.logger.info(f"invoke_custom called for {self.name} with {len(history)} messages.")

        # Extraire le texte brut initial (typiquement le premier message utilisateur)
        raw_text = next((m.content for m in history if m.role == Role.USER and m.content), "")
        
        # Extraire l'état d'analyse (typiquement un résumé JSON dans un message d'assistant récent)
        analysis_state_snapshot = next((m.content for m in reversed(history) if m.role == Role.ASSISTANT and m.content and 'tasks_defined' in m.content), "{}")

        if not raw_text:
            self.logger.warning("Aucun texte brut (message utilisateur initial) trouvé dans l'historique.")
            return ChatMessageContent(role=Role.ASSISTANT, content='{"error": "Initial text (user message) not found in history."}', name=self.name)

        # Décider de l'action : écrire la conclusion ou définir la prochaine tâche.
        # Cette logique est simplifiée. Une vraie implémentation analyserait `analysis_state_snapshot`
        # pour voir si toutes les tâches sont complétées.
        # Si le prompt v11 est assez intelligent, il peut faire ce choix lui-même.
        action_to_perform = "conclusion" if '"final_conclusion": null' not in analysis_state_snapshot and len(analysis_state_snapshot) > 10 else "define_tasks"

        self.logger.info(f"PM Agent সিদ্ধান্ত (decision): {action_to_perform}")

        try:
            if action_to_perform == "conclusion" and '"conclusion"' in self.system_prompt: # Vérifie si la conclusion est une étape attendue
                self.logger.info("Tentative de rédaction de la conclusion.")
                result_str = await self.write_conclusion(analysis_state_snapshot, raw_text)
            else:
                self.logger.info("Définition de la prochaine tâche.")
                result_str = await self.define_tasks_and_delegate(analysis_state_snapshot, raw_text)
            
            return ChatMessageContent(role=Role.ASSISTANT, content=result_str, name=self.name)

        except Exception as e:
            self.logger.error(f"Erreur durant l'invocation du PM Agent: {e}", exc_info=True)
            error_msg = f'{{"error": "An unexpected error occurred in ProjectManagerAgent: {e}"}}'
            return ChatMessageContent(role=Role.ASSISTANT, content=error_msg, name=self.name)

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
    import argparse
    import asyncio
    import os
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    
    # Configuration du logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    logger_main = logging.getLogger(__name__)
    
    # Parse des arguments de ligne de commande
    parser = argparse.ArgumentParser(description='Project Manager Agent - Générateur de rapports via SK')
    parser.add_argument('--generate-report', action='store_true', help='Génère un rapport d\'analyse')
    parser.add_argument('--trace-file', type=str, help='Fichier de trace d\'entrée')
    parser.add_argument('--model', type=str, default='gpt-4o-mini', help='Modèle LLM à utiliser')
    parser.add_argument('--output', type=str, help='Fichier de sortie (optionnel, sinon stdout)')
    
    args = parser.parse_args()
    
    if args.generate_report:
        async def generate_report():
            try:
                # Lecture du fichier de trace
                trace_content = ""
                if args.trace_file and os.path.exists(args.trace_file):
                    with open(args.trace_file, 'r', encoding='utf-8') as f:
                        trace_content = f.read()
                    logger_main.info(f"Fichier de trace lu: {args.trace_file}")
                else:
                    logger_main.warning("Aucun fichier de trace spécifié ou fichier inexistant")
                
                # Configuration du kernel SK
                kernel_instance = Kernel()
                
                # Configuration du service LLM OpenAI
                api_key = os.getenv('OPENAI_API_KEY', '').strip('"')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY non configurée")
                
                llm_service = OpenAIChatCompletion(
                    service_id="openai_service",
                    ai_model_id=args.model,
                    api_key=api_key
                )
                kernel_instance.add_service(llm_service)
                
                # Création de l'agent PM
                pm_agent = ProjectManagerAgent(kernel=kernel_instance)
                pm_agent.setup_agent_components("openai_service")
                
                # Prompt de génération de rapport
                report_prompt = f"""
# Génération de Rapport d'Analyse - EPITA Intelligence Symbolique

Basé sur la trace d'exécution suivante, génère un rapport complet d'analyse :

## Trace d'Exécution
```
{trace_content}
```

## Instructions
Génère un rapport structuré en markdown qui inclut :

1. **Résumé Exécutif**
   - Statut global du projet (100% de succès)
   - Points clés de l'analyse

2. **Analyse Détaillée**
   - Modules testés et leur statut
   - Corrections apportées
   - Technologies utilisées

3. **Architecture Technique**
   - Description de l'architecture hybride Python/Java
   - Utilisation du Semantic Kernel
   - Pipeline agentique

4. **Résultats et Métriques**
   - Taux de succès par catégorie
   - Performance globale
   - Améliorations réalisées

5. **Conclusion et Recommandations**
   - Succès du projet
   - Perspective d'évolution
   - Bonnes pratiques identifiées

Le rapport doit être professionnel, technique et complet.
"""

                # Invocation directe via le kernel
                from semantic_kernel.functions import KernelFunction
                from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
                
                # Création d'une fonction de génération de rapport
                report_function = KernelFunction.from_prompt(
                    prompt=report_prompt,
                    function_name="GenerateReport",
                    plugin_name="ReportGenerator"
                )
                
                # Exécution de la génération
                result = await kernel_instance.invoke(report_function)
                report_content = str(result)
                
                # Sortie du rapport
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(report_content)
                    logger_main.info(f"Rapport généré: {args.output}")
                else:
                    print(report_content)
                
                logger_main.info("Génération de rapport terminée avec succès")
                
            except Exception as e:
                logger_main.error(f"Erreur lors de la génération du rapport: {e}")
                raise
        
        # Exécution asynchrone
        asyncio.run(generate_report())
    else:
        logger_main.info("Exemple d'initialisation et d'utilisation (nécessite un kernel configuré):")
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
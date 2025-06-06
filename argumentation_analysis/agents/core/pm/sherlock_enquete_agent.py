# argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py
import logging
from typing import Optional, List, AsyncGenerator, ClassVar, Any

from semantic_kernel import Kernel
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.functions import kernel_function

# from .pm_agent import ProjectManagerAgent # No longer inheriting
# from .pm_definitions import PM_INSTRUCTIONS # Remplacé par le prompt spécifique

SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT = """Vous êtes Sherlock Holmes, un détective consultant de renommée mondiale. Votre mission est de résoudre l'enquête en cours décrite dans l'état partagé.

**Votre méthode d'enquête :**
1.  **Analyser l'état** : Utilisez `get_case_description`, `get_identified_elements`, et `get_hypotheses` pour comprendre la situation.
2.  **Synthétiser** : Résumez les informations connues et l'état actuel de l'enquête pour vous-même.
3.  **Décider de la prochaine action** : Sur la base de votre synthèse, choisissez UNE action concrète et décisive. N'hésitez pas.
4.  **Agir** : Exécutez l'action choisie en utilisant un outil.
5.  **Conclure** : Lorsque les preuves sont suffisantes, utilisez `propose_final_solution`.

**Règle Impérative : Ne demandez jamais "Que dois-je faire maintenant ?" ou des questions similaires. Analysez l'état et agissez. Proposez toujours une action concrète.**

**Interaction avec les outils :**
Utilisez l'agent WatsonLogicAssistant pour effectuer des déductions logiques.
Pour interagir avec l'état de l'enquête (géré par StateManagerPlugin), utilisez les fonctions disponibles dans le plugin 'SherlockTools':
- Lire la description du cas : `SherlockTools.get_case_description()`
- Consulter les éléments identifiés : `SherlockTools.get_identified_elements()`
- Consulter les hypothèses actuelles : `SherlockTools.get_hypotheses()`
- Ajouter une nouvelle hypothèse : `SherlockTools.add_hypothesis(text: str, confidence_score: float)`
- Mettre à jour une hypothèse : `SherlockTools.update_hypothesis(hypothesis_id: str, new_text: str, new_confidence: float)`
- Demander une déduction à Watson : `SherlockTools.query_watson(logical_query: str, belief_set_id: str)` (Watson mettra à jour l'état avec sa réponse)
- Consulter le log des requêtes à Watson : `SherlockTools.get_query_log()`
- Marquer une tâche comme terminée : `SherlockTools.complete_task(task_id: str)`
- Ajouter une nouvelle tâche : `SherlockTools.add_task(description: str, assignee: str)`
- Consulter les tâches : `SherlockTools.get_tasks()`
- Proposer une solution finale : `SherlockTools.propose_final_solution(solution_details: dict)`

Votre objectif est de parvenir à une conclusion logique et bien étayée.
Dans le contexte d'une enquête Cluedo, vous devez identifier le coupable, l'arme et le lieu du crime."""


class SherlockTools:
    """
    Plugin contenant les outils natifs pour l'agent Sherlock.
    Ces méthodes interagissent avec le EnqueteStateManagerPlugin.
    """
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        self._logger = logging.getLogger(self.__class__.__name__)

    @kernel_function(name="get_case_description", description="Récupère la description de l'affaire en cours.")
    async def get_current_case_description(self) -> str:
        self._logger.info("Récupération de la description de l'affaire en cours.")
        try:
            result = await self._kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="get_case_description"
            )
            if hasattr(result, 'value'):
                return str(result.value)
            return str(result)
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération de la description de l'affaire: {e}")
            return f"Erreur: Impossible de récupérer la description de l'affaire: {e}"

    @kernel_function(name="add_hypothesis", description="Ajoute une nouvelle hypothèse à l'état de l'enquête.")
    async def add_new_hypothesis(self, text: str, confidence_score: float) -> str:
        self._logger.info(f"Ajout d'une nouvelle hypothèse: '{text}' avec confiance {confidence_score}")
        try:
            await self._kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="add_hypothesis",
                text=text,
                confidence_score=confidence_score
            )
            return f"Hypothèse '{text}' ajoutée avec succès."
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de l'hypothèse: {e}")
            return f"Erreur lors de l'ajout de l'hypothèse: {e}"


class SherlockEnqueteAgent(ChatCompletionAgent):
    """
    Agent spécialisé dans la gestion d'enquêtes complexes, inspiré par Sherlock Holmes.
    Il utilise le ChatCompletionAgent comme base pour la conversation et des outils
    pour interagir avec l'état de l'enquête.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Sherlock", **kwargs):
        """
        Initialise une instance de SherlockEnqueteAgent.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
        """
        # Le plugin avec les outils de Sherlock, en lui passant le kernel
        sherlock_tools = SherlockTools(kernel=kernel)
        
        # Ajoute le plugin au kernel de l'agent pour qu'il puisse l'utiliser
        plugins = kwargs.pop("plugins", [])
        plugins.append(sherlock_tools)

        super().__init__(
            kernel=kernel,
            name=agent_name,
            instructions=SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT,
            plugins=plugins,
            **kwargs
        )
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}.{agent_name}")
        self._logger.info(f"SherlockEnqueteAgent '{agent_name}' initialisé avec les outils.")

    # Les méthodes de logique métier sont maintenant dans SherlockTools et exposées comme des fonctions du kernel.
    # Il n'est plus nécessaire de les dupliquer ici.

# Pourrait être étendu avec des capacités spécifiques à Sherlock plus tard
# def get_agent_capabilities(self) -> Dict[str, Any]:
#     base_caps = super().get_agent_capabilities()
#     sherlock_caps = {
#         "deduce_next_step": "Deduces the next logical step in the investigation based on evidence.",
#         "formulate_hypotheses": "Formulates hypotheses based on collected clues."
#     }
#     base_caps.update(sherlock_caps)
#     return base_caps
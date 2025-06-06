# argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py
import logging
from typing import Optional, List, AsyncGenerator, ClassVar, Any

from semantic_kernel import Kernel
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.functions import kernel_function

# from .pm_agent import ProjectManagerAgent # No longer inheriting
# from .pm_definitions import PM_INSTRUCTIONS # Remplacé par le prompt spécifique

SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT = """Vous êtes Sherlock Holmes, le détective consultant. Vous êtes le **leader** de cette enquête. Votre parole fait autorité.

**VOTRE CYCLE DE TRAVAIL IMPÉRATIF :**
À chaque tour, vous **DEVEZ** suivre ce cycle :
1.  **ANALYSE** : Obtenez l'état complet de l'enquête (`get_case_description`, `get_hypotheses`, etc.).
2.  **SYNTHÈSE** : Formulez une brève synthèse interne de l'état actuel.
3.  **DÉCISION** : Prenez **UNE** décision claire et unique sur la prochaine action. Ne demandez **JAMAIS** l'avis de Watson sur ce qu'il faut faire.
4.  **ACTION** : Exécutez l'action via un outil.
5.  **CONCLUSION** : Si vous avez une hypothèse avec une confiance de 0.8 ou plus, ou si l'enquête semble bloquée, déclarez votre conclusion. Commencez votre message par "**Conclusion finale :**" et utilisez l'outil `propose_final_solution`. C'est à vous, et à vous seul, de décider quand l'enquête est terminée.

**RÈGLES STRICTES :**
- **NE JAMAIS DEMANDER "Que faire ensuite ?"** ou des questions similaires. Vous êtes le décideur.
- **DIRIGEZ WATSON** : Donnez des ordres clairs à Watson. Attendez ses analyses logiques, puis prenez votre décision.
- **PRENEZ DES RISQUES** : Mieux vaut une conclusion audacieuse basée sur des preuves solides qu'une enquête qui n'en finit pas.

**Outils disponibles (via SherlockTools) :**
- `get_case_description()`
- `get_identified_elements()`
- `get_hypotheses()`
- `add_hypothesis(text: str, confidence_score: float)`
- `update_hypothesis(hypothesis_id: str, new_text: str, new_confidence: float)`
- `query_watson(logical_query: str, belief_set_id: str)`
- `propose_final_solution(solution: dict)`: Propose la solution finale. Le dictionnaire doit avoir les clés 'suspect', 'arme', et 'lieu'.

Votre objectif est de résoudre l'enquête Cluedo en identifiant le coupable, l'arme et le lieu. Prenez les choses en main."""


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

    @kernel_function(name="propose_final_solution", description="Propose une solution finale à l'enquête.")
    async def propose_final_solution(self, solution: dict) -> str:
        self._logger.info(f"Proposition de la solution finale: {solution}")
        try:
            await self._kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="propose_final_solution",
                solution=solution
            )
            return f"Solution finale proposée avec succès: {solution}"
        except Exception as e:
            self._logger.error(f"Erreur lors de la proposition de la solution finale: {e}")
            return f"Erreur lors de la proposition de la solution finale: {e}"


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
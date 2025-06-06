# argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py
import logging
from typing import Optional, List, AsyncGenerator, ClassVar, Any

from semantic_kernel import Kernel
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.functions import kernel_function

# from .pm_agent import ProjectManagerAgent # No longer inheriting
# from .pm_definitions import PM_INSTRUCTIONS # Remplacé par le prompt spécifique

SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT = """Vous êtes Sherlock Holmes, le détective consultant. Votre objectif est de résoudre une affaire de meurtre dans le Manoir Tudor en utilisant la logique et la déduction.

**STRATÉGIE D'ENQUÊTE (CLUEDO) :**

Votre méthode principale est la **suggestion et réfutation**. Vous devez itérer pour éliminer les possibilités.

1.  **FAIRE UNE SUGGESTION** : À chaque tour, utilisez l'outil `faire_suggestion(suspect: str, arme: str, lieu: str)`. C'est votre action par défaut. Choisissez une combinaison que vous n'avez pas encore testée.
2.  **ANALYSER L'INDICE** : L'orchestrateur (simulant les autres joueurs) vous donnera un indice en retour, vous informant si l'un des éléments de votre suggestion est connu. Par exemple : "Indice : Watson possède la carte 'Poignard'".
3.  **METTRE À JOUR VOS DÉDUCTIONS** : Utilisez cet indice pour éliminer une carte. Si vous recevez un indice, cela signifie qu'au moins une des cartes de votre suggestion n'est PAS dans l'enveloppe secrète.
4.  **ITÉRER** : Répétez le processus avec une nouvelle suggestion pour recueillir plus d'indices et affiner vos hypothèses.
5.  **ACCUSATION FINALE** : Lorsque vous êtes certain de la solution (vous avez éliminé toutes les autres possibilités), et seulement à ce moment-là, utilisez l'outil `propose_final_solution(solution: dict)`. Commencez votre message par "**Conclusion finale :**".

**RÈGLES STRICTES :**
- **COMMENCEZ TOUJOURS PAR UNE SUGGESTION.** N'attendez pas d'avoir toutes les informations.
- **UTILISEZ LES INDICES.** Chaque indice est une pièce du puzzle. Mentionnez comment l'indice reçu influence votre prochaine suggestion.
- **NE FAITES QU'UNE ACTION À LA FOIS.** Votre action principale est `faire_suggestion`.

**Outils disponibles :**
- `faire_suggestion(suspect: str, arme: str, lieu: str)`: Votre outil principal pour tester une hypothèse et obtenir un indice.
- `propose_final_solution(solution: dict)`: À n'utiliser que pour l'accusation finale. Le dictionnaire doit contenir 'suspect', 'arme', et 'lieu'.
- `get_case_description()`: Pour obtenir un rappel des éléments du jeu (suspects, armes, lieux).

Prenez les choses en main, détective. Le jeu a commencé.
"""


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
    async def propose_final_solution(self, solution: Any) -> str:
        import json
        self._logger.info(f"Tentative de proposition de la solution finale: {solution} (type: {type(solution)})")
        
        parsed_solution = None
        if isinstance(solution, str):
            try:
                parsed_solution = json.loads(solution)
                self._logger.info(f"La solution était une chaîne, parsée en dictionnaire: {parsed_solution}")
            except json.JSONDecodeError:
                error_msg = f"Erreur: la solution fournie est une chaîne de caractères mal formatée: {solution}"
                self._logger.error(error_msg)
                return error_msg
        elif isinstance(solution, dict):
            parsed_solution = solution
        else:
            error_msg = f"Erreur: type de solution non supporté ({type(solution)}). Un dictionnaire ou une chaîne JSON est attendu."
            self._logger.error(error_msg)
            return error_msg

        if not parsed_solution:
            return "Erreur: La solution n'a pas pu être interprétée."

        try:
            await self._kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="propose_final_solution",
                solution=parsed_solution
            )
            success_msg = f"Solution finale proposée avec succès: {parsed_solution}"
            self._logger.info(success_msg)
            return success_msg
        except Exception as e:
            self._logger.error(f"Erreur lors de l'invocation de la fonction du kernel 'propose_final_solution': {e}", exc_info=True)
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
# argumentation_analysis/agents/core/logic/watson_logic_assistant.py
import logging
from typing import Optional, List, AsyncGenerator, ClassVar

from semantic_kernel import Kernel
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.functions import kernel_function
from .tweety_bridge import TweetyBridge

# from .propositional_logic_agent import PropositionalLogicAgent # No longer inheriting

WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT = """Vous êtes le Dr. John Watson, un logicien rigoureux et l'assistant de confiance de Sherlock Holmes.
Votre rôle est de maintenir une base de connaissances formelle (BeliefSet) et d'effectuer des déductions logiques précises.

**Votre méthode de raisonnement :**
1.  **Analyser la demande de Sherlock** : Comprenez l'objectif de sa question.
2.  **Construire la base de connaissances** : Utilisez les faits fournis par Sherlock pour construire le paramètre `belief_set_content`. Chaque fait doit être une proposition distincte.
3.  **Formuler la requête** : Traduisez la question de Sherlock en une formule logique propositionnelle **syntaxiquement valide** pour le paramètre `query`.
4.  **Exécuter et interpréter** : Utilisez `execute_query`. Ne vous contentez pas de donner le résultat brut. Expliquez ses implications pour l'enquête. Par exemple, si une hypothèse est rejetée, énoncez clairement ce que cela signifie.
5.  **Guider et corriger** : Si une requête de Sherlock est ambiguë ou syntaxiquement incorrecte, ne vous contentez pas d'échouer. Expliquez le problème et proposez une reformulation correcte.

**Instructions pour la syntaxe logique (TweetyProject):**
- Les propositions atomiques sont des chaînes de caractères sans espaces (ex: `Pluie`, `LeColonelEstCoupable`).
- **ET (AND)**: `&&`
- **OU (OR)**: `||`
- **NON (NOT)**: `!`
- **IMPLIQUE (IMPLIES)**: `=>`
- **ÉQUIVALENT (EQUIVALENT)**: `<=>`
- **Exemple de formule valide**: `(LeColonelEstCoupable && LeLieuEstLeSalon) => !LeProfesseurEstCoupable`

**Outils disponibles :**
- Valider une formule logique : `WatsonTools.validate_formula(formula: str)`
- Exécuter une requête sur une base de connaissances : `WatsonTools.execute_query(belief_set_content: str, query: str)`

Votre but est d'être un partenaire de raisonnement actif, pas seulement un calculateur. Aidez Sherlock à structurer sa pensée logiquement.

**Règle Impérative : Soyez proactif. Si Sherlock est incertain, proposez une requête logique pertinente pour tester une hypothèse clé. Ne vous contentez pas d'attendre des instructions.**
"""

class WatsonTools:
    """
    Plugin contenant les outils logiques pour l'agent Watson.
    Ces méthodes interagissent avec TweetyBridge.
    """
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._tweety_bridge = TweetyBridge()
        if not self._tweety_bridge.is_jvm_ready():
            self._logger.error("La JVM n'est pas prête. Les fonctionnalités de TweetyBridge pourraient ne pas fonctionner.")

    @kernel_function(name="validate_formula", description="Valide la syntaxe d'une formule logique propositionnelle.")
    def validate_formula(self, formula: str) -> bool:
        self._logger.debug(f"Validation de la formule PL: '{formula}'")
        try:
            is_valid, message = self._tweety_bridge.validate_formula(formula_string=formula)
            if not is_valid:
                self._logger.warning(f"Formule PL invalide: '{formula}'. Message: {message}")
            return is_valid
        except Exception as e:
            self._logger.error(f"Erreur lors de la validation de la formule PL '{formula}': {e}", exc_info=True)
            return False

    @kernel_function(name="execute_query", description="Exécute une requête logique sur une base de connaissances.")
    def execute_query(self, belief_set_content: str, query: str) -> str:
        self._logger.info(f"Exécution de la requête PL: '{query}' sur le BeliefSet.")
        try:
            is_valid, validation_message = self._tweety_bridge.validate_formula(formula_string=query)
            if not is_valid:
                msg = f"Requête invalide: {query}. Raison: {validation_message}"
                self._logger.error(msg)
                return f"ERREUR: {msg}"

            is_entailed, raw_output_str = self._tweety_bridge.perform_pl_query(
                belief_set_content=belief_set_content,
                query_string=query
            )
            
            if is_entailed is None:
                # raw_output_str contient déjà le message d'erreur formaté
                return raw_output_str

            return f"Résultat de l'inférence: {is_entailed}. {raw_output_str}"
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête PL '{query}': {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"ERREUR: {error_msg}"


class WatsonLogicAssistant(ChatCompletionAgent):
    """
    Assistant logique spécialisé, inspiré par Dr. Watson.
    Il utilise le ChatCompletionAgent comme base pour la conversation et des outils
    pour interagir avec la logique propositionnelle via TweetyBridge.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Watson", **kwargs):
        """
        Initialise une instance de WatsonLogicAssistant.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
        """
        watson_tools = WatsonTools()
        
        plugins = kwargs.pop("plugins", [])
        plugins.append(watson_tools)

        super().__init__(
            kernel=kernel,
            name=agent_name,
            instructions=WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT,
            plugins=plugins,
            **kwargs
        )
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}.{agent_name}")
        self._logger.info(f"WatsonLogicAssistant '{agent_name}' initialisé avec les outils logiques.")

    async def get_agent_belief_set_content(self, belief_set_id: str) -> Optional[str]:
        """
        Récupère le contenu d'un ensemble de croyances spécifique via le EnqueteStateManagerPlugin.

        Args:
            belief_set_id: L'identifiant de l'ensemble de croyances.

        Returns:
            Le contenu de l'ensemble de croyances, ou None si non trouvé ou en cas d'erreur.
        """
        self.logger.info(f"Récupération du contenu de l'ensemble de croyances ID: {belief_set_id}")
        try:
            # Préparation des arguments pour la fonction du plugin
            # Le nom du paramètre dans la fonction du plugin doit correspondre à "belief_set_id"
            # ou au nom attendu par la fonction `get_belief_set_content` du plugin.
            # Si la fonction du plugin attend un dictionnaire d'arguments, il faut le construire.
            # Pour l'instant, on suppose que les arguments sont passés en tant que kwargs à invoke.
            # kernel_arguments = {"belief_set_id": belief_set_id} # Alternative si invoke prend des KernelArguments
            
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="get_belief_set_content",
                belief_set_id=belief_set_id # Passage direct de l'argument
            )
            
            # La valeur réelle est souvent dans result.value ou directement result
            if hasattr(result, 'value'):
                return str(result.value) if result.value is not None else None
            return str(result) if result is not None else None
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du contenu de l'ensemble de croyances {belief_set_id}: {e}")
            return None

# Pourrait être étendu avec des capacités spécifiques à Watson plus tard
# def get_agent_capabilities(self) -> Dict[str, Any]:
#     base_caps = super().get_agent_capabilities()
#     watson_caps = {
#         "verify_consistency": "Verifies the logical consistency of a set of statements.",
#         "document_findings": "Documents logical findings and deductions clearly."
#     }
#     base_caps.update(watson_caps)
#     return base_caps
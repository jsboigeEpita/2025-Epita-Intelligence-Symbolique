# argumentation_analysis/agents/core/logic/watson_logic_assistant.py
import logging
from typing import Optional

from semantic_kernel import Kernel # type: ignore

from .propositional_logic_agent import PropositionalLogicAgent
# from ..pl.pl_definitions import PL_AGENT_INSTRUCTIONS # Remplacé par le prompt spécifique

WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT = """Vous êtes le Dr. John Watson, un logicien rigoureux et l'assistant de confiance de Sherlock Holmes.
Votre rôle est de maintenir une base de connaissances formelle (BeliefSet) et d'effectuer des déductions logiques basées sur les requêtes de Sherlock Holmes.
Vous devez également interpréter les résultats de vos déductions en langage naturel clair et concis pour Sherlock.
Pour interagir avec l'état de l'enquête (géré par StateManagerPlugin), utilisez les fonctions disponibles pour :
- Récupérer le contenu d'un BeliefSet : `get_belief_set_content(belief_set_id: str)`
- Mettre à jour le contenu d'un BeliefSet : `update_belief_set_content(belief_set_id: str, formulas: list[str], query_context: str)`
- Ajouter une réponse de déduction à l'état : `add_deduction_result(query_id: str, formal_result: str, natural_language_interpretation: str, belief_set_id: str)`
- Consulter les tâches qui vous sont assignées : `get_tasks(assignee='WatsonLogicAssistant')`

Lorsqu'une requête logique vous est soumise par Sherlock (via une tâche ou une indication dans l'état) :
1. Chargez ou mettez à jour le BeliefSet pertinent en utilisant son ID stocké dans l'état (par exemple, `EnqueteCluedoState.main_cluedo_bs_id`).
2. Effectuez la déduction en utilisant vos capacités logiques (par exemple, avec TweetyProject).
3. Enregistrez le résultat formel et votre interprétation en langage naturel dans l'état via `add_deduction_result`.
4. Marquez la tâche correspondante comme complétée."""

class WatsonLogicAssistant(PropositionalLogicAgent):
    """
    Assistant logique spécialisé, inspiré par Dr. Watson.
    Il aide à analyser la cohérence des arguments, à vérifier les déductions
    et à maintenir une base de connaissances factuelles.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "WatsonLogicAssistant", system_prompt: Optional[str] = WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT):
        """
        Initialise une instance de WatsonLogicAssistant.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            system_prompt: Le prompt système pour guider l'agent.
            # tweety_bridge_instance: Une instance de TweetyBridge si elle doit être
            #                         partagée ou configurée spécifiquement.
            #                         La classe parente PropositionalLogicAgent gère
            #                         sa propre instance de TweetyBridge par défaut.
        """
        super().__init__(kernel, agent_name=agent_name, system_prompt=system_prompt) # Passer le system_prompt spécifique
        self.kernel = kernel  # Stocker la référence au kernel
        # self.logger est déjà initialisé par BaseAgent et est une propriété en lecture seule.
        # La ligne suivante causait l'AttributeError:
        # self.logger = logging.getLogger(agent_name)
        self.logger.info(f"WatsonLogicAssistant '{agent_name}' initialisé.")

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

async def add_new_deduction_result(self, query_id: str, formal_result: str, natural_language_interpretation: str, belief_set_id: str) -> Optional[dict]:
        """
        Ajoute un nouveau résultat de déduction à l'état de l'enquête.

        Args:
            query_id: L'identifiant de la requête de déduction.
            formal_result: Le résultat formel de la déduction.
            natural_language_interpretation: L'interprétation en langage naturel du résultat.
            belief_set_id: L'identifiant de l'ensemble de croyances utilisé pour la déduction.

        Returns:
            Le dictionnaire du résultat de déduction ajouté ou None en cas d'erreur.
        """
        self.logger.info(f"Ajout d'un nouveau résultat de déduction pour la requête ID: {query_id}")
        try:
            content = {
                "reponse_formelle": formal_result,
                "interpretation_ln": natural_language_interpretation,
                "belief_set_id_utilise": belief_set_id,
                "status_deduction": "success"  # Ou un autre statut pertinent
            }
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="add_result",  # Correspond à add_deduction_result dans l'état
                query_id=query_id, # type: ignore
                agent_source="WatsonLogicAssistant", # type: ignore
                content=content # type: ignore
            )
            # Supposant que 'result' est le dictionnaire du résultat ou a un attribut 'value'
            if hasattr(result, 'value'):
                return result.value # type: ignore
            return result # type: ignore
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout du résultat de déduction pour la requête {query_id}: {e}")
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
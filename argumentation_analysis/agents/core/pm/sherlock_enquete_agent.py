# argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py
import logging
from typing import Optional

from semantic_kernel import Kernel # type: ignore

from .pm_agent import ProjectManagerAgent
# from .pm_definitions import PM_INSTRUCTIONS # Remplacé par le prompt spécifique

SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT = """Vous êtes Sherlock Holmes, un détective consultant de renommée mondiale. Votre mission est de résoudre l'enquête en cours décrite dans l'état partagé.
Vous devez analyser les informations disponibles, formuler des hypothèses et diriger l'enquête.
Utilisez l'agent WatsonLogicAssistant pour effectuer des déductions logiques basées sur les faits et les règles établies.
Pour interagir avec l'état de l'enquête (géré par StateManagerPlugin), utilisez les fonctions disponibles pour :
- Lire la description du cas : `get_case_description()`
- Consulter les éléments identifiés : `get_identified_elements()`
- Consulter les hypothèses actuelles : `get_hypotheses()`
- Ajouter une nouvelle hypothèse : `add_hypothesis(hypothesis_text: str, confidence_score: float)`
- Mettre à jour une hypothèse : `update_hypothesis(hypothesis_id: str, new_text: str, new_confidence: float)`
- Demander une déduction à Watson : `query_watson(logical_query: str, belief_set_id: str)` (Watson mettra à jour l'état avec sa réponse)
- Consulter le log des requêtes à Watson : `get_query_log()`
- Marquer une tâche comme terminée : `complete_task(task_id: str)`
- Ajouter une nouvelle tâche : `add_task(description: str, assignee: str)`
- Consulter les tâches : `get_tasks()`
- Proposer une solution finale : `propose_final_solution(solution_details: dict)`

Votre objectif est de parvenir à une conclusion logique et bien étayée.
Dans le contexte d'une enquête Cluedo, vous devez identifier le coupable, l'arme et le lieu du crime."""

class SherlockEnqueteAgent(ProjectManagerAgent):
    """
    Agent spécialisé dans la gestion d'enquêtes complexes, inspiré par Sherlock Holmes.
    Il planifie les étapes d'investigation, identifie les pistes à suivre et
    synthétise les informations pour résoudre l'affaire.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "SherlockEnqueteAgent", system_prompt: Optional[str] = SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT):
        """
        Initialise une instance de SherlockEnqueteAgent.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            system_prompt: Le prompt système pour guider l'agent.
        """
        super().__init__(kernel, agent_name=agent_name, system_prompt=system_prompt)
        self.kernel = kernel  # Stocker la référence au kernel
        # self.logger = logging.getLogger(agent_name) # Assurer un logger spécifique - Géré par BaseAgent._logger
        self._logger.info(f"SherlockEnqueteAgent '{agent_name}' initialisé.")

    async def get_current_case_description(self) -> str:
        """
        Récupère la description de l'affaire en cours via le EnqueteStateManagerPlugin.

        Returns:
            La description de l'affaire.
        """
        self._logger.info("Récupération de la description de l'affaire en cours.")
        try:
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="get_case_description"
            )
            # La valeur réelle est souvent dans result.value ou directement result selon la config du kernel
            # Pour l'instant, supposons que 'result' est directement la chaîne ou a un attribut 'value'
            # Ceci pourrait nécessiter un ajustement basé sur le comportement réel de 'invoke'
            if hasattr(result, 'value'):
                return str(result.value)
            return str(result)
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération de la description de l'affaire: {e}")
            # Retourner une chaîne vide ou lever une exception spécifique pourrait être mieux
            return "Erreur: Impossible de récupérer la description de l'affaire."

    async def add_new_hypothesis(self, hypothesis_text: str, confidence_score: float) -> Optional[dict]:
        """
        Ajoute une nouvelle hypothèse à l'état de l'enquête.

        Args:
            hypothesis_text: Le texte de l'hypothèse.
            confidence_score: Le score de confiance de l'hypothèse.

        Returns:
            Le dictionnaire de l'hypothèse ajoutée ou None en cas d'erreur.
        """
        self._logger.info(f"Ajout d'une nouvelle hypothèse: '{hypothesis_text}' avec confiance {confidence_score}")
        try:
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="add_hypothesis",
                text=hypothesis_text, # type: ignore
                confidence_score=confidence_score # type: ignore
            )
            # Supposant que 'result' est le dictionnaire de l'hypothèse ou a un attribut 'value'
            if hasattr(result, 'value'):
                return result.value # type: ignore
            return result # type: ignore
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de l'hypothèse: {e}")
            return None

async def add_new_hypothesis(self, hypothesis_text: str, confidence_score: float) -> Optional[dict]:
        """
        Ajoute une nouvelle hypothèse à l'état de l'enquête.

        Args:
            hypothesis_text: Le texte de l'hypothèse.
            confidence_score: Le score de confiance de l'hypothèse.

        Returns:
            Le dictionnaire de l'hypothèse ajoutée ou None en cas d'erreur.
        """
        self._logger.info(f"Ajout d'une nouvelle hypothèse: '{hypothesis_text}' avec confiance {confidence_score}")
        try:
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="add_hypothesis",
                text=hypothesis_text, # type: ignore
                confidence_score=confidence_score # type: ignore
            )
            # Supposant que 'result' est le dictionnaire de l'hypothèse ou a un attribut 'value'
            if hasattr(result, 'value'):
                return result.value # type: ignore
            return result # type: ignore
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de l'hypothèse: {e}")
            return None
# Pourrait être étendu avec des capacités spécifiques à Sherlock plus tard
# def get_agent_capabilities(self) -> Dict[str, Any]:
#     base_caps = super().get_agent_capabilities()
#     sherlock_caps = {
#         "deduce_next_step": "Deduces the next logical step in the investigation based on evidence.",
#         "formulate_hypotheses": "Formulates hypotheses based on collected clues."
#     }
#     base_caps.update(sherlock_caps)
#     return base_caps
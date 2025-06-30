# argumentation_analysis/orchestration/cluedo_components/cluedo_plugins.py
import logging
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import KernelArguments

logger = logging.getLogger(__name__)

class CluedoInvestigatorPlugin:
    """Un plugin pour les actions d'investigation de Sherlock."""

    def __init__(self, suggestion_handler):
        self._suggestion_handler = suggestion_handler

    @kernel_function(
        description="Fait une suggestion formelle pour une combinaison suspect, arme et lieu.",
        name="make_suggestion"
    )
    async def make_suggestion(
        self,
        suspect: str,
        arme: str,
        lieu: str,
    ) -> str:
        """
        Enregistre une suggestion formelle et déclenche la réfutation de l'oracle.
        """
        raw_suggestion = {"suspect": suspect, "arme": arme, "lieu": lieu}
        logger.info(f"Tool Call 'make_suggestion': {raw_suggestion}")

        # L'appel à Moriarty est maintenant géré ici directement
        try:
            # Note: le 'suggesting_agent_name' devra être passé d'une manière ou d'une autre,
            # ou l'abstraire du handler. Pour l'instant, hardcodons "Sherlock" comme exemple.
            oracle_revelation = await self._suggestion_handler.force_moriarty_oracle_revelation(raw_suggestion, "Sherlock")
            if oracle_revelation and oracle_revelation.get('content'):
                logger.info(f"Réponse de Moriarty (via plugin): {oracle_revelation['content']}")
                return oracle_revelation['content']
            else:
                return "Moriarty n'a rien à ajouter."
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Moriarty via le plugin: {e}", exc_info=True)
            return f"Une erreur a empêché Moriarty de répondre: {e}"
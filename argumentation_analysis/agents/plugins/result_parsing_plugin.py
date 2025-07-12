# Fichier: argumentation_analysis/agents/plugins/result_parsing_plugin.py
import json
import logging
from typing import Annotated
from semantic_kernel.functions.kernel_function_decorator import kernel_function

class ResultParsingPlugin:
    """Plugin simple pour parser et retourner le résultat final de l'analyse."""
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    @kernel_function(
        name="parse_and_return_fallacy",
        description="Prend le nom du sophisme identifié et le retourne."
    )
    def parse_and_return_fallacy(
        self, fallacy_name: Annotated[str, "Le nom du sophisme identifié."]
    ) -> Annotated[str, "Le nom du sophisme, formaté en chaîne de caractères."]:
        """
        Prend le nom du sophisme et retourne une chaîne simple.
        """
        self.logger.info(f"Received fallacy_name: {fallacy_name}")
        return fallacy_name
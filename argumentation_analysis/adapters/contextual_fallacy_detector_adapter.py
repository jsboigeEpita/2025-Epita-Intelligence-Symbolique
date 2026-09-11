from argumentation_analysis.core.interfaces.fallacy_detector import (
    AbstractFallacyDetector,
)
from argumentation_analysis.agents.tools.analysis.new import ContextualFallacyDetector

# #2149 : le contrat de l'ABC est `detect(text)` — sans contexte — alors que le
# détecteur encapsulé exige une description de contexte (dont il infère les
# facteurs qui pondèrent la gravité). Ce pont doit donc choisir un contexte par
# défaut ; il est neutre et nommé ici pour que le choix soit visible et
# réversible, plutôt qu'enfoui dans l'appel.
DEFAULT_CONTEXT_DESCRIPTION = "contexte général"


class ContextualFallacyDetectorAdapter(AbstractFallacyDetector):
    """
    Adapter for the ContextualFallacyDetector to conform to the AbstractFallacyDetector interface.
    """

    def __init__(self, contextual_fallacy_detector: ContextualFallacyDetector):
        """
        Initializes the adapter.

        Args:
            contextual_fallacy_detector: An instance of ContextualFallacyDetector.
        """
        self._detector = contextual_fallacy_detector

    def detect(self, text: str) -> dict:
        """
        Detects fallacies using the wrapped ContextualFallacyDetector.

        Args:
            text: The text to analyze.

        Returns:
            A dictionary containing the detected fallacies.
        """
        return self._detector.detect_contextual_fallacies(
            text, context_description=DEFAULT_CONTEXT_DESCRIPTION
        )

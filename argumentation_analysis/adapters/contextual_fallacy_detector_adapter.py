from argumentation_analysis.core.interfaces.fallacy_detector import AbstractFallacyDetector
from argumentation_analysis.agents.tools.analysis.new import ContextualFallacyDetector


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
        return self._detector.detect(text)
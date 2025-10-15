import abc


class AbstractFallacyDetector(abc.ABC):
    @abc.abstractmethod
    def detect(self, text: str) -> dict:
        """
        Detects fallacies in the given text.

        Args:
            text: The text to analyze.

        Returns:
            A dictionary containing the detected fallacies.
        """
        raise NotImplementedError

import logging
import sys

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[MOCK JPYPE EXCEPTIONS LOG] %(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)


class JException(Exception):
    """Simule jpype.JException."""

    def __init__(self, message="Mock Java Exception"):
        super().__init__(message)
        self.message = message
        mock_logger.debug(f"JException initialisée avec message: {message}")

    def getClass(self):
        """Simule la méthode getClass() de Java."""

        class MockClass:  # Classe interne pour simuler java.lang.Class
            def getName(self):
                # Pourrait être plus spécifique si l'exception originale est connue
                return "org.mockexception.MockException"

        return MockClass()

    def getMessage(self):
        """Simule la méthode getMessage() de Java."""
        return self.message


class JVMNotFoundException(Exception):
    """Simule jpype.JVMNotFoundException."""

    def __init__(self, message="Mock JVM Not Found Exception"):
        super().__init__(message)
        self.message = message
        mock_logger.debug(f"JVMNotFoundException initialisée avec message: {message}")


mock_logger.info("Module jpype_components.exceptions initialisé.")

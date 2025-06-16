import logging
import sys

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE CONFIG LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

class MockConfig:
    def __init__(self):
        self.jvm_path = None # Initialement None, peut être défini par startJVM
        self.convertStrings = False # Valeur par défaut typique
        self.onexit = True # Attribut manquant pour la callback atexit
        self.destroy_jvm = True # Attribut pour la terminaison de la JVM
        # Ajouter d'autres attributs de config si besoin
        mock_logger.debug(f"MockConfig instance créée. jvm_path: {self.jvm_path}, convertStrings: {self.convertStrings}, onexit: {self.onexit}, destroy_jvm: {self.destroy_jvm}")

config = MockConfig()
mock_logger.info("Instance 'config' de MockConfig créée.")
import logging
import sys

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE COLLECTIONS LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

mock_logger.info("Module jpype_components.collections initialisé. Les définitions de MockJavaCollection et _ModuleLevelMockJavaIterator ont été déplacées vers jpype_components.types.")
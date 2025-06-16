import sys
import logging
from unittest.mock import MagicMock

# Configurer un logger de base pour le bootstrapping
logging.basicConfig(level=logging.INFO, format='%(asctime)s [BOOTSTRAP] [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

log.info("Démarrage du bootstrap des mocks.")

# --- Mock de NumPy ---
# Appliquer un mock de base pour NumPy pour éviter les ImportError précoces.
# Les tests spécifiques qui en dépendent auront des fixtures plus complètes.
if 'numpy' not in sys.modules:
    try:
        from . import numpy_mock
        sys.modules['numpy'] = numpy_mock
        log.info("Mock 'numpy_mock' appliqué pour NumPy.")
    except ImportError:
        sys.modules['numpy'] = MagicMock()
        log.warning("tests.mocks.numpy_mock non trouvé, utilisation de MagicMock pour NumPy.")

# --- Mock de JPype ---
# De même, appliquer un mock pour JPype pour éviter les erreurs d'initialisation de la JVM.
if 'jpype' not in sys.modules:
    try:
        from . import jpype_mock
        sys.modules['jpype'] = jpype_mock
        sys.modules['jpype1'] = jpype_mock # Assurer la compatibilité pour les deux noms
        log.info("Mock 'jpype_mock' appliqué pour JPype et JPype1.")
    except ImportError:
        sys.modules['jpype'] = MagicMock()
        sys.modules['jpype1'] = MagicMock()
        log.warning("tests.mocks.jpype_mock non trouvé, utilisation de MagicMock pour JPype.")

log.info("Bootstrap des mocks terminé.")
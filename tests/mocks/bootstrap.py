import sys
import logging
import os
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
        from .numpy_mock import numpy_mock_instance
        sys.modules['numpy'] = numpy_mock_instance
        log.info("Instance 'numpy_mock_instance' appliquée pour NumPy.")
    except ImportError:
        sys.modules['numpy'] = MagicMock()
        log.warning("tests.mocks.numpy_mock non trouvé, utilisation de MagicMock pour NumPy.")

# --- Mock de JPype ---
# De même, appliquer un mock pour JPype pour éviter les erreurs d'initialisation de la JVM.
if os.environ.get('PYTEST_DISABLE_JPYPE_MOCK') == '1':
    log.warning("Le mock JPype est DÉSACTIVÉ via la variable d'environnement PYTEST_DISABLE_JPYPE_MOCK.")
else:
    if 'jpype' not in sys.modules:
        try:
            from .jpype_mock import jpype_mock
            sys.modules['jpype'] = jpype_mock
            sys.modules['jpype1'] = jpype_mock # Assurer la compatibilité pour les deux noms
            log.info("Mock 'jpype_mock' appliqué pour JPype et JPype1.")
        except ImportError:
            sys.modules['jpype'] = MagicMock()
            sys.modules['jpype1'] = MagicMock()
            log.warning("tests.mocks.jpype_mock non trouvé, utilisation de MagicMock pour JPype.")

log.info("Bootstrap des mocks terminé.")
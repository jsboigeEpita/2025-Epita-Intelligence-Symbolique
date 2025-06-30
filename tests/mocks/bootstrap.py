import sys
import logging
import os
from unittest.mock import MagicMock

# Configurer un logger de base pour le bootstrapping
logging.basicConfig(level=logging.INFO, format='%(asctime)s [BOOTSTRAP] [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

log.info("Démarrage du bootstrap des mocks.")

# --- Mock de NumPy (Désactivé) ---
# Le mock est désactivé car il est trop complexe à maintenir et provoque des
# erreurs d'importation avec pandas et matplotlib. La solution est d'installer
# numpy dans l'environnement de test.
#if 'numpy' not in sys.modules:
#    try:
#        from .numpy_mock import numpy_mock_instance
#        sys.modules['numpy'] = numpy_mock_instance
#        # Enregistrer explicitement les sous-modules pour que les imports fonctionnent
#        for sub_module_name in ['core', '_core', 'linalg', 'fft', 'random', 'rec', 'lib', 'typing']:
#            if hasattr(numpy_mock_instance, sub_module_name):
#                sys.modules[f'numpy.{sub_module_name}'] = getattr(numpy_mock_instance, sub_module_name)
#        log.info("Instance 'numpy_mock_instance' et ses sous-modules appliqués pour NumPy.")
#    except ImportError:
#        sys.modules['numpy'] = MagicMock()
#        log.warning("tests.mocks.numpy_mock non trouvé, utilisation de MagicMock pour NumPy.")

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
            # Enregistrer les sous-modules nécessaires
            if hasattr(jpype_mock, 'imports'):
                sys.modules['jpype.imports'] = jpype_mock.imports
            if hasattr(jpype_mock, '_core'):
                sys.modules['jpype._core'] = jpype_mock._core
            log.info("Mock 'jpype_mock' et ses sous-modules appliqués pour JPype et JPype1.")
        except ImportError:
            sys.modules['jpype'] = MagicMock()
            sys.modules['jpype1'] = MagicMock()
            log.warning("tests.mocks.jpype_mock non trouvé, utilisation de MagicMock pour JPype.")

log.info("Bootstrap des mocks terminé.")
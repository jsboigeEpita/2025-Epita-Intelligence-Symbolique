import os
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package de mocks pour les tests.
"""

import logging
import importlib.util

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Mocks")

# Log de chargement
logger.debug("Package mocks chargé")
# Mock pour semantic_kernel
try:
    import semantic_kernel
except ImportError:
    import sys
    from pathlib import Path
    mock_path = Path(__file__).parent / "semantic_kernel_mock.py"
    spec = importlib.util.spec_from_file_location("semantic_kernel", mock_path)
    semantic_kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(semantic_kernel)
    sys.modules['semantic_kernel'] = semantic_kernel
    sys.modules['semantic_kernel.contents'] = semantic_kernel.contents
    sys.modules['semantic_kernel.functions'] = semantic_kernel.functions
    sys.modules['semantic_kernel.connectors'] = semantic_kernel.connectors
    sys.modules['semantic_kernel.connectors.ai'] = semantic_kernel.connectors.ai
    sys.modules['semantic_kernel.connectors.ai.open_ai'] = semantic_kernel.connectors.ai.open_ai

# Mock pour numpy_mock
try:
    from . import numpy_mock
    import sys
    sys.modules['numpy_mock'] = numpy_mock
except ImportError:
    logger.warning("Impossible d'importer numpy_mock")

# Mock pour pandas_mock
try:
    from . import pandas_mock
    import sys
    sys.modules['pandas_mock'] = pandas_mock
except ImportError:
    logger.warning("Impossible d'importer pandas_mock")

# Mock pour NetworkX
try:
    import networkx
    logger.info("NetworkX déjà installé")
except ImportError:
    try:
        from . import networkx_mock
        import sys
        sys.modules['networkx'] = networkx_mock
        logger.info("Mock NetworkX activé")
    except ImportError:
        logger.warning("Impossible d'importer networkx_mock")

# Mock pour JPype
# Vérifier si la vraie JVM a été initialisée par le conftest racine
# ou si une variable d'environnement force l'utilisation du vrai JPype.
# JPYPE_REAL_JVM_INITIALIZED est défini par le conftest racine.
# USE_REAL_JPYPE_FORCE peut être défini manuellement pour débogage.
real_jvm_was_initialized = os.environ.get("JPYPE_REAL_JVM_INITIALIZED") == "1"
force_real_jpype = os.environ.get("USE_REAL_JPYPE_FORCE") == "1"

if real_jvm_was_initialized or force_real_jpype:
    if real_jvm_was_initialized:
        logger.info("Mock JPype NON activé car la VRAIE JVM a été initialisée par le conftest racine.")
    if force_real_jpype:
        logger.info("Mock JPype NON activé car USE_REAL_JPYPE_FORCE=1.")
    # S'assurer que le vrai jpype est utilisé si déjà importé, sinon l'importer.
    if 'jpype' not in sys.modules:
        try:
            import jpype
            logger.info("Vrai module JPype importé car mock désactivé.")
        except ImportError:
            logger.error("ERREUR CRITIQUE: Vrai JPype non trouvé et mock désactivé.")
    else:
        # Vérifier si le jpype dans sys.modules est le vrai ou le mock
        current_jpype = sys.modules['jpype']
        module_path = getattr(current_jpype, '__file__', '')
        if 'jpype_mock.py' in module_path:
            logger.warning("ATTENTION: Le mock JPype était déjà dans sys.modules mais on force le vrai JPype. Tentative de restauration (peut être instable).")
            # Tentative de suppression du mock pour forcer la réimportation du vrai.
            # Cela est risqué si d'autres modules détiennent des références au mock.
            del sys.modules['jpype']
            if 'jpype1' in sys.modules and getattr(sys.modules['jpype1'], '__file__', '') == module_path:
                del sys.modules['jpype1']
            try:
                import jpype # Réimporter le vrai
                logger.info("Vrai module JPype réimporté après suppression du mock.")
            except ImportError:
                 logger.error("ERREUR CRITIQUE: Impossible de réimporter le vrai JPype après suppression du mock.")
        else:
            logger.info("Vrai module JPype déjà présent dans sys.modules.")

else:
    logger.info("Tentative d'activation du mock JPype (la vraie JVM n'a pas été signalée comme initialisée par le conftest racine ET USE_REAL_JPYPE_FORCE n'est pas à 1).")
    try:
        # Essayer d'importer le vrai jpype d'abord pour voir s'il est installé
        import jpype as real_jpype_module
        jpype_real_path = getattr(real_jpype_module, '__file__', 'N/A')
        logger.info(f"Vrai JPype trouvé ({jpype_real_path}). Le mock ne sera PAS activé par défaut pour 'jpype' à moins que 'jpype1' ne soit pas trouvé.")
        # Le comportement original était de mocker 'jpype' seulement si 'jpype1' n'était pas trouvé.
        # On garde cette logique si on n'est pas dans un cas de forçage du vrai JPype.
        try:
            import jpype1 # Tenter d'importer jpype1
            logger.info("Module 'jpype1' trouvé. Le mock JPype ne sera pas activé pour 'jpype' ou 'jpype1'.")
        except ImportError:
            logger.info("Module 'jpype1' non trouvé. Activation du mock JPype pour 'jpype' et 'jpype1'.")
            from . import jpype_mock
            sys.modules['jpype1'] = jpype_mock
            sys.modules['jpype'] = jpype_mock
            logger.info("Mock JPype activé pour 'jpype' et 'jpype1' car 'jpype1' est manquant.")

    except ImportError:
        # Le vrai jpype n'est pas installé, donc on peut mocker sans risque.
        logger.info("Vrai module JPype non trouvé (ImportError). Activation du mock JPype.")
        try:
            from . import jpype_mock
            # sys.modules['jpype1'] = jpype_mock # jpype1 n'est pas le nom standard
            sys.modules['jpype'] = jpype_mock
            logger.info("Mock JPype activé pour 'jpype'.")
        except ImportError:
            logger.warning("Impossible d'importer jpype_mock.")

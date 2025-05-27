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
try:
    import jpype1
    logger.info("JPype1 déjà installé")
except ImportError:
    try:
        from . import jpype_mock
        import sys
        sys.modules['jpype1'] = jpype_mock
        sys.modules['jpype'] = jpype_mock
        logger.info("Mock JPype activé")
    except ImportError:
        logger.warning("Impossible d'importer jpype_mock")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package de mocks pour les tests.
"""

import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Mocks")

# Log de chargement
logger.debug("Package mocks chargé")
# -*- coding: utf-8 -*-
"""
Module de pré-amorçage (pre-bootstrap).

Ce module a pour unique but d'importer les bibliothèques lourdes de Machine Learning
(comme torch, transformers, numpy) dans un ordre contrôlé AVANT toute autre
opération, en particulier avant l'initialisation de la JVM via JPype.

Ceci est nécessaire pour éviter des conflits de bibliothèques natives sous Windows,
qui peuvent mener à un crash de type "Windows fatal exception: access violation".

Ce module doit être le TOUT PREMIER import dans les points d'entrée de l'application.
"""
import logging
import time

logger = logging.getLogger(__name__)

# Mettre en place un logger de base si aucun n'est configuré
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [PreBootstrap] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

logger.info("Début du pré-chargement des bibliothèques de bas niveau...")
start_time = time.time()

try:
    import torch
    logger.info("-> torch importé avec succès.")
except ImportError as e:
    logger.warning(f"torch n'a pas pu être importé : {e}")

try:
    import numpy
    logger.info("-> numpy importé avec succès.")
except ImportError as e:
    logger.warning(f"numpy n'a pas pu être importé : {e}")

try:
    import transformers
    logger.info("-> transformers importé avec succès.")
except ImportError as e:
    logger.warning(f"transformers n'a pas pu être importé : {e}")

end_time = time.time()
logger.info(f"Pré-chargement terminé en {end_time - start_time:.2f} secondes.")
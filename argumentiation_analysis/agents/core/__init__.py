"""
Module core des agents contenant les implémentations de base des agents.

Ce module fournit les implémentations de base des différents agents
utilisés dans le système d'analyse argumentative.
"""

# Importations des sous-modules
try:
    from . import extract
except ImportError as e:
    import logging
    logging.warning(f"Le sous-module 'extract' de 'agents.core' n'a pas pu être importé: {e}")
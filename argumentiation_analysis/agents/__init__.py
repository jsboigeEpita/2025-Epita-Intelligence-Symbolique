"""
Module agents contenant les définitions des agents spécialisés.

Ce module inclut les différents agents utilisés dans le système d'analyse argumentative,
tels que les agents d'extraction, les agents de logique propositionnelle, etc.
"""

# Importations des sous-modules
try:
    import argumentiation_analysis.core
    from . import extract  # Importer explicitement le module extract
except ImportError as e:
    import logging
    logging.warning(f"Un sous-module de 'agents' n'a pas pu être importé: {e}")

# Note: Le module 'extract' est maintenant un vrai module dans le répertoire 'agents'
# et non plus une classe de redirection
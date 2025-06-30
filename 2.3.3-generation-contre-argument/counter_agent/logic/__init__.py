"""
Module de validation logique des arguments et contre-arguments.

Ce module fournit des outils pour valider la cohérence logique
des arguments et contre-arguments en utilisant des frameworks
de raisonnement formel comme TweetyProject.
"""

from .validator import CounterArgumentValidator
from .tweety_bridge import TweetyBridge

__all__ = [
    'CounterArgumentValidator',
    'TweetyBridge'
] 
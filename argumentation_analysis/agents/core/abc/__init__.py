"""
Package `abc` (Abstract Base Classes) pour les agents principaux.

Ce package définit les classes de base abstraites qui servent de contrats
pour les différents types d'agents implémentés dans le système d'analyse
argumentative. Ces classes de base assurent une interface commune et
favorisent la modularité et l'extensibilité des agents.

Modules exportés (exemples) :
    - `agent_bases`: Contient les définitions des classes de base comme
                     `BaseAgent` et `BaseLogicAgent`.
"""

from . import agent_bases

__all__ = ["agent_bases"]

# argumentation_analysis/orchestration/hierarchical/tactical/manager.py
"""
Module servant de point d'entrée pour le TacticalManager.
Il s'agit d'un alias pour TacticalCoordinator (lui-même un alias de TaskCoordinator).
"""

from .coordinator import TacticalCoordinator as TacticalManager

__all__ = ["TacticalManager"]

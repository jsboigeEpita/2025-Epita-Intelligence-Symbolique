# argumentation_analysis/agents/core/logic/__init__.py
"""
Package pour les agents de logique généralisés supportant différents types de logiques.

Ce package contient les implémentations des agents logiques pour différents types de logiques :
- Logique propositionnelle
- Logique du premier ordre
- Logique modale
- Description Logic (ALC ontological reasoning)
- Conditional Logic (non-monotonic reasoning)

It also provides handlers for SAT solving, Dung argumentation frameworks,
and a factory for creating appropriate agents.
"""

from .propositional_logic_agent import PropositionalLogicAgent
from .fol_logic_agent import FOLLogicAgent
from .modal_logic_agent import ModalLogicAgent
from .logic_factory import LogicAgentFactory
from .belief_set import (
    BeliefSet,
    PropositionalBeliefSet,
    FirstOrderBeliefSet,
    ModalBeliefSet,
)
from .query_executor import QueryExecutor

__all__ = [
    "PropositionalLogicAgent",
    "FOLLogicAgent",
    "ModalLogicAgent",
    "LogicAgentFactory",
    "BeliefSet",
    "PropositionalBeliefSet",
    "FirstOrderBeliefSet",
    "ModalBeliefSet",
    "QueryExecutor",
    "DLHandler",
    "CLHandler",
]


# Lazy imports for handlers requiring JVM (avoid import errors when JVM not started)
def __getattr__(name):
    if name == "DLHandler":
        from .dl_handler import DLHandler

        return DLHandler
    if name == "CLHandler":
        from .cl_handler import CLHandler

        return CLHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

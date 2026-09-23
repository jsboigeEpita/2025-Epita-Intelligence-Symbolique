# -*- coding: utf-8 -*-
"""
#2358 — le contrat déclaré par ``oracle/interfaces.py`` est VIVANT : les
implémentations de production en héritent, et chaque membre déclaré colle à
l'implémentation réelle.

L'historique qui motive la garde : le contrat divergeait sur trois membres et
avait **licencié** le défaut de #2340 — un appel sync vers un
``check_permission`` async, exactement ce que la déclaration affirmait
(sync, str). Une coroutine non attendue est truthy : le contrôle de
permission répondait « autorisé » sur tout refus. Un contrat sans exécutant
endosse les bugs au lieu de les attraper.

Ce que la garde mesure (en valeurs, jamais en ImportError) :
1. ``OracleBaseAgent`` hérite de ``OracleAgentInterface`` et
   ``DatasetAccessManager`` de ``DatasetManagerInterface`` ;
2. pour CHAQUE membre abstrait déclaré, l'implémentation réelle a la même
   async-ité et la même signature que la déclaration.

Témoin négatif obligatoire : le vérificateur lui-même est testé — une
implémentation volontairement désynchronisée DOIT produire des violations
(sans lui, un vert pourrait signifier « le vérificateur ne voit rien »).
Témoin positif : une paire conforme produit zéro violation.
"""

import inspect
from abc import ABC

from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    DatasetAccessManager,
)
from argumentation_analysis.agents.core.oracle.interfaces import (
    DatasetManagerInterface,
    OracleAgentInterface,
)
from argumentation_analysis.agents.core.oracle.oracle_base_agent import (
    OracleBaseAgent,
)


def conformance_violations(interface_cls: type, impl_cls: type) -> list:
    """Violations (membre → déclaration vs implémentation) pour une paire.

    Compare l'async-ité et la signature complète de chaque membre abstrait
    déclaré à la méthode réelle de l'implémentation.
    """
    problems: list = []
    for name in sorted(getattr(interface_cls, "__abstractmethods__", ())):
        declared = getattr(interface_cls, name, None)
        actual = getattr(impl_cls, name, None)
        if declared is None or actual is None:
            problems.append(
                f"{name}: absent ({'déclaration' if declared is None else 'implémentation'})"
            )
            continue
        if inspect.iscoroutinefunction(declared) != inspect.iscoroutinefunction(actual):
            problems.append(
                f"{name}: déclaré "
                f"{'async' if inspect.iscoroutinefunction(declared) else 'sync'} "
                f"mais implémenté "
                f"{'async' if inspect.iscoroutinefunction(actual) else 'sync'}"
            )
        declared_sig = str(inspect.signature(declared))
        actual_sig = str(inspect.signature(actual))
        if declared_sig != actual_sig:
            problems.append(
                f"{name}: déclaré {declared_sig} mais implémenté {actual_sig}"
            )
    return problems


def test_production_classes_inherit_the_contracts():
    """Le contrat a des exécutants de production — sinon il ne peut pas rougir."""
    assert issubclass(OracleBaseAgent, OracleAgentInterface), (
        "OracleBaseAgent n'hérite pas de OracleAgentInterface : le contrat "
        "déclaré n'a aucun exécutant de production (#2358)"
    )
    assert issubclass(DatasetAccessManager, DatasetManagerInterface), (
        "DatasetAccessManager n'hérite pas de DatasetManagerInterface : le "
        "contrat déclaré n'a aucun exécutant de production (#2358)"
    )


def test_every_declared_member_matches_the_implementation():
    """Chaque membre déclaré = l'implémentation réelle (async-ité + signature)."""
    oracle_problems = conformance_violations(OracleAgentInterface, OracleBaseAgent)
    dataset_problems = conformance_violations(
        DatasetManagerInterface, DatasetAccessManager
    )
    assert not oracle_problems + dataset_problems, (
        "Le contrat oracle/interfaces.py diverge de l'implémentation :\n  - "
        + "\n  - ".join(oracle_problems + dataset_problems)
    )


def test_check_permission_is_declared_async_the_2340_lesson():
    """#2340 encodé : check_permission est async au contrat ET à l'implémentation.

    Un appel sync vers une coroutine async rend la coroutine truthy — le
    contrôle de permission répond « autorisé » sur tout refus. La déclaration
    sync d'origine avait endossé ce défaut.
    """
    assert inspect.iscoroutinefunction(DatasetManagerInterface.check_permission), (
        "DatasetManagerInterface.check_permission est déclaré sync : c'est la "
        "déclaration qui a licencié le défaut #2340 (coroutine truthy = "
        "permission toujours accordée)"
    )
    assert inspect.iscoroutinefunction(DatasetAccessManager.check_permission)


# ---------------------------------------------------------------------------
# Contrôles du vérificateur — sans eux, un vert ne prouve rien.
# ---------------------------------------------------------------------------


def _make_pair(declared_async: bool, impl_async: bool, declared_ann, impl_ann):
    """Petite paire interface/impl synthétique, conformité pilotable."""

    def _build(is_async: bool, ann):
        if is_async:

            async def run(self, x: ann):
                return x

        else:

            def run(self, x: ann):
                return x

        return run

    class DeclaredI(ABC):
        run = _build(declared_async, declared_ann)

    DeclaredI.__abstractmethods__ = frozenset({"run"})

    class ImplC:
        run = _build(impl_async, impl_ann)

    return DeclaredI, ImplC


def test_the_checker_detects_a_desynchronized_signature():
    """Témoin négatif : sync-vs-async et str-vs-QueryType DOivent produire des violations."""
    from argumentation_analysis.agents.core.oracle.permissions import QueryType

    declared, impl = _make_pair(
        declared_async=True, impl_async=False, declared_ann=QueryType, impl_ann=str
    )
    problems = conformance_violations(declared, impl)
    assert (
        len(problems) == 2
    ), f"le vérificateur devait voir async-ité + signature, vu : {problems}"
    assert any("async" in p for p in problems)
    assert any("QueryType" in p and "str" in p for p in problems)


def test_the_checker_stays_silent_on_a_conforming_pair():
    """Témoin positif : une paire conforme produit zéro violation."""
    from argumentation_analysis.agents.core.oracle.permissions import QueryType

    declared, impl = _make_pair(
        declared_async=True, impl_async=True, declared_ann=QueryType, impl_ann=QueryType
    )
    assert conformance_violations(declared, impl) == []

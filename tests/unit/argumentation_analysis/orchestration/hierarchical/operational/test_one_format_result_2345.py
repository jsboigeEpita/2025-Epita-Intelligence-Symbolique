# -*- coding: utf-8 -*-
"""#2345 — les agents opérationnels formatent leurs résultats par une seule définition.

Les quatre adaptateurs de ``operational/adapters/`` portaient chacun une copie
de ``format_result`` (même empreinte AST), qui surchargeait celle
d'``OperationalAgent`` et en avait dérivé. Les copies vidaient la clé ``type``
des résultats de l'appelant (``pop``) et rangeaient un résultat sans type sous
``"unknown"``, là où le père le jetait sans trace. Seules les copies tournaient
en production (``ServiceManager`` → ``OperationalManager`` →
``OperationalAgentRegistry``) : leur comportement est conservé, sans la mutation.

La population est la table de construction de production
(``OperationalAgentRegistry().agent_classes``), pas une liste recopiée ici : un
adaptateur ajouté à la table entre dans le garde sans qu'on l'édite.
"""

import copy

import pytest

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import (
    OperationalAgent,
)
from argumentation_analysis.orchestration.hierarchical.operational.agent_registry import (
    OperationalAgentRegistry,
)

PRODUCTION_CLASSES = dict(OperationalAgentRegistry().agent_classes)

RESULTS = [
    {"type": "extracts", "value": 1},
    {"type": "extracts", "value": 2},
    {"type": "fallacies", "name": "x"},
    {"value": "untyped"},
]


def test_population_is_the_production_table():
    # Non-vacuité : sans ce plancher, une table vide rendrait les tests
    # paramétrés muets et le garde d'unicité vert.
    assert len(PRODUCTION_CLASSES) >= 4, PRODUCTION_CLASSES


def test_every_production_agent_formats_through_the_one_definition():
    overriding = sorted(
        name
        for name, cls in PRODUCTION_CLASSES.items()
        if cls.format_result is not OperationalAgent.format_result
    )
    assert overriding == [], (
        f"ces agents redéfinissent format_result au lieu d'hériter de "
        f"OperationalAgent : {overriding}"
    )


@pytest.fixture(params=sorted(PRODUCTION_CLASSES))
def format_result(request):
    # La méthode telle que la classe de production la résout ; elle ne lit
    # pas ``self``.
    method = PRODUCTION_CLASSES[request.param].format_result
    return lambda *args: method(None, *args)


def test_results_are_grouped_by_type_without_the_key(format_result):
    out = format_result(
        {"id": "t1", "tactical_task_id": "tt1"}, copy.deepcopy(RESULTS), {"m": 1}, []
    )

    assert out["outputs"]["extracts"] == [{"value": 1}, {"value": 2}]
    assert out["outputs"]["fallacies"] == [{"name": "x"}]
    assert out["id"] == "result-t1"
    assert out["task_id"] == "t1"
    assert out["tactical_task_id"] == "tt1"
    assert out["status"] == "completed"
    assert out["metrics"] == {"m": 1}


def test_an_untyped_result_is_kept_under_unknown(format_result):
    out = format_result({"id": "t1"}, copy.deepcopy(RESULTS), {}, [])

    assert out["outputs"]["unknown"] == [{"value": "untyped"}]


def test_the_callers_results_are_not_mutated(format_result):
    results = copy.deepcopy(RESULTS)

    format_result({"id": "t1"}, results, {}, [])

    assert results == RESULTS


def test_the_reported_id_and_the_issues_status(format_result):
    issues = [{"type": "execution_error", "description": "boom"}]

    out = format_result({"id": "t1"}, [], {}, issues, "t-override")

    assert out["id"] == "result-t-override"
    assert out["task_id"] == "t-override"
    assert out["status"] == "completed_with_issues"
    assert out["issues"] == issues
    assert out["outputs"] == {}

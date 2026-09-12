# -*- coding: utf-8 -*-
"""#2180 — `RESULTS_DIR` (un Path) ne sert plus de clé de contenu.

Même famille de défaut que #2177 (`DATA_DIR`) : `RESULTS_DIR` est un
``pathlib.Path`` utilisé comme clé de dictionnaire dans des charges utiles de
messages et de résultats. Écrivains et lecteurs étant orphelins de part et
d'autre (aucun consommateur du type ``objective_completion``, aucun écrivain
de la clé dans les retours de ``process_task``), rien ne cassait visiblement —
mais toute frontière JSON lève ``TypeError: keys must be str... not
WindowsPath``. Ces gardes fixent le contrat : la charge de résultats vit sous
la clé chaîne ``"results"`` (clé nommée : elle siège À CÔTÉ de clés nommées
dans le payload, pas au niveau où ``#2177`` a posé ``"data"``).
"""

import json
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import (
    TaskCoordinator,
)
from argumentation_analysis.orchestration.hierarchical.templates.analysis_tool_template import (
    BaseAnalysisTool,
)
from argumentation_analysis.orchestration.hierarchical.templates.analysis_type_template import (
    BaseAnalysisType,
)


def make_mock_middleware():
    m = MagicMock()
    m.send_message.return_value = True
    m.publish.return_value = []
    m.global_handlers = []
    return m


def sent_messages(mock_mw):
    return [c.args[0] for c in mock_mw.send_message.call_args_list if c.args]


def make_coordinator_with_objective_done(mock_mw, objective_results):
    state = MagicMock()
    state.get_objective_for_task.return_value = "obj-1"
    state.are_all_tasks_for_objective_done.return_value = True
    state.get_objective_results.return_value = objective_results
    return TaskCoordinator(tactical_state=state, middleware=mock_mw)


class TestCoordinatorReportWriter:
    def test_objective_completion_report_serializes(self):
        """Le rapport objective_completion doit franchir la frontière JSON.

        Le coordinateur écrit les résultats de l'objectif sous une clé du
        contenu du message (``send_report``) : cette clé doit être une chaîne,
        sinon ``json.dumps(Message.to_dict())`` lève (#2180).
        """
        mock_mw = make_mock_middleware()
        objective_results = {"findings": ["f1"], "score": 0.8}
        coordinator = make_coordinator_with_objective_done(mock_mw, objective_results)

        coordinator.handle_task_result(
            {
                "tactical_task_id": "task-1",
                "completion_status": "completed",
            }
        )

        reports = [
            m
            for m in sent_messages(mock_mw)
            if m.content.get("report_type") == "objective_completion"
        ]
        assert (
            reports
        ), "handle_task_result doit émettre le rapport objective_completion"
        round_tripped = json.loads(
            json.dumps(reports[0].to_dict())
        )  # TypeError si clé Path (#2180)
        payload = round_tripped["content"]["data"]
        assert payload["results"] == objective_results


class TestTemplateWriters:
    def test_analysis_tool_get_results_serializes(self):
        results = BaseAnalysisTool({"name": "my_tool"}).get_results()
        round_tripped = json.loads(json.dumps(results))
        assert round_tripped["tool"] == "my_tool"
        assert round_tripped["results"] == {}

    def test_analysis_type_expected_results_serializes(self):
        results = BaseAnalysisType({"name": "my_type"}).get_expected_results()
        round_tripped = json.loads(json.dumps(results))
        assert round_tripped["analysis_type"] == "my_type"
        assert round_tripped["results"] == {}

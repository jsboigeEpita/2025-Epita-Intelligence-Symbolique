# -*- coding: utf-8 -*-
"""#2346 (`agents/core/logic/query_executor.py:28`): a service's health reads what the service needs.

``LogicService`` builds a ``QueryExecutor`` and, in production, uses it for one
thing only: ``is_healthy`` checked that the object existed. An object is always
truthy, so the MCP server's health dict said ``logic: True`` whenever the
service had been built, including when the JVM its logic agents need was not
ready (jpype absent, or ``DISABLE_JAVA_LOGIC=1``). ``QueryExecutor.execute_query``
has no production caller, so its ``FUNC_ERROR`` was never the signal either.

``ValidationService`` scores arguments with keyword heuristics and reads nothing
from its ``LogicService`` except that health. Once logic health tells the truth,
tying validation's health to it would report validation down while it works.
"""

from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.logic.query_executor import QueryExecutor
from argumentation_analysis.agents.core.logic.tweety_bridge import (
    _DegradedInitializer,
)
from argumentation_analysis.services.web_api.models.request_models import (
    ValidationRequest,
)
from argumentation_analysis.services.web_api.services import logic_service
from argumentation_analysis.services.web_api.services.validation_service import (
    ValidationService,
)


class _ReadyInitializer:
    def is_jvm_ready(self) -> bool:
        return True


def _executor(initializer) -> QueryExecutor:
    # The real class, with a bridge stand-in that only carries the initializer:
    # ``QueryExecutor`` reads nothing else from its bridge before a query.
    executor = QueryExecutor.__new__(QueryExecutor)
    executor._logger = logic_service.logging.getLogger("test")
    executor._tweety_bridge = SimpleNamespace(initializer=initializer)
    return executor


def _logic_service(monkeypatch, initializer) -> "logic_service.LogicService":
    monkeypatch.setattr(logic_service, "QueryExecutor", lambda: _executor(initializer))
    return logic_service.LogicService(llm_service=None)


def test_logic_is_not_healthy_when_the_jvm_is_not_ready(monkeypatch):
    service = _logic_service(monkeypatch, _DegradedInitializer())
    assert service.is_healthy() is False


def test_logic_is_healthy_when_the_jvm_is_ready(monkeypatch):
    service = _logic_service(monkeypatch, _ReadyInitializer())
    assert service.is_healthy() is True


def test_the_executor_answers_and_reports_from_the_same_probe():
    executor = _executor(_DegradedInitializer())
    belief_set = SimpleNamespace(logic_type="propositional")
    result, message = executor.execute_query(belief_set, "a")
    assert executor.is_ready() is False
    assert result is None and message.startswith("FUNC_ERROR")


async def test_validation_works_and_says_so_when_logic_is_down(monkeypatch):
    logic = _logic_service(monkeypatch, _DegradedInitializer())
    validation = ValidationService(logic_service=logic)

    response = await validation.validate_argument(
        ValidationRequest(
            premises=["Tous les hommes sont mortels", "Socrate est un homme"],
            conclusion="Donc Socrate est mortel",
            argument_type="deductive",
        )
    )

    assert response.success is True
    assert validation.is_healthy() is True

# -*- coding: utf-8 -*-
"""
CC #1531 item 3 — unit tests for ``StrategicManager._formulate_conclusion``.

The conclusion must cite REAL elements (objective descriptions + measured
production count + strengths/weaknesses), not a generic phrase keyed solely on
``overall_success_rate``.

These tests exercise the REAL ``StrategicManager._formulate_conclusion`` in
isolation (sync, no middleware side-effects). They live in a dedicated module
WITHOUT ``pytestmark = pytest.mark.asyncio`` so the sync test functions do not
inherit an asyncio mark they cannot satisfy — keeping the suite warning-clean.

SDD grounding: ``_evaluate_results_against_objectives`` (manager.py) already
computes ``strengths``/``weaknesses`` from real per-objective rates
(>=0.8 → strength, <=0.4 → weakness). ``_formulate_conclusion`` draws the
conclusion from that ``evaluation`` dict, so the cited elements are measured,
not fabricated.
"""

from unittest.mock import MagicMock


def _real_strategic_manager(objectives):
    """A real ``StrategicManager`` with a mocked middleware (no
    ``create_default_middleware`` side-effect) and controlled objectives.

    ``_formulate_conclusion`` touches neither middleware nor adapter, so the
    mock isolates the test from the network/middleware while exercising the
    real logic.
    """
    from argumentation_analysis.orchestration.hierarchical.strategic.manager import (
        StrategicManager,
    )
    from argumentation_analysis.orchestration.hierarchical.strategic.state import (
        StrategicState,
    )

    state = StrategicState()
    state.global_objectives = objectives
    return StrategicManager(strategic_state=state, middleware=MagicMock())


def test_formulate_conclusion_cites_real_objectives():
    """The conclusion cites the real objectives (descriptions) and the measured
    production, not a rate-keyed generic phrase.

    Before, three fixed phrases carried no finding — a starved run
    (``success_rate=1.0`` on unproductive tasks) still earned « Analyse
    réussie avec une performance globale élevée ». ``evaluation`` already
    carries the real measurements (per-objective rates + descriptions in
    strengths/weaknesses), so the conclusion cites them.
    """
    manager = _real_strategic_manager(
        [
            {
                "id": "obj-fallacy",
                "description": "Détecter les sophismes",
                "priority": "high",
            },
            {
                "id": "obj-args",
                "description": "Extraire les arguments",
                "priority": "high",
            },
        ]
    )
    # obj-fallacy produced (1.0 → strength), obj-args failed (0.0 → weakness).
    results = {"obj-fallacy": {"success_rate": 1.0}, "obj-args": {"success_rate": 0.0}}
    evaluation = manager._evaluate_results_against_objectives(results)
    conclusion = manager._formulate_conclusion(results, evaluation)

    # Cites a real objective description, not a free-floating adjective.
    assert (
        "sophisme" in conclusion.lower() or "argument" in conclusion.lower()
    ), f"conclusion cites no real objective: {conclusion!r}"
    # Anchored in the measured production count (1/2 productive).
    assert (
        "1/2" in conclusion
    ), f"conclusion not anchored in measured production: {conclusion!r}"
    # obj-args failed (0.0) is a weakness cited honestly.
    assert (
        "argument" in conclusion.lower()
    ), f"the weakness (objective « Extraire les arguments » failed) is not cited: {conclusion!r}"


def test_formulate_conclusion_honest_when_nothing_measured():
    """Anti-pendule: no objective measured → honest, no fabricated verdict.

    « No objective measured » is not « zero findings »: the former is the
    absence of analysis, the latter a result. The conclusion must not fabricate
    an adjective over an objectives void.
    """
    manager = _real_strategic_manager([])
    conclusion = manager._formulate_conclusion(
        {}, manager._evaluate_results_against_objectives({})
    )
    assert (
        "aucun objectif" in conclusion.lower()
    ), f"conclusion fabricates a verdict with no measured objective: {conclusion!r}"


def test_formulate_conclusion_clean_corpus_is_success_not_gap():
    """Mirror anti-pendule guard: a run where everything produced (1.0) on a
    clean corpus is a SUCCESS — the conclusion carries the « élevée »
    qualifier, not a pseudo-failure. Do not confuse « 0 finding » with
    « failure ».
    """
    manager = _real_strategic_manager(
        [
            {
                "id": "obj-clean",
                "description": "Analyser un corpus propre",
                "priority": "high",
            }
        ]
    )
    results = {"obj-clean": {"success_rate": 1.0}}
    evaluation = manager._evaluate_results_against_objectives(results)
    conclusion = manager._formulate_conclusion(results, evaluation)

    assert "élevée" in conclusion.lower(), (
        f"a fully productive run (clean corpus, 0 finding) must read as a "
        f"success, not a failure: {conclusion!r}"
    )
    assert (
        "difficultés" not in conclusion.lower()
    ), f"a fully productive run must not be degraded: {conclusion!r}"

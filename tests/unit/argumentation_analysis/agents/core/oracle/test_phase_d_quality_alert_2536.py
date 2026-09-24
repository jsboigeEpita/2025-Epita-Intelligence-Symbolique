"""#2536: the low-quality alert of the Phase D metrics named a logger nobody bound.

``calculate_ideal_trace_metrics`` alerts below a 7.0 score through
``logger_main.critical``, a name defined nowhere in its module. Every trace
scoring under the threshold therefore raised a NameError instead of returning
its metrics. ``CluedoOracleState.get_ideal_trace_metrics`` is this method once
``phase_d_extensions`` patches the class at import, so
``validate_phase_d_requirements`` failed the same way.
"""

import logging

from argumentation_analysis.agents.core.oracle import phase_d_extensions
from argumentation_analysis.agents.core.oracle.phase_d_extensions import (
    PhaseDExtensions,
)

MESSAGES = [
    {"sender": "Sherlock", "content": "Examinons les indices de la bibliotheque."},
    {"sender": "Watson", "content": "Je note le chandelier pres de la porte."},
]


def test_a_low_score_returns_its_metrics_and_logs_the_alert(caplog):
    with caplog.at_level(logging.CRITICAL, logger=phase_d_extensions.__name__):
        metrics = PhaseDExtensions().calculate_ideal_trace_metrics(
            {"messages": MESSAGES}
        )

    assert metrics["score_trace_ideale"] < 7.0
    alerts = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert len(alerts) == 1
    assert "Narrative quality degradation" in alerts[0].getMessage()


def test_the_oracle_state_metrics_are_this_method():
    from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

    assert (
        CluedoOracleState.get_ideal_trace_metrics.__module__
        == phase_d_extensions.__name__
    )

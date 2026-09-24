"""The governance phase publishes only the consensus metrics it computed (#2344).

The phase hands the plugin a vote result without per-agent satisfaction scores.
``fairness_index`` and ``satisfaction`` then came back as 0.0 ("maximally
unfair, nobody satisfied"), and any failure of the computation was dropped at
debug level. The metrics now say which ones are unavailable and why, and a bug
in the computation fails the phase instead of vanishing.
"""

from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.orchestration.unified_pipeline import _invoke_governance


def _context():
    scores = {
        "arg_1": {"clarte": 9.0, "pertinence": 4.0, "structure": 3.0},
        "arg_2": {"clarte": 5.0, "pertinence": 8.0, "structure": 7.0},
        "arg_3": {"clarte": 2.0, "pertinence": 6.0, "structure": 5.0},
    }
    return {
        "phase_extract_output": {
            "arguments": [{"text": "Arg 1"}, {"text": "Arg 2"}, {"text": "Arg 3"}]
        },
        "phase_quality_output": {
            "per_argument_scores": {
                arg: {"scores_par_vertu": s} for arg, s in scores.items()
            }
        },
    }


def _no_llm():
    return (
        patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, None),
        ),
        patch("openai.AsyncOpenAI", side_effect=RuntimeError("no-network-2344")),
    )


async def test_real_plugin_names_the_metrics_it_could_not_compute():
    client, openai = _no_llm()
    with client, openai:
        result = await _invoke_governance("Test", _context())

    assert result["governance_decided_firsthand"] is True
    metrics = result["consensus_metrics"]
    assert 0.0 <= metrics["consensus_rate"] <= 1.0
    # The vote result carries no satisfaction scores: no 0.0 stands in for them.
    assert "fairness_index" not in metrics
    assert "satisfaction" not in metrics
    assert set(metrics["unavailable"]) == {"fairness_index", "satisfaction"}


async def test_a_failing_metric_computation_fails_the_phase():
    plugin = MagicMock()
    plugin.list_governance_methods.return_value = '["majority", "copeland"]'
    plugin.detect_conflicts_fn.return_value = "[]"
    plugin.compute_consensus_metrics.side_effect = AttributeError("bug in metrics")
    client, openai = _no_llm()
    with client, openai, patch(
        "argumentation_analysis.plugins.governance_plugin.GovernancePlugin",
        return_value=plugin,
    ):
        with pytest.raises(AttributeError, match="bug in metrics"):
            await _invoke_governance("Test", _context())
    plugin.compute_consensus_metrics.assert_called_once()

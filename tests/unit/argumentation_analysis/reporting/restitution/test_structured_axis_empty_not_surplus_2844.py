"""#2844 — an axis the ledger files degraded must not reach the surplus channel.

Two readers read the same run: :func:`_collect_structured_arg_findings` (the
presence channel, whose items become the conclusion's established surplus) and
:func:`_collect_absent_dimensions` (the honest-absence channel, which names the
axes the run did not genuinely evaluate). Measured on the #2841 signatures: 23
of 49 documents cited the weighted axis as **established structural surplus**
while the ledger of that same run filed it ``evaluated_empty`` / degraded — the
translator had supplied weighted attacks and the framework still returned only
empty result sets, so the axis contributed no analysis (#1671, and the writer's
own wording: it "must not be counted as capable"). On those documents the two
readers contradicted each other: named lost in the appendix, counted as
established in the surplus.

The guard pins the agreement on the state that produced it: the surplus
projection of such a state carries NO structural item for that axis, while the
non-evaluated block still names it. Two controls keep the assertions from being
vacuously true (#1019): the SAME state with the ledger marking the axis
``evaluated`` (degraded false) still carries the item, and the absence reader
still names the axis in the degraded case.

Privacy: synthetic atoms only (``claim_alpha``/``claim_beta``), never corpus
tokens.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _ABSENT_DIMENSION_LABELS,
    _axis_label,
    build_act3_evidence,
)
from argumentation_analysis.reporting.restitution.conclusion_salience import (
    projection_from_state,
)

_WEIGHTED = "weighted_argumentation"
_WEIGHTED_LABEL = _axis_label(_WEIGHTED)
_STRUCTURAL = "structural"


def _weighted_sidecar() -> dict:
    """The sidecar ``_write_weighted_to_state`` attaches (#1648 Wave-2)."""
    return {
        "dung_1": {
            "name": "weighted_grounded",
            "formalism_specific": {
                "attack_weights": [
                    {"source": "claim_alpha", "target": "claim_beta", "weight": 0.3},
                    {"source": "claim_gamma", "target": "claim_delta", "weight": 0.9},
                ]
            },
        }
    }


def _state(ledger_entry: dict | None) -> SimpleNamespace:
    """A run whose weighted sidecar is populated and whose ledger says ``ledger_entry``."""
    state = SimpleNamespace(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks=_weighted_sidecar(),
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    if ledger_entry is not None:
        state.structured_arg_status = {_WEIGHTED: ledger_entry}
    return state


def _evaluated_empty() -> dict:
    """What ``_record_structured_arg_status`` writes when only empty sets came back."""
    return {
        "capability": _WEIGHTED,
        "status": "evaluated_empty",
        "degraded": True,
        "reason": (
            "Genuine structured input was supplied, but the weighted framework "
            "returned no non-empty result set (1 returned, all empty) — nothing "
            "was accepted, excluded or arbitrated."
        ),
        "extension_count": 1,
    }


def _evaluated() -> dict:
    """The same axis, genuinely evaluated — the non-vacuity control."""
    return {
        "capability": _WEIGHTED,
        "status": "evaluated",
        "degraded": False,
        "reason": (
            "Genuine structured input supplied via context; the framework "
            "returned 1 non-empty result set(s)."
        ),
        "extension_count": 1,
    }


class TestEmptyResultSetsAreNotEstablishedSurplus:
    """The presence channel drops the axis; the absence channel keeps naming it."""

    def test_surplus_projection_carries_no_structural_item(self) -> None:
        state = _state(_evaluated_empty())
        proj = projection_from_state(state)
        cited = [
            item for item in proj["established_items"] if item["nature"] == _STRUCTURAL
        ]
        assert cited == [], (
            "the weighted axis returned only empty result sets on this run; its "
            f"finding must not be counted as established surplus, got {cited}"
        )
        assert proj["established_by_nature"].get(_STRUCTURAL, 0) == 0
        assert proj["carries_non_procedural_surplus"] is False

    def test_the_finding_itself_is_not_collected(self) -> None:
        state = _state(_evaluated_empty())
        capabilities = {
            f.capability for f in build_act3_evidence(state).structured_findings
        }
        assert _WEIGHTED not in capabilities

    def test_the_non_evaluated_block_still_names_the_axis(self) -> None:
        state = _state(_evaluated_empty())
        named = {
            (d.capability, d.status)
            for d in build_act3_evidence(state).absent_dimensions
        }
        assert (_WEIGHTED, "evaluated_empty") in named
        assert _WEIGHTED_LABEL in _ABSENT_DIMENSION_LABELS.values()


class TestControlsKeepTheAssertionsNonVacuous:
    """A green must distinguish "the filter works" from "nothing was ever there"."""

    def test_a_genuinely_evaluated_axis_still_carries_its_item(self) -> None:
        state = _state(_evaluated())
        proj = projection_from_state(state)
        cited = [
            item for item in proj["established_items"] if item["nature"] == _STRUCTURAL
        ]
        assert len(cited) == 1, "the instrument must be able to render a non-zero"
        assert cited[0]["cites"] == [_WEIGHTED_LABEL]

    def test_a_run_without_a_ledger_keeps_the_finding(self) -> None:
        """Every pre-#1605 state (and the whole existing suite) has no ledger."""
        state = _state(None)
        capabilities = {
            f.capability for f in build_act3_evidence(state).structured_findings
        }
        assert capabilities == {_WEIGHTED}
        assert projection_from_state(state)["established_by_nature"] == {_STRUCTURAL: 1}

    def test_a_degraded_axis_without_sidecar_data_adds_nothing(self) -> None:
        """The filter drops findings; it never fabricates one to fill the gap."""
        state = _state(_evaluated_empty())
        state.dung_frameworks = {}
        assert build_act3_evidence(state).structured_findings == []
        assert projection_from_state(state)["established_items"] == []

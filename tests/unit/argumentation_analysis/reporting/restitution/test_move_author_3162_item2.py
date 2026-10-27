# -*- coding: utf-8 -*-
"""#3162 item 2 — a SETAF line says whose position the target is.

The SETAF projection (item 1, #3197) now only calls a coalition irreducible when
it is. What it cannot say is *whose* side the target belongs to: on the R1107c
state ``arg_6`` was the opponent's first position, and the writer turned a
defeat of that position into "the speaker's case stands poorly".

The coordinator's decision (R1110) accepts the measured shape:

* ``move_author`` joins ``argument_provenance[arg_id]``, in the #3180 closed
  vocabulary (``speaker`` | ``reported``), **absent when the text does not let
  us tell** — never defaulted (#1019);
* the extraction producer asks for it and the writer passes it; ``add_argument``
  writes it only when the value is in the vocabulary (the gate
  ``add_fallacy`` already applies to the same field);
* ``_setaf_finding`` qualifies the target with « (position rapportée) » when the
  raw provenance says ``reported`` — read raw, never through
  ``move_author_of()`` whose ``speaker`` default is the fallacy reader's legacy,
  not a measurement for a unit;
* the Act III briefing carries the reading rule **only when a line carries the
  qualifier**: a defeat of a reported position is a defeat of that camp, never a
  weakness of the attacker.

Anti-pendulum: the line keeps claiming no side when the datum is absent — the
qualifier appears only on a measured value.

Synthetic atoms only (privacy HARD).
"""

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_fact_extraction_to_state,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

from .test_act3_conclusion_plugin import _formalism_specific_state

_TARGET = "claim_gamma"
_ATTACKS = [{"attackers": ["claim_alpha", "claim_beta"], "target": _TARGET}]
_RULE_MARKER = "jamais une faiblesse de l'attaquant"
_QUALIFIER = "(position rapportée)"


def _state_with_move_author(value):
    state = _formalism_specific_state({"set_attacks": _ATTACKS})
    entry = {"producer": "llm_extract"}
    if value is not None:
        entry["move_author"] = value
    state.argument_provenance = {_TARGET: entry}
    return state


def _setaf_finding(state):
    (finding,) = [
        f
        for f in build_act3_evidence(state).structured_findings
        if f.capability == "setaf_reasoning"
    ]
    return finding


class TestTheProducerRecordCarriesTheMoveAuthor:
    """The datum exists only where the model stated it (closed vocabulary)."""

    def test_a_reported_position_is_recorded(self):
        state = UnifiedAnalysisState("A source text carrying one position.")
        arg_id = state.add_argument(
            "a reported position", producer="llm_extract", move_author="reported"
        )
        assert state.argument_provenance[arg_id]["move_author"] == "reported"

    def test_the_speakers_own_position_is_recorded(self):
        state = UnifiedAnalysisState("A source text carrying one position.")
        arg_id = state.add_argument(
            "the speaker's position", producer="llm_extract", move_author="speaker"
        )
        assert state.argument_provenance[arg_id]["move_author"] == "speaker"

    def test_an_out_of_vocabulary_value_is_not_written(self):
        state = UnifiedAnalysisState("A source text carrying one position.")
        arg_id = state.add_argument(
            "a position", producer="llm_extract", move_author="someone-else"
        )
        assert "move_author" not in state.argument_provenance[arg_id]

    def test_an_absent_value_is_not_defaulted(self):
        """Absent stays absent — never the historical ``speaker`` default."""
        state = UnifiedAnalysisState("A source text carrying one position.")
        arg_id = state.add_argument("a position", producer="llm_extract")
        assert "move_author" not in state.argument_provenance[arg_id]


class TestTheWriterPassesTheExtractedField:
    def test_the_extraction_output_reaches_the_provenance(self):
        state = UnifiedAnalysisState(
            "The text reports that the other camp wants to reopen the file."
        )
        _write_fact_extraction_to_state(
            {
                "arguments": [
                    {
                        "text": "the other camp wants to reopen the file",
                        "source_quote": "the other camp wants to reopen the file",
                        "move_author": "reported",
                    }
                ]
            },
            state,
            {},
        )
        (arg_id,) = state.identified_arguments
        assert state.argument_provenance[arg_id]["move_author"] == "reported"


class TestTheSetafLineNamesTheSide:
    def test_a_reported_target_is_qualified(self):
        finding = _setaf_finding(_state_with_move_author("reported"))
        assert _QUALIFIER in finding.statement
        assert "qu'aucun ne renverse seul" in finding.statement

    def test_the_speakers_own_target_claims_no_side(self):
        finding = _setaf_finding(_state_with_move_author("speaker"))
        assert _QUALIFIER not in finding.statement

    def test_an_absent_datum_claims_no_side(self):
        """Control — absent is not ``reported``: the line keeps claiming none."""
        finding = _setaf_finding(_state_with_move_author(None))
        assert _QUALIFIER not in finding.statement

    def test_a_state_without_provenance_claims_no_side(self):
        state = _formalism_specific_state({"set_attacks": _ATTACKS})
        state.argument_provenance = {}
        assert _QUALIFIER not in _setaf_finding(state).statement


class TestTheReadingRuleFollowsTheQualifier:
    """The briefing rule exists only where it has something to govern."""

    def test_the_rule_is_in_the_briefing_with_a_reported_target(self):
        prompt = build_act3_prompt(
            build_act3_evidence(_state_with_move_author("reported"))
        )
        assert _RULE_MARKER in prompt

    def test_the_rule_is_absent_without_the_qualifier(self):
        prompt = build_act3_prompt(
            build_act3_evidence(_state_with_move_author("speaker"))
        )
        assert _RULE_MARKER not in prompt

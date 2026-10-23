"""#3199 rework — Act II's binding clause follows the STATED cause.

#3146 gave a formal finding the source units of its recorded core, and the
weaving line said « rattachement : unités … (le lot de traduction de ces
unités, pas une seule) » — a sentence about a translation batch, printed
whatever the cause.

On an ``unattributed_side`` record (the class #3199 adds) only ONE flank of
the conflict carries source units: the other side has none at all. The
sentence then claimed a shared batch that does not exist. On a record that
stated no cause it asserted one of the same kind.

Witnessed here: the clause says the batch sentence for
``batch_attribution``, the known-flank sentence for ``unattributed_side``,
and nothing categorical for any other class or for a record that stated
none. The units and the line count are unchanged (control).

Opaque atoms, opaque ids — no corpus token. Zero LLM, zero JVM.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_formal_findings,
    build_act2_evidence,
    build_act2_prompt,
)

_BATCH_SENTENCE = "le lot de traduction de ces unités, pas une seule"
_KNOWN_FLANK_SENTENCE = "l'autre côté du conflit ne porte aucune unité source"


def _state(pl_records=()):
    return SimpleNamespace(
        identified_arguments={"arg_1": "these A"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=list(pl_records),
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
    )


def _pl_unsat(cause_kind, units=("u1",)):
    record = {
        "satisfiable": False,
        "formulas": ["p", "! p"],
        "message": "Inconsistent (UNSAT). Solver: cadical195",
    }
    if cause_kind is not None:
        cause = {
            "cause": cause_kind,
            # The recorded MUS core is what makes the content and its units
            # readable (#3146): without it the finding names no unit at all.
            "mus": True,
            "core": {"indices": [0, 1], "size": 2},
        }
        if units:
            cause["pairs"] = [{"sources": [list(units), []], "speakers": [[], []]}]
        record["consistency_cause"] = cause
    return record


class TestTheClauseFollowsTheCause:
    def test_the_batch_sentence_is_kept_for_a_batch_attribution(self):
        findings = _collect_formal_findings(_state([_pl_unsat("batch_attribution")]))
        pl = [f for f in findings if f.kind == "pl"]
        assert pl and pl[0].cause_kind == "batch_attribution"
        prompt = build_act2_prompt(
            build_act2_evidence(_state([_pl_unsat("batch_attribution")]))
        )
        assert _BATCH_SENTENCE in prompt

    def test_an_unattributed_side_does_not_claim_a_shared_batch(self):
        # Born-red on the previous commit: the batch sentence printed for
        # every cause, including this one, where a single flank has units.
        findings = _collect_formal_findings(_state([_pl_unsat("unattributed_side")]))
        pl = [f for f in findings if f.kind == "pl"]
        assert pl and pl[0].cause_kind == "unattributed_side"
        prompt = build_act2_prompt(
            build_act2_evidence(_state([_pl_unsat("unattributed_side")]))
        )
        assert _KNOWN_FLANK_SENTENCE in prompt
        assert _BATCH_SENTENCE not in prompt

    def test_a_between_voices_cause_asserts_no_batch(self):
        findings = _collect_formal_findings(_state([_pl_unsat("between_voices")]))
        assert [f for f in findings if f.kind == "pl"][0].cause_kind == "between_voices"
        prompt = build_act2_prompt(
            build_act2_evidence(_state([_pl_unsat("between_voices")]))
        )
        assert _BATCH_SENTENCE not in prompt and _KNOWN_FLANK_SENTENCE not in prompt

    def test_control_units_and_line_shape_are_unchanged(self):
        # Control: the finding still names the unit, and the clause keeps its
        # « rattachement : unités … » lead whatever the cause.
        findings = _collect_formal_findings(_state([_pl_unsat("batch_attribution")]))
        pl = [f for f in findings if f.kind == "pl"][0]
        assert pl.units == ["u1"]
        prompt = build_act2_prompt(
            build_act2_evidence(_state([_pl_unsat("batch_attribution")]))
        )
        assert "rattachement : unités u1" in prompt


class TestTheStatedCauseIsReadFromTheRecord:
    def test_a_record_that_stated_no_cause_names_no_class(self):
        findings = _collect_formal_findings(_state([_pl_unsat(None)]))
        pl = [f for f in findings if f.kind == "pl"][0]
        assert pl.cause_kind == ""

    def test_the_first_refuted_record_with_a_cause_wins(self):
        records = [
            {
                "satisfiable": True,
                "formulas": ["p"],
                "consistency_cause": {"cause": "self_contradiction"},
            },
            _pl_unsat("unattributed_side"),
        ]
        findings = _collect_formal_findings(_state(records))
        pl = [f for f in findings if f.kind == "pl"][0]
        assert pl.cause_kind == "unattributed_side"

"""#3199 — the decisive role reads the cause the refutation stated.

The #1914/#2307 decisive block promoted any PL record with
``satisfiable is False`` and tested content to ROLE_DECISIF with « La mise
à l'épreuve formelle établit que ce contenu testé ne tient pas » — without
reading ``consistency_cause``. Every other reader in reporting/ (act2
findings, act3 weak points, appendix causes, reading license) qualifies a
formal verdict by its stated cause; the role classifier was the one surface
that charged the speaker unconditionally.

The chosen repair (see the module comment in specialist_roles): the
REFUTATION stays decisive — the solver established it, and #1019 forbids
suppressing a real verdict — but the speaker-charging sentence is replaced
by one that names the stated cause class when that cause does not pin the
conflict inside one voice. ``self_contradiction`` is the only class that
does; a record that stated no cause is the pre-#3122/#3107 artifact shape
and keeps the unqualified statement (the acts' own rule: append a cause
only when one was stated).

Witnessed here:

* an UNSAT whose stated cause is not speaker-attributable emits NO
  « établit que ce contenu testé ne tient pas » statement, keeps its
  decisive role, and names the cause class (anti-pendulum: the role is
  never dropped);
* ``self_contradiction`` keeps the speaker-charging decisive statement
  (the control);
* a record that stated no cause keeps the unqualified statement (scope:
  qualify only what was stated);
* the FOL twin block qualifies the same way.

Opaque atoms, opaque ids — no corpus token. Zero LLM, zero JVM.
"""

import re
from types import SimpleNamespace

import pytest

from argumentation_analysis.reporting.restitution.formal_derivation import (
    _readable_atom,
)
from argumentation_analysis.reporting.restitution.specialist_roles import (
    ROLE_DECISIF,
    _STATEMENT_CAP,
    classify_specialist_roles,
)

#: The sentence that charges the speaker's content unconditionally — the
#: exact string the issue quotes. No assignment may carry it when the
#: stated cause refuses the speaker pin.
_SPEAKER_CHARGING = "établit que ce contenu testé ne tient pas"


def _state(pl_records=(), fol_records=()):
    return SimpleNamespace(
        identified_arguments={"arg_1": "these A"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=list(pl_records),
        fol_analysis_results=list(fol_records),
        modal_analysis_results=[],
        workflow_results={},
    )


def _pl_unsat(cause_kind):
    record = {
        "satisfiable": False,
        "formulas": ["p", "! p"],
        "message": "Inconsistent (UNSAT). Solver: cadical195",
    }
    if cause_kind is not None:
        record["consistency_cause"] = {"cause": cause_kind}
    return record


def _fol_unsat(cause_kind):
    record = {
        "consistent": False,
        "formulas": ["P(a)", "!P(a)"],
        "message": "incoherent",
    }
    if cause_kind is not None:
        record["consistency_cause"] = {"cause": cause_kind}
    return record


class TestNonSpeakerCauseQualifiesTheDecisiveStatement:
    @pytest.mark.parametrize(
        "cause_kind",
        [
            "unattributed_side",  # the #3199 class
            "batch_attribution",
            "undetermined",
            "between_sources",
            "between_voices",
        ],
    )
    def test_witness_no_speaker_charging_sentence(self, cause_kind):
        # Born-red on main: the block read no cause at all and emitted the
        # speaker-charging sentence for every content-backed UNSAT.
        assignments = classify_specialist_roles(_state([_pl_unsat(cause_kind)]))
        assert not any(
            _SPEAKER_CHARGING in a.statement for a in assignments
        ), f"cause {cause_kind} does not pin the conflict inside one voice"

    def test_the_role_stays_decisive_and_names_the_cause(self):
        # Anti-pendulum: the UNSAT the solver established is still a result
        # — the role survives, the sentence says what it is decisive about.
        assignments = classify_specialist_roles(
            _state([_pl_unsat("unattributed_side")])
        )
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert decisif, "an established refutation keeps a role"
        # Rework (coordinator measurement): the class was rendered as the raw
        # enum token « (unattributed_side) ». A reader cannot charge anyone
        # from a token — the statement now carries the readable label.
        assert "un côté est sans unité source" in decisif[0].statement
        assert "unattributed_side" not in decisif[0].statement
        assert "réfuté" in decisif[0].statement or "refuté" in decisif[0].statement
        assert "locuteur" in decisif[0].statement

    def test_two_stated_causes_are_both_named(self):
        record_a = _pl_unsat("batch_attribution")
        record_b = {
            "satisfiable": False,
            "formulas": ["q", "! q"],
            "consistency_cause": {"cause": "undetermined"},
        }
        assignments = classify_specialist_roles(_state([record_a, record_b]))
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert decisif
        assert "contradiction interne à un lot de traduction" in decisif[0].statement
        assert "inconsistance sans cause établie" in decisif[0].statement


class TestSelfContradictionKeepsTheDecisiveStatement:
    def test_control_self_contradiction_keeps_the_sentence(self):
        # The DoD control: the one cause that pins the conflict inside one
        # voice licenses exactly the original decisive statement.
        assignments = classify_specialist_roles(
            _state([_pl_unsat("self_contradiction")])
        )
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert decisif
        assert any(_SPEAKER_CHARGING in a.statement for a in decisif)

    def test_control_absent_cause_keeps_the_unqualified_statement(self):
        # Pre-#3122 artifact shape: nothing was stated, so nothing can be
        # qualified — the same rule the acts follow (append a cause only
        # when one was stated). Pinned so the repair does not pendulum into
        # inventing a cause the run never recorded.
        assignments = classify_specialist_roles(_state([_pl_unsat(None)]))
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert decisif
        assert any(_SPEAKER_CHARGING in a.statement for a in decisif)


class TestFolTwinQualifiesTheSameWay:
    def test_a_non_speaker_fol_cause_loses_the_speaker_charging_sentence(self):
        assignments = classify_specialist_roles(
            _state(fol_records=[_fol_unsat("batch_attribution")])
        )
        assert not any(_SPEAKER_CHARGING in a.statement for a in assignments)
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert decisif, "the FOL refutation keeps its role"
        assert "contradiction interne à un lot de traduction" in decisif[0].statement

    def test_a_self_contradicting_fol_theory_keeps_the_sentence(self):
        assignments = classify_specialist_roles(
            _state(fol_records=[_fol_unsat("self_contradiction")])
        )
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert any(_SPEAKER_CHARGING in a.statement for a in decisif)


def _long_atom(fill: str, width: int) -> str:
    return fill * width


class TestTheBoundedStatementKeepsTheQualifier:
    """Rework — the coordinator's real-state measurement.

    On the doc_A state the tested content is 155 characters and the cause
    qualifier 130: 285 > ``_STATEMENT_CAP`` (240). The cap cut at the last
    sentence boundary, which fell AFTER « ne tient pas » and BEFORE the
    qualifier — so the Décisif line rendered with no qualifier at all and
    charged the speaker again, the very defect this issue repairs. The quote
    now gives way instead: the qualifier is the measurement.
    """

    def _long_tested_record(self):
        atom = _long_atom("a", 70)
        return {
            "satisfiable": False,
            "formulas": [atom, f"! {atom}"],
            "consistency_cause": {"cause": "unattributed_side"},
        }

    def test_the_qualifier_survives_the_cap(self):
        assignments = classify_specialist_roles(_state([self._long_tested_record()]))
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert decisif
        statement = decisif[0].statement
        assert "non imputable au locuteur" in statement
        assert "un côté est sans unité source" in statement
        assert len(statement) <= _STATEMENT_CAP

    def test_the_quote_is_never_sliced(self):
        assignments = classify_specialist_roles(_state([self._long_tested_record()]))
        statement = [a for a in assignments if a.role == ROLE_DECISIF][0].statement
        # #3199 review: the first rework sliced the rendered string, which cut
        # inside the quote and left it open. Whole quotes or nothing now.
        # A ``…`` the PRODUCER put inside a balanced quote (its own bounded
        # atom rendering) is legitimate; an elision that stands where a quote
        # should close is not — so the check is structural, not lexical.
        assert statement.count("«") == statement.count("»"), statement
        for marker in re.finditer("…", statement):
            tail = statement[marker.end() : marker.end() + 2]
            assert tail.startswith(" »"), (
                "an elision marker stands outside a closed quote — the "
                f"statement was sliced, not the atom: {statement}"
            )

    def test_control_a_short_quote_is_kept_whole(self):
        # Control: within the budget, nothing is dropped — both atoms render.
        assignments = classify_specialist_roles(_state([_pl_unsat("between_voices")]))
        statement = [a for a in assignments if a.role == ROLE_DECISIF][0].statement
        assert "« p »" in statement and "« ! p »" in statement
        assert "non imputable au locuteur" in statement


class TestTheRealShapeNeverSlicesAQuote:
    """#3199 review — the coordinator's real-state shape.

    On the doc_A record the budget left for the tested content was 32
    characters: ``tested[: budget - 1]`` cut mid-word after 27 characters and
    the sentence ended in « …. », while the second quote — the negated side of
    the conflict — vanished without a trace. The real shape is TWO atoms of
    about 52 characters with cause ``unattributed_side``.
    """

    # A unit literal, not a sentence: the conflict localiser only pins a
    # verdict on a literal and its negation, which is the shape the run
    # records. These are ~52 characters each — the doc_A width.
    ATOM_A = "proposition_sans_unite_source_du_lot_de_traduction_aa"

    def _record(self):
        return {
            "satisfiable": False,
            "formulas": [self.ATOM_A, f"! {self.ATOM_A}"],
            "consistency_cause": {"cause": "unattributed_side"},
        }

    @property
    def _atoms(self):
        # The producer's own readable rendering (it turns underscores into
        # spaces for the reader): comparing against it keeps this witness
        # from re-implementing that transform.
        return {
            _readable_atom(self.ATOM_A),
            _readable_atom(f"! {self.ATOM_A}"),
        }

    def test_the_two_quotes_are_the_real_width(self):
        # Guard on the fixture itself: a short atom would fit and prove
        # nothing about the cap.
        assert 45 <= len(self.ATOM_A) <= 56, len(self.ATOM_A)

    def _statement(self) -> str:
        assignments = classify_specialist_roles(_state([self._record()]))
        return [a for a in assignments if a.role == ROLE_DECISIF][0].statement

    def test_the_qualifier_is_present(self):
        statement = self._statement()
        assert "non imputable au locuteur" in statement
        assert "un côté est sans unité source" in statement

    def test_the_quotes_stay_balanced(self):
        statement = self._statement()
        assert statement.count("«") == statement.count("»"), statement

    def test_no_quote_stands_open_before_the_period(self):
        # The measured defect shape: the sentence ended in « …. » — a quote
        # never closed, then the sentence's period. Nothing structural may
        # stand between an opening « and its closing » here.
        statement = self._statement()
        assert "…." not in statement, statement
        assert not re.search(r"«[^»]*\.", statement), statement

    def test_every_rendered_quote_is_a_whole_input_atom(self):
        statement = self._statement()
        rendered = re.findall(r"«\s*([^«»]*?)\s*»", statement)
        assert rendered, f"no quote reached the render: {statement}"
        for quote in rendered:
            assert quote in self._atoms, (
                "a rendered quote is not one of the tested atoms — it is a "
                f"slice of one: {quote!r} in {statement}"
            )

    def test_the_dropped_quotes_are_counted_not_silently_lost(self):
        # Honest absence: whatever does not fit is COUNTED, so a reader sees
        # that the render is partial instead of reading one quote as the whole.
        statement = self._statement()
        kept = len(re.findall(r"«", statement))
        if kept < 2:
            assert "(+" in statement, (
                "a dropped quote must be counted with the shared (+N …) "
                f"marker; reads {statement}"
            )
        assert len(statement) <= _STATEMENT_CAP

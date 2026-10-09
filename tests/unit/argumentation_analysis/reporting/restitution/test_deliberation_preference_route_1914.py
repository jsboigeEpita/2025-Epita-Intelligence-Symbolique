"""#1914 (R1080 dispatch) — the deliberation preference route, born red.

Measured on every saved state whose Act III ranking is non-empty: the
governance vote winner is cited by NO ranked item. Every route into
``ranked`` is a test-strength property; « the move the deliberation put
first » is a discourse property, and the Act III contract asks it to be
separated from what the solvers established. This file pins the route the
R1080 dispatch builds (``_deliberation_preference`` in
``conclusion_salience``, fed by ``build_act3_evidence``'s single
``_collect_governance`` read).

Born-red discipline (the sister-file pattern of
``test_act3_salience_channel_nered_1914.py``): this file imports the
``conclusion_salience`` MODULE — the new symbols (``KIND_PREFERENCE``,
``_deliberation_preference``, the ``governance_verdict`` parameter) are
accessed INSIDE test bodies, so pre-fix content reddens with
``AttributeError``/``TypeError`` at test time, never at collection.

Replay recipe: stash ONLY ``conclusion_salience.py`` and
``act3_conclusion_plugin.py`` to main and keep this file — every witness
below goes red while the suite's other greens are untouched.

Privacy HARD: opaque ids only, no corpus tokens, no source names.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import conclusion_salience as cs
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)


def _base() -> dict:
    """A state with NO test-strength signal (nothing ranks) — the route's
    cleanest fixture: whatever enters the ranking below enters by the
    deliberation route alone."""
    return dict(
        identified_arguments={
            "arg_1": "these A",
            "arg_7": "these B",
            "arg_99": "these Z",
        },
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
    )


def _ns(d: dict) -> SimpleNamespace:
    return SimpleNamespace(**d)


def _gv(
    winner: str = "arg_99", provenance: str | None = "vote_aggregate"
) -> SimpleNamespace:
    """A duck-typed governance verdict (the fields ``_collect_governance``
    fills and ``governance_origin`` reads)."""
    return SimpleNamespace(
        winner=winner,
        winner_provenance=provenance,
        method_provenance=None,
    )


def _q(overall: float, n: int = 10) -> dict:
    """Post-#1923 entry shape: ``overall`` is a SUM over n evaluated virtues
    (#1942) — readers normalize by ``len(scores)`` (same helper as the
    sister file; a bare overall would make the fraction nonsense)."""
    return {"overall": overall, "scores": {f"vertu_{i}": 0.5 for i in range(n)}}


def _decisif_state() -> SimpleNamespace:
    """A FOL refutation ranks P1; nothing else ranks."""
    d = _base()
    d["fol_analysis_results"] = [
        {
            "consistent": False,
            "message": "incoherent",
            "formulas": ["mortal(socrates)", "!mortal(socrates)"],
        },
    ]
    d["propositional_analysis_results"] = [{"satisfiable": True}]
    return _ns(d)


def _cited_winner_state() -> SimpleNamespace:
    """arg_1 carries a localized fallacy with weak quality — it ranks as a
    corroborant that CITES arg_1; the vote winner IS arg_1. arg_7 is
    measured strong so the population SPANS the weak bar (#1942: on a
    100%-under-bar population weak corroborates nothing and no item would
    cite the winner at all)."""
    d = _base()
    d["identified_fallacies"] = {
        "f1": {"target_argument_id": "arg_1", "type": "ad_hominem"},
    }
    d["argument_quality_scores"] = {"arg_1": _q(3.0), "arg_7": _q(8.0)}
    return _ns(d)


def _full_cap_state() -> SimpleNamespace:
    """A decisif + a mass of corroborants that alone saturates the cap;
    the winner (arg_99) has no test-strength route of its own."""
    d = _base()
    args = {f"arg_{i}": "weak" for i in range(20)}
    args["arg_99"] = "these Z"
    d["identified_arguments"] = args
    d["identified_fallacies"] = {
        f"f{i}": {"target_argument_id": f"arg_{i}", "type": "ad_hominem"}
        for i in range(20)
    }
    d["argument_quality_scores"] = {
        f"arg_{i}": _q(6.0 if i == 0 else 2.0) for i in range(20)
    }
    d["fol_analysis_results"] = [
        {
            "consistent": False,
            "message": "incoherent",
            "formulas": ["mortal(socrates)", "!mortal(socrates)"],
        },
    ]
    d["propositional_analysis_results"] = [{"satisfiable": True}]
    return _ns(d)


class TestEntry:
    """Who enters: kind ``vote`` AND an id that resolves to an identified
    argument — nothing else (each exclusion has its witness)."""

    def test_vote_winner_with_no_test_strength_route_enters(self):
        sal = cs.assess_conclusion_salience(_ns(_base()), governance_verdict=_gv())
        prefs = [i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE]
        assert len(prefs) == 1, "the vote winner must have its route in"
        assert prefs[0].cites == ("arg_99", "deliberation")
        assert prefs[0].weight == cs._WEIGHT_PREFERENCE

    def test_llm_strategy_winner_is_absent(self):
        sal = cs.assess_conclusion_salience(
            _ns(_base()), governance_verdict=_gv(provenance="llm_resolution")
        )
        assert [i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE] == []

    def test_mediation_winner_is_absent(self):
        sal = cs.assess_conclusion_salience(
            _ns(_base()), governance_verdict=_gv(provenance="conflict_resolution")
        )
        assert [i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE] == []

    def test_unrecorded_provenance_is_absent(self):
        sal = cs.assess_conclusion_salience(
            _ns(_base()), governance_verdict=_gv(provenance=None)
        )
        assert [i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE] == []

    def test_non_unit_winner_is_absent(self):
        # a designation agent id never resolves to an identified argument —
        # asking whether it sits in a ranking of units is not this question.
        sal = cs.assess_conclusion_salience(
            _ns(_base()), governance_verdict=_gv(winner="agent_1")
        )
        assert [i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE] == []

    def test_no_verdict_no_entry(self):
        # the module reads ONLY the verdict it is handed — a state carrying
        # governance_decisions but no verdict passed in must not rank a
        # preference (one reader per leaf, #1633).
        state = _ns(_base())
        state.governance_decisions = [
            {
                "method": "formal-aggregation",
                "winner": "arg_99",
                "winner_provenance": "vote_aggregate",
            }
        ]
        sal = cs.assess_conclusion_salience(state)
        assert [i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE] == []


class TestTheKindIsItsOwn:
    """Its kind is its own, and its STATEMENT says so — an énoncé, not a
    presence: the item must never read as established by a solver."""

    def test_statement_carries_the_deliberation_framing(self):
        sal = cs.assess_conclusion_salience(_ns(_base()), governance_verdict=_gv())
        pref = next(i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE)
        assert "préférence de délibération" in pref.statement
        assert "pas une force établie par un solveur" in pref.statement
        assert len(pref.statement) <= cs._STATEMENT_CAP

    def test_never_above_a_decisif(self):
        sal = cs.assess_conclusion_salience(_decisif_state(), governance_verdict=_gv())
        weights = [i.weight for i in sal.ranked]
        assert weights == sorted(weights), "the grafted list stays weight-ordered"
        pref_positions = [
            k for k, i in enumerate(sal.ranked) if i.kind == cs.KIND_PREFERENCE
        ]
        assert pref_positions, "fixture must produce the preference"
        for k in pref_positions:
            assert all(
                i.weight == cs._WEIGHT_DECISIVE for i in sal.ranked[:k]
            ), "a preference item sits above a decisif"


class TestCapAndDuplicate:
    def test_already_cited_winner_is_annoted_not_duplicated(self):
        sal = cs.assess_conclusion_salience(
            _cited_winner_state(), governance_verdict=_gv(winner="arg_1")
        )
        citing = [i for i in sal.ranked if "arg_1" in i.cites]
        assert len(citing) == 1, "the winner must appear exactly once"
        assert "deliberation" in citing[0].cites, "the anchor must travel"
        assert citing[0].kind != cs.KIND_PREFERENCE, "annotated, not duplicated"
        assert "aussi le coup que la délibération" in citing[0].statement
        assert len(citing[0].statement) <= cs._STATEMENT_CAP

    def test_winner_survives_the_cap_and_decisif_stays_first(self):
        sal = cs.assess_conclusion_salience(_full_cap_state(), governance_verdict=_gv())
        assert len(sal.ranked) <= cs._MAX_RANKED
        assert sal.ranked[0].weight == cs._WEIGHT_DECISIVE, "decisif stays first"
        prefs = [i for i in sal.ranked if i.kind == cs.KIND_PREFERENCE]
        assert len(prefs) == 1, "the winner survives the cap"
        assert "arg_99" in prefs[0].cites


class TestAct3Wiring:
    """The production path: ONE ``_collect_governance`` read, verdict passed
    to the salience, kind rendered and named in the consigne."""

    def _governed_decisif_state(self) -> SimpleNamespace:
        state = _decisif_state()
        state.governance_decisions = [
            {
                "method": "formal-aggregation",
                "winner": "arg_99",
                "winner_provenance": "vote_aggregate",
            }
        ]
        return state

    def test_evidence_ranks_the_preference_from_the_real_leaf(self):
        evidence = build_act3_evidence(self._governed_decisif_state())
        assert evidence.governance_verdict is not None
        assert evidence.governance_verdict.winner == "arg_99"
        assert any(
            i.kind == cs.KIND_PREFERENCE for i in evidence.salience.ranked
        ), "the collected verdict must feed the salience route"

    def test_prompt_renders_the_kind_and_the_consigne_names_it(self):
        prompt = build_act3_prompt(build_act3_evidence(self._governed_decisif_state()))
        assert "- P2 [preference]" in prompt, "the data line must reach the prompt"
        # the consigne pin, in ITS OWN wording (distinct from the data
        # statement — naming a constant is not naming a presence), and WITHIN
        # one rendered line: the consigne is hard-wrapped, a pin straddling
        # a wrap matches nothing
        assert "un choix de la délibération, jamais une force" in prompt
        assert "jamais au-dessus d'un P1" in prompt

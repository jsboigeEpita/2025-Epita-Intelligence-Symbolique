"""#3150 — the fallacy echo is not a structural insight, and containment is bound.

The R1106 Act III render said, right after the propositional UNSAT:

    « L'analyse de croyances montre en outre que cette contradiction reste
      confinée : la plupart des engagements survivent intacts. »

Two defects, one axis:

1. the revision base was ``arg_1 … arg_40`` while the propositional core named
   arg_53 / arg_65 / arg_76 — the revision never saw those units, so it cannot
   have measured that contradiction's extent;
2. the multiplicity « 32 retraits de cardinal 5 … plusieurs mondes consistants
   incompatibles, également minimaux » is 2⁵: five disjoint ``arg / ¬arg`` pairs
   (one per fallacy target), each retractable on either side. That is the
   fallacy signal re-encoded, not a figure the discourse yields.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _belief_revision_finding,
)

_TARGETS = ("arg_14", "arg_18", "arg_25", "arg_30", "arg_39")


def _pair_options(targets=_TARGETS) -> list:
    """Every side-selection of the pairs — the 2**n cube the producer enumerates.

    Two targets are enough to be a product; five reproduce the run's own 32.
    """
    options = []
    for mask in range(2 ** len(targets)):
        option = []
        for index, target in enumerate(targets):
            negated = (mask >> index) & 1
            option.append(f"¬{target}" if negated else target)
        options.append(option)
    return options


def _revision_state(options, *, cardinality, base_units=40, population=91, touched=10):
    original = [f"arg_{i}" for i in range(1, base_units + 1)]
    base_size = base_units + cardinality
    return SimpleNamespace(
        belief_revision_results=[
            {
                "original": original,
                "argument_labels": {},
                "minimal_retraction": {
                    "cardinality": cardinality,
                    "options": options,
                    "options_total": len(options),
                    "base_size": base_size,
                    "touched_count": touched,
                    "degraded": False,
                },
            }
        ],
        identified_arguments={
            f"arg_{i}": f"unité {i}" for i in range(1, population + 1)
        },
    )


class TestTheFallacyProductIsNotSoldAsStructure:
    def test_five_disjoint_pairs_are_named_as_a_product_of_negations(self):
        finding = _belief_revision_finding(
            _revision_state(_pair_options(), cardinality=5)
        )
        assert finding is not None
        statement = finding.statement
        # 1 — the base is named: k units of N, plus the fallacy negations.
        assert "40 engagement(s) sur 91 unités lues" in statement, statement
        assert "5 négations" in statement, statement
        assert "sophismes" in statement, statement
        assert "il ne le corrobore pas" in statement, statement
        # 2 — the multiplicity is stated as arithmetic, never as worlds.
        assert "paires croyance / négation" in statement, statement
        assert "plusieurs mondes" not in statement, statement
        assert "également minimaux" not in statement, statement
        # The cardinality stays (anti-pendulum: #1646's retraction survives).
        assert "cardinal 5" in statement, statement
        assert "32 retraits" in statement, statement

    def test_the_containment_sentence_names_the_contradiction_it_confines(self):
        finding = _belief_revision_finding(
            _revision_state(_pair_options(), cardinality=5)
        )
        assert finding is not None
        statement = finding.statement
        assert "la contradiction née de ces négations est confinée" in statement
        # base_size 45 - touched 10 => 35 survive
        assert "35 engagements survivent intacts" in statement, statement


class TestTwoPairsAreStillAProduct:
    """The collapse is about the arithmetic, not about the cardinality being
    large: two independent pairs already yield four options whose count says
    nothing about the discourse."""

    def test_two_pairs_collapse(self):
        finding = _belief_revision_finding(
            _revision_state(_pair_options(_TARGETS[:2]), cardinality=2, touched=4)
        )
        assert finding is not None
        assert "plusieurs mondes" not in finding.statement
        assert "des 2 paires croyance / négation" in finding.statement


class TestOverlappingOptionsKeepTheInsight:
    """Control (DoD): when the conflicts share a belief, the options are not a
    product and the non-unicity IS a structural figure."""

    def test_a_shared_belief_keeps_the_worlds_insight(self):
        finding = _belief_revision_finding(
            _revision_state(
                [["arg_1", "arg_2"], ["arg_1", "arg_3"]],
                cardinality=2,
                base_units=10,
                population=20,
                touched=3,
            )
        )
        assert finding is not None
        statement = finding.statement
        assert "plusieurs mondes consistants incompatibles, également minimaux" in (
            statement
        ), statement
        # The base is named here too — defect 1 is not conditional on defect 2.
        assert "10 engagement(s) sur 20 unités lues" in statement, statement


_SHARED_BELIEF = (
    "L'analyse de croyances montre en outre que cette contradiction reste "
    "confinée : la plupart des engagements survivent intacts."
)
_NAMED_BASE = (
    "la contradiction née des négations ajoutées par les sophismes est confinée "
    "sur un socle de 40 engagements"
)


def _licence_state(base_units, *, contradiction_units=("arg_53", "arg_65")):
    formulas = [f"f{i}" for i in range(8)]
    sources = [[f"arg_{100 + i}"] for i in range(8)]
    sources[4] = [contradiction_units[0]]
    sources[6] = [contradiction_units[1]]
    return SimpleNamespace(
        belief_revision_results=[{"original": list(base_units)}],
        propositional_analysis_results=[
            {
                "satisfiable": False,
                "formulas": formulas,
                "formula_sources": sources,
                "consistency_cause": {
                    "cause": "mutual_negation",
                    "mus": True,
                    "core": {"indices": [4, 6]},
                    "pairs": [
                        {
                            "left": formulas[4],
                            "right": formulas[6],
                            "sources": [sources[4], sources[6]],
                        }
                    ],
                },
            }
        ],
        fol_analysis_results=[],
    )


def _kinds(text, state):
    report = check_reading_license(text, state)
    return [flag["kind"] for flag in report["flags"]]


class TestTheLicenceBindsContainmentToItsBase:
    def test_containment_over_a_contradiction_outside_the_base_is_flagged(self):
        state = _licence_state([f"arg_{i}" for i in range(1, 41)])
        assert "containment_outside_revision_base" in _kinds(_SHARED_BELIEF, state)

    def test_a_base_that_holds_the_contradiction_is_not_flagged(self):
        state = _licence_state([f"arg_{i}" for i in range(1, 60)])
        assert "containment_outside_revision_base" not in _kinds(_SHARED_BELIEF, state)

    def test_a_sentence_that_names_its_base_is_not_flagged(self):
        state = _licence_state([f"arg_{i}" for i in range(1, 41)])
        assert "containment_outside_revision_base" not in _kinds(_NAMED_BASE, state)

    def test_no_revision_run_leaves_the_check_silent(self):
        state = _licence_state([f"arg_{i}" for i in range(1, 41)])
        state.belief_revision_results = []
        assert "containment_outside_revision_base" not in _kinds(_SHARED_BELIEF, state)

    def test_the_finding_the_plugin_emits_does_not_flag_itself(self):
        """The corrected finding names its base, so the licence stays quiet on
        the run's own sentence — the check guards the WRITER's prose, it must
        not contradict the sentence the plugin now produces."""
        state = _licence_state([f"arg_{i}" for i in range(1, 41)])
        finding = _belief_revision_finding(
            _revision_state(_pair_options(), cardinality=5)
        )
        assert finding is not None
        assert "containment_outside_revision_base" not in _kinds(
            finding.statement, state
        )

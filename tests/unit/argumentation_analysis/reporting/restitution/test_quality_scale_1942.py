"""#1942 — one unit contract for ``overall``, read as a fraction of the
applicable maximum, gated for non-vacuity.

The issue's three incompatible unit contracts: the evaluator SUMS per-virtue
[0, 1] scores (``note_finale``), while two LLM-facing wrapper descriptions
declared "overall (0-1)" — and every reader applied absolute 5.0/7.0
thresholds to whatever number it found. Measured on the real texts of the
local dumps replayed through the current (post-#1923) evaluator: the number
of evaluated virtues VARIES ({2, 6, 8}; 6 dominant), so a *perfect* argument
on 6 virtues sums to 6.0 and the absolute 7.0 strong bar is mathematically
unreachable — 98% of the population under 0.5, 100% under 0.7 even
normalized. The thresholds were never calibrated against the lexical
detectors' population; per the anti-pendulum directive this tranche does NOT
recalibrate either side.

What these tests pin (the revised dispatch DoD):

* the shared normalizer — ``overall / len(scores)``, ``None`` = unmeasured,
  never 0 (same semantics as the trace-side ``_quality_fraction`` of #1907);
* the inversion zone — a 4.8 SUM over 6 virtues is a STRONG fraction (0.8),
  not "weak" the way the absolute 5.0 read it;
* the strong band is REACHABLE — a perfect argument on few virtues
  classifies instead of falling silent between two absolute thresholds;
* the non-vacuity gate — when 100% of a run's measured population is under
  the weak bar, quality corroborates nothing and renders non-discriminant;
  a spanning population keeps the corroboration (bilateral);
* the convergence reader uses the same scale — no more manufactured
  sophisme+faible convergences on uniform populations, no more false
  "/10" in the rendered detail.

Every module imported here pre-exists on main: the suite reddens on the
BEHAVIOR (verdicts on the wrong scale), never on ImportError (leçon R881).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from argumentation_analysis.plugins import narrative_synthesis_plugin as nsp
from argumentation_analysis.reporting.restitution import conclusion_salience as cs
from argumentation_analysis.reporting.restitution import specialist_roles as sr


def _q(overall: float, n: int = 10) -> dict:
    """Post-#1923 entry shape: ``overall`` is a SUM over n evaluated virtues."""
    return {"overall": overall, "scores": {f"vertu_{i}": 0.5 for i in range(n)}}


def _base() -> dict:
    """Shared corpus shape (privacy HARD — opaque ids, no corpus tokens)."""
    return dict(
        identified_arguments={
            "arg_1": "these A",
            "arg_7": "these B",
            "arg_9": "these C",
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


class TestNormalizer:
    def test_fraction_divides_by_evaluated_virtues(self):
        entry = _q(4.8, n=6)
        assert nsp.quality_fraction(entry) == pytest.approx(0.8)

    def test_unmeasured_is_none_never_zero(self):
        # An entry without a denominator carries no measurement — collapsing
        # it to 0 would read "unmeasured" as "worst" (same contract as the
        # #1907 trace-side helper).
        assert nsp.quality_fraction(None) is None
        assert nsp.quality_fraction({"overall": 2.0}) is None
        assert nsp.quality_fraction({"overall": 2.0, "scores": {}}) is None
        assert nsp.quality_fraction({"scores": {"clarte": 1.0}}) is None
        assert nsp.quality_fraction("pas un dict") is None

    def test_perfect_few_virtues_reaches_one(self):
        # The inversion zone, quantified: 6.0 was "under 7.0" on the absolute
        # scale, but as a fraction of its 6-virtue ceiling it is perfect.
        assert nsp.quality_fraction(_q(6.0, n=6)) == 1.0


class TestSpanGate:
    def test_spans_when_one_entry_clears_the_weak_bar(self):
        assert nsp.quality_population_spans_weak({"a": _q(2.0), "b": _q(6.0)})

    def test_uniform_weak_does_not_span(self):
        assert not nsp.quality_population_spans_weak(
            {"a": _q(2.0), "b": _q(3.0), "c": _q(4.9)}
        )

    def test_empty_or_unmeasured_never_spans(self):
        assert not nsp.quality_population_spans_weak({})
        assert not nsp.quality_population_spans_weak(None)
        assert not nsp.quality_population_spans_weak({"a": {"overall": 2.0}})


class TestInversionZone:
    """The blocking né-rouge: sums over few virtues read on the right scale.

    Pre-fix (absolute thresholds) ``overall=4.8`` reads WEAK (< 5.0) — the
    exact inversion the issue documents. Normalized it is 0.8 of the
    applicable maximum: strong.
    """

    def test_sum_over_few_virtues_reads_strong_not_weak(self):
        d = _base()
        d["identified_fallacies"] = {
            "f1": {"target_argument_id": "arg_7", "type": "ad_hominem"},
        }
        d["argument_quality_scores"] = {
            "arg_7": _q(4.8, n=6),  # fraction 0.8 — under 5.0 absolute
            "arg_1": _q(3.0),  # spans the population so the gate stays open
        }
        assignments = sr.classify_specialist_roles(_ns(d))
        contra = [a for a in assignments if "arg_7" in a.cites]
        assert contra and contra[0].role == sr.ROLE_CONTRADICTOIRE
        assert not [
            a
            for a in assignments
            if a.role == sr.ROLE_CORROBORANT and "arg_7" in a.cites
        ]

    def test_perfect_argument_on_few_virtues_classifies(self):
        # Strong band reachable: 6.0/6 sits between the absolute thresholds
        # (silent pre-fix) but is a 1.0 fraction — the band must be open.
        d = _base()
        d["identified_fallacies"] = {
            "f1": {"target_argument_id": "arg_7", "type": "ad_hominem"},
        }
        d["argument_quality_scores"] = {
            "arg_7": _q(6.0, n=6),
            "arg_1": _q(3.0),
        }
        assignments = sr.classify_specialist_roles(_ns(d))
        assert any(
            a.role == sr.ROLE_CONTRADICTOIRE and "arg_7" in a.cites for a in assignments
        )


class TestNonVacuity:
    def test_uniform_weak_population_yields_no_corroboration(self):
        # 100% of the measured population under the bar: "weak" discriminates
        # nothing, so quality corroborates nothing and says so.
        d = _base()
        d["identified_fallacies"] = {
            f"f{i}": {"target_argument_id": f"arg_{i}", "type": "ad_hominem"}
            for i, _ in enumerate(d["identified_arguments"], start=1)
        }
        d["argument_quality_scores"] = {
            "arg_1": _q(2.0),
            "arg_7": _q(3.0),
            "arg_9": _q(4.0),
        }
        assignments = sr.classify_specialist_roles(_ns(d))
        assert not [a for a in assignments if a.role == sr.ROLE_CORROBORANT]
        nd_quality = [
            a
            for a in assignments
            if a.role == sr.ROLE_NON_DISCRIMINANT and "qualite" in a.cites
        ]
        assert nd_quality, "the uniform-weak vacuity must be rendered, not hidden"
        assert "3/3" in nd_quality[0].statement

    def test_spanning_population_keeps_the_corroboration(self):
        # Bilateral: the gate must not over-suppress — one not-weak entry
        # makes weakness informative again for the rest of the population.
        d = _base()
        d["identified_fallacies"] = {
            "f1": {"target_argument_id": "arg_1", "type": "faux dilemme"},
        }
        d["argument_quality_scores"] = {
            "arg_1": _q(3.0),
            "arg_7": _q(6.0),  # 0.6 — neutral, spans the bar
        }
        assignments = sr.classify_specialist_roles(_ns(d))
        assert any(
            a.role == sr.ROLE_CORROBORANT and "arg_1" in a.cites for a in assignments
        )


class TestConvergenceReader:
    def test_uniform_weak_manufactures_no_convergence(self):
        d = _base()
        d["identified_fallacies"] = {
            "f1": {"target_argument_id": "arg_1", "type": "ad_hominem"},
        }
        d["argument_quality_scores"] = {
            "arg_1": _q(2.0),
            "arg_7": _q(3.0),
        }
        result = nsp.compute_argument_convergence(_ns(d))
        methods = [s[0] for s in result["arg_1"]["signals"]]
        assert "sophisme" in methods
        assert "qualite faible" not in methods

    def test_spanning_population_keeps_the_signal_on_the_fraction_scale(self):
        d = _base()
        d["identified_fallacies"] = {
            "f1": {"target_argument_id": "arg_1", "type": "ad_hominem"},
        }
        d["argument_quality_scores"] = {
            "arg_1": _q(3.0),
            "arg_7": _q(6.0),
        }
        result = nsp.compute_argument_convergence(_ns(d))
        qualite = [s for s in result["arg_1"]["signals"] if s[0] == "qualite faible"]
        assert qualite, "a spanning population keeps the weak signal"
        detail = qualite[0][1]
        assert "du maximum applicable" in detail
        assert "/10" not in detail, "the sum is not a note sur 10 — never render one"

    def test_legacy_scoreless_entry_is_unmeasured(self):
        # Entries from the 0-1-contract era carry no denominator: reading
        # them as weak on the absolute scale was the bug, not a fallback.
        d = _base()
        d["identified_fallacies"] = {
            "f1": {"target_argument_id": "arg_1", "type": "ad_hominem"},
        }
        d["argument_quality_scores"] = {"arg_1": {"overall": 0.4}}
        result = nsp.compute_argument_convergence(_ns(d))
        methods = [s[0] for s in result["arg_1"]["signals"]]
        assert "qualite faible" not in methods


class TestStrengthsReader:
    def test_strength_reads_the_fraction(self):
        d = _base()
        d["argument_quality_scores"] = {"arg_9": _q(6.0, n=6)}  # fraction 1.0
        sal = cs.assess_conclusion_salience(_ns(d))
        assert any(
            i.kind == cs.KIND_STRENGTH and "arg_9" in i.cites for i in sal.ranked
        )

    def test_strength_statement_carries_the_fraction_not_over_ten(self):
        d = _base()
        d["argument_quality_scores"] = {"arg_9": _q(8.0, n=10)}
        sal = cs.assess_conclusion_salience(_ns(d))
        strength = next(i for i in sal.ranked if i.kind == cs.KIND_STRENGTH)
        assert "%" in strength.statement
        assert "/10" not in strength.statement

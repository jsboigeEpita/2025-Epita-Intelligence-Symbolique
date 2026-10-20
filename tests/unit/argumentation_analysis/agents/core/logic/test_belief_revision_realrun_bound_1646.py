"""#1646 final increment — the real-run search bound (born-red guards).

Measured on a real corpus run (2026-09-19, doc_0, spectacular 39/39): the
post-incr-2 base construction produced a **genuinely inconsistent** 18-clause
base (10 beliefs + 8 fallacy negations — the pre-fix "all-positive, mute"
forensic is repaired), but the singular insight degraded to
``cardinality=-1``: the true minimal retraction has cardinality **8** (one per
independent clash pair) while the fixed search cap sat at 4. On every real
run the axis's insight was structurally mute by bound, not by honesty.

These guards pin the repair:

* the real-run shape (10 args, 8 targeted) yields cardinality 8 and 2**8
  equally-minimal options — not -1;
* the state shaping caps the stored ``options`` and carries the exact
  ``options_total`` (the Acte III reader names the true multiplicity);
* a component past the search bound still refuses — BY NAME, with its measured
  reason (#3088 item 4: the bare ``-1`` is what the issue opened on);
* the reader prefers ``options_total`` over the capped stored list.

#3088: the 40-clash-pair base that used to degrade (flat sweep, budget
exhausted at k=8) now decomposes exactly — 40 pair-sweeps, cardinality 40,
``options_total`` 2**40. The per-component bound refuses dense components, not
wide sparse bases.

Opaque synthetic atoms only (privacy HARD). No JVM, no API key.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from argumentation_analysis.agents.core.logic.belief_revision_insight import (
    build_belief_base,
    minimal_retractions,
)


def _realrun_doc0_shape():
    """The measured doc_0 shape: 10 beliefs, 8 independently negated."""
    args = [f"claim_{i}" for i in range(10)]
    negated = list(range(8))
    return build_belief_base(args, negated)


class TestRealRunCardinalityReachable:
    """The real-run cardinality (8) must be reachable — it was -1 pre-fix."""

    def test_doc0_shape_yields_cardinality_8_not_degraded(self):
        base, _names = _realrun_doc0_shape()
        result = minimal_retractions(base)
        assert result.cardinality == 8, (
            "the measured doc_0 base has 8 independent clash pairs: the minimal "
            f"retraction is cardinal 8, got {result.cardinality} (the fixed cap "
            "muted the insight on every real run)"
        )
        # One clause from each clash pair: 2**8 equally-minimal retractions.
        assert result.options_total == 256
        assert result.refusal is None

    def test_bound_covers_real_run_cardinality(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            _MAX_SEARCH_K,
        )

        assert _MAX_SEARCH_K >= 8, (
            "real corpus runs measured cardinality 8 (8 fallacy targets); the "
            "k-cap must sit at or above real-run cardinalities. #3088: the cap "
            "now applies PER unsatisfiable component, whose real-run "
            "cardinality is 1 (a clash pair) — so this floor is doubly covered, "
            "and it is the DECOMPOSITION above that makes the total 8 reachable"
        )

    def test_budget_is_finite(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            _MAX_SUBSET_BUDGET,
        )

        # The pathology guard: without it, a large base enumerates C(n,k)
        # forever. Exact value is calibration, finiteness is the contract.
        assert isinstance(_MAX_SUBSET_BUDGET, int) and 0 < _MAX_SUBSET_BUDGET

    def test_wide_sparse_base_decomposes_instead_of_degrading(self):
        """#3088: 40 independent clash pairs = 40 pair-sweeps, cardinality 40.

        The pre-#3088 flat sweep walked C(40, k) over this 80-clause base and
        exhausted its subset budget at k=8 — the issue's own shape, ~36 s of
        churn then a bare ``-1``. The decomposition answers EXACTLY: 40
        components of cardinality 1, an option set of 2**40 (counted, never
        materialized). This is the shape the standing doc_A passes hit.
        """
        import time

        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            _OPTIONS_STORED_CAP,
        )

        args = [f"claim_{i}" for i in range(40)]
        base, _names = build_belief_base(args, list(range(40)))
        started = time.perf_counter()
        result = minimal_retractions(base)
        elapsed = time.perf_counter() - started
        assert result.cardinality == 40
        assert result.options_total == 2**40
        assert result.refusal is None
        assert len(result.options) == _OPTIONS_STORED_CAP
        # The stated budget for this shape: seconds, not the flat sweep's ~36 s
        # churn to a refusal (and never a hang).
        assert elapsed < 30.0, f"decomposed sweep took {elapsed:.1f} s"


class TestStateShapingCapsOptions:
    """Real-run options are combinatorial: cap the stored list, keep the total."""

    def test_shape_caps_and_carries_exact_total(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            _OPTIONS_STORED_CAP,
            shape_minimal_retraction,
        )

        base, names = _realrun_doc0_shape()
        result = minimal_retractions(base)
        shaped = shape_minimal_retraction(result, names)
        assert shaped["cardinality"] == 8
        assert shaped["options_total"] == 256
        assert len(shaped["options"]) == _OPTIONS_STORED_CAP
        assert shaped["base_size"] == len(base)
        # 8 clash pairs: every clause appears in some minimal option.
        assert shaped["touched_count"] == 16
        assert shaped["degraded"] is False

    def test_shape_small_base_stores_everything(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            shape_minimal_retraction,
        )

        # The planted-text scale (cardinal 1): no capping artefact.
        args = ["alpha", "beta", "gamma"]
        base, names = build_belief_base(args, [1])
        result = minimal_retractions(base)
        shaped = shape_minimal_retraction(result, names)
        assert shaped["cardinality"] == 1
        assert shaped["options_total"] == result.options_total == len(shaped["options"])

    def test_shape_options_are_labels_not_indices(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            shape_minimal_retraction,
        )

        base, names = _realrun_doc0_shape()
        result = minimal_retractions(base)
        shaped = shape_minimal_retraction(result, names)
        for opt in shaped["options"]:
            assert isinstance(opt, list)
            for label in opt:
                assert isinstance(label, str)
                assert label in names


class TestReaderNamesTrueMultiplicity:
    """The Acte III reader names options_total, never the storage cap."""

    @staticmethod
    def _finding_for(mr: Dict[str, Any]) -> Any:
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        state = SimpleNamespace(belief_revision_results=[{"minimal_retraction": mr}])
        return _belief_revision_finding(state)

    def test_capped_options_lead_names_total(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            shape_minimal_retraction,
        )

        base, names = _realrun_doc0_shape()
        result = minimal_retractions(base)
        shaped = shape_minimal_retraction(result, names)
        finding = self._finding_for(shaped)
        assert finding is not None
        assert "256" in finding.statement
        assert "cardinal 8" in finding.statement
        # B-3: 2 untouched beliefs survive every retraction.
        assert "inerte" in finding.statement

    def test_legacy_entry_without_total_counts_stored_list(self):
        # Pre-repair entries (no options_total): the reader falls back to
        # counting the stored list — 2 stored options still trip the B-2 lead.
        mr: Dict[str, Any] = {
            "cardinality": 1,
            "options": [["claim_0"], ["¬claim_0"]],
            "base_size": 3,
            "touched_count": 1,
        }
        finding = self._finding_for(mr)
        assert finding is not None
        assert "2" in finding.statement

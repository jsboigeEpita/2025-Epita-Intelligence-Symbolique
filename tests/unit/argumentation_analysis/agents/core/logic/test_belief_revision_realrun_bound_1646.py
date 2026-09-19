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
* a pathological base still degrades to -1 (the bound is a guard, not gone);
* the reader prefers ``options_total`` over the capped stored list.

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
        card, options = minimal_retractions(base)
        assert card == 8, (
            "the measured doc_0 base has 8 independent clash pairs: the minimal "
            f"retraction is cardinal 8, got {card} (the fixed cap muted the "
            "insight on every real run)"
        )
        # One clause from each clash pair: 2**8 equally-minimal retractions.
        assert len(options) == 256

    def test_bound_covers_real_run_cardinality(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            _MAX_SEARCH_K,
        )

        assert _MAX_SEARCH_K >= 8, (
            "real corpus runs measured cardinality 8 (8 fallacy targets); the "
            "k-cap must sit at or above real-run cardinalities"
        )

    def test_budget_is_finite(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            _MAX_SUBSET_BUDGET,
        )

        # The pathology guard: without it, a large base enumerates C(n,k)
        # forever. Exact value is calibration, finiteness is the contract.
        assert isinstance(_MAX_SUBSET_BUDGET, int) and 0 < _MAX_SUBSET_BUDGET

    def test_pathological_base_still_degrades_honestly(self):
        # 40 clash pairs: cardinality 40 is beyond any real-run k-cap — the
        # search degrades to -1 rather than fabricate (or hang).
        args = [f"claim_{i}" for i in range(40)]
        base, _names = build_belief_base(args, list(range(40)))
        card, options = minimal_retractions(base)
        assert card == -1
        assert options == []


class TestStateShapingCapsOptions:
    """Real-run options are combinatorial: cap the stored list, keep the total."""

    def test_shape_caps_and_carries_exact_total(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            _OPTIONS_STORED_CAP,
            shape_minimal_retraction,
        )

        base, names = _realrun_doc0_shape()
        card, options = minimal_retractions(base)
        shaped = shape_minimal_retraction(card, options, names)
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
        card, options = minimal_retractions(base)
        shaped = shape_minimal_retraction(card, options, names)
        assert shaped["cardinality"] == 1
        assert shaped["options_total"] == len(options) == len(shaped["options"])

    def test_shape_options_are_labels_not_indices(self):
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            shape_minimal_retraction,
        )

        base, names = _realrun_doc0_shape()
        card, options = minimal_retractions(base)
        shaped = shape_minimal_retraction(card, options, names)
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
        card, options = minimal_retractions(base)
        shaped = shape_minimal_retraction(card, options, names)
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

"""Tests for Track NN — Narrative d'adjudication (#659).

Verifies that _build_adjudication_table correctly classifies fallacy families
as 'grounded' (per-argument detection + cross-method convergence) or 'claimed'
(detected but not backed by convergence), and that render_markdown includes
the adjudication section in the generated report.
"""

import pytest

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    ConvergentVerdict,
    DeepSynthesisReport,
    FallacyDiagnosis,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_verdict(arg_id: str, score: int = 3, methods=None) -> ConvergentVerdict:
    return ConvergentVerdict(
        arg_id=arg_id,
        score=score,
        methods=methods or ["sophisme", "qualite faible", "JTMS retracte"],
        statement=f"{arg_id} flagged by {score} methods.",
    )


def _make_fallacy(
    fid: str, family: str, impacted_args: list | None = None
) -> FallacyDiagnosis:
    return FallacyDiagnosis(
        fallacy_id=fid,
        family=family,
        taxonomy_path=f"fallacy/{family}/type",
        textual_span="Some textual span.",
        commentary="Some commentary.",
        impacted_args=impacted_args or [],
    )


# ---------------------------------------------------------------------------
# _build_adjudication_table unit tests
# ---------------------------------------------------------------------------


class TestBuildAdjudicationTable:
    """DeepSynthesisAgent._build_adjudication_table."""

    def test_grounded_family_when_arg_in_verdict(self):
        """Family is 'grounded' when its per-arg fallacy targets a converged arg."""
        diagnoses = [_make_fallacy("f1", "relevance", ["arg_1"])]
        verdicts = [_make_verdict("arg_1", score=3)]
        table = DeepSynthesisAgent._build_adjudication_table(diagnoses, verdicts)
        assert len(table) == 1
        row = table[0]
        assert row["family"] == "relevance"
        assert row["status"] == "grounded"
        assert "arg_1" in row["evidence"]
        assert "3" in row["evidence"]

    def test_claimed_wide_net_family(self):
        """Family with no impacted_args (wide-net) is 'claimed'."""
        diagnoses = [_make_fallacy("f1", "causal", [])]
        verdicts = [_make_verdict("arg_1")]
        table = DeepSynthesisAgent._build_adjudication_table(diagnoses, verdicts)
        assert len(table) == 1
        row = table[0]
        assert row["family"] == "causal"
        assert row["status"] == "claimed"
        assert "whole-text" in row["evidence"]

    def test_claimed_per_arg_no_convergence(self):
        """Per-arg fallacy targeting an arg not in any convergent verdict → 'claimed'."""
        diagnoses = [_make_fallacy("f1", "presumption", ["arg_5"])]
        verdicts = [_make_verdict("arg_1")]  # arg_5 not in verdicts
        table = DeepSynthesisAgent._build_adjudication_table(diagnoses, verdicts)
        assert len(table) == 1
        row = table[0]
        assert row["status"] == "claimed"
        assert "arg_5" in row["evidence"]
        assert "no cross-method" in row["evidence"]

    def test_empty_inputs(self):
        """No diagnoses → empty table."""
        table = DeepSynthesisAgent._build_adjudication_table([], [])
        assert table == []

    def test_no_verdicts(self):
        """All families 'claimed' when no convergent verdicts."""
        diagnoses = [
            _make_fallacy("f1", "relevance", ["arg_1"]),
            _make_fallacy("f2", "causal", []),
        ]
        table = DeepSynthesisAgent._build_adjudication_table(diagnoses, [])
        assert all(r["status"] == "claimed" for r in table)

    def test_multiple_families_mixed(self):
        """Mixed: one grounded, one claimed (per-arg no convergence), one wide-net."""
        diagnoses = [
            _make_fallacy("f1", "relevance", ["arg_1"]),  # grounded
            _make_fallacy("f2", "presumption", ["arg_9"]),  # per-arg, no convergence
            _make_fallacy("f3", "inductive", []),  # wide-net
        ]
        verdicts = [_make_verdict("arg_1")]
        table = DeepSynthesisAgent._build_adjudication_table(diagnoses, verdicts)
        assert len(table) == 3
        statuses = {r["family"]: r["status"] for r in table}
        assert statuses["relevance"] == "grounded"
        assert statuses["presumption"] == "claimed"
        assert statuses["inductive"] == "claimed"

    def test_family_picks_best_grounded_arg(self):
        """When a family has multiple diagnoses, the first converged arg is cited."""
        diagnoses = [
            _make_fallacy("f1", "relevance", ["arg_3"]),  # not converged
            _make_fallacy("f2", "relevance", ["arg_1"]),  # converged
        ]
        verdicts = [_make_verdict("arg_1", score=4)]
        table = DeepSynthesisAgent._build_adjudication_table(diagnoses, verdicts)
        assert len(table) == 1
        row = table[0]
        assert row["status"] == "grounded"
        assert "arg_1" in row["evidence"]
        assert "4" in row["evidence"]

    def test_families_sorted_alphabetically(self):
        """Families appear in alphabetical order."""
        diagnoses = [
            _make_fallacy("f1", "relevance", []),
            _make_fallacy("f2", "causal", []),
            _make_fallacy("f3", "ambiguity", []),
        ]
        table = DeepSynthesisAgent._build_adjudication_table(diagnoses, [])
        families = [r["family"] for r in table]
        assert families == sorted(families)


# ---------------------------------------------------------------------------
# render_markdown integration tests
# ---------------------------------------------------------------------------


class TestRenderMarkdownAdjudicationSection:
    """render_markdown includes Adjudication section."""

    def _report_with_adjudication(self, table):
        report = DeepSynthesisReport()
        report.adjudication_table = table
        return report

    def test_adjudication_section_present_in_markdown(self):
        """render_markdown always contains the Adjudication heading."""
        report = self._report_with_adjudication([])
        md = DeepSynthesisAgent.render_markdown(report)
        assert "Adjudication" in md

    def test_grounded_family_rendered_with_checkmark(self):
        """Grounded family renders with ✅ icon."""
        table = [
            {
                "family": "relevance",
                "status": "grounded",
                "evidence": "arg_1 — 3 methods",
            }
        ]
        report = self._report_with_adjudication(table)
        md = DeepSynthesisAgent.render_markdown(report)
        assert "✅" in md
        assert "relevance" in md
        assert "arg_1" in md

    def test_claimed_family_rendered_with_warning(self):
        """Claimed family renders with ⚠️ icon."""
        table = [{"family": "causal", "status": "claimed", "evidence": "wide-net only"}]
        report = self._report_with_adjudication(table)
        md = DeepSynthesisAgent.render_markdown(report)
        assert "⚠️" in md
        assert "causal" in md

    def test_empty_adjudication_table_renders_placeholder(self):
        """Empty table renders placeholder text."""
        report = self._report_with_adjudication([])
        md = DeepSynthesisAgent.render_markdown(report)
        assert "No fallacy families to adjudicate" in md

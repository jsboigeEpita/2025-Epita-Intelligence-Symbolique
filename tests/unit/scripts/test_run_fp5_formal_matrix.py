"""Tests for the FP-5 formal-richness matrix capability classifier.

#1222 (FP-14): the depth-parity matrix refresh post-#1219 surfaced that the
``modal`` cell was OVER-LABELED ``real-verdict``. The #1219 fix let the
spectacular ``modal`` phase reach ``SimpleMlReasoner`` (``solver="tweety"``,
no longer ``"unavailable"``), but on a real political-corpus KB the extracted
formulas are malformed (URL fragments leak as predicates, prose leaks as sort
declarations), so ``MlParser.parseBeliefBase`` raises ``ParserException`` and
``is_modal_kb_consistent`` honestly returns ``(None, "parse error")``. The
phase output dict is non-empty (echoed ``formulas``/``modalities``/``solver``
keys), so ``_output_repr`` strips only ``valid=None`` (falsy) and the
``has_output`` gate mis-labeled it ``real-verdict`` — an undecidable modal
disguised as a decided one (anti-théâtre #1019).

The fix: a verdict key (``is_consistent``/``consistent``/``valid``) that EXISTS
in the unstripped ``raw_out`` with value ``None`` means the solver RAN but
could not decide → ``degraded``, never ``real-verdict``. These tests pin that
contract and guard the regression.
"""

from types import SimpleNamespace


def _result(output: dict, count: int = 1, phase: str = "modal"):
    """Build a minimal runner ``result`` dict for one phase (status=completed)."""
    return {
        "phases": {phase: SimpleNamespace(status="completed", output=output)},
        "state_snapshot": {f"{phase}_analysis_count": count},
    }


class TestFp5ModalClassifierLabeling:
    """The modal cell must be self-proving: ``real-verdict`` only when a real
    verdict (True/False) was produced — never for ``valid=None``."""

    def test_modal_valid_none_with_solver_is_degraded(self):
        """#1222: modal reached the solver (solver='tweety', #1219 fixed) but
        could not decide (valid=None, malformed corpus KB) → ``degraded``, NOT
        ``real-verdict``. The echoed formulas/modalities must not mask the
        missing verdict."""
        from scripts.run_fp5_formal_matrix import _classify_capability

        out = {
            "valid": None,
            "solver": "tweety",
            "message": "Modal KB parse error (consistency undetermined, tweety)",
            "formulas": ["type(rain)", "rain"],
            "modalities": ["none_detected"],
            "logic_type": "modal",
        }
        cls, ev = _classify_capability(_result(out), "modal", "modal_analysis_count")
        assert cls == "degraded", (
            f"#1222 REGRESSION: modal valid=None + solver='tweety' must be "
            f"degraded (solver ran, no decision), got {cls!r}. A real-verdict "
            f"label here is anti-théâtre #1019 (undecidable disguised as decided)."
        )
        # the evidence still records that the solver was reached (verdict=tweety)
        assert ev["verdict"] == "tweety"

    def test_modal_valid_true_is_real_verdict(self):
        """A genuine modal verdict (valid=True) stays ``real-verdict`` — the
        fix must not demote a real decision."""
        from scripts.run_fp5_formal_matrix import _classify_capability

        out = {"valid": True, "solver": "tweety", "message": "consistent"}
        cls, _ = _classify_capability(_result(out), "modal", "modal_analysis_count")
        assert cls == "real-verdict"

    def test_modal_valid_false_is_real_verdict(self):
        """A genuine modal rejection (valid=False) stays ``real-verdict`` — a
        False verdict is a real decision, not degraded (the #1218 contract)."""
        from scripts.run_fp5_formal_matrix import _classify_capability

        out = {"valid": False, "solver": "tweety", "message": "inconsistent"}
        cls, _ = _classify_capability(_result(out), "modal", "modal_analysis_count")
        assert cls == "real-verdict"

    def test_modal_solver_unavailable_valid_none_is_empty(self):
        """The pre-#1219 shape (solver='unavailable', valid=None) stays
        ``empty`` (honest-absent) — the solver never ran. The new degraded
        check must not fire before the honest-absent check."""
        from scripts.run_fp5_formal_matrix import _classify_capability

        out = {"valid": None, "solver": "unavailable", "message": "no solver"}
        cls, _ = _classify_capability(_result(out), "modal", "modal_analysis_count")
        assert cls == "empty"

    def test_fol_is_consistent_none_with_axioms_is_degraded(self):
        """The same over-label affected FOL fail-loud: ``is_consistent=None``
        plus echoed ``axioms`` was mis-labeled real-verdict. The fix corrects
        it to ``degraded`` (no decisive verdict)."""
        from scripts.run_fp5_formal_matrix import _classify_capability

        out = {
            "is_consistent": None,
            "axioms": ["forall x P(x)"],
            "message": "eprover unavailable",
        }
        result = {
            "phases": {"fol": SimpleNamespace(status="completed", output=out)},
            "state_snapshot": {"fol_analysis_count": 1},
        }
        cls, _ = _classify_capability(result, "fol", "fol_analysis_count")
        assert cls == "degraded"

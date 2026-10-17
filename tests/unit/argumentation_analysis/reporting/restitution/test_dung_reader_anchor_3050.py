"""#3050 — the ``unavailable`` status never prints as a phantom appendix
anchor.

Issue #3050 comment (textual impact on the R1090 render): Act II printed

    « …est déclarée indécodable sous sa sémantique … (voir Annexe
    Dung[unavailable]) »

because the compare-mode entry ``verification_unavailable`` puts the native
STATUS in the semantics-label slot, and ``appendix_ref`` folded it into an
anchor. No semantics was computed, so there is no machinery to cite: the
repair (#3050) drops the anchor and names the status in the reader's
language. The #1912 non-concluable branch with a REAL semantics label keeps
its anchor — that is the control.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_dung_extensions_to_state,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_formal_findings,
)
from argumentation_analysis.reporting.restitution.dung_reader import (
    UNAVAILABLE_STATUS,
    appendix_ref,
)

ARGS = ["arg_1", "arg_2", "arg_3", "arg_4"]
ATTACKS = [["arg_1", "arg_2"], ["arg_2", "arg_1"], ["arg_2", "arg_3"]]


def _unavailable_state() -> UnifiedAnalysisState:
    """The reasoner never computed: the writer files ``verification_unavailable``
    (the same shape as the 2672 suite's uncomputed state)."""
    state = UnifiedAnalysisState("A short discourse.")
    _write_dung_extensions_to_state(
        {
            "degraded": True,
            "semantics": "unavailable",
            "extensions": {},
            "arguments": list(ARGS),
            "attacks": [list(a) for a in ATTACKS],
        },
        state,
        {},
    )
    return state


def _undecodable_state() -> UnifiedAnalysisState:
    """A REAL semantics whose extension shape the decoder cannot read — the
    #1912 branch; the anchor must stay (control)."""
    state = UnifiedAnalysisState("A short discourse.")
    _write_dung_extensions_to_state(
        {
            "semantics": "preferred",
            "extensions": {"garbage_shape": 1},
            "arguments": list(ARGS),
            "attacks": [list(a) for a in ATTACKS],
        },
        state,
        {},
    )
    return state


def _dung_finding(state: UnifiedAnalysisState):
    findings = _collect_formal_findings(state)
    return next(f for f in findings if f.kind == "dung")


class TestAppendixRefUnavailable:
    def test_producer_returns_empty_for_the_status(self):
        assert appendix_ref(UNAVAILABLE_STATUS) == ""
        # The label is normalized before the check — case and padding cannot
        # smuggle the status into an anchor.
        assert appendix_ref("UNAVAILABLE ") == ""

    def test_real_semantics_keeps_its_anchor(self):
        assert appendix_ref("preferred") == "Annexe Dung[preferred]"


class TestAct2UnavailableProse:
    def test_no_phantom_anchor_status_named_in_french(self):
        finding = _dung_finding(_unavailable_state())
        assert finding.verdict is not None and finding.detail is not None
        # The status is named in the reader's language…
        assert "aucune sémantique n'a été calculée" in finding.verdict
        assert "indisponible" in finding.verdict
        # …and no anchor is printed: nothing was computed, nothing to cite.
        assert "Annexe Dung" not in finding.verdict
        assert "Annexe Dung" not in finding.detail
        assert "unavailable" not in finding.verdict

    def test_undecodable_real_semantics_keeps_the_anchor(self):
        finding = _dung_finding(_undecodable_state())
        assert finding.verdict is not None and finding.detail is not None
        # #1912 contract unchanged: a real semantics with an undecodable
        # shape keeps its citable anchor and its incertitude verdict.
        assert "Annexe Dung[preferred]" in finding.detail
        assert (
            "non concluable" in finding.verdict
            or "n'est pas concluable" in finding.verdict
        )

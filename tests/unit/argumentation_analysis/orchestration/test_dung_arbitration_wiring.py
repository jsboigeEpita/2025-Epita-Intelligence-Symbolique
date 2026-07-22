"""Integration test: real ``dung_arbitration`` consumer wiring (Track I1 #1501, PR2).

DoD #3 reinforced — calls the REAL pipeline handler
:func:`_invoke_dung_arbitration` and the REAL state writer
:func:`_write_dung_arbitration_to_state` on synthetic opaque candidates (no LLM,
no JVM, no pipeline spin), asserting the anti-#1019 contract end-to-end:

* the stage is a transparent passthrough when ``dung_arbitration`` is OFF;
* when ON, a DECLARED Walton-Krabbe refutation ALTERS the verdict — the targeted
  candidate is eliminated (the verdict genuinely CHANGES, not a cosmetic flag);
* when ON but nothing genuine is declared, the stage is honest-absent
  (surviving == input, no fabricated attack);
* the resulting verdict is traceable in ``UnifiedAnalysisState`` as a Dung
  framework (DoD #4).
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_dung_arbitration,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_dung_arbitration_to_state,
)


def _ctx(*, enabled: bool, with_refutation: bool) -> dict:
    """Build a synthetic pipeline context with two ML-detected candidates.

    The bridge mints ``ml_llm_<index>`` ids in stable order, so candidate 0
    (``ml_llm_0``) is declared to refute candidate 1 (``ml_llm_1``) when
    ``with_refutation`` is set — a genuine unidirectional attack.
    """
    fallacies = [
        {"fallacy_type": "appeal_to_authority", "confidence": 0.7},
        {"fallacy_type": "hasty_generalization", "confidence": 0.6},
    ]
    ctx: dict = {
        "dung_arbitration": enabled,
        "phase_hierarchical_fallacy_output": {"fallacies": fallacies},
    }
    if with_refutation:
        # WaltonKrabbeRelations = {challenger_id: frozenset({target_id})}.
        ctx["walton_krabbe_relations"] = {"ml_llm_0": frozenset({"ml_llm_1"})}
    return ctx


class TestDungArbitrationWiring:
    async def test_off_is_passthrough(self) -> None:
        out = await _invoke_dung_arbitration(
            "opaque_text", _ctx(enabled=False, with_refutation=True)
        )
        verdict = out["verdict"]
        assert verdict["enabled"] is False
        assert verdict["honest_absent"] is True
        # OFF ⇒ surviving == input (no arbitration performed, backward-compat).
        assert verdict["surviving_count"] == verdict["input_count"] == 2
        assert verdict["eliminated_ids"] == {}

    async def test_on_with_refutation_changes_verdict(self) -> None:
        out_off = await _invoke_dung_arbitration(
            "opaque_text", _ctx(enabled=False, with_refutation=True)
        )
        out_on = await _invoke_dung_arbitration(
            "opaque_text", _ctx(enabled=True, with_refutation=True)
        )
        # The verdict CHANGES across the flag (#1019): OFF keeps both candidates,
        # ON eliminates the one defeated by a defended Walton-Krabbe refutation.
        assert out_off["verdict"]["surviving_count"] == 2
        assert out_on["verdict"]["enabled"] is True
        assert out_on["verdict"]["honest_absent"] is False
        assert out_on["verdict"]["surviving_count"] == 1
        assert "ml_llm_1" in out_on["verdict"]["eliminated_ids"]
        # The attack edge (ml_llm_0 → ml_llm_1) is surfaced for auditability.
        assert ["ml_llm_0", "ml_llm_1"] in out_on["verdict"]["attacks"]

    async def test_on_without_refutation_is_honest_absent(self) -> None:
        out = await _invoke_dung_arbitration(
            "opaque_text", _ctx(enabled=True, with_refutation=False)
        )
        # No declared attack, no same-span rivalry ⇒ honest-absent: surviving == input.
        assert out["verdict"]["enabled"] is True
        assert out["verdict"]["honest_absent"] is True
        assert out["verdict"]["surviving_count"] == out["verdict"]["input_count"] == 2
        assert out["verdict"]["eliminated_ids"] == {}

    async def test_writer_records_verdict_in_state(self) -> None:
        out = await _invoke_dung_arbitration(
            "opaque_text", _ctx(enabled=True, with_refutation=True)
        )
        state = UnifiedAnalysisState("opaque_text")
        _write_dung_arbitration_to_state(out, state, {})
        # DoD #4: the verdict is traceable as a Dung framework in the state.
        arbitration = [
            f for f in state.dung_frameworks.values() if f["name"] == "dung_arbitration"
        ]
        assert len(arbitration) == 1
        ext = arbitration[0]["extensions"]
        assert ext["enabled"] is True
        assert ext["honest_absent"] is False
        assert "ml_llm_1" in ext["eliminated_ids"]
        assert ext["surviving_count"] == 1
        assert ext["input_count"] == 2
        # The AF's arguments/attacks are the opaque candidate ids / pairs.
        assert "ml_llm_0" in arbitration[0]["arguments"]
        assert ["ml_llm_0", "ml_llm_1"] in arbitration[0]["attacks"]

    async def test_writer_handles_passthrough_verdict(self) -> None:
        # A passthrough (OFF) verdict is still recorded — the stage RAN.
        out = await _invoke_dung_arbitration(
            "opaque_text", _ctx(enabled=False, with_refutation=True)
        )
        state = UnifiedAnalysisState("opaque_text")
        _write_dung_arbitration_to_state(out, state, {})
        arbitration = [
            f for f in state.dung_frameworks.values() if f["name"] == "dung_arbitration"
        ]
        assert len(arbitration) == 1
        ext = arbitration[0]["extensions"]
        assert ext["enabled"] is False
        assert ext["honest_absent"] is True

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
    """Build a synthetic pipeline context with two per-argument candidates.

    #2920 (R1063 review): the stage's sole source is the hierarchical phase's
    ``per_argument_fallacies`` field (the targeted detections), so the bridge
    mints ``per_argument_<index>`` ids in stable order — candidate 0
    (``per_argument_0``) is declared to refute candidate 1
    (``per_argument_1``) when ``with_refutation`` is set — a genuine
    unidirectional attack. The merged ``fallacies`` list is NOT a source.
    """
    per_argument_fallacies = [
        {
            "fallacy_type": "appeal_to_authority",
            "target_argument": "arg_1",
            "confidence": 0.7,
        },
        {
            "fallacy_type": "hasty_generalization",
            "target_argument": "arg_2",
            "confidence": 0.6,
        },
    ]
    ctx: dict = {
        "dung_arbitration": enabled,
        "phase_hierarchical_fallacy_output": {
            "per_argument_fallacies": per_argument_fallacies,
            # The merged list (pk-only, byte-identical to main) is present on
            # every real run — the stage must IGNORE it, not read it.
            "fallacies": [
                {"fallacy_type": "appeal_to_authority", "confidence": 0.7},
                {"fallacy_type": "hasty_generalization", "confidence": 0.6},
            ],
        },
    }
    if with_refutation:
        # WaltonKrabbeRelations = {challenger_id: frozenset({target_id})}.
        ctx["walton_krabbe_relations"] = {
            "per_argument_0": frozenset({"per_argument_1"})
        }
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
        assert "per_argument_1" in out_on["verdict"]["eliminated_ids"]
        # The attack edge (hierarchical_0 → hierarchical_1) is surfaced for auditability.
        assert ["per_argument_0", "per_argument_1"] in out_on["verdict"]["attacks"]

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
        assert "per_argument_1" in ext["eliminated_ids"]
        assert ext["surviving_count"] == 1
        assert ext["input_count"] == 2
        # The AF's arguments/attacks are the opaque candidate ids / pairs.
        assert "per_argument_0" in arbitration[0]["arguments"]
        assert ["per_argument_0", "per_argument_1"] in arbitration[0]["attacks"]

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


class TestSourceKeysHaveProducers:
    """DoD #2920 witness: every phase-output key the stage reads is written
    by a phase that exists, and every sub-field it reads off a phase dict is
    written by that phase's handler.

    Pre-#2920 the stage read ``phase_taxonomy_sophisms_output`` — no workflow
    defines a phase named ``taxonomy_sophisms`` (the taxonomy tier runs INSIDE
    ``hierarchical_fallacy``), a reader with no writer (#1019 shape). This
    witness parses the handler's own source for ``phase_<name>_output`` reads
    and requires each ``<name>`` to appear as a quoted phase name somewhere in
    the orchestration package, outside the handler's own module.

    R1063 extension: the stage reads ``per_argument_fallacies`` INSIDE the
    hierarchical phase dict. The producer of that field is the hierarchical
    handler — same module (``invoke_callables.py``), so the package-corpus
    check cannot apply. Instead the witness requires the field name to appear
    in a WRITE position (dict-literal key or item assignment) in the module,
    OUTSIDE the Dung handler's own source. A stage reading a field no handler
    writes reddens here.
    """

    def test_every_phase_key_read_has_a_real_phase(self) -> None:
        import inspect
        import re
        from pathlib import Path

        src = inspect.getsource(_invoke_dung_arbitration)
        key_names = set(re.findall(r"phase_([a-z_]+)_output", src))
        assert key_names, "the witness must find at least one phase key read"

        orchestration_dir = Path(
            _invoke_dung_arbitration.__module__.replace(".", "/")
        ).parent
        corpus = ""
        for py in sorted(orchestration_dir.rglob("*.py")):
            if py.name == "invoke_callables.py":
                continue  # the reader's own module is not a producer
            corpus += py.read_text(encoding="utf-8", errors="replace")

        missing = {name for name in key_names if f'"{name}"' not in corpus}
        assert (
            not missing
        ), f"the stage reads phase keys with no producing phase: {sorted(missing)}"

    def test_every_phase_subfield_read_is_written_by_a_handler(self) -> None:
        import inspect
        import re
        from pathlib import Path

        handler_src = inspect.getsource(_invoke_dung_arbitration)
        # Sub-fields the stage reads off a phase dict: `<var>.get("name")`
        # where <var> is the phase-dict local (hierarchical). Restrict the
        # pattern to that variable so context keys (dung_arbitration, ...)
        # are not swept in.
        field_names = set(re.findall(r'hierarchical\.get\("([a-z_]+)"\)', handler_src))
        assert (
            "per_argument_fallacies" in field_names
        ), "the witness must find the per-argument field read"

        module_path = Path(inspect.getsourcefile(_invoke_dung_arbitration))
        module_src = module_path.read_text(encoding="utf-8", errors="replace")
        # The producer must be OUTSIDE the Dung handler itself: a write in the
        # handler's own body would be self-confirmation.
        start = module_src.index(handler_src)
        outside = module_src[:start] + module_src[start + len(handler_src) :]

        missing = []
        for field in field_names:
            written = re.search(rf'\["{field}"\]\s*=|"{field}":', outside)
            if not written:
                missing.append(field)
        assert not missing, (
            f"the stage reads phase sub-fields no handler writes: {sorted(missing)}"
        )

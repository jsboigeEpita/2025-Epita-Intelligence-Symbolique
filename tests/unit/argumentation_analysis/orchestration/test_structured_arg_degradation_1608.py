"""#1608 — anti-théâtre pivot tests for the structured-arg degradation contract.

Three defects closed in #1608, each with a FALSIFIABLE pivot test (a test that
passes on the fixed code AND fails on the pre-#1608 code — "un test qui passe
avec les deux versions du code ne prouve rien"):

* **Défaut 1** — the four distinct causes (translator raised · translator ran
  and found nothing · no API key · nothing wired) used to collapse onto one
  label ``absent_no_translator`` with ``degraded`` invariant across corpus
  A/B/C. The discriminated cause now propagates to four distinct statuses, and
  ``degraded`` stops being invariant.
* **Défaut 2** — ``workflow_results.degraded`` never consulted
  ``structured_arg_status``; a workflow whose translators raised (phase
  COMPLETED, axis degraded) was reported not-degraded. Muter le registre →
  ``degraded`` bascule.
* **Défaut 3** — ``str(asyncio.TimeoutError()) == ""`` left the error registry
  with an empty message. The enriched message names the exception type, the
  phase, and the budget exceeded.

No JVM, no real LLM. Synthetic atoms only (privacy HARD — no corpus tokens).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import pytest

from argumentation_analysis.orchestration.state_writers import (
    _record_structured_arg_status,
    _resolve_absent_status,
    _translation_cause_key,
    _translation_error_key,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowExecutor,
)


class _FakeState:
    """Minimal state double exposing the two surfaces the recorder + the
    workflow degraded-reconciliation read: ``add_structured_arg_status`` and
    ``structured_arg_status``. Stores exactly what the real state stores
    (a dict with a ``degraded`` key per capability)."""

    def __init__(self) -> None:
        self.structured_arg_status: Dict[str, Dict[str, Any]] = {}
        # #1608 act-raccord: per-act degradation motifs (mirrors the real
        # UnifiedAnalysisState field populated by the act state writers).
        self.restitution_acts_degraded: Dict[str, Dict[str, Any]] = {}

    def add_structured_arg_status(
        self,
        capability: str,
        status: str,
        degraded: bool,
        reason: str,
        extension_count: int = 0,
    ) -> None:
        self.structured_arg_status[capability] = {
            "capability": capability,
            "status": status,
            "degraded": degraded,
            "reason": reason,
            "extension_count": extension_count,
        }


# =============================================================================
# Défaut 1 — four causes → four statuses; degraded no longer invariant
# =============================================================================


class TestStructuredArgStatusDiscrimination:
    """#1608 Défaut 1 — the cause discriminated by the translator must reach the
    recorder as a distinct ``(status, degraded)`` pair. Before #1608 four causes
    collapsed onto ``absent_no_translator``; this suite proves the
    discrimination AND that ``degraded`` is no longer invariant across the
    corpus-shaped causes A/B/C."""

    @staticmethod
    def _record(
        capability: str, cause: Optional[str], error: str = ""
    ) -> Dict[str, Any]:
        state = _FakeState()
        ctx: Dict[str, Any] = {}
        if cause is not None:
            ctx[_translation_cause_key(capability)] = cause
            if error:
                ctx[_translation_error_key(capability)] = error
        # output={} → no genuine structured input → absent/discrimination path.
        _record_structured_arg_status(state, capability, output={}, ctx=ctx)
        return state.structured_arg_status[capability]

    def test_translator_failed_is_degraded_true(self):
        # Corpus A — the translator raised (e.g. a timeout). Genuine structured
        # input could not be obtained → degraded.
        rec = self._record("setaf_reasoning", "translator_failed", "TimeoutError")
        assert rec["status"] == "translator_failed"
        assert rec["degraded"] is True
        assert "TimeoutError" in rec["reason"]

    def test_no_genuine_relations_is_degraded_false(self):
        # Corpus B — the translator RAN and found nothing. ANTI-PENDULE crux:
        # this is an analytical result (the text has no joint attack), not a
        # degraded pipeline. It must NOT be red.
        rec = self._record("setaf_reasoning", "no_genuine_relations")
        assert rec["status"] == "no_genuine_relations"
        assert rec["degraded"] is False
        assert "analytical result" in rec["reason"]

    def test_translator_unconfigured_is_degraded_true(self):
        # Corpus C — no LLM API key configured; the translator could not run.
        rec = self._record("setaf_reasoning", "translator_unconfigured")
        assert rec["status"] == "translator_unconfigured"
        assert rec["degraded"] is True

    def test_no_cause_recorded_keeps_legacy_absent_label(self):
        # The legacy path (nothing wired / no cause propagated) preserves the
        # #1236 honest-absent label rather than inventing a cause it did not
        # observe. ``absent_no_translator`` is NOT deleted (#1608 constraint).
        rec = self._record("setaf_reasoning", None)
        assert rec["status"] == "absent_no_translator"
        assert rec["degraded"] is True

    def test_degraded_is_no_longer_invariant_across_corpus_states(self):
        # THE PIVOT. The #1608 measure found ``degraded`` invariant (always
        # False) across corpus A/B/C. After the fix the three corpus-shaped
        # causes yield three DISTINCT ``(status, degraded)`` outcome triples —
        # the correctif now measures something. Before #1608 all three recorded
        # ``absent_no_translator`` → the set would have one element.
        outcomes = {
            (
                self._record("setaf_reasoning", c, "TimeoutError")["status"],
                self._record("setaf_reasoning", c, "TimeoutError")["degraded"],
            )
            for c in (
                "translator_failed",
                "no_genuine_relations",
                "translator_unconfigured",
            )
        }
        assert len(outcomes) == 3
        # And specifically corpus B is the one NOT degraded (anti-pendule).
        assert ("no_genuine_relations", False) in outcomes

    def test_resolve_absent_status_unknown_cause_falls_back(self):
        # Defensive: a cause string the recorder does not recognise falls back
        # to the honest-absent label rather than crash.
        status, degraded, _ = _resolve_absent_status("setaf_reasoning", "???", "")
        assert status == "absent_no_translator"
        assert degraded is True


# =============================================================================
# Défaut 2 — workflow_results.degraded reconciles the structured-arg registry
# =============================================================================


class TestWorkflowDegradedReconcilesStructuredRegistry:
    """#1608 Défaut 2 — ``_compute_workflow_degraded`` must read
    ``structured_arg_status`` so a workflow whose translators raised (phase
    COMPLETED, axis degraded) is reported degraded. Muter le registre → le
    drapeau ``degraded`` bascule (falsifiable: revert the structured read and
    the flip test fails)."""

    @staticmethod
    def _executor() -> WorkflowExecutor:
        # _compute_workflow_degraded is pure (never touches the registry), so a
        # trivial registry is enough to instantiate the executor.
        return WorkflowExecutor(registry=object())  # type: ignore[arg-type]

    @staticmethod
    def _completed_results() -> Dict[str, PhaseResult]:
        return {"p": PhaseResult("p", PhaseStatus.COMPLETED, "cap")}

    def test_clean_registry_is_not_degraded(self):
        state = _FakeState()  # empty structured_arg_status
        degraded, _, caps = self._executor()._compute_workflow_degraded(
            self._completed_results(), state
        )
        assert degraded is False
        assert caps == []

    def test_degraded_structured_axis_flips_workflow_degraded(self):
        # THE FALSIFIABILITY TEST. A structured axis marked degraded=True flips
        # the workflow-level flag EVEN THOUGH every phase COMPLETED with no
        # degraded phase. Revert the structured-arg read in
        # _compute_workflow_degraded → this assertion fails (degraded stays False).
        state = _FakeState()
        state.add_structured_arg_status(
            "setaf_reasoning", "translator_failed", True, "raised", 0
        )
        degraded, _, caps = self._executor()._compute_workflow_degraded(
            self._completed_results(), state
        )
        assert degraded is True
        assert caps == ["setaf_reasoning"]

    def test_no_genuine_relations_does_not_flip_degraded(self):
        # ANTI-PENDULE. Cause 3 carries degraded=False → it must NOT flip the
        # workflow flag. A corpus lacking joint attacks is not a degraded run.
        state = _FakeState()
        state.add_structured_arg_status(
            "setaf_reasoning", "no_genuine_relations", False, "ran empty", 0
        )
        degraded, _, caps = self._executor()._compute_workflow_degraded(
            self._completed_results(), state
        )
        assert degraded is False
        assert caps == []

    def test_phase_level_degraded_still_counted(self):
        # The structured read is ADDITIVE (honest OR), not a replacement: a
        # degraded optional phase still flags the workflow even with a clean
        # structured registry.
        results = {"p": PhaseResult("p", PhaseStatus.FAILED, "cap", degraded=True)}
        degraded, degraded_phases, _ = self._executor()._compute_workflow_degraded(
            results, _FakeState()
        )
        assert degraded is True
        assert degraded_phases == ["p"]

    def test_state_none_is_safe(self):
        degraded, _, _ = self._executor()._compute_workflow_degraded(
            self._completed_results(), None
        )
        assert degraded is False

    def test_multiple_degraded_axes_are_sorted(self):
        state = _FakeState()
        state.add_structured_arg_status(
            "weighted_argumentation", "translator_failed", True, "x", 0
        )
        state.add_structured_arg_status(
            "aspic_plus_reasoning", "translator_failed", True, "y", 0
        )
        _, _, caps = self._executor()._compute_workflow_degraded(
            self._completed_results(), state
        )
        assert caps == ["aspic_plus_reasoning", "weighted_argumentation"]


# =============================================================================
# Défaut 3 — a phase error is never empty; a timeout names phase + budget
# =============================================================================


class TestPhaseErrorIsNeverEmpty:
    """#1608 Défaut 3 — ``str(asyncio.TimeoutError()) == ""`` left the error
    registry with ``{"message": "", "timestamp": null}``. The enriched message
    names the exception type, the phase, and (for timeouts) the budget
    exceeded, so the failure is attributable rather than silent."""

    @staticmethod
    def _msg(exc: BaseException, phase: str, timeout: Optional[float]) -> str:
        return WorkflowExecutor._build_phase_error_message(exc, phase, timeout)

    def test_timeout_names_phase_and_budget(self):
        msg = self._msg(asyncio.TimeoutError(), "setaf_reasoning", 30)
        assert msg != ""
        assert "TimeoutError" in msg
        assert "setaf_reasoning" in msg
        assert "30s" in msg

    def test_exception_with_message_is_preserved(self):
        # A descriptive exception is passed through unchanged.
        msg = self._msg(ValueError("bad input"), "p", None)
        assert msg == "bad input"

    def test_bare_exception_falls_back_to_type_name(self):
        # A bare exception (empty str()) surfaces its type name rather than "".
        class _Bare(Exception):
            pass

        msg = self._msg(_Bare(), "p", None)
        assert msg == "_Bare"
        assert msg != ""

    def test_timeout_without_budget_names_type_only(self):
        # A timeout on a phase that had no budget configured still names the
        # type — never empty.
        msg = self._msg(asyncio.TimeoutError(), "p", None)
        assert msg == "TimeoutError"
        assert msg != ""


# =============================================================================
# Défaut 2 (act raccord, R752) — the restitution acts' degraded dict must feed
# capabilities_degraded, and its motifs must reach the state
# =============================================================================


class TestActDegradedFeedsCapabilities:
    """#1608 R752 — the three restitution acts return ``degraded`` as a DICT of
    motifs, but the only consumer tested ``out.get("degraded") is True`` (a dict
    is never ``is True``), so the acts structurally could not feed
    ``capabilities_degraded`` (7 declaration sites, 0 readers). The invokers now
    surface ``degraded`` as a BOOL + ``degraded_reasons`` dict; this proves the
    raccord via the extracted consumer ``_collect_degraded_capabilities``."""

    @staticmethod
    def _collect(phase_results, state, used):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _collect_degraded_capabilities,
        )

        return _collect_degraded_capabilities(phase_results, state, used)

    def test_act_with_bool_degraded_feeds_capabilities_degraded(self):
        # Post-raccord: the invoker surfaces ``degraded`` as a BOOL, so the
        # ``is True`` predicate matches and the act feeds capabilities_degraded.
        pr = {
            "act3": PhaseResult(
                "act3",
                PhaseStatus.COMPLETED,
                "act3_conclusion",
                output={
                    "act3_conclusion": "x",
                    "degraded": True,
                    "degraded_reasons": {"act3_conclusion_gate": "G2"},
                },
            )
        }
        degraded, used = self._collect(pr, None, ["act3_conclusion"])
        assert "act3_conclusion" in degraded
        assert "act3_conclusion" not in used

    def test_act_with_dict_degraded_does_not_feed(self):
        # THE FALSIFIABILITY TEST. Pre-raccord the invoker returned the dict
        # as-is; ``out.get("degraded") is True`` is False on a dict → the act
        # never fed capabilities_degraded (it stayed "used"). Revert the
        # invoker to return the raw dict and this assertion flips.
        pr = {
            "act3": PhaseResult(
                "act3",
                PhaseStatus.COMPLETED,
                "act3_conclusion",
                output={
                    "act3_conclusion": "x",
                    "degraded": {"act3_conclusion_gate": "G2"},  # dict, not bool
                },
            )
        }
        degraded, used = self._collect(pr, None, ["act3_conclusion"])
        assert "act3_conclusion" not in degraded
        assert "act3_conclusion" in used  # stayed "used" — the bug

    def test_structured_registry_axis_also_feeds(self):
        state = _FakeState()
        state.add_structured_arg_status(
            "setaf_reasoning", "translator_failed", True, "raised", 0
        )
        degraded, _ = self._collect({}, state, [])
        assert "setaf_reasoning" in degraded

    def test_clean_act_unaffected(self):
        pr = {
            "act3": PhaseResult(
                "act3",
                PhaseStatus.COMPLETED,
                "act3_conclusion",
                output={"act3_conclusion": "x"},
            )
        }
        degraded, used = self._collect(pr, None, ["act3_conclusion"])
        assert degraded == []
        assert "act3_conclusion" in used


class TestActDegradedMotifsReachState:
    """#1608 'Faire atteindre l'état aux motifs' — the act state writers persist
    ``degraded_reasons`` into ``state.restitution_acts_degraded`` so the motifs
    no longer die in the return value. Anti-pendule: an act that succeeded
    (empty / absent motifs) is NOT marked degraded."""

    @staticmethod
    def _write_act3(output, state):
        from argumentation_analysis.orchestration.state_writers import (
            _write_act3_conclusion_to_state,
        )

        _write_act3_conclusion_to_state(output, state, {})

    def test_motifs_persisted_for_degraded_act(self):
        state = _FakeState()
        state.act3_conclusion = ""
        self._write_act3(
            {
                "act3_conclusion": "concl",
                "degraded_reasons": {"act3_conclusion_gate": "G2 partielle"},
            },
            state,
        )
        assert state.restitution_acts_degraded == {
            "act3_conclusion": {"act3_conclusion_gate": "G2 partielle"}
        }

    def test_clean_act_not_marked_degraded(self):
        # No degraded_reasons → the field stays empty (anti-pendule: an act
        # that succeeded is never degraded by default).
        state = _FakeState()
        state.act3_conclusion = ""
        self._write_act3({"act3_conclusion": "concl"}, state)
        assert state.restitution_acts_degraded == {}

    def test_empty_motifs_not_persisted(self):
        state = _FakeState()
        state.act3_conclusion = ""
        self._write_act3({"act3_conclusion": "concl", "degraded_reasons": {}}, state)
        assert state.restitution_acts_degraded == {}

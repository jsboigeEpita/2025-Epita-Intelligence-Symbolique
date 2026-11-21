"""#3545 rework (review 7062184686) — the record needs its READERS, not a shape.

The first pass (#3652, ``970588861``) produced the ``inferences`` records but
left three reader-side defects, each measured by the coordinator:

1. **Licence tri-state** — ``reading_license._fol_decisions`` counted ANY
   non-empty ``inferences`` as decisive, so a lone ``no_verdict`` record gave
   ``decisive 1`` and disarmed the R1105b ``vacuous_consistency_as_strength``
   check: the synthesis could again sell "cohérence formelle" as strength on a
   FOL leg that answered nothing. A query the reasoner never answered (#2447)
   is not a decision.
2. **Act III wire** — ``formal_derivation.fol_inference_sentence`` had zero
   production callers (definition + tests only): the sentence existed, the
   render never read it. Wired like ``_delp_verdicts_finding`` (#2952): one
   projector, ``None`` when nothing was decided.
3. **Nested sanitize** — ``sanitize_state`` stripped
   ``external_checks[*].message`` but not ``inferences[*].message``, whose
   payloads carry the same solver/JVM diagnostics (parser echoes, classpath
   text).

Anti-pendulum (coordinator directive): the ``no_verdict`` records STAY in
``inferences`` — it is the readers that learn the tri-state, never the
producer that is silenced (#2447).

Privacy HARD: synthetic atoms only (``ClaimSyn``, ``dana``). Deterministic:
no JVM, no LLM, no network — the writers and readers are pure dict plumbing.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, List

from argumentation_analysis.agents.core.synthesis.reading_license import (
    _fol_decisions,
    check_reading_license,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.orchestration.state_writers import _write_fol_to_state
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)


def _record(verdict: str, message: str = "") -> dict[str, Any]:
    """One #3545 record, the exact shape ``_fol_entailment_inferences`` emits."""
    return {
        "unit_ids": ["u_syn_1"],
        "premises": ["ClaimSyn(dana)"],
        "premise_texts_source": "stated",
        "minted_under": "document_text",
        "query": "PassedSyn(dana)",
        "verdict": verdict,
        "message": message,
    }


_FOL_OUTPUT_WITH: Callable[[List[dict[str, Any]]], dict[str, Any]] = lambda recs: {
    "formulas": ["forall X: (ClaimSyn(X) => PassedSyn(X))", "ClaimSyn(dana)"],
    "consistent": True,
    "inferences": recs,
    "confidence": 1.0,
}


def _writer_built_state(
    *builds: Callable[[UnifiedAnalysisState], None]
) -> SimpleNamespace:
    """Run the REAL fol writer on a real UnifiedAnalysisState, then graft the
    resulting ``fol_analysis_results`` onto the Acte III evidence stub.

    Same contract as #2952's harness: nothing is hand-crafted between writer
    and projector — what the projector reads is exactly what the writer wrote.
    """
    real = UnifiedAnalysisState("3545 synthetic probe")
    for build in builds:
        build(real)
    state = SimpleNamespace(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks=real.dung_frameworks,
        fol_analysis_results=real.fol_analysis_results,
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    return state


def _act3_state(records: List[dict[str, Any]]) -> SimpleNamespace:
    return _writer_built_state(
        lambda real: _write_fol_to_state(_FOL_OUTPUT_WITH(records), real, {})
    )


def _capabilities(state: SimpleNamespace) -> List[str]:
    return [f.capability for f in build_act3_evidence(state).structured_findings]


def _fol_entailment_finding_fn() -> Callable[[Any], Any]:
    """Lazy import: the projector does not exist on the reworked head's parent
    (``970588861``), and a top-level import would error the whole file at
    collection — masking the OTHER witnesses' born-red."""
    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        _fol_entailment_finding,
    )

    return _fol_entailment_finding


_STRENGTH_SENTENCE = (
    "Le discours est robuste au niveau des ancrages factuels et de la "
    "cohérence formelle."
)


class TestLicenceTriState:
    """Defect 1 — ``no_verdict`` is not a decision, for the licence either."""

    def _state(self, inferences: List[Any]) -> UnifiedAnalysisState:
        state = UnifiedAnalysisState("3545 synthetic probe")
        state.add_fol_analysis_result(["P(a)"], True, inferences, message="consistent")
        return state

    def test_no_verdict_only_keeps_vacuous_and_disarms_decisive(self) -> None:
        """RED on ``970588861``: the lone ``no_verdict`` record counted as
        decisive (``decisive 1, vacuous 0``) — the exact disarm the review
        measured. The fix restores ``vacuous 1, decisive 0``."""
        decisions = _fol_decisions(self._state([_record("no_verdict")]))
        assert decisions == {"vacuous_consistent": 1, "decisive": 0}

    def test_no_verdict_does_not_mask_a_decided_sibling(self) -> None:
        """A decided verdict next to a ``no_verdict`` still counts — the
        tri-state reads the records, it does not veto the entry."""
        decisions = _fol_decisions(
            self._state([_record("no_verdict"), _record("not_entailed")])
        )
        assert decisions == {"vacuous_consistent": 0, "decisive": 1}

    def test_decided_verdicts_count_decisive(self) -> None:
        for verdict in ("entailed", "not_entailed"):
            decisions = _fol_decisions(self._state([_record(verdict)]))
            assert decisions == {"vacuous_consistent": 0, "decisive": 1}

    def test_non_dict_items_never_count(self) -> None:
        """Legacy string payloads (pre-#3545 the list was always empty, but
        the reader is shared) are not verdict records — an all-string entry
        stays vacuous, never decisive."""
        decisions = _fol_decisions(self._state(["not a record"]))
        assert decisions == {"vacuous_consistent": 1, "decisive": 0}

    def test_inconsistent_still_counts_decisive_without_any_record(self) -> None:
        """The pre-existing decisive path (``consistent is False``) is not
        narrowed by the fix — deciding an inconsistency is a decision."""
        state = UnifiedAnalysisState("3545 synthetic probe")
        state.add_fol_analysis_result(
            ["P(a)", "!P(a)"], False, [], message="inconsistent"
        )
        assert _fol_decisions(state) == {"vacuous_consistent": 0, "decisive": 1}

    def test_the_flag_still_fires_on_a_no_verdict_only_leg(self) -> None:
        """R1105b end-to-end: selling "cohérence formelle" as strength on a
        leg whose only query went unanswered must flag again. RED on
        ``970588861`` (``decisive 1`` disarmed the check)."""
        result = check_reading_license(
            _STRENGTH_SENTENCE, self._state([_record("no_verdict")])
        )
        assert "vacuous_consistency_as_strength" in [f["kind"] for f in result["flags"]]

    def test_a_decided_leg_licenses_the_sentence(self) -> None:
        """Positive control: with a real entailment verdict the sentence is
        licensed — the fix must not widen the flag to decided legs."""
        result = check_reading_license(
            _STRENGTH_SENTENCE, self._state([_record("entailed")])
        )
        assert "vacuous_consistency_as_strength" not in [
            f["kind"] for f in result["flags"]
        ]


class TestAct3Wire:
    """Defect 2 — ``fol_inference_sentence`` reaches the Acte III prompt."""

    def test_decided_record_becomes_a_finding(self) -> None:
        finding = _fol_entailment_finding_fn()(_act3_state([_record("entailed")]))
        assert finding is not None
        assert finding.capability == "fol_reasoning"
        assert "s'ensuit" in finding.statement
        assert "ne s'ensuit pas" not in finding.statement

    def test_not_entailed_carries_the_negation(self) -> None:
        finding = _fol_entailment_finding_fn()(_act3_state([_record("not_entailed")]))
        assert finding is not None
        assert "ne s'ensuit pas" in finding.statement

    def test_no_verdict_only_yields_no_finding(self) -> None:
        """Honest absence (#2952 contract): a query the reasoner never
        answered supports no sentence (#2447)."""
        assert (
            _fol_entailment_finding_fn()(_act3_state([_record("no_verdict")])) is None
        )

    def test_empty_and_malformed_yield_no_finding(self) -> None:
        finding_fn = _fol_entailment_finding_fn()
        assert finding_fn(_act3_state([])) is None
        assert finding_fn(_act3_state(["legacy string"])) is None

    def test_solver_messages_never_reach_the_statement(self) -> None:
        finding = _fol_entailment_finding_fn()(
            _act3_state(
                [_record("not_entailed", message="Erreur de parsing Tweety: boom")]
            )
        )
        assert finding is not None
        assert "Tweety" not in finding.statement
        assert "boom" not in finding.statement

    def test_finding_reaches_the_evidence_and_the_prompt(self) -> None:
        """End of the channel (#3642 ask 7 pattern): from the state writer's
        own output through ``build_act3_evidence`` to ``build_act3_prompt``.
        RED on ``970588861`` — no projector, so no capability and no sentence.
        """
        state = _act3_state([_record("entailed"), _record("not_entailed")])
        assert "fol_reasoning" in _capabilities(state)
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "s'ensuit" in prompt
        assert "ne s'ensuit pas" in prompt

    def test_no_verdict_only_renders_no_sentence(self) -> None:
        state = _act3_state([_record("no_verdict")])
        assert "fol_reasoning" not in _capabilities(state)
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "s'ensuit" not in prompt


class TestSanitizeNestedInferences:
    """Defect 3 — ``inferences[*].message`` is the same diagnostic surface as
    ``external_checks[*].message`` (#1664) and leaves with it."""

    def _state(self, message: str) -> dict[str, Any]:
        return {
            "fol_analysis_results": [
                {
                    "formulas": ["P(a)"],
                    "consistent": True,
                    "inferences": [_record("not_entailed", message=message)],
                    "external_checks": [
                        {"solver": "tweety", "agrees": None, "message": message}
                    ],
                }
            ]
        }

    def test_verdict_survives_the_solver_message_leaves(self) -> None:
        """RED on ``970588861``: the nested ``inferences[*].message`` survived
        sanitize with the parser echo intact. The verdict and the record's
        arity survive — no export reader reads the message."""
        noisy = "Erreur de parsing Tweety: Variable(s) 'x' not found in quantification"
        out = sanitize_state(self._state(noisy))
        entry = out["fol_analysis_results"][0]
        assert entry["inferences"][0]["verdict"] == "not_entailed"
        assert entry["inferences"][0]["query"] == "PassedSyn(dana)"
        assert "Tweety" not in (entry["inferences"][0].get("message") or "")

    def test_external_checks_control_stays_stripped(self) -> None:
        """Positive control: the pre-existing ``external_checks`` leaf keeps
        its behavior — the fix adds a sibling, never replaces it."""
        out = sanitize_state(self._state("Erreur de parsing Tweety: boom"))
        check = out["fol_analysis_results"][0]["external_checks"][0]
        assert "Tweety" not in (check.get("message") or "")

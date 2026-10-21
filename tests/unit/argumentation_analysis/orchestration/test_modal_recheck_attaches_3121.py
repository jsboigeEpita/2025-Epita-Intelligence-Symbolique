"""#3121 — one modal analysis per formula set, and the entry says what it decided.

Observed on the R1104 tunnel pass (doc_A): the modal phase and the external
modal solver ran the SAME 6-formula knowledge base, and
``_write_external_modal_solver_to_state`` appended its verdict as a SECOND
``modal_analysis_results`` entry — the modal sibling of the #3106 FOL defect.
The synthesis read two entries as "valid under both of its frames", although
one KB had been decided twice by the same prover. Worse, what the prover
decided was CONSISTENCY (``is_modal_kb_consistent``), stored under the key
``valid`` and rendered by the narrative synthesis as modal validity, on a KB
where no modal operator had been detected (``modalities == ['none_detected']``).

The repair mirrors #3108 at the writer — the single site every reader
consumes: an external re-check whose formula list an entry already holds
ATTACHES to that entry (``external_checks``), through the SAME shared helper
the FOL leg uses. The producers now name the property they decided
(``decided_property``), and the synthesis words the verdict by that property —
"consistent", never "valid" — and hands the LLM "no modal operator detected"
when ``modalities`` says so.

The R1104 snapshot lives on the coordinator's seat (gitignored); its measured
shape is quoted in the issue table and reconstructed here with opaque
predicates — counts and keys only, no corpus content.

Real ``UnifiedAnalysisState`` objects, the production writers, the real
synthesis static readers — no network, no LLM, zero spend.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_external_modal_solver_to_state,
    _write_modal_to_state,
)

# The R1104 measured shape: 6 opaque predicates, no modal operator detected.
_R1104_FORMULAS = ["P1(a)", "P2(a, b)", "!P3(c)", "P4(b)", "P5(a, c)", "P6(c)"]
_NONE_DETECTED = ["none_detected"]


def _internal_output(
    formulas=None,
    valid=True,
    modalities=None,
    message="Knowledge base is consistent.",
):
    """Exact emit shape of ``_invoke_modal_logic`` (ModalHandler branch)."""
    return {
        "formulas": list(formulas if formulas is not None else _R1104_FORMULAS),
        "valid": valid,
        "modalities": list(modalities if modalities is not None else _NONE_DETECTED),
        "logic_type": "modal",
        "solver": "tweety",
        "message": message,
        "modal_status": "decided" if valid in (True, False) else "unverified",
        "decided_property": "kb_consistency",
    }


def _external_output(
    formulas=None,
    valid=True,
    modalities=None,
    solver="spass",
    message="Knowledge base is consistent (spass).",
):
    """Exact emit shape of ``_invoke_external_modal_solver`` (SPASS branch)."""
    return {
        "formulas": list(formulas if formulas is not None else _R1104_FORMULAS),
        "valid": valid,
        "modalities": list(modalities if modalities is not None else _NONE_DETECTED),
        "solver": solver,
        "degraded": valid is None,
        "message": message,
        "logic_type": "modal",
        "decided_property": "kb_consistency",
    }


class TestOneModalAnalysisPerFormulaSet:
    def test_the_r1104_replay_holds_one_entry(self):
        """DoD 4 — the measured double-entry run replays as ONE analysis.

        Before the fix this state held ``modal_1`` AND ``modal_2`` on the same
        6 formulas; the synthesis narrated "valid under both of its frames".
        """
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(_internal_output(), state, {})
        _write_external_modal_solver_to_state(_external_output(), state, {})

        assert len(state.modal_analysis_results) == 1
        entry = state.modal_analysis_results[0]
        assert len(entry["formulas"]) == 6
        assert entry["valid"] is True
        assert len(entry["external_checks"]) == 1
        check = entry["external_checks"][0]
        assert check["solver"] == "spass"
        assert check["valid"] is True
        assert check["agrees"] is True
        assert "spass" in check["message"]

    def test_a_divergent_recheck_carries_the_external_verdict(self):
        """Same formula list ⇒ one entry; a divergence is not silently absorbed."""
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(_internal_output(valid=True), state, {})
        _write_external_modal_solver_to_state(
            _external_output(valid=False, message="Knowledge base is inconsistent."),
            state,
            {},
        )

        assert len(state.modal_analysis_results) == 1
        entry = state.modal_analysis_results[0]
        assert entry["valid"] is False, "the prover's decision carries"
        assert entry["valid_source"] == "external:spass"
        assert entry["superseded_verdict"] == {
            "valid": True,
            "source": "modal_agent",
        }, "the verdict it displaced must stay readable, not be erased"
        assert entry["external_checks"][0]["agrees"] is False

    def test_a_degraded_entry_takes_the_external_verdict(self):
        """An agent that decided nothing must not hide a real external decision."""
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(
            _internal_output(valid=None, message="unavailable:no-solver — OOM"),
            state,
            {},
        )
        _write_external_modal_solver_to_state(_external_output(valid=True), state, {})

        assert len(state.modal_analysis_results) == 1
        entry = state.modal_analysis_results[0]
        assert entry["valid"] is True
        assert entry["valid_source"] == "external:spass"
        assert entry["external_checks"][0]["agrees"] is None

    def test_a_different_formula_set_appends(self):
        """Only a re-check attaches; a genuinely new KB is a second analysis."""
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(_internal_output(), state, {})
        _write_external_modal_solver_to_state(
            _external_output(formulas=["Q1(a)", "Q2(b)"]), state, {}
        )

        assert len(state.modal_analysis_results) == 2

    def test_a_degraded_external_answer_never_displaces(self):
        """None from the prover records the attempt, changes no verdict (#1019)."""
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(_internal_output(valid=True), state, {})
        _write_external_modal_solver_to_state(
            _external_output(valid=None, message="unavailable:no-solver"), state, {}
        )

        assert len(state.modal_analysis_results) == 1
        entry = state.modal_analysis_results[0]
        assert entry["valid"] is True
        assert "valid_source" not in entry
        assert entry["external_checks"][0]["agrees"] is None


class TestTheEntrySaysWhatWasDecided:
    def test_the_entry_carries_the_decided_property(self):
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(_internal_output(), state, {})
        assert state.modal_analysis_results[0]["decided_property"] == "kb_consistency"

    def test_the_external_append_path_carries_it_too(self):
        """A formula set no entry holds still appends — with its property."""
        state = UnifiedAnalysisState("texte")
        _write_external_modal_solver_to_state(
            _external_output(formulas=["Q1(a)"]), state, {}
        )
        entry = state.modal_analysis_results[0]
        assert entry["decided_property"] == "kb_consistency"
        assert "external solver" in entry["message"]

    def test_a_pre_3121_entry_keeps_its_exact_shape(self):
        """Strictly additive: an entry written without the property keeps it."""
        state = UnifiedAnalysisState("texte")
        state.add_modal_analysis_result(["P(a)"], True, _NONE_DETECTED, message="m")
        entry = state.modal_analysis_results[0]
        assert entry == {
            "id": entry["id"],
            "formulas": ["P(a)"],
            "valid": True,
            "modalities": _NONE_DETECTED,
            "message": "m",
        }


class TestSynthesisWordsTheProperty:
    """DoD 2 & 3 — the briefing the LLM reads says consistency and the missing
    operator, never "valid", for a decided consistency verdict."""

    @staticmethod
    def _briefing():
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(_internal_output(), state, {})
        _write_external_modal_solver_to_state(_external_output(), state, {})
        return DeepSynthesisAgent.build_artifact_briefing(state)

    @staticmethod
    def _modal_lines(briefing: str):
        return [
            ln
            for ln in briefing.splitlines()
            if "[artifact:modal_analysis_results" in ln
        ]

    def test_the_briefing_says_consistent_not_valid(self):
        lines = self._modal_lines(self._briefing())
        assert lines, "the briefing must cite the modal entry"
        assert len(lines) == 1, "one KB, one cited analysis"
        assert "verdict=consistent" in lines[0]
        assert (
            "valid" not in lines[0].lower()
        ), "a consistency verdict must not reach the narrative as validity"

    def test_none_detected_reaches_the_briefing(self):
        lines = self._modal_lines(self._briefing())
        assert any("no modal operator detected" in ln for ln in lines)

    def test_formal_findings_carry_the_property_and_the_operator_note(self):
        state = UnifiedAnalysisState("texte")
        _write_modal_to_state(_internal_output(), state, {})
        _write_external_modal_solver_to_state(_external_output(), state, {})

        findings = DeepSynthesisAgent._build_formal_findings(state)
        modal = [f for f in findings if f.logic_type == "Modal"]
        assert len(modal) == 1
        results = modal[0].results
        assert results == ["consistent", "no modal operator detected"]
        assert all("valid" not in r.lower() for r in results)

    def test_a_legacy_entry_keeps_the_valid_label(self):
        """Compat (#1019-class): a pre-#3121 entry states no property, so the
        reader cannot know what was decided — it keeps the legacy word."""
        assert DeepSynthesisAgent._verdict_label_modal({"valid": True}) == "valid"
        assert DeepSynthesisAgent._verdict_label_modal({"valid": False}) == "invalid"

    def test_a_query_acceptance_verdict_is_labelled_as_such(self):
        """The internal TweetyBridge fallback decides KB ⊨ KB acceptance, not
        consistency — its verdict must not read as validity either."""
        label_true = DeepSynthesisAgent._verdict_label_modal(
            {"valid": True, "decided_property": "modal_query_acceptance"}
        )
        label_false = DeepSynthesisAgent._verdict_label_modal(
            {"valid": False, "decided_property": "modal_query_acceptance"}
        )
        assert label_true == "accepted"
        assert label_false == "rejected"

"""#3432 (ask 6b + ask 3) — a claim contradicted by a distant passage, decided
by the lens.

Synthetic documents only, opaque ids, no corpus content. The LLM translation
and the propositional reasoner are INJECTED: these witnesses pin the
input/output contract around the wired lens (``TweetyBridge`` in production),
never a second judging implementation. No JVM is started.

Ask 3 note: the announced-check carrier (Act I ``POINT À TRANCHER`` → Act III
closure) was delivered by #3445 (merged 2026-11-05, before this dispatch).
The witness here PINS that contract on a synthetic state in this file — it is
deliberately NOT a born-red re-measurement: the fix landed before the
dispatch, and re-measuring a fixed defect as red would be theatre.
"""

from __future__ import annotations

import asyncio
import json

from argumentation_analysis.agents.core.reading import (
    build_cross_passage_consistency,
    cross_passage_note,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# --- the synthetic document: a claim and its contradiction, far apart ------
#
# Fully synthetic French text. The thesis states the programme was applied
# everywhere; a passage ~20 400 characters later states it was applied
# nowhere. No corpus content, no source names.

_THESIS_QUOTE = "Le programme d'échange a été appliqué dans toutes les régions du pays."
_CONTRA_QUOTE = "Le programme d'échange n'a été appliqué dans aucune région du pays."
_FILLER_SENTENCE = (
    "Les échanges portent sur des volumes mesurés, publiés chaque trimestre "
    "par l'office de statistique, avec les réserves de méthode habituelles."
)


def _synthetic_document() -> str:
    """A document whose contradiction sits ≥ 20 000 characters away."""
    head = f"Exposé de synthèse. {_THESIS_QUOTE} "
    filler = (_FILLER_SENTENCE + " ") * 187  # ~20 400 characters of distance
    tail = f"En conclusion, un constat s'impose. {_CONTRA_QUOTE}"
    document = head + filler + tail
    assert document.index(_CONTRA_QUOTE) - document.index(_THESIS_QUOTE) >= 20000
    return document


def _reading_state(document: str) -> UnifiedAnalysisState:
    """A state whose first reading named the thesis and the contradicting
    pillar, each with its verbatim quote and offset (#3442's record shape)."""
    state = UnifiedAnalysisState(document)
    state.defining_moves = {
        "moves": [
            {
                "kind": "thesis",
                "reading": "La thèse : application généralisée.",
                "quote": _THESIS_QUOTE,
                "offset": document.index(_THESIS_QUOTE),
                "basis": "first_reading",
                "slot": "thesis",
            },
            {
                "kind": "claim",
                "reading": "Un pilier : le constat final.",
                "quote": _CONTRA_QUOTE,
                "offset": document.index(_CONTRA_QUOTE),
                "basis": "first_reading",
                "slot": "pillar",
            },
        ],
        "dropped_quotes": 0,
        "status": "ok",
        "read_scope": {},
        "basis": "first_reading",
    }
    return state


class _MiniSatBridge:
    """The injected lens: UNSAT exactly when the theory carries a claim and
    its negation. The decision is the SOLVER's — production delegates the
    same decision to TweetyBridge over the same belief set."""

    def check_consistency(self, belief_set: str, logic_type: str = "propositional"):
        atoms = [line.strip() for line in belief_set.splitlines() if line.strip()]
        positive = {a for a in atoms if not a.startswith("!")}
        negated = {a[1:] for a in atoms if a.startswith("!")}
        if positive & negated:
            return False, "UNSAT"
        return True, "SAT"


def _translation_llm(document: str):
    """A deterministic translator: each passage id answers its own formula —
    the thesis asserts ``programme_applied``, the pillar its negation. A
    batch prompt carrying BOTH quotes answers BOTH keys (the central theory
    is translated in ONE call, so its propositions mean the same thing on
    both sides); a per-slot prompt answers one. The atoms are shared across
    the two passages BY CONSTRUCTION of this scenario — the pair's UNSAT is
    the document's own contradiction, not a vocabulary artefact."""

    async def llm(prompt: str) -> str:
        answer: dict = {}
        if _THESIS_QUOTE in prompt:
            answer["s1"] = ["programme_applied"]
        if _CONTRA_QUOTE in prompt:
            answer["s2"] = ["!programme_applied"]
        return json.dumps(answer)

    return llm


class TestTheLensDecidesTheDistantContradiction:
    def test_a_contradiction_20000_characters_apart_is_reported_with_both_quotes(
        self,
    ):
        document = _synthetic_document()
        state = _reading_state(document)

        payload = asyncio.run(
            build_cross_passage_consistency(
                state,
                _translation_llm(document),
                bridge=_MiniSatBridge(),
            )
        )

        assert payload["status"] == "inconsistent"
        findings = payload["findings"]
        assert len(findings) == 1
        finding = findings[0]
        assert finding["gap"] >= 20000
        # Both quotes are the DOCUMENT's own characters at their recorded
        # offsets — the citation rule can re-find them (never a paraphrase).
        for side in ("left", "right"):
            entry = finding[side]
            assert entry["quote"] in document
            assert document.find(entry["quote"]) == entry["offset"]
        assert {finding["left"]["slot"], finding["right"]["slot"]} == {
            "thesis",
            "pillar",
        }
        state.cross_passage_consistency = payload
        note = cross_passage_note(state)
        assert "contradiction" in note
        assert f"« {_THESIS_QUOTE} »" in note
        assert f"« {_CONTRA_QUOTE} »" in note
        assert "(position " in note

    def test_the_kb_is_built_from_the_defining_moves_not_the_extraction(self):
        document = _synthetic_document()
        state = _reading_state(document)
        # The extraction window's units say something else entirely: the KB
        # must not read them.
        state.identified_arguments = {
            "arg_1": "Une unité extraite sans rapport avec la thèse.",
        }
        state.argument_provenance = {
            "arg_1": {"producer": "llm_extract", "offset": 5},
        }
        prompts = []
        inner = _translation_llm(document)

        async def llm_recording(prompt: str) -> str:
            prompts.append(prompt)
            return await inner(prompt)

        asyncio.run(
            build_cross_passage_consistency(
                state, llm_recording, bridge=_MiniSatBridge()
            )
        )

        assert prompts, "the check must have called the translator"
        for prompt in prompts:
            assert _THESIS_QUOTE in prompt or _CONTRA_QUOTE in prompt
            assert "unité extraite" not in prompt

    def test_no_llm_route_is_a_named_absence_never_a_verdict(self):
        document = _synthetic_document()
        state = _reading_state(document)

        payload = asyncio.run(
            build_cross_passage_consistency(state, None, bridge=_MiniSatBridge())
        )

        assert payload["status"] == "unreachable"
        assert payload["reason"] == "no_llm_translation_route"
        assert payload["findings"] == []
        state.cross_passage_consistency = payload
        assert "non atteint" in cross_passage_note(state)


class TestTheControlCaseAndTheUndecidedCase:
    def test_a_coherent_document_reports_no_inconsistency(self):
        document = _synthetic_document()
        state = _reading_state(document)

        class _AlwaysSat(_MiniSatBridge):
            def check_consistency(self, belief_set, logic_type="propositional"):
                return True, "SAT"

        payload = asyncio.run(
            build_cross_passage_consistency(
                state, _translation_llm(document), bridge=_AlwaysSat()
            )
        )

        assert payload["status"] == "checked"
        assert payload["findings"] == []
        state.cross_passage_consistency = payload
        note = cross_passage_note(state)
        assert "aucune contradiction" in note
        # A SAT theory of free propositions is the common case: the note may
        # not claim the DOCUMENT is consistent.
        assert "cohérent" not in note

    def test_an_undeciding_reasoner_is_an_absence_not_a_false(self):
        document = _synthetic_document()
        state = _reading_state(document)

        class _Undecided:
            def check_consistency(self, belief_set, logic_type="propositional"):
                return None, "Degraded"

        payload = asyncio.run(
            build_cross_passage_consistency(
                state, _translation_llm(document), bridge=_Undecided()
            )
        )

        assert payload["status"] == "undecided"
        assert payload["findings"] == []
        state.cross_passage_consistency = payload
        assert "non tranche" in cross_passage_note(state)

    def test_a_state_without_the_first_reading_says_its_absence(self):
        state = UnifiedAnalysisState("Un texte court sans première lecture.")

        payload = asyncio.run(
            build_cross_passage_consistency(
                state, _translation_llm("x"), bridge=_MiniSatBridge()
            )
        )

        assert payload["status"] == "unreachable"
        assert payload["reason"] == "no_first_reading_slots"

    def test_the_note_on_states_that_never_ran_the_check(self):
        # A bare state still carries the DEFAULT record: the honest named
        # absence renders, never silence — symmetric with first_reading_note.
        note = cross_passage_note(UnifiedAnalysisState("Texte."))
        assert "non atteint" in note
        # A state with no record AT ALL (dict-shaped, or another class) yields
        # no block: the prompt omits the section rather than putting a
        # producer's vocabulary where none ran (#3395).
        assert cross_passage_note({}) == ""
        assert cross_passage_note(object()) == ""


class TestTheWiring:
    def test_the_state_writer_persists_the_verdict_under_its_capability(self):
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "cross_passage_consistency" in CAPABILITY_STATE_WRITERS
        state = UnifiedAnalysisState("Texte.")
        payload = {
            "status": "checked",
            "reason": "",
            "checked": 3,
            "findings": [],
        }
        CAPABILITY_STATE_WRITERS["cross_passage_consistency"](payload, state, {})
        assert state.cross_passage_consistency["status"] == "checked"
        assert state.cross_passage_consistency["basis"] == "cross_passage_consistency"

    def test_the_registry_serves_the_capability_and_the_panel_workflow_has_the_phase(
        self,
    ):
        from argumentation_analysis.orchestration.registry_setup import setup_registry
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        registry = setup_registry(include_optional=False)
        assert registry.find_for_capability("cross_passage_consistency")
        phase_names = [p.name for p in build_spectacular_workflow().phases]
        assert "cross_passage_consistency" in phase_names


class TestTheAnnouncedCheckCarrierHoldsOnASyntheticState:
    """Ask 3 — the carrier #3445 landed BEFORE this dispatch: this pins the
    contract (not a born-red re-measurement) on a synthetic state, in the
    same file as the cross-passage family it belongs to."""

    def test_act1_announces_a_point_and_act3_evidence_carries_it(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            _extract_announced_checks,
        )
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_evidence,
        )

        state = UnifiedAnalysisState(
            "Texte synthétique portant un point annoncé, sans corpus."
        )
        narrative = (
            "Mise en situation synthétique.\n"
            "POINT À TRANCHER : le dilemme annoncé est-il réel ?\n"
        )
        checks = _extract_announced_checks(narrative)
        assert checks == ["le dilemme annoncé est-il réel ?"]
        state.announced_checks = checks

        evidence = build_act3_evidence(state)
        assert evidence.announced_checks == checks
